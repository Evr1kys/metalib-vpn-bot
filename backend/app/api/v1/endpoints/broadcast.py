from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models import User, BroadcastLog, AdminUser
import asyncio
import base64

router = APIRouter()


class BroadcastButton(BaseModel):
    """Broadcast button model"""
    text: str
    url: str


class BroadcastRequest(BaseModel):
    """Broadcast request with rich features"""
    message: str
    target: str = "all"  # all, active, inactive
    user_ids: Optional[List[int]] = None
    photo_url: Optional[str] = None
    photo_base64: Optional[str] = None
    buttons: Optional[List[BroadcastButton]] = None
    preview: bool = False


class BroadcastLogResponse(BaseModel):
    """Broadcast log response"""
    id: str
    admin_id: str
    admin_username: str
    message: str
    target: str
    sent_count: int
    failed_count: int
    total_count: int
    has_photo: bool
    has_buttons: bool
    created_at: str

@router.post("")
async def send_broadcast(
    request: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Send broadcast message to users with photos and buttons"""
    
    try:
        # Build query based on target
        query = select(User)
        
        if request.user_ids:
            query = query.where(User.telegram_id.in_(request.user_ids))
        elif request.target == "active":
            query = query.where(User.is_active == True)
        elif request.target == "inactive":
            query = query.where(User.is_active == False)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        if not users:
            return {
                "success": True,
                "sent": 0,
                "failed": 0,
                "total": 0,
                "message": "No users found matching criteria"
            }
        
        # Preview mode - only show count and sample
        if request.preview:
            return {
                "preview": True,
                "target_users": len(users),
                "message": request.message,
                "has_photo": bool(request.photo_url or request.photo_base64),
                "has_buttons": bool(request.buttons),
                "buttons": request.buttons
            }
        
        # Import bot
        from app.core.config import settings
        from aiogram import Bot
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        bot = Bot(token=settings.telegram_bot_token)
        
        # Prepare buttons if any
        keyboard = None
        if request.buttons:
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            for btn in request.buttons:
                builder.row(InlineKeyboardButton(text=btn.text, url=btn.url))
            keyboard = builder.as_markup()
        
        sent = 0
        failed = 0
        failed_users = []
        message_ids = {}  # Store message IDs for potential deletion
        
        # Send messages
        for user in users:
            try:
                if request.photo_url or request.photo_base64:
                    # Send with photo
                    photo_source = request.photo_url if request.photo_url else request.photo_base64
                    msg = await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=photo_source,
                        caption=request.message,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    # Text only
                    msg = await bot.send_message(
                        chat_id=user.telegram_id,
                        text=request.message,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                message_ids[str(user.telegram_id)] = msg.message_id
                sent += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except Exception as e:
                failed += 1
                failed_users.append({"user_id": user.telegram_id, "error": str(e)})
        
        await bot.session.close()
        
        # Create broadcast log
        broadcast_log = BroadcastLog(
            admin_id=str(admin.id),
            message=request.message,
            target=request.target,
            sent_count=sent,
            failed_count=failed,
            total_count=len(users),
            has_photo=bool(request.photo_url or request.photo_base64),
            has_buttons=bool(request.buttons),
            buttons_data=[{"text": b.text, "url": b.url} for b in request.buttons] if request.buttons else None,
            message_ids=message_ids
        )
        
        db.add(broadcast_log)
        await db.commit()
        
        return {
            "success": True,
            "sent": sent,
            "failed": failed,
            "total": len(users),
            "failed_users": failed_users[:10],  # Return first 10 failed
            "broadcast_id": str(broadcast_log.id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", response_model=List[BroadcastLogResponse])
async def get_broadcast_logs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get broadcast history logs"""
    
    stmt = select(BroadcastLog).order_by(desc(BroadcastLog.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    response = []
    for log in logs:
        admin_user = await db.get(AdminUser, log.admin_id)
        response.append(BroadcastLogResponse(
            id=str(log.id),
            admin_id=str(log.admin_id),
            admin_username=admin_user.username if admin_user else "Unknown",
            message=log.message[:100] + "..." if len(log.message) > 100 else log.message,
            target=log.target,
            sent_count=log.sent_count,
            failed_count=log.failed_count,
            total_count=log.total_count,
            has_photo=log.has_photo,
            has_buttons=log.has_buttons,
            created_at=log.created_at.isoformat()
        ))
    
    return response


@router.get("/logs/{broadcast_id}")
async def get_broadcast_log_detail(
    broadcast_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get detailed broadcast log"""
    
    log = await db.get(BroadcastLog, broadcast_id)
    
    if not log:
        raise HTTPException(status_code=404, detail="Broadcast log not found")
    
    admin_user = await db.get(AdminUser, log.admin_id)
    
    return {
        "id": str(log.id),
        "admin_id": str(log.admin_id),
        "admin_username": admin_user.username if admin_user else "Unknown",
        "message": log.message,
        "target": log.target,
        "sent_count": log.sent_count,
        "failed_count": log.failed_count,
        "total_count": log.total_count,
        "has_photo": log.has_photo,
        "has_buttons": log.has_buttons,
        "buttons": log.buttons_data,
        "created_at": log.created_at.isoformat(),
        "can_delete": bool(log.message_ids)
    }


@router.delete("/logs/{broadcast_id}")
async def delete_broadcast(
    broadcast_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Delete broadcast and remove messages from all users' chats"""
    
    log = await db.get(BroadcastLog, broadcast_id)
    
    if not log:
        raise HTTPException(status_code=404, detail="Broadcast log not found")
    
    deleted_count = 0
    failed_count = 0
    
    # Delete messages from users' chats if message_ids exist
    if log.message_ids:
        from app.core.config import settings
        from aiogram import Bot
        
        bot = Bot(token=settings.telegram_bot_token)
        
        for chat_id_str, message_id in log.message_ids.items():
            try:
                chat_id = int(chat_id_str)
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
                deleted_count += 1
                await asyncio.sleep(0.03)  # Rate limiting
            except Exception as e:
                failed_count += 1
        
        await bot.session.close()
    
    # Delete broadcast log from database
    await db.delete(log)
    await db.commit()
    
    return {
        "success": True,
        "deleted_messages": deleted_count,
        "failed_deletions": failed_count,
        "message": f"Рассылка удалена. Удалено {deleted_count} сообщений."
    }
