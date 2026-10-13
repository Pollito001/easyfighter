"""
Archivos tipo .ini de MUGEN (.def, constantes de .cns, etc.): se editan sin perder comentarios ni orden.
"""
import re

from core.textio import read_text, write_text

SECTION = re.compile(r"^\s*\[(.+?)\]")


def strip_comment(line):
    """Quita el comentario ';' (respetando comillas)."""
    out, q = [], False
    for ch in line:
        if ch == '"':
            q = not q
        if ch == ";" and not q:
            break
        out.append(ch)
    return "".join(out)


class DefFile:
    def __init__(self, path=None, text=""):
        self.path = path
        self.enc, self.nl = "utf-8", "\r\n"
        if path is not None:
            text, self.enc, self.nl = read_text(path)
        self.lines = text.split("\n")

    # ---- secciones
    def sections(self):
        return [m.group(1).strip() for m in (SECTION.match(ln) for ln in self.lines) if m]

    def _range(self, section):
        low = section.lower()
        start = None
        for i, ln in enumerate(self.lines):
            m = SECTION.match(ln)
            if m:
                if start is not None:
                    return start, i
                if m.group(1).strip().lower() == low:
                    start = i + 1
        return (start, len(self.lines)) if start is not None else (None, None)

    def keys(self, section):
        a, b = self._range(section)
        out = []
        if a is None:
            return out
        for i in range(a, b):
            body = strip_comment(self.lines[i])
            if "=" in body:
                k, _, v = body.partition("=")
                out.append((k.strip(), v.strip()))
        return out

    def get(self, section, key, default=""):
        low = key.lower()
        for k, v in self.keys(section):
            if k.lower() == low:
                return v.strip().strip('"') if v.strip().startswith('"') and v.strip().endswith('"') else v
        return default

    def set(self, section, key, value, quote=False):
        val = f'"{value}"' if quote else str(value)
        a, b = self._range(section)
        if a is None:
            if self.lines and self.lines[-1].strip():
                self.lines.append("")
            self.lines += [f"[{section}]", f"{key} = {val}"]
            return
        low = key.lower()
        for i in range(a, b):
            body = strip_comment(self.lines[i])
            if "=" in body and body.partition("=")[0].strip().lower() == low:
                line = self.lines[i]
                comment = line[len(body):]
                lead = re.match(r"^(\s*)", line).group(1)
                self.lines[i] = f"{lead}{body.partition('=')[0].rstrip()} = {val}" + (
                    ("    " + comment.lstrip()) if comment.strip() else "")
                return
        # agregar al final de la sección (antes de líneas vacías)
        j = b
        while j > a and not self.lines[j - 1].strip():
            j -= 1
        self.lines.insert(j, f"{key} = {val}")

    def remove(self, section, key):
        a, b = self._range(section)
        if a is None:
            return
        low = key.lower()
        for i in range(b - 1, a - 1, -1):
            body = strip_comment(self.lines[i])
            if "=" in body and body.partition("=")[0].strip().lower() == low:
                del self.lines[i]

    def text(self):
        return "\n".join(self.lines)

    def save(self, path=None):
        write_text(path or self.path, self.text(), self.enc, self.nl)
