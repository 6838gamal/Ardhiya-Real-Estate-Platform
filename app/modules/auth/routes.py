"""Auth module routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import secrets

from app.config.database import get_db
from app.config.settings import settings
from app.modules.auth.services import AuthService, SessionService
from app.modules.auth.schemas import (
    AuthInitResponse,
    AuthCallbackRequest,
    AuthCallbackResponse,
    AuthUserResponse,
    LogoutResponse,
    SessionResponse,
)
from app.modules.auth.dependencies import get_current_user, get_current_user_optional

# ✅ البادئة الرئيسية لتوافق مع Google
router = APIRouter(prefix="/auth/google", tags=["Authentication"])

# 🔧 إنشاء راوتر إضافي للتوافق مع الإصدارات السابقة
legacy_router = APIRouter(prefix="/api/auth", tags=["Authentication (Legacy)"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get AuthService instance."""
    return AuthService(db)


def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    """Get SessionService instance."""
    return SessionService(db)


# ============ المسارات الرئيسية (لـ Google) ============

@router.get("/login", response_model=AuthInitResponse)
async def initiate_login(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Initiate OAuth login with Google.
    
    Returns the Google OAuth URL and state parameter.
    """
    try:
        state = secrets.token_urlsafe(32)
        oauth_url = auth_service.generate_oauth_url(state)
        
        response = Response()
        response.set_cookie(
            key="oauth_state",
            value=state,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=600
        )
        
        return AuthInitResponse(
            oauth_url=oauth_url,
            state=state
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate login: {str(e)}"
        )


@router.get("/callback", response_model=AuthCallbackResponse)
async def auth_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Handle OAuth callback from Google.
    
    Exchanges code for tokens, creates/updates user, and creates session.
    """
    try:
        stored_state = request.cookies.get("oauth_state")
        
        if not stored_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing OAuth state"
            )
        
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        result = await auth_service.handle_callback(
            code=code,
            state=state,
            stored_state=stored_state,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        response.delete_cookie("oauth_state")
        
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=result["session"].session_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=settings.JWT_EXPIRE_MINUTES * 60
        )
        
        return AuthCallbackResponse(
            success=True,
            user=AuthUserResponse.from_orm(result["user"]),
            access_token=result["access_token"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


# ============ المسارات الأخرى (الجلسة، تسجيل الخروج، إلخ) ============

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    session_service: SessionService = Depends(get_session_service)
):
    """Logout current user."""
    try:
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        
        if session_token:
            session = session_service.get_session(session_token)
            if session:
                session_service.revoke_session(session.id)
        
        response.delete_cookie(
            key=settings.SESSION_COOKIE_NAME,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax"
        )
        
        return LogoutResponse(success=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.get("/session", response_model=Optional[SessionResponse])
async def get_session_info(
    session = Depends(get_current_user_optional)
):
    """Get current session information."""
    if not session:
        return None
    
    return SessionResponse(
        user_id=session.user_id,
        provider=session.provider,
        provider_user_id=session.provider_user_id,
        expires_at=session.expires_at,
        created_at=session.created_at
    )


@router.post("/session/extend", response_model=SessionResponse)
async def extend_session(
    session = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    """Extend current session expiry."""
    try:
        success = session_service.extend_session(session.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extend session"
            )
        
        session = session_service.get_session(session.session_token)
        
        return SessionResponse(
            user_id=session.user_id,
            provider=session.provider,
            provider_user_id=session.provider_user_id,
            expires_at=session.expires_at,
            created_at=session.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extend session: {str(e)}"
        )


@router.post("/session/revoke-all", response_model=dict)
async def revoke_all_sessions(
    session = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    """Revoke all sessions for current user."""
    try:
        count = session_service.revoke_all_user_sessions(session.user_id)
        
        return {
            "success": True,
            "revoked_count": count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke sessions: {str(e)}"
        )


@router.get("/health")
async def auth_health_check():
    """Health check endpoint for auth module."""
    return {
        "status": "healthy",
        "message": "Auth module is working"
    }


# ============ مسارات متوافقة مع الإصدارات السابقة (Legacy) ============

@legacy_router.get("/login")
async def legacy_login(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Legacy login endpoint - redirects to new endpoint."""
    return await initiate_login(request, auth_service)


@legacy_router.get("/callback")
async def legacy_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Legacy callback endpoint - redirects to new endpoint."""
    return await auth_callback(code, state, request, response, auth_service)


@legacy_router.post("/logout")
async def legacy_logout(
    request: Request,
    response: Response,
    session_service: SessionService = Depends(get_session_service)
):
    """Legacy logout endpoint."""
    return await logout(request, response, session_service)


@legacy_router.get("/session")
async def legacy_session(
    session = Depends(get_current_user_optional)
):
    """Legacy session endpoint."""
    return await get_session_info(session)
