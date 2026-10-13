"""Agrandar (o achicar) sprites y animaciones de verdad, en vez de usar el «tamaño» ([Size] xscale/yscale)."""
import numpy as np

from core.air import Action
from core.sff import Sprite


def scale_pixels(pix, f):
    """Vecino más cercano: los píxeles se agrandan sin ponerse borrosos (sirve para paleta y para RGBA)."""
    h, w = pix.shape[:2]
    nh, nw = max(1, int(round(h * f))), max(1, int(round(w * f)))
    ys = np.minimum((np.arange(nh) / f).astype(np.int64), h - 1)
    xs = np.minimum((np.arange(nw) / f).astype(np.int64), w - 1)
    return np.ascontiguousarray(pix[ys][:, xs])


def scale_sprite(s, f):
    n = Sprite(s.group, s.number, int(round(s.x * f)), int(round(s.y * f)))
    n.set_pixels(scale_pixels(s.pixels(), f))
    n.palidx = s.base().palidx
    return n


def scale_action(a, f):
    b = Action(a.number)
    b.loopstart, b.header, b.title, b.raw = a.loopstart, list(a.header), a.title, None
    for fr in a.frames:
        c = fr.copy()
        c.x, c.y = int(round(fr.x * f)), int(round(fr.y * f))
        c.clsn1 = [tuple(int(round(v * f)) for v in bx) for bx in fr.clsn1]
        c.clsn2 = [tuple(int(round(v * f)) for v in bx) for bx in fr.clsn2]
        b.frames.append(c)
    return b
