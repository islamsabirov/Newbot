import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from .config import BOT_TOKEN, ADMIN_IDS
from .db import init_db
from .handlers import register_handlers
from .admin import register_admin_handlers

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

async def on_startup(dispatcher):
    """Function to be executed on bot startup."""
    # Initialize the database
    init_db()
    
    # Register all handlers
    register_handlers(dispatcher)
    register_admin_handlers(dispatcher)
    
    logging.info("Bot has been started")
    # Notify admins that the bot has started
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "✅ Bot ishga tushdi!")
        except Exception as e:
            logging.error(f"Could not send message to admin {admin_id}: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
