"""Alinear los cuadros de una casilla (modo simple): arrastrar cada cuadro a su lugar, con el cuadro anterior
semitransparente de guía, el suelo, el eje y las cajas de golpe."""
from types import SimpleNamespace

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from core.boxes import auto_boxes, hit_box
from i18n import tr
from ui import theme

CLSN2 = QColor(80, 160, 255)
CLSN1 = QColor(255, 70, 70)


def boxes_for(sprite, ax, ay, hit=False, ref=None, two=True):
    """(clsn1, clsn2) automáticas de un sprite con el eje (ax, ay) — igual que las que pone el modo simple.
    ref: pose normal, para que la caja de golpe vaya solo en lo que pega."""
    fake = SimpleNamespace(pixels=sprite.pixels, x=ax, y=ay)
    try:
        c2 = auto_boxes(fake, two=two)
        c1 = hit_box(fake, ref) if hit else []
    except Exception:
        c1, c2 = [], []
    return c1, c2


def draw_boxes(p, c1, c2, ox, oy, z, alpha=255):
    for boxes, col in ((c2, CLSN2), (c1, CLSN1)):
        for x1, y1, x2, y2 in boxes:
            c = QColor(col)
            c.setAlpha(min(alpha, 70))
            p.setBrush(c)
            c2_ = QColor(col)
            c2_.setAlpha(alpha)
            p.setPen(QPen(c2_, 1))
            p.drawRect(QRectF(ox + min(x1, x2) * z, oy + min(y1, y2) * z, abs(x2 - x1) * z, abs(y2 - y1) * z))


class AlignCanvas(QWidget):
    moved = pyqtSignal()

    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg
        self.zoom = 3.0
        self.drag = None
        self.setMinimumSize(QSize(560, 460))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def origin(self):
        return QPointF(self.width() / 2, self.height() - 50)

    def wheelEvent(self, e):
        self.zoom = max(0.5, min(12.0, self.zoom * (1.2 if e.angleDelta().y() > 0 else 1 / 1.2)))
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag = (e.position(), tuple(self.dlg.axis_of(self.dlg.cur)))
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self.drag is None:
            return
        start, (ax, ay) = self.drag
        d = (e.position() - start) / self.zoom
        self.dlg.set_axis(self.dlg.cur, ax - int(round(d.x())), ay - int(round(d.y())))
        self.update()

    def mouseReleaseEvent(self, _e):
        if self.drag is not None:
            self.drag = None
            self.unsetCursor()
            self.moved.emit()

    def keyPressEvent(self, e):
        step = 10 if e.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
        d = {Qt.Key.Key_Left: (step, 0), Qt.Key.Key_Right: (-step, 0), Qt.Key.Key_Up: (0, step),
             Qt.Key.Key_Down: (0, -step)}.get(e.key())
        if d:
            ax, ay = self.dlg.axis_of(self.dlg.cur)
            self.dlg.set_axis(self.dlg.cur, ax + d[0], ay + d[1])
            self.update()
            self.moved.emit()
        elif e.key() in (Qt.Key.Key_PageDown, Qt.Key.Key_Period):
            self.dlg.go(1)
        elif e.key() in (Qt.Key.Key_PageUp, Qt.Key.Key_Comma):
            self.dlg.go(-1)
        else:
            super().keyPressEvent(e)

    def draw_frame(self, p, i, opacity=1.0, boxes=False):
        dlg = self.dlg
        key = dlg.keys[i]
        s = dlg.sm.sprite(*key)
        pm = dlg.sm.pixmap(*key) if s is not None else None
        if pm is None:
            return
        o = self.origin()
        z = self.zoom
        ax, ay = dlg.axis_of(i)
        p.setOpacity(opacity)
        p.drawPixmap(QRectF(o.x() - ax * z, o.y() - ay * z, pm.width() * z, pm.height() * z), pm, QRectF(pm.rect()))
        p.setOpacity(1.0)
        if boxes:
            hits = dlg.hit_index if isinstance(dlg.hit_index, (set, list, tuple)) else {dlg.hit_index}
            from core import simple_gen as sg
            c1, c2 = boxes_for(s, ax, ay, hit=(i in hits), ref=dlg.ref, two=sg.HURT["two"])
            mh = sg.HURT["by_key"].get((int(key[0]), int(key[1])))
            if mh is not None:
                c2 = list(mh)
            man = dlg.manual
            if man is not None and (i in man or getattr(man, "strict", False)):
                c1 = list(man.get(i, []))
            draw_boxes(p, c1, c2, o.x(), o.y(), z)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.CANVAS))
        dlg = self.dlg
        if not dlg.keys:
            p.end()
            return
        o = self.origin()
        # suelo y eje
        p.setPen(QPen(QColor(255, 107, 53, 170), 1))
        p.drawLine(0, int(o.y()), self.width(), int(o.y()))
        p.setPen(QPen(QColor(255, 255, 255, 60), 1, Qt.PenStyle.DashLine))
        p.drawLine(int(o.x()), 0, int(o.x()), self.height())
        playing = dlg.playing
        i = dlg.play_index() if playing else dlg.cur
        if not playing:
            ref = dlg.reference_index()
            if ref is not None:
                self.draw_frame(p, ref, 0.35)
        self.draw_frame(p, i, 1.0, boxes=dlg.show_boxes.isChecked())
        p.setPen(QColor(theme.ACCENT2))
        p.drawLine(int(o.x() - 6), int(o.y()), int(o.x() + 6), int(o.y()))
        p.drawLine(int(o.x()), int(o.y() - 6), int(o.x()), int(o.y() + 6))
        p.setPen(QColor(theme.MUTED))
        ax, ay = dlg.axis_of(i)
        p.drawText(10, 20, tr('Cuadro {0}/{1} · eje {2}, {3}').format(i + 1, len(dlg.keys), ax, ay))
        p.end()


class AlignDialog(QDialog):
    """Ajusta el eje (punto de apoyo) de los sprites de una casilla. Al aceptar: {clave: (x, y)} cambiados."""

    def __init__(self, sm, title, keys, hit_index=None, mode="ground", manual=None, ref=None):
        super().__init__(sm.main)
        self.sm = sm
        self.keys = [tuple(k) for k in keys]
        self.hit_index = hit_index
        self.manual = manual         # cajas de daño dibujadas a mano (relativas al eje)
        self.ref = ref
        self.axes = {}
        for k in self.keys:
            s = sm.sprite(*k)
            if s is not None:
                self.axes[k] = [s.x, s.y]
        self.orig = {k: tuple(v) for k, v in self.axes.items()}
        self.cur = 0
        self.playing = False
        self.tick = 0
        self.setWindowTitle(tr('✋ Alinear y ver cajas — {0}').format(title))
        self.resize(1000, 700)
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        self.canvas = AlignCanvas(self)
        left.addWidget(self.canvas, 1)
        self.strip = QListWidget()
        self.strip.setViewMode(QListView.ViewMode.IconMode)
        self.strip.setFlow(QListView.Flow.LeftToRight)
        self.strip.setWrapping(False)
        self.strip.setIconSize(QSize(56, 56))
        self.strip.setFixedHeight(96)
        self.strip.setMovement(QListView.Movement.Static)
        for i, k in enumerate(self.keys):
            it = QListWidgetItem(str(i + 1))
            pm = sm.pixmap(*k)
            if pm is not None:
                it.setIcon(QIcon(pm.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio)))
            self.strip.addItem(it)
        self.strip.currentRowChanged.connect(self.on_row)
        left.addWidget(self.strip)
        hint = QLabel(tr('🖱 Arrastra el cuadro para moverlo · flechas: 1 px (Mayús: 10) · rueda: zoom · '
                         'Re Pág / Av Pág: cuadro anterior / siguiente'))
        hint.setObjectName("CardPath")
        hint.setWordWrap(True)
        left.addWidget(hint)
        lay.addLayout(left, 1)

        side = QVBoxLayout()
        g = QGridLayout()
        for i, (txt, d) in enumerate((("↑", (0, 1)), ("←", (1, 0)), ("→", (-1, 0)), ("↓", (0, -1)))):
            b = QPushButton(txt)
            b.setFixedWidth(44)
            b.clicked.connect(lambda _c, d=d: self.nudge(*d))
            g.addWidget(b, *((0, 1), (1, 0), (1, 2), (2, 1))[i])
        side.addLayout(g)
        side.addWidget(QLabel(tr('Guía:')))
        self.ref = QComboBox()
        self.ref.addItem(tr('El cuadro anterior'), "prev")
        self.ref.addItem(tr('El primer cuadro'), "first")
        self.ref.addItem(tr('Ninguna'), "none")
        self.ref.currentIndexChanged.connect(lambda _i: self.canvas.update())
        side.addWidget(self.ref)
        self.show_boxes = QCheckBox(tr('Ver cajas de golpe'))
        self.show_boxes.setChecked(True)
        self.show_boxes.setToolTip(tr('Azul: donde le pueden pegar · rojo: donde pega'))
        self.show_boxes.toggled.connect(lambda _c: self.canvas.update())
        side.addWidget(self.show_boxes)
        legend = QLabel(tr('<span style="color:#50a0ff">■</span> donde le pueden pegar<br>'
                           '<span style="color:#ff4646">■</span> donde pega'))
        side.addWidget(legend)
        side.addSpacing(10)
        side.addWidget(QLabel(tr('Cómo alinear:')))
        from core.autoalign import MODE_TIPS, MODES
        self.mode = QComboBox()
        for i_, (k, t) in enumerate(MODES):
            self.mode.addItem(tr(t), k)
            self.mode.setItemData(i_, tr(MODE_TIPS[k]), Qt.ItemDataRole.ToolTipRole)
        self.mode.setCurrentIndex(max(0, self.mode.findData(mode)))
        side.addWidget(self.mode)
        b = QPushButton(tr('🎯 Alinear con la de parado'))
        b.setObjectName("primary")
        b.setToolTip(tr('Reconoce el cuerpo y los pies de cada cuadro y los pone donde están en la animación de '
                        'parado, sin que la animación brinque. Escoge arriba si es en el suelo, en el aire o '
                        'acostado.'))
        b.clicked.connect(self.auto_advanced)
        side.addWidget(b)
        for txt, tip, fn in (
                (tr('🦶 Pies al suelo (todos)'), tr('Pone los pies de cada cuadro sobre el suelo y centrados. No lo '
                                                     'uses en saltos: los subiría al suelo.'), self.auto_feet),
                (tr('⇔ Igual que el primero'), tr('Copia el eje del primer cuadro a todos (sirve si las imágenes '
                                                  'tienen el mismo tamaño).'), self.same_as_first),
                (tr('↺ Deshacer cambios'), tr('Vuelve a como estaba al abrir esta ventana.'), self.reset)):
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            side.addWidget(b)
        side.addSpacing(10)
        self.play_btn = QPushButton(tr('▶ Ver animado'))
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self.on_play)
        side.addWidget(self.play_btn)
        side.addStretch(1)
        ok = QPushButton(tr('✔ Listo'))
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        cancel = QPushButton(tr('Cancelar'))
        cancel.clicked.connect(self.reject)
        side.addWidget(ok)
        side.addWidget(cancel)
        sw = QWidget()
        sw.setLayout(side)
        sw.setFixedWidth(230)
        lay.addWidget(sw)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.on_tick)
        self.times = [5] * len(self.keys)
        if self.keys:
            self.strip.setCurrentRow(0)
        # zoom para que quepa el más alto
        tall = max([v[1] for v in self.axes.values()] + [40])
        self.canvas.zoom = max(0.5, min(4.0, 420 / tall))
        self.canvas.setFocus()

    # ---- datos
    def axis_of(self, i):
        return self.axes.get(self.keys[i], [0, 0])

    def set_axis(self, i, x, y):
        if self.keys[i] in self.axes:
            self.axes[self.keys[i]] = [int(x), int(y)]

    def reference_index(self):
        mode = self.ref.currentData()
        if mode == "prev" and self.cur > 0:
            return self.cur - 1
        if mode == "prev" and self.cur == 0 and len(self.keys) > 1:
            return len(self.keys) - 1
        if mode == "first" and self.cur != 0:
            return 0
        return None

    def changes(self):
        return {k: tuple(v) for k, v in self.axes.items() if tuple(v) != self.orig[k]}

    # ---- acciones
    def on_row(self, r):
        if r >= 0:
            self.cur = r
            self.canvas.update()
            self.canvas.setFocus()

    def go(self, d):
        if self.keys:
            self.strip.setCurrentRow((self.cur + d) % len(self.keys))

    def nudge(self, dx, dy):
        ax, ay = self.axis_of(self.cur)
        self.set_axis(self.cur, ax + dx, ay + dy)
        self.canvas.update()

    def auto_feet(self):
        for k in self.keys:
            s = self.sm.sprite(*k)
            if s is None:
                continue
            pix = s.pixels()
            m = pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0
            if not m.any():
                continue
            rows = np.where(m.any(axis=1))[0]
            bottom = int(rows[-1]) + 1
            band = m[max(int(rows[0]), bottom - max(2, (bottom - int(rows[0])) // 5)):bottom]
            xs = np.where(band)[1]
            self.axes[k] = [int(np.median(xs)) if len(xs) else pix.shape[1] // 2, bottom]
        self.canvas.update()

    def auto_advanced(self):
        """Alinea con el motor avanzado, tomando de guía el primer cuadro de parado."""
        from core.autoalign import Aligner
        if not self.keys:
            return
        al = Aligner(lambda k: self.sm.sprite(*k))
        ref = self.sm.reference_frame()
        if ref is None or ref in set(self.keys):
            # sin parado (o esta es la de parado): el primer cuadro se queda y los demás se alinean con él
            first = self.keys[0]
            al.done[first] = tuple(self.axes.get(first, (0, 0)))
            al.set_reference(first)
        else:
            al.set_reference(ref)
        for k, v in al.align(self.keys, self.mode.currentData()).items():
            if k in self.axes:
                self.axes[k] = list(v)
        self.canvas.update()

    def same_as_first(self):
        if not self.keys:
            return
        first = list(self.axis_of(0))
        for k in self.keys[1:]:
            if k in self.axes:
                self.axes[k] = list(first)
        self.canvas.update()

    def reset(self):
        self.axes = {k: list(v) for k, v in self.orig.items()}
        self.canvas.update()

    def on_play(self, on):
        self.playing = on
        self.play_btn.setText(tr('⏸ Parar') if on else tr('▶ Ver animado'))
        (self.timer.start if on else self.timer.stop)()
        self.canvas.update()

    def on_tick(self):
        self.tick += 1
        self.canvas.update()

    def play_index(self):
        total = sum(self.times) or 1
        t = self.tick % total
        for i, d in enumerate(self.times):
            if t < d:
                return i
            t -= d
        return 0
