"""Cortador de hojas de sprites: encuentra cada cuadro solo, deja arreglar a mano y muestra la animación."""
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QGraphicsScene,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
    QRadioButton, QScrollArea, QSlider, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from core import sheetcut as sc
from core.sff import qimage_rgba
from i18n import tr
from ui import theme
from ui.common import APP_NAME, ZoomView, cosmetic

IMAGE_FILTER = 'Imágenes (*.png *.bmp *.gif *.pcx *.jpg *.jpeg *.tga *.webp)'
AXIS_LABELS = [("ground", 'Suelo común de cada fila (recomendado)'), ("feet", 'Los pies de cada cuadro'),
               ("center", 'El centro de cada cuadro'),
               ("center_feet", 'El centro de cada cuadro, con los pies en el piso')]
_CACHE = {}   # ruta → (QImage, rgba)


def rgba_image(rgba):
    h, w = rgba.shape[:2]
    return QImage(np.ascontiguousarray(rgba).tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888).copy()


def swatch(rgb, size=16):
    pm = QPixmap(size, size)
    pm.fill(QColor(*rgb))
    return QIcon(pm)


# ---------------------------------------------------------------- la hoja
class SheetView(ZoomView):
    def __init__(self, dlg):
        self.scene_ = QGraphicsScene()
        super().__init__(self.scene_)
        self.dlg = dlg
        self.pix_item = None
        self.drag = None        # (inicio en escena, modo) modo: "select" | "draw"
        self.drag_now = None
        self.picking = False
        self.setMouseTracking(True)
        self.hover = None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        st = getattr(self.dlg, "stretch", None)
        if st is not None and st.isChecked():
            self.dlg.fit()

    def unstretch(self):
        need = Qt.ScrollBarPolicy.ScrollBarAsNeeded
        if self.horizontalScrollBarPolicy() != need:
            self.setHorizontalScrollBarPolicy(need)
            self.setVerticalScrollBarPolicy(need)

    def on_wheel_zoom(self):
        # con la rueda se deja de llenar la zona (zoom libre)
        st = getattr(self.dlg, "stretch", None)
        if st is not None and st.isChecked():
            st.blockSignals(True)
            st.setChecked(False)
            st.blockSignals(False)
            self.dlg.opts["stretch"] = False
        self.unstretch()

    def set_image(self, img):
        self.scene_.clear()
        self.pix_item = self.scene_.addPixmap(QPixmap.fromImage(img))
        self.scene_.setSceneRect(QRectF(-20, -20, img.width() + 40, img.height() + 40))

    def box_at(self, pt):
        best = None
        for b in self.dlg.boxes:
            if b.x0 <= pt.x() < b.x1 and b.y0 <= pt.y() < b.y1:
                if best is None or b.w * b.h < best.w * best.h:
                    best = b
        return best

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            pt = self.mapToScene(e.position().toPoint())
            if self.picking:
                self.dlg.pick_color(int(pt.x()), int(pt.y()))
                return
            mode = "draw" if e.modifiers() & Qt.KeyboardModifier.ShiftModifier else "select"
            self.drag = (pt, mode)
            self.drag_now = pt
            return
        if e.button() == Qt.MouseButton.RightButton:
            # botón derecho: arrastrar mueve la hoja (un clic sin arrastrar abre el menú del cuadro)
            self._pan = e.position()
            self._pan_from = e.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        pt = self.mapToScene(e.position().toPoint())
        if self.drag is not None:
            self.drag_now = pt
            self.viewport().update()
            return
        b = self.box_at(pt)
        if b is not self.hover:
            self.hover = b
            self.viewport().update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton and self._pan is not None:
            moved = (e.position() - self._pan_from).manhattanLength() > 4
            self._pan = None
            self.unsetCursor()
            if not moved:
                b = self.box_at(self.mapToScene(e.position().toPoint()))
                if b is not None:
                    self.dlg.context_menu(b, e.globalPosition().toPoint())
            return
        if e.button() == Qt.MouseButton.LeftButton and self.drag is not None:
            start, mode = self.drag
            end = self.mapToScene(e.position().toPoint())
            self.drag = None
            moved = abs(end.x() - start.x()) > 3 or abs(end.y() - start.y()) > 3
            if mode == "draw" and moved:
                self.dlg.add_manual(start, end)
            elif moved:
                self.dlg.select_rect(QRectF(start, end).normalized(),
                                     add=not (e.modifiers() & Qt.KeyboardModifier.AltModifier))
            else:
                b = self.box_at(end)
                if b is not None:
                    if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                        self.dlg.repeat(b)          # Ctrl+clic: el mismo cuadro otra vez, al final
                    else:
                        self.dlg.toggle(b)
            self.viewport().update()
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        b = self.box_at(self.mapToScene(e.position().toPoint()))
        if b is not None:
            self.dlg.select_row(b.row)

    def drawForeground(self, p, rect):
        boxes = self.dlg.boxes
        order = {}
        for i, k in enumerate(self.dlg.sel):
            order.setdefault(k, []).append(str(i + 1))
        f = QFont()
        f.setPixelSize(max(9, int(12 / max(0.2, self.zoom))))
        f.setBold(True)
        p.setFont(f)
        for b in boxes:
            r = QRectF(b.x0 - 0.5, b.y0 - 0.5, b.w + 1, b.h + 1)
            if not rect.intersects(r):
                continue
            if b.selected:
                p.fillRect(r, QColor(255, 107, 53, 50))
                p.setPen(cosmetic(QColor("#ff6b35"), 2))
            elif b is self.hover:
                p.setPen(cosmetic(QColor("#ffffff"), 1))
            else:
                p.setPen(cosmetic(QColor(80, 220, 255, 200), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r)
            if b.selected:
                t = ",".join(order.get((b.x0, b.y0, b.x1, b.y1), ["?"]))
                tr_ = QRectF(b.x0, b.y0 - f.pixelSize() - 3, max(18, len(t) * f.pixelSize() * 0.62 + 6),
                             f.pixelSize() + 3)
                p.fillRect(tr_, QColor("#ff6b35"))
                p.setPen(QColor("#111"))
                p.drawText(tr_, Qt.AlignmentFlag.AlignCenter, t)
        # cuadros que ya se usaron en este personaje (marcados en morado, con la casilla donde están)
        if self.dlg.show_used.isChecked():
            fs = QFont(f)
            fs.setPixelSize(max(3, int(round(11 / max(0.2, self.zoom)))))
            fs.setBold(True)
            p.setFont(fs)
            for (x0, y0, x1, y1), names in self.dlg.used_groups().items():
                r = QRectF(x0 - 0.5, y0 - 0.5, x1 - x0 + 1, y1 - y0 + 1)
                if not rect.intersects(r):
                    continue
                p.fillRect(r, QColor(170, 90, 255, 55))
                p.setPen(cosmetic(QColor(190, 120, 255, 230), 2, Qt.PenStyle.DashLine))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(r)
                t = "✓ " + " · ".join(names)
                h = fs.pixelSize() + 3
                full = len(t) * fs.pixelSize() * 0.62 + 8
                hov = self.hover is not None and self.dlg.overlaps(
                    (x0, y0, x1, y1), (self.hover.x0, self.hover.y0, self.hover.x1, self.hover.y1))
                # cabe en el cuadro; con el ratón encima se ve el nombre completo
                tw = full if hov else min(max(r.width(), 20), full)
                tag = QRectF(x0, y1 - h, tw, h)
                p.fillRect(tag, QColor(120, 60, 200, 220))
                p.setPen(QColor("#ffffff"))
                p.drawText(tag.adjusted(3, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, t)
            p.setFont(f)
        if self.drag is not None and self.drag_now is not None:
            start, mode = self.drag
            r = QRectF(start, self.drag_now).normalized()
            p.setPen(cosmetic(QColor("#ffb547") if mode == "select" else QColor("#7CFC00"), 1, Qt.PenStyle.DashLine))
            p.fillRect(r, QColor(255, 181, 71, 30) if mode == "select" else QColor(124, 252, 0, 30))
            p.drawRect(r)


# ---------------------------------------------------------------- la animación
class Player(QWidget):
    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg
        self.frames = []    # [(QImage, ax, ay)]
        self.tick = 0
        self.setMinimumSize(QSize(260, 200))
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.step)
        self.timer.start()

    def set_frames(self, frames):
        self.frames = frames
        self.update()

    def step(self):
        if len(self.frames) > 1:
            self.tick += 1
            self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.CANVAS))
        p.drawRoundedRect(r, 8, 8)
        if not self.frames:
            p.setPen(QColor(theme.MUTED))
            p.drawText(r.adjusted(10, 10, -10, -10), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       tr('Elige cuadros en la hoja para verlos animados aquí.'))
            p.end()
            return
        box = None
        for img, ax, ay in self.frames:
            fr = QRectF(-ax, -ay, img.width(), img.height())
            box = fr if box is None else box.united(fr)
        box = box.united(QRectF(-1, -1, 2, 2))
        sc_ = min((r.width() - 20) / box.width(), (r.height() - 30) / box.height(), 4.0)
        ox = r.center().x() - (box.left() + box.width() / 2) * sc_
        oy = r.top() + 10 - box.top() * sc_
        p.setPen(QPen(QColor(255, 107, 53, 140), 1))
        p.drawLine(int(r.left() + 8), int(oy), int(r.right() - 8), int(oy))
        speed = max(1, self.dlg.speed.value())
        i = (self.tick // speed) % len(self.frames)
        img, ax, ay = self.frames[i]
        p.drawImage(QRectF(ox - ax * sc_, oy - ay * sc_, img.width() * sc_, img.height() * sc_), img)
        p.setPen(QColor(theme.MUTED))
        p.drawText(r.adjusted(8, 4, -8, -4), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                   f"{i + 1}/{len(self.frames)}")
        p.end()


# ---------------------------------------------------------------- el diálogo
class SheetCutter(QDialog):
    """slot_title: para el modo simple (elegir los cuadros de una casilla).
    advanced: muestra las opciones para agregarlos como sprites (grupo, paleta, animaciones)."""

    def __init__(self, main, slot_title=None, advanced=False, start_group=0):
        super().__init__(main)
        from ui.mainwindow import load_settings
        self.main = main
        self.advanced = advanced
        self.slot_title = slot_title
        st = load_settings()
        self.opts = dict(st.get("sheet_opts") or {})
        self.path = None
        self.rgba = None
        self.boxes = []
        self.label = None
        self.fg = None
        self.crops = {}
        self.bg_colors = []
        self.used_colors = []
        self.auto_bg = (False, [])
        self.manual_edits = False
        self.sel = []           # cuadros elegidos en orden: (x0, y0, x1, y1); uno puede salir más de una vez
        self._strip_busy = False
        self.setWindowTitle(tr('🧩 Cortar hoja de sprites') + (f" — {slot_title}" if slot_title else ""))
        self.resize(1300, 820)
        lay = QHBoxLayout(self)
        split = QSplitter()
        lay.addWidget(split)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        ob = QPushButton(tr('📂 Abrir hoja…'))
        ob.clicked.connect(self.open_dialog)
        top.addWidget(ob)
        self.file_lbl = QLabel()
        self.file_lbl.setObjectName("CardPath")
        top.addWidget(self.file_lbl, 1)
        fit = QPushButton(tr('🔍 Ver toda'))
        fit.clicked.connect(self.fit)
        top.addWidget(fit)
        self.stretch = QPushButton(tr('↔ A lo ancho'))
        self.stretch.setCheckable(True)
        self.stretch.setToolTip(tr('La hoja ocupa todo el ancho de la zona de edición (sin deformarse); lo de abajo '
                                   'lo ves con la barra o con Ctrl + rueda. Se ajusta sola si cambias el tamaño de '
                                   'la ventana. Con la rueda (sola) vuelves al zoom libre.'))
        self.stretch.setChecked(bool(self.opts.get("stretch", False)))
        self.stretch.toggled.connect(self.on_stretch)
        top.addWidget(self.stretch)
        self.find_btn = QPushButton(tr('🔍 Buscar los que ya usé'))
        self.find_btn.setToolTip(tr('Compara cada cuadro de la hoja con los sprites que ya tienen tus casillas y '
                                    'marca los que son el mismo dibujo (sirve para lo que cortaste antes).'))
        self.find_btn.clicked.connect(lambda: self.find_used(auto=False))
        top.addWidget(self.find_btn)
        ll.addLayout(top)
        self.view = SheetView(self)
        ll.addWidget(self.view, 1)
        hint = QLabel(tr('🖱 Clic: elegir / quitar un cuadro · Ctrl+clic: repetirlo · Doble clic: toda la fila · Arrastrar: elegir varios '
                         '(con Alt: quitarlos) · Mayús + arrastrar: dibujar una caja a mano · Arrastrar con el '
                         'botón derecho: mover la hoja · Clic derecho: más opciones · Rueda: zoom · Mayús + rueda: a los lados · '
                         'Ctrl + rueda: arriba / abajo'))
        hint.setWordWrap(True)
        hint.setObjectName("CardPath")
        self.show_used = QCheckBox(tr('✓ Marcar los cuadros que ya usé en este personaje (en morado, con la casilla '
                                      'donde están)'))
        self.show_used.setChecked(bool(self.opts.get("show_used", True)))
        self.show_used.toggled.connect(lambda _on: self.view.viewport().update())
        ll.addWidget(self.show_used)
        ll.addWidget(hint)
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 0, 4, 0)
        if slot_title:
            t = QLabel(tr('Elige los cuadros de «{0}», en orden.').format(slot_title))
            t.setWordWrap(True)
            t.setObjectName("CardTitle")
            rl.addWidget(t)
        # fondo
        g = QGroupBox(tr('Fondo'))
        gl = QVBoxLayout(g)
        self.bg_mode = QComboBox()
        self.bg_mode.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.bg_mode.addItem(tr('Automático'), "auto")
        self.bg_mode.addItem(tr('La transparencia de la imagen'), "alpha")
        self.bg_mode.addItem(tr('Los colores de la lista'), "colors")
        gl.addWidget(self.bg_mode)
        self.bg_list = QListWidget()
        self.bg_list.setMaximumHeight(70)
        self.bg_list.setIconSize(QSize(16, 16))
        gl.addWidget(self.bg_list)
        row = QHBoxLayout()
        self.pick_btn = QPushButton(tr('🎯 Tomar color de la hoja'))
        self.pick_btn.setCheckable(True)
        self.pick_btn.toggled.connect(self.on_pick_toggle)
        rm = QPushButton(tr('✕ Quitar'))
        rm.clicked.connect(self.remove_color)
        row.addWidget(self.pick_btn)
        row.addWidget(rm)
        gl.addLayout(row)
        f = QFormLayout()
        self.tol = QSlider(Qt.Orientation.Horizontal)
        self.tol.setRange(0, 120)
        self.tol_lbl = QLabel()
        tr_row = QHBoxLayout()
        tr_row.addWidget(self.tol, 1)
        tr_row.addWidget(self.tol_lbl)
        f.addRow(tr('Tolerancia:'), tr_row)
        gl.addLayout(f)
        gl.addWidget(self._muted(tr('Sube la tolerancia si quedan bordes del fondo (imágenes JPG).')))
        rl.addWidget(g)
        # corte
        g = QGroupBox(tr('Corte'))
        gl = QVBoxLayout(g)
        mr = QHBoxLayout()
        self.m_auto = QRadioButton(tr('Automático'))
        self.m_grid = QRadioButton(tr('Cuadrícula'))
        bg = QButtonGroup(self)
        bg.addButton(self.m_auto)
        bg.addButton(self.m_grid)
        mr.addWidget(self.m_auto)
        mr.addWidget(self.m_grid)
        gl.addLayout(mr)
        self.auto_box = QWidget()
        af = QFormLayout(self.auto_box)
        af.setContentsMargins(0, 0, 0, 0)
        self.join = QSpinBox()
        self.join.setRange(0, 40)
        self.join.setSuffix(" px")
        self.attach = QCheckBox(tr('Pegar pedacitos sueltos a su sprite'))
        self.attach.setToolTip(tr('Pelo, chispas, gotas… que quedan separados del cuerpo se unen al sprite más '
                                  'cercano.'))
        self.min_area = QSpinBox()
        self.min_area.setRange(0, 5000)
        self.min_area.setSuffix(" px")
        af.addRow(tr('Unir piezas a menos de:'), self.join)
        af.addRow(self.attach)
        af.addRow(tr('Ignorar manchas de menos de:'), self.min_area)
        gl.addWidget(self.auto_box)
        self.grid_box = QWidget()
        gf = QGridLayout(self.grid_box)
        gf.setContentsMargins(0, 0, 0, 0)
        self.cell_w, self.cell_h, self.off_x, self.off_y, self.gap_x, self.gap_y = (QSpinBox() for _ in range(6))
        for sp in (self.cell_w, self.cell_h):
            sp.setRange(2, 4096)
        for sp in (self.off_x, self.off_y, self.gap_x, self.gap_y):
            sp.setRange(0, 4096)
        gf.addWidget(QLabel(tr('Celda (ancho × alto):')), 0, 0)
        gf.addWidget(self.cell_w, 0, 1)
        gf.addWidget(self.cell_h, 0, 2)
        gf.addWidget(QLabel(tr('Margen (x, y):')), 1, 0)
        gf.addWidget(self.off_x, 1, 1)
        gf.addWidget(self.off_y, 1, 2)
        gf.addWidget(QLabel(tr('Separación (x, y):')), 2, 0)
        gf.addWidget(self.gap_x, 2, 1)
        gf.addWidget(self.gap_y, 2, 2)
        gl.addWidget(self.grid_box)
        redo = QPushButton(tr('↺ Volver a cortar'))
        redo.setToolTip(tr('Vuelve a buscar los cuadros (se pierden los arreglos a mano).'))
        redo.clicked.connect(lambda: self.detect(force=True))
        gl.addWidget(redo)
        rl.addWidget(g)
        # selección
        g = QGroupBox(tr('Cuadros'))
        gl = QGridLayout(g)
        self.count_lbl = QLabel()
        gl.addWidget(self.count_lbl, 0, 0, 1, 2)
        for i, (txt, fn) in enumerate(((tr('✅ Todos'), self.select_all), (tr('⬜ Ninguno'), self.select_none),
                                       (tr('🔗 Unir elegidos'), self.merge_selected),
                                       (tr('🗑 Quitar elegidos'), self.remove_selected))):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            gl.addWidget(b, 1 + i // 2, i % 2)
        rl.addWidget(g)
        # vista previa
        g = QGroupBox(tr('Así se ve'))
        gl = QVBoxLayout(g)
        self.player = Player(self)
        gl.addWidget(self.player, 1)
        lab = QLabel(tr('Orden (arrastra para cambiarlo · Ctrl+clic en la hoja repite un cuadro):'))
        lab.setWordWrap(True)
        lab.setObjectName("CardPath")
        gl.addWidget(lab)
        self.strip = QListWidget()
        self.strip.setViewMode(QListWidget.ViewMode.IconMode)
        self.strip.setFlow(QListWidget.Flow.LeftToRight)
        self.strip.setWrapping(False)
        self.strip.setIconSize(QSize(44, 44))
        self.strip.setFixedHeight(84)
        self.strip.setMovement(QListWidget.Movement.Snap)
        self.strip.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.strip.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.strip.model().rowsMoved.connect(self.on_strip_moved)
        self.strip.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.strip.customContextMenuRequested.connect(self.strip_menu)
        gl.addWidget(self.strip)
        row = QHBoxLayout()
        for txt, tip, fn in ((tr('⧉ Repetir'), tr('Pone el cuadro marcado otra vez, justo después.'), self.strip_repeat),
                             ("◀", tr('Mover antes'), lambda: self.strip_move(-1)),
                             ("▶", tr('Mover después'), lambda: self.strip_move(1)),
                             (tr('✖ Quitar'), tr('Quita este cuadro de la animación (solo esta vez).'),
                              self.strip_remove)):
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        gl.addLayout(row)
        f = QFormLayout()
        self.axis = QComboBox()
        self.axis.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.axis.setMinimumContentsLength(14)
        for k, t in AXIS_LABELS:
            self.axis.addItem(tr(t), k)
        self.speed = QSpinBox()
        self.speed.setRange(1, 60)
        self.speed.setValue(6)
        self.speed.setSuffix(" " + tr('ticks'))
        f.addRow(tr('Pararlo en:'), self.axis)
        self.grow = QSpinBox()
        self.grow.setRange(25, 1000)
        self.grow.setSingleStep(25)
        self.grow.setSuffix(" %")
        self.grow.setToolTip(tr('Agranda los cuadros al cortarlos (sin ponerlos borrosos). Úsalo si la hoja es '
                                'muy chiquita para tu personaje: mejor que agrandarlo después con el tamaño.'))
        f.addRow(tr('Agrandar los cuadros:'), self.grow)
        self.mirror = QCheckBox(tr('↔ Voltear (espejo): para hojas que miran hacia la izquierda'))
        self.mirror.setToolTip(tr('El personaje tiene que mirar hacia la derecha. Si la hoja viene al revés, '
                                  'esto voltea cada cuadro al cortarlo.'))
        f.addRow("", self.mirror)
        f.addRow(tr('Rapidez de la prueba:'), self.speed)
        gl.addLayout(f)
        rl.addWidget(g, 1)
        # para el modo avanzado
        if advanced:
            g = QGroupBox(tr('Agregar al personaje'))
            f = QFormLayout(g)
            self.group = QSpinBox()
            self.group.setRange(0, 65535)
            self.group.setValue(start_group)
            self.per_row = QCheckBox(tr('Un grupo por cada fila (grupo, grupo+1…)'))
            self.per_row.setChecked(True)
            self.make_anims = QCheckBox(tr('Crear una animación con cada fila'))
            self.colors = QComboBox()
            self.colors.addItem(tr('Color verdadero de 32 bits (exacto)'), "rgba")
            self.colors.addItem(tr('Paleta propia de cada imagen'), "own")
            self.colors.addItem(tr('Pasar a la paleta del personaje'), "char")
            f.addRow(tr('Grupo:'), self.group)
            f.addRow(self.per_row)
            f.addRow(self.make_anims)
            f.addRow(tr('Colores:'), self.colors)
            rl.addWidget(g)
        bb = QHBoxLayout()
        self.ok_btn = QPushButton()
        self.ok_btn.setObjectName("primary")
        self.ok_btn.setMinimumHeight(36)
        self.ok_btn.clicked.connect(self.on_ok)
        cancel = QPushButton(tr('Cancelar'))
        cancel.clicked.connect(self.reject)
        bb.addWidget(cancel)
        bb.addWidget(self.ok_btn, 1)
        rl.addLayout(bb)
        sc_area = QScrollArea()
        sc_area.setWidgetResizable(True)
        sc_area.setFrameShape(QFrame.Shape.NoFrame)
        sc_area.setWidget(right)
        sc_area.setMinimumWidth(430)
        sc_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        split.addWidget(sc_area)
        split.setStretchFactor(0, 1)
        split.setSizes([850, 440])

        # valores guardados
        o = self.opts
        self.join.setValue(int(o.get("join", 2)))
        self.attach.setChecked(bool(o.get("attach", True)))
        self.min_area.setValue(int(o.get("min_area", 8)))
        self.axis.setCurrentIndex(max(0, self.axis.findData(o.get("axis", "ground"))))
        self.grow.setValue(int(o.get("grow", 100)))
        self.grow.valueChanged.connect(self.refresh_preview)
        self.mirror.setChecked(bool(o.get("mirror", False)))
        self.mirror.toggled.connect(self.refresh_preview)
        self.m_auto.setChecked(True)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.detect)
        for w in (self.join, self.min_area, self.cell_w, self.cell_h, self.off_x, self.off_y, self.gap_x, self.gap_y):
            w.valueChanged.connect(self.schedule)
        self.tol.valueChanged.connect(self.on_tol)
        self.attach.toggled.connect(self.schedule)
        self.m_auto.toggled.connect(self.on_mode)
        self.bg_mode.currentIndexChanged.connect(self.schedule)
        self.axis.currentIndexChanged.connect(self.refresh_preview)
        self.on_tol(self.tol.value())
        self.on_mode()
        self.update_count()
        last = st.get("sheet_last")
        if last and Path(last).is_file():
            QTimer.singleShot(0, lambda: self.load(last))

    def _muted(self, text):
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setObjectName("CardPath")
        return lab

    # ---- abrir
    def open_dialog(self):
        from ui.mainwindow import load_settings
        start = str(Path(self.path).parent) if self.path else load_settings().get("last_img_dir", str(Path.home()))
        f, _ = QFileDialog.getOpenFileName(self, tr('Abrir hoja de sprites'), start, tr(IMAGE_FILTER))
        if f:
            self.load(f)

    def load(self, path):
        from ui.mainwindow import save_settings
        path = str(path)
        if path not in _CACHE:
            img = QImage(path)
            if img.isNull():
                QMessageBox.warning(self, APP_NAME, tr('No pude abrir esa imagen.'))
                return
            img = img.convertToFormat(QImage.Format.Format_RGBA8888)
            _CACHE.clear()
            _CACHE[path] = (img, qimage_rgba(img))
        img, rgba = _CACHE[path]
        self.path = path
        self.rgba = rgba
        self.view.set_image(img)
        self.file_lbl.setText(f"{Path(path).name}  ·  {img.width()}×{img.height()}")
        save_settings({"sheet_last": path})
        alpha = sc.has_alpha(rgba)
        saved = (self.opts.get("bg") or {}).get(path)
        if saved:
            self.bg_colors = [tuple(c) for c in saved.get("colors", [])]
            mode = saved.get("mode", "auto")
            tol = int(saved.get("tol", 0))
        else:
            _a, self.bg_colors, tol = sc.auto_background(rgba)
            mode = "auto"
        self.auto_bg = (alpha, list(self.bg_colors))
        self.tol.blockSignals(True)
        self.tol.setValue(tol)
        self.tol_lbl.setText(str(tol))
        self.tol.blockSignals(False)
        self.bg_mode.blockSignals(True)
        self.bg_mode.setCurrentIndex(max(0, self.bg_mode.findData(mode)))
        self.bg_mode.blockSignals(False)
        self.fill_bg_list()
        self.detect(force=True)
        if not self.manual_edits:
            g = sc.guess_grid([b for b in self.boxes], rgba.shape)
            for sp, v in ((self.cell_w, g[0]), (self.cell_h, g[1])):
                sp.blockSignals(True)
                sp.setValue(v)
                sp.blockSignals(False)
        QTimer.singleShot(0, self.fit)
        # la primera vez que se abre una hoja sin marcas: buscar solo los cuadros que ya se usaron
        if self.used_store() is not None and not self.used_marks():
            QTimer.singleShot(80, lambda: self.find_used(auto=True))

    def fit(self):
        if self.view.pix_item is not None:
            r = self.view.pix_item.boundingRect()
            vw, vh = self.view.viewport().width(), self.view.viewport().height()
            z = min(vw / max(1, r.width()), vh / max(1, r.height()))
            if self.stretch.isChecked():
                # a lo ancho: la hoja ocupa todo el ancho de la zona de edición (sin deformarse);
                # si queda más alta que la zona, se baja con la rueda + Ctrl o la barra
                v = self.view
                if v.horizontalScrollBarPolicy() != Qt.ScrollBarPolicy.ScrollBarAlwaysOff:
                    v.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                    v.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
                    QApplication.processEvents()
                top = v.verticalScrollBar().value()
                v.set_zoom(max(0.1, v.viewport().width() / max(1, r.width()) * 0.995))
                v.horizontalScrollBar().setValue(v.horizontalScrollBar().minimum())
                v.centerOn(r.center().x(), r.top())
                if top and v.verticalScrollBar().maximum() > 0:
                    v.verticalScrollBar().setValue(min(top, v.verticalScrollBar().maximum()))
                return
            else:
                self.view.unstretch()
                self.view.set_zoom(max(0.1, min(4.0, z * 0.97)))
            self.view.centerOn(r.center())

    def on_stretch(self, on):
        self.opts["stretch"] = bool(on)
        self.fit()

    # ---- fondo
    def fill_bg_list(self):
        self.bg_list.clear()
        for c in self.bg_colors:
            it = QListWidgetItem(swatch(c), "#%02X%02X%02X" % tuple(c))
            self.bg_list.addItem(it)
        if self.rgba is not None and sc.has_alpha(self.rgba):
            it = QListWidgetItem(tr('(y lo transparente)'))
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.bg_list.addItem(it)

    def on_pick_toggle(self, on):
        self.view.picking = on
        self.view.setCursor(Qt.CursorShape.CrossCursor if on else Qt.CursorShape.ArrowCursor)

    def pick_color(self, x, y):
        if self.rgba is None:
            return
        h, w = self.rgba.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            c = tuple(int(v) for v in self.rgba[y, x, :3])
            if c not in self.bg_colors:
                self.bg_colors.append(c)
            self.bg_mode.blockSignals(True)
            self.bg_mode.setCurrentIndex(self.bg_mode.findData("colors"))
            self.bg_mode.blockSignals(False)
            self.fill_bg_list()
            self.detect(force=True)
        self.pick_btn.setChecked(False)

    def remove_color(self):
        r = self.bg_list.currentRow()
        if 0 <= r < len(self.bg_colors):
            del self.bg_colors[r]
            self.bg_mode.setCurrentIndex(self.bg_mode.findData("colors"))
            self.fill_bg_list()
            self.detect(force=True)

    def on_tol(self, v):
        self.tol_lbl.setText(str(v))
        self.schedule()

    def on_mode(self, *_a):
        grid = self.m_grid.isChecked()
        self.auto_box.setVisible(not grid)
        self.grid_box.setVisible(grid)
        self.schedule()

    # ---- cortar
    def schedule(self, *_a):
        if self.rgba is not None:
            self.timer.start()

    def detect(self, force=False):
        if self.rgba is None:
            return
        if self.manual_edits and not force:
            if QMessageBox.question(self, APP_NAME, tr('Volver a cortar borra los arreglos que hiciste a mano. '
                                                       '¿Seguir?')) != QMessageBox.StandardButton.Yes:
                return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            mode = self.bg_mode.currentData()
            alpha = sc.has_alpha(self.rgba)
            if mode == "alpha":
                use_alpha, colors = True, []
            elif mode == "colors":
                use_alpha, colors = alpha, list(self.bg_colors)
            else:
                use_alpha, colors = self.auto_bg
                if self.bg_colors != colors:
                    self.bg_colors = list(colors)
                    self.fill_bg_list()
            tol = self.tol.value()
            self.used_colors = list(colors)
            keep = {(b.x0, b.y0, b.x1, b.y1) for b in self.boxes if b.selected}
            if self.m_grid.isChecked():
                self.fg = sc.foreground(self.rgba, colors, tol, use_alpha)
                self.label = None
                self.boxes = sc.grid_boxes(self.fg, self.cell_w.value(), self.cell_h.value(), self.off_x.value(),
                                           self.off_y.value(), self.gap_x.value(), self.gap_y.value())
            else:
                self.boxes, self.label, self.fg = sc.detect(self.rgba, colors, tol, use_alpha, self.join.value(),
                                                            self.attach.isChecked(), self.min_area.value())
            for b in self.boxes:
                b.selected = (b.x0, b.y0, b.x1, b.y1) in keep
            self.crops = {}
            self.manual_edits = False
        finally:
            QApplication.restoreOverrideCursor()
        self.changed()

    def changed(self):
        self.reconcile()
        self.view.viewport().update()
        self.update_count()
        self.refresh_preview()

    @staticmethod
    def key_of(b):
        return (b.x0, b.y0, b.x1, b.y1)

    def reconcile(self):
        """Pone al día la lista en orden con lo elegido en la hoja: lo que se quitó sale (todas sus veces) y lo
        nuevo entra en su lugar según la hoja (así, sin repetir nada, el orden es el de siempre)."""
        by_key = {self.key_of(b): b for b in self.boxes}
        pos = {self.key_of(b): i for i, b in enumerate(self.boxes)}
        sel = [k for k in self.sel if k in by_key and by_key[k].selected]
        have = set(sel)
        for b in self.boxes:
            k = self.key_of(b)
            if b.selected and k not in have:
                at = next((j for j, o in enumerate(sel) if pos[o] > pos[k]), len(sel))
                sel.insert(at, k)
                have.add(k)
        self.sel = sel

    def sel_boxes(self):
        by_key = {self.key_of(b): b for b in self.boxes}
        return [by_key[k] for k in self.sel if k in by_key]

    def frame_ids(self):
        """Para cada cuadro de frames(): un número igual para los que son el mismo cuadro de la hoja
        (así un cuadro repetido se guarda una sola vez como sprite)."""
        ids = {}
        return [ids.setdefault(k, len(ids)) for k in self.sel]

    def repeat(self, b, after=None):
        """El mismo cuadro otra vez: al final, o justo después de la posición `after`."""
        if not b.selected:
            b.selected = True
            self.reconcile()
            if after is None:
                self.changed()
                return
        k = self.key_of(b)
        if after is None:
            self.sel.append(k)
        else:
            self.sel.insert(after + 1, k)
        self.changed()

    # ---- la tira con el orden
    def fill_strip(self, crops):
        self._strip_busy = True
        cur = self.strip.currentRow()
        self.strip.clear()
        for i, c in enumerate(crops):
            it = QListWidgetItem(str(i + 1))
            img = rgba_image(c)
            if not img.isNull():
                it.setIcon(QIcon(QPixmap.fromImage(img).scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                                                               Qt.TransformationMode.SmoothTransformation)))
            it.setData(Qt.ItemDataRole.UserRole, i)
            self.strip.addItem(it)
        if 0 <= cur < self.strip.count():
            self.strip.setCurrentRow(cur)
        self._strip_busy = False

    def on_strip_moved(self, *_a):
        if self._strip_busy:
            return
        old = list(self.sel)
        order = [self.strip.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.strip.count())]
        if sorted(order) == list(range(len(old))):
            self.sel = [old[i] for i in order]
            QTimer.singleShot(0, self.changed)

    def strip_repeat(self):
        r = self.strip.currentRow()
        if 0 <= r < len(self.sel):
            by_key = {self.key_of(b): b for b in self.boxes}
            b = by_key.get(self.sel[r])
            if b is not None:
                self.repeat(b, after=r)
                self.strip.setCurrentRow(r + 1)

    def strip_move(self, d):
        r = self.strip.currentRow()
        j = r + d
        if 0 <= r < len(self.sel) and 0 <= j < len(self.sel):
            self.sel[r], self.sel[j] = self.sel[j], self.sel[r]
            self.changed()
            self.strip.setCurrentRow(j)

    def strip_remove(self):
        r = self.strip.currentRow()
        if 0 <= r < len(self.sel):
            k = self.sel.pop(r)
            if k not in self.sel:
                for b in self.boxes:
                    if self.key_of(b) == k:
                        b.selected = False
            self.changed()
            self.strip.setCurrentRow(min(r, len(self.sel) - 1))

    def strip_menu(self, pos):
        it = self.strip.itemAt(pos)
        if it is None:
            return
        self.strip.setCurrentItem(it)
        m = QMenu(self)
        m.addAction(tr('⧉ Repetir'), self.strip_repeat)
        m.addAction(tr('✖ Quitar'), self.strip_remove)
        m.exec(self.strip.viewport().mapToGlobal(pos))

    def update_count(self):
        n = len(self.sel)
        rows = len({b.row for b in self.boxes})
        self.count_lbl.setText(tr('{0} cuadros en {1} fila(s) · {2} elegidos').format(len(self.boxes), rows, n))
        self.ok_btn.setText(tr('✔ Usar {0} cuadro(s)').format(n) if not self.advanced else
                            tr('✔ Agregar {0} sprite(s)').format(n))
        self.ok_btn.setEnabled(n > 0)

    # ---- elegir y arreglar
    def toggle(self, b):
        b.selected = not b.selected
        self.changed()

    def select_rect(self, r, add=True):
        for b in self.boxes:
            if r.intersects(QRectF(b.x0, b.y0, b.w, b.h)):
                b.selected = add
        self.changed()

    def select_row(self, row):
        lst = [b for b in self.boxes if b.row == row]
        on = not all(b.selected for b in lst)
        for b in lst:
            b.selected = on
        self.changed()

    def select_all(self):
        for b in self.boxes:
            b.selected = True
        self.changed()

    def select_none(self):
        for b in self.boxes:
            b.selected = False
        self.changed()

    def merge_selected(self):
        sel = [b for b in self.boxes if b.selected]
        if len(sel) < 2:
            QMessageBox.information(self, APP_NAME, tr('Elige dos o más cuadros para unirlos en uno.'))
            return
        self.boxes = sc.merge(self.boxes, sel)
        self.manual_edits = True
        self.crops = {}
        self.changed()

    def remove_selected(self):
        self.boxes = [b for b in self.boxes if not b.selected]
        self.manual_edits = True
        self.changed()

    def add_manual(self, a, b):
        if self.fg is None:
            return
        box = sc.manual_box(self.fg, a.x(), a.y(), b.x(), b.y())
        if box is None:
            return
        box.selected = True
        # lo que quede dentro de la caja nueva se quita (la reemplaza)
        self.boxes = [o for o in self.boxes if not box.contains(o, 0)] + [box]
        if all(o.cell is None for o in self.boxes):
            self.boxes = sc.order_rows(self.boxes)
        self.manual_edits = True
        self.changed()

    def context_menu(self, b, pos):
        m = QMenu(self)
        m.addAction(tr('Elegir / quitar este cuadro'), lambda: self.toggle(b))
        m.addAction(tr('⧉ Agregarlo otra vez (repetir)'), lambda: self.repeat(b))
        m.addAction(tr('Elegir toda la fila'), lambda: self.select_row(b.row))
        m.addAction(tr('🗑 Borrar esta caja'), lambda: self.delete_box(b))
        if any(self.overlaps(r, (b.x0, b.y0, b.x1, b.y1)) for r in self.used_groups()):
            m.addAction(tr('✖ Olvidar que ya lo usé'), lambda: self.forget_used(b))
        m.exec(pos)

    # ---- cuadros ya usados (se guardan en la configuración del modo simple del personaje)
    def used_store(self):
        sm = getattr(self.main, "simple", None)
        if sm is None or not getattr(self.main, "project", None):
            return None
        return sm.cfg.setdefault("sheet_used", {})

    def sheet_key(self):
        if not self.path or self.rgba is None:
            return None
        h, w = self.rgba.shape[:2]
        return f"{Path(self.path).name}|{w}x{h}"

    def used_marks(self):
        st = self.used_store()
        key = self.sheet_key()
        return list(st.get(key, [])) if (st is not None and key) else []

    def used_groups(self):
        out = {}
        for m in self.used_marks():
            r = tuple(int(v) for v in m.get("r", (0, 0, 0, 0)))
            names = out.setdefault(r, [])
            if m.get("slot") and m["slot"] not in names:
                names.append(m["slot"])
        return out

    @staticmethod
    def overlaps(a, b):
        """¿Dos rectángulos (x0, y0, x1, y1) son casi el mismo cuadro? (más de la mitad del más chico)"""
        ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
        iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
        small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])) or 1
        return ix * iy > 0.5 * small

    def record_used(self):
        """Al aceptar: los cuadros elegidos quedan marcados con el nombre de la casilla."""
        st = self.used_store()
        key = self.sheet_key()
        sel = [b for b in self.boxes if b.selected]
        if st is None or not key or not sel:
            return
        name = self.slot_title or tr('Sprites')
        marks = list(st.get(key, []))
        if self.slot_title:
            # la casilla se volvió a cortar: sus marcas viejas se cambian por las nuevas
            marks = [m for m in marks if m.get("slot") != name]
        for b in sel:
            r = [b.x0, b.y0, b.x1, b.y1]
            if not any(m.get("r") == r and m.get("slot") == name for m in marks):
                marks.append({"r": r, "slot": name})
        st[key] = marks
        self.main.simple.mark()

    def slot_sprites(self):
        """[(nombre de la casilla, [(grupo, número)…])] de todo lo que ya tiene el modo simple."""
        from core import simple_gen as sg
        cfg = self.main.simple.cfg
        out = []
        for k, e in (cfg.get("anims") or {}).items():
            fr = (e or {}).get("frames") or []
            if fr and k in sg.ANIM_SLOTS:
                out.append((tr(sg.ANIM_SLOTS[k][1]), fr))
        pos = {p: t for p, t, _n in sg.POSITIONS}
        for k, e in (cfg.get("normals") or {}).items():
            fr = (e or {}).get("frames") or []
            if fr:
                p, b = k.split("_")
                out.append((f"{tr(pos.get(p, p))}: {tr(sg.NORMAL_NAMES.get(b, b))}", fr))
        th = (cfg.get("throw") or {}).get("frames") or []
        if th:
            out.append((tr('Agarre'), th))
        for sp in cfg.get("specials") or []:
            name = sp.get("name") or tr('Especial')
            if sp.get("frames"):
                out.append((name, sp["frames"]))
            for key, extra in (("proj", tr('proyectil')), ("proj_hit", tr('al chocar'))):
                fr = (sp.get(key) or {}).get("frames") or []
                if fr:
                    out.append((f"{name} ({extra})", fr))
        return out

    @staticmethod
    def fingerprint(rgba):
        """Huella de un dibujo: forma (en 24×24), proporción y color promedio. None si está vacío."""
        a = rgba[:, :, 3] > 0
        if not a.any():
            return None
        ys, xs = np.where(a)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        m = a[y0:y1, x0:x1]
        h, w = m.shape
        iy = (np.arange(24) * h // 24).clip(0, h - 1)
        ix = (np.arange(24) * w // 24).clip(0, w - 1)
        small = m[iy][:, ix]
        col = rgba[y0:y1, x0:x1, :3][m].mean(axis=0)
        return w / h, small, col, w, h

    @staticmethod
    def same_drawing(a, b):
        if a is None or b is None:
            return False
        if abs(a[0] - b[0]) > 0.12 * max(a[0], b[0]):
            return False
        if (a[1] == b[1]).mean() < 0.9:
            return False
        return float(np.abs(a[2] - b[2]).max()) <= 30

    def find_used(self, auto=False):
        """Marca los cuadros de la hoja que ya están en alguna casilla (comparando los dibujos)."""
        st = self.used_store()
        key = self.sheet_key()
        if st is None or not key or not self.boxes:
            if not auto:
                QMessageBox.information(self, APP_NAME, tr('Abre un personaje y una hoja primero.'))
            return
        from ui.common import sprite_qimage
        p = self.main.project
        idx = p.sff.index()
        prints = []
        for name, frames in self.slot_sprites():
            for g, n in frames:
                s = idx.get((int(g), int(n)))
                if s is None:
                    continue
                try:
                    fp = self.fingerprint(qimage_rgba(sprite_qimage(p.sff, s)))
                except Exception:
                    fp = None
                if fp is not None:
                    prints.append((name, fp))
        if not prints:
            if not auto:
                QMessageBox.information(self, APP_NAME, tr('Tus casillas todavía no tienen sprites para comparar.'))
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        found = 0
        try:
            marks = list(st.get(key, []))
            for b in self.boxes:
                try:
                    fb = self.fingerprint(self.crop_of(b))
                except Exception:
                    continue
                r = [b.x0, b.y0, b.x1, b.y1]
                for name, fp in prints:
                    if self.same_drawing(fb, fp) and not any(m.get("r") == r and m.get("slot") == name
                                                             for m in marks):
                        marks.append({"r": r, "slot": name})
                        found += 1
            if found:
                st[key] = marks
                self.main.simple.mark()
        finally:
            QApplication.restoreOverrideCursor()
        self.view.viewport().update()
        if not auto:
            QMessageBox.information(self, APP_NAME, tr('Encontré {0} cuadro(s) que ya usaste.').format(found)
                                    if found else tr('No encontré cuadros de esta hoja en tus casillas.'))

    def forget_used(self, b):
        st = self.used_store()
        key = self.sheet_key()
        if st is None or not key:
            return
        box = (b.x0, b.y0, b.x1, b.y1)
        st[key] = [m for m in st.get(key, []) if not self.overlaps(tuple(m.get("r", (0, 0, 0, 0))), box)]
        if not st[key]:
            st.pop(key)
        self.main.simple.mark()
        self.view.viewport().update()

    def delete_box(self, b):
        self.boxes = [o for o in self.boxes if o is not b]
        self.manual_edits = True
        self.changed()

    # ---- resultado
    def crop_of(self, b):
        k = (b.x0, b.y0, b.x1, b.y1, tuple(sorted(b.labels)) if b.labels else None)
        if k not in self.crops:
            self.crops[k] = sc.crop(self.rgba, self.label, self.fg, b, self.used_colors, self.tol.value())
        return self.crops[k]

    def frames(self):
        """[(rgba, (eje_x, eje_y), fila)] de los cuadros elegidos, en orden."""
        sel = self.sel_boxes()
        crops = [self.crop_of(b) for b in sel]
        axes = sc.axes_for(sel, crops, self.axis.currentData())
        g = self.grow.value() / 100.0
        if g != 1:
            from core.rescale import scale_pixels
            crops = [scale_pixels(c, g) for c in crops]
            axes = [(int(round(ax * g)), int(round(ay * g))) for ax, ay in axes]
        if self.mirror.isChecked():
            # espejo: cada cuadro volteado de izquierda a derecha (y su eje también)
            axes = [(c.shape[1] - ax, ay) for c, (ax, ay) in zip(crops, axes)]
            crops = [np.ascontiguousarray(c[:, ::-1]) for c in crops]
        return [(c, a, b.row) for c, a, b in zip(crops, axes, sel)]

    def refresh_preview(self):
        if self.rgba is None:
            self.player.set_frames([])
            self.fill_strip([])
            return
        fr = self.frames()
        self.player.set_frames([(rgba_image(c), ax, ay) for c, (ax, ay), _r in fr])
        self.fill_strip([c for c, _a, _r in fr])

    def on_ok(self):
        from ui.mainwindow import save_settings
        o = self.opts
        o.update(join=self.join.value(), attach=self.attach.isChecked(), min_area=self.min_area.value(),
                 axis=self.axis.currentData(), grow=self.grow.value(), show_used=self.show_used.isChecked(),
                 mirror=self.mirror.isChecked())
        try:
            self.record_used()
        except Exception:
            pass
        if self.path:
            bgs = dict(o.get("bg") or {})
            bgs[self.path] = {"mode": self.bg_mode.currentData(), "colors": [list(c) for c in self.bg_colors],
                              "tol": self.tol.value()}
            o["bg"] = dict(list(bgs.items())[-20:])
        save_settings({"sheet_opts": o})
        self.accept()
