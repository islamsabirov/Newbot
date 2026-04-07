from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import (
    Admin, AdminPermission, AuditLog, Broadcast, BroadcastLog, MovieItem, Payment,
    PaymentScreenshot, Referral, RequiredChannel, Setting, Subscription, User
)

class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, full_name: str, username: str | None, referred_by: int | None = None) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.full_name = full_name
            user.username = username
            user.last_active_at = datetime.now(timezone.utc)
            return user, False
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            referred_by=referred_by,
            last_active_at=datetime.now(timezone.utc),
        )
        self.session.add(user)
        await self.session.flush()
        return user, True

    async def list_for_broadcast(self) -> list[User]:
        result = await self.session.execute(select(User).where(User.is_banned.is_(False)))
        return list(result.scalars().all())

class AdminRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_tg_id(self, telegram_id: int) -> Admin | None:
        result = await self.session.execute(select(Admin).where(Admin.telegram_id == telegram_id, Admin.is_active.is_(True)))
        return result.scalar_one_or_none()

    async def add_admin(self, telegram_id: int, role: str = "limited_admin") -> Admin:
        existing = await self.get_by_tg_id(telegram_id)
        if existing:
            return existing
        admin = Admin(telegram_id=telegram_id, role=role)
        self.session.add(admin)
        await self.session.flush()
        for module in ["stats", "broadcast", "channels", "movies", "settings", "admins"]:
            self.session.add(AdminPermission(admin_id=admin.id, module=module, enabled=(role == "super_admin")))
        return admin

class SettingsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str, default: str = "") -> str:
        result = await self.session.execute(select(Setting).where(Setting.key == key))
        item = result.scalar_one_or_none()
        return item.value if item else default

    async def get_int(self, key: str, default: int) -> int:
        value = await self.get(key, str(default))
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    async def set(self, key: str, value: str) -> None:
        result = await self.session.execute(select(Setting).where(Setting.key == key))
        item = result.scalar_one_or_none()
        if item:
            item.value = value
        else:
            self.session.add(Setting(key=key, value=value))

class ChannelRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def all_active(self) -> list[RequiredChannel]:
        result = await self.session.execute(select(RequiredChannel).where(RequiredChannel.is_active.is_(True)))
        return list(result.scalars().all())

class MovieRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_code(self, code: str) -> MovieItem | None:
        result = await self.session.execute(select(MovieItem).where(MovieItem.code == code.upper()))
        return result.scalar_one_or_none()

    async def add(self, **kwargs) -> MovieItem:
        item = MovieItem(**kwargs)
        self.session.add(item)
        await self.session.flush()
        return item

class PaymentRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_payment(self, **kwargs) -> Payment:
        payment = Payment(**kwargs)
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def find_pending_payment_by_user(self, user_id: int) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.user_id == user_id, Payment.status == "pending").order_by(Payment.id.desc())
        )
        return result.scalars().first()

    async def has_duplicate_screenshot(self, file_unique_id: str) -> bool:
        result = await self.session.execute(select(PaymentScreenshot).where(PaymentScreenshot.file_unique_id == file_unique_id))
        return result.scalar_one_or_none() is not None

    async def attach_screenshot(self, payment_id: int, file_id: str, file_unique_id: str) -> PaymentScreenshot:
        screenshot = PaymentScreenshot(payment_id=payment_id, file_id=file_id, file_unique_id=file_unique_id, status="pending")
        self.session.add(screenshot)
        await self.session.flush()
        return screenshot

class SubscriptionRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def expire_outdated(self) -> None:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(select(Subscription).where(Subscription.is_active.is_(True), Subscription.ends_at < now))
        for sub in result.scalars().all():
            sub.is_active = False
        result = await self.session.execute(select(User).where(User.is_premium.is_(True), User.premium_until < now))
        for user in result.scalars().all():
            user.is_premium = False

    async def grant(self, user: User, plan_code: str, days: int, source: str) -> Subscription:
        now = datetime.now(timezone.utc)
        ends_at = max(user.premium_until or now, now) + timedelta(days=days)
        user.is_premium = True
        user.premium_until = ends_at
        sub = Subscription(user_id=user.id, plan_code=plan_code, ends_at=ends_at, source=source)
        self.session.add(sub)
        await self.session.flush()
        return sub

class ReferralRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, referrer_user_id: int, invited_user_id: int, reward_type: str | None = None) -> Referral:
        item = Referral(referrer_user_id=referrer_user_id, invited_user_id=invited_user_id, reward_type=reward_type)
        self.session.add(item)
        await self.session.flush()
        return item

class BroadcastRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, admin_id: int, text: str | None = None, media_file_id: str | None = None) -> Broadcast:
        item = Broadcast(admin_id=admin_id, text=text, media_file_id=media_file_id)
        self.session.add(item)
        await self.session.flush()
        return item

    async def log(self, broadcast_id: int, user_id: int, status: str, error_text: str | None = None) -> None:
        self.session.add(BroadcastLog(broadcast_id=broadcast_id, user_id=user_id, status=status, error_text=error_text))

class StatsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def dashboard(self) -> dict:
        total_users = int((await self.session.execute(select(func.count()).select_from(User))).scalar() or 0)
        premium_users = int((await self.session.execute(select(func.count()).select_from(User).where(User.is_premium.is_(True)))).scalar() or 0)
        pending_payments = int((await self.session.execute(select(func.count()).select_from(Payment).where(Payment.status == "pending"))).scalar() or 0)
        referrals = int((await self.session.execute(select(func.count()).select_from(Referral))).scalar() or 0)
        movies = int((await self.session.execute(select(func.count()).select_from(MovieItem))).scalar() or 0)
        return {
            "total_users": total_users,
            "premium_users": premium_users,
            "pending_payments": pending_payments,
            "referrals": referrals,
            "movies": movies,
        }

class AuditRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, actor_telegram_id: int | None, action: str, payload_json: str | None = None) -> None:
        self.session.add(AuditLog(actor_telegram_id=actor_telegram_id, action=action, payload_json=payload_json))
