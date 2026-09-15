"""
Server model for VPN infrastructure
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, DateTime, Enum as SQLEnum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, UUIDMixin, TimestampMixin


class ServerStatus(str, enum.Enum):
    """Server health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class ManagementType(str, enum.Enum):
    """Server management method"""
    AGENT = "agent"  # Via VPN agent API
    SSH = "ssh"      # Via SSH commands


class ServerType(str, enum.Enum):
    """Тип сервера по назначению"""
    STANDARD = "standard"       # Обычный сервер
    GAMING = "gaming"           # Оптимизирован для игр (низкий пинг)
    STREAMING = "streaming"     # Оптимизирован для стриминга (высокая скорость)
    PRIVACY = "privacy"         # Двойной VPN, максимальная приватность
    P2P = "p2p"                 # Разрешён торрент


class Server(Base, UUIDMixin, TimestampMixin):
    """VPN server"""
    
    __tablename__ = "servers"
    
    # Basic info
    name = Column(String(255), nullable=False)
    region = Column(String(100), nullable=False, index=True)  # e.g., EU-West, US-East, Asia-SG
    
    # Network
    hostname = Column(String(255), nullable=True)
    ip_address = Column(INET, nullable=False)
    ipv6_address = Column(INET, nullable=True)
    
    # Location
    location_id = Column(UUID(as_uuid=True), ForeignKey("server_locations.id"), nullable=True)
    location = relationship("ServerLocation", back_populates="servers")
    country_code = Column(String(2), nullable=True)  # NL, DE, FI, etc.
    city = Column(String(100), nullable=True)
    
    # Server type
    server_type = Column(
        SQLEnum(ServerType, name="server_type_enum"),
        default=ServerType.STANDARD,
        nullable=False,
        index=True
    )
    
    # Performance metrics (real-time)
    ping_ms = Column(Integer, nullable=True)  # Текущий пинг
    download_speed_mbps = Column(Float, nullable=True)  # Скорость скачивания
    upload_speed_mbps = Column(Float, nullable=True)  # Скорость загрузки
    
    # Специфичные флаги
    is_premium = Column(Boolean, default=False)  # Только для премиум тарифов
    supports_streaming = Column(Boolean, default=True)  # Работает со стримингом
    supports_gaming = Column(Boolean, default=False)  # Оптимизирован для игр
    supports_p2p = Column(Boolean, default=False)  # Разрешён P2P/торренты
    
    # Management
    management_type = Column(
        SQLEnum(ManagementType, name="management_type"),
        default=ManagementType.AGENT,
        nullable=False
    )
    
    # Agent management (encrypted)
    agent_url = Column(String(500), nullable=True)  # e.g., https://vpn1.example.com:8001
    agent_token = Column(Text, nullable=True)  # encrypted
    
    # SSH management (encrypted)
    ssh_host = Column(String(255), nullable=True)
    ssh_port = Column(Integer, default=22, nullable=True)
    ssh_user = Column(String(100), nullable=True)
    ssh_key = Column(Text, nullable=True)  # encrypted private key
    
    # Capacity
    max_users = Column(Integer, default=100, nullable=False)
    current_users = Column(Integer, default=0, nullable=False, index=True)
    max_bandwidth = Column(BigInteger, nullable=True)  # bytes per month
    current_bandwidth = Column(BigInteger, default=0, nullable=False)  # current period bandwidth
    total_bandwidth = Column(BigInteger, default=0, nullable=False)  # all-time total bandwidth
    
    # Health
    status = Column(
        SQLEnum(ServerStatus, name="server_status"),
        default=ServerStatus.HEALTHY,
        nullable=False,
        index=True
    )
    health_check_url = Column(String(500), nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    health_check_failures = Column(Integer, default=0, nullable=False)
    
    # Flags
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    drain_mode = Column(Boolean, default=False, nullable=False)  # stop new assignments
    
    # Metadata (additional config, metrics, etc.)
    server_metadata = Column(JSONB, default=dict, nullable=False)
    # Example: {"cpu_usage": 45, "memory_usage": 60, "vpn_protocols": ["wireguard", "openvpn"]}
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="server")
    vpn_accounts = relationship("VPNAccount", back_populates="server")
    server_group_members = relationship("ServerGroupMember", back_populates="server", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Server(id={self.id}, name={self.name}, region={self.region}, status={self.status})>"
    
    def can_accept_users(self) -> bool:
        """Check if server can accept new users"""
        return (
            self.is_active and
            not self.drain_mode and
            self.status == ServerStatus.HEALTHY and
            self.current_users < self.max_users
        )
    
    def available_capacity(self) -> int:
        """Get available user slots"""
        return max(0, self.max_users - self.current_users)
    
    def load_percentage(self) -> float:
        """Get current load percentage"""
        if self.max_users == 0:
            return 0.0
        return (self.current_users / self.max_users) * 100
