import json
from pathlib import Path
from functools import lru_cache
from typing import Dict

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


def get_translation(lang: str, key: str) -> str:
    translations = _load_translations()
    table = translations.get(lang, translations.get(settings.default_language, {}))
    return table.get(key, key)


def make_gettext(lang: str):
    def _(key: str) -> str:
        return get_translation(lang, key)
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
