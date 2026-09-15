"""
Internationalization (i18n) Module for MetaLib VPN Bot

Features:
- Multi-language support (Russian, English, Ukrainian)
- User language preferences
- Fallback to Russian
- Template formatting with placeholders
"""
from typing import Dict, Optional, Any
from functools import lru_cache
from aiogram.types import User
from loguru import logger

# Supported languages
SUPPORTED_LANGUAGES = ["ru", "en", "uk"]
DEFAULT_LANGUAGE = "ru"


# ===== Translation Dictionary =====

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ===== Common =====
    "btn_back": {
        "ru": "« Назад",
        "en": "« Back",
        "uk": "« Назад"
    },
    "btn_main_menu": {
        "ru": "🏠 Главное меню",
        "en": "🏠 Main Menu",
        "uk": "🏠 Головне меню"
    },
    "btn_subscription": {
        "ru": "💎 Подписка",
        "en": "💎 Subscription",
        "uk": "💎 Підписка"
    },
    "btn_help": {
        "ru": "❓ Помощь",
        "en": "❓ Help",
        "uk": "❓ Допомога"
    },
    "btn_support": {
        "ru": "💬 Поддержка",
        "en": "💬 Support",
        "uk": "💬 Підтримка"
    },
    "btn_settings": {
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
        "uk": "⚙️ Налаштування"
    },
    
    # ===== Welcome =====
    "welcome_title": {
        "ru": "👋 Добро пожаловать в MetaLib VPN!",
        "en": "👋 Welcome to MetaLib VPN!",
        "uk": "👋 Ласкаво просимо до MetaLib VPN!"
    },
    "welcome_description": {
        "ru": "Быстрый и надёжный VPN для безопасного интернета",
        "en": "Fast and reliable VPN for secure internet",
        "uk": "Швидкий та надійний VPN для безпечного інтернету"
    },
    "welcome_features": {
        "ru": """✅ Высокая скорость
✅ Шифрование данных
✅ Поддержка всех устройств
✅ Простая настройка""",
        "en": """✅ High speed
✅ Data encryption
✅ All devices support
✅ Easy setup""",
        "uk": """✅ Висока швидкість
✅ Шифрування даних
✅ Підтримка всіх пристроїв
✅ Просте налаштування"""
    },
    
    # ===== Subscription =====
    "sub_active": {
        "ru": "🟢 Подписка активна",
        "en": "🟢 Subscription active",
        "uk": "🟢 Підписка активна"
    },
    "sub_expired": {
        "ru": "🔴 Подписка истекла",
        "en": "🔴 Subscription expired",
        "uk": "🔴 Підписка закінчилась"
    },
    "sub_expires_in": {
        "ru": "⏱ Осталось: {days} дн.",
        "en": "⏱ Remaining: {days} days",
        "uk": "⏱ Залишилось: {days} дн."
    },
    "sub_plan": {
        "ru": "📋 Тариф: {plan}",
        "en": "📋 Plan: {plan}",
        "uk": "📋 Тариф: {plan}"
    },
    "btn_buy_subscription": {
        "ru": "💳 Оформить подписку",
        "en": "💳 Get Subscription",
        "uk": "💳 Оформити підписку"
    },
    "btn_renew_subscription": {
        "ru": "🔄 Продлить",
        "en": "🔄 Renew",
        "uk": "🔄 Продовжити"
    },
    "btn_my_devices": {
        "ru": "📱 Мои устройства",
        "en": "📱 My Devices",
        "uk": "📱 Мої пристрої"
    },
    
    # ===== Plans =====
    "plans_title": {
        "ru": "💎 Выберите тариф",
        "en": "💎 Choose a Plan",
        "uk": "💎 Оберіть тариф"
    },
    "plan_month": {
        "ru": "{price}₽/мес",
        "en": "{price}₽/mo",
        "uk": "{price}₽/міс"
    },
    "plan_popular": {
        "ru": "🔥 Популярный",
        "en": "🔥 Popular",
        "uk": "🔥 Популярний"
    },
    "plan_discount": {
        "ru": "Скидка {percent}%",
        "en": "Save {percent}%",
        "uk": "Знижка {percent}%"
    },
    
    # ===== Payment =====
    "payment_title": {
        "ru": "💳 Оплата",
        "en": "💳 Payment",
        "uk": "💳 Оплата"
    },
    "payment_amount": {
        "ru": "Сумма: {amount}₽",
        "en": "Amount: {amount}₽",
        "uk": "Сума: {amount}₽"
    },
    "payment_pending": {
        "ru": "⏳ Ожидаем оплату...",
        "en": "⏳ Waiting for payment...",
        "uk": "⏳ Очікуємо оплату..."
    },
    "payment_success": {
        "ru": "✅ Оплата прошла успешно!",
        "en": "✅ Payment successful!",
        "uk": "✅ Оплата пройшла успішно!"
    },
    "payment_failed": {
        "ru": "❌ Ошибка оплаты",
        "en": "❌ Payment failed",
        "uk": "❌ Помилка оплати"
    },
    "btn_pay": {
        "ru": "💳 Оплатить {amount}₽",
        "en": "💳 Pay {amount}₽",
        "uk": "💳 Оплатити {amount}₽"
    },
    "btn_check_payment": {
        "ru": "🔄 Проверить оплату",
        "en": "🔄 Check Payment",
        "uk": "🔄 Перевірити оплату"
    },
    
    # ===== Devices =====
    "devices_title": {
        "ru": "📱 Мои устройства",
        "en": "📱 My Devices",
        "uk": "📱 Мої пристрої"
    },
    "devices_count": {
        "ru": "Устройств: {count}/{max}",
        "en": "Devices: {count}/{max}",
        "uk": "Пристроїв: {count}/{max}"
    },
    "btn_add_device": {
        "ru": "➕ Добавить устройство",
        "en": "➕ Add Device",
        "uk": "➕ Додати пристрій"
    },
    "btn_remove_device": {
        "ru": "🗑 Удалить",
        "en": "🗑 Remove",
        "uk": "🗑 Видалити"
    },
    
    # ===== Referral =====
    "referral_title": {
        "ru": "🎁 Реферальная программа",
        "en": "🎁 Referral Program",
        "uk": "🎁 Реферальна програма"
    },
    "referral_description": {
        "ru": "Приглашай друзей и получай +3 дня к подписке!",
        "en": "Invite friends and get +3 days to subscription!",
        "uk": "Запрошуй друзів та отримуй +3 дні до підписки!"
    },
    "referral_stats": {
        "ru": """👥 Приглашено: {total}
✅ Оплатили: {completed}
🎁 Бонус дней: +{bonus}""",
        "en": """👥 Invited: {total}
✅ Paid: {completed}
🎁 Bonus days: +{bonus}""",
        "uk": """👥 Запрошено: {total}
✅ Оплатили: {completed}
🎁 Бонус днів: +{bonus}"""
    },
    "btn_my_referrals": {
        "ru": "👥 Мои рефералы",
        "en": "👥 My Referrals",
        "uk": "👥 Мої реферали"
    },
    "btn_share_link": {
        "ru": "📤 Поделиться ссылкой",
        "en": "📤 Share Link",
        "uk": "📤 Поділитися посиланням"
    },
    
    # ===== Support =====
    "support_title": {
        "ru": "💬 Поддержка",
        "en": "💬 Support",
        "uk": "💬 Підтримка"
    },
    "support_description": {
        "ru": "Опишите вашу проблему, и мы поможем!",
        "en": "Describe your issue and we'll help!",
        "uk": "Опишіть вашу проблему, і ми допоможемо!"
    },
    "support_sent": {
        "ru": "✅ Сообщение отправлено! Мы ответим в ближайшее время.",
        "en": "✅ Message sent! We'll reply soon.",
        "uk": "✅ Повідомлення надіслано! Ми відповімо найближчим часом."
    },
    
    # ===== Promo =====
    "promo_title": {
        "ru": "🎟 Промокод",
        "en": "🎟 Promo Code",
        "uk": "🎟 Промокод"
    },
    "promo_enter": {
        "ru": "Введите промокод:",
        "en": "Enter promo code:",
        "uk": "Введіть промокод:"
    },
    "promo_success": {
        "ru": "✅ Промокод применён! Скидка: {discount}%",
        "en": "✅ Promo code applied! Discount: {discount}%",
        "uk": "✅ Промокод застосовано! Знижка: {discount}%"
    },
    "promo_invalid": {
        "ru": "❌ Промокод недействителен",
        "en": "❌ Invalid promo code",
        "uk": "❌ Промокод недійсний"
    },
    "btn_enter_promo": {
        "ru": "🎟 Ввести промокод",
        "en": "🎟 Enter Promo Code",
        "uk": "🎟 Ввести промокод"
    },
    
    # ===== Settings =====
    "settings_title": {
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
        "uk": "⚙️ Налаштування"
    },
    "settings_language": {
        "ru": "🌐 Язык: {language}",
        "en": "🌐 Language: {language}",
        "uk": "🌐 Мова: {language}"
    },
    "settings_auto_renew": {
        "ru": "🔄 Автопродление: {status}",
        "en": "🔄 Auto-renewal: {status}",
        "uk": "🔄 Автоподовження: {status}"
    },
    "settings_notifications": {
        "ru": "🔔 Уведомления: {status}",
        "en": "🔔 Notifications: {status}",
        "uk": "🔔 Сповіщення: {status}"
    },
    "btn_change_language": {
        "ru": "🌐 Сменить язык",
        "en": "🌐 Change Language",
        "uk": "🌐 Змінити мову"
    },
    "on": {
        "ru": "Вкл",
        "en": "On",
        "uk": "Увімк"
    },
    "off": {
        "ru": "Выкл",
        "en": "Off",
        "uk": "Вимк"
    },
    
    # ===== Errors =====
    "error_generic": {
        "ru": "❌ Произошла ошибка. Попробуйте позже.",
        "en": "❌ An error occurred. Please try later.",
        "uk": "❌ Сталася помилка. Спробуйте пізніше."
    },
    "error_no_subscription": {
        "ru": "❌ У вас нет активной подписки",
        "en": "❌ You don't have an active subscription",
        "uk": "❌ У вас немає активної підписки"
    },
    "error_max_devices": {
        "ru": "❌ Достигнут лимит устройств",
        "en": "❌ Device limit reached",
        "uk": "❌ Досягнуто ліміт пристроїв"
    },
    
    # ===== FAQ =====
    "faq_title": {
        "ru": "❓ Частые вопросы",
        "en": "❓ FAQ",
        "uk": "❓ Часті питання"
    },
    
    # ===== Trial =====
    "trial_title": {
        "ru": "🎁 Пробный период",
        "en": "🎁 Free Trial",
        "uk": "🎁 Пробний період"
    },
    "trial_description": {
        "ru": "Попробуйте VPN бесплатно на 24 часа!",
        "en": "Try VPN free for 24 hours!",
        "uk": "Спробуйте VPN безкоштовно на 24 години!"
    },
    "trial_activated": {
        "ru": "✅ Пробный период активирован!",
        "en": "✅ Free trial activated!",
        "uk": "✅ Пробний період активовано!"
    },
    "trial_already_used": {
        "ru": "❌ Пробный период уже был использован",
        "en": "❌ Free trial already used",
        "uk": "❌ Пробний період вже використано"
    },
    "btn_start_trial": {
        "ru": "🎁 Попробовать бесплатно",
        "en": "🎁 Try for Free",
        "uk": "🎁 Спробувати безкоштовно"
    },
    
    # ===== Language Names =====
    "lang_ru": {
        "ru": "🇷🇺 Русский",
        "en": "🇷🇺 Russian",
        "uk": "🇷🇺 Російська"
    },
    "lang_en": {
        "ru": "🇬🇧 English",
        "en": "🇬🇧 English",
        "uk": "🇬🇧 English"
    },
    "lang_uk": {
        "ru": "🇺🇦 Українська",
        "en": "🇺🇦 Ukrainian",
        "uk": "🇺🇦 Українська"
    },
}


# ===== Translation Functions =====

# User language cache (in production, use Redis or database)
_user_languages: Dict[int, str] = {}


def get_user_language(user: User) -> str:
    """
    Get user's preferred language.
    
    Priority:
    1. Cached preference
    2. Telegram language code
    3. Default (Russian)
    """
    user_id = user.id
    
    # Check cache
    if user_id in _user_languages:
        return _user_languages[user_id]
    
    # Check Telegram language
    lang_code = user.language_code
    if lang_code:
        # Map common codes
        if lang_code.startswith("ru"):
            return "ru"
        elif lang_code.startswith("uk"):
            return "uk"
        elif lang_code.startswith("en"):
            return "en"
    
    return DEFAULT_LANGUAGE


def set_user_language(user_id: int, language: str) -> bool:
    """Set user's preferred language"""
    if language not in SUPPORTED_LANGUAGES:
        return False
    
    _user_languages[user_id] = language
    return True


def t(key: str, user: Optional[User] = None, lang: Optional[str] = None, **kwargs) -> str:
    """
    Get translated string.
    
    Args:
        key: Translation key
        user: Telegram User (to detect language)
        lang: Language code (overrides user detection)
        **kwargs: Formatting arguments
    
    Returns:
        Translated string with formatting applied
    """
    # Determine language
    if lang:
        language = lang
    elif user:
        language = get_user_language(user)
    else:
        language = DEFAULT_LANGUAGE
    
    # Get translation
    translations = TRANSLATIONS.get(key, {})
    
    if not translations:
        logger.warning(f"Missing translation key: {key}")
        return key
    
    text = translations.get(language) or translations.get(DEFAULT_LANGUAGE, key)
    
    # Apply formatting
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format key {e} for translation: {key}")
    
    return text


def get_language_name(lang_code: str, display_lang: str = None) -> str:
    """Get human-readable language name"""
    key = f"lang_{lang_code}"
    return t(key, lang=display_lang or lang_code)


@lru_cache(maxsize=100)
def get_all_translations(key: str) -> Dict[str, str]:
    """Get all translations for a key (cached)"""
    return TRANSLATIONS.get(key, {})


def get_supported_languages() -> list:
    """Get list of supported languages with names"""
    return [
        {"code": lang, "name": get_language_name(lang, "ru")}
        for lang in SUPPORTED_LANGUAGES
    ]
