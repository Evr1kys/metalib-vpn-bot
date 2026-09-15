"""
Device management handlers
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.api_client import get_api_client
from app.utils.helpers import safe_edit_or_resend, send_with_banner
from app.utils.messages import get_banner_text
from app.keyboards.inline import (
    devices_list_keyboard,
    device_actions_keyboard,
    protocol_selection_keyboard,
    back_button,
    confirm_action_keyboard
)

router = Router()


@router.callback_query(F.data == "my_devices")
async def show_my_devices(callback: CallbackQuery):
    """Show user devices"""
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    api = get_api_client()
    
    try:
        user = await api.get_user(callback.from_user.id)
        subscription = await api.get_active_subscription(user['id'])
        
        if not subscription:
            await send_with_banner(callback.message, 
                f"❌ У вас нет активной подписки.\n"
                "Сначала оформите подписку.",
                reply_markup=back_button()
            )
            await callback.answer()
            return
        
        await show_devices_list(callback, subscription['id'])
        
    except Exception as e:
        await send_with_banner(callback.message, 
            f"❌ Произошла ошибка при загрузке устройств."
        )
    
    await callback.answer()


async def show_devices_list(callback: CallbackQuery, subscription_id: str):
    """Helper to show devices list"""
    api = get_api_client()
    
    devices = await api.get_devices(subscription_id)
    
    if not devices:
        text = (
            f""
            "<b>📲 Мои устройства</b>\n\n"
            "У вас пока нет подключенных устройств.\n\n"
            "Нажмите «Добавить устройство» для подключения."
        )
    else:
        text = (
            f""
            "<b>📲 Мои устройства</b>\n\n"
            f"Подключено: {len(devices)}\n\n"
            "Нажмите на устройство для просмотра информации:"
        )
    
    await send_with_banner(callback.message, 
        text,
        reply_markup=devices_list_keyboard(devices, subscription_id)
    )


@router.callback_query(F.data.startswith("list_devices:"))
async def list_devices(callback: CallbackQuery):
    """List subscription devices"""
    if not callback.data:
        await callback.answer()
        return
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    subscription_id = callback.data.split(":")[1]
    await show_devices_list(callback, subscription_id)
    await callback.answer()


@router.callback_query(F.data.startswith("add_device:"))
async def add_device_select_protocol(callback: CallbackQuery):
    """Add device - select protocol"""
    if not callback.data:
        await callback.answer()
        return
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    subscription_id = callback.data.split(":")[1]
    
    text = (
        f""
        "<b>📲 Подключение устройства</b>\n\n"
        "Выберите протокол VPN:\n\n"
        "<b>WireGuard</b> - быстрый и современный (рекомендуется)\n"
        "<b>OpenVPN</b> - универсальный и надежный\n"
        "<b>Amnezia</b> - с защитой от блокировок"
    )
    
    await send_with_banner(callback.message, 
        text,
        reply_markup=protocol_selection_keyboard(subscription_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("protocol:"))
async def generate_device_token(callback: CallbackQuery):
    """Generate device binding token"""
    if not callback.data:
        await callback.answer()
        return
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    parts = callback.data.split(":")
    protocol = parts[1]
    subscription_id = parts[2]
    
    api = get_api_client()
    
    try:
        token_data = await api.generate_device_token(subscription_id)
        
        token = token_data['token']
        expires_in = token_data['expires_in_seconds'] // 60
        
        protocol_names = {
            'wireguard': 'WireGuard',
            'openvpn': 'OpenVPN',
            'amnezia': 'Amnezia'
        }
        
        instructions = get_connection_instructions(protocol)
        
        text = (
            f"🔑 <b>Код для подключения</b>\n\n"
            f"<code>{token}</code>\n\n"
            f"Протокол: <b>{protocol_names.get(protocol, protocol)}</b>\n"
            f"⏱ Код действителен {expires_in} минут\n\n"
            f"{instructions}"
        )
        
        await send_with_banner(callback.message, 
            text,
            reply_markup=back_button()
        )
        
    except Exception as e:
        if "Device limit reached" in str(e):
            await send_with_banner(callback.message, 
                "❌ Достигнут лимит устройств для вашего тарифа.\n\n"
                "Отвяжите неиспользуемое устройство или обновите тариф.",
                reply_markup=back_button()
            )
        else:
            await send_with_banner(callback.message, 
                "Произошла ошибка при генерации кода.",
                reply_markup=back_button()
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("device_info:"))
async def show_device_info(callback: CallbackQuery):
    """Show device info"""
    if not callback.data:
        await callback.answer()
        return
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    device_id = callback.data.split(":")[1]
    api = get_api_client()
    
    try:
        device = await api.get(f"/devices/{device_id}", telegram_id=callback.from_user.id)
        text = (
            "📱 <b>Информация об устройстве</b>\n\n"
            f"Устройство: {device.get('name', 'Неизвестно')}\n"
            f"Тип: {device.get('type', 'Неизвестно')}\n"
            f"Последнее использование: {device.get('last_used', 'Не определено')}\n"
        )
    except Exception as e:
        logger.error(f"Device info error: {e}")
        text = (
            "📱 <b>Информация об устройстве</b>\n\n"
            "Не удалось загрузить информацию об устройстве."
        )
    
    await send_with_banner(callback.message, 
        text,
        reply_markup=device_actions_keyboard(device_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("unbind_device:"))
async def confirm_unbind_device(callback: CallbackQuery):
    """Confirm device unbinding"""
    if not callback.data:
        await callback.answer()
        return
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    device_id = callback.data.split(":")[1]
    
    text = (
        "⚠️ <b>Отвязка устройства</b>\n\n"
        "Вы уверены, что хотите отвязать это устройство?\n"
        "Доступ к VPN с этого устройства будет прекращен."
    )
    
    await send_with_banner(callback.message, 
        text,
        reply_markup=confirm_action_keyboard("unbind_device", device_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_unbind_device:"))
async def unbind_device(callback: CallbackQuery):
    """Unbind device"""
    if not callback.data:
        await callback.answer()
        return
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    
    device_id = callback.data.split(":")[1]
    
    api = get_api_client()
    
    try:
        await api.unbind_device(device_id)
        
        await send_with_banner(callback.message, 
            "✅ Устройство отвязано.",
            reply_markup=back_button()
        )
        
    except Exception as e:
        await send_with_banner(callback.message, 
            "Произошла ошибка при отвязке устройства.",
            reply_markup=back_button()
        )
    
    await callback.answer()


def get_connection_instructions(protocol: str) -> str:
    """Get connection instructions for protocol"""
    if protocol == "wireguard":
        return (
            "📱 <b>Инструкция по подключению:</b>\n\n"
            "<b>iOS/Android:</b>\n"
            "1. Скачайте WireGuard из App Store/Google Play\n"
            "2. Нажмите «Добавить туннель» → «Создать из QR-кода» или введите код вручную\n\n"
            "<b>Windows/macOS/Linux:</b>\n"
            "1. Установите WireGuard с официального сайта\n"
            "2. Импортируйте конфигурацию"
        )
    elif protocol == "openvpn":
        return (
            "📱 <b>Инструкция по подключению:</b>\n\n"
            "1. Скачайте OpenVPN Connect\n"
            "2. Импортируйте файл конфигурации\n"
            "3. Подключитесь к VPN"
        )
    else:  # amnezia
        return (
            "📱 <b>Инструкция по подключению:</b>\n\n"
            "1. Скачайте Amnezia VPN\n"
            "2. Используйте код для подключения\n"
            "3. Следуйте инструкциям в приложении"
        )
