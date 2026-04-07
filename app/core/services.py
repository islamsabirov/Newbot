from __future__ import annotations
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from app.core.config import settings
from app.core.constants import TARIFFS, ADMIN_MODULES, MIN_CUSTOM_PAYMENT, MAX_CUSTOM_PAYMENT
from app.core.repositories import (
    AuditRepo, BroadcastRepo, ChannelRepo, PaymentRepo,
    ReferralRepo, SettingsRepo, StatsRepo, SubscriptionRepo, UserRepo
)
from app.core.models import Admin, AdminPermission, Setting

class UserService:
    def __init__(self, session):
        self.repo = UserRepo(session)

    async def ensure_user(self, tg_user, referred_by: int | None = None):
        return await self.repo.get_or_create(tg_user.id, f"{tg_user.first_name} {tg_user.last_name or ''}".strip(), tg_user.username, referred_by)

class SubscriptionService:
    def __init__(self, session):
        self.user_repo = UserRepo(session)
        self.sub_repo = SubscriptionRepo(session)

    async def cleanup(self):
        await self.sub_repo.expire_outdated()

    async def grant_tariff(self, telegram_id: int, tariff_code: str, source: str = "manual"):
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None
        tariff = TARIFFS[tariff_code]
        return await self.sub_repo.grant(user, tariff_code, tariff["days"], source)

class PaymentService:
    def __init__(self, session):
        self.payment_repo = PaymentRepo(session)
        self.settings_repo = SettingsRepo(session)

    async def custom_amount_limits(self) -> tuple[int, int]:
        min_amount = await self.settings_repo.get_int("custom_payment_min", MIN_CUSTOM_PAYMENT)
        max_amount = await self.settings_repo.get_int("custom_payment_max", MAX_CUSTOM_PAYMENT)
        if min_amount < MIN_CUSTOM_PAYMENT:
            min_amount = MIN_CUSTOM_PAYMENT
        if max_amount > MAX_CUSTOM_PAYMENT:
            max_amount = MAX_CUSTOM_PAYMENT
        if min_amount > max_amount:
            min_amount, max_amount = MIN_CUSTOM_PAYMENT, MAX_CUSTOM_PAYMENT
        return min_amount, max_amount

    async def validate_custom_amount(self, amount: int) -> None:
        min_amount, max_amount = await self.custom_amount_limits()
        if amount < min_amount or amount > max_amount:
            raise ValueError(f"Summa {min_amount:,} va {max_amount:,} so‘m oralig‘ida bo‘lishi kerak.".replace(",", " "))

    async def create_manual_request(self, user, tariff_code: str, amount: int | None = None, title: str | None = None):
        existing = await self.payment_repo.find_pending_payment_by_user(user.id)
        if existing:
            return existing
        if tariff_code == "custom":
            if amount is None:
                raise ValueError("custom amount required")
            await self.validate_custom_amount(amount)
            payload = '{"custom_title": "%s"}' % (title or "Ixtiyoriy summa")
        else:
            tariff = TARIFFS[tariff_code]
            amount = tariff["price"]
            title = tariff["title"]
            payload = '{"tariff_title": "%s"}' % title
        return await self.payment_repo.create_payment(
            user_id=user.id,
            provider="manual",
            tariff_code=tariff_code,
            amount=amount,
            status="pending",
            metadata_json=payload,
        )

    async def attach_screenshot(self, payment_id: int, photo):
        if await self.payment_repo.has_duplicate_screenshot(photo.file_unique_id):
            raise ValueError("duplicate_screenshot")
        return await self.payment_repo.attach_screenshot(payment_id, photo.file_id, photo.file_unique_id)

    async def payment_card_text(self) -> str:
        return await self.settings_repo.get("manual_payment_card", "💳 To‘lov rekvizitlari kiritilmagan.")

class ReferralService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepo(session)
        self.settings_repo = SettingsRepo(session)
        self.subscription_repo = SubscriptionRepo(session)
        self.referral_repo = ReferralRepo(session)

    async def bind_referral(self, invited_user, referrer_tg_id: int) -> bool:
        if invited_user.telegram_id == referrer_tg_id or invited_user.referred_by:
            return False
        referrer = await self.user_repo.get_by_telegram_id(referrer_tg_id)
        if not referrer:
            return False
        invited_user.referred_by = referrer_tg_id
        referrer.referral_count += 1
        await self.referral_repo.add(referrer.id, invited_user.id, "premium_bonus")
        reward_days = int(await self.settings_repo.get("referral_reward_days", "3"))
        await self.subscription_repo.grant(referrer, "ref_bonus", reward_days, "referral")
        return True

class ChannelService:
    def __init__(self, session, bot: Bot):
        self.repo = ChannelRepo(session)
        self.bot = bot

    async def get_required_channels(self):
        return await self.repo.all_active()

    async def check_user_membership(self, user_id: int):
        channels = await self.repo.all_active()
        results = []
        for channel in channels:
            ok = False
            if channel.channel_id:
                try:
                    member = await self.bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
                    ok = member.status not in ("left", "kicked")
                except TelegramBadRequest:
                    ok = False
            results.append((channel, ok))
        return results

class BroadcastService:
    def __init__(self, session, bot: Bot):
        self.session = session
        self.bot = bot
        self.user_repo = UserRepo(session)
        self.broadcast_repo = BroadcastRepo(session)

    async def send_text(self, admin_id: int, text: str) -> dict:
        broadcast = await self.broadcast_repo.create(admin_id=admin_id, text=text)
        users = await self.user_repo.list_for_broadcast()
        stats = {"sent": 0, "failed": 0, "blocked": 0}
        for user in users:
            try:
                await self.bot.send_message(user.telegram_id, text)
                stats["sent"] += 1
                await self.broadcast_repo.log(broadcast.id, user.id, "sent")
            except Exception as exc:
                err = str(exc)
                status = "blocked" if "bot was blocked by the user" in err.lower() else "failed"
                stats[status] += 1
                await self.broadcast_repo.log(broadcast.id, user.id, status, err)
        return stats

class StatsService:
    def __init__(self, session):
        self.repo = StatsRepo(session)

    async def dashboard(self) -> dict:
        return await self.repo.dashboard()

class CacheService:
    def __init__(self, session):
        self.session = session

    async def clear(self) -> dict:
        targets = [Path("data/tmp"), Path("data/cache"), Path("tmp"), Path("cache")]
        removed_files = 0
        removed_dirs = 0
        for target in targets:
            if not target.exists():
                continue
            for item in sorted(target.rglob("*"), reverse=True):
                try:
                    if item.is_file():
                        item.unlink(missing_ok=True)
                        removed_files += 1
                    elif item.is_dir():
                        item.rmdir()
                        removed_dirs += 1
                except OSError:
                    continue
        return {"removed_files": removed_files, "removed_dirs": removed_dirs}

async def ensure_seed_data(session):
    from sqlalchemy import select
    for tg_id in settings.superadmin_ids:
        result = await session.execute(select(Admin).where(Admin.telegram_id == tg_id))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = Admin(telegram_id=tg_id, role="super_admin")
            session.add(admin)
            await session.flush()
            for module in ADMIN_MODULES:
                session.add(AdminPermission(admin_id=admin.id, module=module, enabled=True))
    defaults = {
        "manual_payment_card": "💳 To‘lovni shu karta orqali qiling: 8600 **** **** 0000",
        "referral_reward_days": "3",
        "ai_enabled": "false",
        "custom_payment_min": str(MIN_CUSTOM_PAYMENT),
        "custom_payment_max": str(MAX_CUSTOM_PAYMENT),
    }
    for key, value in defaults.items():
        result = await session.execute(select(Setting).where(Setting.key == key))
        if not result.scalar_one_or_none():
            session.add(Setting(key=key, value=value))
