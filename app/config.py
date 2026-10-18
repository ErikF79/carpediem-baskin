from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "CarpeDiem Baskin"
    database_url: str = ""
    staff_password: str = "cambiami"
    secret_key: str = "super-secret-change-me"
    auto_seed: bool = True

    @property
    def sqlalchemy_url(self) -> str:
        url = (self.database_url or "").strip()
        if not url:
            return "sqlite:///" + str(BASE_DIR / "carpediem.db")
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://") :]
        return url


settings = Settings()
