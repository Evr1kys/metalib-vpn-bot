"""
Admin handlers for bot management
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import httpx
from loguru import logger

from app.config import settings
from app.i18n import t

router = Router()

# Admin IDs
ADMIN_IDS = [1058835707]  # Add your admin Telegram IDs here


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS


async def get_alerts_from_api(status: str = "active", limit: int = 10):
    """Fetch alerts from backend API"""
    try:
        async with httpx.AsyncClient() as client:
            # Use internal API call
            response = await client.get(
                f"{settings.api_base_url}/admin/alerts/",
                params={"status_filter": status, "limit": limit},
                headers={"X-Internal-Key": settings.internal_api_key} if hasattr(settings, 'internal_api_key') else {},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {e}")
    return []


async def get_alert_stats():
    """Fetch alert statistics from API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.api_base_url}/admin/alerts/stats",
                headers={"X-Internal-Key": settings.internal_api_key} if hasattr(settings, 'internal_api_key') else {},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch alert stats: {e}")
    return None


async def resolve_alert(alert_id: str):
    """Resolve alert via API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.api_base_url}/admin/alerts/{alert_id}/resolve",
                headers={"X-Internal-Key": settings.internal_api_key} if hasattr(settings, 'internal_api_key') else {},
                json={"note": "Resolved via Telegram bot"},
                timeout=10
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
    return False


@router.message(Command("alerts"))
async def cmd_alerts(message: Message):
    """Show active alerts for admins"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к этой команде")
        return
    
    # Get stats
    stats = await get_alert_stats()
    
    if not stats:
        await message.answer("❌ Не удалось получить статистику алертов")
        return
    
    # Build message
    text = "🔔 <b>Системные алерты</b>\n\n"
    
    if stats.get('active_total', 0) == 0:
        text += "✅ Нет активных алертов!\n"
    else:
        text += f"📊 <b>Статистика:</b>\n"
        text += f"├ 🔴 Критических: {stats.get('critical_active', 0)}\n"
        text += f"├ 🟠 Ошибок: {stats.get('error_active', 0)}\n"
        text += f"├ 🟡 Предупреждений: {stats.get('warning_active', 0)}\n"
        text += f"└ 📋 Всего активных: {stats.get('active_total', 0)}\n"
        text += f"\n📅 За 24 часа: {stats.get('last_24h', 0)}\n"
    
    # Build keyboard
    builder = InlineKeyboardBuilder()
    
    if stats.get('active_total', 0) > 0:
        builder.button(text="📋 Показать алерты", callback_data="alerts:show")
        builder.button(text="✅ Решить все", callback_data="alerts:resolve_all")
    
    builder.button(text="🔄 Обновить", callback_data="alerts:refresh")
    builder.adjust(2, 1)
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "alerts:show")
async def show_alerts_list(callback: CallbackQuery):
    """Show list of active alerts"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    alerts = await get_alerts_from_api("active", 10)
    
    if not alerts:
        await callback.answer("Нет активных алертов", show_alert=True)
        return
    
    # Severity emoji map
    severity_emoji = {
        "critical": "🚨",
        "error": "🔴",
        "warning": "⚠️",
        "info": "ℹ️"
    }
    
    text = "📋 <b>Активные алерты:</b>\n\n"
    
    builder = InlineKeyboardBuilder()
    
    for i, alert in enumerate(alerts[:10], 1):
        emoji = severity_emoji.get(alert.get('severity', 'info'), '📢')
        title = alert.get('title', 'Без названия')[:40]
        text += f"{i}. {emoji} <b>{title}</b>\n"
        
        # Short message preview
        msg = alert.get('message', '')[:50]
        if len(alert.get('message', '')) > 50:
            msg += "..."
        text += f"   <i>{msg}</i>\n\n"
        
        # Add resolve button for each alert
        alert_id = alert.get('id', '')
        if alert_id:
            builder.button(
                text=f"✅ {i}",
                callback_data=f"alerts:resolve:{alert_id}"
            )
    
    # Adjust buttons in rows of 5
    builder.adjust(5)
    builder.row()
    builder.button(text="« Назад", callback_data="alerts:refresh")
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "alerts:refresh")
async def refresh_alerts(callback: CallbackQuery):
    """Refresh alerts stats"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    stats = await get_alert_stats()
    
    if not stats:
        await callback.answer("❌ Ошибка получения данных", show_alert=True)
        return
    
    text = "🔔 <b>Системные алерты</b>\n\n"
    
    if stats.get('active_total', 0) == 0:
        text += "✅ Нет активных алертов!\n"
    else:
        text += f"📊 <b>Статистика:</b>\n"
        text += f"├ 🔴 Критических: {stats.get('critical_active', 0)}\n"
        text += f"├ 🟠 Ошибок: {stats.get('error_active', 0)}\n"
        text += f"├ 🟡 Предупреждений: {stats.get('warning_active', 0)}\n"
        text += f"└ 📋 Всего активных: {stats.get('active_total', 0)}\n"
        text += f"\n📅 За 24 часа: {stats.get('last_24h', 0)}\n"
    
    builder = InlineKeyboardBuilder()
    
    if stats.get('active_total', 0) > 0:
        builder.button(text="📋 Показать алерты", callback_data="alerts:show")
        builder.button(text="✅ Решить все", callback_data="alerts:resolve_all")
    
    builder.button(text="🔄 Обновить", callback_data="alerts:refresh")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer("✅ Обновлено")


@router.callback_query(F.data.startswith("alerts:resolve:"))
async def resolve_single_alert(callback: CallbackQuery):
    """Resolve a single alert"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    
    if not callback.data:
        await callback.answer()
        return
    
    alert_id = callback.data.split(":")[-1]
    
    success = await resolve_alert(alert_id)
    
    if success:
        await callback.answer("✅ Алерт решён", show_alert=True)
        # Refresh the list
        await show_alerts_list(callback)
    else:
        await callback.answer("❌ Ошибка при решении алерта", show_alert=True)


@router.callback_query(F.data == "alerts:resolve_all")
async def resolve_all_alerts(callback: CallbackQuery):
    """Resolve all active alerts"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.api_base_url}/admin/alerts/resolve-all",
                headers={"X-Internal-Key": settings.internal_api_key} if hasattr(settings, 'internal_api_key') else {},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                count = result.get('resolved_count', 0)
                await callback.answer(f"✅ Решено {count} алертов", show_alert=True)
                # Refresh stats
                await refresh_alerts(callback)
            else:
                await callback.answer("❌ Ошибка при решении", show_alert=True)
    except Exception as e:
        logger.error(f"Failed to resolve all alerts: {e}")
        await callback.answer("❌ Ошибка подключения", show_alert=True)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Show system stats for admins"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к этой команде")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.api_base_url}/admin/dashboard",
                headers={"X-Internal-Key": settings.internal_api_key} if hasattr(settings, 'internal_api_key') else {},
                timeout=10
            )
            
            if response.status_code == 200:
                stats = response.json()
                
                text = "📊 <b>Статистика системы</b>\n\n"
                text += f"👥 Пользователей: {stats.get('total_users', 0)}\n"
                text += f"✅ Активных подписок: {stats.get('active_subscriptions', 0)}\n"
                text += f"💰 Доход: {stats.get('total_revenue', 0):,.0f} ₽\n"
                text += f"🖥 Серверов: {stats.get('total_servers', 0)}\n"
                
                await message.answer(text, parse_mode="HTML")
            else:
                await message.answer("❌ Не удалось получить статистику")
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await message.answer("❌ Ошибка подключения к API")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    """Send broadcast message to all users"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к этой команде")
        return
    
    # Get text after command
    text = message.text.replace("/broadcast", "").strip()
    
    if not text:
        await message.answer(
            "📢 <b>Рассылка</b>\n\n"
            "Использование:\n"
            "<code>/broadcast Ваше сообщение</code>\n\n"
            "Сообщение будет отправлено всем пользователям бота.",
            parse_mode="HTML"
        )
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data=f"broadcast:confirm")
    builder.button(text="❌ Отмена", callback_data="broadcast:cancel")
    
    preview = f"📢 <b>Предпросмотр рассылки:</b>\n\n{text}\n\n⚠️ Подтвердите отправку"
    
    # Store message in state or use temp storage
    # Store broadcast text in message data attribute for later access
    await message.answer(preview, reply_markup=builder.as_markup(), parse_mode="HTML")


# Store pending broadcast messages (in production use Redis)
_pending_broadcasts = {}


@router.callback_query(F.data.startswith("broadcast:"))
async def handle_broadcast_callback(callback: CallbackQuery):
    """Handle broadcast confirmation/cancellation"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    
    if not callback.data:
        await callback.answer()
        return
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    action = callback.data.split(":")[1]
    
    if action == "cancel":
        await callback.message.edit_text("❌ Рассылка отменена")
        await callback.answer("Отменено")
        return
    
    if action == "confirm":
        # Extract broadcast text from the preview message
        preview_text = callback.message.text or callback.message.caption or ""
        # Remove the prefix and suffix
        if "Предпросмотр рассылки:" in preview_text:
            broadcast_text = preview_text.split("Предпросмотр рассылки:")[1]
            broadcast_text = broadcast_text.replace("⚠️ Подтвердите отправку", "").strip()
        else:
            broadcast_text = preview_text
        
        if not broadcast_text:
            await callback.answer("Ошибка: текст не найден", show_alert=True)
            return
        
        await callback.message.edit_text("📤 Отправка рассылки...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.api_base_url}/api/v1/broadcast",
                    json={"message": broadcast_text},
                    headers={
                        "X-Bot-Token": settings.bot_api_token
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    sent = result.get("sent", 0)
                    failed = result.get("failed", 0)
                    await callback.message.edit_text(
                        f"✅ <b>Рассылка завершена</b>\n\n"
                        f"📨 Отправлено: {sent}\n"
                        f"❌ Ошибок: {failed}",
                        parse_mode="HTML"
                    )
                else:
                    await callback.message.edit_text("❌ Ошибка при отправке рассылки")
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
        
        await callback.answer()


@router.message(Command("backup"))
async def cmd_backup(message: Message):
    """Trigger manual backup"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к этой команде")
        return
    
    await message.answer("🔄 Запускаю резервное копирование...")
    
    # This would need to trigger the backup script
    # For now, just send a message
    await message.answer(
        "ℹ️ Для запуска бэкапа выполните на сервере:\n\n"
        "<code>docker exec metalib_backend /app/scripts/backup.sh</code>",
        parse_mode="HTML"
    )
