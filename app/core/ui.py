from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.core.constants import TARIFFS

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Premium", callback_data="menu:premium")
    kb.button(text="🛍 Sotib olish", callback_data="menu:buy")
    kb.button(text="👥 Referral", callback_data="menu:referral")
    kb.button(text="📢 Kanal", callback_data="menu:channel")
    kb.adjust(2, 2)
    return kb.as_markup()

def back_kb(target: str = "main"):
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Orqaga", callback_data=f"back:{target}")
    return kb.as_markup()

def tariff_kb():
    kb = InlineKeyboardBuilder()
    for code, tariff in TARIFFS.items():
        kb.button(text=f"💳 {tariff['title']} — {tariff['price']:,} so‘m".replace(",", " "), callback_data=f"tariff:{code}")
    kb.button(text="✍️ Boshqa summa kiritish", callback_data="tariff:custom")
    kb.button(text="⬅️ Orqaga", callback_data="back:main")
    kb.adjust(1)
    return kb.as_markup()

def admin_menu():
    kb = InlineKeyboardBuilder()
    for text, code in [
        ("📊 Statistika", "stats"),
        ("📨 Xabar yuborish", "broadcast"),
        ("📢 Kanallar", "channels"),
        ("🎬 Kinolar", "movies"),
        ("⚙️ Sozlamalar", "settings"),
        ("👮 Adminlar", "admins"),
        ("🧹 Kesh tozalash", "cache_clear"),
    ]:
        kb.button(text=text, callback_data=f"admin:{code}")
    kb.button(text="⬅️ Orqaga", callback_data="back:main")
    kb.adjust(2, 2, 2, 1, 1)
    return kb.as_markup()
