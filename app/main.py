from fastapi import FastAPI, Request, Depends, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
from typing import Optional

from app.config.settings import settings
from app.localization.loader import make_gettext, get_direction, get_available_languages

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title=settings.app_name,
    description="أرضية — Real Estate Platform",
    version="0.1.0",
    debug=settings.debug,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_lang(request: Request) -> str:
    lang = request.cookies.get("lang")
    if lang and lang in settings.languages:
        return lang
    return settings.default_language


def render_context(request: Request, lang: str, **extra) -> dict:
    _ = make_gettext(lang)
    return {
        "request": request,
        "_": _,
        "lang": lang,
        "dir": get_direction(lang),
        "app_name": settings.app_name,
        "languages": get_available_languages(),
        "debug": settings.debug,
        **extra,
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, lang: str = Depends(get_lang)):
    ctx = render_context(request, lang, active_page="home")
    return templates.TemplateResponse("home.html", ctx)


@app.get("/properties", response_class=HTMLResponse)
async def properties(request: Request, lang: str = Depends(get_lang)):
    ctx = render_context(request, lang, active_page="properties")
    return templates.TemplateResponse("properties/index.html", ctx)


@app.get("/properties/{property_id}", response_class=HTMLResponse)
async def property_detail(request: Request, property_id: int, lang: str = Depends(get_lang)):
    ctx = render_context(request, lang, active_page="properties")
    return templates.TemplateResponse("properties/detail.html", ctx)


@app.get("/favorites", response_class=HTMLResponse)
async def favorites(request: Request, lang: str = Depends(get_lang)):
    ctx = render_context(request, lang, active_page="favorites")
    return templates.TemplateResponse("favorites.html", ctx)


@app.get("/inquiries", response_class=HTMLResponse)
async def inquiries(request: Request, lang: str = Depends(get_lang)):
    ctx = render_context(request, lang, active_page="inquiries")
    return templates.TemplateResponse("inquiries.html", ctx)


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request, lang: str = Depends(get_lang)):
    ctx = render_context(request, lang, active_page="login")
    return templates.TemplateResponse("auth/login.html", ctx)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, lang: str = Depends(get_lang)):
    ctx = render_context(request, lang, active_page="dashboard")
    return templates.TemplateResponse("dashboard/index.html", ctx)


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, lang: str = Depends(get_lang)):
    ctx = render_context(request, lang, active_page="admin")
    return templates.TemplateResponse("admin/index.html", ctx)


# ===== AI CHAT ROUTE =====
@app.get("/ai-chat", response_class=HTMLResponse)
async def ai_chat(request: Request, lang: str = Depends(get_lang)):
    ctx = render_context(request, lang, active_page="chat")
    return templates.TemplateResponse("ai-chat/index.html", ctx)
# ===== END AI CHAT ROUTE =====


@app.post("/set-lang/{lang_code}")
async def set_lang(lang_code: str, response: Response):
    if lang_code in settings.languages:
        response.set_cookie(key="lang", value=lang_code, httponly=True, max_age=31536000)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
