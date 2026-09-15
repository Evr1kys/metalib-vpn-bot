"""
Telegram Bot Main Application
"""
import asyncio
import sys
import signal
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config import settings
from app.handlers import start, subscription, referral, promo, support, gifts, trial, faq, partners, help, devices, servers, admin
from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>"
)


async def main():
    """Main function"""
    # Initialize bot
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )
    
    # Initialize dispatcher
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(admin.router)  # Admin commands first
    dp.include_router(start.router)
    dp.include_router(subscription.router)
    dp.include_router(referral.router)
    dp.include_router(promo.router)
    dp.include_router(support.router)
    dp.include_router(gifts.router)
    dp.include_router(trial.router)
    dp.include_router(faq.router)
    dp.include_router(partners.router)
    dp.include_router(help.router)
    dp.include_router(devices.router)
    dp.include_router(servers.router)
    
    logger.info("Bot started")
    
    # Delete webhook to ensure clean state
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook deleted")
    
    # Create Redis listener task
    redis_task = None
    
    try:
        if settings.telegram_use_webhook:
            # Webhook mode (production)
            logger.info(f"Starting webhook: {settings.telegram_webhook_url}")
            await bot.set_webhook(
                url=settings.telegram_webhook_url,
                drop_pending_updates=True
            )
            # Note: Actual webhook server would be run by backend (FastAPI)
        else:
            # Polling mode (development)
            logger.info("Starting polling mode")
            
            # Start Redis listener for support replies as background task
            redis_task = asyncio.create_task(support.start_redis_listener(bot))
            logger.info("Support Redis listener started")
            
            await dp.start_polling(
                bot, 
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=True,
                handle_signals=False
            )
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    
    finally:
        # Cancel Redis listener
        if redis_task:
            redis_task.cancel()
            try:
                await redis_task
            except asyncio.CancelledError:
                pass
        await bot.session.close()
        logger.info("Bot session closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
