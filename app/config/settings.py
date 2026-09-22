import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """
    Application settings loaded from environment variables.
    All settings should be defined in .env file.
    """

    def __init__(self):
        # ===== Application =====
        self.APP_NAME: str = os.getenv("APP_NAME", "أرضية")
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "")  # Required - must be set in .env

        # ===== Database =====
        self.DB_USER: str = os.getenv("DB_USER", "ardiya")
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", "ardiya_secret")
        self.DB_HOST: str = os.getenv("DB_HOST", "db")
        self.DB_PORT: str = os.getenv("DB_PORT", "5432")
        self.DB_NAME: str = os.getenv("DB_NAME", "ardiya_db")
        self.DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

        # ===== Localization =====
        self.DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "ar")
        self.SUPPORTED_LANGUAGES: str = os.getenv("SUPPORTED_LANGUAGES", "ar,en")

        # ===== Google OAuth =====
        self.GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")  # Required - must be set in .env
        self.GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")  # Required - must be set in .env
        self.GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")

        # ===== JWT =====
        self.JWT_SECRET: Optional[str] = os.getenv("JWT_SECRET")  # If not set, uses SECRET_KEY
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

        # ===== Session =====
        self.SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "ardiya_session")
        self.SESSION_EXPIRE_MINUTES: int = int(os.getenv("SESSION_EXPIRE_MINUTES", "1440"))  # 24 hours
        self.COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "False").lower() == "true"  # Set to True in production (HTTPS)
        self.COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")
        self.COOKIE_HTTPONLY: bool = os.getenv("COOKIE_HTTPONLY", "True").lower() == "true"

        # ===== CSRF =====
        self.CSRF_SECRET: Optional[str] = os.getenv("CSRF_SECRET")  # If not set, uses SECRET_KEY
        self.CSRF_EXPIRE_MINUTES: int = int(os.getenv("CSRF_EXPIRE_MINUTES", "60"))  # 1 hour

        # ===== Security =====
        self.BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))
        self.RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))  # seconds

        # ===== CORS =====
        self.ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
        self.ALLOWED_METHODS: str = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS")
        self.ALLOWED_HEADERS: str = os.getenv("ALLOWED_HEADERS", "Content-Type,Authorization")

        # ===== Frontend =====
        self.FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.FRONTEND_LOGIN_URL: str = os.getenv("FRONTEND_LOGIN_URL", "/login")
        self.FRONTEND_DASHBOARD_URL: str = os.getenv("FRONTEND_DASHBOARD_URL", "/dashboard")

        # ===== API =====
        self.API_VERSION: str = os.getenv("API_VERSION", "v1")
        self.API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")

        # ===== Logging =====
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # json or text

        # ===== Cache (Optional) =====
        self.REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
        self.CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes

        # ===== Email (Optional) =====
        self.SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
        self.SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
        self.EMAIL_FROM: Optional[str] = os.getenv("EMAIL_FROM")

    # ============================================================
    # Helper: URL Normalization
    # ============================================================
    @staticmethod
    def _normalize_db_url(url: str, target_driver: str = "psycopg2") -> str:
        """
        Normalize a database URL to use the specified driver.

        Handles:
        - postgres:// → postgresql:// (Heroku/Render style)
        - postgresql:// → postgresql+<driver>://
        - postgresql+asyncpg:// → postgresql+<driver>://
        - postgresql+psycopg2:// → postgresql+<driver>://

        Args:
            url: The raw database URL.
            target_driver: Either "psycopg2" (sync) or "asyncpg" (async).

        Returns:
            A properly formatted SQLAlchemy database URL.
        """
        if not url:
            return url

        # 1. Handle Heroku/Render legacy scheme
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        # 2. Ensure we have a postgresql:// prefix (without driver)
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        elif url.startswith("postgresql+psycopg2://"):
            url = url.replace("postgresql+psycopg2://", "postgresql://", 1)
        elif url.startswith("postgresql+psycopg://"):
            url = url.replace("postgresql+psycopg://", "postgresql://", 1)

        # 3. Add the target driver
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", f"postgresql+{target_driver}://", 1)

        return url

    # ============================================================
    # Properties: General
    # ============================================================
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

    # ============================================================
    # Properties: Database URLs
    # ============================================================
    @property
    def database_url(self) -> str:
        """
        Get SYNC database URL (psycopg2 driver).

        This is the default URL used across the application
        (create_engine, SessionLocal, Alembic, etc.).

        Automatically normalizes:
        - postgres:// → postgresql+psycopg2://
        - postgresql+asyncpg:// → postgresql+psycopg2://

        Returns:
            A SQLAlchemy-compatible sync database URL.
        """
        if self.DATABASE_URL:
            return self._normalize_db_url(self.DATABASE_URL, target_driver="psycopg2")
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def sync_database_url(self) -> str:
        """
        Explicit alias for `database_url` (sync / psycopg2).

        Use this when you want to be explicit about the driver,
        e.g., for `create_engine(...)` or Alembic.
        """
        return self.database_url

    @property
    def async_database_url(self) -> str:
        """
        Get ASYNC database URL (asyncpg driver).

        Use this only if you switch to `create_async_engine` +
        `AsyncSession` + `await` everywhere.

        Automatically normalizes:
        - postgres:// → postgresql+asyncpg://
        - postgresql+psycopg2:// → postgresql+asyncpg://
        """
        if self.DATABASE_URL:
            return self._normalize_db_url(self.DATABASE_URL, target_driver="asyncpg")
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_safe(self) -> str:
        """
        Get database URL with password masked (for logging).

        Example:
            postgresql+psycopg2://user:***@host:5432/dbname
        """
        url = self.database_url
        if "@" in url and "://" in url:
            scheme, rest = url.split("://", 1)
            if "@" in rest:
                creds, host = rest.split("@", 1)
                if ":" in creds:
                    user, _ = creds.split(":", 1)
                    return f"{scheme}://{user}:***@{host}"
        return url

    # ============================================================
    # Properties: CORS
    # ============================================================
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

    # ============================================================
    # Properties: Google OAuth
    # ============================================================
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

    # ============================================================
    # Properties: Rate Limiting
    # ============================================================
    @property
    def rate_limit_period_seconds(self) -> int:
        """Get rate limit period in seconds."""
        return self.RATE_LIMIT_PERIOD

    # ============================================================
    # Helpers: URLs
    # ============================================================
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
