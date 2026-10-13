"""
Sección «Selección»: las imágenes del personaje en la pantalla de selección de IKEMEN GO, juntas y fáciles:
- cara en la casilla (sprite 9000,0)
- retrato grande (sprite 9000,1)
- personaje animado en la selección (acción 0) y pose al elegirlo (acción 181)
- retrato de victoria (sprite 9000,2, opcional)
Con una vista previa que imita la pantalla de selección.
"""
from PyQt6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from core.air import Action
from core.sff import Sprite
from i18n import tr
from ui import theme
from ui.common import APP_NAME, checker_brush, image_to_indices, sprite_qimage

SLOTS = [
    # clave, (grupo, número), título, explicación, tamaño MUGEN a 320×240
    ("face", (9000, 0), 'Cara en la casilla', 'La imagen chiquita de la cuadrícula de personajes.', (25, 25)),
    ("portrait", (9000, 1), 'Retrato grande', 'La imagen grande al elegirlo (y en la pantalla VS de muchos screenpacks).', (120, 140)),
    ("victory", (9000, 2), 'Retrato de victoria (opcional)', 'La imagen de la pantalla de victoria en el modo arcade.', (120, 140)),
]


# ---------------------------------------------------------------- recorte
class CropView(QWidget):
    """Imagen con un recuadro de recorte que se mueve (arrastrar) y se agranda (rueda o esquina)."""
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.img = QImage()
        self.aspect = 1.0
        self.sel = QRectF(0, 0, 10, 10)
        self.zoom = 3.0
        self._drag = None
        self.setMinimumSize(420, 360)
        self.setMouseTracking(True)

    def set_image(self, img, aspect):
        self.img = img
        self.aspect = aspect
        w, h = img.width(), img.height()
        if not w or not h:
            return
        sw = min(w, h * aspect)
        sh = sw / aspect
        if sh > h:
            sh = h
            sw = sh * aspect
        self.sel = QRectF((w - sw) / 2, 0, sw, sh)
        self.zoom = max(0.5, min(8.0, min(560 / w, 480 / h)))
        self.setMinimumSize(int(w * self.zoom) + 2, int(h * self.zoom) + 2)
        self.update()
        self.changed.emit()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), checker_brush(6))
        if self.img.isNull():
            return
        z = self.zoom
        p.drawImage(QRectF(0, 0, self.img.width() * z, self.img.height() * z), self.img)
        r = QRectF(self.sel.x() * z, self.sel.y() * z, self.sel.width() * z, self.sel.height() * z)
        shade = QColor(0, 0, 0, 120)
        full = QRectF(0, 0, self.img.width() * z, self.img.height() * z)
        for part in (QRectF(full.left(), full.top(), full.width(), r.top() - full.top()),
                     QRectF(full.left(), r.bottom(), full.width(), full.bottom() - r.bottom()),
                     QRectF(full.left(), r.top(), r.left() - full.left(), r.height()),
                     QRectF(r.right(), r.top(), full.right() - r.right(), r.height())):
            if part.width() > 0 and part.height() > 0:
                p.fillRect(part, shade)
        p.setPen(QPen(QColor("#ff6b35"), 2))
        p.drawRect(r)
        p.fillRect(QRectF(r.right() - 6, r.bottom() - 6, 12, 12), QColor("#ff6b35"))

    def _img_pos(self, pos):
        return QPointF(pos.x() / self.zoom, pos.y() / self.zoom)

    def mousePressEvent(self, e):
        pt = self._img_pos(e.position())
        corner = QRectF(self.sel.right() - 8 / self.zoom, self.sel.bottom() - 8 / self.zoom,
                        16 / self.zoom, 16 / self.zoom)
        if corner.contains(pt):
            self._drag = ("size", pt, QRectF(self.sel))
        elif self.sel.contains(pt):
            self._drag = ("move", pt, QRectF(self.sel))
        else:
            # nuevo recuadro centrado en el clic
            r = QRectF(self.sel)
            r.moveCenter(pt)
            self.sel = self._clamp(r)
            self._drag = ("move", pt, QRectF(self.sel))
            self.update()
            self.changed.emit()

    def mouseMoveEvent(self, e):
        pt = self._img_pos(e.position())
        if self._drag is None:
            corner = QRectF(self.sel.right() - 8 / self.zoom, self.sel.bottom() - 8 / self.zoom,
                            16 / self.zoom, 16 / self.zoom)
            self.setCursor(Qt.CursorShape.SizeFDiagCursor if corner.contains(pt) else
                           (Qt.CursorShape.SizeAllCursor if self.sel.contains(pt) else Qt.CursorShape.CrossCursor))
            return
        kind, start, orig = self._drag
        d = pt - start
        if kind == "move":
            r = QRectF(orig)
            r.translate(d)
        else:
            w = max(4.0, orig.width() + max(d.x(), d.y() * self.aspect))
            r = QRectF(orig.left(), orig.top(), w, w / self.aspect)
        self.sel = self._clamp(r)
        self.update()
        self.changed.emit()

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def wheelEvent(self, e):
        f = 0.92 if e.angleDelta().y() > 0 else 1.08
        c = self.sel.center()
        w = max(4.0, self.sel.width() * f)
        r = QRectF(0, 0, w, w / self.aspect)
        r.moveCenter(c)
        self.sel = self._clamp(r)
        self.update()
        self.changed.emit()

    def _clamp(self, r):
        w, h = self.img.width(), self.img.height()
        if r.width() > w:
            r.setWidth(w)
            r.setHeight(w / self.aspect)
        if r.height() > h:
            r.setHeight(h)
            r.setWidth(h * self.aspect)
        x = min(max(0.0, r.x()), w - r.width())
        y = min(max(0.0, r.y()), h - r.height())
        return QRectF(x, y, r.width(), r.height())

    def cropped(self):
        r = self.sel.toAlignedRect()
        return self.img.copy(r)


class CropDialog(QDialog):
    """Elegir la parte de una imagen o de un sprite y ajustarla al tamaño de la imagen de selección."""

    def __init__(self, parent, sff, palette_override, size, title, file_image=None, default_sprite=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.sff = sff
        self.override = palette_override
        self.target = size
        self.file_image = file_image
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        top = QHBoxLayout()
        self.source = QComboBox()
        if file_image is not None:
            self.source.addItem(tr('Imagen del archivo'), None)
        else:
            for s in sff.sprites:
                self.source.addItem(f"{s.group}, {s.number}", s)
            if default_sprite is not None:
                for i in range(self.source.count()):
                    if self.source.itemData(i) is default_sprite:
                        self.source.setCurrentIndex(i)
        self.source.currentIndexChanged.connect(self.load_source)
        top.addWidget(QLabel(tr('Sacar de:')))
        top.addWidget(self.source, 1)
        left.addLayout(top)
        self.view = CropView()
        self.view.changed.connect(self.update_preview)
        sc = QScrollArea()
        sc.setWidget(self.view)
        sc.setWidgetResizable(False)
        sc.setMinimumSize(600, 500)
        left.addWidget(sc, 1)
        hint = QLabel(tr('Arrastra el recuadro para moverlo; la esquina o la rueda del ratón cambian su tamaño.'))
        hint.setObjectName("CardPath")
        left.addWidget(hint)
        lay.addLayout(left, 1)
        right = QVBoxLayout()
        f = QFormLayout()
        self.w = QSpinBox()
        self.h = QSpinBox()
        for s in (self.w, self.h):
            s.setRange(4, 2000)
        self.w.setValue(size[0])
        self.h.setValue(size[1])
        self.w.valueChanged.connect(self.on_size)
        self.h.valueChanged.connect(self.on_size)
        f.addRow(tr('Ancho final:'), self.w)
        f.addRow(tr('Alto final:'), self.h)
        right.addLayout(f)
        self.smooth = QRadioButton(tr('Suave'))
        self.pixel = QRadioButton(tr('Pixelado (nítido)'))
        self.smooth.setChecked(True)
        g = QButtonGroup(self)
        for b in (self.smooth, self.pixel):
            g.addButton(b)
            right.addWidget(b)
            b.toggled.connect(lambda _c: self.update_preview())
        right.addWidget(QLabel(tr('Colores:')))
        self.own = QRadioButton(tr('Paleta propia (colores exactos)'))
        self.char = QRadioButton(tr('Paleta del personaje (cambia con ella)'))
        g2 = QButtonGroup(self)
        for b in (self.own, self.char):
            g2.addButton(b)
            right.addWidget(b)
        (self.own if file_image is not None else self.char).setChecked(True)
        right.addWidget(QLabel(tr('Así quedará:')))
        self.prev = QLabel()
        self.prev.setMinimumSize(200, 200)
        self.prev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prev.setObjectName("Pic")
        right.addWidget(self.prev)
        right.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        rw = QWidget()
        rw.setLayout(right)
        rw.setFixedWidth(280)
        lay.addWidget(rw)
        self.load_source()

    def load_source(self):
        if self.file_image is not None:
            img = self.file_image
        else:
            s = self.source.currentData()
            img = sprite_qimage(self.sff, s, self.override) if s is not None else QImage()
        self.view.set_image(img.convertToFormat(QImage.Format.Format_ARGB32), self.w.value() / self.h.value())

    def on_size(self):
        self.view.aspect = self.w.value() / self.h.value()
        self.view.sel = self.view._clamp(QRectF(self.view.sel.x(), self.view.sel.y(), self.view.sel.width(),
                                                self.view.sel.width() / self.view.aspect))
        self.view.update()
        self.update_preview()

    def result_image(self):
        mode = Qt.TransformationMode.SmoothTransformation if self.smooth.isChecked() else Qt.TransformationMode.FastTransformation
        img = self.view.cropped().scaled(self.w.value(), self.h.value(), Qt.AspectRatioMode.IgnoreAspectRatio, mode)
        return img

    def update_preview(self):
        img = self.result_image()
        if img.isNull():
            return
        z = max(1, min(8, 190 // max(img.width(), img.height())))
        pm = QPixmap(img.width() * z, img.height() * z)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        p.fillRect(pm.rect(), checker_brush(4))
        p.drawImage(QRect(0, 0, pm.width(), pm.height()), img)
        p.end()
        self.prev.setPixmap(pm)


# ---------------------------------------------------------------- vista previa de la pantalla de selección
class SelectPreview(QWidget):
    def __init__(self, tab):
        super().__init__()
        self.tab = tab
        self.t = 0
        self.setMinimumHeight(240)
        self.setMaximumHeight(380)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        self.done_mode = False

    def tick(self):
        if self.isVisible():
            self.t += 1
            self.update()

    def anim_frame(self, number):
        p = self.tab.main.project
        a = p.air.find(number) if p else None
        if not a or not a.frames:
            return None, None
        total = sum(max(1, f.time) for f in a.frames if f.time >= 0)
        if any(f.time < 0 for f in a.frames):
            t, acc = self.t, 0
            for f in a.frames:
                if f.time < 0 or t < acc + max(1, f.time):
                    return f, a
                acc += max(1, f.time)
            return a.frames[-1], a
        t = self.t % max(1, total)
        acc = 0
        for f in a.frames:
            if t < acc + max(1, f.time):
                return f, a
            acc += max(1, f.time)
        return a.frames[-1], a

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        g = QLinearGradient(QPointF(0, 0), QPointF(0, r.height()))
        g.setColorAt(0, QColor("#1b1030"))
        g.setColorAt(0.6, QColor("#3a1b3f"))
        g.setColorAt(1, QColor("#14161b"))
        p.fillRect(r, g)
        proj = self.tab.main.project
        if not proj:
            return
        sff = proj.sff
        k = 2.0 * 320 / max(1, proj.localcoord()[0])  # 2 píxeles de pantalla por píxel MUGEN
        k = max(0.25, min(4.0, k * min(1.0, r.height() / 330)))
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        # retrato grande
        big = sff.find(9000, 1)
        x0 = 20
        if big is not None:
            img = sprite_qimage(sff, big, self.tab.override())
            bw, bh = img.width() * k, img.height() * k
            p.drawImage(QRectF(x0, r.height() - bh - 30, bw, bh), img)
            x0 += bw + 10
        else:
            p.setPen(QPen(QColor("#5b6270"), 1, Qt.PenStyle.DashLine))
            p.drawRect(QRectF(x0, r.height() - 30 - 140 * k, 120 * k, 140 * k))
            p.drawText(QRectF(x0, r.height() - 30 - 140 * k, 120 * k, 140 * k), Qt.AlignmentFlag.AlignCenter,
                       tr('sin retrato'))
            x0 += 120 * k + 10
        # personaje animado (acción 0 o 181 si «elegido»)
        f, _a = self.anim_frame(181 if self.done_mode else 0)
        if f is None and self.done_mode:
            f, _a = self.anim_frame(0)
        floor = r.height() - 34
        if f is not None:
            s = sff.find(f.group, f.number)
            if s is not None:
                img = sprite_qimage(sff, s, self.tab.override())
                cx = x0 + 60 * k
                p.save()
                p.translate(cx + f.x * k, floor + f.y * k)
                if "H" in (f.flip or "").upper():
                    p.scale(-1, 1)
                if "V" in (f.flip or "").upper():
                    p.scale(1, -1)
                p.drawImage(QRectF(-s.x * k, -s.y * k, img.width() * k, img.height() * k), img)
                p.restore()
        # nombre
        p.setPen(QColor("#ffffff"))
        fnt = QFont(self.font())
        fnt.setPointSize(16)
        fnt.setBold(True)
        p.setFont(fnt)
        p.drawText(QRectF(20, r.height() - 30, r.width() / 2, 28), Qt.AlignmentFlag.AlignVCenter, proj.name())
        # cuadrícula de casillas
        face = sff.find(9000, 0)
        fimg = sprite_qimage(sff, face, self.tab.override()) if face is not None else None
        fw = (fimg.width() if fimg else 25) * k
        fh = (fimg.height() if fimg else 25) * k
        cols, rows = 6, 3
        gap = 4
        gx = r.width() - cols * (fw + gap) - 24
        gy = 24
        for row in range(rows):
            for col in range(cols):
                cell = QRectF(gx + col * (fw + gap), gy + row * (fh + gap), fw, fh)
                p.fillRect(cell, QColor(255, 255, 255, 18))
                p.setPen(QPen(QColor(255, 255, 255, 50), 1))
                p.drawRect(cell)
                if row == 0 and col == 0 and fimg is not None:
                    p.drawImage(cell, fimg)
        cur = QRectF(gx - 2, gy - 2, fw + 4, fh + 4)
        blink = 200 if (self.t // 20) % 2 == 0 else 120
        p.setPen(QPen(QColor(255, 107, 53, blink), 3))
        p.drawRect(cur)
        p.setFont(QFont(self.font().family(), 9))
        p.setPen(QColor("#ffb547"))
        p.drawText(QRectF(gx, gy + rows * (fh + gap) + 4, cols * (fw + gap), 18), Qt.AlignmentFlag.AlignLeft,
                   tr('1P') + ("  ✔ " + tr('elegido') if self.done_mode else ""))


# ---------------------------------------------------------------- pestaña
class SelectTab(QWidget):
    modifiedChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        intro = QLabel(tr('Todo lo que se ve de tu personaje en la pantalla de selección de IKEMEN GO, en un solo '
                          'lugar. Los cambios se guardan en los sprites y animaciones (con deshacer).'))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        top = QHBoxLayout()
        self.preview = SelectPreview(self)
        top.addWidget(self.preview, 1)
        side = QVBoxLayout()
        self.pal = QComboBox()
        self.pal.currentIndexChanged.connect(lambda _i: self.preview.update())
        side.addWidget(QLabel(tr('Paleta:')))
        side.addWidget(self.pal)
        self.done_btn = QPushButton(tr('✔ Ver como «elegido»'))
        self.done_btn.setCheckable(True)
        self.done_btn.setToolTip(tr('Muestra la pose al elegirlo (acción 181)'))
        self.done_btn.toggled.connect(lambda c: setattr(self.preview, "done_mode", c))
        side.addWidget(self.done_btn)
        side.addStretch(1)
        sw = QWidget()
        sw.setLayout(side)
        sw.setFixedWidth(200)
        top.addWidget(sw)
        lay.addLayout(top, 2)
        cards = QWidget()
        grid = QGridLayout(cards)
        grid.setSpacing(10)
        self.cards = {}
        for i, (key, gn, title, desc, size) in enumerate(SLOTS):
            grid.addWidget(self.make_card(key, gn, tr(title), tr(desc), size), 0, i)
        grid.addWidget(self.make_anim_card(), 0, len(SLOTS))
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setWidget(cards)
        sc.setMinimumHeight(300)
        lay.addWidget(sc, 3)

    # ---- tarjetas
    def make_card(self, key, gn, title, desc, size):
        box = QFrame()
        box.setObjectName("Card")
        v = QVBoxLayout(box)
        t = QLabel(f"{title}  <span style='color:{theme.MUTED}'>({gn[0]},{gn[1]})</span>")
        t.setObjectName("CardTitle")
        v.addWidget(t)
        d = QLabel(desc)
        d.setWordWrap(True)
        d.setObjectName("CardPath")
        v.addWidget(d)
        pic = QLabel()
        pic.setMinimumSize(QSize(150, 120))
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pic.setObjectName("Pic")
        v.addWidget(pic, 1)
        info = QLabel()
        info.setObjectName("CardPath")
        info.setWordWrap(True)
        v.addWidget(info)
        for txt, fn in ((tr('📂 Poner una imagen…'), lambda: self.import_image(key)),
                        (tr('🧩 Sacar de una hoja…'), lambda: self.from_sheet(key)),
                        (tr('✂ Sacar de un sprite…'), lambda: self.from_sprite(key)),
                        (tr('🖌 Editar píxeles'), lambda: self.edit_pixels(key)),
                        (tr('💾 Exportar'), lambda: self.export(key)),
                        (tr('🗑 Quitar'), lambda: self.remove(key))):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            v.addWidget(b)
        self.cards[key] = (pic, info)
        return box

    def make_anim_card(self):
        box = QFrame()
        box.setObjectName("Card")
        v = QVBoxLayout(box)
        t = QLabel(tr('Personaje animado'))
        t.setObjectName("CardTitle")
        v.addWidget(t)
        d = QLabel(tr('En la selección se ve la animación de parado (acción 0). Al elegirlo, muchos screenpacks '
                      'muestran la acción 181 (pose de victoria).'))
        d.setWordWrap(True)
        d.setObjectName("CardPath")
        v.addWidget(d)
        self.anim_info = QLabel()
        self.anim_info.setWordWrap(True)
        v.addWidget(self.anim_info)
        v.addStretch(1)
        for txt, fn in ((tr('🚶 Cambiar la animación de parado'), lambda: self.main.simple.goto_slot("idle")),
                        (tr('🏆 Cambiar la pose al elegirlo'), lambda: self.main.simple.goto_slot("select_pose")),
                        (tr('➕ Crear la 181 copiando otra acción…'), self.make_181)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            v.addWidget(b)
        return box

    # ---- datos
    def is_modified(self):
        return False

    def save(self):
        return True

    def load(self):
        self.pal.blockSignals(True)
        self.pal.clear()
        p = self.main.project
        if p:
            for n, name, pal in p.char_palettes():
                self.pal.addItem(tr('Paleta {0}').format(n), pal)
        if self.pal.count() == 0:
            self.pal.addItem(tr('Paleta del SFF'), None)
        self.pal.blockSignals(False)
        self.refresh()

    def activated(self):
        self.refresh()

    def override(self):
        from core.sff import Palette
        d = self.pal.currentData()
        return d if isinstance(d, Palette) else None

    def lc_k(self):
        p = self.main.project
        return (p.localcoord()[0] / 320) if p else 1.0

    def target_size(self, key):
        for k, _gn, _t, _d, size in SLOTS:
            if k == key:
                kk = self.lc_k()
                return max(4, round(size[0] * kk)), max(4, round(size[1] * kk))
        return 25, 25

    def slot(self, key):
        for k, gn, title, _d, _s in SLOTS:
            if k == key:
                return gn, tr(title)
        return None, ""

    def refresh(self):
        p = self.main.project
        if not p:
            return
        sff = p.sff
        for key, gn, _t, _d, _s in SLOTS:
            pic, info = self.cards[key]
            s = sff.find(*gn)
            tw, th = self.target_size(key)
            if s is None:
                pic.setPixmap(QPixmap())
                pic.setText(tr('(no tiene)'))
                info.setText(tr('Tamaño común: {0}×{1}').format(tw, th))
                continue
            img = sprite_qimage(sff, s, self.override())
            z = max(1, min(6, 140 // max(1, max(img.width(), img.height()))))
            pm = QPixmap.fromImage(img.scaled(img.width() * z, img.height() * z, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.FastTransformation))
            if pm.width() > 200 or pm.height() > 160:
                pm = pm.scaled(200, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            pic.setText("")
            pic.setPixmap(pm)
            w, h = s.size()
            note = tr('Tamaño: {0}×{1}').format(w, h)
            if (w, h) != (tw, th):
                note += " · " + tr('común: {0}×{1}').format(tw, th)
            info.setText(note)
        a0, a181 = p.air.find(0), p.air.find(181)
        self.anim_info.setText(
            ("✅ " + tr('Acción 0: {0} cuadros').format(len(a0.frames)) if a0 else "❌ " + tr('Falta la acción 0')) + "<br>" +
            ("✅ " + tr('Acción 181: {0} cuadros').format(len(a181.frames)) if a181 else "⚠ " + tr('No tiene la acción 181')))
        self.preview.update()

    # ---- acciones
    def put_image(self, key, img, own_palette):
        """Guarda la imagen como el sprite de esa parte (con deshacer, desde la pestaña Sprites)."""
        p = self.main.project
        sff = p.sff
        sp = self.main.sprites
        gn, title = self.slot(key)
        if own_palette:
            idx, rgb = image_to_indices(img)
            palidx = sp._palette_slot(rgb)
        else:
            base = self.override() or sff.palettes[0]
            idx, _rgb = image_to_indices(img, base.colors[:, :3])
            palidx = 0
        old = sff.find(*gn)
        before = list(sff.sprites)
        new = Sprite(gn[0], gn[1], 0, 0)
        new.set_pixels(idx)
        new.palidx = palidx

        def redo():
            lst = [s for s in before if s is not old]
            pos = before.index(old) if old is not None else len(lst)
            lst.insert(min(pos, len(lst)), new)
            sff.sprites[:] = lst

        def undo():
            sff.sprites[:] = before
        sp.push(tr('Cambiar {0}').format(title), redo, undo, refresh_list=True)
        sp.fill_sprite_palettes()
        self.main.update_title()
        self.main.refresh_header()
        self.refresh()

    def import_image(self, key):
        p = self.main.project
        if not p:
            return
        f, _ = QFileDialog.getOpenFileName(self, tr('Elegir imagen'), str(p.folder),
                                           tr('Imágenes (*.png *.bmp *.gif *.pcx *.jpg *.jpeg *.webp)'))
        if not f:
            return
        img = QImage(f)
        if img.isNull():
            QMessageBox.warning(self, APP_NAME, tr('No pude abrir esa imagen.'))
            return
        gn, title = self.slot(key)
        dlg = CropDialog(self, p.sff, self.override(), self.target_size(key), title, file_image=img)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.put_image(key, dlg.result_image(), dlg.own.isChecked())

    def from_sheet(self, key):
        """Cortador de hojas: eliges un cuadro de la hoja y luego lo recortas al tamaño de la casilla."""
        p = self.main.project
        if not p:
            return
        from ui.sheet_cutter import SheetCutter, rgba_image
        gn, title = self.slot(key)
        cut = SheetCutter(self.main, slot_title=title)
        if cut.exec() != QDialog.DialogCode.Accepted:
            return
        frames = cut.frames()
        if not frames:
            return
        if len(frames) > 1:
            QMessageBox.information(self, APP_NAME, tr('Elegiste {0} cuadros; se usa el primero.').format(len(frames)))
        img = rgba_image(frames[0][0])
        dlg = CropDialog(self, p.sff, self.override(), self.target_size(key), title, file_image=img)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.put_image(key, dlg.result_image(), dlg.own.isChecked())

    def from_sprite(self, key):
        p = self.main.project
        if not p or not p.sff.sprites:
            return
        gn, title = self.slot(key)
        default = p.sff.find(9000, 1) if key == "face" else p.sff.find(0, 0)
        default = default or p.sff.find(0, 0) or p.sff.sprites[0]
        dlg = CropDialog(self, p.sff, self.override(), self.target_size(key), title, default_sprite=default)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.put_image(key, dlg.result_image(), dlg.own.isChecked())

    def edit_pixels(self, key):
        p = self.main.project
        gn, _t = self.slot(key)
        s = p.sff.find(*gn) if p else None
        if s is None:
            QMessageBox.information(self, APP_NAME, tr('Todavía no tiene esa imagen: ponle una primero.'))
            return
        sp = self.main.sprites
        sp.show_sprite(s)
        sp.current = s
        sp.edit_pixels()
        self.refresh()

    def export(self, key):
        p = self.main.project
        gn, _t = self.slot(key)
        s = p.sff.find(*gn) if p else None
        if s is None:
            return
        f, _ = QFileDialog.getSaveFileName(self, tr('Exportar PNG'), str(p.folder / f"{gn[0]}-{gn[1]}.png"), "PNG (*.png)")
        if f:
            sprite_qimage(p.sff, s, self.override()).save(f, "PNG")

    def remove(self, key):
        p = self.main.project
        gn, title = self.slot(key)
        s = p.sff.find(*gn) if p else None
        if s is None:
            return
        if QMessageBox.question(self, APP_NAME, tr('¿Quitar «{0}»?').format(title)) != QMessageBox.StandardButton.Yes:
            return
        sff = p.sff
        before = list(sff.sprites)
        self.main.sprites.push(tr('Quitar {0}').format(title), lambda: sff.sprites.remove(s) if s in sff.sprites else None,
                               lambda: sff.sprites.__setitem__(slice(None), before), refresh_list=True)
        self.refresh()

    def goto_anim(self, number):
        p = self.main.project
        an = self.main.anims
        a = p.air.find(number) if p else None
        if a is None:
            QMessageBox.information(self, APP_NAME, tr('Todavía no existe la acción {0}.').format(number))
            return
        self.main.tabs.setCurrentWidget(an)
        an.select_action(a)

    def make_181(self):
        p = self.main.project
        if not p:
            return
        if p.air.find(181) is not None:
            if QMessageBox.question(self, APP_NAME, tr('Ya existe la acción 181. ¿Reemplazarla?')) != QMessageBox.StandardButton.Yes:
                return
        dlg = QDialog(self)
        dlg.setWindowTitle(tr('Pose al elegir'))
        f = QFormLayout(dlg)
        combo = QComboBox()
        for a in p.air.actions:
            if a.number != 181:
                combo.addItem(f"{a.number}   {a.title}", a)
        for i in range(combo.count()):
            if combo.itemData(i).number in (180, 195, 0):
                combo.setCurrentIndex(i)
                break
        f.addRow(tr('Copiar la acción:'), combo)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if not dlg.exec():
            return
        src = combo.currentData()
        new = Action(181)
        new.frames = [fr.copy() for fr in src.frames]
        new.loopstart = src.loopstart
        new.title = tr('Pose al elegir')
        new.header = ["; " + new.title]
        new.raw = None
        lst = sorted([a for a in p.air.actions if a.number != 181] + [new], key=lambda a: a.number)
        self.main.anims.edit_list(tr('Crear la acción 181'), lst, new)
        self.refresh()

