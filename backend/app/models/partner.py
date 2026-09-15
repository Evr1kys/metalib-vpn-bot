"""
Partner Program models - партнёрская программа
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class PartnerStatus(str, Enum):
    PENDING = "pending"         # Заявка на рассмотрении
    APPROVED = "approved"       # Одобрен
    REJECTED = "rejected"       # Отклонён
    SUSPENDED = "suspended"     # Приостановлен


class PartnerTier(str, Enum):
    BRONZE = "bronze"           # Базовый уровень
    SILVER = "silver"           # Серебряный
    GOLD = "gold"               # Золотой
    PLATINUM = "platinum"       # Платиновый


class Partner(Base, UUIDMixin, TimestampMixin):
    """Партнёр программы"""
    __tablename__ = "partners"
    
    # Связь с пользователем
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", backref="partner_account")
    
    # Уникальный код партнёра
    referral_code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Статус и уровень
    status = Column(String(20), default="pending")  # pending, approved, rejected, suspended
    tier = Column(String(20), default="bronze")  # bronze, silver, gold, platinum
    
    # Комиссия (в процентах)
    commission_percent = Column(Integer, default=20)
    
    # Информация
    telegram_channel = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Статистика
    total_clicks = Column(Integer, default=0)
    total_sales = Column(Integer, default=0)
    total_earned = Column(Float, default=0)
    pending_payout = Column(Float, default=0)
    
    # Верификация
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)


class PartnerClick(Base, UUIDMixin, TimestampMixin):
    """Клики по партнёрским ссылкам"""
    __tablename__ = "partner_clicks"
    
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    partner = relationship("Partner", backref="clicks")
    
    # IP клиента
    ip_address = Column(String(45), nullable=True)
    
    # User agent
    user_agent = Column(String(500), nullable=True)
    
    # Откуда пришёл
    referrer = Column(String(500), nullable=True)
    
    # UTM метки
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    
    # Конверсия
    converted = Column(Boolean, default=False)
    converted_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class PartnerSale(Base, UUIDMixin, TimestampMixin):
    """Продажи через партнёров"""
    __tablename__ = "partner_sales"
    
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    partner = relationship("Partner", backref="sales")
    
    # Покупатель
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User")
    
    # Платёж
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    
    # Суммы
    sale_amount = Column(Float, nullable=False)
    commission_rate = Column(Float, nullable=False)
    commission_amount = Column(Float, nullable=False)
    
    # Статус выплаты
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)
    payout_id = Column(UUID(as_uuid=True), ForeignKey("partner_payouts.id"), nullable=True)


class PartnerPayout(Base, UUIDMixin, TimestampMixin):
    """Выплаты партнёрам"""
    __tablename__ = "partner_payouts"
    
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    partner = relationship("Partner", backref="payouts")
    
    # Сумма
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    
    # Метод выплаты
    payout_method = Column(String(50), nullable=False)
    payout_details = Column(JSON, nullable=True)
    
    # Статус
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    
    # Даты
    processed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Комментарий
    notes = Column(Text, nullable=True)
    
    # Кто обработал
    processed_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)


class PartnerSettings(Base, UUIDMixin, TimestampMixin):
    """Настройки партнёрской программы"""
    __tablename__ = "partner_settings"
    
    # Программа включена
    is_enabled = Column(Boolean, default=True)
    
    # Комиссии по умолчанию
    default_commission_rate = Column(Float, default=20.0)
    
    # Комиссии по уровням
    bronze_commission = Column(Float, default=20.0)
    silver_commission = Column(Float, default=25.0)
    gold_commission = Column(Float, default=30.0)
    platinum_commission = Column(Float, default=35.0)
    
    # Требования для уровней (по количеству продаж)
    silver_threshold = Column(Integer, default=10)
    gold_threshold = Column(Integer, default=50)
    platinum_threshold = Column(Integer, default=200)
    
    # Минимальная сумма для вывода
    min_payout_amount = Column(Float, default=1000.0)
    
    # Cookie lifetime (дней)
    cookie_lifetime_days = Column(Integer, default=30)
    
    # Описание программы
    description = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)
