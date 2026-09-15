"""
Prometheus Metrics Integration

Provides comprehensive metrics for:
- HTTP request latency and counts
- Business metrics (subscriptions, payments, etc.)
- System health metrics
- VPN server metrics
"""
import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    multiprocess,
    REGISTRY
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from app.core.logging import logger


# ===== HTTP Metrics =====

HTTP_REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

HTTP_REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint']
)


# ===== Business Metrics =====

ACTIVE_SUBSCRIPTIONS = Gauge(
    'metalib_active_subscriptions',
    'Number of active subscriptions'
)

TOTAL_USERS = Gauge(
    'metalib_total_users',
    'Total registered users'
)

PENDING_PAYMENTS = Gauge(
    'metalib_pending_payments',
    'Number of pending payments'
)

REVENUE_TOTAL = Counter(
    'metalib_revenue_total_rub',
    'Total revenue in RUB',
    ['plan_name']
)

NEW_SUBSCRIPTIONS = Counter(
    'metalib_new_subscriptions_total',
    'Total new subscriptions',
    ['plan_name']
)

EXPIRED_SUBSCRIPTIONS = Counter(
    'metalib_expired_subscriptions_total',
    'Total expired subscriptions'
)

SUPPORT_TICKETS = Gauge(
    'metalib_support_tickets_open',
    'Number of open support tickets'
)


# ===== VPN Server Metrics =====

VPN_SERVER_STATUS = Gauge(
    'metalib_vpn_server_status',
    'VPN server status (1=healthy, 0.5=degraded, 0=offline)',
    ['server_name', 'server_ip', 'location']
)

VPN_SERVER_CONNECTIONS = Gauge(
    'metalib_vpn_server_connections',
    'Active VPN connections per server',
    ['server_name']
)

VPN_ACCOUNTS_TOTAL = Gauge(
    'metalib_vpn_accounts_total',
    'Total VPN accounts',
    ['status']
)


# ===== System Metrics =====

CELERY_TASKS_RUNNING = Gauge(
    'metalib_celery_tasks_running',
    'Number of currently running Celery tasks'
)

DB_CONNECTION_POOL = Gauge(
    'metalib_db_connections',
    'Database connection pool status',
    ['state']  # active, idle, overflow
)

REDIS_CONNECTIONS = Gauge(
    'metalib_redis_connections',
    'Redis connection count'
)


def get_path_template(request: Request) -> str:
    """
    Get the path template for a request (e.g., /users/{user_id}).
    This prevents high cardinality from dynamic path parameters.
    """
    for route in request.app.routes:
        match, scope = route.matches({"type": "http", "path": request.url.path, "method": request.method})
        if match == Match.FULL:
            return route.path
    return request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP metrics for Prometheus.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint itself to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Get path template to avoid high cardinality
        path = get_path_template(request)
        method = request.method
        
        # Track in-progress requests
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).inc()
        
        # Time the request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            status = 500
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            
            HTTP_REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=status
            ).inc()
            
            HTTP_REQUEST_LATENCY.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).dec()
        
        return response


async def update_business_metrics():
    """
    Update business metrics from database.
    Called periodically by a background task.
    """
    from sqlalchemy import select, func
    from app.core.database import get_db_session
    from app.models import User, Subscription, Payment, VPNAccount, SupportTicket
    from app.models import SubscriptionStatus, PaymentStatus
    
    try:
        async with get_db_session() as db:
            # Users
            total_users = await db.scalar(select(func.count(User.id)))
            TOTAL_USERS.set(total_users or 0)
            
            # Subscriptions
            active_subs = await db.scalar(
                select(func.count(Subscription.id)).where(
                    Subscription.status == SubscriptionStatus.ACTIVE
                )
            )
            ACTIVE_SUBSCRIPTIONS.set(active_subs or 0)
            
            # Payments
            pending = await db.scalar(
                select(func.count(Payment.id)).where(
                    Payment.status == PaymentStatus.PENDING
                )
            )
            PENDING_PAYMENTS.set(pending or 0)
            
            # VPN accounts by status
            for status in ['active', 'suspended', 'expired']:
                count = await db.scalar(
                    select(func.count(VPNAccount.id)).where(
                        VPNAccount.status == status
                    )
                )
                VPN_ACCOUNTS_TOTAL.labels(status=status).set(count or 0)
            
            # Support tickets (if model exists)
            try:
                open_tickets = await db.scalar(
                    select(func.count(SupportTicket.id)).where(
                        SupportTicket.status.in_(['open', 'pending'])
                    )
                )
                SUPPORT_TICKETS.set(open_tickets or 0)
            except:
                pass
    
    except Exception as e:
        logger.error(f"Failed to update business metrics: {e}")


async def update_server_metrics():
    """
    Update VPN server metrics.
    """
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.server import Server, ServerStatus
    
    try:
        async with get_db_session() as db:
            result = await db.execute(select(Server))
            servers = result.scalars().all()
            
            for server in servers:
                status_value = {
                    ServerStatus.HEALTHY: 1.0,
                    ServerStatus.DEGRADED: 0.5,
                    ServerStatus.OFFLINE: 0.0,
                    ServerStatus.MAINTENANCE: 0.25,
                }.get(server.status, 0)
                
                VPN_SERVER_STATUS.labels(
                    server_name=server.name,
                    server_ip=str(server.ip_address) if server.ip_address else "unknown",
                    location=server.location or "unknown"
                ).set(status_value)
    
    except Exception as e:
        logger.error(f"Failed to update server metrics: {e}")


def setup_prometheus(app: FastAPI):
    """
    Setup Prometheus metrics for FastAPI application.
    """
    # Add middleware
    app.add_middleware(PrometheusMiddleware)
    
    # Add metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint"""
        # Update business metrics on each scrape
        await update_business_metrics()
        await update_server_metrics()
        
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST
        )
    
    logger.info("Prometheus metrics enabled at /metrics")


# ===== Helper Functions for Recording Metrics =====

def record_new_subscription(plan_name: str, amount: float):
    """Record a new subscription"""
    NEW_SUBSCRIPTIONS.labels(plan_name=plan_name).inc()
    REVENUE_TOTAL.labels(plan_name=plan_name).inc(amount)


def record_expired_subscription():
    """Record an expired subscription"""
    EXPIRED_SUBSCRIPTIONS.inc()


def record_payment(plan_name: str, amount: float):
    """Record a successful payment"""
    REVENUE_TOTAL.labels(plan_name=plan_name).inc(amount)
