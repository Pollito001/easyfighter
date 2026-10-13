"""Pestaña Animaciones: acciones, cuadros, reproducción y cajas de golpe (Clsn1 / Clsn2)."""
from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QKeySequence, QPixmap, QTransform, QUndoStack
from PyQt6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGroupBox, QHBoxLayout,
    QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSlider, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

import numpy as np

from core.air import Action, Frame
from core.sff import Palette
from i18n import tr
from ui.common import APP_NAME, ZoomView, warn_banner, axis_pen, cosmetic, rectf, sprite_qimage
from ui.frame_panel import FramePanel, flip_label, trans_label
from ui.undo import FnCommand

COLS = ['Grupo', 'Número', 'X', 'Y', 'Tiempo', 'Voltear', 'Transp.', 'Escala X', 'Escala Y', 'Ángulo']
FLIPS = ["", "H", "V", "HV"]
CLSN_COLORS = {1: QColor(255, 60, 60), 2: QColor(60, 140, 255)}


def clone_action(a):
    b = Action(a.number)
    b.frames = [f.copy() for f in a.frames]
    b.loopstart, b.header, b.title, b.raw = a.loopstart, list(a.header), a.title, a.raw
    return b


def restore_action(dst, src):
    dst.number = src.number
    dst.frames = [f.copy() for f in src.frames]
    dst.loopstart, dst.header, dst.title, dst.raw = src.loopstart, list(src.header), src.title, src.raw


# ---------------------------------------------------------------- vista con edición de cajas
class AnimView(ZoomView):
    boxesEdited = pyqtSignal(object, object)  # (antes, después) listas por tipo
    boxSelected = pyqtSignal(int, int)        # tipo, índice

    HANDLE = 5  # píxeles de pantalla para agarrar bordes

    def __init__(self, scene, tab):
        super().__init__(scene)
        self.tab = tab
        self.mode = "edit"   # edit | draw1 | draw2
        self.flip = False
        self._op = None
        self.sel = (0, -1)
        self.setMouseTracking(True)

    def set_zoom(self, z):
        z = max(0.1, min(32.0, z))
        self.resetTransform()
        self.scale(-z if self.flip else z, z)
        self.zoom = z
        self.zoomChanged.emit(z)

    def frame(self):
        return self.tab.current_frame()

    def boxes(self, kind):
        f = self.frame()
        return (f.clsn1 if kind == 1 else f.clsn2) if f else []

    def hit(self, sp):
        """(tipo, índice, parte) bajo el punto de la escena. parte: 'move' o combinación de l/r/t/b."""
        tol = self.HANDLE / max(0.1, self.zoom)
        f = self.frame()
        if not f or not self.tab.show_clsn.isChecked():
            return None
        for kind in (1, 2):
            boxes = self.boxes(kind)
            for i in range(len(boxes) - 1, -1, -1):
                x1, y1, x2, y2 = boxes[i]
                l, r, t, b = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
                if not (l - tol <= sp.x() <= r + tol and t - tol <= sp.y() <= b + tol):
                    continue
                part = ""
                if abs(sp.x() - l) <= tol:
                    part += "l"
                elif abs(sp.x() - r) <= tol:
                    part += "r"
                if abs(sp.y() - t) <= tol:
                    part += "t"
                elif abs(sp.y() - b) <= tol:
                    part += "b"
                return kind, i, part or "move"
        return None

    def mousePressEvent(self, e):
        f = self.frame()
        if e.button() != Qt.MouseButton.LeftButton or f is None:
            return super().mousePressEvent(e)
        sp = self.mapToScene(e.position().toPoint())
        before = (list(f.clsn1), list(f.clsn2))
        if self.mode in ("draw1", "draw2"):
            kind = 1 if self.mode == "draw1" else 2
            boxes = self.boxes(kind)
            x, y = round(sp.x()), round(sp.y())
            boxes.append((x, y, x, y))
            self._op = ("resize", kind, len(boxes) - 1, "rb", sp, (x, y, x, y), before)
            self.sel = (kind, len(boxes) - 1)
        else:
            h = self.hit(sp)
            if h is None:
                self.sel = (0, -1)
                self.tab.redraw()
                self.boxSelected.emit(0, -1)
                return
            kind, i, part = h
            self.sel = (kind, i)
            box = self.boxes(kind)[i]
            self._op = ("move" if part == "move" else "resize", kind, i, part, sp, box, before)
            self.boxSelected.emit(kind, i)
        self.tab.redraw()
        e.accept()

    def mouseMoveEvent(self, e):
        sp = self.mapToScene(e.position().toPoint())
        if self._op is None:
            if self._pan is None and self.mode == "edit":
                h = self.hit(sp)
                shapes = {"move": Qt.CursorShape.SizeAllCursor, "l": Qt.CursorShape.SizeHorCursor,
                          "r": Qt.CursorShape.SizeHorCursor, "t": Qt.CursorShape.SizeVerCursor,
                          "b": Qt.CursorShape.SizeVerCursor, "lt": Qt.CursorShape.SizeFDiagCursor,
                          "rb": Qt.CursorShape.SizeFDiagCursor, "rt": Qt.CursorShape.SizeBDiagCursor,
                          "lb": Qt.CursorShape.SizeBDiagCursor}
                self.viewport().setCursor(shapes.get(h[2], Qt.CursorShape.ArrowCursor) if h else Qt.CursorShape.ArrowCursor)
            elif self.mode != "edit":
                self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            return super().mouseMoveEvent(e)
        op, kind, i, part, start, box, _before = self._op
        dx, dy = round(sp.x() - start.x()), round(sp.y() - start.y())
        x1, y1, x2, y2 = box
        l, r, t, b = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
        if op == "move":
            l, r, t, b = l + dx, r + dx, t + dy, b + dy
        else:
            if self.mode in ("draw1", "draw2"):
                r, b = box[0] + dx, box[1] + dy
                l, t = box[0], box[1]
            else:
                if "l" in part:
                    l += dx
                if "r" in part:
                    r += dx
                if "t" in part:
                    t += dy
                if "b" in part:
                    b += dy
        boxes = self.boxes(kind)
        if i < len(boxes):
            boxes[i] = (int(l), int(t), int(r), int(b))
        self.tab.redraw()
        e.accept()

    def mouseReleaseEvent(self, e):
        if self._op is not None and e.button() == Qt.MouseButton.LeftButton:
            op, kind, i, part, start, box, before = self._op
            self._op = None
            f = self.frame()
            boxes = self.boxes(kind)
            if i < len(boxes):
                x1, y1, x2, y2 = boxes[i]
                boxes[i] = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
                if abs(x2 - x1) < 1 or abs(y2 - y1) < 1:
                    del boxes[i]  # clic sin arrastrar
                    self.sel = (0, -1)
            after = (list(f.clsn1), list(f.clsn2))
            if after != before:
                self.boxesEdited.emit(before, after)
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        kind, i = self.sel
        f = self.frame()
        if f and kind and i >= 0:
            boxes = self.boxes(kind)
            if i < len(boxes):
                moves = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1),
                         Qt.Key.Key_Down: (0, 1)}
                before = (list(f.clsn1), list(f.clsn2))
                if e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                    del boxes[i]
                    self.sel = (0, -1)
                    self.boxesEdited.emit(before, (list(f.clsn1), list(f.clsn2)))
                    return
                if e.key() in moves:
                    dx, dy = moves[e.key()]
                    x1, y1, x2, y2 = boxes[i]
                    boxes[i] = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
                    self.boxesEdited.emit(before, (list(f.clsn1), list(f.clsn2)))
                    return
        super().keyPressEvent(e)


# ---------------------------------------------------------------- pestaña
class AnimTab(QWidget):
    modifiedChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.undo = QUndoStack(self)
        self.undo.cleanChanged.connect(self.modifiedChanged)
        self.action = None
        self.frame_i = 0
        self.tick = 0
        self._block = False
        self._sprites = {}
        self._pix = {}
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)

        lay = QHBoxLayout(self)
        split = QSplitter()
        lay.addWidget(split)
        # ---- izquierda: acciones
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr('Buscar acción (número o nombre)'))
        self.filter.textChanged.connect(lambda _t: self.fill_actions())
        ll.addWidget(self.filter)
        self.alist = QListWidget()
        self.alist.currentItemChanged.connect(self.on_action)
        ll.addWidget(self.alist, 1)
        row = QHBoxLayout()
        for txt, fn, tip in ((tr('➕'), self.new_action, tr('Nueva acción')),
                             (tr('📋'), self.dup_action, tr('Duplicar acción')),
                             (tr('#'), self.renumber_action, tr('Cambiar número')),
                             (tr('🗑'), self.del_action, tr('Borrar acción')),
                             (tr('💻'), self.show_code, tr('Ver y editar el código (.air) de esta animación'))):
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        split.addWidget(left)
        # ---- centro: vista + cuadros
        center = QSplitter(Qt.Orientation.Vertical)
        top = QWidget()
        tl = QVBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        self.gen_banner = warn_banner()
        self.gen_banner.setText(tr('⚠ <b>Esta animación la hace el modo simple.</b> Se vuelve a armar cada vez que '
                                   'cambias algo en el modo simple, así que lo que cambies aquí se pierde. Para '
                                   'cambiarla, hazlo en el modo simple (o duplícala con 📋 y usa la copia).'))
        tl.addWidget(self.gen_banner)
        self.warned = False
        self.scene = QGraphicsScene()
        self.view = AnimView(self.scene, self)
        self.view.boxesEdited.connect(self.on_boxes_edited)
        self.view.boxSelected.connect(lambda _k, _i: self.fill_boxes())
        tl.addWidget(self.view, 1)
        ctl = QHBoxLayout()
        self.play_btn = QPushButton(tr('▶ Reproducir'))
        self.play_btn.setShortcut(QKeySequence("Space"))
        self.play_btn.clicked.connect(self.toggle_play)
        ctl.addWidget(self.play_btn)
        for txt, d in (("⏮", -1), ("⏭", 1)):
            b = QToolButton()
            b.setText(txt)
            b.clicked.connect(lambda _c, d=d: self.step(d))
            ctl.addWidget(b)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self.on_slider)
        ctl.addWidget(self.slider, 1)
        self.pos_lbl = QLabel()
        ctl.addWidget(self.pos_lbl)
        self.speed = QComboBox()
        for txt, v in (("¼×", 0.25), ("½×", 0.5), ("1×", 1.0), ("2×", 2.0)):
            self.speed.addItem(txt, v)
        self.speed.setCurrentIndex(2)
        self.speed.currentIndexChanged.connect(self.update_timer)
        ctl.addWidget(self.speed)
        gif = QPushButton(tr('🎬 GIF'))
        gif.setToolTip(tr('Exportar esta animación como GIF animado'))
        gif.clicked.connect(self.export_gif)
        ctl.addWidget(gif)
        tl.addLayout(ctl)
        opt = QHBoxLayout()
        self.show_clsn = QCheckBox(tr('Cajas'))
        self.show_clsn.setChecked(True)
        self.show_clsn.toggled.connect(lambda _c: self.redraw())
        self.onion = QCheckBox(tr('Cuadro anterior'))
        self.onion.toggled.connect(lambda _c: self.redraw())
        self.flip_view = QCheckBox(tr('Mirar a la izquierda'))
        self.flip_view.toggled.connect(lambda _c: self.redraw())
        self.pal = QComboBox()
        self.pal.currentIndexChanged.connect(lambda _i: (self._pix.clear(), self.redraw()))
        for w in (self.show_clsn, self.onion, self.flip_view):
            opt.addWidget(w)
        from ui.backgrounds import BackdropPicker
        self.bg_picker = BackdropPicker(main)
        opt.addStretch(1)
        tl.addLayout(opt)
        opt2 = QHBoxLayout()
        opt2.addWidget(self.bg_picker)
        opt2.addStretch(1)
        opt2.addWidget(QLabel(tr('Paleta:')))
        opt2.addWidget(self.pal)
        tl.addLayout(opt2)
        center.addWidget(top)
        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels([tr(c) for c in COLS])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.currentCellChanged.connect(self.on_row)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setToolTip(tr('Los datos del cuadro se cambian en el panel «Cuadro» de la derecha'))
        self.table.cellDoubleClicked.connect(lambda _r, _c: self.right_tabs.setCurrentIndex(0))
        bl.addWidget(self.table, 1)
        fr = QHBoxLayout()
        for txt, fn, tip in ((tr('➕ Cuadro'), self.add_frame, tr('Agrega un cuadro después del actual')),
                             (tr('🖼 Agregar sprites…'), self.add_sprites, tr('Un cuadro por cada sprite de un grupo')),
                             (tr('📋 Duplicar'), self.dup_frame, None),
                             (tr('🗑 Borrar'), self.del_frame, None),
                             (tr('⬆'), lambda: self.move_frame(-1), None),
                             (tr('⬇'), lambda: self.move_frame(1), None)):
            short = txt.split(" ", 1)[0]
            b = QPushButton(short)
            full = txt if " " in txt else ""
            b.setToolTip((full + (" — " + tip if tip else "")) if full else (tip or ""))
            b.clicked.connect(fn)
            fr.addWidget(b)
        fr.addStretch(1)
        from PyQt6.QtGui import QAction
        for txt, fn, key, sig in ((tr('↶'), self.undo.undo, QKeySequence.StandardKey.Undo, self.undo.canUndoChanged),
                                  (tr('↷'), self.undo.redo, QKeySequence.StandardKey.Redo, self.undo.canRedoChanged)):
            a = QAction(txt, self)
            a.setShortcut(QKeySequence(key))
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            a.triggered.connect(fn)
            a.setEnabled(False)
            sig.connect(a.setEnabled)
            self.addAction(a)
            tb = QToolButton()
            tb.setDefaultAction(a)
            fr.addWidget(tb)
        bl.addLayout(fr)
        center.addWidget(bottom)
        center.setSizes([560, 260])
        split.addWidget(center)
        # ---- derecha: cajas
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        from PyQt6.QtWidgets import QScrollArea, QTabWidget
        self.right_tabs = QTabWidget()
        rl.addWidget(self.right_tabs, 1)
        self.panel = FramePanel()
        self.panel.changed.connect(self.on_panel_change)
        self.panel.applyAll.connect(self.on_apply_all)
        self.panel.nudge.connect(self.on_nudge)
        self.panel.loopToggled.connect(self.on_loop_toggled)
        psc = QScrollArea()
        psc.setWidgetResizable(True)
        psc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        psc.setWidget(self.panel)
        self.right_tabs.addTab(psc, tr('🎞 Cuadro'))
        g = QGroupBox(tr('Cajas de golpe'))
        gl = QVBoxLayout(g)
        self.tool_grp = QButtonGroup(self)
        for txt, mode, tip in ((tr('✋ Mover / estirar'), "edit", tr('Arrastra una caja para moverla; sus bordes para estirarla. Supr la borra.')),
                               (tr('🟦 Dibujar Clsn2 (cuerpo)'), "draw2", tr('Donde al personaje le pueden pegar')),
                               (tr('🟥 Dibujar Clsn1 (golpe)'), "draw1", tr('La parte que pega'))):
            b = QPushButton(txt)
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setChecked(mode == "edit")
            b.clicked.connect(lambda _c, mode=mode: setattr(self.view, "mode", mode))
            self.tool_grp.addButton(b)
            gl.addWidget(b)
        self.box_list = QListWidget()
        self.box_list.currentRowChanged.connect(self.on_box_row)
        gl.addWidget(self.box_list, 1)
        for txt, fn in ((tr('🪄 Cajas automáticas…'), self.auto_boxes),
                        (tr('🗑 Borrar caja'), self.del_box),
                        (tr('⬅ Copiar cajas del cuadro anterior'), self.copy_prev_boxes),
                        (tr('⇶ Usar estas cajas en todos los cuadros'), self.boxes_to_all),
                        (tr('✖ Quitar todas las cajas de este cuadro'), self.clear_boxes)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            gl.addWidget(b)
        self.right_tabs.addTab(g, tr('🟦 Cajas'))
        self.info = QLabel()
        self.info.setWordWrap(True)
        rl.addWidget(self.info)
        split.addWidget(right)
        split.setSizes([240, 860, 260])

    # ---- datos
    def project(self):
        return self.main.project

    def air(self):
        p = self.project()
        return p.air if p else None

    def is_modified(self):
        p = self.project()
        return bool(p and p.air_loaded() and (p.air.modified or not self.undo.isClean()))

    def load(self):
        self.stop()
        self.undo.clear()
        self.warned = False
        self._block = True
        self.pal.clear()
        p = self.project()
        if p:
            for n, name, pal in p.char_palettes():
                self.pal.addItem(tr('Paleta {0}').format(n), pal)
        if self.pal.count() == 0:
            self.pal.addItem(tr('Paleta del SFF'), None)
        self._block = False
        self.activated()
        self.fill_actions()
        if self.alist.count():
            self.alist.setCurrentRow(0)
        self.view.set_zoom(2)

    def activated(self):
        """Al entrar a la pestaña: los sprites pueden haber cambiado."""
        p = self.project()
        self._sprites = p.sff.index() if p else {}
        self._pix.clear()
        self.redraw()

    def override(self):
        d = self.pal.currentData()
        return d if isinstance(d, Palette) else None

    def pixmap(self, g, n):
        s = self._sprites.get((g, n))
        if s is None:
            return None, None
        key = (id(s), id(self.override()))
        if key not in self._pix:
            img = sprite_qimage(self.project().sff, s, self.override())
            self._pix[key] = QPixmap.fromImage(img) if not img.isNull() else None
        return self._pix[key], s

    # ---- lista de acciones
    def fill_actions(self, keep=None):
        air = self.air()
        cur = keep if keep is not None else self.action
        self.alist.blockSignals(True)
        self.alist.clear()
        flt = self.filter.text().strip().lower()
        sel_row = -1
        for a in air.actions if air else []:
            label = f"{a.number}    {a.title}" if a.title else str(a.number)
            if flt and flt not in label.lower():
                continue
            it = QListWidgetItem(f"{label}   ({len(a.frames)})")
            it.setData(Qt.ItemDataRole.UserRole, a)
            self.alist.addItem(it)
            if a is cur:
                sel_row = self.alist.count() - 1
        self.alist.blockSignals(False)
        if sel_row >= 0:
            self.alist.setCurrentRow(sel_row)

    def is_generated(self, a):
        """¿La acción la arma el modo simple?"""
        sm = getattr(self.main, "simple", None)
        return bool(a is not None and sm is not None and a.number in set(sm.cfg.get("owned", [])))

    def on_action(self, item, _prev=None):
        self.action = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.gen_banner.setVisible(self.is_generated(self.action))
        self.frame_i = 0
        self.tick = 0
        self.fill_table()
        self.redraw()

    def current_frame(self):
        a = self.action
        if a and 0 <= self.frame_i < len(a.frames):
            return a.frames[self.frame_i]
        return None

    # ---- tabla de cuadros
    def fill_table(self):
        self._block = True
        a = self.action
        frames = a.frames if a else []
        self.table.setRowCount(len(frames))
        for r, f in enumerate(frames):
            vals = [f.group, f.number, f.x, f.y, f.time if f.time >= 0 else "−1 ∞", flip_label(f.flip) if f.flip else "",
                    trans_label(f.trans) if f.trans else "",
                    "" if f.xscale is None else f.xscale, "" if f.yscale is None else f.yscale,
                    "" if f.angle is None else f.angle]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                if r == (a.loopstart if a else -1) and r > 0:
                    it.setBackground(QBrush(QColor(60, 90, 60)))
                self.table.setItem(r, c, it)
            missing = (f.group, f.number) not in self._sprites and f.group >= 0
            if missing:
                for c in (0, 1):
                    self.table.item(r, c).setForeground(QBrush(QColor(255, 90, 90)))
                    self.table.item(r, c).setToolTip(tr('Ese sprite no existe'))
        self.slider.setRange(0, max(0, len(frames) - 1))
        self.slider.setValue(self.frame_i)
        if frames:
            self.table.selectRow(min(self.frame_i, len(frames) - 1))
        self._block = False
        self.fill_boxes()
        self.update_info()

    def update_info(self):
        a = self.action
        if not a:
            self.info.setText("")
            self.pos_lbl.setText("")
            return
        d = a.duration()
        self.info.setText(tr('Acción {0}: {1} cuadros · dura {2}').format(
            a.number, len(a.frames), tr('para siempre') if d < 0 else tr('{0} ticks ({1:.2f} s)').format(d, d / 60)))
        self.pos_lbl.setText(f"{self.frame_i + 1}/{len(a.frames)}")

    def on_row(self, row, _c, _pr, _pc):
        if self._block or row < 0:
            return
        self.frame_i = row
        self.tick = 0
        self._block = True
        self.slider.setValue(row)
        self._block = False
        self.fill_boxes()
        self.update_info()
        self.redraw()

    def on_slider(self, v):
        if self._block:
            return
        self.frame_i = v
        self.tick = 0
        self._block = True
        self.table.selectRow(v)
        self._block = False
        self.fill_boxes()
        self.update_info()
        self.redraw()

    # ---- panel del cuadro
    def fill_panel(self):
        f = self.current_frame()
        a = self.action
        exists = f is not None and (f.group, f.number) in self._sprites
        self.panel.show_frame(f, bool(a and f and a.loopstart == self.frame_i and self.frame_i > 0), exists)

    def on_panel_change(self, field, value):
        a = self.action
        i = self.frame_i
        if not a or not (0 <= i < len(a.frames)):
            return

        def fn():
            f = a.frames[i]
            if field == "scale_reset":
                f.xscale = f.yscale = f.angle = None
            elif field in ("xscale", "yscale"):
                setattr(f, field, float(value))
                if f.xscale is None:
                    f.xscale = 1.0
                if f.yscale is None:
                    f.yscale = 1.0
                if f.angle is None:
                    f.angle = 0.0
            elif field == "angle":
                f.angle = float(value)
                f.xscale = 1.0 if f.xscale is None else f.xscale
                f.yscale = 1.0 if f.yscale is None else f.yscale
            else:
                setattr(f, field, value)
        self.edit(tr('Editar cuadro'), fn)

    def on_apply_all(self, field):
        a = self.action
        f = self.current_frame()
        if not f:
            return
        attrs = {"offset": ("x", "y"), "time": ("time",), "flip": ("flip",), "trans": ("trans",),
                 "scale": ("xscale", "yscale", "angle")}[field]
        vals = {k: getattr(f, k) for k in attrs}

        def fn():
            for x in a.frames:
                for k, v in vals.items():
                    setattr(x, k, v)
        self.edit(tr('Aplicar a todos los cuadros'), fn)

    def on_nudge(self, dx, dy):
        a = self.action
        i = self.frame_i
        if not self.current_frame():
            return

        def fn():
            a.frames[i].x += dx
            a.frames[i].y += dy
        self.edit(tr('Mover cuadro'), fn)

    def on_loop_toggled(self, checked):
        a = self.action
        if not a:
            return
        i = self.frame_i if checked else 0
        self.edit(tr('Repetir desde aquí'), lambda: setattr(a, "loopstart", i))

    def show_code(self):
        a = self.action
        if not a:
            return
        from ui.action_code import ActionCodeDialog
        air = self.air()
        dlg = ActionCodeDialog(self, a, air.path.name if air and air.path else ".air")
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.result_action is None:
            return
        new = dlg.result_action
        if new.number != a.number and air.find(new.number) is not None:
            QMessageBox.warning(self, APP_NAME, tr('Ya existe la acción {0}.').format(new.number))
            return
        lst = [new if x is a else x for x in air.actions]
        self.edit_list(tr('Editar código de la acción'), lst, new)
        self.select_action(new)

    def on_cell(self, item):
        if self._block or not self.action:
            return
        r, c = item.row(), item.column()
        a = self.action
        if r >= len(a.frames):
            return
        txt = item.text().strip()

        def apply():
            f = a.frames[r]
            try:
                if c < 5:
                    v = int(float(txt or 0))
                    setattr(f, ["group", "number", "x", "y", "time"][c], v)
                elif c == 5:
                    f.flip = txt.upper() if txt.upper() in FLIPS else ""
                elif c == 6:
                    f.trans = txt
                else:
                    attr = ["xscale", "yscale", "angle"][c - 7]
                    setattr(f, attr, float(txt) if txt else None)
            except ValueError:
                pass
        self.edit(tr('Editar cuadro'), apply)

    # ---- edición con deshacer
    def edit(self, text, fn, refresh_list=False):
        a = self.action
        if a is None:
            return
        if not self.warned and self.is_generated(a):
            self.warned = True
            QTimer.singleShot(0, lambda: QMessageBox.warning(self, APP_NAME, tr(
                'Ojo: esta animación la hace el modo simple. La próxima vez que cambies algo en el modo simple se '
                'vuelve a armar y este cambio se pierde.\n\nSi quieres que se quede, duplícala con 📋 y cambia '
                'la copia, o cámbiala desde el modo simple.')))
        before = clone_action(a)
        fn()
        a.raw = None
        after = clone_action(a)
        after.raw = None

        def redo():
            restore_action(a, after)

        def undo():
            restore_action(a, before)
        self.undo.push(FnCommand(text, redo, undo, after=lambda: self.after_edit(a, refresh_list)))

    def after_edit(self, a, refresh_list):
        if refresh_list:
            self.fill_actions(a)
        if self.action is a:
            self.frame_i = min(self.frame_i, max(0, len(a.frames) - 1))
            self.fill_table()
        self.redraw()
        self.modifiedChanged.emit()

    def edit_list(self, text, new_list, select=None):
        air = self.air()
        before = list(air.actions)

        def redo():
            air.actions[:] = new_list

        def undo():
            air.actions[:] = before
        self.undo.push(FnCommand(text, redo, undo, after=lambda: (self.fill_actions(select), self.modifiedChanged.emit())))

    # ---- acciones
    def ask_number(self, title, default):
        n, ok = QInputDialog.getInt(self, title, tr('Número de la acción:'), default, -2147483647, 2147483647)
        if not ok:
            return None
        if self.air().find(n) is not None:
            QMessageBox.warning(self, APP_NAME, tr('Ya existe la acción {0}.').format(n))
            return None
        return n

    def free_number(self, start=0):
        n = start
        while self.air().find(n) is not None:
            n += 1
        return n

    def new_action(self):
        if not self.project():
            return
        n = self.ask_number(tr('Nueva acción'), self.free_number(self.action.number + 1 if self.action else 0))
        if n is None:
            return
        a = Action(n)
        a.frames = [Frame(0, 0, 0, 0, 10)]
        self.edit_list(tr('Nueva acción'), sorted(self.air().actions + [a], key=lambda x: x.number), a)
        self.select_action(a)

    def dup_action(self):
        if not self.action:
            return
        n = self.ask_number(tr('Duplicar acción'), self.free_number(self.action.number + 1))
        if n is None:
            return
        a = clone_action(self.action)
        a.number, a.raw = n, None
        a.header = [h for h in a.header]
        self.edit_list(tr('Duplicar acción'), sorted(self.air().actions + [a], key=lambda x: x.number), a)
        self.select_action(a)

    def renumber_action(self):
        a = self.action
        if not a:
            return
        n = self.ask_number(tr('Cambiar número'), a.number)
        if n is None:
            return
        self.edit(tr('Cambiar número'), lambda: setattr(a, "number", n), refresh_list=True)

    def del_action(self):
        a = self.action
        if not a:
            return
        if QMessageBox.question(self, APP_NAME, tr('¿Borrar la acción {0}?').format(a.number)) != QMessageBox.StandardButton.Yes:
            return
        self.edit_list(tr('Borrar acción'), [x for x in self.air().actions if x is not a])
        if self.alist.count():
            self.alist.setCurrentRow(0)

    def select_action(self, a):
        for i in range(self.alist.count()):
            if self.alist.item(i).data(Qt.ItemDataRole.UserRole) is a:
                self.alist.setCurrentRow(i)
                return

    # ---- cuadros
    def add_frame(self):
        a = self.action
        if not a:
            return
        i = self.frame_i
        base = a.frames[i].copy() if a.frames else Frame(0, 0, 0, 0, 5)
        if a.frames:
            base.number += 1 if (base.group, base.number + 1) in self._sprites else 0
        self.edit(tr('Agregar cuadro'), lambda: a.frames.insert(i + 1 if a.frames else 0, base))
        self.go_frame(i + 1)

    def add_sprites(self):
        a = self.action
        if not a:
            return
        groups = sorted({k[0] for k in self._sprites})
        if not groups:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(tr('Agregar sprites'))
        form = QFormLayout(dlg)
        g = QComboBox()
        for x in groups:
            g.addItem(str(x), x)
        if a.frames:
            i = g.findData(a.frames[self.frame_i].group)
            if i >= 0:
                g.setCurrentIndex(i)
        t = QSpinBox()
        t.setRange(-1, 999)
        t.setValue(5)
        form.addRow(tr('Grupo:'), g)
        form.addRow(tr('Tiempo de cada cuadro:'), t)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if not dlg.exec():
            return
        grp = g.currentData()
        nums = sorted(n for (gg, n) in self._sprites if gg == grp)
        new = [Frame(grp, n, 0, 0, t.value()) for n in nums]
        if a.frames:
            for f in new:
                f.clsn1 = list(a.frames[-1].clsn1)
                f.clsn2 = list(a.frames[-1].clsn2)
        self.edit(tr('Agregar sprites'), lambda: a.frames.extend(new), refresh_list=True)

    def dup_frame(self):
        a = self.action
        f = self.current_frame()
        if not f:
            return
        i = self.frame_i
        self.edit(tr('Duplicar cuadro'), lambda: a.frames.insert(i + 1, f.copy()), refresh_list=True)
        self.go_frame(i + 1)

    def del_frame(self):
        a = self.action
        if not self.current_frame():
            return
        i = self.frame_i

        def fn():
            del a.frames[i]
            if a.loopstart > i:
                a.loopstart -= 1
            a.loopstart = min(a.loopstart, max(0, len(a.frames) - 1))
        self.edit(tr('Borrar cuadro'), fn, refresh_list=True)

    def move_frame(self, d):
        a = self.action
        i = self.frame_i
        j = i + d
        if not a or not (0 <= j < len(a.frames)):
            return

        def fn():
            a.frames[i], a.frames[j] = a.frames[j], a.frames[i]
        self.edit(tr('Mover cuadro'), fn)
        self.go_frame(j)

    def set_loopstart(self):
        a = self.action
        if not a:
            return
        i = self.frame_i
        self.edit(tr('Repetir desde aquí'), lambda: setattr(a, "loopstart", i))

    def go_frame(self, i):
        self.frame_i = i
        self.fill_table()
        self.redraw()

    # ---- cajas
    def fill_boxes(self):
        self.box_list.blockSignals(True)
        self.box_list.clear()
        f = self.current_frame()
        sel_row = -1
        if f:
            for kind, boxes in ((2, f.clsn2), (1, f.clsn1)):
                for i, b in enumerate(boxes):
                    it = QListWidgetItem(f"Clsn{kind}[{i}]   {b[0]}, {b[1]}, {b[2]}, {b[3]}")
                    it.setForeground(QBrush(CLSN_COLORS[kind]))
                    it.setData(Qt.ItemDataRole.UserRole, (kind, i))
                    self.box_list.addItem(it)
                    if self.view.sel == (kind, i):
                        sel_row = self.box_list.count() - 1
        self.box_list.setCurrentRow(sel_row)
        self.box_list.blockSignals(False)
        self.fill_panel()

    def on_box_row(self, row):
        it = self.box_list.item(row)
        self.view.sel = it.data(Qt.ItemDataRole.UserRole) if it else (0, -1)
        self.redraw()

    def on_boxes_edited(self, before, after):
        a = self.action
        i = self.frame_i
        f = self.current_frame()
        # la vista ya cambió el cuadro: se deshace para registrar el cambio
        f.clsn1, f.clsn2 = list(before[0]), list(before[1])

        def fn():
            a.frames[i].clsn1, a.frames[i].clsn2 = list(after[0]), list(after[1])
        self.edit(tr('Editar cajas'), fn)

    def sprite_bbox(self, f):
        """Caja (x1,y1,x2,y2) de lo visible del sprite del cuadro, relativa al eje del personaje."""
        s = self._sprites.get((f.group, f.number))
        if s is None:
            return None
        pix = s.pixels()
        mask = pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0
        if not mask.any():
            return None, None
        return mask, s

    def boxes_for(self, f, two):
        got = self.sprite_bbox(f)
        if not got or got[0] is None:
            return []
        mask, s = got
        xs_scale = f.xscale if f.xscale else 1.0
        ys_scale = f.yscale if f.yscale else 1.0
        flip_h = "H" in (f.flip or "").upper()
        flip_v = "V" in (f.flip or "").upper()

        def conv(x0, y0, x1, y1):
            ax0, ax1 = (x0 - s.x) * xs_scale, (x1 - s.x) * xs_scale
            ay0, ay1 = (y0 - s.y) * ys_scale, (y1 - s.y) * ys_scale
            if flip_h:
                ax0, ax1 = -ax1, -ax0
            if flip_v:
                ay0, ay1 = -ay1, -ay0
            return (int(round(ax0 + f.x)), int(round(ay0 + f.y)), int(round(ax1 + f.x)), int(round(ay1 + f.y)))
        ys, xs = np.where(mask)
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        if not two or y1 - y0 < 8:
            return [conv(int(xs.min()), y0, int(xs.max()) + 1, y1)]
        cut = y0 + max(2, int((y1 - y0) * 0.22))
        out = []
        for a, b in ((y0, cut), (cut, y1)):
            part = mask[a:b]
            if part.any():
                pxs = np.where(part.any(axis=0))[0]
                out.append(conv(int(pxs.min()), a, int(pxs.max()) + 1, b))
        return out[::-1]  # cuerpo primero

    def auto_boxes(self):
        a = self.action
        if not a or not a.frames:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(tr('Cajas automáticas'))
        form = QFormLayout(dlg)
        kind = QComboBox()
        kind.addItem(tr('Clsn2 (cuerpo: donde le pueden pegar)'), 2)
        kind.addItem(tr('Clsn1 (golpe)'), 1)
        shape = QComboBox()
        shape.addItem(tr('Dos cajas (cabeza y cuerpo)'), True)
        shape.addItem(tr('Una caja'), False)
        where = QComboBox()
        where.addItem(tr('Todos los cuadros de esta acción'), "all")
        where.addItem(tr('Solo este cuadro'), "one")
        form.addRow(tr('Tipo:'), kind)
        form.addRow(tr('Forma:'), shape)
        form.addRow(tr('Dónde:'), where)
        form.addRow(QLabel(tr('Se calculan con la parte visible del sprite de cada cuadro (reemplazan las de ese tipo).')))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if not dlg.exec():
            return
        k, two = kind.currentData(), shape.currentData()
        idx = range(len(a.frames)) if where.currentData() == "all" else [self.frame_i]
        new = {i: self.boxes_for(a.frames[i], two) for i in idx}

        def fn():
            for i, boxes in new.items():
                if k == 1:
                    a.frames[i].clsn1 = list(boxes)
                else:
                    a.frames[i].clsn2 = list(boxes)
        self.edit(tr('Cajas automáticas'), fn)

    def export_gif(self):
        a = self.action
        if not a or not a.frames:
            return
        from PyQt6.QtWidgets import QFileDialog
        from core.gif import write_gif
        path, _ = QFileDialog.getSaveFileName(self, tr('Exportar GIF'),
                                              str(self.project().folder / f"accion_{a.number}.gif"), "GIF (*.gif)")
        if not path:
            return
        # caja que abarca todos los cuadros
        items = []
        for f in a.frames:
            pm, s = self.pixmap(f.group, f.number)
            items.append((f, pm, s))
        rects = []
        for f, pm, s in items:
            if pm is None:
                continue
            t = self.frame_transform(f, s)
            rects.append(t.mapRect(QRectF(0, 0, pm.width(), pm.height())))
        if not rects:
            return
        box = rects[0]
        for r in rects[1:]:
            box = box.united(r)
        x0, y0 = int(box.left()) - 2, int(box.top()) - 2
        w, h = int(box.width()) + 4, int(box.height()) + 4
        from PyQt6.QtGui import QImage, QPainter
        from ui.common import image_to_indices
        imgs = []
        for f, pm, s in items:
            img = QImage(w, h, QImage.Format.Format_ARGB32)
            img.fill(0)
            if pm is not None:
                p = QPainter(img)
                p.translate(-x0, -y0)
                p.setTransform(self.frame_transform(f, s), True)
                p.drawPixmap(0, 0, pm)
                p.end()
            imgs.append(img)
        # una paleta para todos: se arma con los colores de todos los cuadros juntos
        sheet = QImage(w, h * len(imgs), QImage.Format.Format_ARGB32)
        sheet.fill(0)
        p = QPainter(sheet)
        for i, img in enumerate(imgs):
            p.drawImage(0, i * h, img)
        p.end()
        idx, rgb = image_to_indices(sheet)
        frames = [idx[i * h:(i + 1) * h] for i in range(len(imgs))]
        delays = [max(2, round((f.time if f.time > 0 else 60) * 100 / 60)) for f in a.frames]
        write_gif(path, frames, rgb, delays)
        self.main.status.setText(tr('✅ GIF guardado: {0}').format(path))

    def frame_transform(self, f, s):
        t = QTransform()
        sx = -1 if "H" in (f.flip or "").upper() else 1
        sy = -1 if "V" in (f.flip or "").upper() else 1
        t.translate(f.x, f.y)
        if f.angle:
            t.rotate(-f.angle)
        t.scale(sx * (f.xscale if f.xscale is not None else 1.0), sy * (f.yscale if f.yscale is not None else 1.0))
        t.translate(-s.x, -s.y)
        return t

    def del_box(self):
        f = self.current_frame()
        kind, i = self.view.sel
        if not f or not kind or i < 0:
            return
        before = (list(f.clsn1), list(f.clsn2))
        boxes = f.clsn1 if kind == 1 else f.clsn2
        if i < len(boxes):
            del boxes[i]
        self.view.sel = (0, -1)
        self.on_boxes_edited(before, (list(f.clsn1), list(f.clsn2)))

    def copy_prev_boxes(self):
        a = self.action
        i = self.frame_i
        if not a or i <= 0:
            return
        p = a.frames[i - 1]

        def fn():
            a.frames[i].clsn1, a.frames[i].clsn2 = list(p.clsn1), list(p.clsn2)
        self.edit(tr('Copiar cajas'), fn)

    def boxes_to_all(self):
        a = self.action
        f = self.current_frame()
        if not f:
            return
        c1, c2 = list(f.clsn1), list(f.clsn2)

        def fn():
            for x in a.frames:
                x.clsn1, x.clsn2 = list(c1), list(c2)
        self.edit(tr('Cajas en todos los cuadros'), fn)

    def clear_boxes(self):
        a = self.action
        i = self.frame_i
        if not self.current_frame():
            return

        def fn():
            a.frames[i].clsn1, a.frames[i].clsn2 = [], []
        self.edit(tr('Quitar cajas'), fn)

    # ---- dibujo
    def add_frame_sprite(self, f, opacity=1.0):
        pm, s = self.pixmap(f.group, f.number)
        if pm is None:
            return
        it = QGraphicsPixmapItem(pm)
        it.setOffset(-s.x, -s.y)
        t = QTransform()
        sx = -1 if "H" in (f.flip or "").upper() else 1
        sy = -1 if "V" in (f.flip or "").upper() else 1
        xs = f.xscale if f.xscale is not None else 1.0
        ys = f.yscale if f.yscale is not None else 1.0
        t.translate(f.x, f.y)
        if f.angle:
            t.rotate(-f.angle)
        t.scale(sx * xs, sy * ys)
        it.setTransform(t)
        it.setOpacity(opacity)
        tr_ = (f.trans or "").upper()
        if tr_.startswith("A") and opacity == 1.0:
            it.setOpacity(0.7)
        self.scene.addItem(it)

    def redraw(self):
        self.scene.clear()
        lim = 600
        f = self.current_frame()
        a = self.action
        if f is not None:
            if self.onion.isChecked() and a and self.frame_i > 0:
                self.add_frame_sprite(a.frames[self.frame_i - 1], 0.3)
            self.add_frame_sprite(f)
            if self.show_clsn.isChecked():
                for kind, boxes in ((2, f.clsn2), (1, f.clsn1)):
                    col = CLSN_COLORS[kind]
                    for i, (x1, y1, x2, y2) in enumerate(boxes):
                        r = QGraphicsRectItem(rectf(x1, y1, x2, y2))
                        sel = self.view.sel == (kind, i)
                        r.setPen(cosmetic(col.lighter(150) if sel else col, 2 if sel else 1))
                        fill = QColor(col)
                        fill.setAlpha(90 if sel else 45)
                        r.setBrush(QBrush(fill))
                        self.scene.addItem(r)
        pen = axis_pen()
        self.scene.addLine(-lim, 0, lim, 0, pen)
        self.scene.addLine(0, -lim, 0, 40, pen)
        if self.view.flip != self.flip_view.isChecked():
            self.view.flip = self.flip_view.isChecked()
            self.view.set_zoom(self.view.zoom)
        self.scene.setSceneRect(QRectF(-lim, -lim, lim * 2, lim * 1.3))

    # ---- reproducción
    def toggle_play(self):
        if self.timer.isActive():
            self.stop()
        else:
            if not self.action or not self.action.frames:
                return
            self.tick = 0
            self.update_timer()
            self.timer.start()
            self.play_btn.setText(tr('⏸ Pausa'))

    def update_timer(self):
        sp = self.speed.currentData() or 1.0
        self.timer.setInterval(max(1, int(1000 / (60 * sp))))

    def stop(self):
        self.timer.stop()
        self.play_btn.setText(tr('▶ Reproducir'))

    def on_tick(self):
        a = self.action
        if not a or not a.frames:
            return self.stop()
        f = a.frames[self.frame_i]
        if f.time < 0:
            return self.stop()
        self.tick += 1
        if self.tick >= max(1, f.time):
            self.tick = 0
            nxt = self.frame_i + 1
            if nxt >= len(a.frames):
                nxt = a.loopstart if 0 <= a.loopstart < len(a.frames) else 0
            self.frame_i = nxt
            self._block = True
            self.slider.setValue(nxt)
            self.table.selectRow(nxt)
            self._block = False
            self.update_info()
            self.fill_boxes()
            self.redraw()

    def step(self, d):
        a = self.action
        if not a or not a.frames:
            return
        self.go_frame((self.frame_i + d) % len(a.frames))

    # ---- guardar
    def save(self):
        p = self.project()
        if not p or not p.air_loaded():
            return True
        try:
            p.backup(p.air.path)
            p.air.save()
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, tr('No pude guardar las animaciones: {0}').format(e))
            return False
        if not p.file_value("anim"):
            p.defs.set("Files", "anim", p.air.path.name)
            p.defs_dirty = True
        self.undo.setClean()
        return True
