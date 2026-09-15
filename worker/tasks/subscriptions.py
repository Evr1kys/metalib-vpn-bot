"""
Subscription Management Tasks
"""
from datetime import datetime, timedelta
from sqlalchemy import select, update
from loguru import logger
import httpx

from worker.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_worker_session
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.device import Device
from app.models.user import User
from app.models.payment import Payment, PaymentStatus
from app.services.vpn_service import VPNService


async def send_telegram_message(telegram_id: int, message: str):
    """Send notification via Telegram"""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json={
                "chat_id": telegram_id,
                "text": message,
                "parse_mode": "HTML"
            })
        except Exception as e:
            logger.warning(f"Failed to send telegram message: {e}")


@celery_app.task(name="worker.tasks.subscriptions.cancel_expired_payments")
def cancel_expired_payments():
    """Cancel pending payments older than 1 hour"""
    from worker.celery_app import run_async
    return run_async(cancel_expired_payments_async())


async def cancel_expired_payments_async():
    """Async implementation of payment cancellation"""
    db = get_worker_session()
    try:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        # Find pending payments older than 1 hour
        result = await db.execute(
            select(Payment).where(
                Payment.status == PaymentStatus.PENDING,
                Payment.created_at <= one_hour_ago
            )
        )
        payments = result.scalars().all()
        
        cancelled_count = 0
        for payment in payments:
            payment.status = PaymentStatus.CANCELLED
            cancelled_count += 1
            logger.info(f"Cancelled expired payment: {payment.id}")
        
        if cancelled_count > 0:
            await db.commit()
            logger.info(f"Cancelled {cancelled_count} expired pending payments")
        
        return {"cancelled": cancelled_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error cancelling expired payments: {e}")
        return {"error": str(e)}
    finally:
        await db.close()


@celery_app.task(name="worker.tasks.subscriptions.process_expirations")
def process_expirations():
    """Process expired subscriptions"""
    from worker.celery_app import run_async
    return run_async(process_expirations_async())


async def process_expirations_async():
    """Async implementation of expiration processing"""
    from sqlalchemy.orm import selectinload
    from app.models.vpn_account import VPNAccount
    
    db = get_worker_session()
    try:
        vpn_service = VPNService(db)
        
        # Get expired subscriptions with VPN accounts
        result = await db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at <= datetime.utcnow()
            )
        )
        subscriptions = result.scalars().all()
        
        logger.info(f"Processing {len(subscriptions)} expired subscriptions")
        
        expired_count = 0
        for subscription in subscriptions:
            try:
                # Find VPN account for this subscription
                vpn_result = await db.execute(
                    select(VPNAccount).where(VPNAccount.subscription_id == subscription.id)
                )
                vpn_account = vpn_result.scalar_one_or_none()
                
                # Revoke VPN access
                if vpn_account:
                    await vpn_service.revoke_access(str(vpn_account.id))
                
                # Update subscription status
                subscription.status = SubscriptionStatus.EXPIRED
                subscription.cancelled_at = datetime.utcnow()
                
                # Send notification to user
                user_result = await db.execute(
                    select(User).where(User.id == subscription.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user and user.telegram_id:
                    message = (
                        "🔴 <b>Подписка истекла</b>\n\n"
                        "Ваша подписка завершилась и доступ к VPN приостановлен.\n\n"
                        "Продлите подписку, чтобы продолжить использование:\n"
                        "/start → 💎 Подписка → Продлить"
                    )
                    await send_telegram_message(user.telegram_id, message)
                
                expired_count += 1
                logger.info(f"Subscription {subscription.id} expired")
            
            except Exception as e:
                logger.error(f"Failed to expire subscription {subscription.id}: {e}")
        
        await db.commit()
        
        return {"expired": expired_count}
    finally:
        await db.close()


@celery_app.task(name="worker.tasks.subscriptions.cleanup_device_tokens")
def cleanup_device_tokens():
    """Clean up expired device binding tokens"""
    from worker.celery_app import run_async
    return run_async(cleanup_device_tokens_async())


async def cleanup_device_tokens_async():
    """Async implementation of token cleanup"""
    db = get_worker_session()
    try:
        # Delete tokens older than 1 hour (tokens are valid for 10 minutes)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        result = await db.execute(
            select(Device).where(
                Device.device_token.isnot(None),
                Device.token_expires_at < cutoff_time
            )
        )
        devices = result.scalars().all()
        
        cleaned_count = 0
        for device in devices:
            # Mark token as used/expired
            device.is_token_used = True
            cleaned_count += 1
        
        await db.commit()
        
        logger.info(f"Cleaned up {cleaned_count} expired device tokens")
        
        return {"cleaned": cleaned_count}
    finally:
        await db.close()


@celery_app.task(name="worker.tasks.subscriptions.process_auto_renewals")
def process_auto_renewals():
    """
    Process auto-renewals for subscriptions expiring soon.
    Runs daily to check subscriptions expiring in next 3 days.
    """
    from worker.celery_app import run_async
    return run_async(process_auto_renewals_async())


async def process_auto_renewals_async():
    """Async implementation of auto-renewal processing"""
    from app.models.plan import Plan
    from app.services.payment_service import PaymentService
    
    db = get_worker_session()
    try:
        # Find subscriptions expiring in 1-3 days with auto_renew enabled
        expiry_start = datetime.utcnow() + timedelta(days=1)
        expiry_end = datetime.utcnow() + timedelta(days=3)
        
        result = await db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.auto_renew == True,
                Subscription.expires_at >= expiry_start,
                Subscription.expires_at <= expiry_end
            ).options(selectinload(Subscription.user), selectinload(Subscription.plan))
        )
        subscriptions = result.scalars().all()
        
        logger.info(f"Processing {len(subscriptions)} subscriptions for auto-renewal")
        
        renewed = 0
        failed = 0
        
        for subscription in subscriptions:
            try:
                # Check if user has saved payment method
                user = subscription.user
                plan = subscription.plan
                
                if not user or not plan:
                    continue
                
                # Check if we already sent renewal notification
                last_renewal_attempt = getattr(subscription, 'last_renewal_attempt', None)
                if last_renewal_attempt and (datetime.utcnow() - last_renewal_attempt) < timedelta(days=1):
                    continue
                
                # Send renewal notification
                days_left = (subscription.expires_at - datetime.utcnow()).days
                
                message = f"""🔄 <b>Автопродление подписки</b>

Ваша подписка истекает через <b>{days_left}</b> дн.

📋 Тариф: <b>{plan.name}</b>
💰 Стоимость: <b>{plan.price}₽</b>

<blockquote>Автопродление включено. Для продления нажмите кнопку ниже или отключите автопродление в настройках.</blockquote>"""
                
                # Create renewal payment
                payment_service = PaymentService(db)
                
                try:
                    payment = await payment_service.create_payment(
                        user_id=str(user.id),
                        plan_id=str(plan.id),
                        amount=float(plan.price),
                        description=f"Автопродление: {plan.name}",
                        auto_renewal=True
                    )
                    
                    # Send notification with payment link
                    if user.telegram_id:
                        payment_url = payment.payment_url if hasattr(payment, 'payment_url') else None
                        
                        if payment_url:
                            message += f"\n\n👉 <a href='{payment_url}'>Оплатить {plan.price}₽</a>"
                        
                        await send_telegram_message(user.telegram_id, message)
                    
                    # Mark renewal attempt
                    subscription.last_renewal_attempt = datetime.utcnow()
                    renewed += 1
                    
                    logger.info(f"Auto-renewal payment created for subscription {subscription.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to create renewal payment for {subscription.id}: {e}")
                    failed += 1
                    
                    # Notify user about failed renewal
                    if user.telegram_id:
                        error_msg = """⚠️ <b>Не удалось продлить подписку</b>

Произошла ошибка при автопродлении. Пожалуйста, продлите подписку вручную:

/start → 💎 Подписка → Продлить"""
                        await send_telegram_message(user.telegram_id, error_msg)
                
            except Exception as e:
                logger.error(f"Error processing auto-renewal for {subscription.id}: {e}")
                failed += 1
        
        await db.commit()
        
        return {
            "processed": len(subscriptions),
            "renewed": renewed,
            "failed": failed
        }
        
    except Exception as e:
        logger.error(f"Auto-renewal processing failed: {e}")
        return {"error": str(e)}
    finally:
        await db.close()


@celery_app.task(name="worker.tasks.subscriptions.auto_renew")
def auto_renew(subscription_id: str):
    """Auto-renew specific subscription"""
    from worker.celery_app import run_async
    return run_async(auto_renew_async(subscription_id))


async def auto_renew_async(subscription_id: str):
    """Async implementation of auto-renewal for specific subscription"""
    from app.services.payment_service import PaymentService
    from sqlalchemy.orm import selectinload
    
    db = get_worker_session()
    try:
        result = await db.execute(
            select(Subscription).where(
                Subscription.id == subscription_id
            ).options(selectinload(Subscription.user), selectinload(Subscription.plan))
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return {"error": "Subscription not found"}
        
        if not subscription.auto_renew:
            return {"skipped": "Auto-renew not enabled"}
        
        user = subscription.user
        plan = subscription.plan
        
        if not user or not plan:
            return {"error": "Missing user or plan"}
        
        # Create payment for renewal
        payment_service = PaymentService(db)
        
        try:
            payment = await payment_service.create_payment(
                user_id=str(user.id),
                plan_id=str(plan.id),
                amount=float(plan.price),
                description=f"Автопродление: {plan.name}",
                auto_renewal=True,
                subscription_id=subscription_id
            )
            
            logger.info(f"Auto-renewal payment created: {payment.id} for subscription {subscription_id}")
            
            return {
                "status": "payment_created",
                "payment_id": str(payment.id),
                "amount": float(plan.price)
            }
            
        except Exception as e:
            logger.error(f"Auto-renew payment failed for {subscription_id}: {e}")
            return {"error": str(e)}
            
    finally:
        await db.close()


@celery_app.task(name="worker.tasks.subscriptions.toggle_auto_renew")
def toggle_auto_renew(subscription_id: str, enabled: bool):
    """Toggle auto-renewal for subscription"""
    from worker.celery_app import run_async
    return run_async(toggle_auto_renew_async(subscription_id, enabled))


async def toggle_auto_renew_async(subscription_id: str, enabled: bool):
    """Toggle auto-renewal setting"""
    db = get_worker_session()
    try:
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return {"error": "Subscription not found"}
        
        subscription.auto_renew = enabled
        await db.commit()
        
        logger.info(f"Auto-renew {'enabled' if enabled else 'disabled'} for subscription {subscription_id}")
        
        return {"status": "ok", "auto_renew": enabled}
        
    finally:
        await db.close()


@celery_app.task(name="worker.tasks.subscriptions.check_expiring_subscriptions")
def check_expiring_subscriptions():
    """
    Check for subscriptions expiring soon and create alerts.
    Runs daily - creates alerts for subscriptions expiring in 1 day without auto-renew.
    """
    from worker.celery_app import run_async
    return run_async(check_expiring_subscriptions_async())


async def check_expiring_subscriptions_async():
    """Async implementation of expiring subscriptions check"""
    db = get_worker_session()
    try:
        # Find subscriptions expiring in next 24 hours without auto-renew
        tomorrow = datetime.utcnow() + timedelta(days=1)
        now = datetime.utcnow()
        
        result = await db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at > now,
                Subscription.expires_at <= tomorrow,
                Subscription.auto_renew == False
            )
        )
        expiring = result.scalars().all()
        
        count = len(expiring)
        if count > 0:
            # Create alert about expiring subscriptions
            try:
                from app.models.alert import Alert, AlertSeverity, AlertCategory, AlertStatus
                
                alert = Alert(
                    title=f"{count} подписок истекают завтра",
                    message=f"Без автопродления: {count} пользователей потеряют доступ в течение 24 часов.",
                    severity=AlertSeverity.INFO,
                    category=AlertCategory.SUBSCRIPTION,
                    source="expiration_check",
                    source_id=f"daily_{now.strftime('%Y-%m-%d')}"
                )
                db.add(alert)
                await db.commit()
                logger.info(f"Created alert for {count} expiring subscriptions")
            except Exception as e:
                logger.warning(f"Could not create alert: {e}")
        
        logger.info(f"Found {count} subscriptions expiring in next 24 hours")
        return {"expiring_count": count}
        
    except Exception as e:
        logger.error(f"Error checking expiring subscriptions: {e}")
        return {"error": str(e)}
    finally:
        await db.close()
