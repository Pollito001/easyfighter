"""
Velocidades de moverse y saltar en el modo simple: cada casilla que mueve al personaje (caminar, correr,
salto hacia atrás, saltos) tiene su velocidad, un botón para ajustarla y una prueba animada.

- Caminar y correr: se miden los pasos de la animación (el pie apoyado no debe patinar).
- Saltos y salto hacia atrás: no hay pies en el suelo, así que se ajustan al tamaño del personaje
  (comparado con uno normal como Kung Fu Man).
"""
import math

import numpy as np
from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
    QWidget,
)

from i18n import tr
from ui import theme
from ui.common import APP_NAME

REF_HEIGHT = 105.0      # alto de Kung Fu Man parado (para 320×240), al que van las velocidades de la plantilla
# valores de la plantilla para 320×240 (los de Kung Fu Man)
JUMP_DEFAULTS = [
    ("jump.neu", 1, -8.4), ("jump.back", 0, -2.55), ("jump.fwd", 0, 2.5),
    ("runjump.back", 0, -2.55), ("runjump.back", 1, -8.1), ("runjump.fwd", 0, 4.0), ("runjump.fwd", 1, -8.1),
    ("airjump.neu", 1, -8.1), ("airjump.back", 0, -2.55), ("airjump.fwd", 0, 2.5),
    ("run.back", 0, -4.5), ("run.back", 1, -3.8),
]
WALK_DEFAULTS = {"walk.fwd": 2.4, "walk.back": -2.2, "run.fwd": 4.6}

# casilla → (campos [(etiqueta, clave, índice, signo)], cómo se ajusta, prueba)
MOVE_CTRL = {
    "walk_f": ([('Velocidad', "walk.fwd", 0, 1)], ("stride", 20, 1, "walk.fwd"), "walk"),
    "walk_b": ([('Velocidad', "walk.back", 0, -1)], ("stride", 21, -1, "walk.back"), "back"),
    "run": ([('Velocidad', "run.fwd", 0, 1)], ("stride", 100, 1, "run.fwd"), "run"),
    "hop": ([('Distancia', "run.back", 0, -1)], ("size",), "hop"),
    "jump_up": ([('Altura', "jump.neu", 1, -1)], ("size",), "jump_up"),
    "jump_down": ([], ("size",), "jump_back"),
    "jump_fwd": ([('Avance adelante', "jump.fwd", 0, 1), ('Avance atrás', "jump.back", 0, -1)], ("size",),
                 "jump_fwd"),
}
TESTS = [("walk", 'Caminar adelante'), ("back", 'Caminar atrás'), ("run", 'Correr'), ("hop", 'Salto hacia atrás'),
         ("jump_up", 'Salto quieto'), ("jump_fwd", 'Salto adelante'), ("jump_back", 'Salto atrás')]


# ---------------------------------------------------------------- medir
def _contacts(pix, ax, ay, fx=0, fy=0, band=3, tol=4):
    m = pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0
    if not m.any():
        return None
    rows = np.where(m.any(axis=1))[0]
    bottom = int(rows[-1])
    if abs((bottom + 1 - ay) + fy) > tol:
        return None
    sub = m[max(0, bottom - band + 1):bottom + 1]
    xs = np.where(sub.any(axis=0))[0]
    return set(int(x - ax + fx) for x in xs)


def stride_speed(frames, direction=1, max_shift=80):
    """Unidades por tick que avanza el pie apoyado. frames: [(pixeles, eje_x, eje_y, dx, dy, tiempo)]."""
    cs = [(_contacts(p, ax, ay, fx, fy), t) for p, ax, ay, fx, fy, t in frames]
    speeds = []
    n = len(cs)
    for i in range(n):
        a, t = cs[i]
        b, _t = cs[(i + 1) % n]
        if not a or not b or t <= 0:
            continue
        best, best_s = 0.0, None
        for s in range(1, max_shift):
            d = -s * direction
            hit = sum(1 for x in a if (x + d) in b)
            score = hit / max(1, min(len(a), len(b)))
            if score > best:
                best, best_s = score, s
        if best_s is not None and best >= 0.6:
            speeds.append(best_s / t)
    if len(speeds) < 2:
        return None
    return float(np.median(speeds))


class Motion:
    """Lee y escribe las velocidades del .cns del personaje para el modo simple."""

    def __init__(self, sm):
        self.sm = sm
        self._consts = None

    def doc(self):
        p = self.sm.main.project
        f = p.file("cns") if p else None
        if f is None or f.suffix.lower() == ".zss":
            return None
        return self.sm.main.code.get_open(f).doc

    def consts(self):
        if self._consts is None:
            from core.simulate import parse_constants
            d = self.doc()
            self._consts = parse_constants(d.toPlainText()) if d is not None else {}
        return self._consts

    def forget(self):
        self._consts = None

    def get(self, key, index):
        return self.consts().get(f"velocity.{key}." + ("y" if index else "x"))

    def set_many(self, changes):
        """changes: [(clave en [Velocity], índice, valor)]."""
        from ui.simple_mode import set_const, set_doc_text
        d = self.doc()
        if d is None:
            return
        text = old = d.toPlainText()
        for key, index, value in changes:
            text = set_const(text, "Velocity", key, index, round(float(value), 2))
        if text != old:
            set_doc_text(d, text)
            self.sm.main.sim.states = {}
        self.forget()

    def fix_stop(self):
        """Que al soltar el control se pare en seco: el umbral de frenado de parado va con la velocidad de
        caminar (si camina rápido y el umbral es bajo, resbala unos ticks y parece que da un brinco)."""
        from ui.simple_mode import set_const, set_doc_text
        d = self.doc()
        if d is None:
            return
        c = self.consts()
        if "movement.stand.friction.threshold" not in c:
            return
        top = max(abs(c.get("velocity.walk.fwd.x", 0) or 0), abs(c.get("velocity.walk.back.x", 0) or 0))
        want = round(max(2.0 * self.k(), top * 0.9), 2)
        if abs((c.get("movement.stand.friction.threshold") or 0) - want) > 0.01:
            set_doc_text(d, set_const(d.toPlainText(), "Movement", "stand.friction.threshold", 0, want))
            self.forget()

    def scale(self):
        return float(self.consts().get("size.xscale", 1.0) or 1.0)

    def k(self):
        p = self.sm.main.project
        return p.localcoord()[0] / 320 if p else 1.0

    def gravity(self):
        return float(self.consts().get("movement.yaccel", 0.44 * self.k()) or 0.44)

    def height_factor(self):
        """Alto del personaje parado (con su tamaño) comparado con uno normal; None si no se puede medir."""
        p = self.sm.main.project
        a = p.air.find(0) if p else None
        if a is None or not a.frames or self.sm.is_placeholder(a):
            return None
        f = a.frames[0]
        s = self.sm.sprite(f.group, f.number)
        if s is None:
            return None
        pix = s.pixels()
        m = pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0
        if not m.any():
            return None
        top = int(np.where(m.any(axis=1))[0][0])
        h = (s.y - top) * self.scale()
        return max(0.1, h / (REF_HEIGHT * self.k()))

    def fit_stride(self, num, direction, key):
        """Velocidad según los pasos de la acción num. Devuelve (valor, cómo) o (None, motivo)."""
        p = self.sm.main.project
        a = p.air.find(num)
        if a is not None and not self.sm.is_placeholder(a):
            idx = p.sff.index()
            fr = []
            for f in a.frames:
                sp = idx.get((f.group, f.number))
                if sp is not None:
                    fr.append((sp.pixels(), sp.x, sp.y, f.x, f.y, f.time))
            v = stride_speed(fr, direction)
            if v:
                return round(v * self.scale(), 2) * (1 if direction > 0 else -1), "stride"
        f = self.height_factor()
        if f is None:
            return None, None
        return round(WALK_DEFAULTS[key] * self.k() * f, 2), "size"

    def fit_jumps(self):
        f = self.height_factor()
        if f is None:
            return False
        r = math.sqrt(f) * self.k()
        self.set_many([(key, i, v * r) for key, i, v in JUMP_DEFAULTS])
        return True


# ---------------------------------------------------------------- prueba animada
class MotionPreview(QWidget):
    def __init__(self, sm):
        super().__init__()
        self.sm = sm
        self.mode = "walk"
        self.tick = 0
        self.setMinimumSize(QSize(520, 300))
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.step)
        self.timer.start()

    def set_mode(self, mode):
        self.mode = mode
        self.tick = 0
        self.update()

    def step(self):
        from ui.common import advance
        advance(self)

    # ---- qué cuadro y dónde, en el tick t
    def anim_frame(self, num, t):
        a = self.sm.main.project.air.find(num)
        if a is None or not a.frames:
            return None
        if not any(f.time < 0 for f in a.frames):
            # animación que se repite (caminar, correr…): vuelve a empezar desde su «loopstart»
            total = sum(max(1, f.time) for f in a.frames)
            if t >= total:
                ls = max(0, min(len(a.frames) - 1, int(getattr(a, "loopstart", 0) or 0)))
                head = sum(max(1, f.time) for f in a.frames[:ls])
                loop = max(1, total - head)
                t = head + (t - head) % loop
        acc = 0
        for f in a.frames:
            if f.time < 0:
                return f
            acc += max(1, f.time)
            if t < acc:
                return f
        return a.frames[-1]

    def anim_len(self, num, default=4):
        a = self.sm.main.project.air.find(num)
        if a is None or not a.frames:
            return default
        if any(f.time < 0 for f in a.frames):
            return sum(f.time for f in a.frames if f.time > 0) or default
        return sum(f.time for f in a.frames) or default

    def state(self, t):
        """(acción, tick dentro de la acción, x, y) en unidades del juego."""
        mo = self.sm.motion
        if self.mode in ("walk", "back", "run"):
            key, num = {"walk": ("walk.fwd", 20), "back": ("walk.back", 21), "run": ("run.fwd", 100)}[self.mode]
            v = mo.get(key, 0) or 0
            return num, t, v * t, 0.0
        if self.mode == "hop":
            vx, vy = (mo.get("run.back", 0) or 0), (mo.get("run.back", 1) or 0)
            nums = (105, 105, 106)
        else:
            vy = mo.get("jump.neu", 1) or -8.4
            vx = {"jump_up": 0, "jump_fwd": mo.get("jump.fwd", 0) or 0,
                  "jump_back": mo.get("jump.back", 0) or 0}[self.mode]
            col = {"jump_up": 0, "jump_fwd": 1, "jump_back": 2}[self.mode]
            nums = (41 + col, 44 + col, 47)
        g = mo.gravity()
        pre = 0 if self.mode == "hop" else self.anim_len(40)
        air = max(1, int(math.ceil(-2 * vy / g))) if vy < 0 else 1
        land = self.anim_len(nums[2], 6)
        total = pre + air + land + 20
        t = t % total
        if t < pre:
            return 40, t, 0.0, 0.0
        t -= pre
        if t < air:
            y = vy * t + g * t * t / 2
            num = nums[0] if (vy + g * t) < 0 else nums[1]
            return num, t, vx * t, min(0.0, y)
        t -= air
        return (nums[2], t, vx * air, 0.0) if t < land else (0, t - land, vx * air, 0.0)

    def paintEvent(self, _e):
        p = QPainter(self)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.CANVAS))
        p.drawRoundedRect(r, 8, 8)
        pr = self.sm.main.project
        if not pr:
            p.end()
            return
        mo = self.sm.motion
        scale = mo.scale()
        a0 = pr.air.find(0)
        s0 = self.sm.sprite(a0.frames[0].group, a0.frames[0].number) if a0 and a0.frames else None
        tall = (s0.y if s0 is not None else 100) * scale
        jump_h = 0.0
        if self.mode.startswith("jump"):
            vy = mo.get("jump.neu", 1) or -8.4
            jump_h = vy * vy / (2 * mo.gravity())
        elif self.mode == "hop":
            vy = mo.get("run.back", 1) or 0
            jump_h = vy * vy / (2 * mo.gravity())
        z = min((r.height() - 50) / max(1.0, tall + jump_h), 3.0)
        oy = r.bottom() - 30
        span = (r.width() - 60) / z
        num, ta, x, y = self.state(self.tick)
        # que dé la vuelta dentro del cuadro
        start = span * (0.15 if self.mode not in ("back", "hop", "jump_back") else 0.85)
        xx = (start + x) % span
        ox = r.left() + 30
        p.setPen(QPen(QColor(255, 107, 53, 160), 1))
        p.drawLine(int(r.left() + 6), int(oy), int(r.right() - 6), int(oy))
        p.setPen(QPen(QColor(139, 147, 163, 120), 1))
        u = 0.0
        while u <= span:
            px = ox + u * z
            p.drawLine(int(px), int(oy), int(px), int(oy + 7))
            u += 16
        f = self.anim_frame(num, ta) or self.anim_frame(0, ta)
        if f is not None:
            s = self.sm.sprite(f.group, f.number)
            pm = self.sm.pixmap(f.group, f.number) if s is not None else None
            if pm is not None:
                h, w = s.pixels().shape[:2]
                cx, cy = ox + xx * z, oy + y * z
                p.drawPixmap(QRectF(cx + (f.x - s.x) * scale * z, cy + (f.y - s.y) * scale * z,
                                    w * scale * z, h * scale * z), pm, QRectF(pm.rect()))
        p.end()


class MotionTestDialog(QDialog):
    def __init__(self, sm, mode):
        super().__init__(sm.main)
        self.setWindowTitle(tr('▶ Prueba de movimiento'))
        self.resize(760, 470)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.combo = QComboBox()
        for k, t in TESTS:
            self.combo.addItem(tr(t), k)
        self.combo.setCurrentIndex(max(0, self.combo.findData(mode)))
        row.addWidget(self.combo)
        row.addStretch(1)
        lay.addLayout(row)
        self.view = MotionPreview(sm)
        self.view.set_mode(mode)
        self.combo.currentIndexChanged.connect(lambda _i: self.view.set_mode(self.combo.currentData()))
        lay.addWidget(self.view, 1)
        from ui.common import PlaybackBar
        lay.addWidget(PlaybackBar(self.view))
        hint = QLabel(tr('Las marcas del piso están quietas: al caminar o correr, el pie apoyado no debe resbalar '
                         'sobre ellas. En los saltos mira si la altura y la distancia se ven bien para su '
                         'tamaño.'))
        hint.setWordWrap(True)
        hint.setObjectName("CardPath")
        lay.addWidget(hint)
        b = QPushButton(tr('Cerrar'))
        b.clicked.connect(self.accept)
        lay.addWidget(b, 0, Qt.AlignmentFlag.AlignRight)


# ---------------------------------------------------------------- en cada casilla
class MoveControls(QWidget):
    changed = pyqtSignal()

    def __init__(self, sm, slot):
        super().__init__()
        self.sm = sm
        self.slot = slot
        fields, self.fit, self.test = MOVE_CTRL[slot]
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(4)
        f = QFormLayout()
        f.setContentsMargins(0, 0, 0, 0)
        self.spins = []
        for label, key, index, sign in fields:
            sp = QDoubleSpinBox()
            sp.setDecimals(2)
            sp.setSingleStep(0.1)
            sp.setRange(0, 999)
            sp.valueChanged.connect(self.on_spin)
            f.addRow(tr(label) + ":", sp)
            self.spins.append((sp, key, index, sign))
        lay.addLayout(f)
        row = QHBoxLayout()
        row.setSpacing(4)
        if self.fit[0] == "stride":
            b = QPushButton(tr('🦶 A sus pasos'))
            b.setToolTip(tr('Mide los pasos de la animación y pone la velocidad para que los pies no patinen.'))
        else:
            b = QPushButton(tr('📏 A su tamaño'))
            b.setToolTip(tr('Ajusta la altura y la distancia de todos los saltos al tamaño de tu personaje.'))
        b.clicked.connect(self.on_fit)
        t = QPushButton(tr('▶ Probar'))
        t.clicked.connect(lambda: MotionTestDialog(self.sm, self.test).exec())
        row.addWidget(b, 1)
        row.addWidget(t, 1)
        lay.addLayout(row)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(400)
        self.timer.timeout.connect(self.write)
        self._binding = False

    def bind(self):
        self._binding = True
        mo = self.sm.motion
        for sp, key, index, sign in self.spins:
            v = mo.get(key, index)
            sp.setEnabled(v is not None)
            sp.setValue(abs(v) if v is not None else 0)
        self._binding = False

    def on_spin(self, *_a):
        if not self._binding:
            self.timer.start()

    def write(self):
        changes = [(key, index, sp.value() * sign) for sp, key, index, sign in self.spins if sp.isEnabled()]
        if changes:
            self.sm.motion.set_many(changes)
            if self.slot in ("walk_f", "walk_b"):
                self.sm.motion.fix_stop()
            self.sm.motion_changed()

    def on_fit(self):
        mo = self.sm.motion
        if self.fit[0] == "stride":
            _kind, num, direction, key = self.fit
            v, how = mo.fit_stride(num, direction, key)
            if v is None:
                QMessageBox.information(self, APP_NAME, tr('No pude medir: pon primero la animación de esta casilla '
                                                           '(con los pies en el suelo) o la de «Parado».'))
                return
            mo.set_many([(key, 0, v)])
            if self.slot in ("walk_f", "walk_b"):
                mo.fix_stop()
            if how == "size":
                QMessageBox.information(self, APP_NAME, tr('No encontré los pies en el suelo en esta animación, '
                                                           'así que la ajusté al tamaño de tu personaje.'))
        else:
            if not mo.fit_jumps():
                QMessageBox.information(self, APP_NAME, tr('Pon primero la animación de «Parado» para saber qué '
                                                           'tan grande es tu personaje.'))
                return
        self.sm.motion_changed()
