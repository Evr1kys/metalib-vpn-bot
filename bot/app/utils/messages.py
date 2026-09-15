"""
Message formatting utilities - Beautiful styled messages for MetaLib VPN Bot
"""
from typing import Optional


def get_banner_text() -> str:
    """Get text banner for messages"""
    return """<b>▸ MetaLib VPN</b>
<i>Профессиональная защита вашего интернета</i>

"""


def format_welcome_message(name: str) -> str:
    """Format welcome message"""
    return f"""{get_banner_text()}
Добро пожаловать, <b>{name}</b>

<blockquote>MetaLib VPN — ваш надёжный инструмент для безопасного доступа к интернету без ограничений.</blockquote>

<b>Преимущества сервиса:</b>
▸ Высокая скорость соединения
▸ Военное шифрование данных
▸ Серверы в 15+ странах
▸ Поддержка всех платформ
▸ Политика нулевого логирования

<b>Выберите действие:</b>"""


def format_subscription_info(plan_name: str, days_left: int, expires_date: str, status_emoji: str, status_text: str) -> str:
    """Format subscription info message"""
    warning = ""
    if days_left <= 3:
        warning = "\n\n<blockquote expandable>⚠️ Подписка скоро истечёт! Продлите её, чтобы сохранить доступ к VPN.</blockquote>"
    
    return f"""{get_banner_text()}
<b>Информация о подписке</b>

<b>Тариф:</b> {plan_name}
<b>Статус:</b> {status_emoji} {status_text}
<b>Осталось дней:</b> {days_left}
<b>Действует до:</b> {expires_date}
{warning}"""


def format_no_subscription() -> str:
    """Format no subscription message"""
    return f"""{get_banner_text()}
<b>Подписка не активна</b>

<blockquote>У вас нет активной подписки на сервис MetaLib VPN.</blockquote>

<b>Что даёт подписка:</b>
▸ Доступ ко всем заблокированным ресурсам
▸ Защита данных в публичных сетях
▸ Стабильное быстрое соединение
▸ Неограниченный трафик

Выберите подходящий тариф для активации."""


def format_plans_header() -> str:
    """Format plans list header"""
    return f"""{get_banner_text()}
<b>Выбор тарифа</b>

Выберите подходящий тариф:"""


def format_plan_details(name: str, duration: str, price: float, max_devices: int = None, features: list = None) -> str:
    """Format single plan details - not used anymore"""
    return ""


def format_payment_created(payment_id: str, amount: float) -> str:
    """Format payment created message"""
    return f"""{get_banner_text()}
<b>Оплата подписки</b>

<b>Номер платежа:</b> <code>{payment_id[:8]}...</code>
<b>Сумма:</b> {amount:.0f} ₽

<blockquote>Нажмите кнопку «Оплатить» для перехода на страницу оплаты. После успешной оплаты подписка активируется автоматически.</blockquote>

Вы можете проверить статус платежа кнопкой «Проверить»."""


def format_payment_success() -> str:
    """Format payment success message"""
    return f"""{get_banner_text()}
<b>✓ Оплата выполнена успешно!</b>

<blockquote>Ваша подписка активирована и готова к использованию.</blockquote>

<b>Что делать дальше:</b>
▸ Нажмите «Мой VPN» для получения ключа
▸ Скачайте приложение для вашего устройства
▸ Подключайтесь и пользуйтесь!

Спасибо за выбор MetaLib VPN! 💙"""


def format_payment_pending() -> str:
    """Payment still pending"""
    return "⏳ Оплата ещё не подтверждена.\n\nПодожди минутку и попробуй снова."


def format_payment_failed() -> str:
    """Payment failed"""
    return "❌ Оплата не прошла.\n\nПопробуй ещё раз или выбери другой способ оплаты."


def format_referral_program(referral_code: str, referral_link: str, stats: dict) -> str:
    """Format referral program info with progress visualization"""
    referrals_count = stats.get('referrals_count', 0)
    completed_count = stats.get('completed_count', 0)
    total_bonus_days = stats.get('total_bonus_days', 0)
    
    # Progress bar for referral milestones
    milestones = [3, 5, 10, 20, 50]
    next_milestone = next((m for m in milestones if m > completed_count), 50)
    progress_pct = min(100, int((completed_count / next_milestone) * 100))
    
    # Visual progress bar (10 segments)
    filled = progress_pct // 10
    progress_bar = "█" * filled + "░" * (10 - filled)
    
    # Conversion rate
    conversion_rate = round(completed_count / referrals_count * 100, 1) if referrals_count > 0 else 0
    
    return f"""{get_banner_text()}
<b>🎁 Реферальная программа</b>

<blockquote>Приглашай друзей → они получают скидку
Ты получаешь <b>+3 дня</b> к подписке за каждого!</blockquote>

━━━━━━━━━━━━━━━━━━━━━

<b>📊 Твоя статистика:</b>

👥 Приглашено: <b>{referrals_count}</b>
✅ Оплатили: <b>{completed_count}</b>
📈 Конверсия: <b>{conversion_rate}%</b>
🎁 Бонус дней: <b>+{total_bonus_days}</b>

<b>🏆 Прогресс до {next_milestone} рефералов:</b>
[{progress_bar}] {progress_pct}%

━━━━━━━━━━━━━━━━━━━━━

<b>🔗 Твоя ссылка:</b>
<code>{referral_link}</code>

<i>Поделись с друзьями! 👇</i>"""


def format_share_referral_text(referral_link: str, bot_username: str) -> str:
    """Format text for sharing referral link"""
    return f"""🛡️ <b>MetaLib VPN</b> — твой надёжный VPN!

✨ Преимущества:
• Быстрый — до 100 Мбит/с
• Безопасный — шифрование AES-256
• Простой — настройка за 1 минуту
• Доступный — от 149₽/мес

🎁 Зарегистрируйся по моей ссылке:
{referral_link}

#VPN #MetaLib #БезопасныйИнтернет"""


def format_no_referrals() -> str:
    """No referrals yet - motivational message"""
    return f"""{get_banner_text()}
<b>👥 Твои рефералы</b>

Пока здесь пусто... 😔

<b>Но это легко исправить!</b>

<blockquote>💡 Совет: Отправь ссылку друзьям, которые:
• Часто путешествуют
• Работают удалённо
• Ценят приватность в интернете</blockquote>

За каждого друга ты получишь <b>+3 дня</b> к подписке!

👇 Нажми «Поделиться» ниже"""


def format_referrals_list(referrals: list) -> str:
    """Format referrals list with detailed info"""
    total_bonus = sum(ref.get("bonus_days", 0) for ref in referrals)
    completed = sum(1 for ref in referrals if ref.get("status") == "completed")
    pending = len(referrals) - completed
    
    text = f"""{get_banner_text()}
<b>👥 Твои рефералы ({len(referrals)})</b>

✅ Оплатили: <b>{completed}</b>
⏳ Ожидают: <b>{pending}</b>
🎁 Всего бонус: <b>+{total_bonus} дней</b>

━━━━━━━━━━━━━━━━━━━━━

"""
    for i, ref in enumerate(referrals[:15], 1):
        username = ref.get("username") or ref.get("first_name") or "Пользователь"
        status = ref.get("status")
        bonus_days = ref.get("bonus_days", 0)
        joined_at = ref.get("created_at", "")[:10] if ref.get("created_at") else ""
        
        status_emoji = {"pending": "⏳", "completed": "✅", "rewarded": "🎁"}.get(status, "❓")
        
        name_display = f"@{username}" if username and not username.startswith("Пользователь") else username
        
        if status in ["completed", "rewarded"]:
            text += f"{i}. {status_emoji} {name_display} — <b>+{bonus_days}</b> дн.\n"
        else:
            text += f"{i}. {status_emoji} {name_display} — ожидаем оплату\n"
    
    if len(referrals) > 15:
        text += f"\n<i>...и ещё {len(referrals) - 15} рефералов</i>"
    
    return text


def format_devices_list(devices: list) -> str:
    """Format devices list"""
    used = len(devices)
    
    text = f"""{get_banner_text()}
<b>📱 Твои устройства</b>

Устройств: <b>{used}</b>
"""
    
    if not devices:
        text += "\nУстройства пока не добавлены.\nНажми <b>«Добавить»</b> чтобы получить ключ!"
    else:
        text += "\n"
        for i, device in enumerate(devices, 1):
            name = device.get('name', 'Устройство')
            device_type = device.get('device_type', 'unknown')
            type_emoji = {
                'ios': '📱', 'android': '🤖', 
                'macos': '💻', 'windows': '🖥️',
                'linux': '🐧', 'router': '📡'
            }.get(device_type, '📱')
            text += f"{type_emoji} <b>{name}</b>\n"
    
    return text


def format_help_message() -> str:
    """Format help message"""
    return f"""{get_banner_text()}
<b>💬 Помощь и поддержка</b>

<b>Частые вопросы:</b>

<b>❓ Как подключиться?</b>
Оформи подписку → Перейди в «Моя подписка» → Нажми «Подключить» → Следуй инструкции

<b>❓ Какие приложения использовать?</b>
├ iOS: Streisand, Hiddify
├ Android: Hiddify, v2rayNG
├ macOS/Windows: Hiddify
└ Ссылки будут на странице ключа

<b>❓ Не работает VPN?</b>
1. Проверь интернет-соединение
2. Попробуй другой сервер
3. Напиши в поддержку

<b>📩 Связь с поддержкой:</b>
@metalib_support"""


def format_promo_applied(code: str, discount: float) -> str:
    """Format promo code applied message"""
    return f"""✅ <b>Промокод применён!</b>

Код: <code>{code}</code>
Скидка: <b>-{discount:.0f} ₽</b>

Теперь выбери тариф — скидка применится автоматически."""


def format_promo_invalid() -> str:
    """Format invalid promo code message"""
    return """❌ <b>Промокод недействителен</b>

Проверь правильность кода или попробуй другой."""


def format_price(amount: float, currency: str) -> str:
    """Format price"""
    if currency == "RUB":
        return f"{amount:.0f} ₽"
    elif currency == "USD":
        return f"${amount:.2f}"
    elif currency == "EUR":
        return f"€{amount:.2f}"
    return f"{amount:.2f} {currency}"


def format_duration(days: int) -> str:
    """Format duration in days"""
    if days == 30:
        return "1 месяц"
    elif days == 90:
        return "3 месяца"
    elif days == 180:
        return "6 месяцев"
    elif days == 365:
        return "1 год"
    return f"{days} дней"


def format_bytes(bytes_count: int) -> str:
    """Format bytes to human readable"""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.1f} MB"
    return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"
