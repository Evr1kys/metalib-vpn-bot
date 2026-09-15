"""
Subscription handlers - Beautiful and functional
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from datetime import datetime
from loguru import logger

from app.api_client import get_api_client
from app.keyboards.inline import (
    plans_keyboard,
    subscription_menu_keyboard,
    confirm_action_keyboard
)
from app.states import PaymentStates
from app.utils.messages import (
    format_plans_header,
    format_plan_details,
    format_payment_created,
    format_payment_success,
    format_payment_pending,
    format_payment_failed,
    format_subscription_info,
    format_no_subscription,
    format_duration,
    format_promo_applied,
    format_promo_invalid
)
from app.utils.helpers import safe_edit_or_resend, send_with_banner

router = Router()


@router.callback_query(F.data == "buy_subscription")
async def show_plans(callback: CallbackQuery):
    """Show available plans"""
    api = get_api_client()
    
    try:
        plans = await api.get_plans()
        
        if not plans:
            await send_with_banner(
                callback.message,
                "❌ Тарифы временно недоступны.\nПопробуй позже!"
            )
            await callback.answer()
            return
        
        text = """<b>💎 Выбор тарифного плана</b>

Выберите подходящий тариф:"""
        
        await send_with_banner(
            callback.message,
            text,
            reply_markup=plans_keyboard(plans)
        )
        
    except Exception as e:
        logger.error(f"Show plans error: {e}")
        await send_with_banner(
            callback.message,
            "❌ Ошибка загрузки тарифов.\nПопробуй позже!"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("select_plan:"))
async def select_plan(callback: CallbackQuery, state: FSMContext):
    """Select plan and show payment options"""
    plan_id = callback.data.split(":")[1]
    
    api = get_api_client()
    
    try:
        state_data = await state.get_data()
        active_promo = state_data.get("active_promo_code")
        
        plan = await api.get_plan(plan_id)
        
        original_price = float(plan['price'])
        final_price = original_price
        discount_text = ""
        
        if active_promo:
            try:
                promo_result = await api.post(
                    f"/promocodes/validate",
                    json={"code": active_promo, "user_id": str(callback.from_user.id)}
                )
                if promo_result.get("valid"):
                    promo_data = promo_result.get("promo_code")
                    if promo_data.get("discount_type") == "percentage":
                        discount = original_price * (promo_data.get("discount_value") / 100)
                    else:
                        discount = promo_data.get("discount_value")
                    
                    final_price = max(0, original_price - discount)
                    discount_text = f"\n🎁 Промокод: <code>{active_promo}</code>\n💰 Скидка: <b>-{discount:.0f} ₽</b>"
            except:
                pass
        
        duration = format_duration(plan['duration_days'])
        
        if discount_text:
            price_text = f"<s>{original_price:.0f}</s> <b>{final_price:.0f} ₽</b>"
        else:
            price_text = f"<b>{original_price:.0f} ₽</b>"
        
        # Format features
        features_text = ""
        features = plan.get('features', [])
        if features and isinstance(features, list):
            features_text = "\n\n<b>Включено:</b>\n" + "\n".join([f"✓ {f}" for f in features])
        
        text = f"""
<b>💎 Тариф «{plan['name']}»</b>

⏱ Срок: <b>{duration}</b>
 Цена: {price_text}{discount_text}{features_text}

Нажми <b>«Оплатить»</b> для продолжения!"""
        
        await state.update_data(selected_plan_id=plan_id)
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="💳 Оплатить", callback_data=f"create_payment:{plan_id}"))
        if not active_promo:
            builder.row(InlineKeyboardButton(text="🎫 Применить промокод", callback_data="activate_promo"))
        builder.row(InlineKeyboardButton(text="« Назад", callback_data="buy_subscription"))
        
        await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
        
    except Exception as e:
        logger.error(f"Select plan error: {e}")
        await send_with_banner(callback.message, 
            f"\n❌ Ошибка загрузки тарифа.\nПопробуй позже!"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("create_payment:"))
async def create_payment(callback: CallbackQuery, state: FSMContext):
    """Create Platega payment and show payment link"""
    plan_id = callback.data.split(":")[1]
    
    api = get_api_client()
    
    try:
        user_id = callback.from_user.id
        state_data = await state.get_data()
        active_promo = state_data.get("active_promo_code")
        
        payment_data = {
            "user_id": str(user_id),
            "plan_id": plan_id
        }
        
        if active_promo:
            payment_data["promo_code"] = active_promo
        
        payment = await api.post("/payments", json=payment_data)
        
        if not payment.get("payment_url"):
            raise Exception("Не удалось создать платёж")
        
        text = format_payment_created(payment['id'], payment['amount'])
        text += "\n\n<i>После оплаты подписка активируется автоматически.</i>"
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="💳 Оплатить", url=payment['payment_url']))
        builder.row(InlineKeyboardButton(text="« Назад", callback_data="buy_subscription"))
        
        await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
        
        if active_promo:
            await state.update_data(active_promo_code=None)
        
    except Exception as e:
        logger.error(f"Create payment error: {e}")
        await send_with_banner(callback.message, 
            f"\n❌ Ошибка создания платежа\n\n<code>{str(e)}</code>\n\nПопробуй позже!"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment(callback: CallbackQuery):
    """Check payment status"""
    payment_id = callback.data.split(":")[1]
    
    api = get_api_client()
    
    try:
        payment = await api.get(f"/payments/{payment_id}")
        status = payment.get("status")
        
        if status == "paid":
            text = format_payment_success()
            
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="🔑 Мой VPN", callback_data="my_vpn"))
            builder.row(InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription"))
            builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
            
            await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
            await callback.answer("✅ Оплата прошла!", show_alert=True)
        
        elif status == "failed":
            await callback.answer(format_payment_failed(), show_alert=True)
        
        else:
            await callback.answer(format_payment_pending(), show_alert=True)
    
    except Exception as e:
        logger.error(f"Check payment error: {e}")
        await callback.answer("❌ Ошибка проверки", show_alert=True)


@router.callback_query(F.data == "my_vpn")
async def show_my_vpn(callback: CallbackQuery):
    """Show user's VPN key"""
    api = get_api_client()
    
    try:
        user = await api.get_user(callback.from_user.id)
        subscription = await api.get_active_subscription(user['id'])
        
        if not subscription:
            text = f"""
<b>❌ Нет активной подписки</b>

Для доступа к VPN необходимо оформить подписку."""
            
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_subscription"))
            builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
            
            await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
            await callback.answer()
            return
        
        vpn_key_url = subscription.get('vpn_key_url')
        
        if vpn_key_url:
            text = f"""
<b>🔑 Твой VPN ключ</b>

Скопируй ссылку и вставь в VPN клиент:

<code>{vpn_key_url}</code>

📱 <b>Приложения для подключения:</b>
• iOS: <a href="https://apps.apple.com/app/v2raytun/id6476628951">V2RayTun</a>
• Android: <a href="https://play.google.com/store/apps/details?id=com.v2raytun.android">V2RayTun</a>
• Windows/Mac: <a href="https://github.com/hiddify/hiddify-app/releases">Hiddify</a>"""
            
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="💎 Продлить подписку", callback_data="buy_subscription"))
            builder.row(InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription"))
            builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
            
            await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
        else:
            # VPN key not provisioned yet - provision it
            text = f"""
<b>⏳ Получаем VPN ключ...</b>

Пожалуйста, подождите."""
            
            await send_with_banner(callback.message, text)
            
            try:
                result = await api.provision_vpn(str(subscription['id']))
                vpn_key_url = result.get('vpn_key_url')
                
                if vpn_key_url:
                    text = f"""
<b>🔑 Твой VPN ключ</b>

Скопируй ссылку и вставь в VPN клиент:

<code>{vpn_key_url}</code>

📱 <b>Приложения для подключения:</b>
• iOS: <a href="https://apps.apple.com/app/v2raytun/id6476628951">V2RayTun</a>
• Android: <a href="https://play.google.com/store/apps/details?id=com.v2raytun.android">V2RayTun</a>
• Windows/Mac: <a href="https://github.com/hiddify/hiddify-app/releases">Hiddify</a>"""
                    
                    builder = InlineKeyboardBuilder()
                    builder.row(InlineKeyboardButton(text="💎 Продлить подписку", callback_data="buy_subscription"))
                    builder.row(InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription"))
                    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
                    
                    await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
                else:
                    await send_with_banner(callback.message, 
                        f"\n❌ Не удалось получить VPN ключ. Попробуйте позже."
                    )
            except Exception as e:
                logger.error(f"Provision VPN error in my_vpn: {e}")
                await send_with_banner(callback.message, 
                    f"\n❌ Ошибка получения VPN ключа."
                )
        
    except Exception as e:
        logger.error(f"Show my VPN error: {e}")
        await callback.answer("Ошибка загрузки VPN", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "my_subscription")
async def show_subscription(callback: CallbackQuery):
    """Show user subscription"""
    api = get_api_client()
    
    try:
        user = await api.get_user(callback.from_user.id)
        subscription = await api.get_active_subscription(user['id'])
        
        if not subscription:
            text = format_no_subscription()
            
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_subscription"))
            builder.row(InlineKeyboardButton(text="« Назад", callback_data="back_to_main"))
            
            await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
        else:
            plan = await api.get_plan(subscription['plan_id'])
            
            expires_at = datetime.fromisoformat(subscription['expires_at'].replace('Z', '+00:00'))
            days_left = (expires_at - datetime.now(expires_at.tzinfo)).days
            
            status_map = {
                'active': ('✅', 'Активна'),
                'expired': ('❌', 'Истекла'),
                'cancelled': ('🚫', 'Отменена'),
                'pending': ('⏳', 'В обработке')
            }
            status_emoji, status_text = status_map.get(subscription['status'], ('❓', 'Неизвестно'))
            
            text = format_subscription_info(
                plan_name=plan['name'],
                days_left=days_left,
                expires_date=expires_at.strftime('%d.%m.%Y'),
                status_emoji=status_emoji,
                status_text=status_text
            )
            
            # Get VPN key URL from subscription response
            vpn_key_url = subscription.get('vpn_key_url')
            
            await send_with_banner(callback.message, 
                text,
                reply_markup=subscription_menu_keyboard(subscription['id'], vpn_key_url=vpn_key_url, has_active=True)
            )
        
    except Exception as e:
        logger.error(f"Show subscription error: {e}")
        await send_with_banner(callback.message, 
            f"\n❌ Ошибка загрузки подписки."
        )
    
    await callback.answer()


# NOTE: activate_promo handler moved to promo.py to avoid duplication


@router.callback_query(F.data.startswith("subscription_stats:"))
async def show_subscription_stats(callback: CallbackQuery):
    """Show subscription statistics"""
    subscription_id = callback.data.split(":")[1]
    
    api = get_api_client()
    
    try:
        sub = await api.get_subscription(subscription_id)
        
        if not sub:
            await callback.answer("Подписка не найдена", show_alert=True)
            return
        
        # Calculate days remaining
        from datetime import datetime
        expires_at = datetime.fromisoformat(sub['expires_at'].replace('Z', '+00:00'))
        now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.utcnow()
        days_left = max(0, (expires_at - now).days)
        
        text = f"""
<b>📈 Статистика подписки</b>

<b>Тариф:</b> {sub.get('plan_name', 'Стандарт')}
<b>Статус:</b> {'✅ Активна' if sub.get('status') == 'active' else '❌ Неактивна'}
<b>Осталось дней:</b> {days_left}
<b>Устройств:</b> {sub.get('devices_count', 0)}"""
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="« Назад", callback_data="my_subscription"))
        
        await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
        
    except Exception as e:
        logger.error(f"Subscription stats error: {e}")
        await callback.answer("Ошибка загрузки статистики", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("cancel:"))
async def confirm_cancel(callback: CallbackQuery):
    """Confirm subscription cancellation"""
    subscription_id = callback.data.split(":")[1]
    
    text = f"""
<b>⚠️ Отмена подписки</b>

Ты уверен, что хочешь отменить подписку?
Доступ к VPN будет прекращён."""
    
    await send_with_banner(callback.message, 
        text,
        reply_markup=confirm_action_keyboard("cancel_subscription", subscription_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_cancel_subscription:"))
async def cancel_subscription(callback: CallbackQuery):
    """Cancel subscription"""
    subscription_id = callback.data.split(":")[1]
    
    api = get_api_client()
    
    try:
        await api.cancel_subscription(subscription_id)
        
        text = f"""
<b>✅ Подписка отменена</b>

Ты можешь оформить новую подписку в любое время!"""
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="💎 Новая подписка", callback_data="buy_subscription"))
        builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
        
        await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
        
    except Exception as e:
        logger.error(f"Cancel subscription error: {e}")
        await send_with_banner(callback.message, 
            f"\n❌ Ошибка отмены подписки."
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("provision_vpn:"))
async def provision_vpn(callback: CallbackQuery):
    """Provision VPN access for subscription"""
    subscription_id = callback.data.split(":")[1]
    
    api = get_api_client()
    
    await callback.answer("⏳ Создаём VPN ключ...", show_alert=False)
    
    try:
        result = await api.provision_vpn(subscription_id)
        vpn_key_url = result.get("vpn_key_url")
        
        if vpn_key_url:
            text = f"""
<b>✅ VPN ключ создан!</b>

Скопируй ссылку и вставь в VPN клиент:

<code>{vpn_key_url}</code>

📱 <b>Приложения для подключения:</b>
• iOS: <a href="https://apps.apple.com/app/v2raytun/id6476628951">V2RayTun</a>
• Android: <a href="https://play.google.com/store/apps/details?id=com.v2raytun.android">V2RayTun</a>
• Windows/Mac: <a href="https://github.com/hiddify/hiddify-app/releases">Hiddify</a>"""
            
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription"))
            builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
            
            await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
        else:
            await send_with_banner(callback.message, 
                f"\n❌ Не удалось создать VPN ключ. Попробуй позже."
            )
        
    except Exception as e:
        logger.error(f"Provision VPN error: {e}")
        await send_with_banner(callback.message, 
            f"\n❌ Ошибка создания VPN ключа."
        )


@router.callback_query(F.data.startswith("show_vpn_key:"))
async def show_vpn_key(callback: CallbackQuery):
    """Show VPN key for subscription"""
    subscription_id = callback.data.split(":")[1]
    
    api = get_api_client()
    
    try:
        user = await api.get_user(callback.from_user.id)
        subscription = await api.get_active_subscription(user['id'])
        
        if not subscription:
            await callback.answer("Подписка не найдена", show_alert=True)
            return
        
        vpn_key_url = subscription.get('vpn_key_url')
        
        if vpn_key_url:
            text = f"""
<b>🔑 Твой VPN ключ</b>

Скопируй ссылку и вставь в VPN клиент:

<code>{vpn_key_url}</code>

📱 <b>Приложения для подключения:</b>
• iOS: <a href="https://apps.apple.com/app/v2raytun/id6476628951">V2RayTun</a>
• Android: <a href="https://play.google.com/store/apps/details?id=com.v2raytun.android">V2RayTun</a>
• Windows/Mac: <a href="https://github.com/hiddify/hiddify-app/releases">Hiddify</a>"""
            
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription"))
            builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
            
            await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
        else:
            await callback.answer("VPN ключ не найден", show_alert=True)
        
    except Exception as e:
        logger.error(f"Show VPN key error: {e}")
        await callback.answer("Ошибка загрузки VPN ключа", show_alert=True)


@router.callback_query(F.data.startswith("renew_subscription:"))
async def renew_subscription(callback: CallbackQuery):
    """Renew subscription with same plan"""
    subscription_id = callback.data.split(":")[1]
    
    api = get_api_client()
    
    await callback.answer("⏳ Создаём платёж...", show_alert=False)
    
    try:
        result = await api.renew_subscription(subscription_id)
        
        payment_url = result.get("payment_url")
        amount = result.get("amount", 0)
        plan_name = result.get("plan_name", "VPN")
        duration_days = result.get("duration_days", 30)
        
        if payment_url:
            text = f"""
<b>🔄 Продление подписки</b>

Тариф: <b>{plan_name}</b>
Период: <b>{duration_days} дней</b>
Сумма: <b>{amount:.0f} ₽</b>

Нажми «Оплатить» для продолжения!"""
            
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="💳 Оплатить", url=payment_url))
            builder.row(InlineKeyboardButton(text="« Назад", callback_data="my_subscription"))
            
            await send_with_banner(callback.message, text, reply_markup=builder.as_markup())
        else:
            await send_with_banner(callback.message, 
                f"\n❌ Не удалось создать платёж. Попробуй позже."
            )
        
    except Exception as e:
        logger.error(f"Renew subscription error: {e}")
        await send_with_banner(callback.message, 
            f"\n❌ Ошибка создания платежа."
        )