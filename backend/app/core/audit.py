"""
Advanced structured logging with audit trail support
"""
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from functools import wraps
from loguru import logger

from app.core.config import settings


# Context variables for request tracing
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[Optional[int]] = ContextVar("user_id", default=None)
admin_id_ctx: ContextVar[Optional[int]] = ContextVar("admin_id", default=None)
ip_address_ctx: ContextVar[Optional[str]] = ContextVar("ip_address", default=None)


class ContextFilter(logging.Filter):
    """Add context variables to log records"""
    
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        record.user_id = user_id_ctx.get()
        record.admin_id = admin_id_ctx.get()
        record.ip_address = ip_address_ctx.get()
        return True


class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to loguru"""
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # Add context to extra
        extra = {
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
            "admin_id": getattr(record, "admin_id", None),
            "ip_address": getattr(record, "ip_address", None),
        }
        
        logger.opt(depth=depth, exception=record.exc_info).bind(**extra).log(
            level, record.getMessage()
        )


def json_serializer(record: Dict[str, Any]) -> str:
    """JSON serializer for structured logging"""
    subset = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }
    
    # Add context from extra
    for key in ["request_id", "user_id", "admin_id", "ip_address"]:
        if key in record["extra"] and record["extra"][key]:
            subset[key] = record["extra"][key]
    
    # Add other extra fields
    for key, value in record["extra"].items():
        if key not in ["request_id", "user_id", "admin_id", "ip_address"]:
            subset[key] = value
    
    # Add exception info
    if record["exception"]:
        subset["exception"] = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback,
        }
    
    return json.dumps(subset)


def setup_logging() -> None:
    """Configure logging for the application"""
    
    # Remove default loggers
    logger.remove()
    
    # Define log format
    if settings.log_format == "json":
        logger.add(
            sys.stdout,
            format="{message}",
            level=settings.log_level,
            serialize=True,
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[request_id]}</cyan> | "
            "<magenta>{extra[user_id]}</magenta> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stdout,
            format=log_format,
            level=settings.log_level,
            colorize=True,
        )
    
    # Add file handler
    if settings.log_file:
        logger.add(
            settings.log_file,
            rotation="1 day",
            retention="30 days",
            compression="gz",
            level=settings.log_level,
            serialize=True,  # JSON for files always
        )
    
    # Add error-specific file handler
    logger.add(
        "logs/errors.log",
        rotation="1 day",
        retention="90 days",
        compression="gz",
        level="ERROR",
        serialize=True,
    )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    for logger_name in [
        "uvicorn", "uvicorn.access", "uvicorn.error", 
        "fastapi", "sqlalchemy.engine", "asyncio"
    ]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
    
    logger.info(f"Logging configured: level={settings.log_level}")


# ============== Audit Logger ==============

class AuditLogger:
    """
    Structured audit logger for tracking admin and user actions
    """
    
    CATEGORIES = {
        "auth": "Authentication",
        "user": "User Management",
        "subscription": "Subscriptions",
        "payment": "Payments",
        "server": "Server Management",
        "vpn": "VPN Configuration",
        "admin": "Admin Actions",
        "system": "System Events",
    }
    
    def __init__(self):
        self._db_session = None
    
    async def log(
        self,
        category: str,
        action: str,
        actor_id: Optional[int] = None,
        actor_type: str = "user",  # user, admin, system
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",  # success, failure, warning
    ):
        """
        Log an audit event
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": category,
            "action": action,
            "actor": {
                "id": actor_id or admin_id_ctx.get() or user_id_ctx.get(),
                "type": actor_type,
            },
            "target": {
                "type": target_type,
                "id": target_id,
            } if target_type else None,
            "details": details or {},
            "ip_address": ip_address or ip_address_ctx.get(),
            "user_agent": user_agent,
            "request_id": request_id_ctx.get(),
            "status": status,
        }
        
        # Log to structured logger
        log_level = "warning" if status == "failure" else "info"
        logger.opt(depth=1).bind(
            audit=True,
            event_category=category,
            event_action=action,
            actor_id=event["actor"]["id"],
            target_id=target_id,
            status=status
        ).log(log_level.upper(), f"AUDIT: {category}.{action} - {status}")
        
        # Save to database
        await self._save_to_db(event)
        
        return event
    
    async def _save_to_db(self, event: Dict[str, Any]):
        """Save audit event to database"""
        try:
            from app.core.database import async_session_maker
            from app.models.audit_log import AuditLog
            
            async with async_session_maker() as session:
                audit_log = AuditLog(
                    category=event["category"],
                    action=event["action"],
                    actor_id=event["actor"]["id"],
                    actor_type=event["actor"]["type"],
                    target_type=event["target"]["type"] if event["target"] else None,
                    target_id=event["target"]["id"] if event["target"] else None,
                    details=event["details"],
                    ip_address=event["ip_address"],
                    status=event["status"],
                    request_id=event["request_id"],
                )
                session.add(audit_log)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to save audit log to DB: {e}")
    
    # ============== Auth Events ==============
    
    async def log_login(
        self, 
        admin_id: int, 
        ip_address: str,
        user_agent: str = None,
        success: bool = True,
        failure_reason: str = None
    ):
        return await self.log(
            category="auth",
            action="login",
            actor_id=admin_id,
            actor_type="admin",
            details={"failure_reason": failure_reason} if failure_reason else {},
            ip_address=ip_address,
            user_agent=user_agent,
            status="success" if success else "failure",
        )
    
    async def log_logout(self, admin_id: int, ip_address: str = None):
        return await self.log(
            category="auth",
            action="logout",
            actor_id=admin_id,
            actor_type="admin",
            ip_address=ip_address,
        )
    
    async def log_2fa_verified(self, admin_id: int, ip_address: str = None):
        return await self.log(
            category="auth",
            action="2fa_verified",
            actor_id=admin_id,
            actor_type="admin",
            ip_address=ip_address,
        )
    
    # ============== User Events ==============
    
    async def log_user_created(
        self, 
        user_id: int, 
        telegram_id: int,
        referrer_id: int = None
    ):
        return await self.log(
            category="user",
            action="created",
            actor_type="system",
            target_type="user",
            target_id=user_id,
            details={
                "telegram_id": telegram_id,
                "referrer_id": referrer_id,
            },
        )
    
    async def log_user_blocked(
        self, 
        admin_id: int, 
        user_id: int, 
        reason: str = None
    ):
        return await self.log(
            category="user",
            action="blocked",
            actor_id=admin_id,
            actor_type="admin",
            target_type="user",
            target_id=user_id,
            details={"reason": reason},
        )
    
    # ============== Subscription Events ==============
    
    async def log_subscription_created(
        self, 
        user_id: int, 
        subscription_id: int,
        plan_id: int,
        amount: float
    ):
        return await self.log(
            category="subscription",
            action="created",
            actor_id=user_id,
            actor_type="user",
            target_type="subscription",
            target_id=subscription_id,
            details={
                "plan_id": plan_id,
                "amount": amount,
            },
        )
    
    async def log_subscription_renewed(
        self, 
        user_id: int, 
        subscription_id: int,
        auto: bool = False
    ):
        return await self.log(
            category="subscription",
            action="renewed",
            actor_id=user_id,
            actor_type="system" if auto else "user",
            target_type="subscription",
            target_id=subscription_id,
            details={"auto_renewal": auto},
        )
    
    async def log_subscription_cancelled(
        self, 
        user_id: int, 
        subscription_id: int,
        reason: str = None
    ):
        return await self.log(
            category="subscription",
            action="cancelled",
            actor_id=user_id,
            actor_type="user",
            target_type="subscription",
            target_id=subscription_id,
            details={"reason": reason},
        )
    
    # ============== Payment Events ==============
    
    async def log_payment_created(
        self, 
        user_id: int, 
        payment_id: int,
        amount: float,
        provider: str
    ):
        return await self.log(
            category="payment",
            action="created",
            actor_id=user_id,
            actor_type="user",
            target_type="payment",
            target_id=payment_id,
            details={
                "amount": amount,
                "provider": provider,
            },
        )
    
    async def log_payment_completed(
        self, 
        payment_id: int,
        amount: float
    ):
        return await self.log(
            category="payment",
            action="completed",
            actor_type="system",
            target_type="payment",
            target_id=payment_id,
            details={"amount": amount},
        )
    
    async def log_payment_failed(
        self, 
        payment_id: int,
        reason: str
    ):
        return await self.log(
            category="payment",
            action="failed",
            actor_type="system",
            target_type="payment",
            target_id=payment_id,
            details={"reason": reason},
            status="failure",
        )
    
    # ============== Server Events ==============
    
    async def log_server_created(
        self, 
        admin_id: int, 
        server_id: int,
        server_name: str
    ):
        return await self.log(
            category="server",
            action="created",
            actor_id=admin_id,
            actor_type="admin",
            target_type="server",
            target_id=server_id,
            details={"server_name": server_name},
        )
    
    async def log_server_status_changed(
        self, 
        server_id: int,
        old_status: str,
        new_status: str,
        admin_id: int = None
    ):
        return await self.log(
            category="server",
            action="status_changed",
            actor_id=admin_id,
            actor_type="admin" if admin_id else "system",
            target_type="server",
            target_id=server_id,
            details={
                "old_status": old_status,
                "new_status": new_status,
            },
        )
    
    # ============== VPN Events ==============
    
    async def log_vpn_key_generated(
        self, 
        user_id: int, 
        server_id: int = None
    ):
        return await self.log(
            category="vpn",
            action="key_generated",
            actor_id=user_id,
            actor_type="user",
            details={"server_id": server_id},
        )
    
    async def log_vpn_connection(
        self, 
        user_id: int, 
        server_id: int,
        connected: bool = True
    ):
        return await self.log(
            category="vpn",
            action="connected" if connected else "disconnected",
            actor_id=user_id,
            actor_type="user",
            target_type="server",
            target_id=server_id,
        )
    
    # ============== Admin Events ==============
    
    async def log_admin_action(
        self, 
        admin_id: int, 
        action: str,
        target_type: str = None,
        target_id: int = None,
        details: Dict[str, Any] = None
    ):
        return await self.log(
            category="admin",
            action=action,
            actor_id=admin_id,
            actor_type="admin",
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    
    async def log_settings_changed(
        self, 
        admin_id: int, 
        setting_key: str,
        old_value: Any,
        new_value: Any
    ):
        return await self.log(
            category="admin",
            action="settings_changed",
            actor_id=admin_id,
            actor_type="admin",
            details={
                "setting_key": setting_key,
                "old_value": str(old_value),
                "new_value": str(new_value),
            },
        )


# Global audit logger instance
audit = AuditLogger()


# ============== Decorator for audit logging ==============

def audit_action(
    category: str,
    action: str,
    target_type: str = None,
    get_target_id: callable = None,
    get_details: callable = None,
):
    """
    Decorator to automatically log audit events for functions
    
    Usage:
        @audit_action("user", "block", target_type="user", get_target_id=lambda args: args[0])
        async def block_user(user_id: int, reason: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            target_id = get_target_id(args, kwargs) if get_target_id else None
            details = get_details(args, kwargs) if get_details else {}
            
            try:
                result = await func(*args, **kwargs)
                await audit.log(
                    category=category,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    details=details,
                    status="success",
                )
                return result
            except Exception as e:
                await audit.log(
                    category=category,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    details={**details, "error": str(e)},
                    status="failure",
                )
                raise
        
        return wrapper
    return decorator


# Export
__all__ = [
    "logger",
    "setup_logging",
    "audit",
    "audit_action",
    "request_id_ctx",
    "user_id_ctx",
    "admin_id_ctx",
    "ip_address_ctx",
]
