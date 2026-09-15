"""
Alert Service

Handles creating, sending and managing system alerts
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, update
from loguru import logger
import httpx

from app.models.alert import Alert, AlertSeverity, AlertCategory, AlertStatus
from app.core.config import settings


# Rate limiting settings
ALERT_RATE_LIMIT_WINDOW = 60  # seconds
ALERT_RATE_LIMIT_MAX = 10  # max alerts per window per source
SIMILAR_ALERT_MERGE_WINDOW = 300  # 5 minutes - merge similar alerts


class AlertService:
    """Service for managing system alerts"""
    
    # Class-level rate limiting storage
    _rate_limits: Dict[str, List[datetime]] = {}
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _check_rate_limit(self, source: str) -> bool:
        """Check if alert creation is rate-limited"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=ALERT_RATE_LIMIT_WINDOW)
        
        if source not in self._rate_limits:
            self._rate_limits[source] = []
        
        # Clean old entries
        self._rate_limits[source] = [
            ts for ts in self._rate_limits[source] if ts > window_start
        ]
        
        # Check limit
        if len(self._rate_limits[source]) >= ALERT_RATE_LIMIT_MAX:
            logger.warning(f"Rate limit exceeded for alert source: {source}")
            return False
        
        # Add new timestamp
        self._rate_limits[source].append(now)
        return True
    
    async def _find_similar_alert(
        self,
        title: str,
        category: AlertCategory,
        source: Optional[str]
    ) -> Optional[Alert]:
        """Find similar active alert to merge with"""
        window_start = datetime.utcnow() - timedelta(seconds=SIMILAR_ALERT_MERGE_WINDOW)
        
        query = select(Alert).where(
            and_(
                Alert.title == title,
                Alert.category == category,
                Alert.status == AlertStatus.ACTIVE,
                Alert.created_at > window_start
            )
        )
        
        if source:
            query = query.where(Alert.source == source)
        
        result = await self.db.execute(query.order_by(desc(Alert.created_at)).limit(1))
        return result.scalar_one_or_none()
    
    async def create_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        category: AlertCategory = AlertCategory.SYSTEM,
        source: Optional[str] = None,
        source_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        send_telegram: bool = True,
        auto_resolve_minutes: int = 0,
        skip_rate_limit: bool = False,
        merge_similar: bool = True
    ) -> Optional[Alert]:
        """
        Create a new alert and optionally send notifications.
        
        Features:
        - Rate limiting to prevent spam
        - Automatic merging of similar alerts
        - Duplicate prevention for same source_id within 5 minutes
        """
        # Rate limiting check
        rate_key = f"{source or 'unknown'}:{category.value}"
        if not skip_rate_limit and not self._check_rate_limit(rate_key):
            logger.debug(f"Alert rate-limited: {title}")
            return None
        
        # Try to merge with similar alert
        if merge_similar:
            similar = await self._find_similar_alert(title, category, source)
            if similar:
                # Update existing alert instead of creating new
                occurrence_count = (similar.extra_data or {}).get('occurrence_count', 1) + 1
                updated_data = similar.extra_data or {}
                updated_data['occurrence_count'] = occurrence_count
                updated_data['last_occurrence'] = datetime.utcnow().isoformat()
                
                similar.extra_data = updated_data
                similar.message = f"{message}\n\n📊 Повторений: {occurrence_count}"
                similar.updated_at = datetime.utcnow()
                
                # Escalate severity if many occurrences
                if occurrence_count >= 5 and similar.severity == AlertSeverity.WARNING:
                    similar.severity = AlertSeverity.ERROR
                elif occurrence_count >= 10 and similar.severity == AlertSeverity.ERROR:
                    similar.severity = AlertSeverity.CRITICAL
                
                await self.db.commit()
                logger.info(f"Alert merged: {title} (count: {occurrence_count})")
                return similar
        
        # Check for recent duplicate by source_id
        if source_id:
            five_min_ago = datetime.utcnow() - timedelta(minutes=5)
            existing = await self.db.execute(
                select(Alert).where(
                    and_(
                        Alert.source_id == source_id,
                        Alert.created_at > five_min_ago,
                        Alert.status != AlertStatus.RESOLVED
                    )
                )
            )
            if existing.scalar_one_or_none():
                logger.debug(f"Skipping duplicate alert for {source_id}")
                return None
        
        alert = Alert(
            title=title,
            message=message,
            severity=severity,
            category=category,
            source=source,
            source_id=source_id,
            extra_data=extra_data or {},
            auto_resolve_after_minutes=auto_resolve_minutes
        )
        
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        
        logger.info(f"Alert created: [{severity.value}] {title}")
        
        # Send notifications
        if send_telegram and severity in [AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            await self._send_telegram_alert(alert)
        
        return alert
    
    async def _send_telegram_alert(self, alert: Alert):
        """Send alert to admin Telegram chat"""
        admin_chat_id = getattr(settings, 'admin_telegram_chat_id', None)
        
        if not admin_chat_id:
            logger.debug("No admin_telegram_chat_id configured, skipping Telegram alert")
            return
        
        # Severity emoji
        emoji_map = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "🔴",
            AlertSeverity.CRITICAL: "🚨"
        }
        emoji = emoji_map.get(alert.severity, "📢")
        
        # Category emoji
        cat_emoji = {
            AlertCategory.SERVER: "🖥",
            AlertCategory.PAYMENT: "💳",
            AlertCategory.SUBSCRIPTION: "📋",
            AlertCategory.SECURITY: "🔐",
            AlertCategory.SYSTEM: "⚙️",
            AlertCategory.VPN: "🔒"
        }
        cat = cat_emoji.get(alert.category, "📌")
        
        text = f"""{emoji} <b>{alert.severity.value.upper()}</b> {cat}

<b>{alert.title}</b>

{alert.message}

<i>Категория: {alert.category.value}</i>
<i>ID: {str(alert.id)[:8]}</i>"""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": admin_chat_id,
                        "text": text,
                        "parse_mode": "HTML"
                    }
                )
                
                if response.status_code == 200:
                    alert.telegram_sent = True
                    await self.db.commit()
                    logger.info(f"Telegram alert sent: {alert.title}")
                else:
                    logger.error(f"Failed to send Telegram alert: {response.text}")
        
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    async def get_active_alerts(
        self,
        category: Optional[AlertCategory] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50
    ) -> List[Alert]:
        """Get active (non-resolved) alerts"""
        query = select(Alert).where(Alert.status != AlertStatus.RESOLVED)
        
        if category:
            query = query.where(Alert.category == category)
        if severity:
            query = query.where(Alert.severity == severity)
        
        query = query.order_by(desc(Alert.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_alerts_history(
        self,
        days: int = 7,
        limit: int = 100
    ) -> List[Alert]:
        """Get alerts history"""
        since = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(Alert)
            .where(Alert.created_at > since)
            .order_by(desc(Alert.created_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    async def acknowledge_alert(self, alert_id: str, admin_username: str) -> Alert:
        """Mark alert as acknowledged"""
        alert = await self.db.get(Alert, alert_id)
        if not alert:
            return None
        
        alert.acknowledge(admin_username)
        await self.db.commit()
        return alert
    
    async def resolve_alert(
        self, 
        alert_id: str, 
        admin_username: str,
        note: Optional[str] = None
    ) -> Alert:
        """Mark alert as resolved"""
        alert = await self.db.get(Alert, alert_id)
        if not alert:
            return None
        
        alert.resolve(admin_username, note)
        await self.db.commit()
        return alert
    
    async def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        # Active count by severity
        active_result = await self.db.execute(
            select(Alert.severity, func.count(Alert.id))
            .where(Alert.status == AlertStatus.ACTIVE)
            .group_by(Alert.severity)
        )
        active_by_severity = {row[0].value: row[1] for row in active_result.all()}
        
        # Last 24h count
        day_ago = datetime.utcnow() - timedelta(days=1)
        day_result = await self.db.execute(
            select(func.count(Alert.id)).where(Alert.created_at > day_ago)
        )
        last_24h = day_result.scalar() or 0
        
        # Total active
        active_total = await self.db.execute(
            select(func.count(Alert.id)).where(Alert.status == AlertStatus.ACTIVE)
        )
        
        return {
            "active_total": active_total.scalar() or 0,
            "active_by_severity": active_by_severity,
            "last_24h": last_24h,
            "critical_active": active_by_severity.get("critical", 0),
            "error_active": active_by_severity.get("error", 0),
        }
    
    async def auto_resolve_expired(self):
        """Auto-resolve alerts that have exceeded their auto_resolve time"""
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(Alert).where(
                and_(
                    Alert.status == AlertStatus.ACTIVE,
                    Alert.auto_resolve_after_minutes > 0
                )
            )
        )
        alerts = result.scalars().all()
        
        resolved_count = 0
        for alert in alerts:
            threshold = alert.created_at + timedelta(minutes=alert.auto_resolve_after_minutes)
            if now > threshold:
                alert.resolve("system", "Auto-resolved after timeout")
                resolved_count += 1
        
        if resolved_count > 0:
            await self.db.commit()
            logger.info(f"Auto-resolved {resolved_count} expired alerts")
        
        return resolved_count


# Convenience functions for creating specific alert types
async def server_offline_alert(db: AsyncSession, server_name: str, server_id: str, reason: str = ""):
    """Create alert when server goes offline"""
    service = AlertService(db)
    return await service.create_alert(
        title=f"Сервер {server_name} недоступен",
        message=f"VPN сервер {server_name} перестал отвечать.\n\nПричина: {reason or 'Нет связи'}",
        severity=AlertSeverity.ERROR,
        category=AlertCategory.SERVER,
        source="health_check",
        source_id=server_id,
        auto_resolve_minutes=30  # Auto-resolve if not resolved in 30 min
    )


async def server_degraded_alert(db: AsyncSession, server_name: str, server_id: str, metrics: dict):
    """Create alert when server performance is degraded"""
    service = AlertService(db)
    
    issues = []
    if metrics.get("cpu_load", 0) > 5:
        issues.append(f"CPU: {metrics['cpu_load']}")
    if metrics.get("memory_percent", 0) > 90:
        issues.append(f"RAM: {metrics['memory_percent']}%")
    if metrics.get("disk_percent", 0) > 85:
        issues.append(f"Диск: {metrics['disk_percent']}%")
    
    return await service.create_alert(
        title=f"Сервер {server_name} перегружен",
        message=f"Производительность сервера снижена.\n\nПроблемы: {', '.join(issues)}",
        severity=AlertSeverity.WARNING,
        category=AlertCategory.SERVER,
        source="health_check",
        source_id=server_id,
        extra_data=metrics,
        auto_resolve_minutes=60
    )


async def payment_failed_alert(db: AsyncSession, payment_id: str, user_id: str, amount: float, reason: str):
    """Create alert for failed payment"""
    service = AlertService(db)
    return await service.create_alert(
        title="Ошибка платежа",
        message=f"Платеж на {amount} ₽ не прошел.\n\nПользователь: {user_id}\nПричина: {reason}",
        severity=AlertSeverity.WARNING,
        category=AlertCategory.PAYMENT,
        source="payment_webhook",
        source_id=payment_id
    )


async def security_alert(db: AsyncSession, title: str, message: str, source_id: str = None):
    """Create security alert"""
    service = AlertService(db)
    return await service.create_alert(
        title=title,
        message=message,
        severity=AlertSeverity.CRITICAL,
        category=AlertCategory.SECURITY,
        source="security",
        source_id=source_id
    )


async def subscription_mass_expiry_alert(db: AsyncSession, count: int, timeframe: str):
    """Alert when many subscriptions are expiring"""
    service = AlertService(db)
    return await service.create_alert(
        title=f"{count} подписок истекает {timeframe}",
        message=f"В ближайшее время истекает {count} подписок. Рассмотрите отправку напоминаний.",
        severity=AlertSeverity.INFO,
        category=AlertCategory.SUBSCRIPTION,
        source="subscription_monitor",
        auto_resolve_minutes=1440  # 24 hours
    )
