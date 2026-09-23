import json
from pathlib import Path
from functools import lru_cache
from typing import Dict, Optional

from app.config.settings import settings

_LOCALE_DIR = Path(__file__).parent


@lru_cache(maxsize=8)
def _load_translations() -> Dict[str, Dict[str, str]]:
    translations: Dict[str, Dict[str, str]] = {}
    for lang in settings.languages:
        filepath = _LOCALE_DIR / f"{lang}.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                translations[lang] = json.load(f)
        else:
            translations[lang] = {}
    return translations


def get_translation(lang: str, key: str, default: Optional[str] = None) -> str:
    """جلب ترجمة مفتاح مع دعم fallback للغة الافتراضية ثم القيمة الافتراضية."""
    translations = _load_translations()

    # 1) اللغة المطلوبة
    table = translations.get(lang, {})
    if key in table and table[key]:
        return table[key]

    # 2) اللغة الافتراضية
    default_table = translations.get(settings.DEFAULT_LANGUAGE, {})
    if key in default_table and default_table[key]:
        return default_table[key]

    # 3) القيمة الافتراضية
    if default is not None:
        return default

    # 4) كحل أخير
    return key


def make_gettext(lang: str):
    """ينشئ دالة _() مرتبطة بلغة معينة وتدعم القيمة الافتراضية."""
    def _(key: str, default: Optional[str] = None) -> str:
        return get_translation(lang, key, default)
    return _


def get_direction(lang: str) -> str:
    return "rtl" if lang == "ar" else "ltr"


def get_available_languages() -> list[dict]:
    return [
        {"code": lang, "name": _lang_name(lang), "dir": get_direction(lang)}
        for lang in settings.languages
    ]


def _lang_name(code: str) -> str:
    names = {"ar": "العربية", "en": "English"}
    return names.get(code, code)
