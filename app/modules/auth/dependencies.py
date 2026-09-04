"""Auth module dependencies."""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config.database import get_db
# ❌ حذف الاستيراد المباشر من auth.services
# from app.modules.auth.services import AuthService, SessionService
from app.modules.auth.models import UserSession
from app.config.settings import settings

# OAuth2 scheme for Bearer token (future API access)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",  # Future token endpoint
    auto_error=False
)


def _get_auth_service_class():
    """Get AuthService with lazy import."""
    from app.modules.auth.services import AuthService
    return AuthService


def _get_session_service_class():
    """Get SessionService with lazy import."""
    from app.modules.auth.services import SessionService
    return SessionService


def get_auth_service(db: Session = Depends(get_db)):
    """Get AuthService instance."""
    AuthService = _get_auth_service_class()
    return AuthService(db)


def get_session_service(db: Session = Depends(get_db)):
    """Get SessionService instance."""
    SessionService = _get_session_service_class()
    return SessionService(db)


async def get_current_user_session(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[UserSession]:
    """Get current user session from cookie."""
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if not session_token:
        return None

    # ✅ استيراد متأخر
    SessionService = _get_session_service_class()
    session_service = SessionService(db)
    session = session_service.get_session(session_token)

    return session


async def get_current_user(
    session: Optional[UserSession] = Depends(get_current_user_session),
) -> UserSession:
    """Get current authenticated user session."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return session


async def get_current_user_optional(
    session: Optional[UserSession] = Depends(get_current_user_session),
) -> Optional[UserSession]:
    """Get current user session or None."""
    return session


def require_roles(allowed_roles: list[str]):
    """Dependency factory for role-based authorization."""
    async def role_checker(
        session: UserSession = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        # ✅ استيراد متأخر للحصول على user
        from app.modules.users.services import UserService
        
        # ✅ تصحيح: UserService لا يقبل معاملات
        user_service = UserService()
        user = user_service.get_user_by_id(session.user_id)
        
        if not user or user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}"
            )
        return session
    return role_checker


# Pre-configured role checkers
require_admin = require_roles(["admin"])
require_buyer = require_roles(["buyer", "admin"])
require_owner = require_roles(["owner", "admin"])
