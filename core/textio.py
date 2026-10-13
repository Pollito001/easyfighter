"""Leer y escribir texto de MUGEN/IKEMEN respetando su codificación (UTF-8, UTF-8 con BOM, Windows viejo)."""
import re
from pathlib import Path


def read_text(path):
    """(texto, codificación, fin_de_línea)."""
    raw = Path(path).read_bytes()
    enc = "utf-8"
    if raw.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8-sig"
        text = raw.decode(enc)
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("cp932")
                if not re.search("[぀-ヿ]", text):
                    raise UnicodeDecodeError("x", b"", 0, 1, "")
                enc = "cp932"
            except UnicodeDecodeError:
                text = raw.decode("cp1252", errors="replace")
                enc = "cp1252"
    nl = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), enc, nl


def write_text(path, text, enc="utf-8", nl="\n"):
    path = Path(path)
    data = text.replace("\r\n", "\n").replace("\n", nl)
    try:
        raw = data.encode(enc)
    except (UnicodeEncodeError, LookupError):
        raw = data.encode("utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(raw)
    tmp.replace(path)


def ci_find(folder, rel):
    """Archivo relativo a 'folder' sin importar mayúsculas ni '\\'. None si no existe."""
    if not rel:
        return None
    rel = rel.strip().strip('"').replace("\\", "/")
    p = Path(folder) / rel
    if p.exists():
        return p
    cur = Path(folder)
    for part in [x for x in rel.split("/") if x and x != "."]:
        if part == "..":
            cur = cur.parent
            continue
        if not cur.is_dir():
            return None
        low = part.lower()
        nxt = next((c for c in cur.iterdir() if c.name.lower() == low), None)
        if nxt is None:
            return None
        cur = nxt
    return cur
