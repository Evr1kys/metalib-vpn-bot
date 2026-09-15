"""
Device models for device binding and tracking
"""
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime, BigInteger, Integer
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class Device(Base, UUIDMixin, TimestampMixin):
    """User device"""
    
    __tablename__ = "devices"
    
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    vpn_account_id = Column(UUID(as_uuid=True), ForeignKey("vpn_accounts.id"), nullable=True, index=True)
    
    # Device binding
    device_token = Column(String(100), unique=True, nullable=False, index=True)  # One-time binding token
    device_fingerprint = Column(String(500), nullable=True)  # Device identifier (best-effort)
    
    # Device info
    device_name = Column(String(255), nullable=True)  # User-provided name
    device_type = Column(String(100), nullable=True)  # iOS, Android, Windows, macOS, Linux
    device_model = Column(String(255), nullable=True)  # iPhone 14, Samsung Galaxy S23, etc.
    os_version = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_token_used = Column(Boolean, default=False, nullable=False)  # Token can only be used once
    token_expires_at = Column(DateTime, nullable=True)
    
    # Usage
    last_used_at = Column(DateTime, nullable=True)
    last_ip = Column(INET, nullable=True)
    connection_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="devices")
    user = relationship("User", back_populates="devices")
    vpn_account = relationship("VPNAccount", back_populates="devices")
    sessions = relationship("DeviceSession", back_populates="device", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Device(id={self.id}, name={self.device_name}, type={self.device_type})>"
    
    def is_token_valid(self) -> bool:
        """Check if binding token is still valid"""
        if self.is_token_used:
            return False
        
        if self.token_expires_at and self.token_expires_at < datetime.utcnow():
            return False
        
        return True


class DeviceSession(Base, UUIDMixin, TimestampMixin):
    """Device connection session (for tracking)"""
    
    __tablename__ = "device_sessions"
    
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    vpn_account_id = Column(UUID(as_uuid=True), ForeignKey("vpn_accounts.id"), nullable=False, index=True)
    
    # Session time
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True, index=True)
    
    # Connection details
    ip_address = Column(INET, nullable=True)
    location = Column(String(255), nullable=True)  # Geo location (country/city)
    
    # Traffic
    bytes_sent = Column(BigInteger, default=0, nullable=False)
    bytes_received = Column(BigInteger, default=0, nullable=False)
    
    # Relationships
    device = relationship("Device", back_populates="sessions")
    vpn_account = relationship("VPNAccount", back_populates="sessions")
    
    def __repr__(self):
        return f"<DeviceSession(id={self.id}, device_id={self.device_id}, started_at={self.started_at})>"
    
    def duration_seconds(self) -> int:
        """Get session duration in seconds"""
        if not self.ended_at:
            return int((datetime.utcnow() - self.started_at).total_seconds())
        
        return int((self.ended_at - self.started_at).total_seconds())
    
    def total_bytes(self) -> int:
        """Get total bytes transferred"""
        return self.bytes_sent + self.bytes_received
