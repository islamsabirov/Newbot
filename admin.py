from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

from .config import ADMIN_IDS
from .keyboards import admin_main_keyboard, back_to_admin_keyboard
from .db import add_channel, delete_channel, add_movie, delete_movie, get_channels
from .main import bot

class AdminStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_url = State()
    waiting_for_channel_title = State()
    waiting_for_channel_to_delete = State()
    waiting_for_movie_code = State()
    waiting_for_movie_file_id = State()
    waiting_for_movie_caption = State()
    waiting_for_movie_to_delete = State()

async def is_admin(user_id):
    return user_id in ADMIN_IDS

async def admin_panel_command(message: types.Message):
    if await is_admin(message.from_user.id):
        await message.answer("Admin panelga xush kelibsiz!", reply_markup=admin_main_keyboard())
    else:
        await message.answer("Siz admin emassiz.")

async def admin_panel_callback(call: types.CallbackQuery):
    if await is_admin(call.from_user.id):
        await call.message.edit_text("Admin panelga xush kelibsiz!", reply_markup=admin_main_keyboard())
        await call.answer()
    else:
        await call.answer("Siz admin emassiz.", show_alert=True)

# --- Kanal qo'shish --- #
async def add_channel_start(call: types.CallbackQuery):
    if await is_admin(call.from_user.id):
        await call.message.edit_text("Yangi kanal ID sini kiriting (masalan, -1001234567890):", reply_markup=back_to_admin_keyboard())
        await AdminStates.waiting_for_channel_id.set()
        await call.answer()

async def process_channel_id(message: types.Message, state: FSMContext):
    try:
        channel_id = int(message.text.strip())
        await state.update_data(channel_id=channel_id)
        await message.answer("Kanalga taklif havolasini kiriting (masalan, https://t.me/your_channel_name):", reply_markup=back_to_admin_keyboard())
        await AdminStates.waiting_for_channel_url.set()
    except ValueError:
        await message.answer("Noto'g'ri ID formati. Iltimos, raqam kiriting.", reply_markup=back_to_admin_keyboard())

async def process_channel_url(message: types.Message, state: FSMContext):
    channel_url = message.text.strip()
    if channel_url.startswith("https://t.me/"):
        await state.update_data(channel_url=channel_url)
        await message.answer("Kanal nomini kiriting (tugmada ko'rinadigan nom):", reply_markup=back_to_admin_keyboard())
        await AdminStates.waiting_for_channel_title.set()
    else:
        await message.answer("Noto'g'ri havola formati. Iltimos, https://t.me/ bilan boshlanadigan havola kiriting.", reply_markup=back_to_admin_keyboard())

async def process_channel_title(message: types.Message, state: FSMContext):
    channel_title = message.text.strip()
    user_data = await state.get_data()
    channel_id = user_data["channel_id"]
    channel_url = user_data["channel_url"]

    if add_channel(channel_id, channel_url, channel_title):
        await message.answer(f"Kanal '{channel_title}' muvaffaqiyatli qo'shildi!", reply_markup=admin_main_keyboard())
    else:
        await message.answer("Xatolik: Kanal allaqachon mavjud yoki qo'shishda xato yuz berdi.", reply_markup=admin_main_keyboard())
    await state.finish()

# --- Kanal o'chirish --- #
async def delete_channel_start(call: types.CallbackQuery):
    if await is_admin(call.from_user.id):
        channels = get_channels()
        if not channels:
            await call.message.edit_text("Hozirda hech qanday kanal qo'shilmagan.", reply_markup=admin_main_keyboard())
            await call.answer()
            return

        channel_list = "Kanallarni o'chirish uchun ID sini kiriting:\n"
        for ch in channels:
            channel_list += f"- {ch['title']} (ID: {ch['channel_id']})\n"
        await call.message.edit_text(channel_list, reply_markup=back_to_admin_keyboard())
        await AdminStates.waiting_for_channel_to_delete.set()
        await call.answer()

async def process_channel_to_delete(message: types.Message, state: FSMContext):
    try:
        channel_id = int(message.text.strip())
        if delete_channel(channel_id):
            await message.answer(f"Kanal (ID: {channel_id}) muvaffaqiyatli o'chirildi!", reply_markup=admin_main_keyboard())
        else:
            await message.answer("Xatolik: Bunday ID ga ega kanal topilmadi.", reply_markup=admin_main_keyboard())
    except ValueError:
        await message.answer("Noto'g'ri ID formati. Iltimos, raqam kiriting.", reply_markup=back_to_admin_keyboard())
    await state.finish()

# --- Kino qo'shish --- #
async def add_movie_start(call: types.CallbackQuery):
    if await is_admin(call.from_user.id):
        await call.message.edit_text("Yangi kino kodini kiriting (masalan, 'MOVIE123'):", reply_markup=back_to_admin_keyboard())
        await AdminStates.waiting_for_movie_code.set()
        await call.answer()

async def process_movie_code(message: types.Message, state: FSMContext):
    movie_code = message.text.strip()
    await state.update_data(movie_code=movie_code)
    await message.answer("Kino fayl ID sini kiriting (videoni botga yuborib, uning file_id sini oling):", reply_markup=back_to_admin_keyboard())
    await AdminStates.waiting_for_movie_file_id.set()

async def process_movie_file_id(message: types.Message, state: FSMContext):
    file_id = message.text.strip()
    await state.update_data(movie_file_id=file_id)
    await message.answer("Kino uchun izoh (caption) kiriting (ixtiyoriy, 'yoq' deb yozsangiz bo'sh qoladi):", reply_markup=back_to_admin_keyboard())
    await AdminStates.waiting_for_movie_caption.set()

async def process_movie_caption(message: types.Message, state: FSMContext):
    caption = message.text.strip()
    if caption.lower() == 'yoq':
        caption = None

    user_data = await state.get_data()
    movie_code = user_data["movie_code"]
    file_id = user_data["movie_file_id"]

    if add_movie(movie_code, file_id, caption):
        await message.answer(f"Kino '{movie_code}' muvaffaqiyatli qo'shildi!", reply_markup=admin_main_keyboard())
    else:
        await message.answer("Xatolik: Kino kodi allaqachon mavjud yoki qo'shishda xato yuz berdi.", reply_markup=admin_main_keyboard())
    await state.finish()

# --- Kino o'chirish --- #
async def delete_movie_start(call: types.CallbackQuery):
    if await is_admin(call.from_user.id):
        await call.message.edit_text("O'chirish uchun kino kodini kiriting:", reply_markup=back_to_admin_keyboard())
        await AdminStates.waiting_for_movie_to_delete.set()
        await call.answer()

async def process_movie_to_delete(message: types.Message, state: FSMContext):
    movie_code = message.text.strip()
    if delete_movie(movie_code):
        await message.answer(f"Kino '{movie_code}' muvaffaqiyatli o'chirildi!", reply_markup=admin_main_keyboard())
    else:
        await message.answer("Xatolik: Bunday kodga ega kino topilmadi.", reply_markup=admin_main_keyboard())
    await state.finish()

# --- Kanallar ro'yxati --- #
async def list_channels_callback(call: types.CallbackQuery):
    if await is_admin(call.from_user.id):
        channels = get_channels()
        if not channels:
            await call.message.edit_text("Hozirda hech qanday kanal qo'shilmagan.", reply_markup=admin_main_keyboard())
            await call.answer()
            return

        channel_list_text = "<b>Majburiy kanallar ro'yxati:</b>\n\n"
        for i, channel in enumerate(channels, 1):
            channel_list_text += f"{i}. Nomi: {channel['title']}\n   ID: <code>{channel['channel_id']}</code>\n   Havola: {channel['url']}\n\n"
        await call.message.edit_text(channel_list_text, reply_markup=back_to_admin_keyboard(), parse_mode=types.ParseMode.HTML)
        await call.answer()


def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(admin_panel_command, Command("admin"), user_id=ADMIN_IDS)
    dp.register_callback_query_handler(admin_panel_callback, text="admin_panel", user_id=ADMIN_IDS)

    # Kanal qo'shish
    dp.register_callback_query_handler(add_channel_start, text="add_channel", user_id=ADMIN_IDS)
    dp.register_message_handler(process_channel_id, state=AdminStates.waiting_for_channel_id, user_id=ADMIN_IDS)
    dp.register_message_handler(process_channel_url, state=AdminStates.waiting_for_channel_url, user_id=ADMIN_IDS)
    dp.register_message_handler(process_channel_title, state=AdminStates.waiting_for_channel_title, user_id=ADMIN_IDS)

    # Kanal o'chirish
    dp.register_callback_query_handler(delete_channel_start, text="delete_channel", user_id=ADMIN_IDS)
    dp.register_message_handler(process_channel_to_delete, state=AdminStates.waiting_for_channel_to_delete, user_id=ADMIN_IDS)

    # Kino qo'shish
    dp.register_callback_query_handler(add_movie_start, text="add_movie", user_id=ADMIN_IDS)
    dp.register_message_handler(process_movie_code, state=AdminStates.waiting_for_movie_code, user_id=ADMIN_IDS)
    dp.register_message_handler(process_movie_file_id, state=AdminStates.waiting_for_movie_file_id, user_id=ADMIN_IDS)
    dp.register_message_handler(process_movie_caption, state=AdminStates.waiting_for_movie_caption, user_id=ADMIN_IDS)

    # Kino o'chirish
    dp.register_callback_query_handler(delete_movie_start, text="delete_movie", user_id=ADMIN_IDS)
    dp.register_message_handler(process_movie_to_delete, state=AdminStates.waiting_for_movie_to_delete, user_id=ADMIN_IDS)

    # Kanallar ro'yxati
    dp.register_callback_query_handler(list_channels_callback, text="list_channels", user_id=ADMIN_IDS)
