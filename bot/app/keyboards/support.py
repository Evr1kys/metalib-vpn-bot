"""
Support keyboards for ticket system
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_support_menu_keyboard(has_active_ticket: bool = False) -> InlineKeyboardMarkup:
    """Get main support menu keyboard"""
    buttons = []
    
    if has_active_ticket:
        buttons.append([
            InlineKeyboardButton(text="💬 Открыть чат", callback_data="open_chat")
        ])
        buttons.append([
            InlineKeyboardButton(text="✅ Закрыть обращение", callback_data="close_ticket")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="📝 Новое обращение", callback_data="new_ticket")
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_in_chat_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for when user is in chat"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚪 Выйти из чата", callback_data="leave_chat"),
            InlineKeyboardButton(text="✅ Закрыть обращение", callback_data="close_ticket"),
        ],
    ])


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Get back to menu keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Центр поддержки", callback_data="support_menu")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")],
    ])
