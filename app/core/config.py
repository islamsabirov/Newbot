from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    bot_token: str
    bot_username: str = "bot"
    superadmins: str = ""
    default_language: str = "uz"

    use_webhook: bool = False
    base_url: str = "https://example.com"
    webhook_path: str = "/webhook/telegram"
    webhook_secret: str = "change-me"
    web_server_host: str = "0.0.0.0"
    web_server_port: int = 8080

    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    log_level: str = "INFO"

    click_service_id: str = ""
    click_merchant_id: str = ""
    click_secret_key: str = ""
    payme_merchant_id: str = ""
    payme_secret_key: str = ""

    ai_enabled: bool = False
    ai_provider: str = "dummy"
    openai_api_key: str = ""

    @property
    def superadmin_ids(self) -> list[int]:
        return [int(item.strip()) for item in self.superadmins.split(",") if item.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
