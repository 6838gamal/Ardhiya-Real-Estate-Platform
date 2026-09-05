"""Auth module routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import secrets
import logging
from urllib.parse import urlencode

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

# إعداد التسجيل
logger = logging.getLogger(__name__)

# ✅ البادئة الرئيسية لتوافق مع Google
router = APIRouter(prefix="/auth/google", tags=["Authentication"])

# 🔧 راوتر إضافي للتوافق مع الإصدارات السابقة (Legacy)
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
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Generate OAuth URL
        oauth_url = auth_service.generate_oauth_url(state)
        
        # Store state in cookie for validation
        response = Response()
        response.set_cookie(
            key="oauth_state",
            value=state,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=600  # 10 minutes
        )
        
        logger.info(f"✅ Login initiated - state: {state[:10]}...")
        
        return AuthInitResponse(
            oauth_url=oauth_url,
            state=state
        )
    except Exception as e:
        logger.error(f"❌ Failed to initiate login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate login: {str(e)}"
        )


@router.get("/callback")
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
    Redirects to home page on success.
    """
    try:
        logger.info(f"📥 Received callback - code: {code[:20]}..., state: {state[:10]}...")
        
        # Get stored state from request
        stored_state = request.cookies.get("oauth_state")
        logger.info(f"🍪 Stored state from cookie: {stored_state[:10] if stored_state else 'None'}...")
        
        if not stored_state:
            logger.error("❌ No stored state found in cookies")
            return RedirectResponse(
                url="/login?error=missing_state",
                status_code=303
            )
        
        # ✅ التحقق من تطابق الـ State
        if state != stored_state:
            logger.error(f"❌ State mismatch! Received: {state[:10]}..., Stored: {stored_state[:10]}...")
            return RedirectResponse(
                url="/login?error=invalid_state",
                status_code=303
            )
        
        logger.info("✅ State validated successfully")
        
        # Get client IP and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        logger.info(f"🔍 Processing callback - IP: {ip_address}, User-Agent: {user_agent[:50] if user_agent else 'None'}...")
        
        # Handle callback
        result = await auth_service.handle_callback(
            code=code,
            state=state,
            stored_state=stored_state,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(f"✅ Callback processed successfully for user: {result['user'].email}")
        
        # Clear the state cookie
        response.delete_cookie("oauth_state")
        
        # Set session cookie
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=result["session"].session_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=settings.JWT_EXPIRE_MINUTES * 60
        )
        
        # ✅ التوجيه إلى الصفحة الرئيسية
        logger.info(f"🔄 Redirecting to home page - User: {result['user'].email}")
        return RedirectResponse(
            url="/",
            status_code=303
        )
        
    except HTTPException as e:
        logger.error(f"❌ HTTP Exception: {e.detail}")
        return RedirectResponse(
            url=f"/login?error={e.detail}",
            status_code=303
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return RedirectResponse(
            url=f"/login?error=authentication_failed",
            status_code=303
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    session_service: SessionService = Depends(get_session_service)
):
    """
    Logout current user.
    
    Revokes the session token and clears the cookie.
    """
    try:
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        
        if session_token:
            # Get session and revoke it
            session = session_service.get_session(session_token)
            if session:
                session_service.revoke_session(session.id)
                logger.info(f"✅ Session revoked: {session_token[:20]}...")
        
        # Clear cookie
        response.delete_cookie(
            key=settings.SESSION_COOKIE_NAME,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax"
        )
        
        return LogoutResponse(success=True)
    except Exception as e:
        logger.error(f"❌ Logout failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.get("/session", response_model=Optional[SessionResponse])
async def get_session_info(
    session = Depends(get_current_user_optional)
):
    """
    Get current session information.
    
    Returns session details if authenticated, None otherwise.
    """
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
    """
    Extend current session expiry.
    
    Requires authentication.
    """
    try:
        success = session_service.extend_session(session.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extend session"
            )
        
        # Refresh session
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
        logger.error(f"❌ Failed to extend session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extend session: {str(e)}"
        )


@router.post("/session/revoke-all", response_model=dict)
async def revoke_all_sessions(
    session = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Revoke all sessions for current user.
    
    Requires authentication. All other sessions will be invalidated.
    """
    try:
        count = session_service.revoke_all_user_sessions(session.user_id)
        
        return {
            "success": True,
            "revoked_count": count
        }
    except Exception as e:
        logger.error(f"❌ Failed to revoke sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke sessions: {str(e)}"
        )


@router.get("/health")
async def auth_health_check():
    """Health check endpoint for auth module."""
    return {
        "status": "healthy",
        "message": "Auth module is working",
        "routes": {
            "login": "/auth/google/login",
            "callback": "/auth/google/callback",
            "logout": "/auth/google/logout",
            "session": "/auth/google/session",
            "health": "/auth/google/health"
        }
    }


# ============ المسارات المتوافقة مع الإصدارات السابقة (Legacy) ============

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


@legacy_router.post("/session/extend")
async def legacy_extend_session(
    session = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    """Legacy extend session endpoint."""
    return await extend_session(session, session_service)


@legacy_router.post("/session/revoke-all")
async def legacy_revoke_all_sessions(
    session = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    """Legacy revoke all sessions endpoint."""
    return await revoke_all_sessions(session, session_service)


@legacy_router.get("/health")
async def legacy_auth_health_check():
    """Legacy health check endpoint."""
    return await auth_health_check()
