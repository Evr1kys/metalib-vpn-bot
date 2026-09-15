"""
Celery task for subscription expiry checking
"""
from datetime import datetime
from celery import shared_task
from sqlalchemy import select, and_
from app.core.database import get_async_session
from app.models import Subscription, SubscriptionStatus, VPNAccount
from app.services.xray_service import XrayService
from app.core.logging import logger


@shared_task(name="tasks.check_subscription_expiry")
async def check_subscription_expiry():
    """
    Check for expired subscriptions and suspend VPN access
    
    Runs every hour via Celery Beat
    """
    async with get_async_session() as db:
        # Find expired subscriptions
        stmt = select(Subscription).where(
            and_(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at <= datetime.utcnow()
            )
        )
        
        result = await db.execute(stmt)
        expired_subs = result.scalars().all()
        
        logger.info(f"Found {len(expired_subs)} expired subscriptions")
        
        xray_service = XrayService(db)
        
        for subscription in expired_subs:
            try:
                # Update subscription status
                subscription.status = SubscriptionStatus.EXPIRED
                
                # Find and revoke VPN accounts
                vpn_stmt = select(VPNAccount).where(
                    and_(
                        VPNAccount.subscription_id == subscription.id,
                        VPNAccount.status == "active"
                    )
                )
                vpn_result = await db.execute(vpn_stmt)
                vpn_accounts = vpn_result.scalars().all()
                
                for vpn_account in vpn_accounts:
                    await xray_service.revoke_account(str(vpn_account.id))
                    logger.info(f"Revoked VPN account {vpn_account.id} for expired subscription {subscription.id}")
                
                await db.commit()
                
                # TODO: Send notification to user about expiry
                
            except Exception as e:
                logger.error(f"Error processing expired subscription {subscription.id}: {e}")
                await db.rollback()
        
        return {
            "checked": len(expired_subs),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(name="tasks.auto_renew_subscriptions")
async def auto_renew_subscriptions():
    """
    Auto-renew subscriptions that are about to expire
    
    Checks subscriptions expiring in next 24 hours with auto_renew=True
    """
    from datetime import timedelta
    
    async with get_async_session() as db:
        # Find subscriptions expiring in next 24 hours with auto-renew
        tomorrow = datetime.utcnow() + timedelta(days=1)
        
        stmt = select(Subscription).where(
            and_(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.auto_renew == True,
                Subscription.expires_at <= tomorrow,
                Subscription.expires_at > datetime.utcnow()
            )
        )
        
        result = await db.execute(stmt)
        renew_subs = result.scalars().all()
        
        logger.info(f"Found {len(renew_subs)} subscriptions for auto-renewal")
        
        renewed_count = 0
        failed_count = 0
        
        for subscription in renew_subs:
            try:
                from app.services.subscription_service import SubscriptionService
                sub_service = SubscriptionService(db)
                
                # Create renewal payment
                payment = await sub_service.renew_subscription(str(subscription.id))
                
                logger.info(f"Created renewal payment {payment.id} for subscription {subscription.id}")
                renewed_count += 1
                
                # TODO: Send payment link to user
                
            except Exception as e:
                logger.error(f"Error auto-renewing subscription {subscription.id}: {e}")
                failed_count += 1
        
        return {
            "checked": len(renew_subs),
            "renewed": renewed_count,
            "failed": failed_count,
            "timestamp": datetime.utcnow().isoformat()
        }
