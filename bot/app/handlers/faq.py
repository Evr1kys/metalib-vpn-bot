"""
FAQ & Knowledge Base handlers for Telegram bot
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from app.api_client import get_api_client
from app.utils.helpers import safe_edit_or_resend

router = Router()


@router.callback_query(F.data == "faq")
@router.callback_query(F.data == "help")
async def show_faq(callback: CallbackQuery):
    """Show FAQ categories"""
    api = get_api_client()
    
    try:
        faq_data = await api.get("/kb/bot/faq")
        categories = faq_data.get("categories", [])
        
        text = "❓ <b>Частые вопросы</b>\n\n"
        text += "Выбери категорию:\n"
        
        buttons = []
        
        for cat in categories:
            emoji = cat.get("icon", "📂")
            name = cat["name"]
            count = cat.get("article_count", 0)
            buttons.append([
                InlineKeyboardButton(
                    text=f"{emoji} {name} ({count})",
                    callback_data=f"faq_cat_{cat['id']}"
                )
            ])
        
        # Quick help buttons
        buttons.append([
            InlineKeyboardButton(text="📲 Как подключиться?", callback_data="faq_quick_connect"),
            InlineKeyboardButton(text="🔧 Не работает?", callback_data="faq_quick_troubleshoot")
        ])
        
        buttons.append([
            InlineKeyboardButton(text="💬 Написать в поддержку", callback_data="support")
        ])
        
        buttons.append([
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
        ])
        
        await safe_edit_or_resend(
            callback.message,
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        
    except Exception as e:
        logger.error(f"FAQ load error: {e}")
        # Fallback static FAQ
        await show_static_faq(callback)
    
    await callback.answer()


@router.callback_query(F.data.startswith("faq_cat_"))
async def show_category_articles(callback: CallbackQuery):
    """Show articles in category"""
    api = get_api_client()
    category_id = int(callback.data.replace("faq_cat_", ""))
    
    try:
        result = await api.get(f"/kb/articles?category_id={category_id}")
        articles = result if isinstance(result, list) else result.get("articles", [])
        
        buttons = []
        for article in articles[:10]:
            buttons.append([
                InlineKeyboardButton(
                    text=f"📄 {article['title']}",
                    callback_data=f"faq_art_{article['id']}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")])
        
        await safe_edit_or_resend(
            callback.message,
            "📂 <b>Статьи в категории:</b>\n\nВыбери статью:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        
    except Exception as e:
        logger.error(f"Category articles error: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("faq_art_"))
async def show_article(callback: CallbackQuery):
    """Show single article"""
    api = get_api_client()
    article_id = int(callback.data.replace("faq_art_", ""))
    
    try:
        article = await api.get(f"/kb/articles/{article_id}")
        
        text = f"📄 <b>{article['title']}</b>\n\n"
        text += article.get("content", "")[:3500]
        
        if len(article.get("content", "")) > 3500:
            text += "\n\n<i>... (полная версия на сайте)</i>"
        
        await safe_edit_or_resend(
            callback.message,
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="👍", callback_data=f"faq_like_{article_id}"),
                    InlineKeyboardButton(text="👎", callback_data=f"faq_dislike_{article_id}")
                ],
                [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Article error: {e}")
        await callback.answer("❌ Статья не найдена", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("faq_like_"))
@router.callback_query(F.data.startswith("faq_dislike_"))
async def like_article(callback: CallbackQuery):
    """Like/dislike article"""
    api = get_api_client()
    
    is_like = callback.data.startswith("faq_like_")
    article_id = int(callback.data.replace("faq_like_", "").replace("faq_dislike_", ""))
    
    try:
        await api.post(
            f"/kb/articles/{article_id}/like",
            json={"is_like": is_like},
            telegram_id=callback.from_user.id
        )
        
        if is_like:
            await callback.answer("👍 Спасибо за отзыв!", show_alert=False)
        else:
            await callback.answer("Спасибо! Мы улучшим статью", show_alert=False)
            
    except Exception as e:
        logger.error(f"Like error: {e}")
        await callback.answer()


@router.callback_query(F.data == "faq_quick_connect")
async def quick_connect_guide(callback: CallbackQuery):
    """Quick connection guide"""
    text = """📲 <b>Как подключиться к VPN</b>

<b>iPhone / iPad:</b>
1. Скачай <b>Streisand</b> из App Store
2. Скопируй VPN-ключ в боте
3. Открой приложение → ➕ → Добавить из буфера
4. Нажми на сервер → Подключить

<b>Android:</b>
1. Скачай <b>v2rayNG</b> из Play Store
2. Скопируй VPN-ключ в боте
3. Открой приложение → ➕ → Импортировать из буфера
4. Нажми на сервер → ▶️

<b>Windows / Mac / Linux:</b>
1. Скачай <b>Hiddify</b>
2. Скопируй VPN-ключ
3. Добавь в приложение
4. Подключайся!

💡 <i>Ключ можно получить в разделе "Моя подписка"</i>"""
    
    await safe_edit_or_resend(
        callback.message,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Скачать приложения", callback_data="download_apps")],
            [InlineKeyboardButton(text="📱 Моя подписка", callback_data="my_subscription")],
            [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "faq_quick_troubleshoot")
async def quick_troubleshoot(callback: CallbackQuery):
    """Quick troubleshooting guide"""
    text = """🔧 <b>VPN не работает? Попробуй это:</b>

<b>1. Перезапусти VPN</b>
Отключи и включи заново

<b>2. Смени сервер</b>
Попробуй другой сервер из списка

<b>3. Проверь интернет</b>
Убедись что интернет работает без VPN

<b>4. Обнови ключ</b>
Получи новый ключ в "Моя подписка"

<b>5. Переустанови приложение</b>
Удали и скачай заново

<b>6. Проверь подписку</b>
Убедись что подписка активна

<b>Всё ещё не работает?</b>
Напиши в поддержку — поможем!"""
    
    await safe_edit_or_resend(
        callback.message,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Моя подписка", callback_data="my_subscription")],
            [InlineKeyboardButton(text="💬 Написать в поддержку", callback_data="support")],
            [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "download_apps")
async def download_apps(callback: CallbackQuery):
    """Show app download options"""
    text = """📲 <b>Скачай VPN-приложение</b>

<b>🍎 iPhone / iPad:</b>
• <a href="https://apps.apple.com/app/streisand/id6450534064">Streisand</a> — рекомендуем!
• <a href="https://apps.apple.com/app/v2box-v2ray-client/id6446814690">V2Box</a>
• <a href="https://apps.apple.com/app/shadowrocket/id932747118">Shadowrocket</a> (платное)

<b>🤖 Android:</b>
• <a href="https://play.google.com/store/apps/details?id=com.v2ray.ang">v2rayNG</a> — рекомендуем!
• <a href="https://play.google.com/store/apps/details?id=app.hiddify.com">Hiddify</a>

<b>💻 Windows:</b>
• <a href="https://github.com/hiddify/hiddify-next/releases">Hiddify</a>
• <a href="https://github.com/2dust/v2rayN/releases">v2rayN</a>

<b>🍏 macOS:</b>
• <a href="https://github.com/hiddify/hiddify-next/releases">Hiddify</a>
• <a href="https://apps.apple.com/app/v2box-v2ray-client/id6446814690">V2Box</a>

<b>🐧 Linux:</b>
• <a href="https://github.com/hiddify/hiddify-next/releases">Hiddify</a>

👆 Нажми на название чтобы скачать"""
    
    await safe_edit_or_resend(
        callback.message,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Как подключиться?", callback_data="faq_quick_connect")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ]),
        disable_web_page_preview=True
    )
    await callback.answer()


async def show_static_faq(callback: CallbackQuery):
    """Static FAQ fallback"""
    text = """❓ <b>Частые вопросы</b>

<b>Что такое VPN?</b>
VPN шифрует ваш интернет-трафик и скрывает IP-адрес, обеспечивая приватность и доступ к заблокированным сайтам.

<b>Какие устройства поддерживаются?</b>
iPhone, iPad, Android, Windows, macOS, Linux — любые устройства!

<b>Насколько это быстро?</b>
Мы используем современный протокол VLESS+Reality — скорость почти как без VPN.

<b>Это безопасно?</b>
Да! Мы не храним логи, используем надёжное шифрование."""
    
    await safe_edit_or_resend(
        callback.message,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Как подключиться?", callback_data="faq_quick_connect")],
            [InlineKeyboardButton(text="🔧 Не работает?", callback_data="faq_quick_troubleshoot")],
            [InlineKeyboardButton(text="💬 Написать в поддержку", callback_data="support")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ])
    )
