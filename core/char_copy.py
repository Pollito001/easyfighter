"""Copiar un personaje con otro nombre: la carpeta, los archivos y lo que dice el .def."""
import re
import shutil
from pathlib import Path

from core.deffile import DefFile
from core.textio import read_text, write_text


def safe_base(name):
    """Nombre que sirve para carpeta y archivos (sin espacios ni símbolos raros)."""
    return re.sub(r"[^\w\-]+", "_", name.strip()).strip("_") or "Personaje"


def free_dir(parent, base):
    dest = Path(parent) / base
    n = 2
    while dest.exists() and any(dest.iterdir()):
        dest = Path(parent) / f"{base}_{n}"
        n += 1
    return dest


def _renamed(fname, old, new):
    """El nombre nuevo de un archivo que empieza con el del personaje (Kaito.sff, Kaito_simple.st,
    Kaito.simple.json), o None si no es de esos."""
    low, o = fname.lower(), old.lower()
    if low.startswith(o) and len(fname) > len(old) and fname[len(old)] in "._":
        return new + fname[len(old):]
    return None


def copy_character(src_def, dest, base, name=None, author=None):
    """Copia la carpeta del personaje a `dest` y cambia `<viejo>.*` por `<base>.*` (también el _simple.st y el
    .simple.json del modo simple), arregla las referencias del .def y le pone el nombre y el autor.
    Devuelve el .def nuevo."""
    src_def = Path(src_def)
    old = src_def.stem
    dest = Path(dest)
    shutil.copytree(src_def.parent, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("_editor_backups", "__pycache__"))
    mapping = {}
    if base != old:
        for f in list(dest.iterdir()):
            if not f.is_file():
                continue
            new = _renamed(f.name, old, base)
            if new and not (dest / new).exists():
                f.rename(dest / new)
                mapping[f.name.lower()] = new
    new_def = dest / f"{base}.def"
    if not new_def.is_file():          # el .def se llamaba distinto a sus archivos
        cand = dest / src_def.name
        if cand.is_file():
            cand.rename(new_def)
    # referencias del .def (cmd, sprite, st, paletas…) que apuntaban a los archivos renombrados
    if mapping:
        text, enc, nl = read_text(new_def)
        out = []
        for ln in text.split("\n"):
            m = re.match(r"^(\s*[\w.]+\s*=\s*)(\"?)([^\";\r]+?)(\"?)(\s*(;.*)?)\r?$", ln)
            if m and m.group(3).strip().lower() in mapping:
                ln = m.group(1) + m.group(2) + mapping[m.group(3).strip().lower()] + m.group(4) + m.group(5)
            out.append(ln)
        write_text(new_def, "\n".join(out), enc, nl)
    if name or author:
        d = DefFile(new_def)
        if name:
            d.set("Info", "name", name, quote=True)
            d.set("Info", "displayname", name, quote=True)
        if author:
            d.set("Info", "author", author, quote=True)
        d.save()
        if name:
            # la primera línea («; Kaito») también
            text, enc, nl = read_text(new_def)
            lines = text.split("\n")
            if lines and lines[0].strip() == f"; {old}":
                lines[0] = f"; {name}"
                write_text(new_def, "\n".join(lines), enc, nl)
    return new_def
