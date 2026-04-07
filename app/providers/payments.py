from dataclasses import dataclass
from app.core.config import settings

@dataclass
class PaymentWebhookResult:
    external_id: str
    success: bool
    amount: int
    telegram_id: int | None
    raw_status: str

class ClickProvider:
    async def parse_webhook(self, payload: dict, headers: dict) -> PaymentWebhookResult:
        if settings.click_secret_key and headers.get("x-click-secret") != settings.click_secret_key:
            raise ValueError("Invalid Click secret")
        return PaymentWebhookResult(
            external_id=str(payload.get("payment_id", "")),
            success=str(payload.get("status")) == "paid",
            amount=int(payload.get("amount", 0)),
            telegram_id=int(payload.get("merchant_trans_id", 0)) if payload.get("merchant_trans_id") else None,
            raw_status=str(payload.get("status", "unknown")),
        )

class PaymeProvider:
    async def parse_webhook(self, payload: dict, headers: dict) -> PaymentWebhookResult:
        if settings.payme_secret_key and headers.get("x-payme-secret") != settings.payme_secret_key:
            raise ValueError("Invalid Payme secret")
        params = payload.get("params", {}) if isinstance(payload, dict) else {}
        account = params.get("account", {}) if isinstance(params, dict) else {}
        return PaymentWebhookResult(
            external_id=str(params.get("id", "")),
            success=payload.get("method") == "PerformTransaction",
            amount=int(params.get("amount", 0)),
            telegram_id=int(account.get("telegram_id", 0)) if account.get("telegram_id") else None,
            raw_status=str(payload.get("method", "unknown")),
        )
