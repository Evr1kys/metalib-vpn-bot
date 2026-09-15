"""
Admin User model with granular permissions system
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
import enum
import json
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class AdminRole(str, enum.Enum):
    """Admin user role"""
    OWNER = "owner"           # Full access - cannot be restricted
    ADMIN = "admin"           # Full access by default, can be customized
    MODERATOR = "moderator"   # Moderate users and support
    SUPPORT = "support"       # Limited support permissions
    VIEWER = "viewer"         # Read-only access


# All available permissions
ALL_PERMISSIONS = {
    # Dashboard
    "view_dashboard": "Просмотр дашборда",
    "view_analytics": "Просмотр аналитики",
    
    # Users management
    "view_users": "Просмотр пользователей",
    "edit_users": "Редактирование пользователей",
    "delete_users": "Удаление пользователей",
    "ban_users": "Блокировка пользователей",
    
    # Subscriptions
    "view_subscriptions": "Просмотр подписок",
    "edit_subscriptions": "Редактирование подписок",
    "create_subscriptions": "Создание подписок",
    "cancel_subscriptions": "Отмена подписок",
    
    # Payments
    "view_payments": "Просмотр платежей",
    "refund_payments": "Возврат платежей",
    
    # Servers & VPN
    "view_servers": "Просмотр серверов",
    "manage_servers": "Управление серверами",
    "view_vpn_accounts": "Просмотр VPN аккаунтов",
    "manage_vpn_accounts": "Управление VPN аккаунтами",
    
    # Plans & Promo
    "view_plans": "Просмотр тарифов",
    "manage_plans": "Управление тарифами",
    "view_promo_codes": "Просмотр промокодов",
    "manage_promo_codes": "Управление промокодами",
    
    # Notifications
    "send_notifications": "Отправка уведомлений",
    "send_broadcasts": "Массовая рассылка",
    
    # Support & Moderation
    "view_support_tickets": "Просмотр тикетов поддержки",
    "respond_support": "Ответ на тикеты",
    "view_telegram_messages": "Просмотр сообщений Telegram",
    "respond_telegram": "Ответ в Telegram",
    
    # Admin management
    "view_admins": "Просмотр администраторов",
    "manage_admins": "Управление администраторами",
    
    # Audit & Logs
    "view_audit_logs": "Просмотр журнала аудита",
    "view_system_logs": "Просмотр системных логов",
    
    # Settings
    "view_settings": "Просмотр настроек",
    "manage_settings": "Управление настройками",
}

# Default permissions by role
DEFAULT_PERMISSIONS = {
    AdminRole.OWNER: list(ALL_PERMISSIONS.keys()),  # All permissions
    AdminRole.ADMIN: [p for p in ALL_PERMISSIONS.keys() if p not in ["manage_admins", "manage_settings"]],
    AdminRole.MODERATOR: [
        "view_dashboard", "view_users", "edit_users", "ban_users",
        "view_subscriptions", "view_payments", "view_support_tickets",
        "respond_support", "view_telegram_messages", "respond_telegram",
        "send_notifications",
    ],
    AdminRole.SUPPORT: [
        "view_dashboard", "view_users", "view_subscriptions", "view_payments",
        "view_support_tickets", "respond_support", "view_telegram_messages",
        "respond_telegram",
    ],
    AdminRole.VIEWER: [
        "view_dashboard", "view_users", "view_subscriptions", "view_payments",
        "view_servers", "view_plans", "view_promo_codes",
    ],
}


class AdminUser(Base, UUIDMixin, TimestampMixin):
    """Admin panel user with granular permissions"""
    
    __tablename__ = "admin_users"
    
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Role
    role = Column(
        SQLEnum(AdminRole, name="admin_role"),
        default=AdminRole.SUPPORT,
        nullable=False,
        index=True
    )
    
    # Custom permissions (JSON array of permission keys)
    # If null, uses default permissions for role
    custom_permissions = Column(JSON, nullable=True)
    
    # Description/Notes
    description = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    
    # Security
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(50), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    
    # 2FA
    twofa_enabled = Column(Boolean, default=True, nullable=True)
    
    # Relationships - use string reference for forward declaration
    audit_logs = relationship("AuditLog", back_populates="admin_user", foreign_keys="[AuditLog.admin_user_id]")
    
    def __repr__(self):
        return f"<AdminUser(id={self.id}, username={self.username}, role={self.role})>"
    
    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def get_permissions(self) -> list:
        """Get list of all permissions for this admin"""
        # Owner always has all permissions
        if self.role == AdminRole.OWNER:
            return list(ALL_PERMISSIONS.keys())
        
        # If custom permissions are set, use them
        if self.custom_permissions:
            return self.custom_permissions
        
        # Otherwise use default permissions for role
        return DEFAULT_PERMISSIONS.get(self.role, [])
    
    def has_permission(self, permission: str) -> bool:
        """Check if admin has specific permission"""
        return permission in self.get_permissions()
    
    def has_any_permission(self, permissions: list) -> bool:
        """Check if admin has any of the specified permissions"""
        admin_perms = self.get_permissions()
        return any(p in admin_perms for p in permissions)
    
    def has_all_permissions(self, permissions: list) -> bool:
        """Check if admin has all of the specified permissions"""
        admin_perms = self.get_permissions()
        return all(p in admin_perms for p in permissions)
