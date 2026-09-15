"""
Telegram logging utility
Send important logs to Telegram channel
"""
import httpx
from app.core.config import settings
from app.core.logging import logger as app_logger
from typing import Optional


async def send_log_to_telegram(
    message: str,
    level: str = "INFO",
    parse_mode: str = "HTML"
):
    """
    Send log message to Telegram channel
    
    Args:
        message: Log message
        level: Log level (INFO, WARNING, ERROR, CRITICAL)
        parse_mode: Message parse mode (HTML, Markdown)
    """
    if not settings.telegram_log_channel_id:
        return
    
    try:
        # Add emoji based on level
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🚨",
            "SUCCESS": "✅"
        }
        
        emoji = emoji_map.get(level, "📝")
        
        # Format message
        formatted_message = f"{emoji} <b>{level}</b>\n\n{message}"
        
        # Send to channel
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "chat_id": settings.telegram_log_channel_id,
                    "text": formatted_message,
                    "parse_mode": parse_mode,
                    "disable_notification": level in ["INFO", "SUCCESS"]
                },
                timeout=5.0
            )
            
            if response.status_code != 200:
                app_logger.warning(f"Failed to send log to Telegram: {response.text}")
    
    except Exception as e:
        app_logger.warning(f"Error sending log to Telegram: {e}")


async def log_payment_event(
    event: str,
    payment_id: str,
    user_id: str,
    amount: float,
    currency: str,
    status: str
):
    """
    Log payment event to Telegram channel
    
    Args:
        event: Event name (created, succeeded, failed)
        payment_id: Payment ID
        user_id: User ID
        amount: Payment amount
        currency: Currency code
        status: Payment status
    """
    level_map = {
        "created": "INFO",
        "succeeded": "SUCCESS",
        "failed": "ERROR",
        "pending": "INFO"
    }
    
    level = level_map.get(event, "INFO")
    
    message = f"""<b>💳 Payment {event.upper()}</b>

<b>ID:</b> <code>{payment_id}</code>
<b>User:</b> <code>{user_id}</code>
<b>Amount:</b> {amount} {currency}
<b>Status:</b> {status}
"""
    
    await send_log_to_telegram(message, level)


async def log_subscription_event(
    event: str,
    subscription_id: str,
    user_id: str,
    plan_name: str,
    expires_at: Optional[str] = None
):
    """
    Log subscription event to Telegram channel
    
    Args:
        event: Event name (created, activated, expired, cancelled)
        subscription_id: Subscription ID
        user_id: User ID
        plan_name: Plan name
        expires_at: Expiration date
    """
    level_map = {
        "created": "INFO",
        "activated": "SUCCESS",
        "expired": "WARNING",
        "cancelled": "WARNING"
    }
    
    level = level_map.get(event, "INFO")
    
    message = f"""<b>📱 Subscription {event.upper()}</b>

<b>ID:</b> <code>{subscription_id}</code>
<b>User:</b> <code>{user_id}</code>
<b>Plan:</b> {plan_name}
"""
    
    if expires_at:
        message += f"<b>Expires:</b> {expires_at}\n"
    
    await send_log_to_telegram(message, level)


async def log_error(
    component: str,
    error_message: str,
    details: Optional[str] = None
):
    """
    Log error to Telegram channel
    
    Args:
        component: Component name (backend, bot, worker, agent)
        error_message: Error message
        details: Additional details
    """
    message = f"""<b>🐛 Error in {component}</b>

<b>Message:</b> {error_message}
"""
    
    if details:
        message += f"\n<b>Details:</b>\n<code>{details}</code>"
    
    await send_log_to_telegram(message, "ERROR")


async def log_user_event(
    event: str,
    user_id: int,
    username: Optional[str] = None,
    details: Optional[str] = None
):
    """
    Log user event to Telegram channel
    
    Args:
        event: Event name (registered, blocked, unblocked)
        user_id: Telegram user ID
        username: Telegram username
        details: Additional details
    """
    message = f"""<b>👤 User {event.upper()}</b>

<b>ID:</b> <code>{user_id}</code>
"""
    
    if username:
        message += f"<b>Username:</b> @{username}\n"
    
    if details:
        message += f"\n{details}"
    
    await send_log_to_telegram(message, "INFO")


async def send_user_notification(
    telegram_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: dict = None
) -> bool:
    """
    Send notification directly to user in Telegram
    
    Args:
        telegram_id: User's Telegram ID
        text: Message text
        parse_mode: Message parse mode (HTML, Markdown)
        reply_markup: Optional inline keyboard
    
    Returns:
        True if sent successfully
    """
    try:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        
        payload = {
            "chat_id": telegram_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 200:
                app_logger.info(f"Notification sent to user {telegram_id}")
                return True
            else:
                app_logger.warning(f"Failed to send notification to {telegram_id}: {response.text}")
                return False
    
    except Exception as e:
        app_logger.warning(f"Error sending notification to {telegram_id}: {e}")
        return False
