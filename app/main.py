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
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse

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
from app.modules.auth.services import SessionService
from app.modules.users.services import UserService
from app.modules.users.models import User
from app.config.database import engine, SessionLocal

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# دوال تهيئة قاعدة البيانات
# ============================================================

async def run_migrations():
    """
    تشغيل ترحيلات Alembic تلقائياً عند بدء التطبيق.

    نستخدم settings.database_url دائمًا (المُحوَّل إلى psycopg2)
    لضمان استخدام Alembic لنفس driver المتزامن.
    """
    print("🔄 جاري تشغيل ترحيلات قاعدة البيانات...")

    # حفظ URL الأصلي لاستعادته لاحقًا
    original_db_url = os.environ.get("DATABASE_URL")

    try:
        # ✅ استخدم دائمًا الـ URL المُحوَّل من settings (psycopg2)
        db_url = settings.database_url

        # ✅ طباعة آمنة (بدون كشف كلمة المرور)
        print(f"📊 استخدام قاعدة البيانات (لـ Alembic): {settings.database_url_safe}")

        # تعيين DATABASE_URL في متغيرات البيئة ليستخدمها alembic.ini
        os.environ["DATABASE_URL"] = db_url

        # الحصول على مسار المشروع
        project_dir = os.getcwd()
        alembic_ini_path = os.path.join(project_dir, "alembic.ini")

        # التحقق من وجود ملف alembic.ini
        if not os.path.exists(alembic_ini_path):
            print("⚠️ ملف alembic.ini غير موجود. تخطي تشغيل الترحيلات.")
            return False

        # تشغيل alembic upgrade head باستخدام subprocess
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            env=os.environ.copy()
        )

        if result.returncode == 0:
            print("✅ تم تشغيل الترحيلات بنجاح")
            if result.stdout:
                lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
                for line in lines[-5:]:  # عرض آخر 5 أسطر فقط
                    print(f"   {line}")
            return True

        # قد يكون الخطأ بسبب عدم وجود ترحيلات جديدة
        error_msg = result.stderr.strip() if result.stderr else "خطأ غير معروف"

        # أخطاء شائعة غير حرجة
        non_fatal_markers = [
            "No such revision",
            "target database is not up to date",
            "No migration",
            "already exists",
        ]
        if any(marker in error_msg for marker in non_fatal_markers):
            print("ℹ️ قاعدة البيانات محدثة بالفعل (لا توجد ترحيلات جديدة)")
            return True

        print(f"⚠️ فشل تشغيل الترحيلات: {error_msg}")
        return False

    except subprocess.CalledProcessError as e:
        print(f"⚠️ خطأ في تشغيل الترحيلات (قد تكون الترحيلات مطبقة بالفعل): {e.stderr if e.stderr else str(e)}")
        return False
    except Exception as e:
        print(f"⚠️ خطأ غير متوقع في تشغيل الترحيلات: {str(e)}")
        return False
    finally:
        # ✅ استعادة DATABASE_URL الأصلي بشكل صحيح
        if original_db_url is not None:
            os.environ["DATABASE_URL"] = original_db_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]


def ensure_database_schema():
    """
    التأكد من وجود جميع الأعمدة المطلوبة في قاعدة البيانات.

    يستخدم SessionLocal المتزامن (psycopg2) — آمن من داخل lifespan
    لأنه لا يحتوي على أي await.
    """
    print("🔧 جاري التحقق من هيكل قاعدة البيانات...")

    db = SessionLocal()
    try:
        from sqlalchemy import text

        # ----- التحقق من جدول users -----
        users_exists = db.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'users')"
        )).scalar()

        if users_exists:
            print("✅ جدول 'users' موجود")

            # ✅ أنواع الأعمدة الصحيحة بدل VARCHAR(500) للجميع
            users_columns = {
                "avatar_url": "VARCHAR(500)",
                "phone": "VARCHAR(50)",
                "bio": "TEXT",
                "last_login": "TIMESTAMP WITH TIME ZONE",
                "updated_at": "TIMESTAMP WITH TIME ZONE",
            }
            for col, col_type in users_columns.items():
                exists = db.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    f"WHERE table_name = 'users' AND column_name = '{col}')"
                )).scalar()
                if not exists:
                    print(f"⚠️ العمود '{col}' غير موجود في جدول users، جاري الإضافة...")
                    db.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
                    db.commit()
                    print(f"✅ تم إضافة العمود '{col}'")

        # ----- التحقق من جدول user_profiles -----
        profiles_exists = db.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'user_profiles')"
        )).scalar()

        if profiles_exists:
            print("✅ جدول 'user_profiles' موجود")

            profiles_columns = {
                "preferred_language": "VARCHAR(10)",
                "preferred_currency": "VARCHAR(10)",
                "notifications_enabled": "BOOLEAN DEFAULT TRUE",
                "marketing_emails": "BOOLEAN DEFAULT FALSE",
                "updated_at": "TIMESTAMP WITH TIME ZONE",
            }
            for col, col_type in profiles_columns.items():
                exists = db.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    f"WHERE table_name = 'user_profiles' AND column_name = '{col}')"
                )).scalar()
                if not exists:
                    print(f"⚠️ العمود '{col}' غير موجود في جدول user_profiles، جاري الإضافة...")
                    db.execute(text(f"ALTER TABLE user_profiles ADD COLUMN {col} {col_type}"))
                    db.commit()
                    print(f"✅ تم إضافة العمود '{col}'")

        print("✅ تم التحقق من هيكل قاعدة البيانات بنجاح")

    except Exception as e:
        print(f"⚠️ خطأ في التحقق من هيكل قاعدة البيانات: {str(e)}")
        db.rollback()
    finally:
        db.close()


def init_database():
    """تهيئة قاعدة البيانات وإنشاء المستخدمين الأوليين إذا لزم الأمر."""
    print("🌱 جاري تهيئة قاعدة البيانات...")

    db = SessionLocal()
    try:
        from app.modules.users.models import User
        from app.modules.auth.security import get_password_hash
        from sqlalchemy import select, func

        # ✅ عدّ المستخدمين بكفاءة بدل جلبهم جميعًا
        count = db.execute(select(func.count()).select_from(User)).scalar() or 0

        if count == 0:
            print("📝 لا يوجد مستخدمين. جاري إنشاء المستخدم الافتراضي...")

            # ✅ قراءة كلمة المرور من env للأمان
            default_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")
            default_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@ardiya.com")

            admin_user = User(
                name="مدير النظام",
                email=default_email,
                password_hash=get_password_hash(default_password),
                role="admin",
                is_active=True,
                is_verified=True,
            )
            db.add(admin_user)
            db.commit()
            print(f"✅ تم إنشاء المستخدم الافتراضي ({admin_user.email})")
            if "DEFAULT_ADMIN_PASSWORD" not in os.environ:
                print("⚠️ تم استخدام كلمة مرور افتراضية. "
                      "عيّن DEFAULT_ADMIN_PASSWORD في متغيرات البيئة للإنتاج!")
        else:
            print(f"ℹ️ يوجد {count} مستخدم في النظام")

        print("✅ تم تهيئة قاعدة البيانات بنجاح")

    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {str(e)}")
        db.rollback()
    finally:
        db.close()


# ============================================================
# Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    print("🚀 Starting application...")
    # ✅ طباعة آمنة (بدون كشف كلمة المرور)
    print(f"📊 Database: {settings.database_url_safe}")
    print(f"🌍 Environment: {settings.APP_ENV}")

    # ============================================================
    # الخطوة 0: تنظيف الجلسات منتهية الصلاحية (مع تجاهل الأخطاء)
    # ============================================================
    db = SessionLocal()
    try:
        session_service = SessionService(db)
        expired_count = session_service.cleanup_expired_sessions()
        if expired_count > 0:
            print(f"🧹 تم تنظيف {expired_count} جلسة منتهية الصلاحية")
    except Exception as e:
        # تجاهل الخطأ إذا كان الجدول غير موجود
        err = str(e).lower()
        if "relation" in err and "does not exist" in err:
            print("ℹ️ جدول الجلسات غير موجود بعد، سيتم إنشاؤه في الترحيلات")
        else:
            print(f"⚠️ خطأ في تنظيف الجلسات: {e}")
    finally:
        db.close()

    # ============================================================
    # الخطوة 1: تشغيل ترحيلات Alembic
    # ============================================================
    await run_migrations()

    # ============================================================
    # الخطوة 2: التحقق من هيكل قاعدة البيانات
    # ============================================================
    ensure_database_schema()

    # ============================================================
    # الخطوة 3: تهيئة قاعدة البيانات
    # ============================================================
    init_database()

    print("✅ التطبيق جاهز للاستخدام!")
    yield

    # ============================================================
    # إيقاف التطبيق
    # ============================================================
    print("🛑 Shutting down application...")
    engine.dispose()
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
    current_user: Optional[User] = None,
    **extra
) -> dict:
    """Render template context with user info."""
    _ = make_gettext(lang)

    # إذا لم يتم تمرير current_user، حاول جلبها من الطلب
    if current_user is None:
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_token:
            db = SessionLocal()
            try:
                session_service = SessionService(db)
                session = session_service.get_session(session_token)
                if session:
                    user_service = UserService(db)
                    user = user_service.get_user_by_id(session.user_id)
                    if user and user.is_active:
                        current_user = user
            except Exception as e:
                logger.error(f"Error getting session: {e}")
            finally:
                db.close()

    # تحويل المستخدم إلى قاموس للقالب
    user_dict = None
    if current_user:
        user_dict = {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
            # ✅ استخدام getattr لتجنب AttributeError
            "avatar_url": getattr(current_user, "avatar_url", None),
            "picture": getattr(current_user, "avatar_url", None),
            "is_authenticated": True,
        }

    return {
        "request": request,
        "_": _,
        "lang": lang,
        "dir": get_direction(lang),
        "app_name": settings.APP_NAME,
        "languages": get_available_languages(),
        "debug": settings.DEBUG,
        "current_user": user_dict,
        **extra,
    }


# ===== Home Routes =====
@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Home page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="home"
    )
    return templates.TemplateResponse("home.html", ctx)


@app.get("/properties", response_class=HTMLResponse)
async def properties(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Properties listing page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="properties"
    )
    return templates.TemplateResponse("properties/index.html", ctx)


@app.get("/properties/{property_id}", response_class=HTMLResponse)
async def property_detail(
    request: Request,
    property_id: int,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Property detail page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="properties"
    )
    return templates.TemplateResponse("properties/detail.html", ctx)


@app.get("/favorites", response_class=HTMLResponse)
async def favorites(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Favorites page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="favorites"
    )
    return templates.TemplateResponse("favorites.html", ctx)


@app.get("/inquiries", response_class=HTMLResponse)
async def inquiries(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Inquiries page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="inquiries"
    )
    return templates.TemplateResponse("inquiries.html", ctx)


@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Login page.
    Redirect to dashboard if already authenticated.
    """
    if current_user:
        return RedirectResponse(
            url="/dashboard",
            status_code=status.HTTP_302_FOUND
        )

    error = request.query_params.get("error")
    success = request.query_params.get("success")

    ctx = await render_context(
        request, lang, current_user=None,
        active_page="login", error=error, success=success
    )
    return templates.TemplateResponse("auth/login.html", ctx)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: User = Depends(get_current_user)
):
    """
    Dashboard page.
    Requires authentication.
    """
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="dashboard"
    )
    return templates.TemplateResponse("dashboard/index.html", ctx)


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: User = Depends(get_current_user)
):
    """
    Admin panel page.
    Requires authentication and admin role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    ctx = await render_context(
        request, lang, current_user=current_user, active_page="admin"
    )
    return templates.TemplateResponse("admin/index.html", ctx)


@app.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: User = Depends(get_current_user)
):
    """User profile page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="profile"
    )
    return templates.TemplateResponse("profile.html", ctx)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: User = Depends(get_current_user)
):
    """User settings page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="settings"
    )
    return templates.TemplateResponse("settings.html", ctx)


# ===== AI Chat Route =====
@app.get("/ai-chat", response_class=HTMLResponse)
async def ai_chat(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """AI Chat page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="chat"
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
            httponly=settings.COOKIE_HTTPONLY,
            max_age=31536000,  # 1 year
            secure=settings.is_secure_cookie,
            samesite=settings.COOKIE_SAMESITE
        )
        return {"ok": True}
    return JSONResponse(
        {"ok": False, "error": "Unsupported language"},
        status_code=400
    )


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


# ===== Favicon (لتجنب 404 المتكرر) =====
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve favicon if present; otherwise return 204 No Content."""
    favicon_path = BASE_DIR / "static" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    return Response(status_code=204)


# ===== Exception Handlers =====
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(
            url="/login",
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

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if settings.is_prod:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


# ===== Static Pages =====
@app.get("/about", response_class=HTMLResponse)
async def about(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """About page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="about"
    )
    return templates.TemplateResponse("about.html", ctx)


@app.get("/contact", response_class=HTMLResponse)
async def contact(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Contact page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="contact"
    )
    return templates.TemplateResponse("contact.html", ctx)


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Privacy policy page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="privacy"
    )
    return templates.TemplateResponse("privacy.html", ctx)


@app.get("/terms", response_class=HTMLResponse)
async def terms(
    request: Request,
    lang: str = Depends(get_lang),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Terms of service page."""
    ctx = await render_context(
        request, lang, current_user=current_user, active_page="terms"
    )
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
