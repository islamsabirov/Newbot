import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from app.core.config import settings
from app.core.db import init_db, session_manager
from app.core.logging_utils import logger, setup_logging
from app.core.middlewares import DbSessionMiddleware, UserActivityMiddleware
from app.core.services import ensure_seed_data
from app.modules.handlers import router as main_router
from app.modules.web import create_fastapi_app

def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(UserActivityMiddleware())
    dp.include_router(main_router)
    return dp

async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    logger.info("starting polling mode")
    await dp.start_polling(bot)

async def run_webhook(bot: Bot, dp: Dispatcher) -> None:
    logger.info("starting webhook mode")
    app = create_fastapi_app(bot=bot, dp=dp)
    config = uvicorn.Config(app, host=settings.web_server_host, port=settings.web_server_port, log_level="info")
    server = uvicorn.Server(config)
    await bot.set_webhook(
        url=f"{settings.base_url.rstrip('/')}{settings.webhook_path}",
        secret_token=settings.webhook_secret,
        drop_pending_updates=True,
    )
    await server.serve()

async def run_app() -> None:
    setup_logging()
    await init_db()
    async with session_manager() as session:
        await ensure_seed_data(session)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()
    if settings.use_webhook:
        await run_webhook(bot, dp)
    else:
        await run_polling(bot, dp)
