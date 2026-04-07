from aiogram.types import User as TgUser

def build_referral_link(bot_username: str, telegram_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{telegram_id}"

def safe_full_name(user: TgUser) -> str:
    return f"{user.first_name} {user.last_name or ''}".strip()
