"""Cuadrícula de 256 colores: clic = elegir, doble clic = cambiar color."""
import numpy as np
from PyQt6.QtCore import QRect, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QColorDialog, QWidget

from i18n import tr


class PaletteGrid(QWidget):
    picked = pyqtSignal(int)
    edited = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.palette = None
        self.used = None
        self.selected = -1
        self.setMinimumSize(QSize(16 * 13, 16 * 13))
        self.setMouseTracking(True)
        self.setToolTip(tr('Clic: elegir color · Doble clic: cambiarlo'))

    def set_palette(self, pal, used=None):
        self.palette = pal
        self.used = used
        self.update()

    def cell(self):
        return max(6, min(self.width(), self.height()) // 16)

    def sizeHint(self):
        return QSize(16 * 14, 16 * 14)

    def index_at(self, pos):
        c = self.cell()
        x, y = int(pos.x()) // c, int(pos.y()) // c
        if 0 <= x < 16 and 0 <= y < 16:
            return y * 16 + x
        return -1

    def paintEvent(self, _e):
        p = QPainter(self)
        c = self.cell()
        p.fillRect(self.rect(), self.palette_bg())
        if self.palette is None:
            return
        cols = self.palette.colors
        for i in range(256):
            x, y = (i % 16) * c, (i // 16) * c
            r = QRect(x + 1, y + 1, c - 2, c - 2)
            if i < len(cols):
                col = QColor(int(cols[i][0]), int(cols[i][1]), int(cols[i][2]))
            else:
                col = QColor(0, 0, 0)
            p.fillRect(r, col)
            if i == 0:
                p.setPen(QPen(QColor(255, 80, 80), 1))
                p.drawLine(r.topLeft(), r.bottomRight())
            if self.used is not None and not self.used[i]:
                p.fillRect(r, QColor(40, 40, 40, 150))
        if 0 <= self.selected < 256:
            x, y = (self.selected % 16) * c, (self.selected // 16) * c
            p.setPen(QPen(QColor(255, 255, 255), 2))
            p.drawRect(QRect(x, y, c, c))
            p.setPen(QPen(QColor(0, 0, 0), 1))
            p.drawRect(QRect(x + 2, y + 2, c - 4, c - 4))

    def palette_bg(self):
        return self.palette_color()

    def palette_color(self):
        return QColor(45, 45, 50)

    def mousePressEvent(self, e):
        i = self.index_at(e.position())
        if i >= 0:
            self.selected = i
            self.update()
            self.picked.emit(i)

    def mouseDoubleClickEvent(self, e):
        i = self.index_at(e.position())
        if i < 0 or self.palette is None:
            return
        cur = self.palette.colors[i] if i < len(self.palette.colors) else (0, 0, 0, 255)
        col = QColorDialog.getColor(QColor(int(cur[0]), int(cur[1]), int(cur[2])), self, tr('Color {0}').format(i))
        if col.isValid():
            if i >= len(self.palette.colors):
                extra = np.zeros((i + 1 - len(self.palette.colors), 4), np.uint8)
                extra[:, 3] = 255
                self.palette.colors = np.vstack([self.palette.colors, extra])
            self.palette.colors[i, :3] = (col.red(), col.green(), col.blue())
            self.update()
            self.edited.emit(i)

    def mouseMoveEvent(self, e):
        i = self.index_at(e.position())
        if i >= 0 and self.palette is not None and i < len(self.palette.colors):
            c = self.palette.colors[i]
            self.setToolTip(f"{i}: RGB {int(c[0])}, {int(c[1])}, {int(c[2])}" + (
                "  — " + tr('transparente') if i == 0 else ""))
