"""Editor de píxeles: lápiz, borrador, relleno, cuentagotas, línea, rectángulo, selección y más."""
from collections import deque

import numpy as np
from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QColorDialog, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from i18n import tr
from ui.common import checker_brush
from ui.palette_widget import PaletteGrid

TOOLS = [("pencil", "✏", 'Lápiz (B)', "B"), ("eraser", "🧽", 'Borrador (E)', "E"),
         ("fill", "🪣", 'Relleno (G)', "G"), ("picker", "💧", 'Cuentagotas (I)', "I"),
         ("line", "╱", 'Línea (L)', "L"), ("rect", "▭", 'Rectángulo (R)', "R"),
         ("frect", "▬", 'Rectángulo lleno (Shift+R)', "Shift+R"), ("select", "⬚", 'Seleccionar y mover (S)', "S"),
         ("axis", "✛", 'Poner el eje (A)', "A")]


def line_points(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pts


class Canvas(QWidget):
    changed = pyqtSignal()
    colorPicked = pyqtSignal(object)
    hover = pyqtSignal(int, int)

    def __init__(self, editor):
        super().__init__()
        self.ed = editor
        self.zoom = 8
        self.grid = True
        self.setMouseTracking(True)
        self._down = None
        self._last = None
        self._preview = None
        self._sel_drag = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def sizeHint(self):
        h, w = self.ed.pix.shape[:2]
        return QSize(w * self.zoom + 2, h * self.zoom + 2)

    def resize_to_fit(self):
        self.setFixedSize(self.sizeHint())
        self.update()

    def to_px(self, pos):
        return int(pos.x()) // self.zoom, int(pos.y()) // self.zoom

    def inside(self, x, y):
        h, w = self.ed.pix.shape[:2]
        return 0 <= x < w and 0 <= y < h

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), checker_brush(max(4, self.zoom)))
        img = self.ed.qimage(self._preview)
        z = self.zoom
        p.drawImage(QRect(0, 0, img.width() * z, img.height() * z), img)
        h, w = self.ed.pix.shape[:2]
        if self.grid and z >= 6:
            p.setPen(QPen(QColor(255, 255, 255, 28), 1))
            for x in range(w + 1):
                p.drawLine(x * z, 0, x * z, h * z)
            for y in range(h + 1):
                p.drawLine(0, y * z, w * z, y * z)
        # eje
        ax, ay = self.ed.axis
        p.setPen(QPen(QColor(255, 220, 0, 200), 1))
        p.drawLine(int(ax * z), 0, int(ax * z), h * z)
        p.drawLine(0, int(ay * z), w * z, int(ay * z))
        sel = self.ed.selection
        if sel is not None:
            x0, y0, x1, y1 = sel
            pen = QPen(QColor(255, 107, 53), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawRect(QRect(x0 * z, y0 * z, (x1 - x0) * z, (y1 - y0) * z))

    # ---- ratón
    def mousePressEvent(self, e):
        x, y = self.to_px(e.position())
        tool = self.ed.tool
        right = e.button() == Qt.MouseButton.RightButton
        if tool == "picker" or (e.modifiers() & Qt.KeyboardModifier.AltModifier):
            if self.inside(x, y):
                self.colorPicked.emit(self.ed.pix[y, x].copy() if self.ed.pix.ndim == 3 else int(self.ed.pix[y, x]))
            return
        if tool == "axis":
            self.ed.set_axis(x, y)
            self.update()
            return
        if tool == "select":
            sel = self.ed.selection
            if sel and sel[0] <= x < sel[2] and sel[1] <= y < sel[3]:
                self.ed.begin_move()
                self._sel_drag = (x, y)
            else:
                self.ed.commit_move()
                self.ed.selection = None
                self._down = (x, y)
            self.update()
            return
        self.ed.snapshot()
        self._down = (x, y)
        self._last = (x, y)
        value = self.ed.erase_value() if (tool == "eraser" or right) else self.ed.color
        if tool in ("pencil", "eraser"):
            self.ed.plot([(x, y)], value)
        elif tool == "fill":
            self.ed.flood(x, y, value)
        self._value = value
        self.update()
        self.changed.emit()

    def mouseMoveEvent(self, e):
        x, y = self.to_px(e.position())
        self.hover.emit(x, y)
        tool = self.ed.tool
        if self._sel_drag is not None:
            dx, dy = x - self._sel_drag[0], y - self._sel_drag[1]
            if dx or dy:
                self.ed.move_selection(dx, dy)
                self._sel_drag = (x, y)
                self.update()
            return
        if self._down is None:
            return
        if tool == "select":
            x0, y0 = self._down
            self.ed.selection = (min(x0, x), min(y0, y), max(x0, x) + 1, max(y0, y) + 1)
            self.update()
            return
        if tool in ("pencil", "eraser") and self._last is not None:
            self.ed.plot(line_points(self._last[0], self._last[1], x, y), self._value)
            self._last = (x, y)
            self.update()
        elif tool in ("line", "rect", "frect"):
            self._preview = (tool, self._down, (x, y), self._value)
            self.update()

    def mouseReleaseEvent(self, e):
        x, y = self.to_px(e.position())
        if self._sel_drag is not None:
            self._sel_drag = None
            return
        if self._down is not None and self.ed.tool in ("line", "rect", "frect"):
            self._preview = None
            self.ed.shape(self.ed.tool, self._down, (x, y), self._value)
            self.changed.emit()
        self._down = None
        self._last = None
        self.update()

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.ed.set_zoom(self.zoom + (1 if e.angleDelta().y() > 0 else -1))
            e.accept()
        else:
            super().wheelEvent(e)


class PixelEditor(QDialog):
    def __init__(self, parent, pix, palette, axis):
        super().__init__(parent)
        self.setWindowTitle(tr('Editor de píxeles'))
        self.resize(1200, 820)
        self.pix = pix.copy()
        self.palette = palette
        self.axis = list(axis)
        self.true_color = self.pix.ndim == 3
        self.color = np.array([255, 255, 255, 255], np.uint8) if self.true_color else 1
        self.tool = "pencil"
        self.selection = None
        self._float = None   # (pixeles, x, y) de lo que se está moviendo
        self.history, self.future = [], []
        lay = QHBoxLayout(self)
        # herramientas
        tools = QVBoxLayout()
        self.tool_grp = QButtonGroup(self)
        for key, icon, tip, sc in TOOLS:
            b = QToolButton()
            b.setText(icon)
            b.setToolTip(tr(tip))
            b.setCheckable(True)
            b.setFixedSize(42, 38)
            b.setChecked(key == self.tool)
            b.clicked.connect(lambda _c, key=key: self.set_tool(key))
            self.tool_grp.addButton(b)
            tools.addWidget(b)
            s = QShortcut(QKeySequence(sc), self)
            s.activated.connect(lambda key=key, b=b: (b.setChecked(True), self.set_tool(key)))
        tools.addStretch(1)
        lay.addLayout(tools)
        # lienzo
        center = QVBoxLayout()
        self.canvas = Canvas(self)
        self.canvas.colorPicked.connect(self.pick)
        self.canvas.hover.connect(lambda x, y: self.pos_lbl.setText(f"x {x - self.axis[0]}, y {y - self.axis[1]}   ({x}, {y})"))
        self.canvas.changed.connect(self.update_used)
        sc = QScrollArea()
        sc.setWidget(self.canvas)
        sc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(sc, 1)
        bar = QHBoxLayout()
        self.pos_lbl = QLabel()
        bar.addWidget(self.pos_lbl)
        bar.addStretch(1)
        self.grid_chk = QCheckBox(tr('Cuadrícula'))
        self.grid_chk.setChecked(True)
        self.grid_chk.toggled.connect(lambda c: (setattr(self.canvas, "grid", c), self.canvas.update()))
        bar.addWidget(self.grid_chk)
        self.zoom = QSpinBox()
        self.zoom.setRange(1, 40)
        self.zoom.setSuffix("×")
        self.zoom.setValue(self.canvas.zoom)
        self.zoom.valueChanged.connect(self.set_zoom)
        bar.addWidget(QLabel(tr('Zoom:')))
        bar.addWidget(self.zoom)
        center.addLayout(bar)
        lay.addLayout(center, 1)
        # derecha
        right = QVBoxLayout()
        self.swatch = QPushButton()
        self.swatch.setFixedHeight(34)
        self.swatch.clicked.connect(self.choose_rgba)
        right.addWidget(self.swatch)
        self.grid = PaletteGrid()
        self.grid.picked.connect(self.pick)
        if not self.true_color:
            right.addWidget(self.grid, 1)
            self.used_only = QCheckBox(tr('Oscurecer colores sin usar'))
            self.used_only.toggled.connect(lambda _c: self.update_used())
            right.addWidget(self.used_only)
        else:
            right.addStretch(1)
        acts = [(tr('↶ Deshacer'), self.undo, "Ctrl+Z"), (tr('↷ Rehacer'), self.redo, "Ctrl+Shift+Z"),
                (tr('⇋ Voltear horizontal'), lambda: self.transform("h"), None),
                (tr('⇵ Voltear vertical'), lambda: self.transform("v"), None),
                (tr('⟳ Girar 90°'), lambda: self.transform("r"), None),
                (tr('🔁 Cambiar un color por otro…'), self.replace_color, None),
                (tr('📐 Tamaño del lienzo…'), self.canvas_size, None),
                (tr('✂ Recortar a lo usado'), self.crop, None),
                (tr('🧹 Borrar selección (Supr)'), self.delete_selection, "Del")]
        for txt, fn, key in acts:
            b = QPushButton(txt)
            b.clicked.connect(fn)
            right.addWidget(b)
            if key:
                QShortcut(QKeySequence(key), self).activated.connect(fn)
        QShortcut(QKeySequence("Ctrl+C"), self).activated.connect(self.copy_sel)
        QShortcut(QKeySequence("Ctrl+V"), self).activated.connect(self.paste)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self.drop_selection)
        hint = QLabel(tr('Clic derecho = borrar · Alt+clic = cuentagotas · Ctrl+rueda = zoom · '
                         'Ctrl+C / Ctrl+V copian y pegan la selección'))
        hint.setWordWrap(True)
        hint.setObjectName("CardPath")
        right.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.finish)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        rw = QWidget()
        rw.setLayout(right)
        rw.setFixedWidth(300)
        lay.addWidget(rw)
        self._clip = None
        h, w = self.pix.shape[:2]
        self.set_zoom(max(2, min(16, 600 // max(1, h), 800 // max(1, w))))
        self.update_used()
        self.update_swatch()

    # ---- pintar
    def qimage(self, preview=None):
        pix = self.pix
        if preview is not None or self._float is not None:
            pix = pix.copy()
            if self._float is not None:
                self._paste_into(pix, *self._float)
            if preview is not None:
                tool, a, b, v = preview
                self._shape_into(pix, tool, a, b, v)
        h, w = pix.shape[:2]
        if pix.ndim == 3:
            return QImage(np.ascontiguousarray(pix).tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        img = QImage(np.ascontiguousarray(pix).tobytes(), w, h, w, QImage.Format.Format_Indexed8).copy()
        img.setColorTable(self.palette.table())
        return img

    def erase_value(self):
        return np.zeros(4, np.uint8) if self.true_color else 0

    def plot(self, pts, v):
        h, w = self.pix.shape[:2]
        for x, y in pts:
            if 0 <= x < w and 0 <= y < h:
                self.pix[y, x] = v

    def flood(self, x, y, v):
        h, w = self.pix.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            return
        target = self.pix[y, x].copy()
        if np.array_equal(target, v):
            return
        if self.pix.ndim == 2:
            mask = self.pix == target
        else:
            mask = np.all(self.pix == target, axis=2)
        seen = np.zeros((h, w), bool)
        q = deque([(x, y)])
        seen[y, x] = True
        while q:
            cx, cy = q.popleft()
            self.pix[cy, cx] = v
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and mask[ny, nx]:
                    seen[ny, nx] = True
                    q.append((nx, ny))

    def _shape_into(self, pix, tool, a, b, v):
        h, w = pix.shape[:2]
        if tool == "line":
            for x, y in line_points(a[0], a[1], b[0], b[1]):
                if 0 <= x < w and 0 <= y < h:
                    pix[y, x] = v
            return
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w - 1, x1), min(h - 1, y1)
        if x0 > x1 or y0 > y1:
            return
        if tool == "frect":
            pix[y0:y1 + 1, x0:x1 + 1] = v
        else:
            pix[y0, x0:x1 + 1] = v
            pix[y1, x0:x1 + 1] = v
            pix[y0:y1 + 1, x0] = v
            pix[y0:y1 + 1, x1] = v

    def shape(self, tool, a, b, v):
        self._shape_into(self.pix, tool, a, b, v)

    # ---- selección
    def begin_move(self):
        if self._float is None and self.selection:
            self.snapshot()
            x0, y0, x1, y1 = self.clip_sel()
            part = self.pix[y0:y1, x0:x1].copy()
            self.pix[y0:y1, x0:x1] = self.erase_value()
            self._float = (part, x0, y0)

    def clip_sel(self):
        h, w = self.pix.shape[:2]
        x0, y0, x1, y1 = self.selection
        return max(0, x0), max(0, y0), min(w, x1), min(h, y1)

    def move_selection(self, dx, dy):
        if self._float is None:
            return
        part, x, y = self._float
        self._float = (part, x + dx, y + dy)
        x0, y0, x1, y1 = self.selection
        self.selection = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)

    def _paste_into(self, pix, part, x, y):
        h, w = pix.shape[:2]
        ph, pw = part.shape[:2]
        for yy in range(ph):
            ty = y + yy
            if not 0 <= ty < h:
                continue
            a, b = max(0, x), min(w, x + pw)
            if a >= b:
                continue
            src = part[yy, a - x:b - x]
            opaque = (src[:, 3] > 0) if src.ndim == 2 else (src != 0)
            row = pix[ty, a:b]
            row[opaque] = src[opaque]

    def commit_move(self):
        if self._float is not None:
            self._paste_into(self.pix, *self._float)
            self._float = None
            self.canvas.changed.emit()

    def drop_selection(self):
        self.commit_move()
        self.selection = None
        self.canvas.update()

    def delete_selection(self):
        if self._float is not None:
            self._float = None
        elif self.selection:
            self.snapshot()
            x0, y0, x1, y1 = self.clip_sel()
            self.pix[y0:y1, x0:x1] = self.erase_value()
        self.selection = None
        self.canvas.update()

    def copy_sel(self):
        if self.selection:
            if self._float is not None:
                self._clip = self._float[0].copy()
            else:
                x0, y0, x1, y1 = self.clip_sel()
                self._clip = self.pix[y0:y1, x0:x1].copy()

    def paste(self):
        if self._clip is None or self._clip.ndim != self.pix.ndim:
            return
        self.commit_move()
        self.snapshot()
        ph, pw = self._clip.shape[:2]
        self._float = (self._clip.copy(), 0, 0)
        self.selection = (0, 0, pw, ph)
        self.set_tool("select")
        for b in self.tool_grp.buttons():
            b.setChecked(b.toolTip() == tr('Seleccionar y mover (S)'))
        self.canvas.update()

    # ---- herramientas
    def set_tool(self, t):
        if t != "select":
            self.commit_move()
        self.tool = t
        self.canvas.setCursor(Qt.CursorShape.CrossCursor)

    def set_zoom(self, z):
        z = max(1, min(40, int(z)))
        self.canvas.zoom = z
        if self.zoom.value() != z:
            self.zoom.setValue(z)
        self.canvas.resize_to_fit()

    def set_axis(self, x, y):
        self.axis = [x, y]

    def pick(self, v):
        if self.true_color:
            if isinstance(v, int):
                c = self.palette.colors[v] if v < len(self.palette.colors) else (0, 0, 0, 255)
                self.color = np.array([c[0], c[1], c[2], 255], np.uint8)
            else:
                self.color = np.array(v, np.uint8)
        else:
            self.color = int(v)
            self.grid.selected = self.color
            self.grid.update()
        self.update_swatch()

    def update_swatch(self):
        if self.true_color:
            r, g, b, a = (int(x) for x in self.color)
            txt = f"RGBA {r},{g},{b},{a}"
        else:
            c = self.palette.colors[self.color] if self.color < len(self.palette.colors) else (0, 0, 0, 255)
            r, g, b = int(c[0]), int(c[1]), int(c[2])
            txt = tr('Color {0}').format(self.color) + (" — " + tr('transparente') if self.color == 0 else "")
        fg = "#111" if (r * 299 + g * 587 + b * 114) / 1000 > 140 else "#fff"
        self.swatch.setText(txt)
        self.swatch.setStyleSheet(f"background: rgb({r},{g},{b}); color: {fg}; font-weight: bold;")

    def choose_rgba(self):
        if not self.true_color:
            return
        r, g, b, a = (int(x) for x in self.color)
        col = QColorDialog.getColor(QColor(r, g, b, a), self, tr('Color'), QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if col.isValid():
            self.color = np.array([col.red(), col.green(), col.blue(), col.alpha()], np.uint8)
            self.update_swatch()

    def update_used(self):
        if self.true_color:
            return
        used = None
        if getattr(self, "used_only", None) is not None and self.used_only.isChecked():
            used = np.zeros(256, bool)
            used[np.unique(self.pix)] = True
        self.grid.set_palette(self.palette, used)
        self.grid.selected = self.color
        self.canvas.update()

    # ---- historial
    def snapshot(self):
        self.history.append((self.pix.copy(), list(self.axis)))
        if len(self.history) > 80:
            self.history.pop(0)
        self.future.clear()

    def undo(self):
        self.commit_move()
        if self.history:
            self.future.append((self.pix.copy(), list(self.axis)))
            self.pix, self.axis = self.history.pop()
            self.canvas.resize_to_fit()
            self.update_used()

    def redo(self):
        if self.future:
            self.history.append((self.pix.copy(), list(self.axis)))
            self.pix, self.axis = self.future.pop()
            self.canvas.resize_to_fit()
            self.update_used()

    # ---- transformaciones
    def transform(self, kind):
        self.commit_move()
        self.snapshot()
        h, w = self.pix.shape[:2]
        if kind == "h":
            self.pix = np.ascontiguousarray(self.pix[:, ::-1])
            self.axis[0] = w - self.axis[0]
        elif kind == "v":
            self.pix = np.ascontiguousarray(self.pix[::-1])
            self.axis[1] = h - self.axis[1]
        else:
            self.pix = np.ascontiguousarray(np.rot90(self.pix, -1))
            ax, ay = self.axis
            self.axis = [h - ay, ax]
        self.canvas.resize_to_fit()

    def replace_color(self):
        if self.true_color:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(tr('Cambiar un color por otro'))
        f = QFormLayout(dlg)
        a = QSpinBox()
        a.setRange(0, 255)
        a.setValue(self.color)
        b = QSpinBox()
        b.setRange(0, 255)
        sel_only = QCheckBox(tr('Solo dentro de la selección'))
        sel_only.setEnabled(self.selection is not None)
        f.addRow(tr('Color (índice):'), a)
        f.addRow(tr('Cambiar por:'), b)
        f.addRow(sel_only)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if not dlg.exec():
            return
        self.commit_move()
        self.snapshot()
        if sel_only.isChecked() and self.selection:
            x0, y0, x1, y1 = self.clip_sel()
            part = self.pix[y0:y1, x0:x1]
            part[part == a.value()] = b.value()
        else:
            self.pix[self.pix == a.value()] = b.value()
        self.update_used()

    def canvas_size(self):
        h, w = self.pix.shape[:2]
        dlg = QDialog(self)
        dlg.setWindowTitle(tr('Tamaño del lienzo'))
        f = QFormLayout(dlg)
        boxes = {}
        for k, lab in (("left", tr('Agregar a la izquierda:')), ("right", tr('Agregar a la derecha:')),
                       ("top", tr('Agregar arriba:')), ("bottom", tr('Agregar abajo:'))):
            s = QSpinBox()
            s.setRange(-2000, 2000)
            boxes[k] = s
            f.addRow(lab, s)
        f.addRow(QLabel(tr('Negativo = quitar. El dibujo y el eje no se mueven de su sitio.')))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if not dlg.exec():
            return
        l, r, t, b = (boxes[k].value() for k in ("left", "right", "top", "bottom"))
        nw, nh = w + l + r, h + t + b
        if nw < 1 or nh < 1:
            return
        self.commit_move()
        self.snapshot()
        shape = (nh, nw, 4) if self.true_color else (nh, nw)
        out = np.zeros(shape, np.uint8)
        sx0, sy0 = max(0, -l), max(0, -t)
        dx0, dy0 = max(0, l), max(0, t)
        cw, ch = min(w - sx0, nw - dx0), min(h - sy0, nh - dy0)
        if cw > 0 and ch > 0:
            out[dy0:dy0 + ch, dx0:dx0 + cw] = self.pix[sy0:sy0 + ch, sx0:sx0 + cw]
        self.pix = out
        self.axis = [self.axis[0] + l, self.axis[1] + t]
        self.canvas.resize_to_fit()

    def crop(self):
        self.commit_move()
        mask = self.pix[:, :, 3] > 0 if self.true_color else self.pix != 0
        if not mask.any():
            return
        ys, xs = np.where(mask)
        self.snapshot()
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        self.pix = np.ascontiguousarray(self.pix[y0:y1, x0:x1])
        self.axis = [self.axis[0] - int(x0), self.axis[1] - int(y0)]
        self.canvas.resize_to_fit()

    def finish(self):
        self.commit_move()
        self.accept()

    def result_data(self):
        return self.pix, tuple(self.axis)


def pixmap_of(arr, pal):
    h, w = arr.shape[:2]
    img = QImage(arr.tobytes(), w, h, w, QImage.Format.Format_Indexed8).copy()
    img.setColorTable(pal.table())
    return QPixmap.fromImage(img)
