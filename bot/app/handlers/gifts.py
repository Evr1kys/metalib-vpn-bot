"""
Gift Certificate handlers for Telegram bot
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from app.api_client import get_api_client
from app.utils.helpers import safe_edit_or_resend

router = Router()


class GiftStates(StatesGroup):
    entering_code = State()
    entering_recipient = State()
    entering_message = State()


# ============== Gifts Menu ==============

@router.callback_query(F.data == "gifts_menu")
async def gifts_menu(callback: CallbackQuery):
    """Show gifts menu"""
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
        
    text = """🎁 <b>Подарочные сертификаты</b>

Подари VPN другу или активируй полученный подарок!

<b>Как это работает:</b>
1. Выбери тариф для подарка
2. Оплати сертификат
3. Получи код и отправь другу
4. Друг активирует код в боте

💡 <i>Отличный подарок для тех, кто ценит приватность!</i>"""
    
    await safe_edit_or_resend(
        callback.message,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Подарить VPN", callback_data="buy_gift")],
            [InlineKeyboardButton(text="📥 Активировать код", callback_data="redeem_gift")],
            [InlineKeyboardButton(text="📋 Мои сертификаты", callback_data="my_gifts")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ])
    )
    await callback.answer()


# ============== Redeem Gift ==============

@router.callback_query(F.data == "redeem_gift")
async def start_redeem_gift(callback: CallbackQuery, state: FSMContext):
    """Start gift redemption process"""
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    await state.set_state(GiftStates.entering_code)
    
    await safe_edit_or_resend(
        callback.message,
        "🎁 <b>Активация подарочного сертификата</b>\n\n"
        "Введи код сертификата в формате:\n"
        "<code>GIFT-XXXX-XXXX-XXXX</code>\n\n"
        "Код можно найти в сообщении от дарителя.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
        ])
    )
    await callback.answer()


@router.message(GiftStates.entering_code)
async def process_gift_code(message: Message, state: FSMContext):
    """Process gift code"""
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст")
        return
    
    code = message.text.strip().upper()
    
    api = get_api_client()
    
    try:
        # Check if code is valid
        check_result = await api.get(f"/gifts/check/{code}")
        
        if not check_result.get("valid"):
            await message.answer(
                f"❌ {check_result.get('message', 'Недействительный код')}\n\n"
                "Проверь код и попробуй снова.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="redeem_gift")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Redeem the gift
        result = await api.post("/gifts/redeem", json={"code": code})
        
        if result.get("success"):
            sender = result.get("sender_name", "Аноним")
            gift_message = result.get("gift_message", "")
            plan_name = result.get("plan_name", "VPN")
            
            text = f"🎉 <b>Поздравляем!</b>\n\n"
            text += f"Ты активировал подарочный сертификат!\n\n"
            text += f"📦 <b>Тариф:</b> {plan_name}\n"
            text += f"👤 <b>От кого:</b> {sender}\n"
            
            if gift_message:
                text += f"\n💬 <b>Сообщение:</b>\n<i>{gift_message}</i>\n"
            
            text += "\nТвой VPN уже активирован! Перейди в раздел 'Подписка' для получения ключа."
            
            await message.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📱 Моя подписка", callback_data="my_subscription")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
        else:
            await message.answer(
                f"❌ Ошибка: {result.get('detail', 'Не удалось активировать')}"
            )
        
    except Exception as e:
        logger.error(f"Gift redeem error: {e}")
        await message.answer(
            "❌ Ошибка при активации сертификата.\nПопробуй позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
    
    await state.clear()


# ============== Buy Gift ==============

@router.callback_query(F.data == "buy_gift")
async def show_gift_plans(callback: CallbackQuery):
    """Show plans for gift purchase"""
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    api = get_api_client()
    
    try:
        plans = await api.get_plans()
        
        if not plans:
            await callback.message.answer("❌ Тарифы временно недоступны")
            await callback.answer()
            return
        
        text = "🎁 <b>Подарочный сертификат</b>\n\n"
        text += "Подари VPN другу! Выбери тариф:\n\n"
        
        buttons = []
        for plan in plans:
            name = plan.get("name", "Plan")
            price = plan.get("price", 0)
            duration = plan.get("duration_days", 30)
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"🎁 {name} — {int(price)}₽",
                    callback_data=f"gift_plan:{plan['id']}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")])
        
        await safe_edit_or_resend(
            callback.message,
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        
    except Exception as e:
        logger.error(f"Gift plans error: {e}")
        await callback.message.answer("❌ Ошибка загрузки тарифов")
    
    await callback.answer()


@router.callback_query(F.data.startswith("gift_plan:"))
async def select_gift_plan(callback: CallbackQuery, state: FSMContext):
    """Select plan for gift"""
    if not callback.data:
        await callback.answer()
        return
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    plan_id = callback.data.split(":")[1]
    
    await state.update_data(gift_plan_id=plan_id)
    await state.set_state(GiftStates.entering_recipient)
    
    await safe_edit_or_resend(
        callback.message,
        "🎁 <b>Кому дарим?</b>\n\n"
        "Напиши имя получателя (необязательно):\n"
        "Это имя будет показано получателю.\n\n"
        "Или нажми 'Пропустить' чтобы оставить анонимно.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="gift_skip_recipient")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "gift_skip_recipient")
async def skip_recipient(callback: CallbackQuery, state: FSMContext):
    """Skip recipient name"""
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    await state.set_state(GiftStates.entering_message)
    
    await safe_edit_or_resend(
        callback.message,
        "💬 <b>Добавить сообщение?</b>\n\n"
        "Напиши поздравление для получателя (необязательно):\n\n"
        "Или нажми 'Пропустить'.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="gift_skip_message")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
        ])
    )
    await callback.answer()


@router.message(GiftStates.entering_recipient)
async def process_recipient_name(message: Message, state: FSMContext):
    """Process recipient name"""
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст")
        return
    
    await state.update_data(recipient_name=message.text.strip()[:100])
    await state.set_state(GiftStates.entering_message)
    
    await message.answer(
        "💬 <b>Добавить сообщение?</b>\n\n"
        "Напиши поздравление для получателя (необязательно):\n\n"
        "Или нажми 'Пропустить'.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="gift_skip_message")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
        ])
    )


@router.callback_query(F.data == "gift_skip_message")
async def skip_message(callback: CallbackQuery, state: FSMContext):
    """Skip gift message and create certificate"""
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    await create_gift_certificate(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.message(GiftStates.entering_message)
async def process_gift_message(message: Message, state: FSMContext):
    """Process gift message and create certificate"""
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст")
        return
    
    await state.update_data(gift_message=message.text.strip()[:500])
    await create_gift_certificate(message, state, message.from_user.id)


async def create_gift_certificate(message: Message, state: FSMContext, user_id: int):
    """Create gift certificate"""
    data = await state.get_data()
    await state.clear()
    
    api = get_api_client()
    
    try:
        result = await api.post("/gifts/create", json={
            "plan_id": data.get("gift_plan_id"),
            "recipient_name": data.get("recipient_name"),
            "message": data.get("gift_message")
        }, telegram_id=user_id)
        
        if result.get("certificate_id"):
            code = result.get("code")
            amount = result.get("amount", 0)
            
            await message.answer(
                "🎁 <b>Сертификат создан!</b>\n\n"
                f"💰 К оплате: <b>{int(amount)}₽</b>\n\n"
                "После оплаты ты получишь код сертификата, который можно отправить другу.\n\n"
                "Он сможет активировать его командой в боте.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_gift:{result['certificate_id']}")],
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
                ])
            )
        else:
            await message.answer("❌ Ошибка создания сертификата")
            
    except Exception as e:
        logger.error(f"Gift create error: {e}")
        await message.answer("❌ Ошибка. Попробуй позже.")


# ============== My Gifts ==============

@router.callback_query(F.data == "my_gifts")
async def show_my_gifts(callback: CallbackQuery):
    """Show user's gift certificates"""
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    api = get_api_client()
    
    try:
        result = await api.get("/gifts/my", telegram_id=callback.from_user.id)
        
        purchased = result.get("purchased", [])
        received = result.get("received", [])
        
        text = "🎁 <b>Мои подарочные сертификаты</b>\n\n"
        
        if purchased:
            text += "📤 <b>Отправленные:</b>\n"
            for g in purchased[:5]:
                status = "✅" if g["status"] == "redeemed" else "⏳"
                text += f"{status} <code>{g['code']}</code>\n"
            text += "\n"
        
        if received:
            text += "📥 <b>Полученные:</b>\n"
            for g in received[:5]:
                text += f"🎁 От {g.get('sender_name', 'Аноним')}\n"
        
        if not purchased and not received:
            text += "У тебя пока нет сертификатов.\n\n"
            text += "Можешь подарить VPN другу! 🎁"
        
        await safe_edit_or_resend(
            callback.message,
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Подарить VPN", callback_data="buy_gift")],
                [InlineKeyboardButton(text="📥 Активировать код", callback_data="redeem_gift")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"My gifts error: {e}")
        await callback.message.answer("❌ Ошибка загрузки")
    
    await callback.answer()


# ============== Pay Gift ==============

@router.callback_query(F.data.startswith("pay_gift:"))
async def pay_gift(callback: CallbackQuery):
    """Create payment for gift certificate"""
    if not callback.data:
        await callback.answer()
        return
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    certificate_id = callback.data.split(":")[1]
    api = get_api_client()
    
    try:
        # Create payment for this gift
        result = await api.post(
            "/payments/create",
            json={
                "gift_certificate_id": certificate_id,
                "payment_type": "gift"
            },
            telegram_id=callback.from_user.id
        )
        
        if result and result.get("payment_url"):
            await callback.message.edit_text(
                "💳 <b>Оплата подарка</b>\n\n"
                "Нажми кнопку ниже для перехода к оплате.\n"
                "После оплаты ты получишь код сертификата.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Перейти к оплате", url=result["payment_url"])],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
        else:
            await callback.answer("Ошибка создания платежа", show_alert=True)
            
    except Exception as e:
        logger.error(f"Pay gift error: {e}")
        await callback.answer("Ошибка. Попробуй позже.", show_alert=True)
