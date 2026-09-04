from fastapi import FastAPI, Request, Depends, Response, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pathlib import Path
from typing import Optional
import secrets

from app.config.settings import settings
from app.localization.loader import make_gettext, get_direction, get_available_languages
from app.modules.auth.routes import router as auth_router
from app.modules.users.routes import router as users_router
from app.modules.auth.dependencies import get_current_user_optional, get_current_user
from app.modules.auth.services import AuthService, SessionService
from app.config.database import get_db

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title=settings.APP_NAME,
    description="أرضية — Real Estate Platform",
    version="0.1.0",
    debug=settings.DEBUG,
)

# ===== Static Files =====
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ===== Templates =====
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ===== Routers =====
app.include_router(auth_router)
app.include_router(users_router)


# ===== Dependencies =====
def get_lang(request: Request) -> str:
    """Get language from cookie or default."""
    lang = request.cookies.get("lang")
    if lang and lang in settings.languages:
        return lang
    return settings.DEFAULT_LANGUAGE


# ===== Context Helper =====
async def render_context(
    request: Request,
    lang: str,
    current_user: Optional[dict] = None,
    **extra
) -> dict:
    """Render template context with user info."""
    _ = make_gettext(lang)
    
    # Get current user if not provided
    if current_user is None:
        # Try to get user from session
        session = await get_current_user_optional(request)
        if session:
            # ✅ استخدام UserService بدون db
            from app.modules.users.services import UserService
            user_service = UserService()
            user = user_service.get_by_id(session.user_id)
            
            if user:
                current_user = {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "picture": user.picture,
                    "is_authenticated": True
                }
            else:
                current_user = None
        else:
            current_user = None
    
    return {
        "request": request,
        "_": _,
        "lang": lang,
        "dir": get_direction(lang),
        "app_name": settings.APP_NAME,
        "languages": get_available_languages(),
        "debug": settings.DEBUG,
        "current_user": current_user,
        **extra,
    }


# ===== Home Routes =====
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, lang: str = Depends(get_lang)):
    """Home page."""
    ctx = await render_context(request, lang, active_page="home")
    return templates.TemplateResponse("home.html", ctx)


@app.get("/properties", response_class=HTMLResponse)
async def properties(request: Request, lang: str = Depends(get_lang)):
    """Properties listing page."""
    ctx = await render_context(request, lang, active_page="properties")
    return templates.TemplateResponse("properties/index.html", ctx)


@app.get("/properties/{property_id}", response_class=HTMLResponse)
async def property_detail(request: Request, property_id: int, lang: str = Depends(get_lang)):
    """Property detail page."""
    ctx = await render_context(request, lang, active_page="properties")
    return templates.TemplateResponse("properties/detail.html", ctx)


@app.get("/favorites", response_class=HTMLResponse)
async def favorites(request: Request, lang: str = Depends(get_lang)):
    """Favorites page."""
    ctx = await render_context(request, lang, active_page="favorites")
    return templates.TemplateResponse("favorites.html", ctx)


@app.get("/inquiries", response_class=HTMLResponse)
async def inquiries(request: Request, lang: str = Depends(get_lang)):
    """Inquiries page."""
    ctx = await render_context(request, lang, active_page="inquiries")
    return templates.TemplateResponse("inquiries.html", ctx)


@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    lang: str = Depends(get_lang),
    session = Depends(get_current_user_optional)
):
    """
    Login page.
    Redirect to dashboard if already authenticated.
    """
    # If user is already logged in, redirect to dashboard
    if session:
        # ✅ استخدام UserService بدون db
        from app.modules.users.services import UserService
        user_service = UserService()
        user = user_service.get_by_id(session.user_id)
        
        if user:
            return RedirectResponse(
                url=settings.get_frontend_url(settings.FRONTEND_DASHBOARD_URL),
                status_code=status.HTTP_302_FOUND
            )
    
    # Get error/success messages from query params
    error = request.query_params.get("error")
    success = request.query_params.get("success")
    
    ctx = await render_context(
        request,
        lang,
        active_page="login",
        error=error,
        success=success
    )
    return templates.TemplateResponse("auth/login.html", ctx)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    lang: str = Depends(get_lang),
    session = Depends(get_current_user)
):
    """
    Dashboard page.
    Requires authentication.
    """
    # ✅ استخدام UserService بدون db
    from app.modules.users.services import UserService
    user_service = UserService()
    user = user_service.get_by_id(session.user_id)
    
    ctx = await render_context(
        request,
        lang,
        current_user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "picture": user.picture,
            "is_authenticated": True
        } if user else None,
        active_page="dashboard"
    )
    return templates.TemplateResponse("dashboard/index.html", ctx)


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    lang: str = Depends(get_lang),
    session = Depends(get_current_user)
):
    """
    Admin panel page.
    Requires authentication and admin role.
    """
    # ✅ استخدام UserService بدون db
    from app.modules.users.services import UserService
    user_service = UserService()
    user = user_service.get_by_id(session.user_id)
    
    # Check if user has admin role
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    ctx = await render_context(
        request,
        lang,
        current_user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "picture": user.picture,
            "is_authenticated": True
        },
        active_page="admin"
    )
    return templates.TemplateResponse("admin/index.html", ctx)


@app.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    lang: str = Depends(get_lang),
    session = Depends(get_current_user)
):
    """User profile page."""
    # ✅ استخدام UserService بدون db
    from app.modules.users.services import UserService
    user_service = UserService()
    user = user_service.get_by_id(session.user_id)
    
    ctx = await render_context(
        request,
        lang,
        current_user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "picture": user.picture,
            "is_authenticated": True
        } if user else None,
        active_page="profile"
    )
    return templates.TemplateResponse("profile.html", ctx)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    lang: str = Depends(get_lang),
    session = Depends(get_current_user)
):
    """User settings page."""
    # ✅ استخدام UserService بدون db
    from app.modules.users.services import UserService
    user_service = UserService()
    user = user_service.get_by_id(session.user_id)
    
    ctx = await render_context(
        request,
        lang,
        current_user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "picture": user.picture,
            "is_authenticated": True
        } if user else None,
        active_page="settings"
    )
    return templates.TemplateResponse("settings.html", ctx)


# ===== AI Chat Route =====
@app.get("/ai-chat", response_class=HTMLResponse)
async def ai_chat(
    request: Request,
    lang: str = Depends(get_lang),
    session = Depends(get_current_user_optional)
):
    """AI Chat page."""
    user = None
    if session:
        # ✅ استخدام UserService بدون db
        from app.modules.users.services import UserService
        user_service = UserService()
        user_obj = user_service.get_by_id(session.user_id)
        
        if user_obj:
            user = {
                "id": user_obj.id,
                "name": user_obj.name,
                "email": user_obj.email,
                "role": user_obj.role,
                "picture": user_obj.picture,
                "is_authenticated": True
            }
    
    ctx = await render_context(
        request,
        lang,
        current_user=user,
        active_page="chat"
    )
    return templates.TemplateResponse("ai-chat/index.html", ctx)


# ===== Language Switcher =====
@app.post("/set-lang/{lang_code}")
async def set_lang(lang_code: str, response: Response):
    """Set language cookie."""
    if lang_code in settings.languages:
        response.set_cookie(
            key="lang",
            value=lang_code,
            httponly=True,
            max_age=31536000,  # 1 year
            secure=settings.is_secure_cookie,
            samesite=settings.COOKIE_SAMESITE
        )
        return {"ok": True}
    return {"ok": False, "error": "Unsupported language"}


# ===== Health Check =====
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "version": "0.1.0"
    }


# ===== OAuth Callback (Redirect) =====
@app.get("/auth/callback")
async def auth_callback_redirect():
    """
    Redirect to OAuth callback.
    This is handled by the auth router.
    """
    return RedirectResponse(url="/auth/callback", status_code=status.HTTP_302_FOUND)


# ===== Exception Handlers =====
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        # Redirect to login for unauthorized access
        return RedirectResponse(
            url=settings.get_frontend_url("/login"),
            status_code=status.HTTP_302_FOUND
        )
    
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": exc.detail}
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


# ===== Startup Events =====
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    # Clean up expired sessions
    try:
        db = next(get_db())
        session_service = SessionService(db)
        expired_count = session_service.cleanup_expired_sessions()
        if expired_count > 0:
            print(f"Cleaned up {expired_count} expired sessions")
    except Exception as e:
        print(f"Error cleaning up sessions: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    # Close database connections etc.
    pass


# ===== Middleware =====
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # HSTS (only in production)
    if settings.is_prod:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


# ===== Static Pages =====
@app.get("/about", response_class=HTMLResponse)
async def about(request: Request, lang: str = Depends(get_lang)):
    """About page."""
    ctx = await render_context(request, lang, active_page="about")
    return templates.TemplateResponse("about.html", ctx)


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request, lang: str = Depends(get_lang)):
    """Contact page."""
    ctx = await render_context(request, lang, active_page="contact")
    return templates.TemplateResponse("contact.html", ctx)


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request, lang: str = Depends(get_lang)):
    """Privacy policy page."""
    ctx = await render_context(request, lang, active_page="privacy")
    return templates.TemplateResponse("privacy.html", ctx)


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request, lang: str = Depends(get_lang)):
    """Terms of service page."""
    ctx = await render_context(request, lang, active_page="terms")
    return templates.TemplateResponse("terms.html", ctx)
