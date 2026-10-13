"""
Cortar hojas de sprites (sprite sheets) en cuadros sueltos, sin Qt (solo numpy).

Pasos:
1. Fondo: si la imagen tiene transparencia se usa; si no, el color más común del borde (o los que elija
   el usuario), con una tolerancia.
2. Piezas: se etiquetan las zonas conectadas (por tramos de cada fila, rápido aunque la hoja sea grande).
   Las piezas a menos de «unir» píxeles se juntan.
3. Arreglos: lo que queda dentro de otra caja se une a ella; los pedacitos chicos (pelo, chispas,
   gotas) se pegan al sprite grande más cercano; las manchas diminutas se descartan.
4. Orden: por filas (de arriba a abajo) y en cada fila de izquierda a derecha.
5. Cada cuadro se recorta solo con SUS píxeles (no se cuelan pedazos del vecino aunque las cajas se
   crucen) y se le calcula el eje (punto de apoyo).
"""
import numpy as np


class Box:
    """Un cuadro encontrado. labels: piezas que lo forman (None = todo lo que no es fondo dentro de la caja)."""

    def __init__(self, x0, y0, x1, y1, labels=None, area=0, cell=None):
        self.x0, self.y0, self.x1, self.y1 = int(x0), int(y0), int(x1), int(y1)
        self.labels = set(labels) if labels is not None else None
        self.area = int(area)
        self.cell = cell            # (x0, y0, x1, y1) de la celda en modo cuadrícula
        self.row = 0
        self.selected = False

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    def rect(self):
        return self.x0, self.y0, self.x1, self.y1

    def contains(self, o, pad=1):
        return (o.x0 >= self.x0 - pad and o.y0 >= self.y0 - pad and o.x1 <= self.x1 + pad and
                o.y1 <= self.y1 + pad)

    def dist(self, o):
        dx = max(0, max(self.x0, o.x0) - min(self.x1, o.x1))
        dy = max(0, max(self.y0, o.y0) - min(self.y1, o.y1))
        return max(dx, dy)

    def absorb(self, o):
        self.x0, self.y0 = min(self.x0, o.x0), min(self.y0, o.y0)
        self.x1, self.y1 = max(self.x1, o.x1), max(self.y1, o.y1)
        if self.labels is not None and o.labels is not None:
            self.labels |= o.labels
        else:
            self.labels = None
        self.area += o.area


# ---------------------------------------------------------------- fondo
def has_alpha(rgba):
    a = rgba[:, :, 3]
    return bool((a < 128).mean() > 0.02)


def border_color(rgba):
    """Color más común del borde de la imagen (el fondo, casi siempre)."""
    h, w = rgba.shape[:2]
    edge = np.concatenate([rgba[0, :, :3], rgba[h - 1, :, :3], rgba[:, 0, :3], rgba[:, w - 1, :3]])
    packed = (edge[:, 0].astype(np.uint32) << 16) | (edge[:, 1].astype(np.uint32) << 8) | edge[:, 2]
    vals, counts = np.unique(packed, return_counts=True)
    v = int(vals[np.argmax(counts)])
    return (v >> 16) & 255, (v >> 8) & 255, v & 255


def auto_tolerance(rgba, color):
    """Tolerancia que cubre las variaciones del fondo (JPG, degradados suaves) mirando el borde."""
    h, w = rgba.shape[:2]
    edge = np.concatenate([rgba[0, :, :3], rgba[h - 1, :, :3], rgba[:, 0, :3], rgba[:, w - 1, :3]]).astype(np.int16)
    d = np.abs(edge - np.array(color, np.int16)).max(axis=1)
    near = d[d <= 90]
    if len(near) < len(d) * 0.5:
        return 0
    t = int(np.percentile(near, 99))
    return 0 if t == 0 else min(90, t + 10)


def _common_color(rgba, mask, limit=200000):
    pix = rgba[:, :, :3][mask]
    if len(pix) > limit:
        pix = pix[:: len(pix) // limit + 1]
    packed = (pix[:, 0].astype(np.uint32) << 16) | (pix[:, 1].astype(np.uint32) << 8) | pix[:, 2]
    vals, counts = np.unique(packed, return_counts=True)
    v = int(vals[np.argmax(counts)])
    return (v >> 16) & 255, (v >> 8) & 255, v & 255


def auto_background(rgba):
    """(usar_transparencia, colores_de_fondo, tolerancia) adivinados. Además del color del borde, reconoce
    un segundo color de relleno y las líneas de una cuadrícula dibujada."""
    alpha = has_alpha(rgba)
    colors = [] if alpha else [border_color(rgba)]
    tol = 0 if alpha else auto_tolerance(rgba, colors[0])
    h, w = rgba.shape[:2]
    for _ in range(3):
        fg = foreground(rgba, colors, tol, alpha)
        if not fg.any():
            break
        if fg.mean() > 0.45:
            c = _common_color(rgba, fg)
        else:
            small = fg[::2, ::2] if fg.size > 4_000_000 else fg
            pcs = Pieces(small, 0)
            sh, sw = small.shape
            lattice = [b for b in pcs.boxes if b.w > 0.6 * sw and b.h > 0.6 * sh and b.area < 0.25 * b.w * b.h]
            if not lattice:
                break
            b = max(lattice, key=lambda b: b.area)
            m = np.zeros(small.shape, bool)
            m[pcs.label == next(iter(b.labels))] = True
            sub = rgba[::2, ::2] if small is not fg else rgba
            c = _common_color(sub, m)
        if c in colors:
            break
        colors.append(c)
    return alpha, colors, tol


def foreground(rgba, bg_colors=(), tolerance=0, use_alpha=None):
    """Máscara de lo que NO es fondo."""
    if use_alpha is None:
        use_alpha = has_alpha(rgba)
    fg = rgba[:, :, 3] >= 128 if use_alpha else np.ones(rgba.shape[:2], bool)
    rgb = rgba[:, :, :3].astype(np.int16)
    for c in bg_colors:
        d = np.abs(rgb - np.array(c, np.int16)).max(axis=2)
        fg &= d > tolerance
    return fg


# ---------------------------------------------------------------- piezas
def _runs(mask):
    """Tramos horizontales de píxeles: (fila, x0, x1) con x1 exclusivo, en orden de lectura."""
    h, w = mask.shape
    pad = np.zeros((h, w + 2), np.int8)
    pad[:, 1:-1] = mask
    d = np.diff(pad, axis=1)
    s = np.argwhere(d == 1)
    e = np.argwhere(d == -1)
    return s[:, 0], s[:, 1], e[:, 1]


def _label_runs(rows, x0, x1, h):
    """Une los tramos que se tocan (8 vecinos). Devuelve la etiqueta de cada tramo (0..n-1)."""
    n = len(rows)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    starts = np.searchsorted(rows, np.arange(h + 1)).tolist()
    xs0, xs1 = x0.tolist(), x1.tolist()
    for r in range(1, h):
        a0, a1, b1 = starts[r - 1], starts[r], starts[r + 1]
        i, j = a0, a1
        while i < a1 and j < b1:
            if xs0[j] <= xs1[i] and xs0[i] <= xs1[j]:
                ra, rb = find(i), find(j)
                if ra != rb:
                    parent[rb] = ra
            if xs1[i] < xs1[j]:
                i += 1
            else:
                j += 1
    roots = np.array([find(k) for k in range(n)], np.int64)
    _u, lab = np.unique(roots, return_inverse=True)
    return lab


def _dilate(mask, r):
    if r <= 0:
        return mask
    m = mask.copy()
    for k in range(1, r + 1):
        m[:, k:] |= mask[:, :-k]
        m[:, :-k] |= mask[:, k:]
    m2 = m.copy()
    for k in range(1, r + 1):
        m2[k:, :] |= m[:-k, :]
        m2[:-k, :] |= m[k:, :]
    return m2


class Pieces:
    """Etiquetas por píxel de lo que no es fondo."""

    def __init__(self, fg, join=2):
        h, w = fg.shape
        self.shape = fg.shape
        rows, x0, x1 = _runs(fg)
        self.label = np.full((h, w), -1, np.int32)
        if len(rows) == 0:
            self.n = 0
            self.boxes = []
            return
        r = max(0, (int(join) + 1) // 2)
        if r:
            drows, dx0, dx1 = _runs(_dilate(fg, r))
            dlab = _label_runs(drows, dx0, dx1, h)
            # a qué tramo dilatado pertenece cada tramo original
            W = w + 2
            keys = drows.astype(np.int64) * W + dx0
            idx = np.searchsorted(keys, rows.astype(np.int64) * W + x0, side="right") - 1
            lab = dlab[idx]
        else:
            lab = _label_runs(rows, x0, x1, h)
        self.n = int(lab.max()) + 1
        lengths = (x1 - x0).astype(np.int64)
        total = int(lengths.sum())
        rr = np.repeat(rows, lengths)
        offs = np.arange(total) - np.repeat(np.cumsum(lengths) - lengths, lengths)
        cc = np.repeat(x0, lengths) + offs
        self.label[rr, cc] = np.repeat(lab, lengths)
        n = self.n
        bx0 = np.full(n, 1 << 30)
        by0 = np.full(n, 1 << 30)
        bx1 = np.zeros(n, np.int64)
        by1 = np.zeros(n, np.int64)
        area = np.zeros(n, np.int64)
        np.minimum.at(bx0, lab, x0)
        np.maximum.at(bx1, lab, x1)
        np.minimum.at(by0, lab, rows)
        np.maximum.at(by1, lab, rows + 1)
        np.add.at(area, lab, lengths)
        self.boxes = [Box(bx0[i], by0[i], bx1[i], by1[i], {i}, area[i]) for i in range(n)]


def smart_merge(boxes, attach=True, attach_dist=10, min_area=8):
    """Une lo que va junto y quita la basura."""
    boxes = [b for b in boxes]
    # 1) lo que queda dentro de la caja de otro (y es más chico) va con ese
    boxes.sort(key=lambda b: -b.w * b.h)
    out = []
    for b in boxes:
        host = next((o for o in out if o.contains(b) and o.area >= b.area), None)
        if host is not None:
            host.absorb(b)
        else:
            out.append(b)
    if attach and len(out) > 1:
        areas = np.array([b.area for b in out])
        big_ref = float(np.median(areas[areas >= np.percentile(areas, 50)])) if len(areas) else 0
        small_lim = max(min_area * 4, big_ref * 0.12)
        bigs = [b for b in out if b.area >= small_lim]
        smalls = [b for b in out if b.area < small_lim]
        if bigs:
            keep = list(bigs)
            for s in sorted(smalls, key=lambda b: -b.area):
                near = sorted(bigs, key=lambda b: b.dist(s))
                tgt = near[0]
                d = tgt.dist(s)
                lim = max(attach_dist, int(min(tgt.w, tgt.h) * 0.08))
                if d <= lim:
                    # que al pegarlo no se meta en otro sprite grande
                    nx0, ny0 = min(tgt.x0, s.x0), min(tgt.y0, s.y0)
                    nx1, ny1 = max(tgt.x1, s.x1), max(tgt.y1, s.y1)
                    clash = any(o is not tgt and o.x0 < nx1 and o.x1 > nx0 and o.y0 < ny1 and o.y1 > ny0 and
                                not (o.x0 < tgt.x1 and o.x1 > tgt.x0 and o.y0 < tgt.y1 and o.y1 > tgt.y0)
                                for o in bigs)
                    if not clash:
                        tgt.absorb(s)
                        continue
                keep.append(s)
            out = keep
    return [b for b in out if b.area >= min_area]


def _bbox_of(mask, ox, oy):
    ys = np.where(mask.any(axis=1))[0]
    xs = np.where(mask.any(axis=0))[0]
    return ox + xs[0], oy + ys[0], ox + xs[-1] + 1, oy + ys[-1] + 1


def _split_once(b, label, med_w, med_h, ids):
    """Si una caja es mucho más grande que las demás y en realidad son dos sprites casi pegados, la parte."""
    if b.labels is None or (b.h < 1.8 * med_h and b.w < 1.8 * med_w):
        return None
    view = label[b.y0:b.y1, b.x0:b.x1]
    own = np.isin(view, list(b.labels))
    groups = None
    raw = Pieces(own, 0)
    comps = sorted(raw.boxes, key=lambda c: -c.area)
    if len(comps) >= 2 and comps[1].area >= 0.25 * comps[0].area:
        # dos piezas grandes que solo estaban cerca: cada pedacito va con la más cercana
        A, B = comps[0], comps[1]
        ga, gb = [A], [B]
        for c in comps[2:]:
            (ga if A.dist(c) <= B.dist(c) else gb).append(c)
        groups = [np.isin(raw.label, [next(iter(c.labels)) for c in g]) for g in (ga, gb)]
    else:
        # se tocan: cortar por la línea más fina
        for axis, size, med in ((1, b.h, med_h), (0, b.w, med_w)):
            if size < 1.8 * med:
                continue
            prof = own.sum(axis=axis)
            lo, hi = int(size * 0.25), int(size * 0.75)
            if hi <= lo:
                continue
            cut = lo + int(np.argmin(prof[lo:hi]))
            if prof[cut] > 3 or cut < 0.5 * med or size - cut < 0.5 * med:
                continue
            g1 = own.copy()
            g2 = own.copy()
            if axis == 1:
                g1[cut:, :] = False
                g2[:cut, :] = False
            else:
                g1[:, cut:] = False
                g2[:, :cut] = False
            groups = [g1, g2]
            break
    if not groups or not all(g.any() for g in groups):
        return None
    out = []
    for g in groups:
        nid = ids[0]
        ids[0] += 1
        view[g] = nid
        out.append(Box(*_bbox_of(g, b.x0, b.y0), {nid}, int(g.sum())))
    return out


def split_touching(boxes, label):
    """Separa sprites que quedaron juntos por estar pegaditos."""
    if len(boxes) < 3:
        return boxes
    big = [b for b in boxes if b.area >= 0.1 * max(x.area for x in boxes)]
    med_w = float(np.median([b.w for b in big]))
    med_h = float(np.median([b.h for b in big]))
    ids = [int(label.max()) + 1]
    out = []
    todo = list(boxes)
    while todo:
        b = todo.pop()
        parts = _split_once(b, label, med_w, med_h, ids)
        if parts:
            todo += parts
        else:
            out.append(b)
    return out


def order_rows(boxes):
    """Pone b.row y devuelve la lista en orden de lectura."""
    rows = []   # [y0, y1, [boxes]]
    for b in sorted(boxes, key=lambda b: (b.y0 + b.y1) / 2):
        best = None
        for r in rows:
            ov = min(r[1], b.y1) - max(r[0], b.y0)
            if ov > 0.45 * min(b.h, r[1] - r[0]):
                best = r
                break
        if best is None:
            rows.append([b.y0, b.y1, [b]])
        else:
            best[0], best[1] = min(best[0], b.y0), max(best[1], b.y1)
            best[2].append(b)
    rows.sort(key=lambda r: r[0])
    out = []
    for i, r in enumerate(rows):
        for b in sorted(r[2], key=lambda b: b.x0):
            b.row = i
            out.append(b)
    return out


def detect(rgba, bg_colors=None, tolerance=0, use_alpha=None, join=2, attach=True, min_area=8):
    """Corte automático. Devuelve (cajas en orden, etiquetas por píxel, máscara)."""
    if use_alpha is None:
        use_alpha = has_alpha(rgba)
    if bg_colors is None:
        bg_colors = [] if use_alpha else [border_color(rgba)]
    fg = foreground(rgba, bg_colors, tolerance, use_alpha)
    pcs = Pieces(fg, join)
    boxes = smart_merge(pcs.boxes, attach=attach, min_area=min_area)
    boxes = split_touching(boxes, pcs.label)
    return order_rows(boxes), pcs.label, fg


def grid_boxes(fg, cell_w, cell_h, off_x=0, off_y=0, gap_x=0, gap_y=0):
    """Corte por cuadrícula: cada celda con algo es un cuadro (recortado a lo que tiene)."""
    h, w = fg.shape
    out = []
    if cell_w < 2 or cell_h < 2:
        return out
    row = 0
    y = off_y
    while y + 2 <= h:
        x = off_x
        any_in_row = False
        while x + 2 <= w:
            cx1, cy1 = min(w, x + cell_w), min(h, y + cell_h)
            sub = fg[y:cy1, x:cx1]
            if sub.any():
                ys = np.where(sub.any(axis=1))[0]
                xs = np.where(sub.any(axis=0))[0]
                b = Box(x + xs[0], y + ys[0], x + xs[-1] + 1, y + ys[-1] + 1, None, int(sub.sum()),
                        cell=(x, y, cx1, cy1))
                b.row = row
                out.append(b)
                any_in_row = True
            x += cell_w + gap_x
        if any_in_row:
            row += 1
        y += cell_h + gap_y
    return out


def guess_grid(boxes, shape):
    """Tamaño de celda probable a partir de cajas detectadas (para llenar la cuadrícula al principio)."""
    if not boxes:
        return max(8, shape[1] // 8), max(8, shape[0] // 4)
    return int(max(b.w for b in boxes)) + 2, int(max(b.h for b in boxes)) + 2


def merge(boxes, chosen):
    """Une las cajas elegidas en una sola (para arreglar a mano)."""
    if len(chosen) < 2:
        return boxes
    first = chosen[0]
    for b in chosen[1:]:
        first.absorb(b)
    rest = [b for b in boxes if b is first or b not in chosen]
    return order_rows(rest) if first.cell is None else rest


def manual_box(fg, x0, y0, x1, y1):
    h, w = fg.shape
    x0, x1 = sorted((max(0, min(w, int(x0))), max(0, min(w, int(x1)))))
    y0, y1 = sorted((max(0, min(h, int(y0))), max(0, min(h, int(y1)))))
    sub = fg[y0:y1, x0:x1]
    if not sub.any():
        return None
    ys = np.where(sub.any(axis=1))[0]
    xs = np.where(sub.any(axis=0))[0]
    return Box(x0 + xs[0], y0 + ys[0], x0 + xs[-1] + 1, y0 + ys[-1] + 1, None, int(sub.sum()))


# ---------------------------------------------------------------- recortar
def crop(rgba, label, fg, box, bg_colors=(), tolerance=0):
    """RGBA del cuadro: solo sus píxeles; el resto transparente. Con tolerancia (JPG) se limpia el borde
    que quedó manchado con el color del fondo."""
    sub = rgba[box.y0:box.y1, box.x0:box.x1].copy()
    if box.labels is not None and label is not None:
        lab = label[box.y0:box.y1, box.x0:box.x1]
        keep = np.isin(lab, list(box.labels))
    else:
        keep = fg[box.y0:box.y1, box.x0:box.x1]
    if tolerance > 0 and bg_colors:
        keep = _defringe(sub[:, :, :3].astype(np.float32), keep, [np.array(c, np.float32) for c in bg_colors])
    sub[~keep] = 0
    return sub


def _shift(a, dy, dx):
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    ys, yd = (slice(max(0, -dy), h - max(0, dy)), slice(max(0, dy), h - max(0, -dy)))
    xs, xd = (slice(max(0, -dx), w - max(0, dx)), slice(max(0, dx), w - max(0, -dx)))
    out[yd, xd] = a[ys, xs]
    return out


def _defringe(rgb, keep, bgs, passes=3):
    """Quita el borde manchado del fondo (típico de JPG): un píxel del borde se va si se parece más al fondo
    que al interior del sprite que tiene al lado."""
    for _ in range(passes):
        out = ~keep
        edge = keep & (_shift(out, 1, 0) | _shift(out, -1, 0) | _shift(out, 0, 1) | _shift(out, 0, -1))
        if not edge.any():
            break
        inner = keep & ~edge
        acc = np.zeros(rgb.shape, np.float32)
        cnt = np.zeros(keep.shape, np.float32)
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2):
                m = _shift(inner, dy, dx)
                acc += _shift(rgb * inner[:, :, None], dy, dx)
                cnt += m
        has = cnt > 0
        mean = acc / np.maximum(cnt, 1)[:, :, None]
        d_in = np.abs(rgb - mean).max(axis=2)
        d_bg = np.min([np.abs(rgb - b).max(axis=2) for b in bgs], axis=0)
        drop = edge & ((has & (d_bg < d_in)) | (~has & (d_bg < 110)))
        if not drop.any():
            break
        keep = keep & ~drop
    return keep


def foot_x(rgba_crop):
    """Centro de los pies: mediana de x de lo visible en el 20 % de abajo (no se mueve si estira un brazo)."""
    m = rgba_crop[:, :, 3] > 0
    if not m.any():
        return rgba_crop.shape[1] // 2
    ys = np.where(m.any(axis=1))[0]
    y_lo = ys[-1] + 1
    band = m[max(ys[0], y_lo - max(2, int((y_lo - ys[0]) * 0.2))):y_lo]
    xs = np.where(band)[1]
    return int(np.median(xs)) if len(xs) else rgba_crop.shape[1] // 2


AXIS_MODES = ["ground", "feet", "center"]


def axes_for(boxes, crops, mode="ground"):
    """Eje (x, y) de cada cuadro.
    ground: el suelo común de su fila (lo que salta queda arriba) · feet: los pies de cada cuadro ·
    center: el centro · center_feet: el centro de lado a lado y los pies abajo."""
    out = []
    row_bottom = {}
    for b in boxes:
        row_bottom[b.row] = max(row_bottom.get(b.row, 0), b.y1)
    for b, c in zip(boxes, crops):
        h, w = c.shape[:2]
        if mode == "center":
            out.append((w // 2, h // 2))
            continue
        if mode == "center_feet":
            # centrado de lado a lado como «el centro», pero con los pies en el piso
            out.append((w // 2, h))
            continue
        if b.cell is not None:
            x = (b.cell[0] + b.cell[2]) // 2 - b.x0
        else:
            x = foot_x(c)
        if mode == "feet":
            out.append((x, h))
        else:
            out.append((x, row_bottom[b.row] - b.y0))
    return out
