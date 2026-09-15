"""
Trial handlers for Telegram bot
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from app.api_client import get_api_client
from app.utils.helpers import safe_edit_or_resend

router = Router()


@router.callback_query(F.data == "start_trial")
async def start_trial(callback: CallbackQuery):
    """Start trial period"""
    api = get_api_client()
    
    try:
        # Check if eligible
        status = await api.get("/trial/status", telegram_id=callback.from_user.id)
        
        if status.get("has_trial"):
            trial = status.get("trial", {})
            
            if trial.get("is_active"):
                hours_left = trial.get("hours_left", 0)
                await safe_edit_or_resend(
                    callback.message,
                    f"⏰ <b>У тебя уже есть активный триал!</b>\n\n"
                    f"Осталось: <b>{hours_left} часов</b>\n\n"
                    "Перейди в раздел подписки чтобы получить ключ.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📱 Моя подписка", callback_data="my_subscription")],
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                    ])
                )
            else:
                await safe_edit_or_resend(
                    callback.message,
                    "❌ <b>Ты уже использовал пробный период</b>\n\n"
                    "Пробный период доступен только один раз.\n"
                    "Оформи подписку чтобы продолжить пользоваться VPN!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_subscription")],
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                    ])
                )
            await callback.answer()
            return
        
        if not status.get("can_start_trial"):
            await callback.answer("❌ Пробный период недоступен", show_alert=True)
            return
        
        # Start trial
        result = await api.post("/trial/start", json={"source": "bot"}, telegram_id=callback.from_user.id)
        
        if result.get("success"):
            trial = result.get("trial", {})
            hours = trial.get("hours_left", 24)
            vpn_key = trial.get("vpn_key")
            
            text = "🎉 <b>Пробный период активирован!</b>\n\n"
            text += f"⏰ Время: <b>{hours} часов</b>\n"
            text += "📱 Устройства: <b>1</b>\n\n"
            
            if vpn_key:
                text += f"🔑 <b>Твой VPN-ключ:</b>\n"
                text += f"<code>{vpn_key}</code>\n\n"
                text += "👆 Нажми чтобы скопировать\n\n"
            
            text += "📲 <b>Как подключиться:</b>\n"
            text += "1. Скачай приложение (кнопка ниже)\n"
            text += "2. Скопируй ключ выше\n"
            text += "3. Добавь в приложение\n"
            text += "4. Подключайся!\n\n"
            text += "💡 <i>Понравится — оформи полную подписку со скидкой!</i>"
            
            await safe_edit_or_resend(
                callback.message,
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📲 Скачать приложение", callback_data="download_apps")],
                    [InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_subscription")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
        else:
            await callback.answer(f"❌ {result.get('detail', 'Ошибка')}", show_alert=True)
        
    except Exception as e:
        logger.error(f"Trial start error: {e}")
        await callback.answer("❌ Ошибка. Попробуй позже.", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "trial_info")
async def trial_info(callback: CallbackQuery):
    """Show trial info"""
    api = get_api_client()
    
    try:
        status = await api.get("/trial/status", telegram_id=callback.from_user.id)
        
        text = "⏰ <b>Пробный период — 24 часа бесплатно!</b>\n\n"
        text += "✅ Полный доступ к VPN\n"
        text += "✅ Любой сервер на выбор\n"
        text += "✅ Без ограничения скорости\n"
        text += "✅ Без привязки карты\n\n"
        
        if status.get("has_trial"):
            if status["trial"].get("is_active"):
                text += f"⏳ Твой триал активен! Осталось {status['trial']['hours_left']} ч."
            else:
                text += "❌ Ты уже использовал пробный период."
        else:
            text += "👇 Нажми чтобы активировать:"
        
        buttons = []
        
        if not status.get("has_trial"):
            buttons.append([InlineKeyboardButton(text="🚀 Начать пробный период", callback_data="start_trial")])
        elif status["trial"].get("is_active"):
            buttons.append([InlineKeyboardButton(text="📱 Моя подписка", callback_data="my_subscription")])
        else:
            buttons.append([InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_subscription")])
        
        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")])
        
        await safe_edit_or_resend(
            callback.message,
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        
    except Exception as e:
        logger.error(f"Trial info error: {e}")
        await callback.message.answer("❌ Ошибка загрузки")
    
    await callback.answer()
