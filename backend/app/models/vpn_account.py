"""
VPN Account model
"""
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, BigInteger, Integer, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class VPNProtocol(str, enum.Enum):
    """VPN Protocol"""
    WIREGUARD = "WIREGUARD"
    OPENVPN = "OPENVPN"
    AMNEZIA = "AMNEZIA"
    VLESS_REALITY = "VLESS_REALITY"
    VLESS = "VLESS"  # Plain VLESS without Reality (simpler, more reliable)


class VPNAccountStatus(str, enum.Enum):
    """VPN Account status"""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class VPNAccount(Base, UUIDMixin, TimestampMixin):
    """VPN access configuration"""
    
    __tablename__ = "vpn_accounts"
    
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    server_id = Column(UUID(as_uuid=True), ForeignKey("servers.id"), nullable=False, index=True)
    
    protocol = Column(
        SQLEnum(VPNProtocol, name="vpn_protocol"),
        nullable=False,
        index=True
    )
    
    # Credentials
    username = Column(String(255), nullable=True)  # for OpenVPN
    
    # Configuration (encrypted)
    config = Column(Text, nullable=False)  # Full VPN config file (encrypted)
    
    # WireGuard specific
    public_key = Column(String(255), nullable=True)
    private_key = Column(Text, nullable=True)  # encrypted
    
    # Network
    ip_address = Column(INET, nullable=True)  # Assigned VPN tunnel IP
    
    # Status
    status = Column(
        SQLEnum(VPNAccountStatus, name="vpn_account_status"),
        default=VPNAccountStatus.ACTIVE,
        nullable=False,
        index=True
    )
    
    # Usage tracking
    bandwidth_used = Column(BigInteger, default=0, nullable=False)  # bytes
    last_connected_at = Column(DateTime, nullable=True)
    connection_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="vpn_accounts")
    server = relationship("Server", back_populates="vpn_accounts")
    devices = relationship("Device", back_populates="vpn_account")
    sessions = relationship("DeviceSession", back_populates="vpn_account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VPNAccount(id={self.id}, protocol={self.protocol}, server_id={self.server_id})>"
