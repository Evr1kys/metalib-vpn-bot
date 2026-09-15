"""
Start command handler
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from loguru import logger
import os

from app.api_client import get_api_client
from app.config import settings
from app.keyboards.inline import main_menu_keyboard
from app.utils.messages import format_welcome_message
from app.utils.helpers import safe_edit_or_resend

router = Router()

# Path to banner image
BANNER_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "banner.png")


async def check_referral_enabled() -> bool:
    """Check if referral program is enabled"""
    try:
        api = get_api_client()
        status = await api.get_referral_status()
        return status.get("enabled", True)
    except:
        return True  # Default to enabled on error


async def check_trial_available(telegram_id: int) -> bool:
    """Check if user can start trial"""
    try:
        api = get_api_client()
        status = await api.get(f"/trial/status", telegram_id=telegram_id)
        return status.get("can_start_trial", False) and not status.get("has_trial", False)
    except:
        return True  # Show trial button by default for new users


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    api = get_api_client()
    
    # Log incoming message
    logger.info(f"START command from {message.from_user.id}: {message.text}")
    
    # Extract deep link param
    deep_link_param = None
    if message.text and " " in message.text:
        deep_link_param = message.text.split()[1]
        logger.info(f"Deep link param: {deep_link_param}")
    
    # Handle web auth - authorize website via deeplink
    if deep_link_param and deep_link_param.startswith("auth_"):
        auth_id = deep_link_param[5:]  # Remove 'auth_' prefix
        logger.info(f"Processing web auth: {auth_id}")
        
        # Create user first
        user_data = {
            "telegram_id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "language_code": message.from_user.language_code or "ru",
        }
        try:
            await api.create_or_get_user(**user_data)
            
            # Confirm auth via API
            await api.post(f"/web/auth/confirm/{auth_id}", telegram_id=message.from_user.id)
            
            await message.answer(
                "<b>Авторизация успешна</b>\n\n"
                "Ты авторизован на сайте. Вернись в браузер — страница обновится автоматически.\n\n"
                f"<a href='{settings.website_url}'>{settings.website_url.replace('https://', '')}</a>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="Открыть сайт",
                        url=settings.website_url
                    )],
                    [InlineKeyboardButton(text="Главное меню", callback_data="back_to_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Failed to confirm web auth: {e}")
            await message.answer(
                "❌ <b>Ошибка авторизации</b>\n\n"
                "Сессия истекла или недействительна. Попробуй снова с сайта.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
        return
    
    # Handle web_login - redirect to website with auth
    if deep_link_param == "web_login":
        await message.answer(
            "🌐 <b>Авторизация на сайте</b>\n\n"
            "Ты уже авторизован! Используй эту ссылку для входа на сайт:\n\n"
            f"<code>{settings.website_url}/?tg_id={message.from_user.id}"
            f"&first_name={message.from_user.first_name or ''}"
            f"&username={message.from_user.username or ''}</code>\n\n"
            "Или просто используй кнопку ниже 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🌐 Открыть сайт",
                    url=f"{settings.website_url}/?tg_id={message.from_user.id}&first_name={message.from_user.first_name or ''}&username={message.from_user.username or ''}"
                )],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
        return
    
    # Handle buy deep links
    if deep_link_param and deep_link_param.startswith("buy_"):
        plan_type = deep_link_param[4:]  # Remove 'buy_' prefix
        # Create user first
        user_data = {
            "telegram_id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "language_code": message.from_user.language_code or "ru",
        }
        try:
            await api.create_or_get_user(**user_data)
            
            # Show plans directly
            from app.keyboards.inline import plans_keyboard
            plans = await api.get_plans()
            
            if plans:
                text = """💎 <b>Покупка подписки</b>

Ты перешёл с сайта! Выбери подходящий тариф:"""
                await message.answer(text, reply_markup=plans_keyboard(plans))
            else:
                await message.answer(
                    "❌ Тарифы временно недоступны.\nПопробуй позже!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                    ])
                )
            return
        except Exception as e:
            logger.error(f"Error handling buy deep link: {e}")
    
    # Extract referral code
    referral_code = None
    if deep_link_param and deep_link_param.startswith("ref_"):
        referral_code = deep_link_param
    elif deep_link_param and not deep_link_param.startswith("buy_") and not deep_link_param.startswith("auth_"):
        referral_code = deep_link_param
    
    # Create or get user
    user_data = {
        "telegram_id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "language_code": message.from_user.language_code or "ru",
    }
    
    try:
        user = await api.create_or_get_user(**user_data)
        
        # Check if user is banned
        if user.get("is_banned"):
            await message.answer("❌ Твой аккаунт заблокирован.")
            return
        
        # Check if referral system is enabled
        show_referrals = await check_referral_enabled()
        
        # Check if trial is available
        show_trial = await check_trial_available(message.from_user.id)
        
        # Apply referral code if provided, enabled, and user doesn't have referrer yet
        if referral_code and show_referrals and not user.get("referrer_id"):
            try:
                await api.post(f"/referrals/apply/{referral_code}", telegram_id=message.from_user.id)
                await message.answer(
                    "🎉 <b>Отлично!</b>\n\n"
                    "Ты зарегистрирован по реферальной ссылке!\n"
                    "После первой оплаты твой друг получит <b>+3 дня</b> к подписке 🎁"
                )
            except:
                pass  # Ignore referral errors
        
        # Send welcome message with banner
        welcome_text = format_welcome_message(message.from_user.first_name or "друг")
        
        # Try to send with banner image
        if os.path.exists(BANNER_PATH):
            try:
                photo = FSInputFile(BANNER_PATH)
                await message.answer_photo(
                    photo=photo,
                    caption=welcome_text,
                    reply_markup=main_menu_keyboard(show_referrals=show_referrals, show_trial=show_trial)
                )
                return
            except Exception as e:
                logger.warning(f"Failed to send banner: {e}")
        
        # Fallback to text-only message
        await message.answer(
            welcome_text,
            reply_markup=main_menu_keyboard(show_referrals=show_referrals, show_trial=show_trial)
        )
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка. Попробуй позже или напиши в поддержку @metalib_support"
        )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Back to main menu"""
    await state.clear()
    
    welcome_text = format_welcome_message(callback.from_user.first_name or "друг")
    show_referrals = await check_referral_enabled()
    show_trial = await check_trial_available(callback.from_user.id)
    
    # Always delete current message and send new with banner
    try:
        await callback.message.delete()
    except:
        pass
    
    # Send new message with banner
    if os.path.exists(BANNER_PATH):
        try:
            photo = FSInputFile(BANNER_PATH)
            await callback.message.answer_photo(
                photo=photo,
                caption=welcome_text,
                reply_markup=main_menu_keyboard(show_referrals=show_referrals, show_trial=show_trial)
            )
            await callback.answer()
            return
        except Exception as e:
            logger.warning(f"Failed to send banner: {e}")
    
    # Fallback to text-only
    await callback.message.answer(
        welcome_text,
        reply_markup=main_menu_keyboard(show_referrals=show_referrals, show_trial=show_trial)
    )
    await callback.answer()
