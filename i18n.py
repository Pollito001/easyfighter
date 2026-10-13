"""
Idiomas de IKEMEN GO Character Editor / IKEMEN GO Character Editor languages.

The program text is written in Spanish in the source code; every visible text goes through tr().
English is the default language. Translations live in lang/<code>.json as {"Spanish text": "translation"}.
To add a language: copy lang/en.json to lang/<code>.json (or to ~/.config/ikemen-chareditor/lang/),
set "_name" and translate the values.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
LANG_DIR = HERE / "lang"
if sys.platform == "win32":
    CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "ikemen-chareditor"
elif sys.platform == "darwin":
    CONFIG_DIR = Path.home() / "Library" / "Application Support" / "ikemen-chareditor"
else:
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ikemen-chareditor"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
DEFAULT_LANG = "en"
SOURCE_LANG = "es"  # idioma en que está escrito el código

_table = {}
LANG = DEFAULT_LANG


def _lang_files():
    """Archivos de idioma: los que vienen con la app y los del usuario (~/.config/ikemen-chareditor/lang)."""
    found = {}
    for d in (LANG_DIR, CONFIG_DIR / "lang"):
        if d.is_dir():
            for p in sorted(d.glob("*.json")):
                found[p.stem] = p  # los del usuario reemplazan a los incluidos
    return found


def available():
    """[(código, nombre)] de los idiomas disponibles."""
    out = {SOURCE_LANG: "Español"}
    for p in _lang_files().values():
        try:
            out[p.stem] = json.loads(p.read_text(encoding="utf-8")).get("_name", p.stem)
        except (OSError, ValueError):
            continue
    order = [DEFAULT_LANG] + sorted(c for c in out if c != DEFAULT_LANG)
    return [(c, out[c]) for c in order if c in out]


def set_language(code):
    global LANG, _table
    LANG = code or DEFAULT_LANG
    _table = {}
    if LANG == SOURCE_LANG:
        return
    p = _lang_files().get(LANG, LANG_DIR / f"{LANG}.json")
    try:
        _table = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        LANG = SOURCE_LANG  # sin archivo: se queda el texto original


def tr(text):
    """Traduce un texto visible. Si no hay traducción, devuelve el original."""
    return _table.get(text, text)


def saved_language():
    try:
        return json.loads(SETTINGS_FILE.read_text()).get("language", DEFAULT_LANG)
    except (OSError, ValueError):
        return DEFAULT_LANG


set_language(saved_language())
