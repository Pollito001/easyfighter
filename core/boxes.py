"""Cajas automáticas a partir de la parte visible de un sprite."""
import numpy as np


def auto_boxes(s, two=True):
    pix = s.pixels()
    mask = pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0
    if not mask.any():
        return []
    ys, xs = np.where(mask)
    y0, y1 = int(ys.min()), int(ys.max()) + 1

    def conv(x0, a, x1, b):
        return (x0 - s.x, a - s.y, x1 - s.x, b - s.y)
    if not two or y1 - y0 < 8:
        return [conv(int(xs.min()), y0, int(xs.max()) + 1, y1)]
    cut = y0 + max(2, int((y1 - y0) * 0.22))
    out = []
    for a, b in ((cut, y1), (y0, cut)):
        part = mask[a:b]
        if part.any():
            pxs = np.where(part.any(axis=0))[0]
            out.append(conv(int(pxs.min()), a, int(pxs.max()) + 1, b))
    return out


def _mask(s):
    pix = s.pixels()
    return pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0


_TIPS_CACHE = {}


def _tips_of(sprite):
    """_tips del sprite, guardado mientras su imagen no cambie (la misma imagen no se vuelve a analizar)."""
    pix = sprite.pixels()
    hit = _TIPS_CACHE.get(id(pix))
    if hit is not None and hit[0] is pix:
        return hit[1]
    res = _tips(pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0)
    if len(_TIPS_CACHE) > 600:
        _TIPS_CACHE.clear()
    _TIPS_CACHE[id(pix)] = (pix, res)
    return res


def _tips(mask):
    """Puntas del dibujo (puños, pies, cabeza, pelo…): los puntos más lejos del centro del cuerpo yendo por
    dentro de la silueta. Devuelve (puntas [(x, y, distancia)], distancias por pixel, escala)."""
    h, w = mask.shape
    f = max(1, int(max(h, w) // 110))
    m = mask[::f, ::f].copy()
    hh, ww = m.shape
    # grosor: cuántas veces hay que «comer» el borde hasta que el pixel desaparece; lo más grueso es el torso
    thick = np.zeros(m.shape, np.int32)
    cur = m.copy()
    for _ in range(60):
        if not cur.any():
            break
        thick += cur
        sh = cur.copy()
        sh[1:, :] &= cur[:-1, :]
        sh[:-1, :] &= cur[1:, :]
        sh[:, 1:] &= cur[:, :-1]
        sh[:, :-1] &= cur[:, 1:]
        cur = sh
    cy, cx = np.unravel_index(int(np.argmax(thick)), thick.shape)
    # distancia yendo por dentro (sin saltar entre brazo y cuerpo): se expande un anillo a la vez
    geo = np.full(m.shape, -1, np.int32)
    geo[cy, cx] = 0
    front = np.zeros(m.shape, bool)
    front[cy, cx] = True
    seen = front.copy()
    d = 0
    while front.any():
        d += 1
        g = front.copy()
        g[1:, :] |= front[:-1, :]
        g[:-1, :] |= front[1:, :]
        g[:, 1:] |= front[:, :-1]
        g[:, :-1] |= front[:, 1:]
        g[1:, 1:] |= front[:-1, :-1]
        g[:-1, :-1] |= front[1:, 1:]
        g[1:, :-1] |= front[:-1, 1:]
        g[:-1, 1:] |= front[1:, :-1]
        front = g & m & ~seen
        seen |= front
        geo[front] = d
    top = geo.max()
    if top <= 0:
        return [], geo, f
    # máximos locales lejos del centro = puntas
    tips = []
    r = 4
    # máximo local en una ventana de (2r+1)²: se compara con la mayor de cada ventana
    pad = np.pad(geo, r, constant_values=-1)
    mx = np.full(geo.shape, -1, np.int32)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            mx = np.maximum(mx, pad[r + dy:r + dy + hh, r + dx:r + dx + ww])
    ys, xs = np.where((geo >= top * 0.3) & (geo >= mx))
    order = np.argsort(-geo[ys, xs])
    for y, x in zip(ys[order], xs[order]):
        if all((x - tx) ** 2 + (y - ty) ** 2 > (r * 2) ** 2 for tx, ty, _g in tips):
            tips.append((int(x), int(y), int(geo[y, x])))
    return [(x * f, y * f, g * f) for x, y, g in tips], geo, f


def strike_box(s, ref=None):
    """Caja de golpe solo en la parte que pega (el puño, el pie, la rodilla…), no en todo el cuerpo.

    Busca las puntas del dibujo (manos, pies, cabeza…) y escoge la que ataca: la que más se aleja del cuerpo,
    hacia adelante o hacia arriba, que no esté apoyada en el suelo. Con `ref` (la pose normal, por ejemplo el
    primer cuadro de parado) descarta las puntas que están igual que en esa pose (la cabeza, el pie de atrás).
    Devuelve [(x1, y1, x2, y2)] relativo al eje."""
    mask = _mask(s)
    if not mask.any():
        return []
    ys, xs = np.where(mask)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    tall = max(8, y1 - y0)
    tips, geo, f = _tips_of(s)
    if not tips:
        return _old_hit_box(s)
    ref_tips = []
    if ref is not None:
        try:
            if _mask(ref).any():
                ref_tips = [(x - ref.x, y - ref.y) for x, y, _g in _tips_of(ref)[0]]
        except Exception:
            ref_tips = []
    cy = (y0 + y1) / 2 - s.y
    near_ref = max(10, tall * 0.12)
    ref_top = min((ry for _rx, ry in ref_tips), default=-10 ** 6)   # más arriba que la cabeza: no se descuenta
    best, best_score = None, None
    for x, y, g in tips:
        px, py = x - s.x, y - s.y
        dy = py - cy
        if py > (y1 - s.y) - tall * 0.08 and px < tall * 0.45:
            continue                     # pie apoyado en el suelo
        score = g + px * 0.8 - max(0.0, -px) * 2.0 - max(0.0, dy) * 0.4 + max(0.0, -dy) * 0.15
        if px < tall * 0.15 and py > ref_top + 4 and \
                any((px - rx) ** 2 + (py - ry) ** 2 < near_ref ** 2 for rx, ry in ref_tips):
            score -= tall * 0.25         # casi donde mismo que en la pose normal (la cabeza): menos probable
        if best_score is None or score > best_score:
            best, best_score = (x, y, g), score
    if best is None:
        best = max(tips, key=lambda t: t[2])
    tx, ty, tg = best
    rad = max(7, int(tall * 0.12))
    # la punta del miembro: cerca de la punta y casi igual de lejos del centro (no se pega al cuerpo)
    gy, gx = np.where(geo >= 0)
    gd = geo[gy, gx] * f
    px_, py_ = gx * f, gy * f
    sel = (np.hypot(px_ - tx, py_ - ty) <= rad) & (gd >= tg - rad * 1.3)
    if not sel.any():
        sel = np.hypot(px_ - tx, py_ - ty) <= rad
    bx, by = px_[sel], py_[sel]
    m = 2 + f
    return [(int(bx.min()) - m - s.x, int(by.min()) - m - s.y, int(bx.max()) + f + m - s.x,
             int(by.max()) + f + m - s.y)]


def hit_box(s, ref=None):
    """Caja de golpe automática (ahora en la parte que pega; ver strike_box)."""
    try:
        return strike_box(s, ref)
    except Exception:
        return _old_hit_box(s)


def _old_hit_box(s):
    """Caja de golpe: la parte de adelante (derecha) de lo visible, a media altura."""
    pix = s.pixels()
    mask = pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0
    if not mask.any():
        return []
    ys, xs = np.where(mask)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    front = max(s.x, x0 + int((x1 - x0) * 0.55))
    if front >= x1 - 2:
        front = x0 + int((x1 - x0) * 0.6)
    region = mask[y0:y1, front:x1]
    if region.any():
        rys = np.where(region.any(axis=1))[0]
        return [(front - s.x, y0 + int(rys.min()) - s.y, x1 - s.x, y0 + int(rys.max()) + 1 - s.y)]
    return [(front - s.x, y0 - s.y, x1 - s.x, y1 - s.y)]
