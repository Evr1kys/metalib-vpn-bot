"""
Referral system handler - Beautiful and functional
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from loguru import logger

from app.api_client import get_api_client
from app.utils.helpers import safe_edit_or_resend
from app.utils.messages import (
    format_referral_program,
    format_share_referral_text,
    format_no_referrals,
    format_referrals_list
)

router = Router()


async def check_referral_enabled() -> bool:
    """Check if referral program is enabled"""
    try:
        api = get_api_client()
        status = await api.get_referral_status()
        return status.get("enabled", True)
    except:
        return True


@router.callback_query(F.data == "referral_program")
async def show_referral_program(callback: CallbackQuery):
    """Show referral program info"""
    api = get_api_client()
    
    # Check if enabled
    if not await check_referral_enabled():
        await callback.answer("❌ Реферальная программа временно недоступна", show_alert=True)
        return
    
    try:
        # Get referral info from API
        referral_info = await api.get_referral_stats(callback.from_user.id)
        
        referral_code = referral_info.get("referral_code", "")
        
        # Generate referral link
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"
        
        stats = {
            "referrals_count": referral_info.get("referrals_count", 0),
            "completed_count": referral_info.get("completed_count", 0),
            "total_bonus_days": referral_info.get("total_bonus_days", 0)
        }
        
        text = format_referral_program(referral_code, referral_link, stats)
        
        # Share text for inline query
        share_text = format_share_referral_text(referral_link, bot_username)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="👥 Мои рефералы", callback_data="my_referrals")
        )
        builder.row(
            InlineKeyboardButton(
                text="📤 Поделиться ссылкой", 
                switch_inline_query=share_text
            )
        )
        builder.row(
            InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_ref:{referral_code}")
        )
        builder.row(
            InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
        )
        
        await safe_edit_or_resend(callback.message, 
            text,
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Referral program error: {e}")
        await callback.answer("❌ Ошибка загрузки. Попробуй позже.", show_alert=True)


@router.callback_query(F.data.startswith("copy_ref:"))
async def copy_referral_link(callback: CallbackQuery):
    """Show referral link for copying"""
    referral_code = callback.data.split(":")[1]
    bot_info = await callback.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={referral_code}"
    
    await callback.answer(
        f"🔗 Ссылка:\n{referral_link}",
        show_alert=True
    )


@router.callback_query(F.data == "my_referrals")
async def show_my_referrals(callback: CallbackQuery):
    """Show user's referrals list"""
    api = get_api_client()
    
    try:
        referral_info = await api.get_referral_stats(callback.from_user.id)
        referrals = referral_info.get("referrals", [])
        
        if not referrals:
            text = format_no_referrals()
        else:
            text = format_referrals_list(referrals)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="« Назад к программе", callback_data="referral_program")
        )
        
        await safe_edit_or_resend(callback.message, 
            text,
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"My referrals error: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)


@router.message(Command("ref"))
async def cmd_referral(message: Message):
    """Show referral program (command shortcut)"""
    api = get_api_client()
    
    try:
        referral_info = await api.get_referral_stats(message.from_user.id)
        referral_code = referral_info.get("referral_code", "")
        
        bot_info = await message.bot.get_me()
        bot_username = bot_info.username
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"
        
        stats = {
            "referrals_count": referral_info.get("referrals_count", 0),
            "completed_count": referral_info.get("completed_count", 0),
            "total_earned": referral_info.get("total_earned", 0)
        }
        
        text = format_referral_program(referral_code, referral_link, stats)
        share_text = format_share_referral_text(referral_link, bot_username)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="👥 Мои рефералы", callback_data="my_referrals")
        )
        builder.row(
            InlineKeyboardButton(
                text="📤 Поделиться ссылкой",
                switch_inline_query=share_text
            )
        )
        builder.row(
            InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_ref:{referral_code}")
        )
        builder.row(
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
        )
        
        await message.answer(text, reply_markup=builder.as_markup())
        
    except Exception as e:
        logger.error(f"Ref command error: {e}")
        await message.answer("❌ Ошибка. Попробуй позже.")


@router.inline_query()
async def inline_referral_share(inline_query: InlineQuery):
    """Handle inline query for sharing referral link"""
    api = get_api_client()
    
    try:
        # Get user's referral info
        referral_info = await api.get_referral_stats(inline_query.from_user.id)
        referral_code = referral_info.get("referral_code", "")
        
        # Generate referral link
        bot_info = await inline_query.bot.get_me()
        bot_username = bot_info.username
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"
        
        # Create share message
        share_text = format_share_referral_text(referral_link, bot_username)
        
        # Create inline result
        result = InlineQueryResultArticle(
            id="referral_share",
            title="🛡️ Поделиться MetaLib VPN",
            description="Пригласи друга и получай 10% с его оплат!",
            input_message_content=InputTextMessageContent(
                message_text=share_text,
                parse_mode="HTML"
            ),
            thumbnail_url="https://telegram.org/img/t_logo.png"
        )
        
        await inline_query.answer([result], cache_time=60)
        
    except Exception as e:
        logger.error(f"Inline query error: {e}")
        # Return empty result on error
        await inline_query.answer([], cache_time=10)
