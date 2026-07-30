from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache

_LOCALE_DIR = Path(__file__).resolve().parent.parent.parent / 'locales'

@lru_cache(maxsize=4)
def load_locale(lang: str) -> dict[str, str]:
    path = _LOCALE_DIR / f'{lang}.json'
    if not path.is_file():
        if lang == 'en':
            return {}
        return load_locale('en')
    return json.loads(path.read_text(encoding='utf-8'))

def t(key: str, lang: str = 'en', **fmt) -> str:
    locale = load_locale(lang)
    text = locale.get(key, key)
    if fmt:
        return text.format(**fmt)
    return text
