"""
Models package - import all models for Alembic
"""
from app.models.base import Base, UUIDMixin, TimestampMixin
from app.models.user import User
from app.models.plan import Plan
from app.models.server_location import ServerLocation, ServerTypeConfig
from app.models.server import Server, ServerStatus, ManagementType, ServerType
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.server_group import ServerGroup, ServerGroupMember, LoadBalancingStrategy
from app.models.vpn_account import VPNAccount, VPNProtocol, VPNAccountStatus
from app.models.device import Device, DeviceSession
from app.models.admin import AdminUser, AdminRole
from app.models.audit_log import AuditLog
from app.models.promo_code import PromoCode, PromoCodeUse, DiscountType
from app.models.referral import Referral, ReferralStatus
from app.models.notification import Notification, NotificationType
from app.models.broadcast import BroadcastLog
from app.models.support import SupportTicket, SupportMessage, SupportSettings, TicketStatus, TicketPriority, MessageSender

# New models
from app.models.gift_certificate import GiftCertificate, GiftCertificateStatus
from app.models.trial import Trial, TrialStatus, TrialSettings
from app.models.smart_connect import (
    SmartConnectProfile, OperatorServerRecommendation, 
    ServerHealthCheck, ServerAlert, SpeedTestResult,
    MobileOperator, ServerHealthStatus
)
from app.models.knowledge_base import (
    KnowledgeBaseArticle, FAQCategory, ArticleView, ArticleLike,
    ArticleStatus, ArticleCategory
)
from app.models.partner import (
    Partner, PartnerClick, PartnerSale, PartnerPayout, PartnerSettings,
    PartnerStatus, PartnerTier
)
from app.models.promotion import Promotion, SavingsCalculatorConfig, PromotionUse, PromoType
from app.models.alert import Alert, AlertSeverity, AlertCategory, AlertStatus

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "User",
    "Plan",
    "Subscription",
    "SubscriptionStatus",
    "Payment",
    "PaymentStatus",
    "Server",
    "ServerStatus",
    "ServerType",
    "ManagementType",
    "ServerGroup",
    "ServerGroupMember",
    "LoadBalancingStrategy",
    "VPNAccount",
    "VPNProtocol",
    "VPNAccountStatus",
    "Device",
    "DeviceSession",
    "AdminUser",
    "AdminRole",
    "AuditLog",
    "PromoCode",
    "PromoCodeUse",
    "DiscountType",
    "Referral",
    "ReferralStatus",
    "Notification",
    "NotificationType",
    "BroadcastLog",
    "SupportTicket",
    "SupportMessage",
    "SupportSettings",
    "TicketStatus",
    "TicketPriority",
    "MessageSender",
    # Gift Certificates
    "GiftCertificate",
    "GiftCertificateStatus",
    # Server Locations
    "ServerLocation",
    "ServerTypeConfig",
    # Trial
    "Trial",
    "TrialStatus",
    "TrialSettings",
    # Smart Connect
    "SmartConnectProfile",
    "OperatorServerRecommendation",
    "ServerHealthCheck",
    "ServerAlert",
    "SpeedTestResult",
    "MobileOperator",
    "ServerHealthStatus",
    # Knowledge Base
    "KnowledgeBaseArticle",
    "FAQCategory",
    "ArticleView",
    "ArticleLike",
    "ArticleStatus",
    "ArticleCategory",
    # Partner Program
    "Partner",
    "PartnerClick",
    "PartnerSale",
    "PartnerPayout",
    "PartnerSettings",
    "PartnerStatus",
    "PartnerTier",
    # Promotions
    "Promotion",
    "SavingsCalculatorConfig",
    "PromotionUse",
    "PromoType",
    # System Alerts
    "Alert",
    "AlertSeverity",
    "AlertCategory",
    "AlertStatus",
]
