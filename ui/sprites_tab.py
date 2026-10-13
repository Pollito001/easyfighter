"""Pestaña Sprites: ver, ordenar, importar/exportar imágenes, ejes y paletas."""
import re
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QAbstractListModel, QModelIndex, QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QImage, QKeySequence, QPixmap, QUndoStack
from PyQt6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGraphicsPixmapItem, QGraphicsScene, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListView, QMessageBox, QPushButton, QRadioButton, QSpinBox, QSplitter, QToolBar,
    QVBoxLayout, QWidget,
)

from core.sff import Palette, Sprite, palette_from_rgb, read_act, write_act
from i18n import tr
from ui.common import APP_NAME, ZoomView, axis_pen, image_to_indices, run_with_progress, sprite_qimage
from ui.palette_widget import PaletteGrid
from ui.undo import FnCommand

NAME_RE = re.compile(r"(\d+)\s*[-_, ]\s*(\d+)\D*$")


# ---------------------------------------------------------------- lista (rápida: solo pide lo visible)
class SpriteModel(QAbstractListModel):
    def __init__(self, tab):
        super().__init__()
        self.tab = tab
        self.rows = []
        self.icons = {}

    def refresh(self, keep_icons=False):
        self.beginResetModel()
        sff = self.tab.sff()
        flt = self.tab.filter_text()
        self.rows = []
        for i, s in enumerate(sff.sprites if sff else []):
            if flt and not self._match(s, flt):
                continue
            self.rows.append(i)
        if not keep_icons:
            self.icons = {}
        self.endResetModel()

    @staticmethod
    def _match(s, flt):
        flt = flt.replace(" ", "")
        if "," in flt:
            g, _, n = flt.partition(",")
            return (not g or str(s.group) == g) and (not n or str(s.number) == n)
        return str(s.group).startswith(flt)

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def sprite(self, row):
        sff = self.tab.sff()
        if sff and 0 <= row < len(self.rows) and self.rows[row] < len(sff.sprites):
            return sff.sprites[self.rows[row]]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        s = self.sprite(index.row())
        if s is None:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            w, h = s.size()
            link = "  🔗" if s.link is not None else ""
            return f"{s.group}, {s.number}    {w}×{h}{link}"
        if role == Qt.ItemDataRole.DecorationRole:
            key = id(s)
            if key not in self.icons:
                img = sprite_qimage(self.tab.sff(), s, self.tab.override_palette())
                if img.isNull():
                    self.icons[key] = QIcon()
                else:
                    pm = QPixmap.fromImage(img.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                                      Qt.TransformationMode.FastTransformation))
                    self.icons[key] = QIcon(pm)
            return self.icons[key]
        if role == Qt.ItemDataRole.ToolTipRole:
            return tr('Grupo {0}, número {1} · eje {2},{3}').format(s.group, s.number, s.x, s.y)
        return None


# ---------------------------------------------------------------- vista del sprite (arrastrar = mover el eje)
class SpriteView(ZoomView):
    axisDragged = pyqtSignal(int, int, bool)  # dx, dy, terminado
    doubleClicked = pyqtSignal()

    def mouseDoubleClickEvent(self, e):
        self.doubleClicked.emit()

    def __init__(self, scene):
        super().__init__(scene)
        self._drag = None
        self._acc = (0, 0)
        self.setToolTip(tr('Rueda: zoom · Arrastrar: mover el sprite respecto a su eje · Flechas: mover 1 píxel'))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = self.mapToScene(e.position().toPoint())
            self._acc = (0, 0)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            p = self.mapToScene(e.position().toPoint())
            dx, dy = int(round(p.x() - self._drag.x())), int(round(p.y() - self._drag.y()))
            if dx or dy:
                self._drag = QPointF(self._drag.x() + dx, self._drag.y() + dy)
                self._acc = (self._acc[0] + dx, self._acc[1] + dy)
                self.axisDragged.emit(dx, dy, False)
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._drag is not None:
            self._drag = None
            self.axisDragged.emit(self._acc[0], self._acc[1], True)
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        moves = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if e.key() in moves:
            dx, dy = moves[e.key()]
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                dx, dy = dx * 10, dy * 10
            self.axisDragged.emit(dx, dy, False)
            self.axisDragged.emit(dx, dy, True)
            return
        super().keyPressEvent(e)


# ---------------------------------------------------------------- diálogo de importar
class ImportDialog(QDialog):
    def __init__(self, parent, files, sff, start_group):
        super().__init__(parent)
        self.setWindowTitle(tr('Agregar imágenes'))
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr('{0} imagen(es)').format(len(files))))
        form = QFormLayout()
        self.group = QSpinBox()
        self.group.setRange(0, 65535)
        self.group.setValue(start_group)
        self.number = QSpinBox()
        self.number.setRange(0, 65535)
        self.auto = QCheckBox(tr('Tomar grupo y número del nombre del archivo (p. ej. «200-3.png»)'))
        self.auto.setChecked(any(NAME_RE.search(Path(f).stem) for f in files))
        form.addRow(tr('Grupo:'), self.group)
        form.addRow(tr('Primer número:'), self.number)
        lay.addLayout(form)
        lay.addWidget(self.auto)
        free = 0
        while sff.find(start_group, free):
            free += 1
        self.number.setValue(free)
        box = QGroupBox(tr('Colores'))
        bl = QVBoxLayout(box)
        self.c_own = QRadioButton(tr('Paleta propia de la imagen (si ya es de 256 colores, se usa tal cual)'))
        self.c_char = QRadioButton(tr('Pasar a la paleta del personaje (cambia de color con las paletas)'))
        self.c_rgba = QRadioButton(tr('Color verdadero de 32 bits (solo IKEMEN GO; no cambia con las paletas)'))
        self.c_char.setChecked(True)
        for b in (self.c_own, self.c_char, self.c_rgba):
            bl.addWidget(b)
        lay.addWidget(box)
        self.corner = QCheckBox(tr('El color de la esquina superior izquierda es el transparente'))
        lay.addWidget(self.corner)
        box2 = QGroupBox(tr('Eje (punto de apoyo)'))
        b2 = QHBoxLayout(box2)
        self.ax_bottom = QRadioButton(tr('Abajo al centro (pies)'))
        self.ax_center = QRadioButton(tr('Centro'))
        self.ax_zero = QRadioButton(tr('Esquina (0,0)'))
        self.ax_bottom.setChecked(True)
        grp = QButtonGroup(self)
        for b in (self.ax_bottom, self.ax_center, self.ax_zero):
            grp.addButton(b)
            b2.addWidget(b)
        lay.addWidget(box2)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


# ---------------------------------------------------------------- pestaña
class SpritesTab(QWidget):
    modifiedChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.undo = QUndoStack(self)
        self.undo.cleanChanged.connect(self.modifiedChanged)
        self._block = False
        self.current = None
        lay = QVBoxLayout(self)
        tb = QToolBar()
        lay.addWidget(tb)

        def act(text, fn, key=None, tip=None):
            a = QAction(text, self)
            a.triggered.connect(fn)
            if key:
                a.setShortcut(key if isinstance(key, QKeySequence.StandardKey) else QKeySequence(key))
                a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            if tip:
                a.setToolTip(tip)
            tb.addAction(a)
            self.addAction(a)
            return a
        ua = act(tr('↶'), self.undo.undo, QKeySequence.StandardKey.Undo)
        ra = act(tr('↷'), self.undo.redo, QKeySequence.StandardKey.Redo)
        ua.setEnabled(False)
        ra.setEnabled(False)
        self.undo.canUndoChanged.connect(ua.setEnabled)
        self.undo.canRedoChanged.connect(ra.setEnabled)
        tb.addSeparator()
        act(tr('➕ Agregar imágenes…'), self.add_images, "Ins")
        act(tr('🧩 Cortar hoja…'), self.cut_sheet, None,
            tr('Corta los cuadros de una hoja de sprites (sprite sheet) y los agrega'))
        act(tr('🖌 Editar píxeles'), self.edit_pixels, "Ctrl+E", tr('Lápiz, relleno, selección… (también con doble clic en el sprite)'))
        act(tr('🔁 Reemplazar imagen…'), self.replace_image)
        act(tr('💾 Exportar PNG…'), self.export_png)
        act(tr('📤 Exportar todos…'), self.export_all)
        tb.addSeparator()
        act(tr('📋 Duplicar'), self.duplicate, "Ctrl+D")
        act(tr('🗑 Borrar'), self.delete, "Del")
        act(tr('✂ Recortar bordes'), self.crop, None, tr('Quita el espacio transparente alrededor sin mover la imagen'))
        act(tr('↕ Ordenar'), self.sort_sprites, None, tr('Ordena por grupo y número'))
        from PyQt6.QtWidgets import QMenu, QToolButton
        batch = QToolButton()
        batch.setText(tr('🧰 En lote'))
        batch.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        bm = QMenu(batch)
        bm.addAction(tr('Eje de los seleccionados…'), self.batch_axis)
        bm.addAction(tr('Paleta de los seleccionados…'), self.batch_palette)
        bm.addAction(tr('Renumerar los seleccionados…'), self.batch_renumber)
        bm.addAction(tr('Exportar los seleccionados…'), self.export_selected)
        batch.setMenu(bm)
        tb.addWidget(batch)
        tb.addSeparator()
        split = QSplitter()
        lay.addWidget(split, 1)
        # izquierda: lista
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr('Filtrar: grupo o «grupo,número»'))
        self.filter.textChanged.connect(lambda _t: self.model.refresh(True))
        ll.addWidget(self.filter)
        self.model = SpriteModel(self)
        self.list = QListView()
        self.list.setModel(self.model)
        self.list.setUniformItemSizes(True)
        self.list.setIconSize(QSize(40, 40))
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.selectionModel().currentChanged.connect(lambda cur, _p: self.show_sprite(self.model.sprite(cur.row())))
        ll.addWidget(self.list, 1)
        self.count = QLabel()
        ll.addWidget(self.count)
        split.addWidget(left)
        # centro: vista
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        self.scene = QGraphicsScene()
        self.view = SpriteView(self.scene)
        self.view.axisDragged.connect(self.on_axis_drag)
        self.view.doubleClicked.connect(self.edit_pixels)
        cl.addWidget(self.view, 1)
        row = QHBoxLayout()
        self.onion = QComboBox()
        self.onion.addItem(tr('Sin sprite de referencia'), None)
        self.onion.addItem(tr('Referencia: 0,0 (parado)'), (0, 0))
        self.onion.addItem(tr('Referencia: sprite anterior'), "prev")
        self.onion.currentIndexChanged.connect(lambda _i: self.redraw())
        row.addWidget(self.onion)
        from ui.backgrounds import BackdropPicker
        self.bg_picker = BackdropPicker(main)
        self.zoom_lbl = QLabel()
        self.view.zoomChanged.connect(lambda z: self.zoom_lbl.setText(f"{z * 100:.0f}%"))
        row.addStretch(1)
        row.addWidget(self.zoom_lbl)
        for txt, z in (("1:1", 1), ("2×", 2), ("4×", 4)):
            b = QPushButton(txt)
            b.clicked.connect(lambda _c, z=z: self.view.set_zoom(z))
            row.addWidget(b)
        cl.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(self.bg_picker)
        row2.addStretch(1)
        cl.addLayout(row2)
        split.addWidget(center)
        # derecha: propiedades y paleta
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        g = QGroupBox(tr('Sprite'))
        f = QFormLayout(g)
        self.sp_group = QSpinBox()
        self.sp_group.setRange(0, 65535)
        self.sp_number = QSpinBox()
        self.sp_number.setRange(0, 65535)
        self.sp_x = QSpinBox()
        self.sp_x.setRange(-32768, 32767)
        self.sp_y = QSpinBox()
        self.sp_y.setRange(-32768, 32767)
        self.sp_group.editingFinished.connect(self.on_rename)
        self.sp_number.editingFinished.connect(self.on_rename)
        self.sp_x.valueChanged.connect(self.on_axis_spin)
        self.sp_y.valueChanged.connect(self.on_axis_spin)
        f.addRow(tr('Grupo:'), self.sp_group)
        f.addRow(tr('Número:'), self.sp_number)
        f.addRow(tr('Eje X:'), self.sp_x)
        f.addRow(tr('Eje Y:'), self.sp_y)
        self.sp_info = QLabel()
        self.sp_info.setWordWrap(True)
        f.addRow(self.sp_info)
        self.sp_pal = QComboBox()
        self.sp_pal.setToolTip(tr('Paleta guardada en el SFF que usa este sprite. La 1,1 es la del personaje.'))
        self.sp_pal.activated.connect(self.on_sprite_palette)
        f.addRow(tr('Su paleta:'), self.sp_pal)
        rl.addWidget(g)
        g2 = QGroupBox(tr('Paleta'))
        v2 = QVBoxLayout(g2)
        self.view_pal = QComboBox()
        self.view_pal.setToolTip(tr('Con qué paleta del personaje se ve (como al elegir color en la selección)'))
        self.view_pal.currentIndexChanged.connect(self.on_view_palette)
        v2.addWidget(self.view_pal)
        self.grid = PaletteGrid()
        self.grid.edited.connect(self.on_color_edited)
        v2.addWidget(self.grid, 1)
        self.used_only = QCheckBox(tr('Oscurecer colores que este sprite no usa'))
        self.used_only.toggled.connect(lambda _c: self.update_grid())
        v2.addWidget(self.used_only)
        pr = QHBoxLayout()
        for txt, fn in ((tr('Abrir .act…'), self.load_act), (tr('Guardar .act…'), self.save_act),
                        (tr('➕ Nueva paleta'), self.new_palette)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            pr.addWidget(b)
        v2.addLayout(pr)
        rl.addWidget(g2, 1)
        split.addWidget(right)
        split.setSizes([260, 700, 300])

    # ---- datos
    def project(self):
        return self.main.project

    def sff(self):
        p = self.project()
        return p.sff if p else None

    def filter_text(self):
        return self.filter.text().strip()

    def override_palette(self):
        d = self.view_pal.currentData()
        return d if isinstance(d, Palette) else None

    def is_modified(self):
        p = self.project()
        return bool(p and p.sff_loaded() and (p.sff.modified or not self.undo.isClean()))

    def load(self):
        self.undo.clear()
        self._block = True
        self.view_pal.clear()
        p = self.project()
        if p:
            for n, name, pal in p.char_palettes():
                self.view_pal.addItem(tr('Paleta {0}  ({1})').format(n, name) if pal else
                                      tr('Paleta {0}  ({1}, no se encontró)').format(n, name), pal)
        if self.view_pal.count() == 0:
            self.view_pal.addItem(tr('Paleta del SFF'), None)
        self._block = False
        self.fill_sprite_palettes()
        self.model.refresh()
        self.update_count()
        if self.model.rowCount():
            self.list.setCurrentIndex(self.model.index(0))
        else:
            self.show_sprite(None)
        self.view.set_zoom(2)

    def fill_sprite_palettes(self):
        self.sp_pal.clear()
        sff = self.sff()
        if not sff:
            return
        for i, p in enumerate(sff.palettes):
            self.sp_pal.addItem(f"{i}:  {p.group},{p.number}", i)

    def update_count(self):
        sff = self.sff()
        self.count.setText(tr('{0} sprites · {1} paletas').format(len(sff.sprites), len(sff.palettes)) if sff else "")

    def changed(self, refresh_list=False):
        self.modifiedChanged.emit()
        if refresh_list:
            self.model.refresh(True)
            self.update_count()
        self.redraw()

    def push(self, text, redo, undo, refresh_list=False):
        self.undo.push(FnCommand(text, redo, undo, after=lambda: self.after_undo(refresh_list)))

    def after_undo(self, refresh_list):
        if refresh_list:
            self.model.icons = {}
            self.model.refresh(True)
            self.update_count()
        self.show_sprite(self.current, keep_view=True)
        self.modifiedChanged.emit()

    # ---- mostrar
    def show_sprite(self, s, keep_view=False):
        self.current = s
        self._block = True
        on = s is not None
        for w in (self.sp_group, self.sp_number, self.sp_x, self.sp_y, self.sp_pal):
            w.setEnabled(on)
        if on:
            self.sp_group.setValue(s.group)
            self.sp_number.setValue(s.number)
            self.sp_x.setValue(s.x)
            self.sp_y.setValue(s.y)
            w, h = s.size()
            b = s.base()
            info = [tr('Tamaño: {0}×{1}').format(w, h),
                    tr('Color verdadero (32 bits)') if b.depth == 32 else tr('256 colores')]
            if s.link is not None:
                info.append(tr('Comparte imagen con {0},{1}').format(s.link.group, s.link.number))
            self.sp_info.setText(" · ".join(info))
            self.sp_pal.setCurrentIndex(max(0, min(b.palidx, self.sp_pal.count() - 1)))
        else:
            self.sp_info.setText("")
        self._block = False
        self.redraw(keep_view)
        self.update_grid()

    def redraw(self, keep_view=True):
        self.scene.clear()
        s = self.current
        sff = self.sff()
        lim = 400
        if s is not None and sff is not None:
            ref = self.onion.currentData()
            r = None
            if ref == "prev":
                i = sff.sprites.index(s) if s in sff.sprites else -1
                r = sff.sprites[i - 1] if i > 0 else None
            elif ref:
                r = sff.find(*ref)
            if r is not None and r is not s:
                img = sprite_qimage(sff, r, self.override_palette())
                if not img.isNull():
                    it = QGraphicsPixmapItem(QPixmap.fromImage(img))
                    it.setOffset(-r.x, -r.y)
                    it.setOpacity(0.35)
                    self.scene.addItem(it)
            img = sprite_qimage(sff, s, self.override_palette())
            if not img.isNull():
                it = QGraphicsPixmapItem(QPixmap.fromImage(img))
                it.setOffset(-s.x, -s.y)
                self.scene.addItem(it)
                lim = max(lim, img.width() + abs(s.x) + 50, img.height() + abs(s.y) + 50)
        pen = axis_pen()
        self.scene.addLine(-lim, 0, lim, 0, pen)
        self.scene.addLine(0, -lim, 0, lim, pen)
        self.scene.setSceneRect(-lim, -lim, lim * 2, lim * 2)
        if not keep_view:
            self.view.centerOn(0, -40)

    def update_grid(self):
        s = self.current
        sff = self.sff()
        if sff is None:
            self.grid.set_palette(None)
            return
        pal = self.override_palette() if (s is None or s.base().palidx == 0) else None
        if pal is None:
            pal = sff.palette_for(s) if s is not None else sff.palettes[0]
        used = None
        if self.used_only.isChecked() and s is not None and s.base().depth == 8:
            used = np.zeros(256, bool)
            used[np.unique(s.pixels())] = True
        self.grid.set_palette(pal, used)

    # ---- eventos de edición
    def on_axis_drag(self, dx, dy, done):
        s = self.current
        if s is None:
            return
        if not done:
            s.x -= dx
            s.y -= dy
            self._block = True
            self.sp_x.setValue(s.x)
            self.sp_y.setValue(s.y)
            self._block = False
            self.redraw()
            return
        if dx or dy:
            nx, ny = s.x, s.y
            ox, oy = nx + dx, ny + dy
            self.push(tr('Mover eje'), lambda: (setattr(s, "x", nx), setattr(s, "y", ny)),
                      lambda: (setattr(s, "x", ox), setattr(s, "y", oy)))

    def on_axis_spin(self):
        s = self.current
        if self._block or s is None:
            return
        nx, ny, ox, oy = self.sp_x.value(), self.sp_y.value(), s.x, s.y
        if (nx, ny) != (ox, oy):
            self.push(tr('Cambiar eje'), lambda: (setattr(s, "x", nx), setattr(s, "y", ny)),
                      lambda: (setattr(s, "x", ox), setattr(s, "y", oy)))

    def on_rename(self):
        s = self.current
        if self._block or s is None:
            return
        g, n = self.sp_group.value(), self.sp_number.value()
        if (g, n) == s.key:
            return
        other = self.sff().find(g, n)
        if other is not None and other is not s:
            QMessageBox.warning(self, APP_NAME, tr('Ya hay un sprite {0},{1}.').format(g, n))
            self._block = True
            self.sp_group.setValue(s.group)
            self.sp_number.setValue(s.number)
            self._block = False
            return
        og, on = s.group, s.number
        self.push(tr('Renumerar sprite'), lambda: (setattr(s, "group", g), setattr(s, "number", n)),
                  lambda: (setattr(s, "group", og), setattr(s, "number", on)), refresh_list=True)

    def on_sprite_palette(self, _i):
        s = self.current
        if self._block or s is None:
            return
        b = s.base()
        new, old = self.sp_pal.currentData(), b.palidx
        if new != old:
            self.push(tr('Cambiar paleta del sprite'), lambda: setattr(b, "palidx", new),
                      lambda: setattr(b, "palidx", old), refresh_list=True)

    def on_view_palette(self, _i):
        if self._block:
            return
        self.model.icons = {}
        self.list.viewport().update()
        self.redraw()
        self.update_grid()

    def on_color_edited(self, i):
        pal = self.grid.palette
        sff = self.sff()
        # quien sea dueño de la paleta queda modificado
        if pal is not None and any(pal is p for p in sff.palettes):
            sff.modified = True
        else:
            self.main.act_modified(pal)
        self.model.icons = {}
        self.list.viewport().update()
        self.redraw()
        self.modifiedChanged.emit()

    # ---- selección
    def selected(self):
        rows = sorted({i.row() for i in self.list.selectionModel().selectedIndexes()})
        out = [self.model.sprite(r) for r in rows]
        out = [s for s in out if s is not None]
        if not out and self.current is not None:
            out = [self.current]
        return out

    def select(self, sprite):
        sff = self.sff()
        if sprite is None or sprite not in sff.sprites:
            return
        i = sff.sprites.index(sprite)
        if i in self.model.rows:
            idx = self.model.index(self.model.rows.index(i))
            self.list.setCurrentIndex(idx)
            self.list.scrollTo(idx)

    # ---- acciones
    def add_images(self):
        if not self.require():
            return
        files, _ = QFileDialog.getOpenFileNames(self, tr('Agregar imágenes'), str(self.project().folder),
                                                tr('Imágenes (*.png *.bmp *.gif *.pcx *.jpg *.jpeg *.tga *.webp)'))
        if not files:
            return
        sff = self.sff()
        start_group = self.current.group if self.current else 0
        dlg = ImportDialog(self, files, sff, start_group)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        axes = {}
        axes_file = Path(files[0]).parent / "axes.txt"
        if axes_file.exists():
            for ln in axes_file.read_text(errors="replace").splitlines():
                p = [x.strip() for x in ln.split(",")]
                if len(p) >= 4:
                    try:
                        axes[(int(p[0]), int(p[1]))] = (int(p[2]), int(p[3]))
                    except ValueError:
                        pass
        created = []
        number = dlg.number.value()
        char_pal = (self.override_palette() or sff.palettes[0]).colors[:, :3]
        for fpath in files:
            img = QImage(fpath)
            if img.isNull():
                continue
            if dlg.auto.isChecked() and NAME_RE.search(Path(fpath).stem):
                m = NAME_RE.search(Path(fpath).stem)
                g, n = int(m.group(1)), int(m.group(2))
            else:
                g, n = dlg.group.value(), number
                while sff.find(g, n) or any(c.key == (g, n) for c in created):
                    n += 1
                number = n + 1
            corner = None
            if dlg.corner.isChecked():
                c = img.pixel(0, 0)
                corner = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
            s = Sprite(g, n)
            if dlg.c_rgba.isChecked():
                from core.sff import qimage_rgba
                rgba = qimage_rgba(img)
                if corner is not None:
                    rgba[np.all(rgba[:, :, :3] == np.array(corner, np.uint8), axis=2), 3] = 0
                s.set_pixels(rgba)
            elif dlg.c_char.isChecked():
                idx, _rgb = image_to_indices(img, char_pal, corner)
                s.set_pixels(idx)
                s.palidx = 0
            else:
                idx, rgb = image_to_indices(img, None, corner)
                s.set_pixels(idx)
                s.palidx = self._palette_slot(rgb)
            h, w = s.pixels().shape[:2]
            if (g, n) in axes:
                s.x, s.y = axes[(g, n)]
            elif dlg.ax_bottom.isChecked():
                s.x, s.y = w // 2, h
            elif dlg.ax_center.isChecked():
                s.x, s.y = w // 2, h // 2
            created.append(s)
        if not created:
            return
        replaced = {}
        for s in created:
            old = sff.find(*s.key)
            if old is not None:
                replaced[s.key] = old
        if replaced and QMessageBox.question(
                self, APP_NAME, tr('{0} sprite(s) ya existen con ese grupo y número. ¿Reemplazarlos?').format(
                    len(replaced))) != QMessageBox.StandardButton.Yes:
            created = [s for s in created if s.key not in replaced]
            replaced = {}
        before = list(sff.sprites)

        def redo():
            lst = [x for x in before if x.key not in replaced or x is not replaced[x.key]]
            sff.sprites[:] = lst + created
        self.push(tr('Agregar imágenes'), redo, lambda: sff.sprites.__setitem__(slice(None), before), refresh_list=True)
        self.fill_sprite_palettes()
        self.select(created[0])

    def cut_sheet(self):
        if not self.require():
            return
        from ui.sheet_cutter import SheetCutter, rgba_image
        sff = self.sff()
        start = self.current.group if self.current else 0
        dlg = SheetCutter(self.main, advanced=True, start_group=start)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        frames = dlg.frames()
        if not frames:
            return
        base = dlg.group.value()
        per_row = dlg.per_row.isChecked()
        mode = dlg.colors.currentData()
        rows = []
        for _c, _a, r in frames:
            if r not in rows:
                rows.append(r)
        char_pal = (self.override_palette() or sff.palettes[0]).colors[:, :3] if sff.palettes else None
        created = []
        by_group = {}
        ids = dlg.frame_ids()
        made = {}               # cuadro repetido → el mismo sprite (se guarda una sola vez)
        for fid, (rgba, (ax, ay), r) in zip(ids, frames):
            g = base + (rows.index(r) if per_row else 0)
            if fid in made:
                by_group.setdefault(g, []).append(made[fid])
                continue
            n = 0
            while sff.find(g, n) or any(c.key == (g, n) for c in created):
                n += 1
            s = Sprite(g, n)
            if mode == "char" and char_pal is not None:
                idx, _rgb = image_to_indices(rgba_image(rgba), char_pal, None)
                s.set_pixels(idx)
                s.palidx = 0
            elif mode == "own":
                idx, rgb = image_to_indices(rgba_image(rgba), None, None)
                s.set_pixels(idx)
                s.palidx = self._palette_slot(rgb)
            else:
                s.set_pixels(np.ascontiguousarray(rgba))
            s.x, s.y = int(ax), int(ay)
            created.append(s)
            made[fid] = s
            by_group.setdefault(g, []).append(s)
        before = list(sff.sprites)

        def redo():
            sff.sprites[:] = before + created
        self.push(tr('Cortar hoja'), redo, lambda: sff.sprites.__setitem__(slice(None), before), refresh_list=True)
        self.fill_sprite_palettes()
        self.select(created[0])
        if dlg.make_anims.isChecked():
            from core.simple_gen import make_action
            air = self.project().air
            idx = {s.key: s for s in created}
            used = {a.number for a in air.actions}
            new = []
            for g, lst in by_group.items():
                num = g
                while num in used:
                    num += 1
                used.add(num)
                new.append(make_action(num, tr('Hoja de sprites: grupo {0}').format(g), [s.key for s in lst],
                                       dlg.speed.value(), "loop", idx))
            self.main.anims.edit_list(tr('Cortar hoja'), sorted(air.actions + new, key=lambda a: a.number), new[0])
            QMessageBox.information(self, APP_NAME, tr('✅ {0} sprite(s) agregados y {1} animación(es) creadas '
                                                       '(míralas en Animaciones).').format(len(created), len(new)))

    def _palette_slot(self, rgb):
        """Índice de una paleta del SFF con estos colores (la crea si no existe)."""
        sff = self.sff()
        for i, p in enumerate(sff.palettes):
            if np.array_equal(p.colors[:len(rgb), :3][:256], np.array(rgb, np.uint8)[:len(p.colors)]):
                return i
        nums = {p.number for p in sff.palettes if p.group == 2}
        n = 1
        while n in nums:
            n += 1
        sff.palettes.append(palette_from_rgb(rgb, 2, n))
        sff.modified = True
        return len(sff.palettes) - 1

    def edit_pixels(self):
        s = self.current
        if s is None:
            return
        from ui.pixel_editor import PixelEditor
        sff = self.sff()
        b = s.base()
        pal = (self.override_palette() if b.palidx == 0 else None) or sff.palette_for(s)
        dlg = PixelEditor(self, s.pixels(), pal, (s.x, s.y))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_pix, (nx, ny) = dlg.result_data()
        old_state = (s._pix, s._raw, s._decoder, s.link, s.w, s.h, s.depth, s.x, s.y, s.palidx)
        palidx = b.palidx

        def redo():
            s.set_pixels(new_pix)
            s.palidx = palidx
            s.x, s.y = nx, ny

        def undo():
            s._pix, s._raw, s._decoder, s.link, s.w, s.h, s.depth, s.x, s.y, s.palidx = old_state
        self.push(tr('Editar píxeles'), redo, undo, refresh_list=True)

    def replace_image(self):
        s = self.current
        if s is None:
            return
        fpath, _ = QFileDialog.getOpenFileName(self, tr('Reemplazar imagen'), str(self.project().folder),
                                               tr('Imágenes (*.png *.bmp *.gif *.pcx *.jpg *.jpeg *.tga *.webp)'))
        if not fpath:
            return
        img = QImage(fpath)
        if img.isNull():
            return
        sff = self.sff()
        b = s.base()
        if b.depth == 32:
            from core.sff import qimage_rgba
            new_pix = qimage_rgba(img)
        else:
            pal = (self.override_palette() if b.palidx == 0 else None) or sff.palette_for(s)
            if img.format() == QImage.Format.Format_Indexed8 and QMessageBox.question(
                    self, APP_NAME, tr('La imagen ya es de 256 colores. ¿Usar sus índices tal cual '
                                       '(recomendado si la exportaste de aquí)?')) == QMessageBox.StandardButton.Yes:
                from core.sff import qimage_indices
                new_pix = qimage_indices(img)
            else:
                new_pix, _rgb = image_to_indices(img, pal.colors[:, :3])
        old_state = (s._pix, s._raw, s._decoder, s.link, s.w, s.h, s.depth)

        def redo():
            pal = s.base().palidx
            s.set_pixels(new_pix)
            s.palidx = pal

        def undo():
            s._pix, s._raw, s._decoder, s.link, s.w, s.h, s.depth = old_state
        self.push(tr('Reemplazar imagen'), redo, undo, refresh_list=True)

    def export_png(self):
        s = self.current
        if s is None:
            return
        fpath, _ = QFileDialog.getSaveFileName(self, tr('Exportar PNG'),
                                               str(self.project().folder / f"{s.group}-{s.number}.png"), "PNG (*.png)")
        if fpath:
            sprite_qimage(self.sff(), s, self.override_palette()).save(fpath, "PNG")

    def export_all(self):
        sff = self.sff()
        if not sff or not sff.sprites:
            return
        folder = QFileDialog.getExistingDirectory(self, tr('Carpeta para exportar'), str(self.project().folder))
        if not folder:
            return
        folder = Path(folder)
        pal = self.override_palette()
        sprites = list(sff.sprites)

        def work(step):
            lines = []
            for i, s in enumerate(sprites):
                if i % 20 == 0:
                    step(tr('Exportando {0}/{1}…').format(i + 1, len(sprites)), i / len(sprites))
                img = sprite_qimage(sff, s, pal)
                if not img.isNull():
                    img.save(str(folder / f"{s.group}-{s.number}.png"), "PNG")
                lines.append(f"{s.group},{s.number},{s.x},{s.y}")
            (folder / "axes.txt").write_text("\n".join(lines) + "\n")
            return len(sprites)
        n, cancelled = run_with_progress(self, tr('Exportando sprites…'), work)
        if not cancelled and n:
            QMessageBox.information(self, APP_NAME, tr('✅ {0} sprites exportados. «axes.txt» guarda los ejes: si '
                                                       'vuelves a agregar esas imágenes, se respetan.').format(n))

    # ---- en lote
    def _form_dialog(self, title, rows):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        f = QFormLayout(dlg)
        for label, w in rows:
            if label:
                f.addRow(label, w)
            else:
                f.addRow(w)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        return dlg.exec() == QDialog.DialogCode.Accepted

    def batch_axis(self):
        sel = self.selected()
        if not sel:
            return
        mode = QComboBox()
        mode.addItem(tr('Mover el eje (sumar)'), "add")
        mode.addItem(tr('Poner este eje exacto'), "set")
        mode.addItem(tr('Abajo al centro de cada imagen'), "feet")
        mode.addItem(tr('Centro de cada imagen'), "center")
        x, y = QSpinBox(), QSpinBox()
        for s in (x, y):
            s.setRange(-32768, 32767)
        if not self._form_dialog(tr('Eje de {0} sprite(s)').format(len(sel)),
                                 [(tr('Cómo:'), mode), (tr('X:'), x), (tr('Y:'), y)]):
            return
        m, vx, vy = mode.currentData(), x.value(), y.value()
        old = [(s, s.x, s.y) for s in sel]
        new = []
        for s in sel:
            w, h = s.size()
            if m == "add":
                new.append((s, s.x + vx, s.y + vy))
            elif m == "set":
                new.append((s, vx, vy))
            elif m == "feet":
                new.append((s, w // 2, h))
            else:
                new.append((s, w // 2, h // 2))

        def apply(vals):
            for s, a, b in vals:
                s.x, s.y = a, b
        self.push(tr('Eje en lote'), lambda: apply(new), lambda: apply(old))

    def batch_palette(self):
        sel = self.selected()
        sff = self.sff()
        if not sel or not sff:
            return
        box = QComboBox()
        for i, p in enumerate(sff.palettes):
            box.addItem(f"{i}:  {p.group},{p.number}", i)
        if not self._form_dialog(tr('Paleta de {0} sprite(s)').format(len(sel)), [(tr('Paleta:'), box)]):
            return
        new = box.currentData()
        old = [(s.base(), s.base().palidx) for s in sel]

        def redo():
            for b, _o in old:
                b.palidx = new

        def undo():
            for b, o in old:
                b.palidx = o
        self.push(tr('Paleta en lote'), redo, undo, refresh_list=True)

    def batch_renumber(self):
        sel = self.selected()
        sff = self.sff()
        if not sel:
            return
        g, n = QSpinBox(), QSpinBox()
        for s in (g, n):
            s.setRange(0, 65535)
        g.setValue(sel[0].group)
        n.setValue(sel[0].number)
        if not self._form_dialog(tr('Renumerar {0} sprite(s)').format(len(sel)),
                                 [(tr('Grupo:'), g), (tr('Desde el número:'), n)]):
            return
        targets = [(g.value(), n.value() + i) for i in range(len(sel))]
        others = {s.key for s in sff.sprites if s not in sel}
        clash = [t for t in targets if t in others]
        if clash:
            QMessageBox.warning(self, APP_NAME, tr('Ya hay sprites con esos números (p. ej. {0},{1}).').format(*clash[0]))
            return
        old = [(s, s.group, s.number) for s in sel]
        new = [(s, a, b) for s, (a, b) in zip(sel, targets)]

        def apply(vals):
            for s, a, b in vals:
                s.group, s.number = a, b
        self.push(tr('Renumerar en lote'), lambda: apply(new), lambda: apply(old), refresh_list=True)

    def export_selected(self):
        sel = self.selected()
        if not sel:
            return
        folder = QFileDialog.getExistingDirectory(self, tr('Carpeta para exportar'), str(self.project().folder))
        if not folder:
            return
        lines = []
        for s in sel:
            img = sprite_qimage(self.sff(), s, self.override_palette())
            if not img.isNull():
                img.save(str(Path(folder) / f"{s.group}-{s.number}.png"), "PNG")
            lines.append(f"{s.group},{s.number},{s.x},{s.y}")
        (Path(folder) / "axes.txt").write_text("\n".join(lines) + "\n")
        QMessageBox.information(self, APP_NAME, tr('✅ {0} sprites exportados.').format(len(sel)))

    def duplicate(self):
        sel = self.selected()
        if not sel:
            return
        sff = self.sff()
        copies = []
        for s in sel:
            c = s.copy()
            n = s.number + 1
            while sff.find(s.group, n) or any(x.key == (s.group, n) for x in copies):
                n += 1
            c.number = n
            copies.append(c)
        before = list(sff.sprites)

        def redo():
            lst = list(before)
            for s, c in zip(sel, copies):
                lst.insert(lst.index(s) + 1, c)
            sff.sprites[:] = lst
        self.push(tr('Duplicar'), redo, lambda: sff.sprites.__setitem__(slice(None), before), refresh_list=True)
        self.select(copies[0])

    def delete(self):
        sel = self.selected()
        if not sel:
            return
        sff = self.sff()
        before = list(sff.sprites)
        # los que compartían imagen con uno borrado se quedan con su propia copia
        dependents = [s for s in before if s not in sel and s.link is not None and s.base() in sel]
        saved = [(d, d.link) for d in dependents]
        pix = {id(d): d.pixels() for d in dependents}
        row = self.list.currentIndex().row()

        def redo():
            for d in dependents:
                p = d.base().palidx
                d.set_pixels(pix[id(d)])
                d.palidx = p
            sff.sprites[:] = [s for s in before if s not in sel]

        def undo():
            sff.sprites[:] = before
            for d, link in saved:
                d.link = link
                d._pix = None
        self.push(tr('Borrar sprites'), redo, undo, refresh_list=True)
        if self.model.rowCount():
            self.list.setCurrentIndex(self.model.index(min(row, self.model.rowCount() - 1)))
        else:
            self.show_sprite(None)

    def crop(self):
        sel = [s for s in self.selected() if s.link is None]
        changes = []
        for s in sel:
            pix = s.pixels()
            mask = pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0
            if not mask.any():
                continue
            ys, xs = np.where(mask)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            if (x0, y0, x1, y1) == (0, 0, pix.shape[1], pix.shape[0]):
                continue
            changes.append((s, pix, pix[y0:y1, x0:x1].copy(), s.x, s.y, s.x - int(x0), s.y - int(y0), s.palidx,
                            (s._raw, s._decoder)))
        if not changes:
            return

        def redo():
            for s, _old, new, _ox, _oy, nx, ny, pal, _r in changes:
                s.set_pixels(new)
                s.x, s.y, s.palidx = nx, ny, pal

        def undo():
            for s, old, _new, ox, oy, _nx, _ny, pal, (raw, dec) in changes:
                s.set_pixels(old)
                s._raw, s._decoder = raw, dec
                s.x, s.y, s.palidx = ox, oy, pal
        self.push(tr('Recortar bordes'), redo, undo, refresh_list=True)

    def sort_sprites(self):
        sff = self.sff()
        before = list(sff.sprites)
        after = sorted(before, key=lambda s: (s.group, s.number))
        # un sprite enlazado debe ir después de su original
        self.push(tr('Ordenar sprites'), lambda: sff.sprites.__setitem__(slice(None), after),
                  lambda: sff.sprites.__setitem__(slice(None), before), refresh_list=True)

    # ---- paletas
    def load_act(self):
        pal = self.grid.palette
        if pal is None:
            return
        fpath, _ = QFileDialog.getOpenFileName(self, tr('Abrir paleta'), str(self.project().folder), "ACT (*.act)")
        if not fpath:
            return
        new = read_act(fpath)
        old = pal.colors.copy()
        cols = new.colors.copy()

        def redo():
            pal.colors = cols.copy()

        def undo():
            pal.colors = old.copy()
        self.push(tr('Cargar paleta'), redo, undo, refresh_list=True)
        self.on_color_edited(-1)

    def save_act(self):
        pal = self.grid.palette
        if pal is None:
            return
        fpath, _ = QFileDialog.getSaveFileName(self, tr('Guardar paleta'), str(self.project().folder), "ACT (*.act)")
        if fpath:
            write_act(fpath, pal)

    def new_palette(self):
        """Agrega al SFF una paleta del personaje (1,n) copiando la que se está viendo."""
        sff = self.sff()
        if not sff:
            return
        nums = {p.number for p in sff.palettes if p.group == 1}
        n = 1
        while n in nums:
            n += 1
        src = self.grid.palette or sff.palettes[0]
        new = Palette(1, n, src.colors.copy())

        def redo():
            sff.palettes.append(new)
            sff.modified = True

        def undo():
            if new in sff.palettes:
                sff.palettes.remove(new)
        self.push(tr('Nueva paleta'), redo, undo)
        self.fill_sprite_palettes()
        self.view_pal.addItem(tr('Paleta {0}  ({1})').format(n, f"SFF 1,{n}"), new)
        self.view_pal.setCurrentIndex(self.view_pal.count() - 1)
        self.update_count()

    # ---- guardar
    def require(self):
        if self.project() is None:
            QMessageBox.information(self, APP_NAME, tr('Primero abre o crea un personaje.'))
            return False
        return True

    def save(self):
        p = self.project()
        if not p or not p.sff_loaded():
            return True
        sff = p.sff
        p.backup(sff.path)

        def work(step):
            sff.save(None, lambda f: step(tr('Guardando sprites…'), f))
            return True
        ok, cancelled = run_with_progress(self, tr('Guardando sprites…'), work)
        if ok:
            self.undo.setClean()
            if not p.file_value("sprite"):
                p.defs.set("Files", "sprite", sff.path.name)
                p.defs_dirty = True
        return bool(ok) and not cancelled
