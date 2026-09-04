from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "أرضية"
    app_env: str = "development"
    debug: bool = True

    # Database
    db_user: str = "ardiya"
    db_password: str = "ardiya_secret"
    db_host: str = "db"
    db_port: str = "5432"
    db_name: str = "ardiya_db"
    database_url: str = "postgresql+psycopg2://ardiya:ardiya_secret@db:5432/ardiya_db"

    # Localization
    default_language: str = "ar"
    supported_languages: str = "ar,en"

    # Future: Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    @property
    def languages(self) -> List[str]:
        return [lang.strip() for lang in self.supported_languages.split(",") if lang.strip()]

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"


settings = Settings()
