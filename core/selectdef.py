"""
La línea del personaje en data/select.def de IKEMEN GO: si está en la pantalla de selección y su música
(music=, victory.music=, life.music=; IKEMEN GO no lee música desde el .def del personaje).
"""
import re
from pathlib import Path

from core.textio import read_text, write_text

MUSIC_KEYS = ["music", "victory.music", "life.music"]


def game_root(project, ikemen_dir=None):
    """Carpeta de IKEMEN GO donde está el personaje (…/chars/<personaje>/x.def) o la de la configuración."""
    folder = Path(project.folder).resolve()
    for up in [folder.parent] + list(folder.parents):
        if up.name.lower() == "chars" and (up.parent / "data" / "select.def").is_file():
            return up.parent
    if ikemen_dir and (Path(ikemen_dir) / "data" / "select.def").is_file():
        return Path(ikemen_dir)
    return None


def char_ref(project, root):
    """Cómo se nombra el personaje en select.def (relativo a chars/)."""
    chars = (Path(root) / "chars").resolve()
    d = Path(project.def_path).resolve()
    try:
        rel = d.relative_to(chars)
    except ValueError:
        return str(d)
    if len(rel.parts) == 2 and rel.parent.name.lower() == rel.stem.lower():
        return rel.parent.as_posix()
    return rel.as_posix()


def _split(line):
    body, _, comment = line.partition(";")
    return [f.strip() for f in body.split(",")], (";" + comment if comment else "")


def _matches(first, project, root):
    first = first.strip().strip('"').replace("\\", "/").lower()
    if not first:
        return False
    d = Path(project.def_path).resolve()
    folder = d.parent.name.lower()
    cands = {folder, f"{folder}/{d.name.lower()}"}
    if root:
        try:
            cands.add(d.relative_to((Path(root) / "chars").resolve()).as_posix().lower())
        except ValueError:
            pass
        cands.add(f"chars/{folder}/{d.name.lower()}")
    if first in cands:
        return True
    return first.endswith(".def") and first.split("/")[-2:] == [folder, d.name.lower()]


class SelectDef:
    def __init__(self, path):
        self.path = Path(path)
        text, self.enc, self.nl = read_text(self.path)
        self.lines = text.split("\n")

    def _chars_range(self):
        start = None
        for i, ln in enumerate(self.lines):
            m = re.match(r"^\s*\[(.+?)\]", ln)
            if m:
                if start is not None:
                    return start, i
                if m.group(1).strip().lower() == "characters":
                    start = i + 1
        return (start, len(self.lines)) if start is not None else (None, None)

    def find(self, project, root):
        a, b = self._chars_range()
        if a is None:
            return None
        for i in range(a, b):
            fields, _c = _split(self.lines[i])
            if fields and _matches(fields[0], project, root):
                return i
        return None

    def params(self, i):
        fields, _c = _split(self.lines[i])
        out = {}
        for f in fields[1:]:
            if "=" in f:
                k, _, v = f.partition("=")
                out.setdefault(k.strip().lower(), v.strip())
        return out

    def set_param(self, i, key, value):
        fields, comment = _split(self.lines[i])
        fields = [f for f in fields if f and not (("=" in f) and f.partition("=")[0].strip().lower() == key)]
        if value:
            fields.append(f"{key}={value}")
        self.lines[i] = ", ".join(fields) + (" " + comment if comment else "")

    def add_char(self, ref):
        a, b = self._chars_range()
        if a is None:
            self.lines += ["", "[Characters]", ref]
            return len(self.lines) - 1
        j = b
        while j > a and not self.lines[j - 1].strip():
            j -= 1
        self.lines.insert(j, ref)
        return j

    def save(self):
        write_text(self.path, "\n".join(self.lines), self.enc, self.nl)
