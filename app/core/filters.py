from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from app.core.config import settings
from app.core.repositories import AdminRepo

class AdminFilter(BaseFilter):
    async def __call__(self, obj: Message | CallbackQuery, session) -> bool:
        user_id = obj.from_user.id
        if user_id in settings.superadmin_ids:
            return True
        admin = await AdminRepo(session).get_by_tg_id(user_id)
        return bool(admin)
