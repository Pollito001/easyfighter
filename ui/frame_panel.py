"""Panel de propiedades del cuadro (como en Fighter Factory): cada dato con su caja o su lista de opciones."""
import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QLabel, QSpinBox, QToolButton, QVBoxLayout,
    QWidget,
)

from i18n import tr

FLIP_OPTIONS = [("", 'Ninguno'), ("H", 'Horizontal'), ("V", 'Vertical'), ("HV", 'Ambos (H y V)')]
TRANS_OPTIONS = [("", 'Ninguna'), ("A", 'Suma (brilla)'), ("A1", 'Suma suave (A1)'), ("S", 'Resta (oscurece)'),
                 ("AS", 'Mezcla (origen / destino)')]
TRANS_RE = re.compile(r"^AS(\d+)D(\d+)$", re.IGNORECASE)


def flip_label(code):
    code = (code or "").upper()
    for c, label in FLIP_OPTIONS:
        if c == code:
            return tr(label)
    return code


def parse_trans(text):
    """('', 'A', 'A1', 'S' o 'AS', origen, destino)."""
    t = (text or "").strip().upper()
    m = TRANS_RE.match(t)
    if m:
        return "AS", int(m.group(1)), int(m.group(2))
    if t in ("A", "A1", "S"):
        return t, 256, 256
    if t in ("", "NONE"):
        return "", 256, 256
    return t, 256, 256


def trans_text(kind, src, dst):
    if kind == "AS":
        return f"AS{src}D{dst}"
    return kind


def trans_label(text):
    kind, src, dst = parse_trans(text)
    for c, label in TRANS_OPTIONS:
        if c == kind:
            return tr(label) + (f" {src}/{dst}" if kind == "AS" else "")
    return text


class FramePanel(QWidget):
    """Emite changed(campo, valor) y applyAll(campo) para que la pestaña registre el cambio (con deshacer)."""
    changed = pyqtSignal(str, object)
    applyAll = pyqtSignal(str)
    nudge = pyqtSignal(int, int)
    loopToggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._block = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 4)
        g = QGridLayout()
        g.setHorizontalSpacing(6)
        g.setVerticalSpacing(4)
        lay.addLayout(g)

        def spin(lo, hi, special=None):
            s = QSpinBox()
            s.setRange(lo, hi)
            if special:
                s.setSpecialValueText(special)
            s.setAccelerated(True)
            s.setMinimumWidth(60)
            return s

        def dspin(lo, hi, step, dec):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setSingleStep(step)
            s.setDecimals(dec)
            s.setAccelerated(True)
            s.setMinimumWidth(60)
            return s

        def all_btn(field, tip):
            b = QToolButton()
            b.setText("⇶")
            b.setObjectName("Nudge")
            b.setFixedWidth(28)
            b.setToolTip(tip)
            b.clicked.connect(lambda: self.applyAll.emit(field))
            return b

        # sprite
        self.group = spin(-1, 65535)
        self.number = spin(-1, 65535)
        g.addWidget(QLabel(tr('Grupo:')), 0, 0)
        g.addWidget(QLabel(tr('Número:')), 0, 1)
        g.addWidget(self.group, 1, 0)
        g.addWidget(self.number, 1, 1)
        self.missing = QLabel()
        self.missing.setObjectName("Error")
        g.addWidget(self.missing, 2, 0, 1, 3)
        # desplazamiento
        self.x = spin(-9999, 9999)
        self.y = spin(-9999, 9999)
        g.addWidget(QLabel(tr('Desplazamiento X:')), 3, 0)
        g.addWidget(QLabel(tr('Desplazamiento Y:')), 3, 1)
        g.addWidget(self.x, 4, 0)
        g.addWidget(self.y, 4, 1)
        g.addWidget(all_btn("offset", tr('Usar este desplazamiento en todos los cuadros')), 4, 2)
        arrows = QGridLayout()
        arrows.setSpacing(2)
        for txt, dx, dy, r, c in (("▲", 0, -1, 0, 1), ("◀", -1, 0, 1, 0), ("▶", 1, 0, 1, 2), ("▼", 0, 1, 2, 1)):
            b = QToolButton()
            b.setText(txt)
            b.setObjectName("Nudge")
            b.setFixedSize(30, 24)
            b.setAutoRepeat(True)
            b.setToolTip(tr('Mover el cuadro 1 píxel'))
            b.clicked.connect(lambda _c, dx=dx, dy=dy: self.nudge.emit(dx, dy))
            arrows.addWidget(b, r, c)
        aw = QWidget()
        aw.setLayout(arrows)
        g.addWidget(aw, 5, 0, 1, 3, Qt.AlignmentFlag.AlignHCenter)
        # tiempo
        self.time = spin(-1, 9999, tr('−1 (para siempre)'))
        g.addWidget(QLabel(tr('Tiempo (ticks):')), 6, 0, 1, 2)
        g.addWidget(self.time, 7, 0, 1, 2)
        g.addWidget(all_btn("time", tr('Usar este tiempo en todos los cuadros')), 7, 2)
        # voltear
        self.flip = QComboBox()
        self.flip.setMinimumWidth(60)
        for code, label in FLIP_OPTIONS:
            self.flip.addItem(tr(label), code)
        g.addWidget(QLabel(tr('Voltear:')), 8, 0, 1, 2)
        g.addWidget(self.flip, 9, 0, 1, 2)
        g.addWidget(all_btn("flip", tr('Voltear igual todos los cuadros')), 9, 2)
        # transparencia
        self.trans = QComboBox()
        self.trans.setMinimumWidth(60)
        for code, label in TRANS_OPTIONS:
            self.trans.addItem(tr(label), code)
        g.addWidget(QLabel(tr('Transparencia:')), 10, 0, 1, 2)
        g.addWidget(self.trans, 11, 0, 1, 2)
        g.addWidget(all_btn("trans", tr('Usar esta transparencia en todos los cuadros')), 11, 2)
        self.src = spin(0, 256)
        self.dst = spin(0, 256)
        self.src_lbl = QLabel(tr('Origen:'))
        self.dst_lbl = QLabel(tr('Destino:'))
        g.addWidget(self.src_lbl, 12, 0)
        g.addWidget(self.dst_lbl, 12, 1)
        g.addWidget(self.src, 13, 0)
        g.addWidget(self.dst, 13, 1)
        # repetir
        self.loop = QCheckBox(tr('La repetición empieza en este cuadro'))
        self.loop.setToolTip(tr('Loopstart: al terminar, la animación vuelve a este cuadro'))
        g.addWidget(self.loop, 14, 0, 1, 3)
        # escala y ángulo (IKEMEN)
        self.xs = dspin(-100, 100, 0.05, 4)
        self.ys = dspin(-100, 100, 0.05, 4)
        self.angle = dspin(-3600, 3600, 1, 2)
        g.addWidget(QLabel(tr('Escala X:')), 15, 0)
        g.addWidget(QLabel(tr('Escala Y:')), 15, 1)
        g.addWidget(self.xs, 16, 0)
        g.addWidget(self.ys, 16, 1)
        g.addWidget(all_btn("scale", tr('Usar esta escala y ángulo en todos los cuadros')), 16, 2)
        g.addWidget(QLabel(tr('Ángulo:')), 17, 0)
        g.addWidget(self.angle, 18, 0)
        reset = QToolButton()
        reset.setText("↺")
        reset.setToolTip(tr('Quitar escala y ángulo (como en MUGEN)'))
        reset.clicked.connect(lambda: self.changed.emit("scale_reset", None))
        g.addWidget(reset, 18, 1, Qt.AlignmentFlag.AlignLeft)
        hint = QLabel(tr('Escala y ángulo son de IKEMEN GO (MUGEN los ignora).'))
        hint.setObjectName("CardPath")
        hint.setWordWrap(True)
        g.addWidget(hint, 19, 0, 1, 3)
        lay.addStretch(1)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)

        self.group.valueChanged.connect(lambda v: self._emit("group", v))
        self.number.valueChanged.connect(lambda v: self._emit("number", v))
        self.x.valueChanged.connect(lambda v: self._emit("x", v))
        self.y.valueChanged.connect(lambda v: self._emit("y", v))
        self.time.valueChanged.connect(lambda v: self._emit("time", v))
        self.flip.currentIndexChanged.connect(lambda _i: self._emit("flip", self.flip.currentData()))
        self.trans.currentIndexChanged.connect(self._trans_changed)
        self.src.valueChanged.connect(self._trans_changed)
        self.dst.valueChanged.connect(self._trans_changed)
        self.loop.toggled.connect(lambda c: None if self._block else self.loopToggled.emit(c))
        self.xs.valueChanged.connect(lambda v: self._emit("xscale", v))
        self.ys.valueChanged.connect(lambda v: self._emit("yscale", v))
        self.angle.valueChanged.connect(lambda v: self._emit("angle", v))

    def _emit(self, field, value):
        if not self._block:
            self.changed.emit(field, value)

    def _trans_changed(self, *_a):
        custom = self.trans.currentData() == "AS"
        for w in (self.src, self.dst, self.src_lbl, self.dst_lbl):
            w.setEnabled(custom)
        if not self._block:
            self.changed.emit("trans", trans_text(self.trans.currentData(), self.src.value(), self.dst.value()))

    def show_frame(self, f, is_loop, sprite_exists):
        self._block = True
        self.setEnabled(f is not None)
        if f is not None:
            self.group.setValue(f.group)
            self.number.setValue(f.number)
            self.x.setValue(f.x)
            self.y.setValue(f.y)
            self.time.setValue(f.time)
            i = self.flip.findData((f.flip or "").upper())
            self.flip.setCurrentIndex(max(0, i))
            kind, src, dst = parse_trans(f.trans)
            i = self.trans.findData(kind)
            self.trans.setCurrentIndex(max(0, i))
            self.src.setValue(src)
            self.dst.setValue(dst)
            self.loop.setChecked(is_loop)
            self.xs.setValue(f.xscale if f.xscale is not None else 1.0)
            self.ys.setValue(f.yscale if f.yscale is not None else 1.0)
            self.angle.setValue(f.angle if f.angle is not None else 0.0)
            self.missing.setText("" if sprite_exists or f.group < 0 else tr('⚠ Ese sprite no existe'))
        custom = self.trans.currentData() == "AS"
        for w in (self.src, self.dst, self.src_lbl, self.dst_lbl):
            w.setEnabled(custom)
        self._block = False
