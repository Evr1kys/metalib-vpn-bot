"""
Server Location model - локации серверов с расширенной информацией
"""
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class ServerType(str, Enum):
    STANDARD = "standard"       # Обычный сервер
    GAMING = "gaming"           # Оптимизирован для игр (низкий пинг)
    STREAMING = "streaming"     # Оптимизирован для стриминга (высокая скорость)
    PRIVACY = "privacy"         # Двойной VPN, максимальная приватность
    P2P = "p2p"                 # Разрешён торрент


class ServerLocation(Base, UUIDMixin, TimestampMixin):
    """Локация/страна для серверов"""
    __tablename__ = "server_locations"
    
    # Основная информация
    country_code = Column(String(2), nullable=False, unique=True)  # NL, DE, FI, LV, KZ
    country_name = Column(String(100), nullable=False)  # Netherlands, Germany, etc.
    country_name_ru = Column(String(100), nullable=False)  # Нидерланды, Германия
    city = Column(String(100), nullable=True)  # Amsterdam, Frankfurt
    city_ru = Column(String(100), nullable=True)  # Амстердам, Франкфурт
    
    # Флаг страны (emoji или URL)
    flag_emoji = Column(String(10), nullable=True)  # 🇳🇱, 🇩🇪
    flag_url = Column(String(255), nullable=True)
    
    # Координаты для карты
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Рекомендуемость
    is_recommended = Column(Boolean, default=False)  # Показывать как рекомендованный
    is_premium = Column(Boolean, default=False)  # Только для премиум тарифов
    
    # Порядок отображения
    sort_order = Column(Integer, default=0)
    
    # Активность
    is_active = Column(Boolean, default=True)
    
    # Связь с серверами
    servers = relationship("Server", back_populates="location")


class ServerTypeConfig(Base, UUIDMixin, TimestampMixin):
    """Конфигурация типов серверов"""
    __tablename__ = "server_type_configs"
    
    # Тип сервера
    server_type = Column(String(50), nullable=False, unique=True)
    
    # Отображение
    name = Column(String(100), nullable=False)
    name_ru = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    description_ru = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # emoji или icon name
    
    # Настройки XRay для этого типа
    xray_settings = Column(JSON, nullable=True)  # Специфичные настройки
    
    # Приоритет при Smart Connect
    priority_for_gaming = Column(Integer, default=0)  # Чем выше, тем лучше для игр
    priority_for_streaming = Column(Integer, default=0)
    priority_for_privacy = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
