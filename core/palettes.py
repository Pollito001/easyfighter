"""Colores alternativos del personaje (paletas 1,1 … 1,12).

En IKEMEN GO / MUGEN las paletas solo cambian los sprites de 8 bits que usan la paleta del personaje (la 1,1);
los de 32 bits (color verdadero) se ven siempre igual. Aquí:
- pasar los sprites de 32 bits a una paleta compartida de 255 colores (median cut),
- agrupar los colores de la paleta en «partes» (piel, ropa, pelo…) para cambiarlos de un golpe,
- recolorear una parte conservando sus sombras y brillos."""
import colorsys

import numpy as np

KEEP_GROUPS = {9000}      # retratos: se quedan en color verdadero (no gastan colores de la paleta)


# ---------------------------------------------------------------- uso de los colores
def char_index(sff):
    """Lugar de la paleta 1,1 (la del personaje) en la lista del SFF."""
    i = sff.find_palette(1, 1)
    return 0 if i is None else i


def char_sprites(sff):
    """Sprites (base, sin repetir) que cambian con la paleta del personaje: 8 bits con la 1,1."""
    ci = char_index(sff)
    seen, out = set(), []
    for s in sff.sprites:
        b = s.base()
        if id(b) in seen:
            continue
        seen.add(id(b))
        if b.palidx == ci:
            pix = b.pixels()
            if pix.ndim == 2:
                out.append(b)
    return out


def true_color_sprites(sff, keep=KEEP_GROUPS):
    seen, out = set(), []
    for s in sff.sprites:
        b = s.base()
        if id(b) in seen or b.group in keep:
            continue
        seen.add(id(b))
        if b.pixels().ndim == 3:
            out.append(b)
    return out


def usage(sff, limit=600):
    """Cuántos píxeles usan cada color de la paleta del personaje (muestra de hasta `limit` sprites)."""
    counts = np.zeros(256, np.int64)
    sprites = char_sprites(sff)
    step = max(1, len(sprites) // limit)
    for b in sprites[::step]:
        counts += np.bincount(b.pixels().ravel(), minlength=256)[:256]
    counts[0] = 0
    return counts


# ---------------------------------------------------------------- 32 bits → paleta compartida
def _pack(rgb):
    rgb = rgb.astype(np.uint32)
    return (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def _unpack(p):
    return np.stack([(p >> 16) & 255, (p >> 8) & 255, p & 255], axis=-1).astype(np.int32)


def median_cut(cols, weights, n=255):
    """Hasta n colores representativos de (cols, weights)."""
    if len(cols) <= n:
        return cols.astype(np.int32)
    boxes = [np.arange(len(cols))]
    while len(boxes) < n:
        best, score = -1, -1.0
        for i, ix in enumerate(boxes):
            if len(ix) < 2:
                continue
            c = cols[ix]
            rng = (c.max(0) - c.min(0)).max()
            sc = float(rng) * float(np.sqrt(weights[ix].sum()))
            if sc > score:
                best, score = i, sc
        if best < 0 or score <= 0:
            break
        ix = boxes.pop(best)
        c = cols[ix]
        ch = int(np.argmax(c.max(0) - c.min(0)))
        order = ix[np.argsort(c[:, ch], kind="stable")]
        w = np.cumsum(weights[order])
        cut = int(np.searchsorted(w, w[-1] / 2.0))
        cut = min(max(cut, 1), len(order) - 1)
        boxes += [order[:cut], order[cut:]]
    out = []
    for ix in boxes:
        w = weights[ix].astype(np.float64)[:, None]
        out.append(np.round((cols[ix] * w).sum(0) / max(1e-9, w.sum())))
    return np.array(out, np.int32)


def nearest(cols, pal):
    """Índice (en pal) del color más parecido para cada color."""
    out = np.empty(len(cols), np.int64)
    pal = pal.astype(np.int32)
    # el ojo nota más el verde: pesos de luminancia
    wts = np.array([0.30, 0.59, 0.11]) * 3
    for a in range(0, len(cols), 4096):
        d = (((cols[a:a + 4096, None, :] - pal[None, :, :]) ** 2) * wts).sum(2)
        out[a:a + 4096] = d.argmin(1)
    return out


def to_shared_palette(sprites, base_rgb=None, base_counts=None):
    """Pasa sprites RGBA a índices con una paleta compartida.
    base_rgb / base_counts: la paleta que ya usan los sprites de 8 bits y cuánto se usa cada color: esos
    colores se conservan y los nuevos van en los lugares libres. Devuelve (paleta (256,3), {id(sprite): índices})."""
    counts = {}
    for s in sprites:
        px = s.pixels()
        solid = px[:, :, 3] >= 128
        u, c = np.unique(_pack(px[:, :, :3][solid]), return_counts=True)
        for k_, v in zip(u.tolist(), c.tolist()):
            counts[k_] = counts.get(k_, 0) + v
    keys = np.array(sorted(counts), np.uint32)
    weights = np.array([counts[k_] for k_ in keys.tolist()], np.float64)
    cols = _unpack(keys) if len(keys) else np.zeros((0, 3), np.int32)
    pal = np.zeros((256, 3), np.int32)
    if base_rgb is not None:
        pal[:] = np.asarray(base_rgb, np.int32)[:256]
        used = np.asarray(base_counts if base_counts is not None else np.ones(256), np.int64)[:256] > 0
        used[0] = False
        keep = list(np.flatnonzero(used))
        free = [i for i in range(1, 256) if not used[i]]
    else:
        keep, free = [], list(range(1, 256))
    reps = median_cut(cols, weights, len(free)) if free and len(cols) else np.zeros((0, 3), np.int32)
    slots = free[:len(reps)]
    for i, c in zip(slots, reps):
        pal[i] = c
    cand = np.array(sorted(keep + slots), np.int64)
    idx_of = {}
    if len(cols) and len(cand):
        idx_of = dict(zip(keys.tolist(), cand[nearest(cols, pal[cand])].tolist()))
    out = {}
    for s in sprites:
        px = s.pixels()
        solid = px[:, :, 3] >= 128
        packed = _pack(px[:, :, :3])
        u, inv = np.unique(packed, return_inverse=True)
        lut = np.array([idx_of.get(k_, 0) for k_ in u.tolist()], np.uint8)
        idx = lut[inv].reshape(packed.shape).astype(np.uint8)
        idx[~solid] = 0
        out[id(s)] = idx
    return pal.astype(np.uint8), out


# ---------------------------------------------------------------- partes
def _hsv(rgb):
    a = np.asarray(rgb, np.float64) / 255.0
    return np.array([colorsys.rgb_to_hsv(*c) for c in a]) if len(a) else np.zeros((0, 3))


def _features(rgb):
    hsv = _hsv(rgb)
    h, s, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]
    sw = np.clip(s * 1.6, 0, 1) * np.clip(v * 2.5, 0, 1)        # en lo muy oscuro el tono no cuenta
    return np.stack([sw * np.cos(2 * np.pi * h), sw * np.sin(2 * np.pi * h), v * 0.45], axis=1)


def find_parts(rgb, counts, k=8):
    """Agrupa los colores usados en k partes. Devuelve labels (256,) con -1 para los no usados (y el 0),
    ordenadas de la parte más grande a la más chica."""
    rgb = np.asarray(rgb, np.int32)[:256]
    used = np.flatnonzero(np.asarray(counts)[:256] > 0)
    used = used[used != 0]
    labels = -np.ones(256, np.int64)
    if len(used) == 0:
        return labels
    k = max(1, min(int(k), len(used)))
    x = _features(rgb[used])
    w = np.sqrt(np.asarray(counts, np.float64)[used])
    rs = np.random.RandomState(7)
    # k-means++ con pesos
    cent = [x[int(np.argmax(w))]]
    for _ in range(1, k):
        d = np.min([((x - c) ** 2).sum(1) for c in cent], axis=0) * w
        if d.sum() <= 0:
            break
        cent.append(x[rs.choice(len(x), p=d / d.sum())])
    cent = np.array(cent)
    for _ in range(40):
        lab = ((x[:, None, :] - cent[None]) ** 2).sum(2).argmin(1)
        new = np.array([(x[lab == j] * w[lab == j, None]).sum(0) / max(1e-9, w[lab == j].sum())
                        if (lab == j).any() else cent[j] for j in range(len(cent))])
        if np.allclose(new, cent):
            break
        cent = new
    lab = ((x[:, None, :] - cent[None]) ** 2).sum(2).argmin(1)
    # numerar por tamaño
    sizes = [(-(np.asarray(counts)[used][lab == j]).sum(), j) for j in range(len(cent)) if (lab == j).any()]
    remap = {j: n for n, (_s, j) in enumerate(sorted(sizes))}
    labels[used] = [remap[j] for j in lab]
    return labels


def part_color(rgb, counts, labels, part):
    """Color típico de una parte (promedio pesado por uso)."""
    ix = np.flatnonzero(labels == part)
    if not len(ix):
        return (128, 128, 128)
    w = np.asarray(counts, np.float64)[ix][:, None] + 1e-9
    c = (np.asarray(rgb, np.float64)[ix] * w).sum(0) / w.sum()
    return tuple(int(round(v)) for v in c)


def _circ(d):
    return (d + 0.5) % 1.0 - 0.5


def recolor(base_rgb, counts, labels, parts=None, singles=None):
    """Paleta nueva: base_rgb con cada parte llevada a su color (conservando sombras y brillos) y luego los
    colores sueltos cambiados a mano."""
    out = np.asarray(base_rgb, np.int32)[:256].copy()
    for key, target in (parts or {}).items():
        part = int(key)
        ix = np.flatnonzero(labels == part)
        if not len(ix) or target is None:
            continue
        b = colorsys.rgb_to_hsv(*(np.array(part_color(base_rgb, counts, labels, part)) / 255.0))
        t = colorsys.rgb_to_hsv(*(np.array(target, np.float64) / 255.0))
        for i in ix:
            h, s, v = colorsys.rgb_to_hsv(*(out[i] / 255.0))
            nh = t[0] if b[1] < 0.15 else (t[0] + _circ(h - b[0])) % 1.0
            ns = float(np.clip(s + (t[1] - b[1]), 0, 1)) if b[1] >= 0.15 else float(np.clip(t[1] * (0.6 + 0.4 * v), 0, 1))
            mult = v * (t[2] / b[2]) if b[2] > 0.03 else t[2]
            nv = float(np.clip(0.5 * mult + 0.5 * (v + t[2] - b[2]), 0, 1))
            out[i] = np.round(np.array(colorsys.hsv_to_rgb(nh, ns, nv)) * 255)
    for key, c in (singles or {}).items():
        i = int(key)
        if 0 < i < 256 and c is not None:
            out[i] = c
    return np.clip(out, 0, 255).astype(np.uint8)


def random_parts(base_rgb, counts, labels, rng=None, keep_dark=True):
    """Colores al azar (pero que combinen) para cada parte."""
    rng = rng or np.random.default_rng()
    n = int(labels.max()) + 1 if (labels >= 0).any() else 0
    hue0 = rng.random()
    out = {}
    for p in range(n):
        c = part_color(base_rgb, counts, labels, p)
        h, s, v = colorsys.rgb_to_hsv(*(np.array(c) / 255.0))
        if keep_dark and v < 0.18:
            continue            # contornos y negros: se quedan
        if 0.02 <= h <= 0.13 and 0.18 <= s <= 0.65 and v >= 0.45:
            continue            # piel: se queda (una piel morada no se ve bien)
        # tonos repartidos alrededor de uno base (esquema armónico)
        nh = (hue0 + rng.choice([0, 0.08, 0.33, 0.5, 0.58, 0.92]) + rng.normal(0, 0.03)) % 1.0
        ns = float(np.clip(max(s, 0.35) * rng.uniform(0.8, 1.2), 0.2, 1))
        nv = float(np.clip(v * rng.uniform(0.85, 1.15), 0.15, 1))
        out[str(p)] = [int(round(x * 255)) for x in colorsys.hsv_to_rgb(nh, ns, nv)]
    return out
