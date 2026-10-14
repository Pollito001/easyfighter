"""Piezas compartidas de la interfaz: imágenes, vista con zoom, barra de progreso."""
import numpy as np
from PyQt6.QtCore import QEventLoop, QPointF, QRectF, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QComboBox, QGraphicsView, QHBoxLayout, QLabel, QMessageBox, QProgressDialog, QPushButton, QWidget,
)

from i18n import tr

APP_NAME = "EasyFighter"


def read_audio(parent, path):
    """Lee un sonido para el .snd: si no es un WAV que sirva (OGG, MP3, FLAC…) lo pasa a WAV.
    Devuelve los bytes o None (y avisa)."""
    from pathlib import Path

    from PyQt6.QtWidgets import QApplication

    from core import audio
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        return audio.to_wav(path)
    except (audio.AudioError, OSError):
        QMessageBox.warning(parent, APP_NAME, tr('No pude leer «{0}» como sonido. Prueba con otro formato '
                                                 '(WAV, OGG, MP3 o FLAC).').format(Path(path).name))
        return None
    finally:
        QApplication.restoreOverrideCursor()


def audio_filter():
    from core import audio
    return tr('Sonidos') + " (" + " ".join("*" + e for e in audio.EXTS) + ")"


def warn_banner():
    """Franja de aviso (amarilla, se ve bien en los dos temas). Empieza escondida."""
    lab = QLabel()
    lab.setWordWrap(True)
    lab.setTextFormat(Qt.TextFormat.RichText)
    lab.setStyleSheet("QLabel { background: rgba(255, 170, 0, 0.16); border: 1px solid rgba(255, 170, 0, 0.55);"
                      " border-radius: 6px; padding: 6px 10px; }")
    lab.hide()
    return lab


# ---------------------------------------------------------------- imágenes
def sprite_qimage(sff, sprite, override=None, pal=None):
    """QImage (ARGB) de un sprite con su paleta (o la elegida para el personaje)."""
    pix = sprite.pixels()
    h, w = pix.shape[:2]
    if w == 0 or h == 0:
        return QImage()
    if pix.ndim == 3:
        img = QImage(pix.tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        return img
    img = QImage(pix.tobytes(), w, h, w, QImage.Format.Format_Indexed8).copy()
    p = pal or sff.palette_for(sprite, override)
    img.setColorTable(p.table())
    return img


def image_to_indices(img, palette_rgb=None, transparent_rgb=None):
    """Convierte una QImage a (índices, paleta_rgb_256).
    - Si es de 8 bits con paleta, se usan sus índices y su paleta.
    - Si palette_rgb se da, cada color va al más parecido de esa paleta (el 0 queda para lo transparente).
    - Si no, se crea una paleta propia (hasta 255 colores)."""
    if img.format() == QImage.Format.Format_Indexed8 and palette_rgb is None:
        from core.sff import qimage_indices
        idx = qimage_indices(img)
        table = img.colorTable()
        rgb = np.zeros((256, 3), np.uint8)
        for i, c in enumerate(table[:256]):
            rgb[i] = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
        # lo transparente de la paleta pasa al índice 0
        alpha = np.array([(c >> 24) & 255 for c in table[:256]] + [255] * (256 - len(table[:256])), np.uint8)
        if alpha[0] != 0 and (alpha < 128).any():
            t = int(np.argmax(alpha < 128))
            swap = np.arange(256, dtype=np.uint8)
            swap[0], swap[t] = t, 0
            idx = swap[idx]
            rgb[[0, t]] = rgb[[t, 0]]
        return idx, rgb
    from core.sff import qimage_rgba
    rgba = qimage_rgba(img)
    h, w = rgba.shape[:2]
    trans = rgba[:, :, 3] < 128
    if transparent_rgb is not None:
        tr_ = np.array(transparent_rgb, np.uint8)
        trans |= np.all(rgba[:, :, :3] == tr_, axis=2)
    rgb = rgba[:, :, :3]
    packed = (rgb[:, :, 0].astype(np.uint32) << 16) | (rgb[:, :, 1].astype(np.uint32) << 8) | rgb[:, :, 2]
    packed = np.where(trans, np.uint32(0xFFFFFFFF), packed)
    uniq, inv = np.unique(packed.ravel(), return_inverse=True)
    solid = uniq[uniq != 0xFFFFFFFF]
    cols = np.stack([(solid >> 16) & 255, (solid >> 8) & 255, solid & 255], axis=1).astype(np.int32)
    if palette_rgb is not None:
        pal = np.array(palette_rgb, np.int32)[1:256]
        lut = np.zeros(len(uniq), np.uint8)
        if len(cols):
            best = np.empty(len(cols), np.int64)
            for a in range(0, len(cols), 4096):
                chunk = cols[a:a + 4096]
                d = ((chunk[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
                best[a:a + 4096] = d.argmin(axis=1) + 1
            lut[uniq != 0xFFFFFFFF] = best.astype(np.uint8)
        out_rgb = np.zeros((256, 3), np.uint8)
        out_rgb[:len(palette_rgb)] = np.array(palette_rgb, np.uint8)[:256]
        return lut[inv].reshape(h, w), out_rgb
    if len(cols) <= 255:
        lut = np.zeros(len(uniq), np.uint8)
        lut[uniq != 0xFFFFFFFF] = np.arange(1, len(cols) + 1, dtype=np.uint8)
        out_rgb = np.zeros((256, 3), np.uint8)
        out_rgb[1:len(cols) + 1] = cols
        return lut[inv].reshape(h, w), out_rgb
    # demasiados colores: Qt reduce a 255 y se mapea
    q = img.convertToFormat(QImage.Format.Format_RGB32).convertToFormat(
        QImage.Format.Format_Indexed8, Qt.ImageConversionFlag.ThresholdDither)
    table = q.colorTable()[:255]
    pal = [(0, 0, 0)] + [((c >> 16) & 255, (c >> 8) & 255, c & 255) for c in table]
    idx, out = image_to_indices(img, pal, transparent_rgb)
    return idx, out


def checker_brush(size=8):
    pm = QPixmap(size * 2, size * 2)
    pm.fill(QColor(70, 70, 76))
    p = QPainter(pm)
    p.fillRect(0, 0, size, size, QColor(86, 86, 94))
    p.fillRect(size, size, size, size, QColor(86, 86, 94))
    p.end()
    return QBrush(pm)


class ZoomView(QGraphicsView):
    """Vista con zoom (rueda), arrastre con el botón del medio y fondo de cuadritos."""
    zoomChanged = pyqtSignal(float)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(checker_brush())
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._pan = None
        self.zoom = 1.0
        self.backdrop_key = "checker"
        self.backdrop_rect = None
        self.backdrop_dim = 0

    def set_backdrop(self, key, rect, dim=0):
        """Fondo dibujado detrás de todo, en coordenadas de la escena (suelo en y = 0)."""
        self.backdrop_key = key or "checker"
        self.backdrop_rect = rect
        self.backdrop_dim = dim
        self.resetCachedContent()
        self.viewport().update()

    def drawBackground(self, painter, rect):
        if self.backdrop_key == "checker" or self.backdrop_rect is None:
            return super().drawBackground(painter, rect)
        from ui import backgrounds
        r = self.backdrop_rect
        scale = max(1.0, min(3.0, 2400 / max(1.0, r.width())))
        img = backgrounds.render(self.backdrop_key, r.width() * scale, r.height() * scale)
        if img is None or img.isNull():
            return super().drawBackground(painter, rect)
        top = QColor(img.pixel(img.width() // 2, 1))
        bottom = QColor(img.pixel(img.width() // 2, img.height() - 2))
        painter.fillRect(rect, top)
        if rect.bottom() > r.bottom():
            painter.fillRect(QRectF(rect.left(), r.bottom() - 1, rect.width(), rect.bottom() - r.bottom() + 1), bottom)
        # a los lados se repite el borde del fondo
        if rect.left() < r.left():
            painter.drawImage(QRectF(rect.left(), r.top(), r.left() - rect.left() + 1, r.height()), img,
                              QRectF(0, 0, 1, img.height()))
        if rect.right() > r.right():
            painter.drawImage(QRectF(r.right() - 1, r.top(), rect.right() - r.right() + 1, r.height()), img,
                              QRectF(img.width() - 1, 0, 1, img.height()))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(r, img)
        if self.backdrop_dim:
            painter.fillRect(r, QColor(0, 0, 0, int(self.backdrop_dim)))
        painter.restore()

    def set_zoom(self, z):
        z = max(0.1, min(32.0, z))
        self.resetTransform()
        self.scale(z, z)
        self.zoom = z
        self.zoomChanged.emit(z)

    wheel_step = 1.0009      # cuánto acerca cada «clic» de la rueda (120 unidades ≈ +11 %)

    def wheelEvent(self, e):
        """Zoom suave: proporcional a cuánto se movió la rueda (o el touchpad), no a saltos.
        Mayús + rueda: mover a los lados · Ctrl + rueda: mover arriba / abajo."""
        d = e.angleDelta()
        if e.pixelDelta() is not None and not e.pixelDelta().isNull() and d.isNull():
            d = e.pixelDelta() * 2
        mods = e.modifiers()
        if mods & Qt.KeyboardModifier.ShiftModifier:
            bar = self.horizontalScrollBar()
            bar.setValue(bar.value() - int((d.y() or d.x()) / 3))
            e.accept()
            return
        if mods & Qt.KeyboardModifier.ControlModifier:
            bar = self.verticalScrollBar()
            bar.setValue(bar.value() - int(d.y() / 3))
            e.accept()
            return
        delta = d.y() or d.x()
        if delta:
            self.set_zoom(self.zoom * (self.wheel_step ** max(-360, min(360, delta))))
            if hasattr(self, "on_wheel_zoom"):
                self.on_wheel_zoom()
        e.accept()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.MiddleButton:
            self._pan = e.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            d = e.position() - self._pan
            self._pan = e.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - d.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - d.y()))
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.MiddleButton and self._pan is not None:
            self._pan = None
            self.unsetCursor()
            e.accept()
            return
        super().mouseReleaseEvent(e)


def axis_pen():
    p = QPen(QColor(255, 220, 0, 200))
    p.setCosmetic(True)
    return p


def cosmetic(color, width=1, style=Qt.PenStyle.SolidLine):
    p = QPen(QColor(color))
    p.setCosmetic(True)
    p.setWidth(width)
    p.setStyle(style)
    return p


# ---------------------------------------------------------------- trabajos largos
class Cancelled(BaseException):
    pass


class _Job(QThread):
    step = pyqtSignal(str, float)

    def __init__(self, fn):
        super().__init__()
        self.fn, self.result, self.error, self.cancel = fn, None, None, False

    def report(self, text, frac):
        if self.cancel:
            raise Cancelled()
        self.step.emit(text, float(frac))

    def run(self):
        try:
            self.result = self.fn(self.report)
        except Cancelled:
            self.error = Cancelled()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error = e


def run_with_progress(parent, title, fn):
    """fn(report) en otro hilo con barra de progreso; report(texto, 0..1). Devuelve (resultado, cancelado)."""
    dlg = QProgressDialog(title, tr('Cancelar'), 0, 1000, parent)
    dlg.setWindowTitle(APP_NAME)
    dlg.setWindowModality(Qt.WindowModality.WindowModal)
    dlg.setMinimumDuration(300)
    dlg.setMinimumWidth(420)
    dlg.setAutoClose(False)
    dlg.setAutoReset(False)
    job = _Job(fn)

    def on_step(text, frac):
        if dlg.wasCanceled():
            job.cancel = True
            return
        dlg.setLabelText(text)
        dlg.setValue(max(0, min(1000, int(frac * 1000))))
    job.step.connect(on_step)
    dlg.canceled.connect(lambda: setattr(job, "cancel", True))
    loop = QEventLoop()
    job.finished.connect(loop.quit)
    job.start()
    if job.isRunning():
        loop.exec()
    job.wait()
    dlg.close()
    if isinstance(job.error, Cancelled):
        return None, True
    if job.error is not None:
        QMessageBox.warning(parent, APP_NAME, tr('❌ Algo falló: {0}').format(job.error))
    return job.result, False


def rectf(x1, y1, x2, y2):
    return QRectF(QPointF(min(x1, x2), min(y1, y2)), QPointF(max(x1, x2), max(y1, y2)))


# ---------------------------------------------------------------- controles de las pruebas animadas
def advance(view):
    """Avanza el reloj de una vista animada según su rapidez (y nada si está en pausa)."""
    if not view.isVisible() or getattr(view, "paused", False):
        return
    view._acc = getattr(view, "_acc", 0.0) + getattr(view, "speed", 1.0)
    n = int(view._acc)
    view._acc -= n
    if n:
        view.tick += n
        view.update()


class PlaybackBar(QWidget):
    """Rapidez, pausa y cuadro a cuadro para una vista animada (que tenga .tick)."""
    SPEEDS = [(1.0, '100% (normal)'), (0.5, '50%'), (0.25, '25%'), (0.1, '10%'), (2.0, '200%')]

    def __init__(self, view):
        super().__init__()
        self.view = view
        view.speed = 1.0
        view.paused = False
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tr('Rapidez:')))
        self.speed = QComboBox()
        for v, t in self.SPEEDS:
            self.speed.addItem(tr(t), v)
        self.speed.currentIndexChanged.connect(lambda _i: setattr(view, "speed", self.speed.currentData()))
        lay.addWidget(self.speed)
        self.pause = QPushButton(tr('⏸ Pausa'))
        self.pause.setCheckable(True)
        self.pause.toggled.connect(self.on_pause)
        lay.addWidget(self.pause)
        back = QPushButton(tr('⏮ −1'))
        back.setToolTip(tr('Un tick atrás (60 ticks = 1 segundo)'))
        back.clicked.connect(lambda: self.nudge(-1))
        fwd = QPushButton(tr('⏭ +1'))
        fwd.setToolTip(tr('Un tick adelante (60 ticks = 1 segundo)'))
        fwd.clicked.connect(lambda: self.nudge(1))
        lay.addWidget(back)
        lay.addWidget(fwd)
        self.lbl = QLabel()
        self.lbl.setObjectName("CardPath")
        lay.addWidget(self.lbl)
        lay.addStretch(1)
        from PyQt6.QtCore import QTimer
        self.t = QTimer(self)
        self.t.setInterval(100)
        self.t.timeout.connect(self.show_tick)
        self.t.start()

    def on_pause(self, on):
        self.view.paused = bool(on)
        self.pause.setText(tr('▶ Seguir') if on else tr('⏸ Pausa'))

    def nudge(self, d):
        if not self.pause.isChecked():
            self.pause.setChecked(True)
        self.view.tick = max(0, self.view.tick + d)
        self.view.update()
        self.show_tick()

    def show_tick(self):
        self.lbl.setText(tr('tick {0}').format(self.view.tick))
