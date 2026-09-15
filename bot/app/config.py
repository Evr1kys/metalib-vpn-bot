"""
Telegram Bot Configuration
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class BotSettings(BaseSettings):
    """Bot settings"""
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Telegram
    telegram_bot_token: str = Field(...)
    telegram_webhook_url: str = Field(default="")
    telegram_use_webhook: bool = Field(default=False)
    
    # API
    api_base_url: str = Field(...)
    bot_api_token: str = Field(...)  # Bot API token for backend
    
    # Website URLs
    website_url: str = Field(default="https://vpn.metalib.xyz")
    admin_url: str = Field(default="https://panel.metalib.xyz")
    
    # Redis
    redis_url: str = Field(...)
    
    # Logging
    log_level: str = Field(default="INFO")
    
    # Features
    enable_referral_program: bool = Field(default=True)
    enable_promo_codes: bool = Field(default=True)


settings = BotSettings()
