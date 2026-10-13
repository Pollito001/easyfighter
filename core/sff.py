"""
Sprites de MUGEN / IKEMEN GO (.sff v1 y v2).

Para que un SFF enorme abra al instante:
- al abrir solo se lee el índice; cada sprite se decodifica la primera vez que se necesita;
- al guardar, los sprites que no cambiaron se copian tal cual (sin volver a comprimir);
- los sprites nuevos o editados se guardan como PNG (formatos 10/12 de SFF v2), que comprime zlib (C).
Se guarda siempre como SFF v2 (el que entiende IKEMEN GO).
"""
import re
import struct
import zlib
from pathlib import Path

import numpy as np

from i18n import tr

SIG = b"ElecbyteSpr\0"


# ---------------------------------------------------------------- paletas
class Palette:
    def __init__(self, group, number, colors):
        self.group, self.number = int(group), int(number)
        self.colors = np.array(colors, dtype=np.uint8).reshape(-1, 4)  # RGBA

    @property
    def key(self):
        return (self.group, self.number)

    def copy(self):
        return Palette(self.group, self.number, self.colors.copy())

    def rgb_list(self):
        return [tuple(int(v) for v in c[:3]) for c in self.colors]

    def table(self):
        """Tabla ARGB para QImage (el color 0 siempre transparente)."""
        c = self.colors.astype(np.uint32)
        t = (np.uint32(0xFF000000) | (c[:, 0] << 16) | (c[:, 1] << 8) | c[:, 2])
        t = list(int(v) for v in t) + [0xFF000000] * (256 - len(t))
        t[0] = 0
        return t[:256]


def palette_from_rgb(rgb, group=1, number=1):
    arr = np.zeros((256, 4), np.uint8)
    rgb = np.array(list(rgb)[:256], np.uint8).reshape(-1, 3)
    arr[:len(rgb), :3] = rgb
    arr[:, 3] = 255
    arr[0, 3] = 0
    return Palette(group, number, arr)


def read_act(path):
    """Paleta .act de MUGEN (guardada al revés: el color 0 es el último)."""
    raw = Path(path).read_bytes()[:768].ljust(768, b"\0")
    rgb = np.frombuffer(raw, np.uint8).reshape(256, 3)[::-1]
    return palette_from_rgb(rgb)


def write_act(path, pal):
    rgb = np.zeros((256, 3), np.uint8)
    n = min(256, len(pal.colors))
    rgb[:n] = pal.colors[:n, :3]
    Path(path).write_bytes(rgb[::-1].tobytes())


# ---------------------------------------------------------------- decodificadores
_PCX_TOKENS = re.compile(rb"[\xc0-\xff][\s\S]?|[\x00-\xbf]+")
_RLE8_TOKENS = re.compile(rb"[\x40-\x7f][\s\S]?|[^\x40-\x7f]+")


def rle_pcx(data, w, h, bpl):
    """PCX RLE de MUGEN (las repeticiones no pasan de una línea a otra)."""
    if bpl <= 0:
        bpl = w
    total = bpl * h
    stream = bytearray()
    for m in _PCX_TOKENS.finditer(data):
        if len(stream) >= total:
            break
        tok = m.group()
        if tok[0] >= 0xC0:
            n = tok[0] & 0x3F
            v = tok[1] if len(tok) > 1 else 0
            if n:
                stream += bytes((v,)) * min(n, bpl - len(stream) % bpl)
        else:
            stream += tok
    stream = bytes(stream[:total]).ljust(total, b"\0")
    a = np.frombuffer(stream, np.uint8).reshape(h, bpl)
    if bpl >= w:
        return np.ascontiguousarray(a[:, :w])
    out = np.zeros((h, w), np.uint8)
    out[:, :bpl] = a
    return out


def rle8(data, w, h):
    total = w * h
    out = bytearray()
    for m in _RLE8_TOKENS.finditer(data):
        if len(out) >= total:
            break
        tok = m.group()
        if 0x40 <= tok[0] <= 0x7F:
            out += bytes((tok[1] if len(tok) > 1 else 0,)) * (tok[0] & 0x3F)
        else:
            out += tok
    return np.frombuffer(bytes(out[:total]).ljust(total, b"\0"), np.uint8).reshape(h, w)


def rle5(data, w, h):
    out = bytearray(w * h)
    if not data:
        return np.zeros((h, w), np.uint8)
    i = j = 0
    last = len(data) - 1
    n_out = len(out)
    while j < n_out:
        rl = data[i]
        i = min(i + 1, last)
        dl = data[i] & 0x7F
        c = 0
        if data[i] >> 7:
            i = min(i + 1, last)
            c = data[i]
        i = min(i + 1, last)
        while True:
            if j < n_out:
                out[j] = c
                j += 1
            rl -= 1
            if rl < 0:
                dl -= 1
                if dl < 0:
                    break
                c = data[i] & 0x1F
                rl = data[i] >> 5
                i = min(i + 1, last)
    return np.frombuffer(bytes(out), np.uint8).reshape(h, w)


def lz5(data, w, h):
    out = bytearray(w * h)
    if not data:
        return np.zeros((h, w), np.uint8)
    n_out = len(out)
    last = len(data) - 1
    i = j = n = 0
    ct, cts, rb, rbc = data[0], 0, 0, 0
    i = min(i + 1, last)
    while j < n_out:
        d = data[i]
        i = min(i + 1, last)
        if ct & (1 << cts):
            if d & 0x3F == 0:
                d = ((d << 2) | data[i]) + 1
                i = min(i + 1, last)
                n = data[i] + 2
                i = min(i + 1, last)
            else:
                rb |= ((d & 0xC0) >> rbc) & 0xFF
                rbc += 2
                n = d & 0x3F
                if rbc < 8:
                    d = data[i] + 1
                    i = min(i + 1, last)
                else:
                    d = rb + 1
                    rb, rbc = 0, 0
            # copia (puede solaparse: se hace byte a byte cuando hace falta)
            cnt = n + 1
            src = j - d
            if src >= 0 and d >= cnt:
                end = min(n_out, j + cnt)
                out[j:end] = out[src:src + (end - j)]
                j = end
            else:
                for _ in range(cnt):
                    if j < n_out:
                        out[j] = out[j - d] if j - d >= 0 else 0
                        j += 1
        else:
            if d & 0xE0 == 0:
                n = data[i] + 8
                i = min(i + 1, last)
            else:
                n = d >> 5
                d &= 0x1F
            end = min(n_out, j + n)
            out[j:end] = bytes((d,)) * (end - j)
            j = end
        cts += 1
        if cts >= 8:
            ct, cts = data[i], 0
            i = min(i + 1, last)
    return np.frombuffer(bytes(out), np.uint8).reshape(h, w)


def png_decode(data):
    """(pixeles, profundidad). Índices (h,w) para PNG con paleta; RGBA (h,w,4) para color directo."""
    from PyQt6.QtCore import QByteArray
    from PyQt6.QtGui import QImage
    img = QImage()
    if not img.loadFromData(QByteArray(bytes(data)), "PNG"):
        raise ValueError("PNG")
    if img.format() in (QImage.Format.Format_Mono, QImage.Format.Format_MonoLSB):
        img = img.convertToFormat(QImage.Format.Format_Indexed8)
    if img.format() == QImage.Format.Format_Indexed8:
        return qimage_indices(img), 8
    img = img.convertToFormat(QImage.Format.Format_RGBA8888)
    return qimage_rgba(img), 32


def qimage_indices(img):
    w, h, bpl = img.width(), img.height(), img.bytesPerLine()
    bits = img.constBits()
    bits.setsize(img.sizeInBytes())
    return np.frombuffer(bytes(bits), np.uint8).reshape(h, bpl)[:, :w].copy()


def qimage_rgba(img):
    from PyQt6.QtGui import QImage
    img = img.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h, bpl = img.width(), img.height(), img.bytesPerLine()
    bits = img.constBits()
    bits.setsize(img.sizeInBytes())
    return np.frombuffer(bytes(bits), np.uint8).reshape(h, bpl)[:, :w * 4].reshape(h, w, 4).copy()


# ---------------------------------------------------------------- codificadores
def _chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png8(pix, pal_rgb):
    h, w = pix.shape
    rows = np.zeros((h, w + 1), np.uint8)
    rows[:, 1:] = pix
    plte = bytes(np.array(pal_rgb, np.uint8)[:256, :3].tobytes()).ljust(768, b"\0")
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
            + _chunk(b"PLTE", plte) + _chunk(b"tRNS", b"\0") + _chunk(b"IDAT", zlib.compress(rows.tobytes(), 6))
            + _chunk(b"IEND", b""))


def png32(rgba):
    h, w, _ = rgba.shape
    rows = np.zeros((h, w * 4 + 1), np.uint8)
    rows[:, 1:] = rgba.reshape(h, w * 4)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(rows.tobytes(), 6)) + _chunk(b"IEND", b""))


def rle8_encode(pix):
    flat = bytes(np.ascontiguousarray(pix).tobytes())
    out = bytearray()
    for m in re.finditer(rb"([\s\S])\1{0,62}", flat):
        run = m.end() - m.start()
        v = flat[m.start()]
        if run > 1 or (v & 0xC0) == 0x40:
            out += bytes((0x40 | run, v))
        else:
            out.append(v)
    return bytes(out)


# ---------------------------------------------------------------- sprites
class Sprite:
    """Un sprite. Los píxeles se decodifican al pedirlos (pixels())."""

    def __init__(self, group=0, number=0, x=0, y=0):
        self.group, self.number = int(group), int(number)
        self.x, self.y = int(x), int(y)  # eje (axis)
        self.w = self.h = 0
        self.depth = 8
        self.palidx = 0
        self.link = None       # otro Sprite con la misma imagen
        self._pix = None
        self._decoder = None   # función que devuelve los píxeles
        self._raw = None       # (fmt, bytes) para copiar tal cual al guardar (solo SFF v2 sin cambios)

    @property
    def key(self):
        return (self.group, self.number)

    def base(self):
        s, n = self, 0
        while s.link is not None and n < 64:
            s, n = s.link, n + 1
        return s

    def pixels(self):
        b = self.base()
        if b._pix is None:
            try:
                b._pix = b._decoder() if b._decoder else np.zeros((max(1, b.h), max(1, b.w)), np.uint8)
            except Exception:
                b._pix = np.zeros((max(1, b.h), max(1, b.w)), np.uint8)
            if b._pix.ndim == 3:
                b.depth = 32
            b.h, b.w = b._pix.shape[:2]
        return b._pix

    def set_pixels(self, pix):
        """Imagen nueva: índices (h,w) uint8 o RGBA (h,w,4)."""
        self._pix = np.ascontiguousarray(pix, dtype=np.uint8)
        self.h, self.w = self._pix.shape[:2]
        self.depth = 32 if self._pix.ndim == 3 else 8
        self._raw = None
        self._decoder = None
        self.link = None

    def size(self):
        b = self.base()
        if b._pix is None and (b.w == 0 or b.h == 0):
            b.pixels()
        return b.w, b.h

    def copy(self):
        s = Sprite(self.group, self.number, self.x, self.y)
        s.set_pixels(self.pixels().copy())
        s.palidx = self.palidx
        return s


def black_score(pix, pal_colors):
    """Píxeles (no transparentes) que caen en un negro puro de la paleta."""
    c = np.asarray(pal_colors)
    black = np.zeros(256, bool)
    n = min(256, len(c))
    black[:n] = (c[:n, 0] == 0) & (c[:n, 1] == 0) & (c[:n, 2] == 0)
    black[0] = False
    return int(black[pix].sum())


def best_palette(pix, palettes, cands):
    """La primera de cands, salvo que con ella la imagen salga muy negra y otra la arregle."""
    solid = int((pix != 0).sum()) or 1
    first = black_score(pix, palettes[cands[0]].colors)
    if first <= solid * 0.25:
        return cands[0]
    best = min(cands, key=lambda i: black_score(pix, palettes[i].colors))
    return best if black_score(pix, palettes[best].colors) < first * 0.5 else cands[0]


# ---------------------------------------------------------------- archivo
class SffFile:
    def __init__(self):
        self.path = None
        self.sprites = []
        self.palettes = [palette_from_rgb([(i, i, i) for i in range(256)], 1, 1)]
        self.source_version = 2
        self.modified = False

    # ---- consultas
    def find(self, group, number):
        for s in self.sprites:
            if s.group == group and s.number == number:
                return s
        return None

    def index(self):
        return {s.key: s for s in reversed(self.sprites)}

    def palette_for(self, sprite, override=None):
        """Paleta con que se dibuja un sprite. override = paleta elegida para el personaje
        (reemplaza a la 1,1 en los sprites que la usan, como hace el juego)."""
        if sprite.base().palidx < len(self.palettes):
            p = self.palettes[sprite.base().palidx]
        else:
            p = self.palettes[0]
        if override is not None and sprite.base().palidx == 0:
            return override
        return p

    def find_palette(self, group, number):
        for i, p in enumerate(self.palettes):
            if p.group == group and p.number == number:
                return i
        return None

    def char_palette_numbers(self):
        return sorted(p.number for p in self.palettes if p.group == 1)

    # ---- abrir
    @classmethod
    def load(cls, path):
        f = cls()
        f.path = Path(path)
        data = f.path.read_bytes()
        if data[:12] != SIG:
            raise ValueError(tr('no es un archivo SFF'))
        ver = data[15]
        f.source_version = ver
        if ver == 2:
            f._load_v2(data)
        elif ver == 1:
            f._load_v1(data)
        else:
            raise ValueError(tr('versión de SFF desconocida'))
        return f

    def _load_v2(self, d):
        spr_ofs, nspr, pal_ofs, npal, lofs, _ll, tofs = struct.unpack_from("<IIIIIII", d, 36)
        ver_lo2 = d[13]
        self.palettes = []
        for i in range(npal):
            g, n, ncol, link, ofs, size = struct.unpack_from("<HHHHII", d, pal_ofs + i * 16)
            if size == 0 and link < len(self.palettes):
                cols = self.palettes[link].colors.copy()
            else:
                raw = d[lofs + ofs:lofs + ofs + size]
                cols = np.frombuffer(raw[:len(raw) // 4 * 4], np.uint8).reshape(-1, 4).copy()
                if ver_lo2 == 0 or not cols[1:, 3].any():  # paletas sin alfa
                    cols[:, 3] = 255
                cols[0, 3] = 0
            self.palettes.append(Palette(g, n, cols))
        if not self.palettes:
            self.palettes = [palette_from_rgb([(i, i, i) for i in range(256)], 1, 1)]
        order = []
        for idx in range(nspr):
            g, n, w, h, ax, ay, link, fmt, depth, ofs, size, palidx, flags = \
                struct.unpack_from("<HHHHhhHBBIIHH", d, spr_ofs + idx * 28)
            s = Sprite(g, n, ax, ay)
            s.w, s.h, s.palidx = w, h, palidx
            s.depth = 32 if depth > 8 else 8
            if size == 0:
                s._link_index = link
            else:
                start = (tofs if flags & 1 else lofs) + ofs
                blob = d[start:start + size]
                s._raw = (fmt, depth, bytes(blob))
                s._decoder = _v2_decoder(fmt, depth, blob, w, h)
            order.append(s)
        for s in order:
            li = getattr(s, "_link_index", None)
            if li is not None:
                if li < len(order) and order[li] is not s:
                    s.link = order[li]
                    s.palidx = order[li].palidx
                del s._link_index
        self.sprites = order

    def _load_v1(self, d):
        """SFF v1: mismas reglas de paletas que usa la conversión del manager."""
        nspr, first = struct.unpack_from("<II", d, 20)
        nodes, ofs = [], first
        for _ in range(nspr):
            if ofs <= 0 or ofs + 32 > len(d):
                break
            nxt, size, ax, ay, g, n, link, same = struct.unpack_from("<IIhhHHHB", d, ofs)
            nodes.append((ofs, nxt, size, ax, ay, g, n, link, same))
            ofs = nxt
        own = {}
        info = {}
        for k, (ofs, nxt, size, ax, ay, g, n, link, same) in enumerate(nodes):
            if not size:
                continue
            start = ofs + 32
            x0, y0, x1, y1 = struct.unpack_from("<HHHH", d, start + 4)
            bpl = struct.unpack_from("<H", d, start + 66)[0]
            w, h = x1 - x0 + 1, y1 - y0 + 1
            end = nxt if nxt > ofs else start + size
            pal_pos = None
            if not same:
                pos = end - 769
                while pos >= start + 128:
                    if d[pos] == 0x0C:
                        pal_pos = pos + 1
                        break
                    pos -= 1
                if pal_pos is None:
                    pal_pos = end - 768
                rgb = np.frombuffer(d[pal_pos:pal_pos + 768].ljust(768, b"\0"), np.uint8).reshape(256, 3)
                own[k] = palette_from_rgb(rgb)
            data_end = (pal_pos - 1) if pal_pos is not None else end
            info[k] = (start + 128, data_end, w, h, bpl)
        # paleta del personaje: la del 0,0; si no, la del primer sprite que no sea retrato
        keys = {k: (nodes[k][5], nodes[k][6]) for k in own}
        first_own = (next((own[k] for k in own if keys[k] == (0, 0)), None)
                     or next((own[k] for k in own if keys[k][0] != 9000), None)
                     or next(iter(own.values()), None)
                     or palette_from_rgb([(i, i, i) for i in range(256)]))
        palettes = [Palette(1, 1, first_own.colors.copy())]

        def pal_index(p):
            for i, q in enumerate(palettes):
                if np.array_equal(q.colors[:, :3], p.colors[:, :3]):
                    return i
            palettes.append(Palette(9000, len(palettes), p.colors.copy()))
            return len(palettes) - 1

        order, cur, cur_g = [], 0, -1
        for k, (ofs, nxt, size, ax, ay, g, n, link, same) in enumerate(nodes):
            s = Sprite(g, n, ax, ay)
            if not size:
                s._link_index = link
                order.append(s)
                continue
            a, b, w, h, bpl = info[k]
            s.w, s.h = w, h
            blob = d[a:b]
            s._decoder = (lambda blob=blob, w=w, h=h, bpl=bpl: rle_pcx(blob, w, h, bpl))
            p = own.get(k)
            if g == 9000:
                cands = [pal_index(p)] if p is not None else []
                cands += [0] + ([cur] if cur_g == 9000 and cur else [])
                cands += [i for i in range(len(palettes)) if i not in cands]
                s.palidx = best_palette(s.pixels(), palettes, cands)
            elif p is None:
                s.palidx = cur if cur_g != 9000 else 0
            elif np.array_equal(p.colors[:, :3], palettes[0].colors[:, :3]):
                s.palidx = 0
            else:
                s.palidx = pal_index(p)
            cur, cur_g = s.palidx, g
            order.append(s)
        for s in order:
            li = getattr(s, "_link_index", None)
            if li is not None:
                if li < len(order) and order[li] is not s:
                    s.link = order[li]
                    s.palidx = order[li].palidx
                del s._link_index
        self.sprites = order
        # números únicos para las paletas extra
        used = set()
        for p in palettes[1:]:
            num = 1
            while (9000, num) in used:
                num += 1
            p.group, p.number = 9000, num
            used.add((9000, num))
        self.palettes = palettes
        self.modified = True  # se guardará como v2

    # ---- guardar
    def save(self, path=None, progress=None):
        """Guarda como SFF v2. progress(fracción) opcional."""
        path = Path(path or self.path)
        pal_nodes, pdata = bytearray(), bytearray()
        for p in self.palettes:
            cols = p.colors.copy()
            cols[:, 3] = 255
            cols[0, 3] = 0
            raw = cols.tobytes()
            pal_nodes += struct.pack("<HHHHII", p.group, p.number, len(cols), 0, len(pdata), len(raw))
            pdata += raw
        index_of = {id(s): i for i, s in enumerate(self.sprites)}
        nodes, ldata = [], bytearray(pdata)
        total = max(1, len(self.sprites))
        for i, s in enumerate(self.sprites):
            if progress and i % 32 == 0:
                progress(i / total)
            palidx = min(s.base().palidx, len(self.palettes) - 1)
            if s.link is not None and id(s.link) in index_of and index_of[id(s.link)] < i:
                w, h = s.size()
                nodes.append(struct.pack("<HHHHhhHBBIIHH", s.group, s.number, w, h, s.x, s.y,
                                         index_of[id(s.link)], 0, 8 if s.base().depth == 8 else 32, 0, 0, palidx, 0))
                continue
            b = s.base()
            if b._raw is not None and b is s:
                fmt, depth, blob = b._raw
                w, h = b.w, b.h
            else:
                pix = s.pixels()
                h, w = pix.shape[:2]
                if pix.ndim == 3:
                    fmt, depth, blob = 12, 32, struct.pack("<I", w * h * 4) + png32(pix)
                elif w and h:
                    fmt, depth = 10, 8
                    blob = struct.pack("<I", w * h) + png8(pix, self.palettes[palidx].colors[:, :3])
                else:
                    fmt, depth, blob = 2, 8, struct.pack("<I", 0)
            ofs = len(ldata)
            ldata += blob
            nodes.append(struct.pack("<HHHHhhHBBIIHH", s.group, s.number, w, h, s.x, s.y, 0, fmt, depth,
                                     ofs, len(blob), palidx, 0))
        header = bytearray(512)
        header[:12] = SIG
        header[12:16] = bytes((0, 1, 0, 2))
        header[24:28] = bytes((0, 1, 0, 2))
        pal_ofs = 512
        spr_ofs = pal_ofs + len(pal_nodes)
        lofs = spr_ofs + len(nodes) * 28
        struct.pack_into("<IIIIIIII", header, 36, spr_ofs, len(nodes), pal_ofs, len(self.palettes), lofs,
                         len(ldata), lofs + len(ldata), 0)
        out = bytes(header) + bytes(pal_nodes) + b"".join(nodes) + bytes(ldata)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(out)
        tmp.replace(path)
        self.path = path
        self.modified = False
        self.source_version = 2
        # lo guardado ya se puede copiar tal cual la próxima vez
        if progress:
            progress(1.0)


def _v2_decoder(fmt, depth, blob, w, h):
    def dec():
        if fmt == 0:
            if depth > 8:
                bpp = depth // 8
                a = np.frombuffer(bytes(blob).ljust(w * h * bpp, b"\0")[:w * h * bpp], np.uint8).reshape(h, w, bpp)
                if bpp == 3:
                    a = np.dstack([a, np.full((h, w), 255, np.uint8)])
                return a
            return np.frombuffer(bytes(blob).ljust(w * h, b"\0")[:w * h], np.uint8).reshape(h, w)
        body = blob[4:]
        if fmt == 2:
            return rle8(body, w, h)
        if fmt == 3:
            return rle5(body, w, h)
        if fmt == 4:
            return lz5(body, w, h)
        if fmt in (10, 11, 12):
            pix, _d = png_decode(body)
            return pix
        raise ValueError(f"formato {fmt}")
    return dec


def new_sff():
    return SffFile()
