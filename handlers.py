from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.utils.deep_linking import get_start_link, decode_payload

from .db import get_channels, get_movie
from .keyboards import subscription_keyboard
from .main import bot # Bot obyektini import qilish

async def check_all_channels_subscribed(user_id):
    channels = get_channels()
    if not channels: # Agar majburiy kanallar bo'lmasa, obuna tekshirish shart emas
        return True

    for channel in channels:
        try:
            chat_member = await bot.get_chat_member(chat_id=channel["channel_id"], user_id=user_id)
            if chat_member.status == "left":
                return False
        except Exception as e:
            # Kanal topilmasa yoki boshqa xato bo'lsa, obuna bo'lmagan deb hisoblaymank
            print(f"Error checking subscription for channel {channel['channel_id']}: {e}")
            return False
    return True

async def start_command(message: types.Message):
    user_id = message.from_user.id
    if await check_all_channels_subscribed(user_id):
        await message.answer("Assalomu alaykum! Kino kodini yuboring.")
    else:
        await message.answer(
            "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
            reply_markup=subscription_keyboard()
        )

async def check_subscription_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await check_all_channels_subscribed(user_id):
        await call.message.edit_text("✅ Obuna tasdiqlandi! Kino kodini yuboring.")
    else:
        await call.answer("Siz hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)

async def movie_code_handler(message: types.Message):
    user_id = message.from_user.id
    if not await check_all_channels_subscribed(user_id):
        await message.answer(
            "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
            reply_markup=subscription_keyboard()
        )
        return

    movie_code = message.text.strip()
    movie = get_movie(movie_code)

    if movie:
        await message.answer_video(video=movie["file_id"], caption=movie["caption"])
    else:
        await message.answer("Ushbu kodga tegishli kino topilmadi. Iltimos, to'g'ri kod kiriting.")

async def deep_link_start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    if args:
        movie_code = decode_payload(args)
        if not await check_all_channels_subscribed(user_id):
            await message.answer(
                "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
                reply_markup=subscription_keyboard()
            )
            return

        movie = get_movie(movie_code)
        if movie:
            await message.answer_video(video=movie["file_id"], caption=movie["caption"])
        else:
            await message.answer("Ushbu kodga tegishli kino topilmadi. Iltimos, to'g'ri kod kiriting.")
    else:
        await start_command(message)

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_command, Command("start"))
    dp.register_message_handler(deep_link_start, Command("start", deep_link=True))
    dp.register_callback_query_handler(check_subscription_callback, text="check_subscription")
    dp.register_message_handler(movie_code_handler, content_types=types.ContentType.TEXT))
