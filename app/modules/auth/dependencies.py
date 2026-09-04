"""Auth module dependencies."""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.services import AuthService, SessionService
from app.modules.auth.models import UserSession
from app.core.config import settings

# OAuth2 scheme for Bearer token (future API access)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",  # Future token endpoint
    auto_error=False
)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get AuthService instance."""
    return AuthService(db)


def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    """Get SessionService instance."""
    return SessionService(db)


async def get_current_user_session(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[UserSession]:
    """Get current user session from cookie."""
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if not session_token:
        return None

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
        if not session.user.role in allowed_roles:
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
