"""
Application entry point for أرضية — Real Estate Platform.

Assembles the FastAPI app, mounts static files, configures Jinja2,
registers all web and API routers, and wires exception handlers.
Handles database migrations and initialization on startup.
"""
import logging
import subprocess
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Depends, Response, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import secrets

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("app.main")

from app.config.settings import settings
from app.localization.loader import make_gettext, get_direction, get_available_languages
from app.modules.auth.routes import router as auth_router
from app.modules.users.routes import router as users_router
from app.modules.auth.dependencies import get_current_user_optional, get_current_user
from app.modules.auth.services import AuthService, SessionService
from app.config.database import get_db, engine

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# دوال تهيئة قاعدة البيانات
# ============================================================

async def run_migrations():
    """
    تشغيل ترحيلات Alembic تلقائياً عند بدء التطبيق
    
    هذه الدالة تقوم بتشغيل جميع الترحيلات المعلقة لتحديث هيكل قاعدة البيانات
    إلى أحدث إصدار. يتم تشغيلها مرة واحدة عند بدء التطبيق.
    """
    print("🔄 جاري تشغيل ترحيلات قاعدة البيانات...")
    
    # حفظ URL الأصلي
    original_db_url = os.environ.get("DATABASE_URL")
    
    try:
        # الحصول على DATABASE_URL من متغيرات البيئة أو الإعدادات
        db_url = original_db_url
        if not db_url:
            db_url = settings.DATABASE_URL
        
        # تحويل URL من asyncpg إلى psycopg2 لـ Alembic
        # Alembic لا يدعم asyncpg، لذلك نحتاج إلى استخدام psycopg2
        sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # طباعة معلومات للتتبع (مع إخفاء كلمة المرور)
        if '@' in sync_url:
            parts = sync_url.split('@')
            if len(parts) > 1:
                print(f"📊 استخدام قاعدة البيانات (لـ Alembic): {parts[1]}")
        
        # تعيين DATABASE_URL في متغيرات البيئة ليستخدمها alembic.ini
        os.environ["DATABASE_URL"] = sync_url
        
        # الحصول على مسار المشروع
        project_dir = os.getcwd()
        alembic_ini_path = os.path.join(project_dir, "alembic.ini")
        
        # التحقق من وجود ملف alembic.ini
        if not os.path.exists(alembic_ini_path):
            print("⚠️ ملف alembic.ini غير موجود. تخطي تشغيل الترحيلات.")
            # استعادة URL الأصلي
            if original_db_url:
                os.environ["DATABASE_URL"] = original_db_url
            return False
        
        # تشغيل alembic upgrade head باستخدام subprocess
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            env=os.environ.copy()
        )
        
        # استعادة URL الأصلي
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        
        if result.returncode == 0:
            print("✅ تم تشغيل الترحيلات بنجاح")
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:  # عرض آخر 5 أسطر فقط
                    if line.strip():
                        print(f"   {line}")
            return True
        else:
            # قد يكون الخطأ بسبب عدم وجود ترحيلات جديدة
            error_msg = result.stderr.strip() if result.stderr else "خطأ غير معروف"
            
            # أخطاء شائعة غير حرجة
            if "No such revision" in error_msg:
                print("ℹ️ قاعدة البيانات محدثة بالفعل (لا توجد ترحيلات جديدة)")
                return True
            elif "target database is not up to date" in error_msg:
                print("ℹ️ قاعدة البيانات محدثة بالفعل")
                return True
            elif "No migration" in error_msg:
                print("ℹ️ لا توجد ترحيلات جديدة")
                return True
            else:
                print(f"⚠️ فشل تشغيل الترحيلات: {error_msg}")
                # لا نوقف التطبيق، نكمل بـ ensure_database_schema
                return False
            
    except subprocess.CalledProcessError as e:
        print(f"⚠️ خطأ في تشغيل الترحيلات (قد تكون الترحيلات مطبقة بالفعل): {e.stderr if e.stderr else str(e)}")
        # استعادة URL الأصلي
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        return False
    except Exception as e:
        print(f"⚠️ خطأ غير متوقع في تشغيل الترحيلات: {str(e)}")
        # استعادة URL الأصلي
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        # نكمل التطبيق ولا نوقفه
        return False


async def ensure_database_schema():
    """
    التأكد من وجود جميع الأعمدة المطلوبة في قاعدة البيانات
    
    هذه الدالة تضيف الأعمدة المفقودة في الجداول الموجودة
    لتجنب أخطاء SQLAlchemy عند تشغيل التطبيق.
    """
    print("🔧 جاري التحقق من هيكل قاعدة البيانات...")
    
    try:
        from sqlalchemy import text
        from app.config.database import get_db
        
        async for db in get_db():
            try:
                # هنا يمكن إضافة فحوصات للأعمدة المفقودة حسب الحاجة
                # مثال: التحقق من وجود عمود معين في جدول users
                await db.execute(text("""
                    DO $$
                    BEGIN
                        -- يمكن إضافة فحوصات للأعمدة المفقودة هنا
                        -- مثال:
                        -- IF NOT EXISTS (
                        --     SELECT 1 FROM information_schema.columns 
                        --     WHERE table_name = 'users' AND column_name = 'avatar_url'
                        -- ) THEN
                        --     ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);
                        -- END IF;
                    END $$;
                """))
                
                await db.commit()
                print("✅ تم التحقق من هيكل قاعدة البيانات بنجاح")
                break
            except Exception as e:
                print(f"⚠️ خطأ في التحقق من هيكل قاعدة البيانات: {str(e)}")
                await db.rollback()
                break
    except Exception as e:
        print(f"⚠️ خطأ في الاتصال بقاعدة البيانات: {str(e)}")


async def init_database():
    """تهيئة قاعدة البيانات وإنشاء المستخدمين الأوليين إذا لزم الأمر."""
    print("🌱 جاري تهيئة قاعدة البيانات...")
    
    try:
        from app.modules.users.services import UserService
        from app.modules.users.models import User
        from app.modules.auth.services import AuthService
        from app.config.database import get_db
        from app.modules.auth.models import Session as SessionModel
        from sqlalchemy import select
        
        async for db in get_db():
            try:
                # التحقق من وجود مستخدمين
                stmt = select(User)
                result = await db.execute(stmt)
                users = result.scalars().all()
                
                if len(users) == 0:
                    print("📝 لا يوجد مستخدمين. جاري إنشاء المستخدم الافتراضي...")
                    
                    # إنشاء مستخدم مدير افتراضي
                    from app.modules.auth.security import get_password_hash
                    
                    admin_user = User(
                        name="مدير النظام",
                        email="admin@ardiya.com",
                        password_hash=get_password_hash("Admin@123"),
                        role="admin",
                        is_active=True,
                        is_verified=True
                    )
                    db.add(admin_user)
                    await db.commit()
                    print("✅ تم إنشاء المستخدم الافتراضي (admin@ardiya.com / Admin@123)")
                else:
                    print(f"ℹ️ يوجد {len(users)} مستخدم في النظام")
                
                print("✅ تم تهيئة قاعدة البيانات بنجاح")
                break
                
            except Exception as e:
                print(f"❌ خطأ في تهيئة قاعدة البيانات: {str(e)}")
                await db.rollback()
                break
                
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {str(e)}")


# ============================================================
# Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    يتم تشغيل هذا الكود عند بدء التطبيق وإيقافه.
    الترتيب:
    1. تنظيف الجلسات منتهية الصلاحية
    2. تشغيل ترحيلات Alembic (تحديث هيكل قاعدة البيانات)
    3. التحقق من هيكل قاعدة البيانات (إضافة الأعمدة المفقودة)
    4. تهيئة البيانات الأساسية (المستخدمين)
    5. إغلاق اتصال قاعدة البيانات عند الإيقاف
    """
    print("🚀 Starting application...")
    print(f"📊 Database: {settings.DATABASE_URL}")
    
    # ============================================================
    # الخطوة 0: تنظيف الجلسات منتهية الصلاحية
    # ============================================================
    try:
        db = next(get_db())
        session_service = SessionService(db)
        expired_count = session_service.cleanup_expired_sessions()
        if expired_count > 0:
            print(f"🧹 تم تنظيف {expired_count} جلسة منتهية الصلاحية")
    except Exception as e:
        print(f"⚠️ خطأ في تنظيف الجلسات: {e}")
    
    # ============================================================
    # الخطوة 1: تشغيل ترحيلات Alembic
    # ============================================================
    await run_migrations()
    
    # ============================================================
    # الخطوة 2: التحقق من هيكل قاعدة البيانات (إضافة الأعمدة المفقودة)
    # ============================================================
    await ensure_database_schema()
    
    # ============================================================
    # الخطوة 3: تهيئة قاعدة البيانات (المستخدمين)
    # ============================================================
    await init_database()
    
    print("✅ التطبيق جاهز للاستخدام!")
    yield
    
    # ============================================================
    # إيقاف التطبيق
    # ============================================================
    print("🛑 Shutting down application...")
    
    # إغلاق اتصال قاعدة البيانات عند الإيقاف
    await engine.dispose()
    print("✅ Database connection closed.")


# ============================================================
# إنشاء التطبيق
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    description="أرضية — Real Estate Platform",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
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
        # استخدام cookie مباشرة بدلاً من get_current_user_optional
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_token:
            try:
                db = next(get_db())
                session_service = SessionService(db)
                session = session_service.get_session(session_token)
                if session:
                    from app.modules.users.services import UserService
                    user = UserService.get_user_by_id(session.user_id)
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
            except Exception as e:
                print(f"Error getting session: {e}")
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
        from app.modules.users.services import UserService
        user = UserService.get_user_by_id(session.user_id)
        
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
    from app.modules.users.services import UserService
    user = UserService.get_user_by_id(session.user_id)
    
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
    from app.modules.users.services import UserService
    user = UserService.get_user_by_id(session.user_id)
    
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
    from app.modules.users.services import UserService
    user = UserService.get_user_by_id(session.user_id)
    
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
    from app.modules.users.services import UserService
    user = UserService.get_user_by_id(session.user_id)
    
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
        from app.modules.users.services import UserService
        user_obj = UserService.get_user_by_id(session.user_id)
        
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


# ============================================================
# تشغيل التطبيق (للتطوير المحلي)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
