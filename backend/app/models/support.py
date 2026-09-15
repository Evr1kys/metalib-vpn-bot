"""
Support ticket models for Telegram support system
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum, BigInteger, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.admin import AdminUser


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageSender(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class SupportTicket(Base):
    """Support ticket from Telegram user"""
    __tablename__ = "support_tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User info (no ForeignKey to avoid table resolution issues)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    telegram_username = Column(String(255), nullable=True)
    telegram_first_name = Column(String(255), nullable=True)
    telegram_last_name = Column(String(255), nullable=True)
    
    # Ticket info
    subject = Column(String(500), nullable=True)  # Auto-generated from first message
    status = Column(
        SQLEnum(TicketStatus, name='ticketstatus', create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=TicketStatus.OPEN, 
        nullable=False
    )
    priority = Column(
        SQLEnum(TicketPriority, name='ticketpriority', create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=TicketPriority.NORMAL, 
        nullable=False
    )
    
    # Assignment
    assigned_admin_id = Column(UUID(as_uuid=True), nullable=True)  # References admin_users.id
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_message_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Stats
    message_count = Column(Integer, default=0, nullable=False)
    unread_count = Column(Integer, default=0, nullable=False)  # Unread by admin
    
    # Relations
    messages = relationship("SupportMessage", back_populates="ticket", order_by="SupportMessage.created_at")
    # Note: assigned_admin relationship handled via join in queries to avoid circular imports
    # Note: User and AdminUser relationships removed to avoid circular import issues
    # Use telegram_user_id and assigned_admin_id directly for queries
    
    def __repr__(self):
        return f"<SupportTicket {self.id} - {self.telegram_username or self.telegram_user_id}>"


class SupportMessage(Base):
    """Individual message in support ticket"""
    __tablename__ = "support_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("support_tickets.id"), nullable=False)
    
    # Sender info
    sender_type = Column(
        SQLEnum(MessageSender, name='messagesender', create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    sender_admin_id = Column(UUID(as_uuid=True), nullable=True)  # Admin who sent the message
    
    # Message content
    text = Column(Text, nullable=True)
    
    # Telegram message info (for user messages)
    telegram_message_id = Column(BigInteger, nullable=True)
    
    # Attachments (JSON array of file info)
    # Format: [{"type": "photo", "file_id": "...", "file_name": "..."}, ...]
    attachments = Column(Text, nullable=True)  # JSON string
    
    # Status
    is_read = Column(Boolean, default=False, nullable=False)
    delivered_at = Column(DateTime, nullable=True)  # When bot sent reply to user
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relations
    ticket = relationship("SupportTicket", back_populates="messages")
    # Note: AdminUser relationship removed to avoid circular import issues
    # Use sender_admin_id directly for queries
    
    def __repr__(self):
        return f"<SupportMessage {self.id} - {self.sender_type}>"


class SupportSettings(Base):
    """Global support settings"""
    __tablename__ = "support_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Auto-reply settings
    auto_reply_enabled = Column(Boolean, default=True)
    auto_reply_message = Column(Text, default="Спасибо за обращение! Наш специалист ответит вам в ближайшее время.")
    
    # Working hours
    working_hours_enabled = Column(Boolean, default=False)
    working_hours_start = Column(String(5), default="09:00")  # HH:MM
    working_hours_end = Column(String(5), default="18:00")
    working_hours_timezone = Column(String(50), default="Europe/Moscow")
    outside_hours_message = Column(Text, default="Сейчас нерабочее время. Мы ответим вам в рабочие часы.")
    
    # Notification settings
    notify_new_ticket = Column(Boolean, default=True)
    notify_new_message = Column(Boolean, default=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
