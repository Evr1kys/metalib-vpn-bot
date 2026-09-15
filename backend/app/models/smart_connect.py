"""
Smart Connect & Server Monitoring models
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class MobileOperator(str, Enum):
    """Мобильные операторы России"""
    MTS = "mts"
    MEGAFON = "megafon"
    BEELINE = "beeline"
    TELE2 = "tele2"
    YOTA = "yota"
    TINKOFF = "tinkoff"
    ROSTELECOM = "rostelecom"
    OTHER = "other"
    UNKNOWN = "unknown"


class ServerHealthStatus(str, Enum):
    HEALTHY = "healthy"         # Всё ок
    DEGRADED = "degraded"       # Работает, но есть проблемы
    DOWN = "down"               # Не работает
    MAINTENANCE = "maintenance" # На обслуживании


class SmartConnectProfile(Base, UUIDMixin, TimestampMixin):
    """Профиль Smart Connect для пользователя"""
    __tablename__ = "smart_connect_profiles"
    
    # Пользователь
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", backref="smart_connect_profile")
    
    # Определённый оператор
    detected_operator = Column(SQLEnum(MobileOperator), default=MobileOperator.UNKNOWN)
    
    # Предпочтения пользователя
    preferred_use_case = Column(String(50), nullable=True)  # gaming, streaming, privacy, general
    
    # Автоматически определённые параметры
    detected_region = Column(String(50), nullable=True)  # Moscow, SPB, etc.
    detected_isp = Column(String(100), nullable=True)  # Провайдер
    
    # Рекомендованный сервер
    recommended_server_id = Column(UUID(as_uuid=True), ForeignKey("servers.id"), nullable=True)
    recommended_server = relationship("Server")
    
    # История замеров
    last_speed_test = Column(DateTime, nullable=True)
    last_ping_ms = Column(Integer, nullable=True)
    last_download_mbps = Column(Float, nullable=True)
    last_upload_mbps = Column(Float, nullable=True)
    
    # Настройки
    auto_connect = Column(Boolean, default=True)  # Автоподключение к лучшему серверу
    notify_on_better_server = Column(Boolean, default=True)  # Уведомлять если есть сервер лучше


class OperatorServerRecommendation(Base, UUIDMixin, TimestampMixin):
    """Рекомендации серверов для операторов"""
    __tablename__ = "operator_server_recommendations"
    
    # Оператор
    operator = Column(SQLEnum(MobileOperator), nullable=False)
    
    # Регион (опционально)
    region = Column(String(50), nullable=True)  # Moscow, SPB, Kazan, etc.
    
    # Рекомендуемый сервер
    server_id = Column(UUID(as_uuid=True), ForeignKey("servers.id"), nullable=False)
    server = relationship("Server")
    
    # Приоритет (выше = лучше)
    priority = Column(Integer, default=0)
    
    # Почему рекомендуется
    reason = Column(Text, nullable=True)
    
    # Активность
    is_active = Column(Boolean, default=True)


class ServerHealthCheck(Base, UUIDMixin, TimestampMixin):
    """Результаты мониторинга серверов"""
    __tablename__ = "server_health_checks"
    
    # Сервер
    server_id = Column(UUID(as_uuid=True), ForeignKey("servers.id"), nullable=False)
    server = relationship("Server", backref="health_checks")
    
    # Статус
    status = Column(SQLEnum(ServerHealthStatus), nullable=False)
    
    # Метрики
    ping_ms = Column(Integer, nullable=True)
    packet_loss_percent = Column(Float, nullable=True)
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    
    # Сетевые метрики
    bandwidth_mbps = Column(Float, nullable=True)
    active_connections = Column(Integer, nullable=True)
    
    # XRay специфичные
    xray_running = Column(Boolean, nullable=True)
    xray_version = Column(String(20), nullable=True)
    
    # Ошибки
    error_message = Column(Text, nullable=True)
    
    # Время проверки
    checked_at = Column(DateTime, default=datetime.utcnow)


class ServerAlert(Base, UUIDMixin, TimestampMixin):
    """Алерты о проблемах с серверами"""
    __tablename__ = "server_alerts"
    
    # Сервер
    server_id = Column(UUID(as_uuid=True), ForeignKey("servers.id"), nullable=False)
    server = relationship("Server", backref="alerts")
    
    # Тип алерта
    alert_type = Column(String(50), nullable=False)  # down, high_load, high_latency, disk_full
    
    # Серьёзность
    severity = Column(String(20), nullable=False)  # info, warning, critical
    
    # Сообщение
    message = Column(Text, nullable=False)
    
    # Статус
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)
    
    # Уведомления
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime, nullable=True)


class SpeedTestResult(Base, UUIDMixin, TimestampMixin):
    """Результаты спидтестов пользователей"""
    __tablename__ = "speed_test_results"
    
    # Пользователь (опционально, может быть анонимный тест)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="speed_tests")
    
    # Сервер который тестировали
    server_id = Column(UUID(as_uuid=True), ForeignKey("servers.id"), nullable=True)
    server = relationship("Server", backref="speed_tests")
    
    # Результаты
    download_mbps = Column(Float, nullable=False)
    upload_mbps = Column(Float, nullable=False)
    ping_ms = Column(Integer, nullable=False)
    jitter_ms = Column(Float, nullable=True)
    
    # Контекст
    test_server_location = Column(String(100), nullable=True)  # Где находится тест-сервер
    client_ip = Column(String(45), nullable=True)
    client_isp = Column(String(100), nullable=True)
    
    # VPN статус
    vpn_connected = Column(Boolean, default=True)
    
    # Источник теста
    source = Column(String(50), default="website")  # website, bot, app
