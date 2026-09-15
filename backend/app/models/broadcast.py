"""
Broadcast models
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class BroadcastLog(Base, UUIDMixin, TimestampMixin):
    """Broadcast message log"""
    __tablename__ = "broadcast_logs"

    message = Column(Text, nullable=False)
    photo_url = Column(String(500), nullable=True)
    buttons = Column(JSON, nullable=True)  # List of buttons
    buttons_data = Column(JSON, nullable=True)  # Alias for buttons
    target = Column(String(50), nullable=False, default="all")  # all, active, inactive
    target_filter = Column(String(50), nullable=True)  # Legacy alias
    target_plan_id = Column(String(36), nullable=True)  # For plan-specific targeting
    force_send = Column(Boolean, default=False)  # Ignore user notification settings
    
    # Statistics
    total_count = Column(Integer, default=0)  # Total targeted users
    total_users = Column(Integer, default=0)  # Legacy alias
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Flags
    has_photo = Column(Boolean, default=False)
    has_buttons = Column(Boolean, default=False)
    
    # Message IDs for deletion (JSON: {chat_id: message_id})
    message_ids = Column(JSON, nullable=True)
    
    # Admin who sent
    admin_id = Column(String(36), nullable=False)
    admin_username = Column(String(255), nullable=True)
