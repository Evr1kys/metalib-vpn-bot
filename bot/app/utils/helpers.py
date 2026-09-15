"""Helper utilities for bot"""
import os
from datetime import datetime, timedelta
from aiogram.types import Message, InlineKeyboardMarkup, FSInputFile
from typing import Optional, Dict, Any
from loguru import logger

# Path to banner image
BANNER_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "banner.png")


def format_connection_status(subscription: Dict[str, Any]) -> str:
    """Format beautiful connection status card"""
    if not subscription:
        return "❌ <b>Нет активной подписки</b>\n\nПодключите VPN для безопасного интернета!"
    
    status = subscription.get('status', 'unknown')
    expires_at = subscription.get('expires_at')
    plan_name = subscription.get('plan_name', 'VPN')
    
    # Calculate days left
    days_left = 0
    if expires_at:
        try:
            exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            days_left = (exp_date - datetime.now(exp_date.tzinfo)).days
        except:
            pass
    
    # Status indicators
    if status == 'active' and days_left > 0:
        status_emoji = "🟢"
        status_text = "Активна"
        progress = min(100, max(0, days_left / 30 * 100))
        progress_bar = generate_progress_bar(progress)
    elif days_left <= 3 and days_left > 0:
        status_emoji = "🟡"
        status_text = "Скоро истекает"
        progress_bar = generate_progress_bar(days_left / 30 * 100)
    else:
        status_emoji = "🔴"
        status_text = "Неактивна"
        progress_bar = generate_progress_bar(0)
    
    text = f"""
{status_emoji} <b>Статус VPN: {status_text}</b>

📋 Тариф: <b>{plan_name}</b>
📅 Осталось: <b>{days_left} дней</b>
{progress_bar}

"""
    
    if days_left <= 3 and days_left > 0:
        text += "⚠️ <i>Не забудьте продлить подписку!</i>\n"
    elif days_left <= 0:
        text += "❌ <i>Подписка истекла. Продлите для восстановления доступа.</i>\n"
    
    return text


def generate_progress_bar(percent: float, width: int = 10) -> str:
    """Generate visual progress bar"""
    filled = int(width * percent / 100)
    empty = width - filled
    
    if percent > 50:
        bar = "🟩" * filled + "⬜" * empty
    elif percent > 20:
        bar = "🟨" * filled + "⬜" * empty
    else:
        bar = "🟥" * filled + "⬜" * empty
    
    return f"[{bar}] {int(percent)}%"


def format_server_recommendation(servers: list) -> str:
    """Format server recommendation based on load"""
    if not servers:
        return "❌ Нет доступных серверов"
    
    # Sort by load (assuming lower is better)
    sorted_servers = sorted(servers, key=lambda s: s.get('current_load', 100))
    
    text = "🚀 <b>Рекомендуемые серверы</b>\n\n"
    
    for i, server in enumerate(sorted_servers[:3], 1):
        load = server.get('current_load', 0)
        location = server.get('location', 'Unknown')
        
        # Load indicator
        if load < 30:
            load_emoji = "🟢"
            load_text = "Низкая"
        elif load < 70:
            load_emoji = "🟡"
            load_text = "Средняя"
        else:
            load_emoji = "🔴"
            load_text = "Высокая"
        
        text += f"{i}. 🌍 <b>{location}</b>\n"
        text += f"   {load_emoji} Нагрузка: {load_text} ({load}%)\n\n"
    
    return text


def calculate_savings(monthly_price: float, period_months: int, actual_price: float) -> Dict[str, Any]:
    """Calculate savings for long-term subscriptions"""
    full_price = monthly_price * period_months
    saved = full_price - actual_price
    percent = (saved / full_price * 100) if full_price > 0 else 0
    
    return {
        "full_price": full_price,
        "actual_price": actual_price,
        "saved": saved,
        "percent": round(percent, 0)
    }


async def send_with_banner(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    delete_previous: bool = True
):
    """
    Send message with banner photo.
    Deletes previous message and sends new one with banner.
    """
    if delete_previous:
        try:
            await message.delete()
        except:
            pass
    
    # Try to send with banner
    if os.path.exists(BANNER_PATH):
        try:
            photo = FSInputFile(BANNER_PATH)
            await message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup
            )
            return
        except Exception as e:
            logger.warning(f"Failed to send banner: {e}")
    
    # Fallback to text
    await message.answer(text, reply_markup=reply_markup)


async def safe_edit_or_resend(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_web_page_preview: bool = False,
    **kwargs
):
    """
    Safely edit message or resend if it contains photo.
    If message has photo (banner), deletes it and sends new text message.
    Otherwise, edits the text.
    """
    try:
        # If message has photo, we must delete and resend
        if message.photo:
            await message.delete()
            await message.answer(text, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
        else:
            # Regular text message - can edit
            await message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
    except Exception:
        # Fallback: delete and resend
        try:
            await message.delete()
            await message.answer(text, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
        except Exception:
            # Last resort: just answer
            await message.answer(text, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
