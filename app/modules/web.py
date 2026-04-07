from fastapi import FastAPI, Header, HTTPException, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from app.core.config import settings
from app.core.db import session_manager
from app.core.services import SubscriptionService
from app.providers.payments import ClickProvider, PaymeProvider

def create_fastapi_app(bot: Bot, dp: Dispatcher) -> FastAPI:
    app = FastAPI(title="Telegram Premium Bot Lite")

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post(settings.webhook_path)
    async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
        if settings.webhook_secret and x_telegram_bot_api_secret_token != settings.webhook_secret:
            raise HTTPException(status_code=403, detail="invalid secret token")
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        return {"ok": True}

    @app.post("/webhooks/click")
    async def click_webhook(request: Request, x_click_secret: str | None = Header(default=None)):
        payload = await request.json()
        result = await ClickProvider().parse_webhook(payload, {"x-click-secret": x_click_secret or ""})
        if result.success and result.telegram_id:
            async with session_manager() as session:
                await SubscriptionService(session).grant_tariff(result.telegram_id, "1m", "click")
        return {"ok": True, "status": result.raw_status}

    @app.post("/webhooks/payme")
    async def payme_webhook(request: Request, x_payme_secret: str | None = Header(default=None)):
        payload = await request.json()
        result = await PaymeProvider().parse_webhook(payload, {"x-payme-secret": x_payme_secret or ""})
        if result.success and result.telegram_id:
            async with session_manager() as session:
                await SubscriptionService(session).grant_tariff(result.telegram_id, "1m", "payme")
        return {"ok": True, "status": result.raw_status}

    return app
