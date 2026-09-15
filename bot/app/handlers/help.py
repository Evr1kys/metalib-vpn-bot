"""
Help and support handlers
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from app.keyboards.inline import back_button
from app.utils.messages import format_help_message
from app.utils.helpers import safe_edit_or_resend

router = Router()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Show help information"""
    text = format_help_message()
    
    await safe_edit_or_resend(callback.message, 
        text,
        reply_markup=back_button(),
        disable_web_page_preview=True
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    text = format_help_message()
    
    await message.answer(
        text,
        reply_markup=back_button(),
        disable_web_page_preview=True
    )


@router.message(Command("support"))
async def cmd_support(message: Message):
    """Handle /support command"""
    from app.utils.messages import get_banner_text
    
    text = f"""{get_banner_text()}
<b>📞 Связаться с поддержкой</b>

Мы всегда рады помочь! 

<b>Telegram:</b> @metalib_support
<b>Время ответа:</b> до 24 часов

Напиши нам, если есть вопросы! 💬"""
    
    await message.answer(text)
