"""
Server Group models for load balancing
"""
from sqlalchemy import Column, String, ForeignKey, Integer, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class LoadBalancingStrategy(str, enum.Enum):
    """Load balancing strategy"""
    LEAST_LOADED = "least_loaded"  # Choose server with lowest load
    ROUND_ROBIN = "round_robin"    # Rotate between servers
    GEO_CLOSEST = "geo_closest"    # Choose geographically closest


class ServerGroup(Base, UUIDMixin, TimestampMixin):
    """Group of servers for load balancing"""
    
    __tablename__ = "server_groups"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    regions = Column(ARRAY(String), default=[], nullable=False)  # e.g., ["EU-West", "EU-East"]
    
    load_balancing_strategy = Column(
        SQLEnum(LoadBalancingStrategy, name="load_balancing_strategy"),
        default=LoadBalancingStrategy.LEAST_LOADED,
        nullable=False
    )
    
    # Relationships
    members = relationship("ServerGroupMember", back_populates="group", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ServerGroup(id={self.id}, name={self.name})>"


class ServerGroupMember(Base, UUIDMixin, TimestampMixin):
    """Server membership in a group"""
    
    __tablename__ = "server_group_members"
    
    group_id = Column(UUID(as_uuid=True), ForeignKey("server_groups.id"), nullable=False, index=True)
    server_id = Column(UUID(as_uuid=True), ForeignKey("servers.id"), nullable=False, index=True)
    priority = Column(Integer, default=100, nullable=False)  # higher = higher priority
    
    # Relationships
    group = relationship("ServerGroup", back_populates="members")
    server = relationship("Server", back_populates="server_group_members")
    
    def __repr__(self):
        return f"<ServerGroupMember(group_id={self.group_id}, server_id={self.server_id})>"
