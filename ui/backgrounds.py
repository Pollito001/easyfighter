"""
Fondos para las vistas de Sprites, Animaciones y Simulador.
Se dibujan aquí mismo (no hacen falta imágenes), con el suelo en el 85 % de la altura para que el
personaje quede parado sobre él. También se puede usar una imagen propia.
"""
import math
import random
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient

from i18n import tr
from ui import theme

FLOOR = 0.85  # el suelo (y = 0 del personaje) está a esta altura del fondo

BACKGROUNDS = [
    ("checker", 'Cuadritos (transparente)'),
    ("dojo", 'Dojo'),
    ("sunset", 'Atardecer'),
    ("city", 'Ciudad de noche'),
    ("forest", 'Bosque'),
    ("beach", 'Playa'),
    ("temple", 'Templo'),
    ("snow", 'Montaña nevada'),
    ("training", 'Entrenamiento (cuadrícula)'),
    ("green", 'Pantalla verde'),
    ("black", 'Negro'),
    ("gray", 'Gris'),
]


def label(key):
    for k, lab in BACKGROUNDS:
        if k == key:
            return tr(lab)
    if key.startswith("file:"):
        return Path(key[5:]).name
    return key


# ---------------------------------------------------------------- utilidades de dibujo
def vgrad(p, rect, stops):
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    for pos, col in stops:
        g.setColorAt(pos, QColor(col))
    p.fillRect(rect, QBrush(g))


def poly(p, pts, color):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))


def ridge(rng, w, base, amp, step, jag=0.5):
    """Línea de montañas: lista de puntos de izquierda a derecha."""
    pts, x = [], -step
    y = base - rng.uniform(0, amp)
    while x <= w + step:
        pts.append((x, y))
        x += step * rng.uniform(0.6, 1.4)
        y = max(base - amp, min(base, y + rng.uniform(-amp * jag, amp * jag)))
    return pts


# ---------------------------------------------------------------- fondos
def _dojo(p, w, h, fy, rng):
    vgrad(p, QRectF(0, 0, w, fy), [(0, "#3b2614"), (0.6, "#5a3a1e"), (1, "#6e4824")])
    # ventanas de papel
    win_w, win_h = w * 0.16, fy * 0.42
    for i in range(5):
        x = w * (0.06 + i * 0.19)
        y = fy * 0.18
        p.fillRect(QRectF(x - 6, y - 6, win_w + 12, win_h + 12), QColor("#2a1a0c"))
        g = QLinearGradient(QPointF(x, y), QPointF(x, y + win_h))
        g.setColorAt(0, QColor("#f6e7c8"))
        g.setColorAt(1, QColor("#e2c99a"))
        p.fillRect(QRectF(x, y, win_w, win_h), QBrush(g))
        p.setPen(QPen(QColor("#3a2412"), max(1.5, w / 600)))
        for k in range(1, 4):
            p.drawLine(QPointF(x + win_w * k / 4, y), QPointF(x + win_w * k / 4, y + win_h))
        for k in range(1, 5):
            p.drawLine(QPointF(x, y + win_h * k / 5), QPointF(x + win_w, y + win_h * k / 5))
    # vigas
    for i in range(6):
        x = w * (0.025 + i * 0.19)
        p.fillRect(QRectF(x, 0, w * 0.022, fy), QColor("#2b1a0b"))
    p.fillRect(QRectF(0, fy * 0.08, w, fy * 0.04), QColor("#2b1a0b"))
    p.fillRect(QRectF(0, fy * 0.86, w, fy * 0.14), QColor("#3a2412"))
    # pergamino colgado
    p.setPen(Qt.PenStyle.NoPen)
    p.fillRect(QRectF(w * 0.475, fy * 0.62, w * 0.05, fy * 0.2), QColor("#efe2c2"))
    p.fillRect(QRectF(w * 0.47, fy * 0.61, w * 0.06, fy * 0.015), QColor("#2b1a0b"))
    p.fillRect(QRectF(w * 0.47, fy * 0.815, w * 0.06, fy * 0.015), QColor("#2b1a0b"))
    p.setBrush(QColor("#9b1c1c"))
    p.drawEllipse(QPointF(w * 0.5, fy * 0.69), w * 0.012, w * 0.012)
    p.fillRect(QRectF(w * 0.497, fy * 0.73, w * 0.006, fy * 0.06), QColor("#2b1a0b"))
    # piso de madera en perspectiva
    vgrad(p, QRectF(0, fy, w, h - fy), [(0, "#a8723d"), (1, "#6d4521")])
    p.setPen(QPen(QColor(60, 35, 15, 120), max(1, w / 900)))
    cx = w / 2
    for i in range(-12, 13):
        p.drawLine(QPointF(cx + i * w * 0.05, fy), QPointF(cx + i * w * 0.12, h))
    for k in range(1, 5):
        y = fy + (h - fy) * (k / 5) ** 1.6
        p.drawLine(QPointF(0, y), QPointF(w, y))


def _sunset(p, w, h, fy, rng):
    vgrad(p, QRectF(0, 0, w, fy), [(0, "#1d1238"), (0.45, "#7a2e5c"), (0.75, "#ff7a3d"), (1, "#ffd27a")])
    sun = QRadialGradient(QPointF(w * 0.62, fy * 0.78), fy * 0.22)
    sun.setColorAt(0, QColor("#fff3c4"))
    sun.setColorAt(0.45, QColor("#ffcf6a"))
    sun.setColorAt(1, QColor(255, 150, 60, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(sun))
    p.drawEllipse(QPointF(w * 0.62, fy * 0.78), fy * 0.22, fy * 0.22)
    for i, (col, base, amp) in enumerate((("#5a2a52", fy * 0.80, fy * 0.30), ("#3e1d40", fy * 0.90, fy * 0.22),
                                          ("#26122b", fy * 1.0, fy * 0.14))):
        pts = ridge(rng, w, base, amp, w / (10 + 4 * i))
        poly(p, pts + [(w + 50, fy + 2), (-50, fy + 2)], col)
    vgrad(p, QRectF(0, fy, w, h - fy), [(0, "#3a1a26"), (1, "#180a12")])
    p.setPen(QPen(QColor(255, 160, 90, 90), max(1, w / 800)))
    p.drawLine(QPointF(0, fy), QPointF(w, fy))


def _city(p, w, h, fy, rng):
    vgrad(p, QRectF(0, 0, w, fy), [(0, "#070b1f"), (0.6, "#1a1446"), (1, "#3b1f5c")])
    p.setPen(Qt.PenStyle.NoPen)
    for _ in range(int(w / 6)):
        p.setBrush(QColor(255, 255, 255, rng.randint(60, 220)))
        r = rng.uniform(0.6, 1.6) * w / 1200
        p.drawEllipse(QPointF(rng.uniform(0, w), rng.uniform(0, fy * 0.6)), r, r)
    p.setBrush(QColor("#f4f1d8"))
    p.drawEllipse(QPointF(w * 0.18, fy * 0.18), fy * 0.07, fy * 0.07)
    for layer, (col, hmin, hmax, lit) in enumerate((("#1c1d3a", 0.35, 0.65, 0.15), ("#11122a", 0.25, 0.55, 0.35))):
        x = -10
        while x < w:
            bw = rng.uniform(w * 0.04, w * 0.09)
            bh = fy * rng.uniform(hmin, hmax)
            p.setBrush(QColor(col))
            p.drawRect(QRectF(x, fy - bh, bw, bh))
            cell = max(3.0, w / 220)
            for wy in range(int(bh / (cell * 2.2))):
                for wx in range(int(bw / (cell * 2))):
                    if rng.random() < lit:
                        p.setBrush(QColor(rng.choice(["#ffd27a", "#ffe9a8", "#9fd3ff"])))
                        p.drawRect(QRectF(x + cell * 0.6 + wx * cell * 2, fy - bh + cell + wy * cell * 2.2, cell, cell * 1.2))
            p.setBrush(QColor(col))
            x += bw + rng.uniform(0, w * 0.01)
    vgrad(p, QRectF(0, fy, w, h - fy), [(0, "#26263a"), (1, "#0d0d16")])
    p.setPen(QPen(QColor(255, 210, 120, 160), max(2, w / 300), Qt.PenStyle.DashLine))
    p.drawLine(QPointF(0, fy + (h - fy) * 0.55), QPointF(w, fy + (h - fy) * 0.55))
    p.setPen(QPen(QColor(255, 107, 53, 120), max(1, w / 900)))
    p.drawLine(QPointF(0, fy), QPointF(w, fy))


def _forest(p, w, h, fy, rng):
    vgrad(p, QRectF(0, 0, w, fy), [(0, "#9ad7e8"), (0.7, "#d7f0d0"), (1, "#bfe3a5")])
    p.setPen(Qt.PenStyle.NoPen)
    for layer, col in enumerate(("#7fb07a", "#4f8a55", "#2f6640")):
        n = 14 + layer * 6
        for i in range(n):
            x = rng.uniform(-w * 0.05, w * 1.05)
            th = fy * rng.uniform(0.35, 0.6) * (1 + layer * 0.25)
            tw = th * rng.uniform(0.35, 0.5)
            base = fy - layer * 2
            poly(p, [(x - tw / 2, base), (x + tw / 2, base), (x, base - th)], col)
            poly(p, [(x - tw * 0.4, base - th * 0.3), (x + tw * 0.4, base - th * 0.3), (x, base - th * 1.15)], col)
    # rayos de luz
    for i in range(4):
        x = w * (0.15 + i * 0.22)
        poly(p, [(x, 0), (x + w * 0.05, 0), (x + w * 0.16, fy), (x + w * 0.09, fy)], QColor(255, 255, 220, 28))
    vgrad(p, QRectF(0, fy, w, h - fy), [(0, "#4f8a3a"), (1, "#24451c")])
    p.setPen(QPen(QColor("#2e5a22"), max(1, w / 900)))
    for _ in range(int(w / 8)):
        x = rng.uniform(0, w)
        y = fy + rng.uniform(0, h - fy)
        p.drawLine(QPointF(x, y), QPointF(x + rng.uniform(-3, 3), y - rng.uniform(3, 9) * w / 900))


def _beach(p, w, h, fy, rng):
    vgrad(p, QRectF(0, 0, w, fy * 0.62), [(0, "#3d8fd6"), (1, "#bfe6ff")])
    p.setPen(Qt.PenStyle.NoPen)
    for _ in range(6):
        cx, cy, s = rng.uniform(0, w), rng.uniform(fy * 0.08, fy * 0.35), rng.uniform(0.6, 1.2) * w / 20
        p.setBrush(QColor(255, 255, 255, 220))
        for k in range(4):
            p.drawEllipse(QPointF(cx + k * s * 0.7, cy + (k % 2) * s * 0.15), s * 0.8, s * 0.45)
    vgrad(p, QRectF(0, fy * 0.62, w, fy * 0.38), [(0, "#1f7fb8"), (1, "#3fb4c9")])
    p.setPen(QPen(QColor(255, 255, 255, 120), max(1, w / 700)))
    for i in range(14):
        y = fy * 0.64 + i * fy * 0.026
        for _ in range(4):
            x = rng.uniform(0, w)
            p.drawLine(QPointF(x, y), QPointF(x + w * 0.04, y))
    p.setPen(Qt.PenStyle.NoPen)
    sand = QPainterPath(QPointF(0, fy * 0.97))
    for i in range(11):
        sand.lineTo(w * i / 10, fy * (0.95 + 0.03 * math.sin(i)))
    sand.lineTo(w, h)
    sand.lineTo(0, h)
    sand.closeSubpath()
    g = QLinearGradient(QPointF(0, fy), QPointF(0, h))
    g.setColorAt(0, QColor("#f3dfa6"))
    g.setColorAt(1, QColor("#d2b06a"))
    p.setBrush(QBrush(g))
    p.drawPath(sand)


def _temple(p, w, h, fy, rng):
    vgrad(p, QRectF(0, 0, w, fy), [(0, "#6a0f1a"), (0.6, "#c0392b"), (1, "#f39c4a")])
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffe2a8"))
    p.drawEllipse(QPointF(w * 0.5, fy * 0.42), fy * 0.16, fy * 0.16)
    dark = "#2a0a0e"
    cx = w * 0.5
    for i, (ww, hh) in enumerate(((0.36, 0.1), (0.28, 0.1), (0.2, 0.1))):
        y = fy * (0.58 - i * 0.16)
        poly(p, [(cx - w * ww / 2, y), (cx + w * ww / 2, y), (cx + w * ww * 0.36, y - fy * hh), (cx - w * ww * 0.36, y - fy * hh)], dark)
        p.fillRect(QRectF(cx - w * ww * 0.3, y, w * ww * 0.6, fy * 0.06), QColor(dark))
    p.fillRect(QRectF(cx - w * 0.15, fy * 0.6, w * 0.3, fy * 0.4), QColor(dark))
    for side in (-1, 1):
        for k in range(3):
            x = cx + side * w * (0.25 + k * 0.08)
            p.fillRect(QRectF(x - w * 0.012, fy * 0.45, w * 0.024, fy * 0.55), QColor("#3a0d12"))
            p.fillRect(QRectF(x - w * 0.02, fy * 0.43, w * 0.04, fy * 0.03), QColor("#3a0d12"))
    vgrad(p, QRectF(0, fy, w, h - fy), [(0, "#8a7b70"), (1, "#4d433d")])
    p.setPen(QPen(QColor(40, 30, 25, 140), max(1, w / 900)))
    for i in range(-14, 15):
        p.drawLine(QPointF(cx + i * w * 0.045, fy), QPointF(cx + i * w * 0.1, h))
    for k in range(1, 4):
        y = fy + (h - fy) * (k / 4) ** 1.5
        p.drawLine(QPointF(0, y), QPointF(w, y))


def _snow(p, w, h, fy, rng):
    vgrad(p, QRectF(0, 0, w, fy), [(0, "#5f86bf"), (0.7, "#cfe0f5"), (1, "#eef5fd")])
    for col, base, amp, step in (("#9fb3d3", fy * 0.78, fy * 0.55, w / 6), ("#6f86ad", fy * 0.95, fy * 0.38, w / 9)):
        pts = []
        x, up = -step, True
        while x <= w + step:
            y = base - amp * (rng.uniform(0.75, 1.0) if up else rng.uniform(0.15, 0.4))
            pts.append((x, y))
            x += step / 2 * rng.uniform(0.8, 1.2)
            up = not up
        poly(p, pts + [(w + 50, fy + 2), (-50, fy + 2)], col)
        for i in range(1, len(pts) - 1):
            x, y = pts[i]
            if y < pts[i - 1][1] and y < pts[i + 1][1]:
                k = 0.28
                lx = x + (pts[i - 1][0] - x) * k
                ly = y + (pts[i - 1][1] - y) * k
                rx = x + (pts[i + 1][0] - x) * k
                ry = y + (pts[i + 1][1] - y) * k
                poly(p, [(x, y), (rx, ry), ((x + rx) / 2, ry + fy * 0.02), (x, ry - fy * 0.01),
                         ((x + lx) / 2, ly + fy * 0.025), (lx, ly)], "#ffffff")
    vgrad(p, QRectF(0, fy, w, h - fy), [(0, "#f7fbff"), (1, "#c9d8ea")])
    p.setPen(Qt.PenStyle.NoPen)
    for _ in range(int(w / 5)):
        p.setBrush(QColor(255, 255, 255, rng.randint(120, 230)))
        r = rng.uniform(0.8, 2.2) * w / 1200
        p.drawEllipse(QPointF(rng.uniform(0, w), rng.uniform(0, fy)), r, r)


def _training(p, w, h, fy, rng):
    p.fillRect(QRectF(0, 0, w, h), QColor("#0b1830"))
    step = w / 24
    p.setPen(QPen(QColor(120, 170, 255, 60), 1))
    x = w / 2
    while x < w:
        p.drawLine(QPointF(x, 0), QPointF(x, h))
        p.drawLine(QPointF(w - x, 0), QPointF(w - x, h))
        x += step
    y = fy
    while y > 0:
        p.drawLine(QPointF(0, y), QPointF(w, y))
        y -= step
    p.setPen(QPen(QColor(120, 170, 255, 140), max(2, w / 500)))
    p.drawLine(QPointF(0, fy), QPointF(w, fy))
    p.drawLine(QPointF(w / 2, 0), QPointF(w / 2, h))
    vgrad(p, QRectF(0, fy + 1, w, h - fy), [(0, "#13274a"), (1, "#081022")])


SOLID = {"green": "#00b140", "black": "#000000", "gray": "#6b6f78"}
PAINTERS = {"dojo": _dojo, "sunset": _sunset, "city": _city, "forest": _forest, "beach": _beach,
            "temple": _temple, "snow": _snow, "training": _training}
FILL = {"dojo": "#3b2614", "sunset": "#1d1238", "city": "#070b1f", "forest": "#9ad7e8", "beach": "#3d8fd6",
        "temple": "#6a0f1a", "snow": "#7fa8d9", "training": "#0b1830", "green": "#00b140", "black": "#000000",
        "gray": "#6b6f78"}
_cache = {}


def render(key, w, h):
    """QImage del fondo (w×h) con el suelo en FLOOR·h. None para «cuadritos»."""
    w, h = max(16, int(w)), max(16, int(h))
    ck = (key, w, h)
    if ck in _cache:
        return _cache[ck]
    img = None
    if key in SOLID:
        img = QImage(w, h, QImage.Format.Format_RGB32)
        img.fill(QColor(SOLID[key]))
    elif key in PAINTERS:
        img = QImage(w, h, QImage.Format.Format_RGB32)
        img.fill(QColor("#000000"))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        PAINTERS[key](p, w, h, h * FLOOR, random.Random(sum(map(ord, key)) * 7919))
        p.end()
    elif key.startswith("file:"):
        src = QImage(key[5:])
        if not src.isNull():
            img = src.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                             Qt.TransformationMode.SmoothTransformation)
            x, y = (img.width() - w) // 2, img.height() - h
            img = img.copy(x, max(0, y), w, h)
    if len(_cache) > 24:
        _cache.clear()
    _cache[ck] = img
    return img


def fill_color(key):
    if key.startswith("file:"):
        img = render(key, 64, 64)
        if img is not None and not img.isNull():
            return QColor(img.pixel(32, 2))
        return QColor(theme.CANVAS)
    return QColor(FILL.get(key, theme.CANVAS))


def scene_rect(localcoord):
    """Zona de la escena (en píxeles del personaje) que ocupa el fondo: el suelo en y = 0."""
    lw, lh = localcoord
    w = lw * 2.4
    h = lh * 1.15
    return QRectF(-w / 2, -h * FLOOR, w, h)


# ---------------------------------------------------------------- selector
def preview_icon(key):
    from PyQt6.QtGui import QIcon, QPixmap
    if key == "checker":
        from ui.common import checker_brush
        pm = QPixmap(48, 28)
        p = QPainter(pm)
        p.fillRect(pm.rect(), checker_brush(4))
        p.end()
        return QIcon(pm)
    img = render(key, 96, 56)
    if img is None or img.isNull():
        return QIcon()
    return QIcon(QPixmap.fromImage(img.scaled(48, 28, Qt.AspectRatioMode.IgnoreAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)))


class BackdropPicker:
    """Lista de fondos + oscurecer; todas las vistas comparten la elección (MainWindow.set_backdrop)."""

    def __new__(cls, main):
        from PyQt6.QtCore import QSize
        from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSlider, QWidget
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        combo = QComboBox()
        combo.setIconSize(QSize(40, 22))
        combo.setMinimumWidth(110)
        combo.setToolTip(tr('Fondo de la vista'))
        lay.addWidget(combo)
        dim = QSlider(Qt.Orientation.Horizontal)
        dim.setRange(0, 180)
        dim.setFixedWidth(50)
        dim.setToolTip(tr('Oscurecer el fondo (para ver mejor el sprite y las cajas)'))
        lay.addWidget(QLabel("🌓"))
        lay.addWidget(dim)
        w.combo, w.dim = combo, dim

        def fill(current):
            combo.blockSignals(True)
            combo.clear()
            for key, lab in BACKGROUNDS:
                combo.addItem(preview_icon(key), tr(lab), key)
            if current.startswith("file:"):
                combo.addItem(preview_icon(current), Path(current[5:]).name, current)
            combo.addItem(tr('🖼 Imagen propia…'), "pick")
            i = combo.findData(current)
            combo.setCurrentIndex(max(0, i))
            combo.blockSignals(False)
        w.fill = fill

        def on_combo(_i):
            key = combo.currentData()
            if key == "pick":
                from PyQt6.QtWidgets import QFileDialog
                f, _ = QFileDialog.getOpenFileName(w, tr('Imagen de fondo'), str(Path.home()),
                                                   tr('Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.webp)'))
                if not f:
                    fill(main.backdrop[0])
                    return
                key = "file:" + f
            main.set_backdrop(key, dim.value())
        combo.currentIndexChanged.connect(on_combo)
        dim.valueChanged.connect(lambda v: main.set_backdrop(main.backdrop[0], v))
        return w
