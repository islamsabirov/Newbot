from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .db import get_channels

def subscription_keyboard():
    channels = get_channels()
    keyboard = InlineKeyboardMarkup(row_width=1)
    for channel in channels:
        keyboard.add(InlineKeyboardButton(text=channel["title"], url=channel["url"]))
    keyboard.add(InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="check_subscription"))
    return keyboard

def admin_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel"),
        InlineKeyboardButton(text="➖ Kanal o'chirish", callback_data="delete_channel"),
        InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="add_movie"),
        InlineKeyboardButton(text="➖ Kino o'chirish", callback_data="delete_movie"),
        InlineKeyboardButton(text="📊 Kanallar ro'yxati", callback_data="list_channels")
    ]
    keyboard.add(*buttons)
    return keyboard

def back_to_admin_keyboard():
    return InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_panel"))
