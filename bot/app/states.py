"""
FSM States for bot
"""
from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    """Payment process states"""
    waiting_for_promo_code = State()
    confirming_payment = State()


class ReferralStates(StatesGroup):
    """Referral system states"""
    waiting_for_referral_code = State()

