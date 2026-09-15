"""
MetaLib VPN Bot - Backend Configuration
"""
from typing import List, Optional, Union, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # General
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    secret_key: str = Field(...)
    encryption_key: str = Field(...)
    
    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_base_url: str = Field(...)
    api_cors_origins: Union[str, List[str]] = Field(default_factory=list)
    api_rate_limit: str = Field(default="100/minute")
    bot_api_token: str = Field(...)
    
    # Database
    database_url: str = Field(...)
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(...)
    postgres_user: str = Field(...)
    postgres_password: str = Field(...)
    
    # Redis
    redis_url: str = Field(...)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: Optional[str] = Field(default=None)
    redis_db: int = Field(default=0)
    
    # Celery
    celery_broker_url: str = Field(...)
    celery_result_backend: str = Field(...)
    
    # JWT
    jwt_secret_key: str = Field(...)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=10080)  # 7 days for admin panel
    jwt_refresh_token_expire_days: int = Field(default=30)
    
    # Telegram
    telegram_bot_token: str = Field(...)
    telegram_bot_username: str = Field(...)
    telegram_webhook_url: Optional[str] = Field(default=None)
    telegram_webhook_secret: Optional[str] = Field(default=None)
    telegram_use_webhook: bool = Field(default=False)
    
    # Platega
    platega_api_url: str = Field(...)
    platega_merchant_id: str = Field(...)
    platega_secret_key: str = Field(...)
    platega_webhook_url: str = Field(...)
    platega_success_url: str = Field(...)
    platega_failure_url: str = Field(...)
    platega_webhook_ips: Union[str, List[str]] = Field(default_factory=list)
    
    # VPN Agent
    agent_api_token: str = Field(...)
    agent_port: int = Field(default=8001)
    agent_auth_type: str = Field(default="hmac")
    VPN_AGENT_SECRET_KEY: str = Field(...)  # HMAC secret for VPN agent
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_file: str = Field(default="/var/log/metalib-vpn-bot/app.log")
    
    # Sentry
    sentry_dsn: Optional[str] = Field(default=None)
    sentry_environment: str = Field(default="development")
    sentry_traces_sample_rate: float = Field(default=0.1)
    
    # Email
    smtp_host: Optional[str] = Field(default=None)
    smtp_port: int = Field(default=587)
    smtp_user: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    smtp_from_email: str = Field(default="noreply@example.com")
    smtp_use_tls: bool = Field(default=True)
    
    # Default settings
    default_language: str = Field(default="ru")
    default_currency: str = Field(default="RUB")
    subscription_expiry_notification_days: Union[str, List[int]] = Field(default_factory=lambda: [3, 1])
    device_binding_token_expiry_minutes: int = Field(default=10)
    max_device_binding_attempts: int = Field(default=3)
    telegram_admin_id: Optional[int] = Field(default=None)
    telegram_log_channel_id: Optional[int] = Field(default=None)
    admin_telegram_chat_id: Optional[int] = Field(default=None)  # For system alerts
    
    # Platega api key (optional, if not set in required fields)
    platega_api_key: str = Field(default="")
    
    # Feature flags
    enable_referral_program: bool = Field(default=True)
    enable_promo_codes: bool = Field(default=True)
    enable_auto_renewal: bool = Field(default=True)
    enable_geolocation: bool = Field(default=True)
    
    @validator("api_cors_origins", pre=True)
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(v, list):
            return v
        if not v or v == "" or v is None:
            return []
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return []
    
    @validator("platega_webhook_ips", pre=True)
    def parse_webhook_ips(cls, v) -> List[str]:
        """Parse webhook IPs from comma-separated string or list"""
        if isinstance(v, list):
            return v
        if not v or v == "" or v is None:
            return []
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return []
    
    @validator("subscription_expiry_notification_days", pre=True)
    def parse_notification_days(cls, v) -> List[int]:
        """Parse notification days from comma-separated string or list"""
        if isinstance(v, list):
            return [int(x) for x in v]
        if isinstance(v, str):
            return [int(day.strip()) for day in v.split(",") if day.strip()]
        return [3, 1]


# Global settings instance
settings = Settings()
