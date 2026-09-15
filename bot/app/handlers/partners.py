"""
Partner program handlers for Telegram bot
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from app.api_client import get_api_client
from app.utils.helpers import safe_edit_or_resend

router = Router()


class PartnerStates(StatesGroup):
    entering_telegram_channel = State()
    entering_website = State()
    entering_description = State()


@router.callback_query(F.data == "partner_program")
async def partner_program_info(callback: CallbackQuery):
    """Show partner program info"""
    api = get_api_client()
    
    try:
        # Check if already partner
        partner_info = await api.get("/partners/my", telegram_id=callback.from_user.id)
        
        if partner_info and partner_info.get("id"):
            await show_partner_dashboard(callback, partner_info)
            return
    except:
        pass
    
    # Show info for non-partners
    text = """🤝 <b>Партнёрская программа Metalib VPN</b>

Зарабатывай вместе с нами! Рекомендуй VPN друзьям и получай до <b>40% с каждой продажи</b>.

<b>💰 Комиссии по уровням:</b>

🥉 <b>Bronze</b> (старт) — 20%
   0-10 продаж

🥈 <b>Silver</b> — 25%
   10+ продаж

🥇 <b>Gold</b> — 30%
   50+ продаж

💎 <b>Platinum</b> — 40%
   100+ продаж

<b>Как это работает:</b>
1. Получи персональную ссылку
2. Делись с аудиторией
3. Получай % с каждой покупки
4. Выводи от 1000₽

<b>Подходит для:</b>
• Telegram-каналов
• YouTube-блогеров  
• Сайтов и блогов
• Любых инфлюенсеров"""
    
    await safe_edit_or_resend(
        callback.message,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Стать партнёром", callback_data="partner_apply")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ])
    )
    await callback.answer()


async def show_partner_dashboard(callback: CallbackQuery, partner_info: dict):
    """Show partner dashboard"""
    tier = partner_info.get("tier", "bronze").title()
    tier_emoji = {"Bronze": "🥉", "Silver": "🥈", "Gold": "🥇", "Platinum": "💎"}.get(tier, "🥉")
    
    referral_link = partner_info.get("referral_link", "")
    total_clicks = partner_info.get("total_clicks", 0)
    total_sales = partner_info.get("total_sales", 0)
    total_earned = partner_info.get("total_earned", 0)
    pending_payout = partner_info.get("pending_payout", 0)
    commission = partner_info.get("commission_percent", 20)
    
    text = f"""🤝 <b>Партнёрский кабинет</b>

{tier_emoji} Уровень: <b>{tier}</b>
💰 Комиссия: <b>{commission}%</b>

<b>📊 Статистика:</b>
👆 Переходов: <b>{total_clicks}</b>
🛒 Продаж: <b>{total_sales}</b>
💵 Заработано: <b>{total_earned}₽</b>
⏳ К выплате: <b>{pending_payout}₽</b>

<b>🔗 Твоя ссылка:</b>
<code>{referral_link}</code>

👆 Нажми чтобы скопировать"""
    
    buttons = []
    
    if pending_payout >= 1000:
        buttons.append([InlineKeyboardButton(text="💸 Вывести средства", callback_data="partner_payout")])
    
    buttons.append([InlineKeyboardButton(text="📊 Детальная статистика", callback_data="partner_stats")])
    buttons.append([InlineKeyboardButton(text="📝 Промо-материалы", callback_data="partner_materials")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")])
    
    await safe_edit_or_resend(
        callback.message,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data == "partner_apply")
async def partner_apply(callback: CallbackQuery, state: FSMContext):
    """Start partner application"""
    await safe_edit_or_resend(
        callback.message,
        "📝 <b>Заявка на партнёрство</b>\n\n"
        "Расскажи о своей площадке.\n\n"
        "Введи ссылку на Telegram-канал (если есть) или напиши 'нет':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="partner_program")]
        ])
    )
    await state.set_state(PartnerStates.entering_telegram_channel)
    await callback.answer()


@router.message(PartnerStates.entering_telegram_channel)
async def process_telegram_channel(message: Message, state: FSMContext):
    """Process Telegram channel"""
    await state.update_data(telegram_channel=message.text if message.text.lower() != "нет" else None)
    
    await message.answer(
        "Введи ссылку на сайт/блог (если есть) или напиши 'нет':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="partner_program")]
        ])
    )
    await state.set_state(PartnerStates.entering_website)


@router.message(PartnerStates.entering_website)
async def process_website(message: Message, state: FSMContext):
    """Process website"""
    await state.update_data(website=message.text if message.text.lower() != "нет" else None)
    
    await message.answer(
        "Опиши свою аудиторию (кто подписчики, сколько их):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="partner_program")]
        ])
    )
    await state.set_state(PartnerStates.entering_description)


@router.message(PartnerStates.entering_description)
async def process_description(message: Message, state: FSMContext):
    """Submit partner application"""
    api = get_api_client()
    
    data = await state.get_data()
    
    try:
        result = await api.post(
            "/partners/apply",
            json={
                "telegram_channel": data.get("telegram_channel"),
                "website": data.get("website"),
                "description": message.text
            },
            telegram_id=message.from_user.id
        )
        
        if result.get("success"):
            await message.answer(
                "✅ <b>Заявка отправлена!</b>\n\n"
                "Мы рассмотрим её в течение 24 часов.\n"
                "Ответ придёт в этот чат.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
        else:
            await message.answer(
                f"❌ {result.get('detail', 'Ошибка отправки заявки')}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="partner_apply")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
            
    except Exception as e:
        logger.error(f"Partner apply error: {e}")
        await message.answer("❌ Ошибка. Попробуй позже.")
    
    await state.clear()


@router.callback_query(F.data == "partner_stats")
async def partner_stats(callback: CallbackQuery):
    """Show detailed partner stats"""
    api = get_api_client()
    
    try:
        stats = await api.get("/partners/stats", telegram_id=callback.from_user.id)
        
        text = "📊 <b>Детальная статистика</b>\n\n"
        
        # Last 7 days
        text += "<b>За последние 7 дней:</b>\n"
        for day in stats.get("daily", [])[-7:]:
            date = day.get("date", "")
            clicks = day.get("clicks", 0)
            sales = day.get("sales", 0)
            earned = day.get("earned", 0)
            text += f"📅 {date}: 👆{clicks} | 🛒{sales} | 💵{earned}₽\n"
        
        text += f"\n<b>Всего за месяц:</b>\n"
        text += f"👆 Переходов: {stats.get('month_clicks', 0)}\n"
        text += f"🛒 Продаж: {stats.get('month_sales', 0)}\n"
        text += f"💵 Заработано: {stats.get('month_earned', 0)}₽\n"
        text += f"📈 Конверсия: {stats.get('conversion', 0):.1f}%"
        
        await safe_edit_or_resend(
            callback.message,
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="partner_program")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Partner stats error: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "partner_materials")
async def partner_materials(callback: CallbackQuery):
    """Show promo materials"""
    text = """📝 <b>Промо-материалы</b>

<b>Готовые тексты для постов:</b>

<i>Вариант 1 (короткий):</i>
🚀 Лучший VPN для России — быстрый, надёжный, без логов.
Обходи блокировки легко!
→ [ваша ссылка]

<i>Вариант 2 (с фичами):</i>
🔐 Metalib VPN — твой надёжный VPN:
✅ Скорость без ограничений
✅ Работает с Netflix, Spotify
✅ 5 устройств на одной подписке
✅ Поддержка 24/7
→ [ваша ссылка]

<i>Вариант 3 (со скидкой):</i>
💰 VPN со скидкой до 50%!
Годовая подписка = 3 месяца бесплатно
→ [ваша ссылка]

<b>Советы:</b>
• Делай честные обзоры
• Показывай скорость
• Упоминай поддержку
• Предлагай промокоды"""
    
    await safe_edit_or_resend(
        callback.message,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="partner_program")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "partner_payout")
async def partner_payout(callback: CallbackQuery):
    """Request payout"""
    api = get_api_client()
    
    try:
        partner = await api.get("/partners/my", telegram_id=callback.from_user.id)
        pending = partner.get("pending_payout", 0)
        
        if pending < 1000:
            await callback.answer("❌ Минимальная сумма для вывода: 1000₽", show_alert=True)
            return
        
        text = f"""💸 <b>Вывод средств</b>

К выплате: <b>{pending}₽</b>

<b>Способы вывода:</b>
• Банковская карта (РФ)
• ЮMoney
• USDT (TRC20)

Для вывода напиши в поддержку:
• Сумму вывода
• Способ получения
• Реквизиты

Выплаты обрабатываются в течение 3 рабочих дней."""
        
        await safe_edit_or_resend(
            callback.message,
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Написать в поддержку", callback_data="support")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="partner_program")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Partner payout error: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    
    await callback.answer()
