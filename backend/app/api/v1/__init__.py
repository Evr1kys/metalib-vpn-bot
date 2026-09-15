"""
API Router - v1
"""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    plans,
    plans_crud,
    subscriptions,
    payments,
    servers,
    devices,
    admin,
    webhooks,
    promocodes,
    referrals,
    stats,
    broadcast,
    vpn,
    audit_logs,
    support,
    web_auth,
    web_api,
    # New feature endpoints
    gift_certificates,
    trial,
    smart_connect,
    knowledge_base,
    partners,
    promotions,
    telegram_miniapp,
    alerts,
    analytics,
    websocket,
)

api_router = APIRouter()

# Public endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(web_auth.router, prefix="/web", tags=["web-auth"])
api_router.include_router(web_api.router, prefix="/website", tags=["website"])

# New public endpoints
api_router.include_router(smart_connect.router, prefix="/smart-connect", tags=["smart-connect"])
api_router.include_router(knowledge_base.router, prefix="/kb", tags=["knowledge-base"])
api_router.include_router(promotions.router, prefix="/promotions", tags=["promotions"])
api_router.include_router(telegram_miniapp.router, prefix="/telegram", tags=["telegram-miniapp"])

# Bot endpoints (protected by bot token OR admin JWT)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(referrals.router, prefix="/referrals", tags=["referrals"])
api_router.include_router(gift_certificates.router, prefix="/gifts", tags=["gift-certificates"])
api_router.include_router(trial.router, prefix="/trial", tags=["trial"])
api_router.include_router(partners.router, prefix="/partners", tags=["partners"])

# Admin endpoints (protected by JWT)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(audit_logs.router, prefix="/admin", tags=["audit-logs"])
api_router.include_router(servers.router, prefix="/servers", tags=["servers"])
api_router.include_router(promocodes.router, prefix="/promocodes", tags=["promocodes"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(broadcast.router, prefix="/broadcast", tags=["broadcast"])
api_router.include_router(vpn.router, prefix="/vpn", tags=["vpn"])
api_router.include_router(support.router, prefix="/support", tags=["support"])
api_router.include_router(plans_crud.router, prefix="/admin/plans", tags=["plans-admin"])
api_router.include_router(alerts.router, prefix="/admin/alerts", tags=["alerts"])
api_router.include_router(analytics.router, prefix="/admin", tags=["analytics"])

# WebSocket endpoints
api_router.include_router(websocket.router, tags=["websocket"])

