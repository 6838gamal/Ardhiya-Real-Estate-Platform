from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings should be defined in .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # ===== Application =====
    APP_NAME: str = "أرضية"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str  # Required - must be set in .env

    # ===== Database =====
    DB_USER: str = "ardiya"
    DB_PASSWORD: str = "ardiya_secret"
    DB_HOST: str = "db"
    DB_PORT: str = "5432"
    DB_NAME: str = "ardiya_db"
    DATABASE_URL: Optional[str] = None

    # ===== Localization =====
    DEFAULT_LANGUAGE: str = "ar"
    SUPPORTED_LANGUAGES: str = "ar,en"

    # ===== Google OAuth =====
    GOOGLE_CLIENT_ID: str  # Required - must be set in .env
    GOOGLE_CLIENT_SECRET: str  # Required - must be set in .env
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    # ===== JWT =====
    JWT_SECRET: Optional[str] = None  # If not set, uses SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ===== Session =====
    SESSION_COOKIE_NAME: str = "ardiya_session"
    SESSION_EXPIRE_MINUTES: int = 1440  # 24 hours
    COOKIE_SECURE: bool = False  # Set to True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"
    COOKIE_HTTPONLY: bool = True

    # ===== CSRF =====
    CSRF_SECRET: Optional[str] = None  # If not set, uses SECRET_KEY
    CSRF_EXPIRE_MINUTES: int = 60  # 1 hour

    # ===== Security =====
    BCRYPT_ROUNDS: int = 12
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    # ===== CORS =====
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    ALLOWED_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    ALLOWED_HEADERS: str = "Content-Type,Authorization"

    # ===== Frontend =====
    FRONTEND_URL: str = "http://localhost:3000"
    FRONTEND_LOGIN_URL: str = "/login"
    FRONTEND_DASHBOARD_URL: str = "/dashboard"

    # ===== API =====
    API_VERSION: str = "v1"
    API_PREFIX: str = "/api/v1"

    # ===== Logging =====
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # ===== Cache (Optional) =====
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 300  # 5 minutes

    # ===== Email (Optional) =====
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None

    # ===== Properties =====
    @property
    def languages(self) -> List[str]:
        """Get list of supported languages."""
        return [lang.strip() for lang in self.SUPPORTED_LANGUAGES.split(",") if lang.strip()]

    @property
    def is_dev(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"

    @property
    def is_prod(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENV == "production"

    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.APP_ENV == "test"

    @property
    def jwt_secret_key(self) -> str:
        """Get JWT secret key (fallback to SECRET_KEY if not set)."""
        return self.JWT_SECRET or self.SECRET_KEY

    @property
    def csrf_secret_key(self) -> str:
        """Get CSRF secret key (fallback to SECRET_KEY if not set)."""
        return self.CSRF_SECRET or self.SECRET_KEY

    @property
    def session_expire_seconds(self) -> int:
        """Get session expiry in seconds."""
        return self.SESSION_EXPIRE_MINUTES * 60

    @property
    def jwt_expire_seconds(self) -> int:
        """Get JWT expiry in seconds."""
        return self.JWT_EXPIRE_MINUTES * 60

    @property
    def is_secure_cookie(self) -> bool:
        """Check if secure cookies should be used."""
        return self.COOKIE_SECURE and self.is_prod

    @property
    def database_url(self) -> str:
        """Get database URI (use DATABASE_URL if provided, else construct)."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_methods_list(self) -> List[str]:
        """Get allowed methods as list."""
        return [method.strip() for method in self.ALLOWED_METHODS.split(",") if method.strip()]

    @property
    def allowed_headers_list(self) -> List[str]:
        """Get allowed headers as list."""
        return [header.strip() for header in self.ALLOWED_HEADERS.split(",") if header.strip()]

    @property
    def google_oauth_scopes(self) -> List[str]:
        """Get Google OAuth scopes."""
        return ["openid", "email", "profile"]

    @property
    def google_auth_url(self) -> str:
        """Get Google OAuth authorization URL."""
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def google_token_url(self) -> str:
        """Get Google OAuth token URL."""
        return "https://oauth2.googleapis.com/token"

    @property
    def google_userinfo_url(self) -> str:
        """Get Google user info URL."""
        return "https://www.googleapis.com/oauth2/v3/userinfo"

    @property
    def google_jwks_url(self) -> str:
        """Get Google JWKS URL for token verification."""
        return "https://www.googleapis.com/oauth2/v3/certs"

    @property
    def rate_limit_period_seconds(self) -> int:
        """Get rate limit period in seconds."""
        return self.RATE_LIMIT_PERIOD

    def get_frontend_url(self, path: str = "") -> str:
        """Get frontend URL with optional path."""
        base = self.FRONTEND_URL.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}" if path else base

    def get_redirect_url(self, path: str = "") -> str:
        """Get redirect URL with optional path."""
        base = self.FRONTEND_URL.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}" if path else base


settings = Settings()
