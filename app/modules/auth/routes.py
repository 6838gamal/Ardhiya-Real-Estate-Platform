"""Auth module routes."""
import secrets
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse

from app.config.database import get_db
from app.modules.auth.dependencies import (
    get_auth_service,
    get_current_user,
    get_current_user_optional,
    require_admin
)
from app.modules.auth.schemas import (
    GoogleLoginURLResponse,
    SessionResponse,
    UserInfoResponse,
    ErrorResponse
)
from app.modules.auth.services import AuthService
from app.config.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Store state in memory (use Redis in production)
_state_store = {}


@router.get("/login", response_model=GoogleLoginURLResponse)
async def login_with_google(
    auth_service: AuthService = Depends(get_auth_service),
    redirect_after: Optional[str] = None
):
    """
    Initiate Google OAuth login flow.
    Returns URL to redirect user to Google consent screen.
    """
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state with optional redirect
    _state_store[state] = {
        "created_at": datetime.utcnow().isoformat(),
        "redirect_after": redirect_after or "/dashboard"
    }

    # Generate OAuth URL
    auth_url = auth_service.generate_oauth_url(state)

    return GoogleLoginURLResponse(auth_url=auth_url)


@router.get("/callback")
async def oauth_callback(
    request: Request,
    response: Response,
    code: str,
    state: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    OAuth callback endpoint.
    Exchanges code for tokens and creates session.
    """
    # Validate state
    stored_state = _state_store.pop(state, None)
    if not stored_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )

    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        # Handle callback and create session
        result = await auth_service.handle_callback(
            code=code,
            state=state,
            stored_state=state,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Set session cookie
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=result["session"].session_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=settings.JWT_EXPIRE_MINUTES * 60
        )

        # Redirect to original page or dashboard
        redirect_url = stored_state.get("redirect_after", "/dashboard")
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    except HTTPException as e:
        # Redirect to login with error
        return RedirectResponse(
            url=f"/login?error={e.detail}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session = Depends(get_current_user_optional)
):
    """Destroy current session and clear cookie."""
    if session:
        db = get_db().__next__()
        session_service = get_session_service(db)
        session_service.revoke_session(session.id)

    # Clear cookie
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax"
    )

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    session = Depends(get_current_user)
):
    """Get current authenticated user info."""
    user = session.user
    return UserInfoResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        picture=user.picture,
        is_authenticated=True
    )


@router.get("/session", response_model=SessionResponse)
async def get_current_session(
    session = Depends(get_current_user)
):
    """Get current session information."""
    user = session.user
    return SessionResponse(
        user_id=user.id,
        role=user.role,
        email=user.email,
        name=user.name,
        expires_at=session.expires_at,
        created_at=session.created_at
    )


@router.post("/session/extend")
async def extend_session(
    session = Depends(get_current_user),
    session_service = Depends(get_session_service)
):
    """Extend current session expiry."""
    extended = session_service.extend_session(session.id)
    if not extended:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to extend session"
        )
    return {"message": "Session extended"}


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    session = Depends(get_current_user),
    session_service = Depends(get_session_service)
):
    """Revoke all sessions for current user."""
    count = session_service.revoke_all_user_sessions(session.user_id)
    return {"message": f"Revoked {count} sessions"}


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: int,
    session = Depends(get_current_user),
    session_service = Depends(get_session_service),
    # Only admins can revoke other users' sessions
    _ = Depends(require_admin)
):
    """Revoke a specific session (admin only)."""
    success = session_service.revoke_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return {"message": "Session revoked"}
