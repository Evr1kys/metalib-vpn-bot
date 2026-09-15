"""
VPN Provisioning Tasks
"""
from sqlalchemy import select
from loguru import logger

from worker.celery_app import celery_app
from app.core.database import get_worker_session
from app.models.subscription import Subscription
from app.models.vpn_account import VPNAccount
from app.services.vpn_service import VPNService


@celery_app.task(name="worker.tasks.vpn_provisioning.provision_vpn_account")
def provision_vpn_account(subscription_id: str):
    """
    Provision VPN account for subscription
    
    This is queued to handle provisioning asynchronously
    """
    from worker.celery_app import run_async
    return run_async(provision_vpn_account_async(subscription_id))


async def provision_vpn_account_async(subscription_id: str):
    """Async implementation of VPN provisioning"""
    db = get_worker_session()
    try:
        vpn_service = VPNService(db)
        
        try:
            # Get subscription
            result = await db.execute(
                select(Subscription).where(Subscription.id == subscription_id)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                logger.error(f"Subscription {subscription_id} not found")
                return {"error": "Subscription not found"}
            
            # Check if already provisioned
            if subscription.vpn_account_id:
                logger.warning(f"Subscription {subscription_id} already has VPN account")
                return {"skipped": "Already provisioned"}
            
            # Provision VPN account
            vpn_account = await vpn_service.provision_vpn_account(
                user_id=subscription.user_id,
                protocol="wireguard",  # Default protocol
                subscription_id=subscription.id
            )
            
            # Update subscription
            subscription.vpn_account_id = vpn_account.id
            await db.commit()
            
            logger.info(f"VPN account provisioned for subscription {subscription_id}")
            
            return {
                "status": "provisioned",
                "vpn_account_id": str(vpn_account.id)
            }
        
        except Exception as e:
            logger.error(f"Failed to provision VPN account for subscription {subscription_id}: {e}")
            return {"error": str(e)}
    finally:
        await db.close()


@celery_app.task(name="worker.tasks.vpn_provisioning.rotate_vpn_keys")
def rotate_vpn_keys(vpn_account_id: str):
    """Rotate VPN keys for account"""
    from worker.celery_app import run_async
    return run_async(rotate_vpn_keys_async(vpn_account_id))


async def rotate_vpn_keys_async(vpn_account_id: str):
    """Async implementation of key rotation"""
    db = get_worker_session()
    try:
        vpn_service = VPNService(db)
        
        try:
            # Rotate keys
            await vpn_service.rotate_vpn_account_keys(vpn_account_id)
            
            logger.info(f"VPN keys rotated for account {vpn_account_id}")
            
            return {"status": "rotated"}
        
        except Exception as e:
            logger.error(f"Failed to rotate VPN keys for account {vpn_account_id}: {e}")
            return {"error": str(e)}
    finally:
        await db.close()
