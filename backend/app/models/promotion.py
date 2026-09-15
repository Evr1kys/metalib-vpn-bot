"""
Promo & Marketing models - акции, таймеры, калькуляторы
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class PromoType(str, Enum):
    DISCOUNT = "discount"           # Скидка
    FREE_DAYS = "free_days"         # Бесплатные дни
    FLASH_SALE = "flash_sale"       # Быстрая распродажа
    HOLIDAY = "holiday"             # Праздничная акция
    REFERRAL_BONUS = "referral_bonus"  # Бонус за реферала


class Promotion(Base, UUIDMixin, TimestampMixin):
    """Акция/промо-кампания"""
    __tablename__ = "promotions"
    
    # Название
    name = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    
    # Описание
    description = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    
    # Тип акции
    promo_type = Column(SQLEnum(PromoType), default=PromoType.DISCOUNT)
    
    # Размер скидки
    discount_percent = Column(Integer, nullable=True)  # Процент скидки
    discount_amount = Column(Float, nullable=True)  # Фиксированная скидка
    free_days = Column(Integer, nullable=True)  # Бесплатные дни
    
    # Применимость
    applicable_plans = Column(JSON, nullable=True)  # ID планов или null для всех
    min_purchase_amount = Column(Float, nullable=True)  # Минимальная сумма покупки
    
    # Временные рамки
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    
    # Таймер на сайте
    show_timer = Column(Boolean, default=True)
    timer_title = Column(String(255), nullable=True)
    timer_title_en = Column(String(255), nullable=True)
    
    # Баннер
    banner_url = Column(String(500), nullable=True)
    banner_text = Column(Text, nullable=True)
    banner_color = Column(String(20), nullable=True)  # Цвет фона
    
    # Где показывать
    show_on_website = Column(Boolean, default=True)
    show_in_bot = Column(Boolean, default=True)
    show_in_app = Column(Boolean, default=False)
    
    # Ограничения
    max_uses = Column(Integer, nullable=True)  # Максимум использований
    current_uses = Column(Integer, default=0)
    max_uses_per_user = Column(Integer, default=1)
    
    # Связанный промокод (опционально)
    promo_code_id = Column(UUID(as_uuid=True), ForeignKey("promo_codes.id"), nullable=True)
    
    # Активность
    is_active = Column(Boolean, default=True)
    
    @property
    def is_running(self) -> bool:
        now = datetime.utcnow()
        return self.is_active and self.starts_at <= now <= self.ends_at
    
    @property
    def time_left_seconds(self) -> int:
        if not self.is_running:
            return 0
        delta = self.ends_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


class SavingsCalculatorConfig(Base, UUIDMixin, TimestampMixin):
    """Конфигурация калькулятора экономии"""
    __tablename__ = "savings_calculator_config"
    
    # Включён ли калькулятор
    is_enabled = Column(Boolean, default=True)
    
    # Текст заголовка
    title = Column(String(255), default="Калькулятор экономии")
    title_en = Column(String(255), default="Savings Calculator")
    
    # Описание
    description = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    
    # Сравнение с конкурентами
    competitor_monthly_price = Column(Float, default=500.0)  # Средняя цена конкурентов в месяц
    competitor_name = Column(String(100), default="Другие VPN")
    
    # Показывать экономию в процентах или рублях
    show_percent = Column(Boolean, default=True)
    show_amount = Column(Boolean, default=True)
    
    # Кастомные тексты
    savings_text = Column(String(255), default="Вы экономите {amount}₽")
    savings_text_en = Column(String(255), default="You save {amount}₽")


class PromotionUse(Base, UUIDMixin, TimestampMixin):
    """Использование акции"""
    __tablename__ = "promotion_uses"
    
    promotion_id = Column(UUID(as_uuid=True), ForeignKey("promotions.id"), nullable=False)
    promotion = relationship("Promotion", backref="uses")
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User")
    
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)
    
    discount_applied = Column(Float, nullable=True)
    original_amount = Column(Float, nullable=True)
    final_amount = Column(Float, nullable=True)
