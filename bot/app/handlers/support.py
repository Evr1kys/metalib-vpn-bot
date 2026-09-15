"""
Support ticket system - full chat experience for users
Users can enter support chat, send multiple messages, and leave at any time
"""
import asyncio
import json
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import redis.asyncio as aioredis
import httpx

from app.config import settings
from app.keyboards.support import (
    get_support_menu_keyboard,
    get_in_chat_keyboard,
    get_back_to_menu_keyboard
)
from app.utils.messages import get_banner_text
from app.utils.helpers import send_with_banner

logger = logging.getLogger(__name__)
router = Router()


class SupportStates(StatesGroup):
    """Support states"""
    in_chat = State()  # User is in chat mode, all messages go to ticket


# ============= API Client for Support =============

class SupportAPIClient:
    """Support API client"""
    
    def __init__(self):
        self.base_url = settings.api_base_url.rstrip("/")
        self.token = settings.bot_api_token
        
    async def get_or_create_ticket(
        self,
        telegram_user_id: int,
        telegram_username: Optional[str],
        telegram_first_name: Optional[str],
        telegram_last_name: Optional[str],
    ) -> dict:
        """Get active ticket or create new one"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/support/bot/ticket",
                json={
                    "telegram_user_id": telegram_user_id,
                    "telegram_username": telegram_username,
                    "telegram_first_name": telegram_first_name,
                    "telegram_last_name": telegram_last_name,
                },
                headers={
                    "X-Bot-Token": self.token,
                    "Content-Type": "application/json",
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def send_message(
        self,
        telegram_user_id: int,
        text: str,
        telegram_message_id: int
    ) -> dict:
        """Send message to ticket"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/support/bot/message",
                json={
                    "telegram_user_id": telegram_user_id,
                    "text": text,
                    "telegram_message_id": telegram_message_id,
                },
                headers={
                    "X-Bot-Token": self.token,
                    "Content-Type": "application/json",
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_ticket_messages(
        self,
        telegram_user_id: int,
        limit: int = 10
    ) -> list:
        """Get recent messages from ticket"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/support/bot/messages",
                params={
                    "telegram_user_id": telegram_user_id,
                    "limit": limit,
                },
                headers={
                    "X-Bot-Token": self.token,
                }
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json()
    
    async def close_ticket(self, telegram_user_id: int) -> dict:
        """Close user's active ticket"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/support/bot/close",
                json={
                    "telegram_user_id": telegram_user_id,
                },
                headers={
                    "X-Bot-Token": self.token,
                    "Content-Type": "application/json",
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_settings(self) -> dict:
        """Get support settings"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/support/bot/settings",
                headers={
                    "X-Bot-Token": self.token,
                }
            )
            if response.status_code == 404:
                return {
                    "auto_reply_enabled": True,
                    "auto_reply_message": "Спасибо за обращение! Наш специалист ответит вам в ближайшее время.",
                }
            response.raise_for_status()
            return response.json()


support_api = SupportAPIClient()


# ============= Redis Listener for Admin Replies =============

async def start_redis_listener(bot):
    """Start listening for admin replies via Redis"""
    while True:
        try:
            redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            pubsub = redis.pubsub()
            await pubsub.subscribe("support_messages")
            
            logger.info("Started Redis listener for support messages")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        if data.get("type") == "support_reply":
                            telegram_user_id = data.get("telegram_user_id")
                            text = data.get("text")
                            admin_name = data.get("admin_name", "Поддержка")
                            
                            # Format message as chat bubble from support
                            reply_text = (
                                f"👤 <b>{admin_name}</b>\n"
                                f"━━━━━━━━━━━━━━━\n"
                                f"{text}"
                            )
                            
                            # Send to user
                            await bot.send_message(
                                chat_id=telegram_user_id,
                                text=reply_text,
                                parse_mode="HTML"
                            )
                            
                            logger.info(f"Sent support reply to user {telegram_user_id}")
                            
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
                        
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
            await asyncio.sleep(5)  # Retry after delay


# ============= Handlers =============

@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext):
    """Open support menu"""
    await state.clear()
    
    # Try to get existing ticket
    try:
        messages = await support_api.get_ticket_messages(message.from_user.id, limit=1)
        has_active_ticket = len(messages) > 0
    except:
        has_active_ticket = False
    
    text = (
        "🎫 <b>Центр поддержки</b>\n\n"
        "Здесь вы можете связаться с нашей командой поддержки.\n\n"
    )
    
    if has_active_ticket:
        text += "📬 У вас есть активное обращение.\n"
        text += "Нажмите «Открыть чат», чтобы продолжить общение."
    else:
        text += "📭 У вас нет активных обращений.\n"
        text += "Нажмите «Новое обращение», чтобы создать тикет."
    
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_support_menu_keyboard(has_active_ticket)
    )


@router.callback_query(F.data.in_({"support", "support_menu", "open_support", "back_to_support"}))
async def cb_support_menu(callback: CallbackQuery, state: FSMContext):
    """Return to support menu"""
    await state.clear()
    
    # Try to get existing ticket
    try:
        messages = await support_api.get_ticket_messages(callback.from_user.id, limit=1)
        has_active_ticket = len(messages) > 0
    except:
        has_active_ticket = False
    
    text = f""
    text += "<b>🎫 Центр поддержки</b>\n\n"
    text += "Здесь вы можете связаться с нашей командой поддержки.\n\n"
    
    if has_active_ticket:
        text += "📬 У вас есть активное обращение.\n"
        text += "Нажмите «Открыть чат», чтобы продолжить общение."
    else:
        text += "📭 У вас нет активных обращений.\n"
        text += "Нажмите «Новое обращение», чтобы создать тикет."
    
    await send_with_banner(
        callback.message,
        text,
        reply_markup=get_support_menu_keyboard(has_active_ticket)
    )
    await callback.answer()


@router.callback_query(F.data == "new_ticket")
async def cb_new_ticket(callback: CallbackQuery, state: FSMContext):
    """Create new ticket and enter chat"""
    try:
        # Create or get existing ticket
        ticket = await support_api.get_or_create_ticket(
            telegram_user_id=callback.from_user.id,
            telegram_username=callback.from_user.username,
            telegram_first_name=callback.from_user.first_name,
            telegram_last_name=callback.from_user.last_name,
        )
        
        # Enter chat mode
        await state.set_state(SupportStates.in_chat)
        
        # Get settings
        settings_data = await support_api.get_settings()
        auto_reply = settings_data.get(
            "auto_reply_message",
            "Здравствуйте! Опишите вашу проблему, и мы ответим в ближайшее время."
        )
        
        await send_with_banner(
            callback.message,
            f"<b>💬 Чат с поддержкой</b>\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>Поддержка</b>\n"
            f"{auto_reply}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"<i>Напишите ваше сообщение...</i>",
            reply_markup=get_in_chat_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        await send_with_banner(
            callback.message,
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_back_to_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "open_chat")
async def cb_open_chat(callback: CallbackQuery, state: FSMContext):
    """Open existing chat"""
    try:
        # Get recent messages
        messages = await support_api.get_ticket_messages(callback.from_user.id, limit=5)
        
        if not messages:
            await callback.answer("Нет активных обращений", show_alert=True)
            return
        
        # Enter chat mode
        await state.set_state(SupportStates.in_chat)
        
        # Build chat history
        chat_text = "💬 <b>Чат с поддержкой</b>\n\n"
        
        # Show last few messages (reversed to show oldest first)
        for msg in reversed(messages[-5:]):
            sender = "Вы" if msg.get("sender_type") == "user" else "Поддержка"
            icon = "👤" if msg.get("sender_type") != "user" else "👤"
            text = msg.get("text", "")[:200]  # Limit text length
            chat_text += f"{icon} <b>{sender}</b>\n{text}\n━━━━━━━━━━━━━━━\n"
        
        chat_text += "\n<i>Напишите ваше сообщение...</i>"
        
        await send_with_banner(
            callback.message,
            chat_text,
            reply_markup=get_in_chat_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error opening chat: {e}")
        await send_with_banner(
            callback.message,
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_back_to_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "leave_chat")
async def cb_leave_chat(callback: CallbackQuery, state: FSMContext):
    """Leave chat but keep ticket open"""
    await state.clear()
    
    await send_with_banner(
        callback.message,
        "✅ <b>Вы вышли из чата</b>\n\n"
        "Ваше обращение остаётся открытым.\n"
        "Вы получите уведомление, когда поддержка ответит.\n\n"
        "Чтобы вернуться в чат, используйте /support",
        reply_markup=get_back_to_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "close_ticket")
async def cb_close_ticket(callback: CallbackQuery, state: FSMContext):
    """Close the ticket"""
    try:
        await support_api.close_ticket(callback.from_user.id)
        await state.clear()
        
        await send_with_banner(
            callback.message,
            "✅ <b>Обращение закрыто</b>\n\n"
            "Спасибо за обращение!\n"
            "Если у вас возникнут новые вопросы, создайте новое обращение через /support",
            reply_markup=get_back_to_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error closing ticket: {e}")
        await callback.answer("Ошибка при закрытии обращения", show_alert=True)
    
    await callback.answer()


@router.message(StateFilter(SupportStates.in_chat))
async def handle_chat_message(message: Message, state: FSMContext):
    """Handle message in chat mode"""
    try:
        # Get message text
        text = message.text or message.caption or "[Медиа]"
        
        # Send to backend
        await support_api.send_message(
            telegram_user_id=message.from_user.id,
            text=text,
            telegram_message_id=message.message_id
        )
        
        # Reply to user message with action buttons
        await message.reply(
            "✅",
            reply_markup=get_in_chat_keyboard()
        )
            
    except Exception as e:
        logger.error(f"Error sending chat message: {e}")
        await message.reply(
            "❌ Не удалось отправить сообщение",
            reply_markup=get_in_chat_keyboard()
        )
