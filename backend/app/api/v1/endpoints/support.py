"""
Support system API endpoints
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_admin, verify_bot_token
from app.models.admin import AdminUser
from app.models.support import (
    SupportTicket, SupportMessage, SupportSettings,
    TicketStatus, TicketPriority, MessageSender
)
from app.core.redis import redis_client

router = APIRouter()


# ============= Schemas =============

class MessageOut(BaseModel):
    id: UUID
    ticket_id: UUID
    sender_type: str
    sender_admin_id: Optional[UUID] = None
    sender_admin_name: Optional[str] = None
    text: Optional[str] = None
    attachments: Optional[List[dict]] = None
    is_read: bool
    delivered_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TicketOut(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    telegram_user_id: int
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    telegram_last_name: Optional[str] = None
    subject: Optional[str] = None
    status: str
    priority: str
    assigned_admin_id: Optional[UUID] = None
    assigned_admin_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    resolved_at: Optional[datetime] = None
    message_count: int
    unread_count: int
    last_message: Optional[MessageOut] = None
    
    class Config:
        from_attributes = True


class TicketDetailOut(TicketOut):
    messages: List[MessageOut] = []


class TicketListResponse(BaseModel):
    tickets: List[TicketOut]
    total: int
    page: int
    per_page: int


class SendMessageRequest(BaseModel):
    text: str
    attachments: Optional[List[dict]] = None


class UpdateTicketRequest(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_admin_id: Optional[UUID] = None


class SupportSettingsOut(BaseModel):
    auto_reply_enabled: bool
    auto_reply_message: str
    working_hours_enabled: bool
    working_hours_start: str
    working_hours_end: str
    working_hours_timezone: str
    outside_hours_message: str
    notify_new_ticket: bool
    notify_new_message: bool
    
    class Config:
        from_attributes = True


class UpdateSupportSettingsRequest(BaseModel):
    auto_reply_enabled: Optional[bool] = None
    auto_reply_message: Optional[str] = None
    working_hours_enabled: Optional[bool] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    working_hours_timezone: Optional[str] = None
    outside_hours_message: Optional[str] = None
    notify_new_ticket: Optional[bool] = None
    notify_new_message: Optional[bool] = None


class SupportStatsOut(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_today: int
    avg_response_time_minutes: Optional[float] = None
    unread_messages: int


# ============= Endpoints =============

@router.get("/stats", response_model=SupportStatsOut)
async def get_support_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Get support dashboard statistics"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Total tickets
    total_result = await db.execute(select(func.count(SupportTicket.id)))
    total_tickets = total_result.scalar() or 0
    logger.info(f"Support stats: total_tickets={total_tickets}")
    
    # Open tickets
    open_result = await db.execute(
        select(func.count(SupportTicket.id))
        .where(SupportTicket.status == TicketStatus.OPEN)
    )
    open_tickets = open_result.scalar() or 0
    
    # In progress tickets
    in_progress_result = await db.execute(
        select(func.count(SupportTicket.id))
        .where(SupportTicket.status == TicketStatus.IN_PROGRESS)
    )
    in_progress_tickets = in_progress_result.scalar() or 0
    
    # Resolved today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_result = await db.execute(
        select(func.count(SupportTicket.id))
        .where(and_(
            SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            SupportTicket.resolved_at >= today_start
        ))
    )
    resolved_today = resolved_result.scalar() or 0
    
    # Unread messages
    unread_result = await db.execute(
        select(func.sum(SupportTicket.unread_count))
    )
    unread_messages = unread_result.scalar() or 0
    
    return SupportStatsOut(
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        resolved_today=resolved_today,
        avg_response_time_minutes=None,  # TODO: Calculate
        unread_messages=unread_messages
    )


@router.get("/tickets", response_model=TicketListResponse)
async def list_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    assigned_to_me: bool = False,
    unassigned: bool = False,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """List support tickets with filtering"""
    query = select(SupportTicket).options(
        selectinload(SupportTicket.messages)
    )
    
    # Apply filters
    filters = []
    
    if status:
        filters.append(SupportTicket.status == status)
    
    if priority:
        filters.append(SupportTicket.priority == priority)
    
    if assigned_to_me:
        filters.append(SupportTicket.assigned_admin_id == current_admin.id)
    
    if unassigned:
        filters.append(SupportTicket.assigned_admin_id.is_(None))
    
    if search:
        search_filter = or_(
            SupportTicket.telegram_username.ilike(f"%{search}%"),
            SupportTicket.telegram_first_name.ilike(f"%{search}%"),
            SupportTicket.subject.ilike(f"%{search}%")
        )
        filters.append(search_filter)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Count total
    count_query = select(func.count(SupportTicket.id))
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Order by last message
    query = query.order_by(SupportTicket.last_message_at.desc())
    
    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    # Format response
    ticket_list = []
    for ticket in tickets:
        last_message = None
        if ticket.messages:
            msg = ticket.messages[-1]
            attachments = None
            if msg.attachments:
                try:
                    attachments = json.loads(msg.attachments)
                except:
                    pass
            last_message = MessageOut(
                id=msg.id,
                ticket_id=msg.ticket_id,
                sender_type=msg.sender_type.value,
                sender_admin_id=msg.sender_admin_id,
                text=msg.text,
                attachments=attachments,
                is_read=msg.is_read,
                delivered_at=msg.delivered_at,
                created_at=msg.created_at
            )
        
        ticket_list.append(TicketOut(
            id=ticket.id,
            user_id=ticket.user_id,
            telegram_user_id=ticket.telegram_user_id,
            telegram_username=ticket.telegram_username,
            telegram_first_name=ticket.telegram_first_name,
            telegram_last_name=ticket.telegram_last_name,
            subject=ticket.subject,
            status=ticket.status.value,
            priority=ticket.priority.value,
            assigned_admin_id=ticket.assigned_admin_id,
            assigned_admin_name=None,  # TODO: join AdminUser if needed
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            last_message_at=ticket.last_message_at,
            resolved_at=ticket.resolved_at,
            message_count=ticket.message_count,
            unread_count=ticket.unread_count,
            last_message=last_message
        ))
    
    return TicketListResponse(
        tickets=ticket_list,
        total=total,
        page=page,
        per_page=per_page
    )


# Log for debugging
import logging
logger = logging.getLogger(__name__)


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def get_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Get ticket details with messages"""
    query = select(SupportTicket).options(
        selectinload(SupportTicket.messages).selectinload(SupportMessage.sender_admin)
    ).where(SupportTicket.id == ticket_id)
    
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Mark messages as read
    for msg in ticket.messages:
        if msg.sender_type == MessageSender.USER and not msg.is_read:
            msg.is_read = True
    ticket.unread_count = 0
    await db.commit()
    
    # Format messages
    messages = []
    for msg in ticket.messages:
        attachments = None
        if msg.attachments:
            try:
                attachments = json.loads(msg.attachments)
            except:
                pass
        messages.append(MessageOut(
            id=msg.id,
            ticket_id=msg.ticket_id,
            sender_type=msg.sender_type.value,
            sender_admin_id=msg.sender_admin_id,
            sender_admin_name=msg.sender_admin.username if msg.sender_admin else None,
            text=msg.text,
            attachments=attachments,
            is_read=msg.is_read,
            delivered_at=msg.delivered_at,
            created_at=msg.created_at
        ))
    
    return TicketDetailOut(
        id=ticket.id,
        user_id=ticket.user_id,
        telegram_user_id=ticket.telegram_user_id,
        telegram_username=ticket.telegram_username,
        telegram_first_name=ticket.telegram_first_name,
        telegram_last_name=ticket.telegram_last_name,
        subject=ticket.subject,
        status=ticket.status.value,
        priority=ticket.priority.value,
        assigned_admin_id=ticket.assigned_admin_id,
        assigned_admin_name=None,  # TODO: join AdminUser if needed
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        last_message_at=ticket.last_message_at,
        resolved_at=ticket.resolved_at,
        message_count=ticket.message_count,
        unread_count=0,
        messages=messages
    )


@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: UUID,
    request: UpdateTicketRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Update ticket status, priority, or assignment"""
    query = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if request.status is not None:
        ticket.status = request.status
        if request.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            ticket.resolved_at = datetime.utcnow()
    
    if request.priority is not None:
        ticket.priority = request.priority
    
    if request.assigned_admin_id is not None:
        ticket.assigned_admin_id = request.assigned_admin_id
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
    
    ticket.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ticket)
    
    return TicketOut(
        id=ticket.id,
        user_id=ticket.user_id,
        telegram_user_id=ticket.telegram_user_id,
        telegram_username=ticket.telegram_username,
        telegram_first_name=ticket.telegram_first_name,
        telegram_last_name=ticket.telegram_last_name,
        subject=ticket.subject,
        status=ticket.status.value,
        priority=ticket.priority.value,
        assigned_admin_id=ticket.assigned_admin_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        last_message_at=ticket.last_message_at,
        resolved_at=ticket.resolved_at,
        message_count=ticket.message_count,
        unread_count=ticket.unread_count
    )


@router.post("/tickets/{ticket_id}/messages", response_model=MessageOut)
async def send_message(
    ticket_id: UUID,
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Send a reply to user via bot"""
    # Get ticket
    query = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Create message
    attachments_json = json.dumps(request.attachments) if request.attachments else None
    
    message = SupportMessage(
        ticket_id=ticket_id,
        sender_type=MessageSender.ADMIN,
        sender_admin_id=current_admin.id,
        text=request.text,
        attachments=attachments_json
    )
    db.add(message)
    
    # Update ticket
    ticket.message_count += 1
    ticket.last_message_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()
    ticket.status = TicketStatus.WAITING_USER
    
    # Auto-assign if not assigned
    if not ticket.assigned_admin_id:
        ticket.assigned_admin_id = current_admin.id
    
    await db.commit()
    await db.refresh(message)
    
    # Publish message to Redis for bot to send
    message_data = {
        "type": "support_reply",
        "ticket_id": str(ticket_id),
        "message_id": str(message.id),
        "telegram_user_id": ticket.telegram_user_id,
        "text": request.text,
        "attachments": request.attachments,
        "admin_name": current_admin.username
    }
    
    try:
        await redis_client.publish("support_messages", json.dumps(message_data))
    except Exception as e:
        print(f"Failed to publish message to Redis: {e}")
    
    attachments = None
    if message.attachments:
        try:
            attachments = json.loads(message.attachments)
        except:
            pass
    
    return MessageOut(
        id=message.id,
        ticket_id=message.ticket_id,
        sender_type=message.sender_type.value,
        sender_admin_id=message.sender_admin_id,
        sender_admin_name=current_admin.username,
        text=message.text,
        attachments=attachments,
        is_read=True,
        delivered_at=None,
        created_at=message.created_at
    )


@router.post("/tickets/{ticket_id}/assign-me")
async def assign_to_me(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Assign ticket to current admin"""
    query = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.assigned_admin_id = current_admin.id
    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True, "message": "Ticket assigned"}


@router.get("/settings", response_model=SupportSettingsOut)
async def get_support_settings(
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Get support settings"""
    result = await db.execute(select(SupportSettings).limit(1))
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Create default settings
        settings = SupportSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return SupportSettingsOut(
        auto_reply_enabled=settings.auto_reply_enabled,
        auto_reply_message=settings.auto_reply_message,
        working_hours_enabled=settings.working_hours_enabled,
        working_hours_start=settings.working_hours_start,
        working_hours_end=settings.working_hours_end,
        working_hours_timezone=settings.working_hours_timezone,
        outside_hours_message=settings.outside_hours_message,
        notify_new_ticket=settings.notify_new_ticket,
        notify_new_message=settings.notify_new_message
    )


@router.patch("/settings", response_model=SupportSettingsOut)
async def update_support_settings(
    request: UpdateSupportSettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Update support settings"""
    result = await db.execute(select(SupportSettings).limit(1))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = SupportSettings()
        db.add(settings)
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    settings.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(settings)
    
    return SupportSettingsOut(
        auto_reply_enabled=settings.auto_reply_enabled,
        auto_reply_message=settings.auto_reply_message,
        working_hours_enabled=settings.working_hours_enabled,
        working_hours_start=settings.working_hours_start,
        working_hours_end=settings.working_hours_end,
        working_hours_timezone=settings.working_hours_timezone,
        outside_hours_message=settings.outside_hours_message,
        notify_new_ticket=settings.notify_new_ticket,
        notify_new_message=settings.notify_new_message
    )


# ============= Bot Endpoints =============

class BotMessageRequest(BaseModel):
    telegram_user_id: int
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    telegram_last_name: Optional[str] = None
    text: str
    telegram_message_id: int = 0
    attachments: Optional[List[dict]] = None


@router.post("/bot/message")
async def bot_create_message(
    request: BotMessageRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token)
):
    """Bot endpoint: Create or update ticket with new message from user"""
    # Find existing open ticket or create new one
    query = select(SupportTicket).where(
        and_(
            SupportTicket.telegram_user_id == request.telegram_user_id,
            SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_USER])
        )
    ).order_by(SupportTicket.created_at.desc())
    
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        # Create new ticket
        ticket = SupportTicket(
            telegram_user_id=request.telegram_user_id,
            telegram_username=request.telegram_username,
            telegram_first_name=request.telegram_first_name,
            telegram_last_name=request.telegram_last_name,
            subject=request.text[:100] if len(request.text) > 100 else request.text,
            status=TicketStatus.OPEN,
            priority=TicketPriority.NORMAL,
        )
        db.add(ticket)
        await db.flush()
    
    # Create message
    attachments_json = json.dumps(request.attachments) if request.attachments else None
    
    message = SupportMessage(
        ticket_id=ticket.id,
        sender_type=MessageSender.USER,
        text=request.text,
        telegram_message_id=request.telegram_message_id,
        attachments=attachments_json,
    )
    db.add(message)
    
    # Update ticket stats
    ticket.message_count += 1
    ticket.unread_count += 1
    ticket.last_message_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()
    
    # If waiting for user response, change to in_progress
    if ticket.status == TicketStatus.WAITING_USER:
        ticket.status = TicketStatus.IN_PROGRESS
    
    await db.commit()
    await db.refresh(ticket)
    
    # Notify admins via Redis
    try:
        notification = {
            "type": "new_support_message",
            "ticket_id": str(ticket.id),
            "telegram_user_id": request.telegram_user_id,
            "telegram_username": request.telegram_username,
            "text": request.text[:200],
        }
        await redis_client.publish("admin_notifications", json.dumps(notification))
    except Exception as e:
        print(f"Failed to publish notification: {e}")
    
    return {
        "success": True,
        "ticket_id": str(ticket.id),
        "is_new_ticket": ticket.message_count == 1
    }


@router.get("/bot/settings")
async def bot_get_settings(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token)
):
    """Bot endpoint: Get support settings"""
    result = await db.execute(select(SupportSettings).limit(1))
    settings = result.scalar_one_or_none()
    
    if not settings:
        return {
            "auto_reply_enabled": True,
            "auto_reply_message": "Спасибо за обращение! Наш специалист ответит вам в ближайшее время.",
            "working_hours_enabled": False,
        }
    
    return {
        "auto_reply_enabled": settings.auto_reply_enabled,
        "auto_reply_message": settings.auto_reply_message,
        "working_hours_enabled": settings.working_hours_enabled,
        "working_hours_start": settings.working_hours_start,
        "working_hours_end": settings.working_hours_end,
        "working_hours_timezone": settings.working_hours_timezone,
        "outside_hours_message": settings.outside_hours_message,
    }


# ============= Additional Bot Endpoints =============

class BotTicketRequest(BaseModel):
    telegram_user_id: int
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    telegram_last_name: Optional[str] = None


class BotSimpleMessageRequest(BaseModel):
    telegram_user_id: int
    text: str
    telegram_message_id: int


class BotCloseRequest(BaseModel):
    telegram_user_id: int


@router.post("/bot/ticket")
async def bot_get_or_create_ticket(
    request: BotTicketRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token)
):
    """Bot endpoint: Get or create ticket for user"""
    # Find existing open ticket
    query = select(SupportTicket).where(
        and_(
            SupportTicket.telegram_user_id == request.telegram_user_id,
            SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_USER])
        )
    ).order_by(SupportTicket.created_at.desc())
    
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        # Create new ticket
        ticket = SupportTicket(
            telegram_user_id=request.telegram_user_id,
            telegram_username=request.telegram_username,
            telegram_first_name=request.telegram_first_name,
            telegram_last_name=request.telegram_last_name,
            status=TicketStatus.OPEN,
            priority=TicketPriority.NORMAL,
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
    
    return {
        "ticket_id": str(ticket.id),
        "status": ticket.status.value,
        "created_at": ticket.created_at.isoformat(),
        "message_count": ticket.message_count,
    }


@router.get("/bot/messages")
async def bot_get_messages(
    telegram_user_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token)
):
    """Bot endpoint: Get messages from user's active ticket"""
    # Find active ticket
    ticket_query = select(SupportTicket).where(
        and_(
            SupportTicket.telegram_user_id == telegram_user_id,
            SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_USER])
        )
    ).order_by(SupportTicket.created_at.desc())
    
    result = await db.execute(ticket_query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        return []
    
    # Get messages
    messages_query = (
        select(SupportMessage)
        .where(SupportMessage.ticket_id == ticket.id)
        .order_by(SupportMessage.created_at.desc())
        .limit(limit)
    )
    
    messages_result = await db.execute(messages_query)
    messages = messages_result.scalars().all()
    
    return [
        {
            "id": str(msg.id),
            "sender_type": msg.sender_type.value,
            "text": msg.text,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]


@router.post("/bot/close")
async def bot_close_ticket(
    request: BotCloseRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token)
):
    """Bot endpoint: Close user's active ticket"""
    # Find active ticket
    query = select(SupportTicket).where(
        and_(
            SupportTicket.telegram_user_id == request.telegram_user_id,
            SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_USER])
        )
    ).order_by(SupportTicket.created_at.desc())
    
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        return {"success": False, "error": "No active ticket found"}
    
    ticket.status = TicketStatus.CLOSED
    ticket.resolved_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True, "ticket_id": str(ticket.id)}
