"""
Celery Worker Configuration
"""
import asyncio
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


def run_async(coro):
    """Run async coroutine in sync Celery task - fixes event loop issues"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Create Celery app
celery_app = Celery(
    "metalib_vpn_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "worker.tasks.health_checks",
        "worker.tasks.subscriptions",
        "worker.tasks.notifications",
        "worker.tasks.vpn_provisioning"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Periodic tasks schedule
celery_app.conf.beat_schedule = {
    # Check server health every 5 minutes
    "check-server-health": {
        "task": "worker.tasks.health_checks.check_all_servers",
        "schedule": 300.0,  # 5 minutes
    },
    # Process subscription expirations every hour
    "process-expirations": {
        "task": "worker.tasks.subscriptions.process_expirations",
        "schedule": 3600.0,  # 1 hour
    },
    # Cancel pending payments older than 1 hour - every 15 minutes
    "cancel-expired-payments": {
        "task": "worker.tasks.subscriptions.cancel_expired_payments",
        "schedule": 900.0,  # 15 minutes
    },
    # Send expiry notifications daily at 10:00 UTC
    "send-expiry-notifications": {
        "task": "worker.tasks.notifications.send_expiry_notifications",
        "schedule": crontab(hour=10, minute=0),
    },
    # Clean up expired device tokens every hour
    "cleanup-device-tokens": {
        "task": "worker.tasks.subscriptions.cleanup_device_tokens",
        "schedule": 3600.0,  # 1 hour
    },
    # Process auto-renewals daily at 09:00 UTC
    "process-auto-renewals": {
        "task": "worker.tasks.subscriptions.process_auto_renewals",
        "schedule": crontab(hour=9, minute=0),
    },
    # Check expiring subscriptions daily at 08:00 UTC (create alerts)
    "check-expiring-subscriptions": {
        "task": "worker.tasks.subscriptions.check_expiring_subscriptions",
        "schedule": crontab(hour=8, minute=0),
    },
}
