"""
Notification Tasks
"""
from datetime import datetime, timedelta
from sqlalchemy import select
from loguru import logger
import httpx

from worker.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_worker_session
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User


@celery_app.task(name="worker.tasks.notifications.send_expiry_notifications")
def send_expiry_notifications():
    """Send notifications for subscriptions expiring soon"""
    from worker.celery_app import run_async
    return run_async(send_expiry_notifications_async())


async def send_expiry_notifications_async():
    """Async implementation of expiry notifications"""
    db = get_worker_session()
    try:
        # Get subscriptions expiring in 3 days
        cutoff_date = datetime.utcnow() + timedelta(days=3)
        
        result = await db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at <= cutoff_date,
                Subscription.expires_at > datetime.utcnow()
            )
        )
        subscriptions = result.scalars().all()
        
        logger.info(f"Sending expiry notifications for {len(subscriptions)} subscriptions")
        
        sent_count = 0
        for subscription in subscriptions:
            try:
                # Get user
                result = await db.execute(
                    select(User).where(User.id == subscription.user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.telegram_id:
                    continue
                
                # Calculate days remaining
                days_remaining = (subscription.expires_at - datetime.utcnow()).days
                
                # Different messages based on days remaining
                if days_remaining <= 1:
                    urgency = "🔴"
                    urgency_text = "СЕГОДНЯ" if days_remaining < 1 else "ЗАВТРА"
                    message = (
                        f"<b>▸ MetaLib VPN</b>\n\n"
                        f"{urgency} <b>Подписка истекает {urgency_text}!</b>\n\n"
                        f"📅 Срок действия: {subscription.expires_at.strftime('%d.%m.%Y')}\n\n"
                        f"Продлите подписку, чтобы не потерять доступ к VPN."
                    )
                else:
                    urgency = "⚠️"
                    message = (
                        f"<b>▸ MetaLib VPN</b>\n\n"
                        f"{urgency} <b>Подписка скоро истекает</b>\n\n"
                        f"⏳ Осталось дней: <b>{days_remaining}</b>\n"
                        f"📅 Срок действия: {subscription.expires_at.strftime('%d.%m.%Y')}\n\n"
                        f"Продлите подписку заранее для бесперебойного доступа."
                    )
                
                # Send notification via bot with buttons
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "💎 Продлить подписку", "callback_data": "buy_subscription"}],
                        [{"text": "📊 Моя подписка", "callback_data": "my_subscription"}],
                        [{"text": "🔑 Мой VPN", "callback_data": "my_vpn"}]
                    ]
                }
                
                await send_telegram_notification(
                    telegram_id=user.telegram_id,
                    message=message,
                    reply_markup=keyboard
                )
                
                sent_count += 1
                logger.info(f"Expiry notification sent to user {user.id}")
            
            except Exception as e:
                logger.error(f"Failed to send expiry notification for subscription {subscription.id}: {e}")
        
        return {"sent": sent_count}
    finally:
        await db.close()


@celery_app.task(name="worker.tasks.notifications.send_payment_notification")
def send_payment_notification(user_id: str, payment_id: str, status: str):
    """Send payment status notification"""
    from worker.celery_app import run_async
    return run_async(send_payment_notification_async(user_id, payment_id, status))


async def send_payment_notification_async(user_id: str, payment_id: str, status: str):
    """Async implementation of payment notification"""
    db = get_worker_session()
    try:
        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.telegram_id:
            return {"error": "User not found"}
        
        # Prepare message and keyboard based on status
        keyboard = None
        if status == "succeeded":
            message = (
                "<b>▸ MetaLib VPN</b>\n\n"
                "✅ <b>Оплата успешна!</b>\n\n"
                "Ваша подписка активирована и готова к использованию.\n\n"
                "Перейдите в раздел «Мой VPN» чтобы получить ключ подключения."
            )
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔑 Мой VPN", "callback_data": "my_vpn"}],
                    [{"text": "📊 Моя подписка", "callback_data": "my_subscription"}],
                    [{"text": "🏠 Главное меню", "callback_data": "back_to_main"}]
                ]
            }
        elif status == "failed":
            message = (
                f"<b>▸ MetaLib VPN</b>\n\n"
                f"❌ <b>Оплата не прошла</b>\n\n"
                f"Попробуйте ещё раз или свяжитесь с поддержкой.\n\n"
                f"ID платежа: <code>{payment_id}</code>"
            )
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💎 Попробовать снова", "callback_data": "buy_subscription"}],
                    [{"text": "💬 Поддержка", "url": "https://t.me/metalib_support"}]
                ]
            }
        else:
            message = f"<b>▸ MetaLib VPN</b>\n\nℹ️ Статус оплаты: {status}"
        
        # Send notification
        await send_telegram_notification(
            telegram_id=user.telegram_id,
            message=message,
            reply_markup=keyboard
        )
        
        logger.info(f"Payment notification sent to user {user_id}")
        
        return {"status": "sent"}
    
    except Exception as e:
        logger.error(f"Failed to send payment notification: {e}")
        return {"error": str(e)}
    finally:
        await db.close()


async def send_telegram_notification(telegram_id: int, message: str, reply_markup: dict = None) -> dict:
    """
    Send notification via Telegram Bot API
    
    Args:
        telegram_id: User's Telegram ID
        message: Message text (HTML formatted)
        reply_markup: Optional inline keyboard markup
    
    Returns:
        dict with success status and error if any
    """
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    
    payload = {
        "chat_id": telegram_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            result = response.json()
            
            if not result.get("ok"):
                error_code = result.get("error_code")
                description = result.get("description", "Unknown error")
                
                # User blocked the bot or chat not found
                if error_code in (403, 400):
                    logger.warning(f"Cannot send to {telegram_id}: {description}")
                    return {"success": False, "error": description, "blocked": True}
                
                logger.error(f"Telegram API error for {telegram_id}: {description}")
                return {"success": False, "error": description}
            
            return {"success": True, "message_id": result.get("result", {}).get("message_id")}
            
    except httpx.TimeoutException:
        logger.error(f"Timeout sending notification to {telegram_id}")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        logger.error(f"Failed to send notification to {telegram_id}: {e}")
        return {"success": False, "error": str(e)}
