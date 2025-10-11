"""
    By @NYXBAM
    
    t.me/OsintRatBot
    t.me/OsintRatBot
    t.me/OsintRatBot
    t.me/OsintRatBot
    
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from bot_instance import dp

import config
from database import db
from handlers import user, admin
from utils.queue_manager import QueueManager
from utils.search_stub import save_total_count


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=config.LOG_FILE,
)
logger = logging.getLogger(__name__)


async def on_startup(dp: Dispatcher):
    """
    Actions to perform when the bot starts.
    Initialize database and start background tasks.
    """
    logger.info("🤖 Bot is starting up...")
    
    # Initialize database
    db.init_db()
    
    # Create queue manager and store it in bot data
    queue_manager = QueueManager(dp.bot)
    dp.bot['queue_manager'] = queue_manager
    
    # Start periodic queue checking in background
    asyncio.create_task(queue_manager.start_periodic_check())
    logger.info("✅ Queue manager started")
    
    logger.info("🚀 Bot is ready!")
    logger.info(f"📊 Free searches per user: {config.FREE_SEARCHES_PER_USER}")
    logger.info(f"👥 Admin IDs: {config.ADMIN_IDS}")


async def on_shutdown(dp: Dispatcher):
    """
    Actions to perform when the bot shuts down.
    Clean up resources.
    """
    logger.info("🛑 Bot is shutting down...")
    
    await dp.storage.close()
    await dp.storage.wait_closed()
    
    logger.info("👋 Bot has been shut down")


def main():
    """
    Main function to start the bot.
    """
    # Validate configuration
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ Please set BOT_TOKEN in config.py!")
        return
    
    if not config.ADMIN_IDS:
        logger.warning("⚠️ No admin IDs configured! Set ADMIN_IDS in config.py")

    
    # Register handlers
    admin.register_admin_handlers(dp)
    user.register_user_handlers(dp)
    logger.info("✅ Handlers registered")
    
    try:
        total = save_total_count()
        logger.info(f"🔢 Total records in database: {total}")
    except Exception as e:
        logger.error(f"❌ Error fetching total count: {e}")
        
    # Start polling
    logger.info("🔄 Starting bot polling...")
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise