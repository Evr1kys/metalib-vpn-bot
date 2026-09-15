"""
Gift Certificate model - подарочные сертификаты
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class GiftCertificateStatus(str, Enum):
    PENDING = "pending"         # Ожидает оплаты
    ACTIVE = "active"           # Оплачен, можно использовать
    REDEEMED = "redeemed"       # Активирован получателем
    EXPIRED = "expired"         # Истёк срок действия
    CANCELLED = "cancelled"     # Отменён


class GiftCertificate(Base, UUIDMixin, TimestampMixin):
    """Подарочный сертификат VPN"""
    __tablename__ = "gift_certificates"
    
    # Уникальный код для активации
    code = Column(String(20), unique=True, nullable=False, index=True)
    
    # Кто купил сертификат
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    buyer = relationship("User", foreign_keys=[buyer_id], backref="purchased_gifts")
    
    # Кто активировал (получатель)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    recipient = relationship("User", foreign_keys=[recipient_id], backref="received_gifts")
    
    # Тариф, который получит пользователь
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    plan = relationship("Plan")
    
    # Сумма оплаты
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    
    # Статус
    status = Column(SQLEnum(GiftCertificateStatus), default=GiftCertificateStatus.ACTIVE)
    
    # Персонализация
    sender_name = Column(String(100), nullable=True)  # Имя дарителя
    recipient_name = Column(String(100), nullable=True)  # Имя получателя (опционально)
    message = Column(Text, nullable=True)  # Поздравительное сообщение
    
    # Даты
    expires_at = Column(DateTime, nullable=False)  # Когда истекает сертификат
    redeemed_at = Column(DateTime, nullable=True)  # Когда активирован
    
    # Платёж
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)
    
    @staticmethod
    def generate_code() -> str:
        """Генерация уникального кода сертификата"""
        import random
        import string
        # Формат: GIFT-XXXX-XXXX-XXXX
        chars = string.ascii_uppercase + string.digits
        parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
        return f"GIFT-{'-'.join(parts)}"
