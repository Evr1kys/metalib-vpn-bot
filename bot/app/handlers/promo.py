"""
Promo code handler for bot
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.utils.helpers import safe_edit_or_resend

from app.api_client import get_api_client
from app.keyboards.inline import back_button

router = Router()


class PromoCodeStates(StatesGroup):
    """Promo code FSM states"""
    waiting_for_code = State()


@router.callback_query(F.data == "activate_promo")
async def activate_promo_start(callback: CallbackQuery, state: FSMContext):
    """Start promo code activation"""
    await safe_edit_or_resend(callback.message, 
        "🎁 <b>Активация промокода</b>\n\n"
        "Введите промокод для получения скидки:",
        reply_markup=back_button()
    )
    await state.set_state(PromoCodeStates.waiting_for_code)
    await callback.answer()


@router.message(PromoCodeStates.waiting_for_code)
async def promo_code_entered(message: Message, state: FSMContext):
    """Handle promo code input"""
    api = get_api_client()
    promo_code = message.text.strip().upper()
    
    try:
        # Validate promo code
        result = await api.post(
            f"/promocodes/validate",
            json={"code": promo_code, "user_id": str(message.from_user.id)}
        )
        
        if result.get("valid"):
            promo = result.get("promo_code")
            discount_type = promo.get("discount_type")
            discount_value = promo.get("discount_value")
            
            if discount_type == "free_plan":
                # Apply free plan immediately
                try:
                    apply_result = await api.post(
                        f"/promocodes/apply-free",
                        json={
                            "code": promo_code,
                            "user_telegram_id": message.from_user.id
                        }
                    )
                    
                    if apply_result.get("success"):
                        plan_name = apply_result.get("plan_name", "тариф")
                        await message.answer(
                            f"🎉 <b>Поздравляем!</b>\n\n"
                            f"Промокод <code>{promo_code}</code> успешно активирован!\n"
                            f"Вам выдан бесплатный тариф: <b>{plan_name}</b>\n\n"
                            f"Перейдите в раздел «Моя подписка» для просмотра деталей.",
                            reply_markup=back_button()
                        )
                    else:
                        error = apply_result.get("error", "Неизвестная ошибка")
                        await message.answer(
                            f"❌ Не удалось активировать промокод: {error}",
                            reply_markup=back_button()
                        )
                except Exception as e:
                    await message.answer(
                        "❌ Ошибка при активации промокода. Попробуйте позже.",
                        reply_markup=back_button()
                    )
            else:
                # Regular discount promo code
                if discount_type == "percentage":
                    discount_text = f"{discount_value}%"
                else:
                    discount_text = f"{discount_value} ₽"
                
                # Store promo code in state for future payment
                await state.update_data(active_promo_code=promo_code)
                
                await message.answer(
                    f"✅ <b>Промокод активирован!</b>\n\n"
                    f"🎁 Код: <code>{promo_code}</code>\n"
                    f"💰 Скидка: <b>{discount_text}</b>\n\n"
                    f"Промокод будет применен при следующей оплате.",
                    reply_markup=back_button()
                )
        else:
            error = result.get("error", "Промокод недействителен")
            await message.answer(
                f"❌ {error}\n\n"
                f"Попробуйте другой код:",
                reply_markup=back_button()
            )
    except Exception as e:
        await message.answer(
            "❌ Ошибка при проверке промокода. Попробуйте позже.",
            reply_markup=back_button()
        )
    
    await state.clear()


@router.message(Command("promo"))
async def cmd_promo(message: Message, state: FSMContext):
    """Activate promo code via command"""
    # Extract code from command args
    if " " in message.text:
        promo_code = message.text.split(maxsplit=1)[1].strip().upper()
        
        api = get_api_client()
        try:
            result = await api.post(
                f"/promocodes/validate",
                json={"code": promo_code, "user_id": str(message.from_user.id)}
            )
            
            if result.get("valid"):
                promo = result.get("promo_code")
                discount_type = promo.get("discount_type")
                discount_value = promo.get("discount_value")
                
                if discount_type == "percentage":
                    discount_text = f"{discount_value}%"
                else:
                    discount_text = f"{discount_value} ₽"
                
                await state.update_data(active_promo_code=promo_code)
                
                await message.answer(
                    f"✅ <b>Промокод активирован!</b>\n\n"
                    f"🎁 Код: <code>{promo_code}</code>\n"
                    f"💰 Скидка: <b>{discount_text}</b>\n\n"
                    f"Промокод будет применен при следующей оплате."
                )
            else:
                await message.answer(f"❌ Промокод недействителен или истек.")
        except:
            await message.answer("❌ Ошибка при проверке промокода.")
    else:
        await message.answer(
            "🎁 <b>Использование промокода</b>\n\n"
            "Формат: <code>/promo ПРОМОКОД</code>\n"
            "Пример: <code>/promo SUMMER2026</code>"
        )
