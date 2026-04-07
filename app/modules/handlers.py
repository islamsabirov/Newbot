from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.core.config import settings
from app.core.constants import TARIFFS
from app.core.filters import AdminFilter
from app.core.helpers import build_referral_link, safe_full_name
from app.core.repositories import AdminRepo, AuditRepo, MovieRepo, UserRepo
from app.core.services import (
    BroadcastService, CacheService, ChannelService, PaymentService,
    ReferralService, StatsService, SubscriptionService
)
from app.core.ui import admin_menu, back_kb, main_menu, tariff_kb
from app.locales.manager import t

router = Router()

admin_router = Router()
admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())
router.include_router(admin_router)

class ManualPaymentState(StatesGroup):
    waiting_custom_amount = State()
    waiting_screenshot = State()

class AdminState(StatesGroup):
    waiting_admin_id = State()
    waiting_broadcast = State()
    waiting_movie = State()

@router.message(CommandStart())
async def start_handler(message: Message, session):
    payload = (message.text or "").split(maxsplit=1)
    start_arg = payload[1] if len(payload) > 1 else ""
    repo = UserRepo(session)
    user, _ = await repo.get_or_create(message.from_user.id, safe_full_name(message.from_user), message.from_user.username)
    await SubscriptionService(session).cleanup()
    if start_arg.startswith("ref_"):
        try:
            referrer_tg_id = int(start_arg.replace("ref_", ""))
            await ReferralService(session).bind_referral(user, referrer_tg_id)
        except ValueError:
            pass
    await message.answer(t("welcome", user.language), reply_markup=main_menu())

@router.callback_query(F.data == "back:main")
async def back_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("🏠 <b>Bosh menyu</b>\n\nKerakli bo‘limni tanlang.", reply_markup=main_menu())
    await cb.answer()

@router.callback_query(F.data == "menu:premium")
async def premium_info(cb: CallbackQuery, session):
    user = await UserRepo(session).get_by_telegram_id(cb.from_user.id)
    text = "💎 <b>Premium holati</b>\n\n"
    if user and user.is_premium:
        text += f"Faol ✅\nTugash vaqti: {user.premium_until}"
    else:
        text += "Hozircha oddiy foydalanuvchisiz."
    await cb.message.edit_text(text, reply_markup=back_kb())
    await cb.answer()

@router.callback_query(F.data == "menu:buy")
async def buy_menu(cb: CallbackQuery, session):
    service = PaymentService(session)
    min_amount, max_amount = await service.custom_amount_limits()
    await cb.message.edit_text(
        "🛍 <b>Tarif tanlang</b>\n\n"
        "O‘zingizga mos premium paketni tanlang yoki ixtiyoriy summa kiriting.\n"
        f"Ixtiyoriy summa oralig‘i: <b>{min_amount:,}</b> — <b>{max_amount:,}</b> so‘m".replace(",", " "),
        reply_markup=tariff_kb(),
    )
    await cb.answer()

@router.callback_query(F.data == "tariff:custom")
async def choose_custom_amount(cb: CallbackQuery, state: FSMContext, session):
    service = PaymentService(session)
    min_amount, max_amount = await service.custom_amount_limits()
    await state.set_state(ManualPaymentState.waiting_custom_amount)
    await cb.message.edit_text(
        "💸 <b>Ixtiyoriy summa</b>\n\n"
        f"Summani oddiy raqamda yuboring. Masalan: <code>{min_amount}</code>\n\n"
        f"Ruxsat etilgan oraliq: <b>{min_amount:,}</b> — <b>{max_amount:,}</b> so‘m".replace(",", " "),
        reply_markup=back_kb("main"),
    )
    await cb.answer()

@router.message(ManualPaymentState.waiting_custom_amount)
async def custom_amount_input(message: Message, state: FSMContext, session):
    raw = (message.text or "").replace(" ", "").replace(",", "")
    if not raw.isdigit():
        await message.answer("❌ Summani faqat raqamda yuboring. Masalan: <code>15000</code>")
        return
    amount = int(raw)
    user = await UserRepo(session).get_by_telegram_id(message.from_user.id)
    payment_service = PaymentService(session)
    try:
        payment = await payment_service.create_manual_request(user, "custom", amount=amount, title="Ixtiyoriy summa")
    except ValueError as exc:
        await message.answer(f"⚠️ {exc}")
        return
    await state.update_data(payment_id=payment.id, tariff_code="custom", custom_amount=amount)
    card_text = await payment_service.payment_card_text()
    await message.answer(
        f"💳 <b>Manual to‘lov</b>\n\nPaket: Ixtiyoriy summa\nNarx: {amount:,} so‘m\n\n{card_text}\n\nTo‘lovdan keyin screenshot yuboring.".replace(",", " "),
        reply_markup=back_kb("main"),
    )
    await state.set_state(ManualPaymentState.waiting_screenshot)

@router.callback_query(F.data.startswith("tariff:"))
async def choose_tariff(cb: CallbackQuery, state: FSMContext, session):
    code = cb.data.split(":", 1)[1]
    if code == "custom":
        await cb.answer()
        return
    user = await UserRepo(session).get_by_telegram_id(cb.from_user.id)
    payment_service = PaymentService(session)
    payment = await payment_service.create_manual_request(user, code)
    await state.update_data(payment_id=payment.id, tariff_code=code)
    card_text = await payment_service.payment_card_text()
    tariff = TARIFFS[code]
    await cb.message.edit_text(
        f"💳 <b>Manual to‘lov</b>\n\nPaket: {tariff['title']}\nNarx: {tariff['price']:,} so‘m\n\n{card_text}\n\nTo‘lovdan keyin screenshot yuboring.".replace(",", " "),
        reply_markup=back_kb("main"),
    )
    await state.set_state(ManualPaymentState.waiting_screenshot)
    await cb.answer()

@router.message(ManualPaymentState.waiting_screenshot, F.photo)
async def upload_screenshot(message: Message, state: FSMContext, session):
    data = await state.get_data()
    payment_id = data["payment_id"]
    service = PaymentService(session)
    try:
        await service.attach_screenshot(payment_id, message.photo[-1])
    except ValueError:
        await message.answer("⚠️ Bu screenshot oldin yuborilgan. Iltimos boshqa fayl yuboring.")
        return
    await message.answer("✅ Screenshot qabul qilindi. Admin tekshiruvdan keyin premium faollashtiriladi.")
    await state.clear()

@router.callback_query(F.data == "menu:referral")
async def referral_page(cb: CallbackQuery, session):
    user = await UserRepo(session).get_by_telegram_id(cb.from_user.id)
    link = build_referral_link(settings.bot_username, cb.from_user.id)
    text = (
        "👥 <b>Referral bo‘limi</b>\n\n"
        f"Siz taklif qilganlar: <b>{user.referral_count}</b> ta\n"
        f"Havolangiz:\n<code>{link}</code>"
    )
    await cb.message.edit_text(text, reply_markup=back_kb())
    await cb.answer()

@router.callback_query(F.data == "menu:channel")
async def required_channels_page(cb: CallbackQuery, session, bot):
    service = ChannelService(session, bot)
    channels = await service.get_required_channels()
    if not channels:
        await cb.message.edit_text("📢 Hozircha majburiy kanal yo‘q.", reply_markup=back_kb())
        await cb.answer()
        return
    lines = ["📢 <b>Majburiy obuna</b>"]
    for idx, channel in enumerate(channels, 1):
        if channel.invite_link:
            link = channel.invite_link
        elif channel.channel_id:
            link = f"ID: <code>{channel.channel_id}</code>"
        else:
            link = "-"
        lines.append(f"{idx}. <b>{channel.title}</b> — {channel.channel_type}\n{link}")
    lines.append("Obuna bo‘lgach, qayta tekshirish uchun /start bosing.")
    await cb.message.edit_text("\n\n".join(lines), reply_markup=back_kb())
    await cb.answer()

@router.message(Command("movie"))
async def movie_lookup(message: Message, session):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🎬 Kod yuboring: <code>/movie ABC123</code>")
        return
    code = parts[1].strip().upper()
    item = await MovieRepo(session).get_by_code(code)
    if not item:
        await message.answer("❌ Bu kod bo‘yicha kino topilmadi.")
        return
    item.views += 1
    text = (
        f"🎬 <b>{item.title}</b>\n\n"
        f"Kod: <code>{item.code}</code>\n"
        f"Kategoriya: {item.category or '-'}\n\n"
        f"{item.description or 'Tavsif yo‘q.'}"
    )
    if item.channel_post_link:
        text += f"\n\n🔗 {item.channel_post_link}"
    await message.answer(text)

@admin_router.message(Command("admin"))
async def admin_command(message: Message):
    await message.answer("🛠 <b>Admin panel</b>\n\nKerakli bo‘limni tanlang.", reply_markup=admin_menu())

@admin_router.callback_query(F.data == "admin:stats")
async def admin_stats(cb: CallbackQuery, session):
    stats = await StatsService(session).dashboard()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchi: <b>{stats['total_users']}</b>\n"
        f"💎 Premium: <b>{stats['premium_users']}</b>\n"
        f"🎬 Kinolar: <b>{stats['movies']}</b>\n"
        f"👥 Referral: <b>{stats['referrals']}</b>\n"
        f"⏳ Kutilayotgan to‘lovlar: <b>{stats['pending_payments']}</b>"
    )
    await cb.message.edit_text(text, reply_markup=admin_menu())
    await cb.answer()

@admin_router.callback_query(F.data == "admin:admins")
async def admin_admins(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_admin_id)
    await cb.message.edit_text("👮 <b>Yangi admin qo‘shish</b>\n\nYangi admin ID sini kiriting.", reply_markup=back_kb())
    await cb.answer()

@admin_router.message(AdminState.waiting_admin_id)
async def add_admin_flow(message: Message, state: FSMContext, session):
    try:
        tg_id = int((message.text or "").strip())
    except Exception:
        await message.answer("❌ ID noto‘g‘ri. Raqam yuboring.")
        return
    admin = await AdminRepo(session).add_admin(tg_id)
    await AuditRepo(session).log(message.from_user.id, "admin_added", f'{{"telegram_id": {tg_id}}}')
    await message.answer(f"✅ Admin muvaffaqiyatli qo‘shildi.\n\nID: <code>{admin.telegram_id}</code>\nRol: {admin.role}")
    await state.clear()

@admin_router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_broadcast)
    await cb.message.edit_text("📨 <b>Xabar yuborish</b>\n\nYuboriladigan matnni kiriting.", reply_markup=back_kb())
    await cb.answer()

@admin_router.message(AdminState.waiting_broadcast)
async def send_broadcast(message: Message, state: FSMContext, session, bot):
    stats = await BroadcastService(session, bot).send_text(message.from_user.id, message.html_text or message.text or "")
    await message.answer(f"✅ Yakunlandi\nSent: {stats['sent']}\nFailed: {stats['failed']}\nBlocked: {stats['blocked']}")
    await state.clear()

@admin_router.callback_query(F.data == "admin:movies")
async def admin_movies(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_movie)
    await cb.message.edit_text(
        "🎬 <b>Kino qo‘shish</b>\n\nFormat:\n<code>Nomi | KOD123 | Kategoriya | https://t.me/link | Tavsif</code>",
        reply_markup=back_kb(),
    )
    await cb.answer()

@admin_router.message(AdminState.waiting_movie)
async def add_movie(message: Message, state: FSMContext, session):
    try:
        title, code, category, link, description = [x.strip() for x in (message.text or "").split("|", 4)]
    except Exception:
        await message.answer("❌ Format noto‘g‘ri.")
        return
    item = await MovieRepo(session).add(
        title=title,
        code=code.upper(),
        category=category,
        channel_post_link=link,
        description=description,
        created_by=message.from_user.id,
    )
    await AuditRepo(session).log(message.from_user.id, "movie_added", f'{{"code": "{item.code}"}}')
    await message.answer(f"✅ Qo‘shildi: <b>{item.title}</b>\nKod: <code>{item.code}</code>")
    await state.clear()

@admin_router.callback_query(F.data == "admin:channels")
async def channels_stub(cb: CallbackQuery):
    await cb.message.edit_text(
        "📢 <b>Kanallar</b>\n\nBu lite versiyada kanal boshqaruv backend modeli tayyor. Keyingi bosqichda add/delete flow va link/ID bo‘yicha form qo‘shiladi.",
        reply_markup=admin_menu(),
    )
    await cb.answer()

@admin_router.callback_query(F.data == "admin:settings")
async def settings_stub(cb: CallbackQuery, session):
    service = PaymentService(session)
    min_amount, max_amount = await service.custom_amount_limits()
    await cb.message.edit_text(
        "⚙️ <b>Sozlamalar</b>\n\n"
        "Asosiy settinglar DB ichida saqlanadi.\n"
        f"Manual custom to‘lov oralig‘i: <b>{min_amount:,}</b> — <b>{max_amount:,}</b> so‘m\n"
        "Manual karta rekvizitlari: <code>manual_payment_card</code>".replace(",", " "),
        reply_markup=admin_menu(),
    )
    await cb.answer()

@admin_router.callback_query(F.data == "admin:cache_clear")
async def cache_clear(cb: CallbackQuery, session):
    result = await CacheService(session).clear()
    await AuditRepo(session).log(
        cb.from_user.id,
        "cache_cleared",
        f'{{"removed_files": {result["removed_files"]}, "removed_dirs": {result["removed_dirs"]}}}',
    )
    await cb.message.edit_text(
        "🧹 <b>Kesh tozalandi</b>\n\n"
        f"Fayllar: <b>{result['removed_files']}</b>\n"
        f"Papkalar: <b>{result['removed_dirs']}</b>",
        reply_markup=admin_menu(),
    )
    await cb.answer()
