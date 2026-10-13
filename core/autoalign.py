"""Alineación automática avanzada de sprites.

Para cada sprite se identifica:
  - la silueta (lo que no es transparente),
  - el «cuerpo» (tronco y cabeza): la silueta «comida» por los bordes hasta que desaparecen brazos y piernas,
  - los pies: la fila más baja y el centro de la franja de abajo.

Con eso cada animación se alinea así:
  - el primer cuadro se ancla a la animación de parado (el cuerpo en el mismo lugar respecto al eje),
  - los demás se encadenan con el cuadro anterior buscando el corrimiento en que más se parecen
    (correlación de siluetas, con más peso en el cuerpo), así la animación no «brinca»,
  - en el suelo los pies quedan sobre el suelo; en el aire se respeta la altura del cuerpo;
    acostado se usa la fila de abajo y el centro del cuerpo.

Solo usa numpy. Las coordenadas del eje son las del SFF: (x, y) dentro de la imagen.
"""
import numpy as np

MODES = [("feet", 'Suelo: pie fijo'), ("ground", 'Suelo: cuerpo fijo'), ("air", 'Aire: golpes'),
         ("spin", 'Aire: vueltas y caídas'), ("lying", 'Acostado')]
MODE_TIPS = {
    "feet": 'Pies en el suelo y el pie de apoyo quieto. Para golpes, cubrirse y recibir golpes.',
    "ground": 'Pies en el suelo y el cuerpo quieto. Para parado, caminar, correr, agarres y especiales.',
    "air": 'El tronco siempre en el mismo lugar. Para golpes en el aire y cubrirse en el aire.',
    "spin": 'Para saltos con vueltas, salir volando y caer: se usa el centro del dibujo.',
    "lying": 'Acostado en el suelo: la parte de abajo sobre el suelo.',
}


class Feat:
    """Datos de un sprite para alinearlo."""

    def __init__(self, pix):
        m = pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0
        self.mask = m
        self.h, self.w = m.shape
        self.ok = bool(m.any())
        if not self.ok:
            self.bottom, self.feet_x, self.core = self.h, self.w // 2, (self.w / 2, self.h / 2)
            self.weight = m.astype(np.float32)
            self.weight_feet = self.weight
            return
        rows = np.where(m.any(axis=1))[0]
        top, bottom = int(rows[0]), int(rows[-1]) + 1
        self.top, self.bottom = top, bottom
        band = m[max(top, bottom - max(2, (bottom - top) // 6)):bottom]
        xs = np.where(band)[1]
        self.feet_x = int(np.median(xs)) if len(xs) else self.w // 2
        core = erode_core(m, max(2, int(round((bottom - top) * 0.07))))
        ys, xs = np.nonzero(core)
        self.core = (float(xs.mean()), float(ys.mean())) if len(xs) else self.centroid()
        # peso: la silueta cuenta 1 y el cuerpo 3 (así se alinean los cuerpos, no los brazos y piernas)
        self.weight = m.astype(np.float32) + 2.0 * core.astype(np.float32)
        # para golpes: además mucho peso a la franja de los pies (el pie de apoyo no se mueve)
        lo = max(top, bottom - max(2, int((bottom - top) * 0.15)))
        band_w = np.zeros_like(self.weight)
        band_w[lo:bottom] = m[lo:bottom]
        self.weight_feet = self.weight + 4.0 * band_w

    def centroid(self):
        ys, xs = np.nonzero(self.mask)
        return float(xs.mean()), float(ys.mean())


def erode_core(m, r):
    """Quita brazos y piernas: erosiona r veces; si se borra todo, prueba con menos."""
    while r >= 1:
        c = m.copy()
        for _ in range(r):
            n = c.copy()
            n[1:, :] &= c[:-1, :]
            n[:-1, :] &= c[1:, :]
            n[:, 1:] &= c[:, :-1]
            n[:, :-1] &= c[:, 1:]
            c = n
            if not c.any():
                break
        if c.any():
            return c
        r //= 2
    return m


def best_shift(a, b, max_dx, max_dy, fixed_dy=None):
    """t = (tx, ty) que hace que b(p + t) se parezca más a a(p). a, b: pesos (float)."""
    H = a.shape[0] + b.shape[0]
    W = a.shape[1] + b.shape[1]
    fa = np.fft.rfft2(a, (H, W))
    fb = np.fft.rfft2(b, (H, W))
    corr = np.fft.irfft2(np.conj(fa) * fb, (H, W))
    # corr[ty, tx] = sum a(p) b(p + t) (índices negativos dan la vuelta)
    best, bt = None, (0, 0)
    dys = [fixed_dy] if fixed_dy is not None else range(-max_dy, max_dy + 1)
    for ty in dys:
        if abs(ty) >= H:
            continue
        row = corr[ty % H]
        for tx in range(-max_dx, max_dx + 1):
            v = row[tx % W]
            # en empate, el corrimiento más chico
            if best is None or v > best + 1e-6 or (abs(v - best) <= 1e-6 and abs(tx) + abs(ty) < sum(map(abs, bt))):
                best, bt = v, (tx, ty)
    return bt


class Aligner:
    """Calcula ejes nuevos. get_sprite(key) → sprite (con .pixels(), .x, .y) o None."""

    def __init__(self, get_sprite):
        self.get_sprite = get_sprite
        self.feats = {}
        self.ref = None          # (feat, eje) del cuadro de referencia (parado)
        self.done = {}           # ejes ya decididos en esta pasada

    def feat(self, key):
        key = tuple(key)
        if key not in self.feats:
            s = self.get_sprite(key)
            self.feats[key] = Feat(s.pixels()) if s is not None else None
        return self.feats[key]

    def axis(self, key):
        key = tuple(key)
        if key in self.done:
            return self.done[key]
        s = self.get_sprite(key)
        return (s.x, s.y) if s is not None else (0, 0)

    def set_reference(self, key):
        f = self.feat(key)
        if f is None or not f.ok:
            return False
        self.ref = (f, self.axis(key))
        return True

    def ref_offset(self):
        """Dónde queda el cuerpo de parado respecto a su eje: (dx, dy)."""
        f, (ax, ay) = self.ref
        return f.core[0] - ax, f.core[1] - ay

    def foot_off(self):
        """Cuánto por debajo (o encima) del suelo tiene los pies la de parado (casi siempre 0)."""
        if self.ref is None:
            return 0
        f, (_ax, ay) = self.ref
        return ay - f.bottom

    def anchor(self, f, mode):
        """Eje del primer cuadro de una animación, para que el cuerpo quede donde el de parado."""
        if self.ref is None:
            return f.feet_x, f.bottom
        dx, dy = self.ref_offset()
        x = int(round(f.core[0] - dx))
        if mode == "air":
            return x, int(round(f.core[1] - dy))
        if mode in ("ground", "feet"):
            rf, (rax, ray) = self.ref
            # buscar el corrimiento horizontal en que más se parece a parado (con los pies en el suelo)
            mx = max(8, min(f.w, rf.w) // 3)
            tx, _ty = best_shift(rf.weight, f.weight, mx, 0, fixed_dy=f.bottom - rf.bottom)
            x2 = rax + tx
            # si la correlación se va muy lejos del cuerpo, quedarse con el cuerpo
            if abs(x2 - x) > max(6, f.w // 6):
                x2 = x
            return int(x2), f.bottom + self.foot_off()
        return x, f.bottom + self.foot_off()          # acostado

    def align(self, keys, mode="ground", keep_first=False):
        """Ejes para los cuadros de una animación. Devuelve {key: (x, y)} y los recuerda.

        ground: pies en el suelo y cada cuadro encadenado con el anterior (correlación de siluetas, el cuerpo
                pesa más: no se desliza al caminar).
        feet:   igual, pero pesa más la franja de los pies (en los golpes el pie de apoyo no se mueve).
        air:    el tronco en el mismo lugar en todos los cuadros (sirve para golpes en el aire).
        spin:   el tronco en horizontal y el centro de la silueta en vertical (vueltas, caídas, saltos).
        lying:  la fila de abajo en el suelo y el tronco en horizontal.
        """
        keys = [tuple(k) for k in keys]
        out = {}
        prev = None
        const = None            # (dx, dy) fijos de la animación: rasgo − eje
        for k in keys:
            f = self.feat(k)
            if f is None or not f.ok:
                continue
            if k in self.done:
                ax, ay = self.done[k]
            elif mode == "lying":
                ax, ay = self.anchor(f, mode)
            elif mode in ("air", "spin"):
                fy = f.core[1] if mode == "air" else (f.top + f.bottom) / 2
                if const is None:
                    ax0, ay0 = self.axis(k) if keep_first else self.anchor(f, "air")
                    const = (f.core[0] - ax0, fy - ay0)
                ax, ay = int(round(f.core[0] - const[0])), int(round(fy - const[1]))
            elif prev is None:
                ax, ay = self.axis(k) if keep_first else self.anchor(f, mode)
            else:
                pf, (pax, _pay) = prev
                ty = f.bottom - pf.bottom
                mx = max(8, min(f.w, pf.w) // 3)
                wa, wb = (pf.weight_feet, f.weight_feet) if mode == "feet" else (pf.weight, f.weight)
                tx, _ = best_shift(wa, wb, mx, 0, fixed_dy=ty)
                ax, ay = pax + tx, f.bottom + self.foot_off()
                # red de seguridad: si se aleja demasiado del cuerpo, usar el cuerpo
                if self.ref is not None:
                    cx = self.anchor(f, "lying")[0]
                    if abs(ax - cx) > max(10, f.w // 4):
                        ax = cx
            ax, ay = int(ax), int(ay)
            if (mode in ("air", "spin")) and const is None:
                const = (f.core[0] - ax, ((f.core[1] if mode == "air" else (f.top + f.bottom) / 2)) - ay)
            out[k] = (ax, ay)
            self.done[k] = (ax, ay)
            prev = (f, (ax, ay))
        return out


# cómo se alinea cada casilla del modo simple
SPIN_SLOTS = {"jump_up", "jump_down", "jump_fwd", "fly", "fall", "air_recover", "trip"}
FEET_SLOTS = {"guard_s", "guard_c", "hit_high", "hit_low", "hit_crouch", "dizzy"}
AIR_SLOTS = {"hop", "guard_a"}
LYING_SLOTS = {"ground_hit", "lie"}


def mode_for_slot(kind, key=None, sp=None):
    """kind: anim / normal / throw / special / ad. Devuelve ground / air / spin / lying."""
    if kind == "anim":
        if key in SPIN_SLOTS:
            return "spin"
        if key in AIR_SLOTS:
            return "air"
        if key in LYING_SLOTS:
            return "lying"
        if key in FEET_SLOTS:
            return "feet"
        return "ground"
    if kind == "normal":
        return "air" if str(key).startswith("A_") else "feet"
    if kind == "ad":
        return "feet"
    if kind == "special" and sp is not None and sp.get("use_where") == "air":
        return "air"
    return "ground"
