"""Auth module dependencies."""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.modules.auth.models import UserSession
from app.modules.users.models import User  # ✅ إضافة استيراد User
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# OAuth2 scheme for Bearer token (future API access)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    auto_error=False
)


def _get_session_service_class():
    """Get SessionService with lazy import."""
    from app.modules.auth.services import SessionService
    return SessionService


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

    SessionService = _get_session_service_class()
    session_service = SessionService(db)
    session = session_service.get_session(session_token)

    return session


async def get_current_user(
    session: Optional[UserSession] = Depends(get_current_user_session),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # ✅ جلب المستخدم الكامل من قاعدة البيانات
    from app.modules.users.services import UserService
    user_service = UserService(db)
    user = user_service.get_user_by_id(session.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_user_optional(
    session: Optional[UserSession] = Depends(get_current_user_session),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user or None."""
    if not session:
        return None
    
    # ✅ جلب المستخدم الكامل من قاعدة البيانات
    try:
        from app.modules.users.services import UserService
        user_service = UserService(db)
        user = user_service.get_user_by_id(session.user_id)
        return user if user and user.is_active else None
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None


def require_roles(allowed_roles: list[str]):
    """Dependency factory for role-based authorization."""
    async def role_checker(
        user: User = Depends(get_current_user),  # ✅ الآن user هو كائن User
        db: Session = Depends(get_db)
    ):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}"
            )
        return user  # ✅ إرجاع المستخدم الكامل
    return role_checker


# Pre-configured role checkers
require_admin = require_roles(["admin"])
require_buyer = require_roles(["buyer", "admin"])
require_owner = require_roles(["owner", "admin"])
