"""
Trial model - пробный период
"""
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class TrialStatus(str, Enum):
    ACTIVE = "active"           # Триал активен
    EXPIRED = "expired"         # Триал истёк
    CONVERTED = "converted"     # Пользователь купил подписку
    CANCELLED = "cancelled"     # Отменён


class Trial(Base, UUIDMixin, TimestampMixin):
    """Пробный период 24 часа"""
    __tablename__ = "trials"
    
    # Пользователь
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", backref="trial")
    
    # Статус (string в БД, не enum)
    status = Column(String(20), default="active", nullable=False)
    
    # Длительность
    duration_hours = Column(Integer, nullable=True)
    
    # Временные рамки
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Откуда пришёл пользователь
    source = Column(String(50), nullable=True)  # website, bot, referral
    
    # IP при регистрации (для защиты от абуза)
    ip_address = Column(String(45), nullable=True, index=True)
    device_fingerprint = Column(String(255), nullable=True)
    
    # Привязка к подписке при конверсии
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True)
    
    # Конверсия
    converted_at = Column(DateTime, nullable=True)
    
    @property
    def is_active(self) -> bool:
        return self.status == "active" and self.expires_at > datetime.utcnow()
    
    @property
    def hours_left(self) -> int:
        if self.expires_at <= datetime.utcnow():
            return 0
        delta = self.expires_at - datetime.utcnow()
        return int(delta.total_seconds() / 3600)


class TrialSettings(Base, UUIDMixin, TimestampMixin):
    """Настройки пробного периода"""
    __tablename__ = "trial_settings"
    
    # Включён ли триал
    is_enabled = Column(Boolean, default=True)
    
    # Длительность в часах
    duration_hours = Column(Integer, default=24)
    
    # Ограничения (колонки как в БД)
    max_devices = Column(Integer, nullable=True)
    max_per_ip = Column(Integer, default=1)  # Максимум триалов с одного IP
    max_per_fingerprint = Column(Integer, nullable=True)
    require_telegram = Column(Boolean, default=True)  # Требовать Telegram аккаунт
    
    # Свойство для совместимости с кодом
    @property
    def max_trials_per_ip(self):
        return self.max_per_ip or 1
