"""
Inline keyboards for bot
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any


def main_menu_keyboard(show_referrals: bool = True, show_trial: bool = False) -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Trial button for new users
    if show_trial:
        builder.row(
            InlineKeyboardButton(text="🎁 Попробовать бесплатно (24ч)", callback_data="start_trial")
        )
    
    builder.row(
        InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_subscription")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription")
    )
    
    if show_referrals:
        builder.row(
            InlineKeyboardButton(text="👥 Рефералы", callback_data="referral_program"),
            InlineKeyboardButton(text="🤝 Партнёрка", callback_data="partner_program")
        )
    
    builder.row(
        InlineKeyboardButton(text="🎁 Промокод", callback_data="activate_promo"),
        InlineKeyboardButton(text="🎀 Подарки", callback_data="gifts_menu")
    )
    
    builder.row(
        InlineKeyboardButton(text="❓ FAQ", callback_data="faq"),
        InlineKeyboardButton(text="💬 Поддержка", callback_data="support")
    )
    
    return builder.as_markup()


def plans_keyboard(plans: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Plans selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    for plan in plans:
        price = plan['price']
        duration = plan['duration_days']
        
        if duration == 30:
            duration_text = "1 месяц"
        elif duration == 90:
            duration_text = "3 месяца"
        elif duration == 365:
            duration_text = "1 год"
        else:
            duration_text = f"{duration} дней"
        
        button_text = f"{plan['name']} — {price:.0f} ₽ / {duration_text}"
        
        if plan.get('is_featured'):
            button_text = f"⭐ {button_text}"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"select_plan:{plan['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def confirm_payment_keyboard(payment_url: str, payment_id: str) -> InlineKeyboardMarkup:
    """Payment confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💳 Оплатить", url=payment_url)
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Применить промокод", callback_data=f"use_promo:{payment_id}")
    )
    builder.row(
        InlineKeyboardButton(text="« Отмена", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def subscription_menu_keyboard(subscription_id: str, vpn_key_url: str = None, has_active: bool = True) -> InlineKeyboardMarkup:
    """Subscription menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    if has_active:
        # Show VPN key - if it's a VLESS URL, show copy button, otherwise show link
        if vpn_key_url:
            if vpn_key_url.startswith("vless://"):
                # VLESS URL - show as copyable button (will open in VPN client)
                builder.row(
                    InlineKeyboardButton(text="🔑 Подключиться к VPN", callback_data=f"show_vpn_key:{subscription_id}")
                )
            else:
                builder.row(
                    InlineKeyboardButton(text="🔑 Моя VPN ссылка", url=vpn_key_url)
                )
        else:
            # No VPN key yet - offer to provision
            builder.row(
                InlineKeyboardButton(text="⚙️ Получить VPN ключ", callback_data=f"provision_vpn:{subscription_id}")
            )
        builder.row(
            InlineKeyboardButton(text="🔄 Продлить", callback_data=f"renew_subscription:{subscription_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_subscription")
        )
    
    builder.row(
        InlineKeyboardButton(text="« Главное меню", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def protocol_selection_keyboard(subscription_id: str) -> InlineKeyboardMarkup:
    """VPN protocol selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⚡ VLESS+Reality (рекомендуется)", callback_data=f"protocol:vless+reality:{subscription_id}")
    )
    builder.row(
        InlineKeyboardButton(text="WireGuard", callback_data=f"protocol:wireguard:{subscription_id}")
    )
    builder.row(
        InlineKeyboardButton(text="OpenVPN", callback_data=f"protocol:openvpn:{subscription_id}")
    )
    builder.row(
        InlineKeyboardButton(text="Amnezia", callback_data=f"protocol:amnezia:{subscription_id}")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="my_subscription")
    )
    
    return builder.as_markup()


def devices_list_keyboard(devices: List[Dict[str, Any]], subscription_id: str) -> InlineKeyboardMarkup:
    """Devices list keyboard"""
    builder = InlineKeyboardBuilder()
    
    for device in devices:
        device_name = device.get('device_name') or device.get('device_type') or 'Устройство'
        device_type_emoji = {
            'iOS': '📱',
            'Android': '📱',
            'Windows': '💻',
            'macOS': '💻',
            'Linux': '🐧',
        }.get(device.get('device_type'), '📱')
        
        builder.row(
            InlineKeyboardButton(
                text=f"{device_type_emoji} {device_name}",
                callback_data=f"device_info:{device['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить устройство", callback_data=f"add_device:{subscription_id}")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="my_subscription")
    )
    
    return builder.as_markup()


def device_actions_keyboard(device_id: str) -> InlineKeyboardMarkup:
    """Device actions keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🗑 Отвязать устройство", callback_data=f"unbind_device:{device_id}")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад к устройствам", callback_data="my_devices")
    )
    
    return builder.as_markup()


def back_button() -> InlineKeyboardMarkup:
    """Simple back button"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def confirm_action_keyboard(action: str, data: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}:{data}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="back_to_main")
    )
    
    return builder.as_markup()
