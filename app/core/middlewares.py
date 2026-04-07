from typing import Any, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from app.core.db import session_manager
from app.core.helpers import safe_full_name
from app.core.repositories import UserRepo

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: Any, data: Dict[str, Any]):
        async with session_manager() as session:
            data["session"] = session
            return await handler(event, data)

class UserActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: Any, data: Dict[str, Any]):
        session = data.get("session")
        tg_user = None
        if isinstance(event, Message):
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery):
            tg_user = event.from_user
        if session and tg_user:
            repo = UserRepo(session)
            await repo.get_or_create(tg_user.id, safe_full_name(tg_user), tg_user.username)
        return await handler(event, data)
