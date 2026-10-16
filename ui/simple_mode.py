"""
Modo simple: el personaje por casillas. Pones los sprites de cada cosa (parado, caminar, golpes,
especiales, recibir golpes…), eliges voces y música, y el editor escribe solo las animaciones y el código.
"""
import re
from collections import Counter
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QObject, QRectF, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap, QTextCursor
from PyQt6.QtWidgets import (
    QTabWidget, QApplication, QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter, QToolButton, QVBoxLayout, QWidget,
)

from core import simple_gen as sg
from core.sff import Sprite, qimage_rgba
from i18n import tr
from ui import theme
from ui.common import APP_NAME, image_to_indices, sprite_qimage
from ui.motion import MOVE_CTRL, Motion, MoveControls

IMAGE_FILTER = 'Imágenes (*.png *.bmp *.gif *.pcx *.jpg *.jpeg *.tga *.webp)'
SPEEDS = [(2, 'Muy rápida'), (3, 'Rápida'), (4, 'Algo rápida'), (5, 'Normal'), (7, 'Lenta'), (10, 'Muy lenta')]
SOUND_FILTER = 'Música (*.ogg *.mp3 *.wav *.flac *.mid *.midi *.xm *.mod *.it *.s3m)'


def natural_key(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", Path(p).name)]


def muted(text, wrap=True):
    lab = QLabel(text)
    lab.setObjectName("CardPath")
    lab.setWordWrap(wrap)
    return lab


def title_label(text):
    lab = QLabel(text)
    lab.setObjectName("CardTitle")
    lab.setWordWrap(True)
    return lab


# ---------------------------------------------------------------- vista animada
class AnimPreview(QWidget):
    def __init__(self, sm, w=170, h=140):
        super().__init__()
        self.sm = sm
        self.frames = []      # [(g, n, tiempo, x, y)]
        self.hit = None
        self.empty_text = ""
        self.box = QRectF(-1, -1, 2, 2)
        self.boxes = None
        self.setMinimumSize(QSize(w, h))
        sm.previews.append(self)

    def is_hit(self, i):
        """¿Este cuadro pega? (hit puede ser un número o un conjunto de cuadros)"""
        if self.hit is None:
            return False
        if isinstance(self.hit, (set, frozenset, list, tuple)):
            return i in self.hit
        return i == self.hit

    def set_frames(self, frames, hit=None, empty_text="", boxes=None):
        self.frames = list(frames)
        self.boxes = boxes
        self.hit = hit
        self.empty_text = empty_text
        box = None
        for g, n, _t, x, y in self.frames:
            s = self.sm.sprite(g, n)
            if s is None:
                continue
            h, w = s.pixels().shape[:2]
            r = QRectF(x - s.x, y - s.y, w, h)
            box = r if box is None else box.united(r)
        self.box = box or QRectF(-1, -1, 2, 2)
        self.update()

    def current(self):
        if not self.frames:
            return None, None
        times = [(t if t > 0 else 30) for _g, _n, t, _x, _y in self.frames]
        total = sum(times)
        t = self.sm.tick % max(1, total)
        for i, d in enumerate(times):
            if t < d:
                return i, self.frames[i]
            t -= d
        return len(self.frames) - 1, self.frames[-1]

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.CANVAS))
        p.drawRoundedRect(r, 8, 8)
        i, fr = self.current()
        if fr is None:
            p.setPen(QColor(theme.MUTED))
            p.drawText(r.adjusted(8, 8, -8, -8), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       self.empty_text)
            p.end()
            return
        box = self.box
        sc = min((r.width() - 16) / max(1, box.width()), (r.height() - 16) / max(1, box.height()), 3.0)
        ox = r.center().x() - (box.left() + box.width() / 2) * sc
        oy = r.center().y() - (box.top() + box.height() / 2) * sc
        # suelo
        if box.top() < 0 <= box.bottom() + 1:
            p.setPen(QPen(QColor(255, 107, 53, 90), 1))
            p.drawLine(int(r.left() + 6), int(oy), int(r.right() - 6), int(oy))
        g, n, _t, x, y = fr
        s = self.sm.sprite(g, n)
        if s is not None:
            pm = self.sm.pixmap(g, n)
            if pm is not None:
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, sc < 1)
                p.drawPixmap(QRectF(ox + (x - s.x) * sc, oy + (y - s.y) * sc, pm.width() * sc, pm.height() * sc),
                             pm, QRectF(pm.rect()))
            if self.sm.show_boxes:
                from ui.align_dialog import draw_boxes
                bx = self.boxes[i] if self.boxes and i < len(self.boxes) and self.boxes[i] is not None else \
                    self.sm.auto_boxes_of(g, n, self.is_hit(i), getattr(self, "ref_kind", "S"))
                manual = getattr(self, "manual", None) or {}
                if i in manual:
                    bx = (manual[i], bx[1] if bx else [])
                elif getattr(getattr(self, "manual", None), "strict", False):
                    bx = ([], bx[1] if bx else [])
                if bx:
                    draw_boxes(p, bx[0], bx[1], ox + x * sc, oy + y * sc, sc, 200)
        if self.is_hit(i):
            p.setPen(QPen(QColor("#ff4d4d"), 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(2, 2, -2, -2), 8, 8)
            p.setPen(QColor("#ff8080"))
            p.drawText(r.adjusted(8, 4, -8, -4), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, "💥")
        p.setPen(QColor(theme.MUTED))
        p.drawText(r.adjusted(8, 4, -8, -4), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                   f"{i + 1}/{len(self.frames)}")
        p.end()


# ---------------------------------------------------------------- elegir sprites que ya tiene
class SpritePicker(QDialog):
    def __init__(self, sm, title, current=()):
        super().__init__(sm.main)
        self.sm = sm
        self.setWindowTitle(title)
        self.resize(820, 520)
        lay = QVBoxLayout(self)
        lay.addWidget(muted(tr('Elige un grupo y marca los cuadros en orden (Ctrl o Mayús para elegir varios). '
                               'Si no marcas ninguno, se usa el grupo entero.')))
        split = QSplitter()
        self.groups = QListWidget()
        self.groups.setIconSize(QSize(40, 40))
        self.grid = QListWidget()
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setIconSize(QSize(80, 80))
        self.grid.setGridSize(QSize(100, 110))
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        split.addWidget(self.groups)
        split.addWidget(self.grid)
        split.setSizes([220, 600])
        lay.addWidget(split, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        sff = sm.main.project.sff
        self.by_group = {}
        for s in sff.sprites:
            self.by_group.setdefault(s.group, []).append(s)
        want = Counter(g for g, _n in current).most_common(1)
        want = want[0][0] if want else None
        for g in sorted(self.by_group):
            lst = sorted(self.by_group[g], key=lambda s: s.number)
            it = QListWidgetItem(tr('Grupo {0} ({1})').format(g, len(lst)))
            it.setData(Qt.ItemDataRole.UserRole, g)
            pm = sm.pixmap(lst[0].group, lst[0].number)
            if pm is not None:
                it.setIcon(QIcon(pm.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)))
            self.groups.addItem(it)
            if g == want:
                self.groups.setCurrentItem(it)
        self.groups.currentItemChanged.connect(self.fill)
        if self.groups.currentItem() is None and self.groups.count():
            self.groups.setCurrentRow(0)
        self.fill()
        cur = set(current)
        for i in range(self.grid.count()):
            it = self.grid.item(i)
            if tuple(it.data(Qt.ItemDataRole.UserRole)) in cur:
                it.setSelected(True)

    def fill(self, *_a):
        self.grid.clear()
        it = self.groups.currentItem()
        if it is None:
            return
        g = it.data(Qt.ItemDataRole.UserRole)
        for s in sorted(self.by_group.get(g, []), key=lambda s: s.number):
            gi = QListWidgetItem(f"{s.group},{s.number}")
            gi.setData(Qt.ItemDataRole.UserRole, [s.group, s.number])
            pm = self.sm.pixmap(s.group, s.number)
            if pm is not None:
                gi.setIcon(QIcon(pm.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)))
            self.grid.addItem(gi)

    def keys(self):
        sel = [self.grid.item(i) for i in range(self.grid.count()) if self.grid.item(i).isSelected()]
        if not sel:
            sel = [self.grid.item(i) for i in range(self.grid.count())]
        return [tuple(it.data(Qt.ItemDataRole.UserRole)) for it in sel]


# ---------------------------------------------------------------- casilla de cuadros
class FramesBox(QWidget):
    """Vista animada + botones para poner los sprites de una animación."""
    changed = pyqtSignal()

    def __init__(self, sm, dialog_title, group_hint, default_time=5, show_hit=False, fallback=None,
                 hit_label=None, small=False):
        super().__init__()
        self.sm = sm
        self.dialog_title = dialog_title
        self.group_hint = group_hint
        self.default_time = default_time
        self.show_hit = show_hit
        self.fallback = fallback
        self.entry = {}
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        self.preview = AnimPreview(sm, 150 if small else 180, 110 if small else 150)
        v.addWidget(self.preview, 1)
        self.status = muted("")
        v.addWidget(self.status)
        row = QGridLayout()
        row.setSpacing(4)
        b4 = QPushButton(tr('🧩 De una hoja'))
        b4.setToolTip(tr('Cortar los cuadros de una hoja de sprites (sprite sheet).'))
        b4.clicked.connect(self.on_sheet)
        b1 = QPushButton(tr('📂 Imágenes'))
        b1.setToolTip(tr('Poner imágenes de tu computadora (PNG, BMP, GIF…), en orden por nombre.'))
        b1.clicked.connect(self.on_import)
        b2 = QPushButton(tr('🖼 Sprites'))
        b2.setToolTip(tr('Usar sprites que el personaje ya tiene.'))
        b2.clicked.connect(self.on_pick)
        b3 = QPushButton(tr('🗑 Vaciar'))
        b3.setToolTip(tr('Dejar esta casilla vacía'))
        b3.clicked.connect(self.on_clear)
        b5 = QPushButton(tr('✋ Alinear y ver cajas'))
        b5.setToolTip(tr('Mueve cada cuadro a su lugar si quedaron desalineados, y mira las cajas de golpe.'))
        b5.clicked.connect(self.on_align)
        b6 = QPushButton(tr('↔ Voltear'))
        b6.setToolTip(tr('Espejo: voltea los cuadros de izquierda a derecha (para imágenes u hojas que miran '
                         'hacia la izquierda). El personaje tiene que mirar hacia la derecha.'))
        b6.clicked.connect(self.on_mirror)
        row.addWidget(b1, 0, 0)
        row.addWidget(b4, 0, 1)
        row.addWidget(b2, 1, 0)
        row.addWidget(b3, 1, 1)
        row.addWidget(b5, 2, 0)
        row.addWidget(b6, 2, 1)
        # caja de daño (la roja): automática o dibujada a mano
        self.box_row = QWidget()
        br = QHBoxLayout(self.box_row)
        br.setContentsMargins(0, 0, 0, 0)
        bl = QLabel(tr('🟥 Caja de daño:'))
        bl.setToolTip(tr('La caja roja: la parte del dibujo que le hace daño al rival.'))
        self.box_mode = QComboBox()
        self.box_mode.addItem(tr('Automática'), "auto")
        self.box_mode.addItem(tr('A mano'), "manual")
        self.box_mode.setToolTip(tr('Automática: el editor la pone sola en la punta de lo que pega (el puño, el '
                                    'pie…). A mano: solo pega lo que dibujes tú.'))
        self.box_mode.currentIndexChanged.connect(self.on_box_mode)
        self.box_btn = QPushButton(tr('✏ Dibujar…'))
        self.box_btn.setToolTip(tr('Dibuja o mueve la caja de daño cuadro por cuadro. Al guardar, la caja de esta '
                                   'animación pasa a «A mano».'))
        self.box_btn.clicked.connect(self.on_hitbox)
        br.addWidget(bl)
        br.addWidget(self.box_mode, 1)
        br.addWidget(self.box_btn)
        self.box_row.setVisible(show_hit)
        row.addWidget(self.box_row, 4, 0, 1, 2)
        # cajas del cuerpo (las azules, donde le pueden pegar): automáticas o dibujadas a mano
        self.hurt_row = QWidget()
        hr = QHBoxLayout(self.hurt_row)
        hr.setContentsMargins(0, 0, 0, 0)
        hl = QLabel(tr('🟦 Cuerpo:'))
        hl.setToolTip(tr('Las cajas azules: la parte del dibujo donde le pueden pegar.'))
        self.hurt_mode = QComboBox()
        self.hurt_mode.addItem(tr('Automático'), "auto")
        self.hurt_mode.addItem(tr('A mano'), "manual")
        self.hurt_mode.setToolTip(tr('Automático: el editor las pone solas (1 o 2 cajas, se escoge en «👤 Personaje»). '
                                     'A mano: solo cuenta lo que dibujes tú.'))
        self.hurt_mode.currentIndexChanged.connect(self.on_hurt_mode)
        self.hurt_btn = QPushButton(tr('✏ Dibujar…'))
        self.hurt_btn.setToolTip(tr('Dibuja o mueve las cajas del cuerpo cuadro por cuadro. Al guardar, el cuerpo '
                                    'de esta animación pasa a «A mano».'))
        self.hurt_btn.clicked.connect(self.on_hurtbox)
        hr.addWidget(hl)
        hr.addWidget(self.hurt_mode, 1)
        hr.addWidget(self.hurt_btn)
        row.addWidget(self.hurt_row, 5, 0, 1, 2)
        self.copy_btn = QPushButton(tr('📋 Rehacer en el modo simple'))
        self.copy_btn.setToolTip(tr('Cambia el golpe del personaje por uno hecho con el modo simple (con la misma '
                                    'animación y daño). Ojo: se pierde lo especial de su código, como sus combos. '
                                    'Vuelve si vacías la casilla.'))
        self.copy_btn.clicked.connect(self.on_copy_original)
        self.copy_btn.hide()
        row.addWidget(self.copy_btn, 3, 0, 1, 2)
        row.setColumnStretch(0, 1)
        row.setColumnStretch(1, 1)
        v.addLayout(row)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self.speed = QSpinBox()
        self.speed.setRange(1, 99)
        self.speed.setSuffix(" " + tr('ticks por cuadro'))
        self.speed.setToolTip(tr('Cuánto dura cada cuadro (60 ticks = 1 segundo): menos = más rápida. '
                                 'Más rápida 2 · normal 5 · lenta 7 · muy lenta 10.'))
        self.speed.setKeyboardTracking(False)
        self.speed.valueChanged.connect(self.on_speed)
        form.addRow(tr('Rapidez:'), self.speed)
        self.hit = QSpinBox()
        self.hit.setRange(0, 99)
        self.hit.setSpecialValueText(tr('Automático'))
        self.hit.valueChanged.connect(self.on_hit)
        if show_hit:
            form.addRow(hit_label or tr('Pega en el cuadro:'), self.hit)
        v.addLayout(form)

    def bind(self, entry):
        self.entry = entry
        self.speed.blockSignals(True)
        self.speed.setValue(int(entry.get("time", self.default_time)))
        self.speed.blockSignals(False)
        self.hit.blockSignals(True)
        self.hit.setValue(int(entry.get("hit", 0) or 0))
        self.hit.blockSignals(False)
        self.refresh()

    def keys(self):
        return [(int(g), int(n)) for g, n in self.entry.get("frames", [])]

    def refresh(self):
        keys = self.keys()
        p = self.sm.main.project
        off_key = getattr(self, "off_key", None)
        if off_key is not None and self.sm.is_off(off_key):
            self.refresh_off(off_key, keys)
            return
        for w in self.findChildren(QPushButton):
            w.setEnabled(True)
        self.copy_btn.hide()
        self.orig_mode = None
        prov = getattr(self, "orig_provider", None)
        orig = prov() if (prov is not None and not keys) else None
        if orig:
            self.orig_mode = orig if isinstance(orig, list) else [orig]
            self.show_original(self.orig_mode)
            return
        if keys:
            t = int(self.entry.get("time", self.default_time))
            hit = sg.hit_frame_of(self.entry, keys, p.sff.index()) if self.show_hit else None
            manual = {int(f) - 1 for f in self.entry.get("hit_frames") or [] if 1 <= int(f) <= len(keys)}
            if self.show_hit and manual and getattr(self, "multi_hit", False):
                hit = manual
            self.preview.ref_kind = getattr(self, "ref_kind", "S")
            self.preview.manual = sg.manual_boxes(self.entry)
            self.sync_box_mode()
            self.sync_hurt_mode()
            offs = [0] * len(keys)
            if getattr(self, "step_aware", False) and self.entry.get("step"):
                hf_ = hit if isinstance(hit, int) else sg.hit_frame_of(self.entry, keys, p.sff.index())
                offs = sg.step_offsets(self.entry, len(keys), hf_)
            self.preview.set_frames([(g, n, t, offs[i], 0) for i, (g, n) in enumerate(keys)], hit)
            self.status.setText(tr('✅ {0} cuadro(s)').format(len(keys)))
            self.hit.setMaximum(len(keys))
            self.report("ok", tr('✅ {0} cuadro(s)').format(len(keys)), keys[0])
        else:
            a = p.air.find(self.fallback) if (p and self.fallback is not None) else None
            src = sg.FALLBACK.get(getattr(self, "slot_key", None))
            src_on = bool(src and self.sm.fallback_source(self.slot_key)[0])
            if a is not None and a.frames and src_on:
                self.preview.set_frames([(f.group, f.number, f.time, f.x, f.y) for f in a.frames],
                                        boxes=[(f.clsn1, f.clsn2) for f in a.frames])
                self.status.setText(tr('Usa «{0}»{1}.').format(tr(sg.ANIM_SLOTS[src[0]][1]),
                                                              tr(' al revés') if src[1] else ""))
                self.report("ok", "✅ " + self.status.text(), (a.frames[0].group, a.frames[0].number))
            elif getattr(self, "slot_key", None) == "crouch_idle" and a is not None and a.frames:
                self.preview.set_frames([(f.group, f.number, f.time, f.x, f.y) for f in a.frames],
                                        boxes=[(f.clsn1, f.clsn2) for f in a.frames])
                self.status.setText(tr('Usa el último cuadro de «Agacharse» (quieto).'))
                self.report("info", "ℹ " + tr('Opcional'), (a.frames[0].group, a.frames[0].number))
            elif a is not None and a.frames and not self.sm.is_placeholder(a):
                self.preview.set_frames([(f.group, f.number, f.time, f.x, f.y) for f in a.frames],
                                        boxes=[(f.clsn1, f.clsn2) for f in a.frames])
                self.status.setText(tr('Usa lo que ya tenía (acción {0}).').format(self.fallback))
                self.report("info", "ℹ " + tr('Usa lo que ya tenía'), (a.frames[0].group, a.frames[0].number))
            elif getattr(self, "slot_key", None) in sg.OPTIONAL_EMPTY or getattr(self, "optional", False):
                self.preview.set_frames([], empty_text=tr('Opcional'))
                self.status.setText(tr('⚪ Opcional: si la llenas, sale al azar con las demás.')
                                    if getattr(self, "slot_key", None) in sg.EXTRA_POSES else tr('⚪ Opcional'))
                self.report("info", "ℹ " + tr('Opcional'))
            else:
                self.preview.set_frames([], empty_text=tr('Vacía\nPon imágenes o sprites'))
                self.status.setText(tr('⚪ Vacía'))
                self.report("empty", tr('⚠ Falta poner sprites'))

    def show_original(self, origs):
        """La casilla está vacía pero el personaje ya tiene ese golpe en su código: se ve el suyo, y lo que se
        le ponga (imágenes, sprites, rapidez) cambia su animación sin tocar su código."""
        p = self.sm.main.project
        orig = origs[0]
        a = p.air.find(orig.anim) if orig.anim is not None else None
        if a is not None and a.frames:
            self.speed.blockSignals(True)
            self.speed.setValue(typical_time(a.frames, self.default_time))
            self.speed.blockSignals(False)
        thumb = None
        if a is not None and a.frames:
            self.preview.set_frames([(f.group, f.number, f.time, f.x, f.y) for f in a.frames],
                                    boxes=[(f.clsn1, f.clsn2) for f in a.frames])
            thumb = (a.frames[0].group, a.frames[0].number)
        else:
            self.preview.set_frames([], empty_text=tr('Ya lo tiene'))
        self.status.setText(tr('Ya lo tiene: «{0}» (estado {1}). Si le pones imágenes o sprites, o le cambias la '
                               'rapidez, se cambia su animación sin tocar su código ni sus combos.').format(
            orig.label, orig.state))
        self.copy_btn.setVisible(a is not None and bool(a.frames) and getattr(self, "orig_key", None) is not None)
        self.report("info", "ℹ " + tr('Ya lo tiene: «{0}»').format(orig.label), thumb)

    def on_copy_original(self):
        if QMessageBox.question(self, APP_NAME, tr(
                'El golpe se va a rehacer con el modo simple. Se pierde lo especial de su código (combos, '
                'cancelaciones, efectos). Para cambiarle solo la animación o el daño no hace falta: ponle '
                'imágenes o sprites aquí mismo. ¿Rehacerlo de todos modos?')) != QMessageBox.StandardButton.Yes:
            return
        orig = self.sm.original_move(getattr(self, "orig_key", None))
        p = self.sm.main.project
        a = p.air.find(orig.anim) if (orig and orig.anim is not None) else None
        if a is None or not a.frames:
            return
        self.entry["frames"] = [[f.group, f.number] for f in a.frames]
        self.entry["time"] = typical_time(a.frames, self.default_time)
        hit = next((i for i, f in enumerate(a.frames) if f.clsn1), None)
        if hit is not None:
            self.entry["hit"] = hit + 1
        if orig.damage is not None:
            self.entry["damage"] = int(orig.damage)
        self.bind(self.entry)
        self.changed.emit()
        if hasattr(self, "after_copy"):
            self.after_copy()

    def refresh_off(self, off_key, keys):
        """El personaje no tiene este movimiento: se dice qué se usa en su lugar."""
        p = self.sm.main.project
        sub = sg.SUBSTITUTE.get(off_key)
        if sub:
            text = tr('⭘ No lo tiene · usa «{0}»').format(tr(sg.ANIM_SLOTS[sub[0]][1]))
        elif off_key == "jump_fwd":
            text = tr('⭘ No lo tiene · usa el salto normal')
        else:
            text = tr('⭘ No lo tiene')
        a = p.air.find(self.fallback) if (p and self.fallback is not None and (sub or off_key == "jump_fwd")) else None
        if a is not None and a.frames:
            self.preview.set_frames([(f.group, f.number, f.time, f.x, f.y) for f in a.frames],
                                    boxes=[(f.clsn1, f.clsn2) for f in a.frames])
            thumb = (a.frames[0].group, a.frames[0].number)
        else:
            self.preview.set_frames([], empty_text=tr('No lo tiene'))
            thumb = None
        self.status.setText(text)
        for w in self.findChildren(QPushButton):
            w.setEnabled(False)
        self.report("off", text, thumb)

    def report(self, state, text, key=None):
        hook = getattr(self, "status_hook", None)
        if hook is not None:
            hook(state, text, key)

    def set_keys(self, keys, group=None):
        if getattr(self, "orig_mode", None):
            self.sm.replace_original_anims(self.orig_mode, keys, int(self.speed.value() or self.default_time))
            self.refresh()
            return
        if [list(k) for k in keys] != self.entry.get("frames"):
            self.entry.pop("boxes", None)      # otros cuadros: las cajas hechas a mano eran de los de antes
            if self.entry.pop("hurt", None) is not None or self.entry.pop("hurt_mode", None):
                self.entry.pop("hurt_mode", None)
                sg.set_hurt(self.sm.cfg)
        self.entry["frames"] = [list(k) for k in keys]
        if group is not None:
            self.entry["group"] = group
        self.entry.setdefault("time", self.default_time)
        if self.entry.get("hit", 0) and self.entry["hit"] > len(keys):
            self.entry["hit"] = 0
        self.refresh()
        self.changed.emit()

    def on_import(self):
        res = self.sm.import_frames(self.dialog_title, self.group_hint, self.keys(), self.entry.get("group"))
        if res:
            keys, group = res
            self.set_keys(keys, group)

    def on_align(self):
        p = self.sm.main.project
        if not p:
            return
        keys = self.keys()
        time = int(self.entry.get("time", self.default_time))
        hit = None
        num = self.fallback
        if getattr(self, "orig_mode", None):
            num = self.orig_mode[0].anim
        if keys:
            if self.show_hit:
                hit = sg.hit_frame_of(self.entry, keys, p.sff.index())
        else:
            a = p.air.find(num) if num is not None else None
            if a is None or not a.frames or self.sm.is_placeholder(a):
                QMessageBox.information(self, APP_NAME, tr('Primero pon los cuadros de esta casilla.'))
                return
            keys = [(f.group, f.number) for f in a.frames]
            time = next((f.time for f in a.frames if f.time > 0), 5)
        from ui.align_dialog import AlignDialog
        fn = getattr(self, "align_mode_fn", None)
        if hit is not None and self.keys():
            hit = self.hit_indices(keys)
        dlg = AlignDialog(self.sm, self.dialog_title, keys, hit,
                          mode=fn() if fn else getattr(self, "align_mode", "ground"),
                          manual=sg.manual_boxes(self.entry) if self.keys() else None,
                          ref=self.sm.ref_sprite(getattr(self, "ref_kind", "S")) if hit is not None else None)
        dlg.times = [max(1, time)] * len(dlg.keys)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        ch = dlg.changes()
        if not ch:
            return
        old = self.sm.apply_axes(ch)
        if self.keys():
            self.changed.emit()
        else:
            self.sm.refit_action_boxes(num, ch, old)
        self.refresh()

    def on_sheet(self):
        res = self.sm.cut_frames(self.dialog_title, self.group_hint, self.keys(), self.entry.get("group"))
        if res:
            keys, group = res
            self.set_keys(keys, group)

    def on_pick(self):
        if not self.sm.main.project:
            return
        dlg = SpritePicker(self.sm, self.dialog_title, self.keys())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            keys = dlg.keys()
            if keys:
                self.entry.pop("group", None)
                self.set_keys(keys)

    def on_clear(self):
        p = self.sm.main.project
        if not p:
            return
        old = self.keys()
        if not old and getattr(self, "orig_mode", None):
            QMessageBox.information(self, APP_NAME, tr('Este movimiento es del personaje. Para quitarlo, quítale el '
                                                       'tick «Lo tiene».'))
            return
        if not old:
            a = p.air.find(self.fallback) if self.fallback is not None else None
            if a is None or self.sm.is_placeholder(a):
                return
            if QMessageBox.question(self, APP_NAME, tr('¿Quitar la animación que ya tenía (acción {0})? Se queda '
                                                       'con la figura provisional.').format(self.fallback)) != \
                    QMessageBox.StandardButton.Yes:
                return
        self.sm.forget_sprites(old, self.entry.get("group"))
        self.entry["frames"] = []
        self.entry["hit"] = 0
        self.entry.pop("group", None)
        self.changed.emit()
        self.refresh()

    def on_speed(self, _i):
        if getattr(self, "orig_mode", None):
            self.sm.retime_originals(self.orig_mode, int(self.speed.value()))
            self.refresh()
            return
        self.entry["time"] = int(self.speed.value())
        self.refresh()
        if self.keys():
            self.changed.emit()

    def hit_indices(self, keys):
        """Los cuadros que pegan (desde 0), como los pone el código."""
        sp = self.entry
        if getattr(self, "multi_hit", False):
            manual = sorted({int(f) - 1 for f in sp.get("hit_frames") or [] if 1 <= int(f) <= len(keys)})
            if manual:
                return set(manual)
            hf = sg.hit_frame_of(sp, keys, self.sm.main.project.sff.index())
            return set(range(hf, len(keys))) if int(sg.spec(sp, "hits") or 1) > 1 else {hf}
        return {sg.hit_frame_of(sp, keys, self.sm.main.project.sff.index())}

    def on_hitbox(self):
        keys = self.keys()
        if not keys:
            QMessageBox.information(self, APP_NAME, tr('Primero pon los cuadros de esta casilla.'))
            self.sync_box_mode()
            return
        from ui.hitbox_editor import HitboxEditor
        dlg = HitboxEditor(self.sm, self.dialog_title, keys, self.hit_indices(keys), self.entry,
                           getattr(self, "ref_kind", "S"))
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.result is None:
            self.sync_box_mode()
            return
        self.entry["boxes"] = dlg.result
        self.entry["box_mode"] = "manual"
        self.sync_box_mode()
        self.refresh()
        self.changed.emit()

    def on_hurtbox(self):
        keys = self.keys()
        if not keys:
            QMessageBox.information(self, APP_NAME, tr('Primero pon los cuadros de esta casilla.'))
            self.sync_hurt_mode()
            return
        from ui.hitbox_editor import HitboxEditor
        hits = self.hit_indices(keys) if self.show_hit else set()
        dlg = HitboxEditor(self.sm, self.dialog_title, keys, hits, self.entry, getattr(self, "ref_kind", "S"),
                           body=True)
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.result is None:
            self.sync_hurt_mode()
            return
        self.entry["hurt"] = dlg.result
        self.entry["hurt_mode"] = "manual"
        self.sync_hurt_mode()
        self.sm.hurt_changed()

    def sync_hurt_mode(self):
        if not hasattr(self, "hurt_mode"):
            return
        self.hurt_mode.blockSignals(True)
        self.hurt_mode.setCurrentIndex(1 if self.entry.get("hurt_mode") == "manual" else 0)
        self.hurt_mode.blockSignals(False)

    def on_hurt_mode(self, _i):
        mode = self.hurt_mode.currentData()
        if mode == "auto":
            if self.entry.get("hurt_mode") != "manual":
                return
            self.entry["hurt_mode"] = "auto"      # lo dibujado se guarda por si vuelves a «A mano»
            self.sm.hurt_changed()
            return
        if self.entry.get("hurt"):
            self.entry["hurt_mode"] = "manual"
            self.sm.hurt_changed()
        else:
            self.on_hurtbox()                     # sin nada dibujado: se abre para dibujarlas

    def sync_box_mode(self):
        if not hasattr(self, "box_mode"):
            return
        m = sg.box_mode(self.entry)
        self.box_mode.blockSignals(True)
        self.box_mode.setCurrentIndex(1 if m in ("manual", "mixed") else 0)
        self.box_mode.blockSignals(False)

    def on_box_mode(self, _i):
        mode = self.box_mode.currentData()
        if mode == "auto":
            if sg.box_mode(self.entry) == "auto":
                return
            self.entry["box_mode"] = "auto"      # lo dibujado se guarda por si vuelves a «A mano»
            self.refresh()
            self.changed.emit()
            return
        if self.entry.get("boxes"):
            self.entry["box_mode"] = "manual"
            self.refresh()
            self.changed.emit()
        else:
            self.on_hitbox()                     # sin nada dibujado: se abre para dibujarla

    def on_mirror(self):
        keys = self.keys()
        if not keys:
            QMessageBox.information(self, APP_NAME, tr('Primero pon los cuadros de esta casilla.'))
            return
        if not self.entry.get("group"):
            # sprites escogidos de los que ya tenía: puede que otra animación también los use
            if QMessageBox.question(self, APP_NAME, tr(
                    'Estos sprites los escogiste de los que ya tenía el personaje: si otra animación los usa, '
                    'también se voltean ahí. ¿Voltearlos?')) != QMessageBox.StandardButton.Yes:
                return
        self.sm.mirror_sprites(keys)
        if self.entry.get("boxes"):
            self.entry.pop("boxes", None)      # los dibujos cambiaron de lado: las cajas a mano ya no sirven
        if self.entry.get("hurt"):
            self.entry.pop("hurt", None)
            self.entry.pop("hurt_mode", None)
            sg.set_hurt(self.sm.cfg)
        self.refresh()
        self.changed.emit()

    def on_hit(self, v):
        self.entry["hit"] = int(v)
        self.refresh()
        if self.keys():
            self.changed.emit()


def card(title, desc=None):
    box = QFrame()
    box.setObjectName("Card")
    v = QVBoxLayout(box)
    v.setContentsMargins(10, 10, 10, 10)
    v.setSpacing(6)
    v.addWidget(title_label(title))
    if desc:
        v.addWidget(muted(desc))
    return box, v


def typical_time(frames, default):
    """Rapidez de una animación del personaje: la duración más común de sus cuadros."""
    ts = sorted(f.time for f in frames if f.time > 0)
    return max(1, ts[len(ts) // 2]) if ts else default


def state_color(state):
    return {"ok": theme.OK, "info": theme.INFO, "empty": theme.WARN}.get(state, theme.MUTED)


class FoldHead(QWidget):
    clicked = pyqtSignal()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class FoldCard(QFrame):
    """Casilla que se abre y se cierra. Cerrada muestra un dibujito y si le falta algo."""

    def __init__(self, sm, title, desc=None):
        super().__init__()
        self.sm = sm
        self.state = "empty"
        self.page = None
        self.setObjectName("Card")
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(4)
        head = FoldHead()
        head.setCursor(Qt.CursorShape.PointingHandCursor)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        self.arrow = QLabel("▸")
        self.arrow.setFixedWidth(14)
        hl.addWidget(self.arrow)
        self.thumb = QLabel()
        self.thumb.setFixedSize(36, 36)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setObjectName("Thumb")
        hl.addWidget(self.thumb)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.title_lbl = title_label(title)
        self.status_lbl = QLabel()
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("font-size: 9pt;")
        col.addWidget(self.title_lbl)
        col.addWidget(self.status_lbl)
        hl.addLayout(col, 1)
        self.hl = hl
        self.tick = None
        head.clicked.connect(lambda: self.set_open(not self.body.isVisibleTo(self)))
        root.addWidget(head)
        self.body = QWidget()
        self.v = QVBoxLayout(self.body)
        self.v.setContentsMargins(0, 4, 0, 0)
        self.v.setSpacing(6)
        if desc:
            self.v.addWidget(muted(desc))
        root.addWidget(self.body)
        self.body.hide()

    def set_open(self, on):
        self.body.setVisible(bool(on))
        self.arrow.setText("▾" if on else "▸")

    def add_tick(self, key):
        """Casilla opcional: con el tick quitado el personaje no tiene ese movimiento."""
        self.tick = QCheckBox(tr('Lo tiene'))
        self.tick.setChecked(True)
        self.tick.setToolTip(tr('Quítale el tick si tu personaje no tiene este movimiento. Así no te pide '
                                'sprites y el juego usa otra animación en su lugar (o no lo deja hacer).'))
        self.tick.toggled.connect(lambda on: self.sm.set_off(key, not on))
        self.hl.addWidget(self.tick, 0, Qt.AlignmentFlag.AlignTop)

    def bind_tick(self, key):
        if self.tick is not None:
            self.tick.blockSignals(True)
            self.tick.setChecked(not self.sm.is_off(key))
            self.tick.blockSignals(False)

    def set_status(self, state, text, key=None):
        self.state = state
        col = state_color(state)
        self.status_lbl.setText(f"<span style='color:{col}'>{text}</span>")
        self.title_lbl.setEnabled(state != "off")
        pm = self.sm.pixmap(*key) if key is not None else None
        if pm is not None:
            self.thumb.setPixmap(pm.scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
        else:
            self.thumb.clear()
            self.thumb.setText("⚠" if state == "empty" else "")
        if self.page is not None:
            self.page.update_counts()


class Page(QScrollArea):
    """Página del modo simple con título y secciones."""

    def __init__(self, sm, title, intro):
        super().__init__()
        self.sm = sm
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        self.setWidget(host)
        self.lay = QVBoxLayout(host)
        self.lay.setContentsMargins(4, 4, 12, 12)
        self.lay.setSpacing(10)
        t = QLabel(title)
        t.setStyleSheet("font-size: 17pt; font-weight: 800;")
        self.lay.addWidget(t)
        self.lay.addWidget(muted(intro))
        self.warn = QLabel()
        self.warn.setWordWrap(True)
        self.warn.setObjectName("Warn")
        self.warn.hide()
        self.lay.addWidget(self.warn)

    def section(self, text, cols=4):
        lab = QLabel(text)
        lab.setObjectName("SectionTitle")
        self.lay.addWidget(lab)
        self._sections = getattr(self, "_sections", [])
        self._sections.append((lab, text, []))
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        for c in range(cols):
            grid.setColumnStretch(c, 1)
        self.lay.addWidget(w)
        return grid

    def fold(self, card_, grid, r, c):
        """Pone una casilla plegable en la sección actual."""
        card_.page = self
        self._sections[-1][2].append(card_)
        self.folds = getattr(self, "folds", []) + [card_]
        grid.addWidget(card_, r, c, Qt.AlignmentFlag.AlignTop)

    def update_counts(self):
        for lab, text, cards in getattr(self, "_sections", []):
            if not cards:
                continue
            done = sum(1 for c in cards if c.state != "empty")
            col = theme.OK if done == len(cards) else theme.MUTED
            lab.setText(f"{text}  <span style='font-size:10pt; color:{col}'>"
                        f"{tr('{0} de {1} listas').format(done, len(cards))}</span>")

    def set_all_open(self, on):
        for c in getattr(self, "folds", []):
            c.set_open(on)

    def finish(self):
        self.lay.addStretch(1)

    def activated(self):
        self.sm.refresh_page(self)



# ---------------------------------------------------------------- páginas
class AnimsPage(Page):
    def __init__(self, sm, title, intro, sections):
        super().__init__(sm, title, intro)
        self.boxes = {}
        self.moves = {}
        for sec_key, sec_title, slots in sg.ANIM_SECTIONS:
            if sec_key not in sections:
                continue
            grid = self.section(tr(sec_title))
            for i, (key, stitle, desc, group, forms) in enumerate(slots):
                box = FoldCard(sm, tr(stitle), tr(desc))
                v = box.v
                fb = FramesBox(sm, tr(stitle), group, fallback=forms[0][1])
                from core.autoalign import mode_for_slot
                fb.align_mode = mode_for_slot("anim", key)
                fb.status_hook = box.set_status
                fb.slot_key = key
                if key in sg.OPTIONAL_ANIMS:
                    fb.off_key = key
                    box.add_tick(key)
                fb.changed.connect(lambda key=key: sm.anim_slot_changed(key))
                v.addWidget(fb, 1)
                if key in MOVE_CTRL:
                    mc = MoveControls(sm, key)
                    v.addWidget(mc)
                    self.moves[key] = mc
                self.fold(box, grid, i // 4, i % 4)
                self.boxes[key] = (box, fb)
        self.finish()

    def bind(self, cfg):
        for key, (box, fb) in self.boxes.items():
            box.bind_tick(key)
            fb.bind(cfg["anims"].setdefault(key, {}))
        self.bind_moves()

    def bind_moves(self):
        self.sm.motion.forget()
        for mc in self.moves.values():
            mc.bind()


class RepeatDialog(QDialog):
    """«Al apretar otra vez»: hasta 3 animaciones más para el mismo botón apretado seguido."""

    def __init__(self, sm, key, title, pos, entry):
        super().__init__(sm.main)
        self.sm, self.entry = sm, entry
        self.setWindowTitle(tr('🔁 Al apretar otra vez: {0}').format(title))
        self.resize(980, 560)
        lay = QVBoxLayout(self)
        lay.addWidget(muted(tr('Si aprietas el mismo botón otra vez mientras da el golpe (después del cuadro que '
                               'pega), sale la animación 2; otra vez, la 3… Con una sola animación más y «vuelve a '
                               'la primera», alterna entre las dos mientras sigas apretando.')))
        row = QHBoxLayout()
        more = list(entry.get("more") or [])
        while len(more) < 3:
            more.append({})
        entry["more"] = more
        _p, _b, strength, _k, base = sg.normal_info(key)
        for j in range(3):
            m = more[j]
            col = QVBoxLayout()
            col.addWidget(title_label(tr('Animación {0}').format(j + 2)))
            fb = FramesBox(sm, f"{title} ({j + 2})", base + 1 + j, default_time=3 + strength, show_hit=True,
                           small=True)
            fb.align_mode = "air" if pos == "A" else "feet"
            fb.ref_kind = pos
            fb.bind(m)
            fb.changed.connect(sm.moves_changed)
            col.addWidget(fb, 1)
            dmg = QSpinBox()
            dmg.setRange(0, 999)
            dmg.setValue(int(m.get("damage", entry.get("damage", sg.BASE_DAMAGE[key.split("_")[1]]))))
            dmg.valueChanged.connect(lambda v, m=m: (m.__setitem__("damage", int(v)), sm.moves_changed()))
            f = QFormLayout()
            f.addRow(tr('Daño:'), dmg)
            col.addLayout(f)
            w = QWidget()
            w.setLayout(col)
            row.addWidget(w, 1)
        lay.addLayout(row, 1)
        self.need_hit = QCheckBox(tr('Solo si el golpe anterior pegó (o lo cubrieron)'))
        self.need_hit.setChecked(bool(entry.get("more_hit")))
        self.need_hit.toggled.connect(lambda on: (entry.__setitem__("more_hit", bool(on)), sm.moves_changed()))
        self.cycle = QCheckBox(tr('Al terminar la última, vuelve a la primera (alterna mientras sigas apretando)'))
        self.cycle.setChecked(bool(entry.get("more_cycle", True)))
        self.cycle.toggled.connect(lambda on: (entry.__setitem__("more_cycle", bool(on)), sm.moves_changed()))
        lay.addWidget(self.need_hit)
        lay.addWidget(self.cycle)
        close = QPushButton(tr('Cerrar'))
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)


class AttacksPage(Page):
    def __init__(self, sm):
        super().__init__(sm, tr('👊 Golpes'), tr(
            'Puños con x, y, z (débil, medio, fuerte) y patadas con a, b, c. Pon la animación de cada golpe y '
            'el editor le pone las cajas, el daño y el código. El cuadro con borde rojo es el que pega '
            '(se elige solo: el que más se estira; lo puedes cambiar).'))
        self.boxes = {}
        self.cards = {}
        self.steps = {}
        self.more_btns = {}
        for pos, ptitle, _base in sg.POSITIONS:
            grid = self.section(tr(ptitle), cols=3)
            for i, b in enumerate(sg.BUTTONS):
                key = sg.normal_key(pos, b)
                _p, _b, strength, kick, base = sg.normal_info(key)
                t = f"{tr(sg.NORMAL_NAMES[b])}  ·  {b}"
                box = FoldCard(sm, t)
                v = box.v
                fb = FramesBox(sm, t, base, default_time=3 + strength, show_hit=True, small=True)
                fb.align_mode = "air" if pos == "A" else "feet"
                fb.ref_kind = pos
                fb.status_hook = box.set_status
                fb.orig_key = key
                fb.orig_provider = lambda key=key: sm.original_move(key)
                fb.after_copy = lambda key=key: self.bind_damage(key)
                if key in sg.OPTIONAL_MOVES:
                    fb.off_key = key
                    box.add_tick(key)
                fb.changed.connect(sm.moves_changed)
                v.addWidget(fb, 1)
                dmg = QSpinBox()
                dmg.setRange(0, 999)
                dmg.setKeyboardTracking(False)
                dmg.valueChanged.connect(lambda val, key=key: self.on_damage(key, val))
                f = QFormLayout()
                f.addRow(tr('Daño:'), dmg)
                if pos != "A":
                    fb.step_aware = True
                    srow = QHBoxLayout()
                    step = QSpinBox()
                    step.setRange(-200, 300)
                    step.setSuffix(" px")
                    step.setSpecialValueText(tr('No se mueve'))
                    step.setKeyboardTracking(False)
                    step.setToolTip(tr('Cuánto avanza el personaje mientras da el golpe (un paso adelante). '
                                       'Negativo: retrocede. Se ve en la vista de arriba y en el juego.'))
                    sfr = QSpinBox()
                    sfr.setRange(0, 99)
                    sfr.setPrefix(tr('cuadro') + " ")
                    sfr.setSpecialValueText(tr('hasta el golpe'))
                    sfr.setToolTip(tr('Desde qué cuadro avanza (hasta el cuadro que pega). «hasta el golpe»: '
                                      'avanza en el cuadro de antes del golpe y en el del golpe.'))
                    sfr.setKeyboardTracking(False)
                    step.valueChanged.connect(lambda _v, key=key: self.on_step(key))
                    sfr.valueChanged.connect(lambda _v, key=key: self.on_step(key))
                    srow.addWidget(step, 1)
                    srow.addWidget(sfr, 1)
                    f.addRow(tr('Avanza:'), srow)
                    self.steps[key] = (step, sfr)
                v.addLayout(f)
                more = QPushButton()
                more.setToolTip(tr('Otras animaciones al apretar el mismo botón otra vez (seguido): golpes '
                                   'distintos uno tras otro, o alternar entre dos.'))
                more.clicked.connect(lambda _c=False, key=key, t=t, pos=pos: self.on_more(key, t, pos))
                v.addWidget(more)
                self.more_btns[key] = more
                self.fold(box, grid, i // 3, i % 3)
                self.boxes[key] = (fb, dmg)
                self.cards[key] = box
        grid = self.section(tr('Agarre'), cols=2)
        box = FoldCard(sm, tr('Agarrar y lanzar'), tr('Se hace cerca del rival con → + el botón. La animación es la '
                                                      'de tu personaje agarrando y lanzando; el rival sale volando.'))
        v = box.v
        self.throw_fb = FramesBox(sm, tr('Agarre'), 800, default_time=5, show_hit=True,
                                  hit_label=tr('Lo lanza en el cuadro:'))
        self.throw_fb.status_hook = box.set_status
        self.throw_fb.off_key = "throw"
        self.throw_fb.orig_key = "throw"
        self.throw_fb.orig_provider = lambda: sm.original_move("throw")
        box.add_tick("throw")
        self.cards["throw"] = box
        self.throw_fb.changed.connect(sm.moves_changed)
        v.addWidget(self.throw_fb, 1)
        f = QFormLayout()
        self.throw_btn = QComboBox()
        for b in sg.BUTTONS:
            self.throw_btn.addItem(f"→ + {b}", b)
        self.throw_btn.currentIndexChanged.connect(self.on_throw_opts)
        self.throw_dmg = QSpinBox()
        self.throw_dmg.setRange(0, 999)
        self.throw_dmg.valueChanged.connect(self.on_throw_opts)
        f.addRow(tr('Botón:'), self.throw_btn)
        f.addRow(tr('Daño:'), self.throw_dmg)
        v.addLayout(f)
        self.fold(box, grid, 0, 0)
        # agarre en el aire (opcional)
        box = FoldCard(sm, tr('Agarre en el aire'), tr('Opcional: en el aire, cerca de un rival que también va por '
                                                       'el aire, → + el botón. Lo agarra y lo estrella contra el '
                                                       'suelo. Si la dejas vacía, no tiene agarre en el aire.'))
        v = box.v
        self.athrow_fb = FramesBox(sm, tr('Agarre en el aire'), 850, default_time=4, show_hit=True,
                                   hit_label=tr('Lo lanza en el cuadro:'))
        self.athrow_fb.status_hook = box.set_status
        self.athrow_fb.ref_kind = "A"
        self.athrow_fb.optional = True
        self.cards["air_throw"] = box
        self.athrow_fb.changed.connect(sm.moves_changed)
        v.addWidget(self.athrow_fb, 1)
        f = QFormLayout()
        self.athrow_btn = QComboBox()
        for b in sg.BUTTONS:
            self.athrow_btn.addItem(f"→ + {b}", b)
        self.athrow_btn.currentIndexChanged.connect(self.on_athrow_opts)
        self.athrow_dmg = QSpinBox()
        self.athrow_dmg.setRange(0, 999)
        self.athrow_dmg.valueChanged.connect(self.on_athrow_opts)
        f.addRow(tr('Botón:'), self.athrow_btn)
        f.addRow(tr('Daño:'), self.athrow_dmg)
        v.addLayout(f)
        self.fold(box, grid, 0, 1)
        self.finish()
        self._binding = False

    def bind(self, cfg):
        self._binding = True
        for key, c in self.cards.items():
            c.bind_tick(key)
        for key, (fb, dmg) in self.boxes.items():
            e = cfg["normals"].setdefault(key, {})
            fb.bind(e)
            self.show_damage(key)
            self.show_step(key)
            self.show_more(key)
        th = cfg.setdefault("throw", {})
        self.throw_fb.bind(th)
        th.setdefault("button", "y")
        self.throw_btn.setCurrentIndex(max(0, self.throw_btn.findData(th.get("button", "y"))))
        self.throw_dmg.setValue(int(th.get("damage", 80)))
        ath = cfg.setdefault("air_throw", {})
        self.athrow_fb.bind(ath)
        ath.setdefault("button", "y")
        self.athrow_btn.setCurrentIndex(max(0, self.athrow_btn.findData(ath.get("button", "y"))))
        self.athrow_dmg.setValue(int(ath.get("damage", 70)))
        self._binding = False

    def bind_damage(self, key):
        self._binding = True
        self.show_damage(key)
        self._binding = False

    def show_more(self, key):
        b = self.more_btns.get(key)
        if b is None:
            return
        e = self.sm.cfg["normals"].get(key) or {}
        n = sum(1 for m in e.get("more") or [] if m.get("frames"))
        b.setText(tr('🔁 Al apretar otra vez') + (f"  ({n})" if n else ""))
        b.setEnabled(not getattr(self.boxes[key][0], "orig_mode", None))

    def on_more(self, key, title, pos):
        e = self.sm.cfg["normals"].setdefault(key, {})
        if not sg._frames(e):
            QMessageBox.information(self, APP_NAME, tr('Primero pon la animación de este golpe.'))
            return
        dlg = RepeatDialog(self.sm, key, title, pos, e)
        dlg.exec()
        e["more"] = [m for m in e.get("more") or [] if m.get("frames")]
        if not e["more"]:
            e.pop("more", None)
        self.show_more(key)
        self.sm.moves_changed()

    def show_step(self, key):
        if key not in self.steps:
            return
        step, sfr = self.steps[key]
        e = self.sm.cfg["normals"].get(key) or {}
        for w, v in ((step, int(e.get("step") or 0)), (sfr, int(e.get("step_frame") or 0))):
            w.blockSignals(True)
            w.setValue(v)
            w.blockSignals(False)
        fb = self.boxes[key][0]
        on = not getattr(fb, "orig_mode", None)
        step.setEnabled(on)
        sfr.setEnabled(on and bool(e.get("step")))

    def on_step(self, key):
        if self._binding:
            return
        step, sfr = self.steps[key]
        e = self.sm.cfg["normals"].setdefault(key, {})
        e["step"] = int(step.value())
        e["step_frame"] = int(sfr.value())
        if not e["step"]:
            e.pop("step", None)
            e.pop("step_frame", None)
        sfr.setEnabled(bool(e.get("step")))
        fb = self.boxes[key][0]
        fb.refresh()
        if fb.keys():
            self.sm.moves_changed()

    def show_damage(self, key):
        """El daño del golpe del modo simple o, si la casilla muestra el del personaje, el suyo."""
        fb, dmg = self.boxes[key]
        orig = fb.orig_mode[0] if getattr(fb, "orig_mode", None) else None
        old = dmg.blockSignals(True)
        if orig is not None:
            dmg.setEnabled(orig.damage is not None)
            dmg.setValue(int(orig.damage or 0))
        else:
            dmg.setEnabled(True)
            dmg.setValue(int(fb.entry.get("damage", sg.BASE_DAMAGE[key.split("_")[1]])))
        dmg.blockSignals(old)

    def on_damage(self, key, val):
        if self._binding:
            return
        fb = self.boxes[key][0]
        if getattr(fb, "orig_mode", None):
            self.sm.set_original_damage(fb.orig_mode, int(val))
            return
        self.sm.cfg["normals"].setdefault(key, {})["damage"] = int(val)
        if self.boxes[key][0].keys():
            self.sm.moves_changed()

    def on_athrow_opts(self, *_a):
        if self._binding:
            return
        ath = self.sm.cfg.setdefault("air_throw", {})
        ath["button"] = self.athrow_btn.currentData()
        ath["damage"] = self.athrow_dmg.value()
        if self.athrow_fb.keys():
            self.sm.moves_changed()

    def on_throw_opts(self, *_a):
        if self._binding:
            return
        th = self.sm.cfg.setdefault("throw", {})
        th["button"] = self.throw_btn.currentData()
        th["damage"] = self.throw_dmg.value()
        if self.throw_fb.keys():
            self.sm.moves_changed()


class HitFramesRow(QWidget):
    """Los cuadros del especial como botones: los marcados llevan caja de golpe (pegan)."""

    def __init__(self, sm, card):
        super().__init__()
        self.sm, self.card = sm, card
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 6, 0, 0)
        top = QHBoxLayout()
        top.addWidget(title_label(tr('💥 Cuadros que pegan')))
        top.addStretch(1)
        self.auto = QPushButton(tr('↺ Automático'))
        self.auto.setToolTip(tr('Vuelve a lo de antes: pega en el cuadro de «Pega / lanza en el cuadro».'))
        self.auto.clicked.connect(self.clear)
        top.addWidget(self.auto)
        v.addLayout(top)
        self.info = muted("")
        v.addWidget(self.info)
        self.btn_host = QWidget()
        self.grid = QGridLayout(self.btn_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(4)
        v.addWidget(self.btn_host)
        self.buttons = []
        self.rebuild()

    def applies(self):
        return self.card.sp.get("type", "proj") in ("hit", "dash", "rise")

    def rebuild(self):
        for b in self.buttons:
            # sin quitarle el padre: un botón suelto se vuelve una ventanita aparte
            self.grid.removeWidget(b)
            b.hide()
            b.deleteLater()
        self.buttons = []
        sp = self.card.sp
        keys = sg._frames(sp)
        if not (self.applies() and bool(keys)):
            self.hide()
        elif self.parentWidget() is not None:
            self.show()         # sin padre todavía: se ve sola cuando la ponen en la tarjeta
        if not self.applies() or not keys:
            return
        marked = {int(f) for f in sp.get("hit_frames") or []}
        for i, (g, n) in enumerate(keys):
            b = QToolButton(self.btn_host)
            b.setText(str(i + 1))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setCheckable(True)
            b.setChecked((i + 1) in marked)
            b.setFixedSize(54, 62)
            pm = self.sm.pixmap(g, n)
            if pm is not None:
                b.setIcon(QIcon(pm.scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)))
                b.setIconSize(QSize(34, 34))
            b.setToolTip(tr('Cuadro {0}: márcalo si en ese cuadro pega.').format(i + 1))
            b.toggled.connect(self.on_toggle)
            self.grid.addWidget(b, i // 8, i % 8)
            self.buttons.append(b)
        self.update_info()

    def update_info(self):
        sp = self.card.sp
        frames = sorted(int(f) for f in sp.get("hit_frames") or [])
        self.auto.setEnabled(bool(frames))
        if not frames:
            self.info.setText(tr('Ninguno marcado: pega en el cuadro de «Pega / lanza en el cuadro» (automático). '
                                 'Marca los cuadros que pegan; cada grupo de cuadros seguidos es un golpe.'))
            return
        runs = 0
        prev = None
        for f in frames:
            if prev is None or f != prev + 1:
                runs += 1
            prev = f
        self.info.setText(tr('Pega en {0} cuadro(s): {1} golpe(s). Cada grupo de cuadros seguidos es un golpe; '
                             'el daño se reparte entre los golpes.').format(len(frames), runs))

    def on_toggle(self, _on):
        sp = self.card.sp
        frames = [i + 1 for i, b in enumerate(self.buttons) if b.isChecked()]
        if frames:
            sp["hit_frames"] = frames
        else:
            sp.pop("hit_frames", None)
        self.update_info()
        self.card.body.refresh()
        self.card.refresh_head()
        self.sm.moves_changed()

    def clear(self):
        self.card.sp.pop("hit_frames", None)
        self.rebuild()
        self.card.body.refresh()
        self.card.refresh_head()
        self.sm.moves_changed()


class SpecialCard(QFrame):
    """Un especial o súper: una fila que se abre y se cierra, con pestañas por dentro."""

    def __init__(self, sm, page, sp, idx):
        super().__init__()
        self.sm, self.page, self.sp, self.idx = sm, page, sp, idx
        self.setObjectName("Card")
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)
        # ---- encabezado (siempre visible)
        head = QHBoxLayout()
        self.toggle = QPushButton()
        self.toggle.setFixedWidth(34)
        self.toggle.setToolTip(tr('Abrir / cerrar'))
        self.toggle.clicked.connect(lambda: self.set_open(not self.is_open()))
        head.addWidget(self.toggle)
        self.thumb = QLabel()
        self.thumb.setFixedSize(40, 40)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setObjectName("Thumb")
        head.addWidget(self.thumb)
        self.title = title_label("")
        self.summary = muted("", wrap=False)
        tcol = QVBoxLayout()
        tcol.setSpacing(0)
        tcol.addWidget(self.title)
        tcol.addWidget(self.summary)
        head.addLayout(tcol, 1)
        test = QPushButton(tr('▶ Probar'))
        test.setToolTip(tr('Mira el especial en acción: el personaje, el proyectil y un rival de prueba.'))
        test.clicked.connect(self.on_test)
        head.addWidget(test)
        if sp.get("from_orig"):
            back = QPushButton(tr('↩ Original'))
            back.setToolTip(tr('Quita este especial del modo simple y vuelve a prender el del personaje, como estaba.'))
            back.clicked.connect(lambda: page.restore_one(sp))
            head.addWidget(back)
        rm = QPushButton("🗑")
        rm.setFixedWidth(34)
        rm.setToolTip(tr('Quitar'))
        rm.clicked.connect(lambda: page.remove(sp))
        head.addWidget(rm)
        root.addLayout(head)
        # ---- cuerpo con pestañas
        self.body_w = QTabWidget()
        root.addWidget(self.body_w)
        base = (3000 if sp.get("kind") == "super" else 3500 if sp.get("kind") == "ender" else 1000) + 100 * idx
        # pestaña: datos
        t1 = QWidget()
        f = QFormLayout(t1)
        self.name = QLineEdit(sp.get("name", ""))
        self.name.editingFinished.connect(self.on_opts)
        self.motion = QComboBox()
        self.fill_motions()
        mrow = QHBoxLayout()
        mrow.addWidget(self.motion, 1)
        mb = QPushButton(tr('🎮 Crear…'))
        mb.setToolTip(tr('Abre el creador de comandos: tocas las flechas y queda guardado en la lista.'))
        mb.clicked.connect(self.on_builder)
        mrow.addWidget(mb)
        self.family = QComboBox()
        for k, t, _b in sg.FAMILIES:
            self.family.addItem(tr(t), k)
        self.family.setCurrentIndex(max(0, self.family.findData(sp.get("family", "punch"))))
        self.type = QComboBox()
        conv = sp.get("type") == "converted"
        for k, t in sg.SPECIAL_TYPES:
            if (k == "converted") == conv:
                self.type.addItem(tr(t), k)
        self.type.setEnabled(not conv)
        self.type.setCurrentIndex(max(0, self.type.findData(sp.get("type", "proj"))))
        self.damage = QSpinBox()
        self.damage.setRange(0, 9999)
        self.damage.setValue(int(sp.get("damage", 60)))
        self.damage.setToolTip(tr('Daño total de la versión media (si pega varias veces, se reparte).'))
        f.addRow(tr('Nombre:'), self.name)
        f.addRow(tr('Comando:'), mrow)
        if not conv:
            f.addRow(tr('Botón:'), self.family)
        f.addRow(tr('Qué hace:'), self.type)
        if not conv:
            f.addRow(tr('Daño:'), self.damage)
        self.versions = []
        if conv:
            vb = sp.get("vbutton") or {}
            names = [f"{tr(sg.VERSION_NAMES[int(v)])} ({b})" for v, b in sorted(vb.items(), key=lambda x: int(x[0]))]
            f.addRow(tr('Versiones:'), QLabel(", ".join(names)))
            f.addRow(muted(tr('Viene del código del personaje: cada versión conserva su código, partido en eventos '
                              '(pestaña «⏱ Eventos»), y sus condiciones (combos, poder…) siguen en su lugar en el '
                              '.cmd. Puedes cambiar el comando, la animación y cada evento, y agregarle más.')))
        elif sp.get("kind") == "ender":
            self.ender_of = QComboBox()
            self.ender_of.addItem(tr('(su propio comando)'), "")
            for i, o in enumerate(sm.cfg.get("specials", [])):
                if o is sp or o.get("kind") in ("super", "ender") or o.get("type") == "converted":
                    continue
                self.ender_of.addItem(f"🔥 {o.get('name') or '?'}", sg.special_ref(i, o))
            self.ender_of.setCurrentIndex(max(0, self.ender_of.findData(sp.get("ender_of", ""))))
            self.ender_of.setToolTip(tr('Como en Killer Instinct: el remate sale con el mismo comando del especial y '
                                        'el botón fuerte, pero solo después de un autodoble. Débil y medio siguen '
                                        'siendo el especial (linker).'))
            f.addRow(tr('Remate de:'), self.ender_of)
            f.addRow(muted(tr('Remate (Ender): sale solo después de un autodoble (pestaña «🔗 Combos»), con su '
                              'comando y cualquier fuerza del botón. Tumba al rival y cierra el combo; el daño '
                              'sube con el «extra del remate» de la pestaña de combos.')))
            f.addRow(muted(tr('Si escoges «Remate de» un especial, usa su mismo comando con el botón fuerte.')))
            self.ender_of.currentIndexChanged.connect(self.on_ender_of)
        if not conv:
            special = sp.get("kind") not in ("super", "ender")
            vr = QHBoxLayout()
            vals = list(sp.get("versions", [1, 1, 1])) + [1, 1, 1, 0][len(sp.get("versions", [1, 1, 1])):]
            for i, name in enumerate(sg.VERSION_NAMES if special else sg.STRENGTH):
                c = QCheckBox(tr(name))
                c.setChecked(bool(vals[i]))
                c.toggled.connect(self.on_opts)
                if i == 3:
                    c.setToolTip(tr('Versión EX: dos botones juntos (x+y o a+b). Gasta media barra de poder '
                                    '(cámbialo en «Ajustes»), pega más y brilla.'))
                vr.addWidget(c)
                self.versions.append(c)
            vr.addStretch(1)
            self.versions_lbl = QLabel(tr('Versiones:'))
            f.addRow(self.versions_lbl, vr)
            if special:
                f.addRow(muted(tr('Cada versión sale con su botón (débil, medio o fuerte): más fuerte = más daño '
                                  'y más rápido. La EX sale con dos botones juntos.')))
            else:
                f.addRow(muted(tr('Cada versión sale con su botón (débil, medio o fuerte): más fuerte = más daño '
                                  'y más rápido.')))
        if sp.get("kind") == "ender" and not conv:
            self.sync_ender_of()
        if sp.get("kind") == "super":
            f.addRow(muted(tr('El súper gasta barras de poder (cuántas, en «Ajustes»). Su pausa con la pantalla '
                              'oscura está en «⏱ Eventos».')))
        if not conv:
            self.voice = special_voice_picker(sm, sp)
            f.addRow(tr('Voz:'), self.voice)
        for w in (self.motion, self.family, self.type):
            w.currentIndexChanged.connect(self.on_opts)
        self.damage.valueChanged.connect(self.on_opts)
        self.body_w.addTab(t1, tr('📋 Datos'))
        # pestaña: animación
        t2 = QWidget()
        l2 = QHBoxLayout(t2)
        self.body = FramesBox(sm, tr('Animación del especial'), base, default_time=4, show_hit=True,
                              hit_label=tr('Pega / lanza en el cuadro:'))
        from core.autoalign import mode_for_slot
        self.body.align_mode_fn = lambda: mode_for_slot("special", sp=self.sp)
        self.body.bind(sp)
        self.body.changed.connect(self.on_body_changed)
        self.body.changed.connect(lambda: self.hits_row.rebuild())
        self.body.changed.connect(self.refresh_head)
        self.body.changed.connect(lambda: self.fill_pos() if hasattr(self, "p_x") else None)
        self.body.multi_hit = True
        col2 = QVBoxLayout()
        col2.addWidget(self.body, 1)
        self.hits_row = HitFramesRow(sm, self)
        col2.addWidget(self.hits_row)
        l2.addLayout(col2, 1)
        l2.addWidget(muted(tr('La animación de tu personaje haciendo el especial. El cuadro con borde rojo es '
                              'el que pega (o el que lanza el proyectil). Para que pegue en varios cuadros, '
                              'márcalos en «💥 Cuadros que pegan».')), 1)
        self.body_w.addTab(t2, tr('🎞 Animación'))
        # pestaña: proyectil
        self.proj_tab = QWidget()
        pc = QHBoxLayout(self.proj_tab)
        c1 = QVBoxLayout()
        self.proj_title = title_label(tr('El proyectil'))
        c1.addWidget(self.proj_title)
        self.proj = FramesBox(sm, tr('Proyectil'), base + 50, default_time=4, small=True)
        self.proj.bind(sp.setdefault("proj", {}))
        self.proj.changed.connect(sm.moves_changed)
        c1.addWidget(self.proj, 1)
        c2 = QVBoxLayout()
        self.proj_hit_title = title_label(tr('Al chocar (opcional)'))
        c2.addWidget(self.proj_hit_title)
        self.proj_hit = FramesBox(sm, tr('Proyectil al chocar'), base + 60, default_time=3, small=True)
        self.proj_hit.bind(sp.setdefault("proj_hit", {}))
        self.proj_hit.changed.connect(sm.moves_changed)
        c2.addWidget(self.proj_hit, 1)
        c3 = QVBoxLayout()
        self.proj_pos_title = title_label(tr('Posición del proyectil'))
        c3.addWidget(self.proj_pos_title)
        pf = QFormLayout()
        self.p_auto = QCheckBox(tr('Automática'))
        self.p_auto.setToolTip(tr('Sale de la mano o el pie que pega'))
        self.p_x = QSpinBox()
        self.p_y = QSpinBox()
        for w in (self.p_x, self.p_y):
            w.setRange(-9999, 9999)
        self.p_speed = QDoubleSpinBox()
        self.p_speed.setRange(0.1, 99)
        self.p_speed.setDecimals(2)
        self.p_speed.setSingleStep(0.5)
        self.p_speed.setValue(float(sg.spec(sp, "proj_vel")))
        self.p_speed.setToolTip(tr('Velocidad de la versión media (débil y fuerte salen solas).'))
        pf.addRow(self.p_auto)
        pf.addRow(tr('Adelante:'), self.p_x)
        pf.addRow(tr('Altura:'), self.p_y)
        pf.addRow(tr('Velocidad:'), self.p_speed)
        c3.addLayout(pf)
        c3.addWidget(muted(tr('Altura negativa = más arriba. También puedes tocar el punto de salida en '
                              '«▶ Probar».')))
        c3.addStretch(1)
        pc.addLayout(c1, 1)
        pc.addLayout(c2, 1)
        pc.addLayout(c3, 1)
        self.fill_pos()
        self.p_auto.toggled.connect(self.on_pos)
        for w in (self.p_x, self.p_y, self.p_speed):
            w.valueChanged.connect(self.on_pos)
        self.body_w.addTab(self.proj_tab, tr('🔥 Proyectil'))
        # pestaña: eventos
        from ui.events_editor import EventsEditor
        self.events = EventsEditor(sm, self)
        self.body_w.addTab(self.events, tr('⏱ Eventos'))
        # pestaña: condiciones (las del personaje, si viene convertido)
        self.cond_tab = QWidget()
        cl = QVBoxLayout(self.cond_tab)
        cl.addWidget(muted(tr('Las condiciones originales para hacerlo (del .cmd del personaje): combos, '
                              'cancelaciones, poder que necesita… Se usan tal cual con el comando nuevo.')))
        self.cond_edits = {}
        for vkey, ents in sorted((sp.get("ventry") or {}).items(), key=lambda x: int(x[0])):
            cl.addWidget(title_label(tr(sg.VERSION_NAMES[int(vkey)])))
            ed = QPlainTextEdit("\n\n".join(ents))
            ed.setMinimumHeight(120)
            ed.textChanged.connect(lambda vkey=vkey, ed=ed: self.on_cond(vkey, ed))
            cl.addWidget(ed)
            self.cond_edits[vkey] = ed
        self.body_w.addTab(self.cond_tab, tr('🧩 Condiciones'))
        # pestaña: ajustes
        t4 = QWidget()
        g4 = QGridLayout(t4)
        g4.setHorizontalSpacing(18)
        self.adv = {}
        for i, (key, label, kind, lo, hi, where, tip) in enumerate(sg.SPECIAL_FIELDS):
            if kind is bool:
                w = QCheckBox(tr(label))
                w.setChecked(bool(sg.spec(sp, key)))
                w.toggled.connect(lambda v, key=key: self.on_adv(key, bool(v)))
                lab = None
            elif kind == "height" or isinstance(kind, tuple):
                w = QComboBox()
                for hk, ht in (sg.HEIGHTS if kind == "height" else kind[1]):
                    w.addItem(tr(ht), hk)
                w.setCurrentIndex(max(0, w.findData(self.adv_value(key))))
                w.currentIndexChanged.connect(lambda _i, key=key, w=w: self.on_adv(key, w.currentData()))
                lab = QLabel(tr(label) + ":")
            else:
                w = QDoubleSpinBox() if kind is float else QSpinBox()
                if kind is float:
                    w.setDecimals(2)
                    w.setSingleStep(0.5)
                w.setRange(lo, hi)
                w.setValue(sg.spec(sp, key))
                w.valueChanged.connect(lambda v, key=key: self.on_adv(key, v))
                lab = QLabel(tr(label) + ":")
            w.setToolTip(tr(tip))
            if lab is not None:
                lab.setToolTip(tr(tip))
            self.adv[key] = (lab, w, where)
        self.adv_grid = g4
        self.layout_adv()
        reset = QPushButton(tr('↺ Valores de fábrica'))
        reset.clicked.connect(self.reset_adv)
        g4.addWidget(reset, 99, 0)
        g4.addWidget(muted(tr('Los números son de la versión media: la débil y la fuerte salen solas.')), 99, 1, 1, 3)
        self.adv_tab = t4
        self.body_w.addTab(t4, tr('⚙ Ajustes'))
        self.set_open(bool(sp.get("open", False)))
        self.update_tabs()
        self.refresh_head()

    # ---- abrir / cerrar y encabezado
    def is_open(self):
        return bool(self.sp.get("open", False))

    def set_open(self, on):
        self.sp["open"] = bool(on)
        self.body_w.setVisible(bool(on))
        self.toggle.setText("▾" if on else "▸")

    def refresh_head(self):
        sp = self.sp
        if hasattr(self, "events"):
            self.events.fill()
        icon = {"super": "⚡", "ender": "💥"}.get(sp.get("kind"), "🔥")
        kind = {"super": tr('Súper'), "ender": tr('Remate')}.get(sp.get("kind"), tr('Especial'))
        self.title.setText(f"{icon} {sp.get('name') or kind}")
        typ = dict(sg.SPECIAL_TYPES).get(sp.get("type", "proj"), "")
        hits = int(sg.spec(sp, "hits"))
        hf = sorted(int(f) for f in sp.get("hit_frames") or [])
        if hf and sp.get("type") in ("hit", "dash", "rise"):
            hits = sum(1 for i, f in enumerate(hf) if i == 0 or f != hf[i - 1] + 1)
        parts = [self.motion.currentText().replace("🎮 ", ""), tr(typ)]
        if hits > 1:
            parts.append(tr('{0} golpes').format(hits))
        if not sg._frames(sp):
            parts.append(tr('⚠ falta la animación'))
        elif sp.get("type", "proj") == "proj" and not sg._frames(sp.get("proj") or {}):
            parts.append(tr('⚠ falta el proyectil'))
        self.summary.setText("  ·  ".join(parts))
        keys = sg._frames(sp)
        pm = self.sm.pixmap(*keys[0]) if keys else None
        if pm is not None:
            self.thumb.setPixmap(pm.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
        else:
            self.thumb.setText(icon)

    def update_tabs(self):
        typ = self.sp.get("type", "proj")
        if hasattr(self, "hits_row"):
            self.hits_row.rebuild()
        self.body_w.setTabVisible(self.body_w.indexOf(self.proj_tab), typ in ("proj", "helper"))
        helper = typ == "helper"
        self.body_w.setTabText(self.body_w.indexOf(self.proj_tab), tr('🧍 Ayudante') if helper else tr('🔥 Proyectil'))
        self.proj_title.setText(tr('El ayudante (su animación)') if helper else tr('El proyectil'))
        self.proj_pos_title.setText(tr('Dónde aparece') if helper else tr('Posición del proyectil'))
        self.proj_hit_title.setVisible(not helper)
        self.proj_hit.setVisible(not helper)
        self.body_w.setTabVisible(self.body_w.indexOf(self.cond_tab), typ == "converted" and
                                  bool(self.sp.get("ventry")))
        self.body_w.setTabVisible(self.body_w.indexOf(self.adv_tab), typ != "converted")
        self.layout_adv()

    def on_body_changed(self):
        if self.sp.get("type") == "converted":
            self.sp["anim_changed"] = bool(sg._frames(self.sp))
        self.sm.moves_changed()

    def on_cond(self, vkey, ed):
        import re as _re
        parts = [x.strip() for x in _re.split(r"\n\s*\n(?=\s*\[)", ed.toPlainText()) if x.strip()]
        self.sp.setdefault("ventry", {})[vkey] = parts
        self.sm.moves_changed()

    def layout_adv(self):
        g = self.adv_grid
        for lab, w, _where in self.adv.values():
            if lab is not None:
                g.removeWidget(lab)
                lab.hide()
            g.removeWidget(w)
            w.hide()
        i = 0
        for key, (lab, w, where) in self.adv.items():
            if not sg.field_applies(where, self.sp):
                continue
            r, c = i // 2, (i % 2) * 2
            if lab is not None:
                g.addWidget(lab, r, c)
                g.addWidget(w, r, c + 1)
                lab.show()
            else:
                g.addWidget(w, r, c, 1, 2)
            w.show()
            i += 1

    def adv_value(self, key):
        """Lo que vale de verdad un ajuste (el de «lo tumba» depende también de los autodobles)."""
        if key == "launch":
            from core import combos
            return sg.launch_mode(self.sp, combos.get(self.sm.cfg))
        return sg.spec(self.sp, key)

    def on_adv(self, key, value):
        self.sp[key] = value
        if key == "ad_open" and "launch" not in self.sp and "launch" in self.adv:
            # «lo tumba» de fábrica cambia: abre autodobles → se queda de pie; si no → lo tumba
            w = self.adv["launch"][1]
            w.blockSignals(True)
            w.setCurrentIndex(max(0, w.findData(self.adv_value("launch"))))
            w.blockSignals(False)
        self.refresh_head()
        self.sm.moves_changed()

    def reset_adv(self):
        for key, _l, _k, _lo, _hi, _w, _t in sg.SPECIAL_FIELDS:
            self.sp.pop(key, None)
        for key, (lab, w, _where) in self.adv.items():
            w.blockSignals(True)
            v = self.adv_value(key)
            if isinstance(w, QCheckBox):
                w.setChecked(bool(v))
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(max(0, w.findData(v)))
            else:
                w.setValue(v)
            w.blockSignals(False)
        self.refresh_head()
        self.sm.moves_changed()

    def fill_motions(self):
        from ui.mainwindow import load_settings
        sp = self.sp
        self.motion.blockSignals(True)
        self.motion.clear()
        for k, t, _c in sg.MOTIONS:
            self.motion.addItem(tr(t), k)
        seen = set()
        for m in list(self.sm.cfg.get("custom_motions", [])) + list(load_settings().get("custom_motions", [])):
            if m.get("key") in seen:
                continue
            seen.add(m.get("key"))
            self.motion.addItem("🎮 " + m.get("label", "?"), m.get("key"))
        self.motion.setCurrentIndex(max(0, self.motion.findData(sp.get("motion", "QCF"))))
        self.motion.blockSignals(False)

    def remember_motion(self, key):
        """Si el comando elegido es uno creado, se copia al personaje (para que su código no dependa de la lista)."""
        from ui.mainwindow import load_settings
        if key in sg.MOTION_CMD:
            return
        own = self.sm.cfg.setdefault("custom_motions", [])
        if any(m.get("key") == key for m in own):
            return
        m = next((m for m in load_settings().get("custom_motions", []) if m.get("key") == key), None)
        if m:
            own.append(dict(m))

    def on_builder(self):
        from ui.command_builder import CommandBuilder
        from ui.mainwindow import load_settings, save_settings
        lib = list(load_settings().get("custom_motions", []))
        dlg = CommandBuilder(self, lib)
        res = dlg.exec()
        save_settings({"custom_motions": lib})
        if res and dlg.result_motion:
            key = dlg.result_motion["key"]
            self.remember_motion(key)
            for card in self.page.cards:
                card.fill_motions()
            self.motion.setCurrentIndex(max(0, self.motion.findData(key)))
            self.on_opts()
        else:
            for card in self.page.cards:
                card.fill_motions()

    def refresh_proj(self):
        """Después de cambiar el proyectil desde su evento: la pestaña «🔥 Proyectil» y la animación al día."""
        self.proj.bind(self.sp.setdefault("proj", {}))
        self.proj_hit.bind(self.sp.setdefault("proj_hit", {}))
        self.body.bind(self.sp)
        self.p_speed.blockSignals(True)
        self.p_speed.setValue(float(sg.spec(self.sp, "proj_vel")))
        self.p_speed.blockSignals(False)
        self.fill_pos()
        for key, (lab, w, _where) in self.adv.items():
            w.blockSignals(True)
            v = self.adv_value(key)
            if isinstance(w, QCheckBox):
                w.setChecked(bool(v))
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(max(0, w.findData(v)))
            else:
                w.setValue(v)
            w.blockSignals(False)
        self.damage.blockSignals(True)
        self.damage.setValue(int(self.sp.get("damage", 60)))
        self.damage.blockSignals(False)
        self.refresh_head()

    def fill_pos(self):
        sp = self.sp
        try:
            prm = sg.special_params(sp, 1, self.sm.main.project.sff.index(), self.sm.motion.k())
        except Exception:
            return
        for w, v in ((self.p_x, prm["px"]), (self.p_y, prm["py"])):
            w.blockSignals(True)
            w.setValue(int(v))
            w.setEnabled(sp.get("proj_x") is not None)
            w.blockSignals(False)
        self.p_auto.blockSignals(True)
        self.p_auto.setChecked(sp.get("proj_x") is None)
        self.p_auto.blockSignals(False)

    def on_pos(self, *_a):
        sp = self.sp
        if self.p_auto.isChecked():
            sp.pop("proj_x", None)
            sp.pop("proj_y", None)
        else:
            sp["proj_x"], sp["proj_y"] = self.p_x.value(), self.p_y.value()
        sp["proj_vel"] = self.p_speed.value()
        sp.pop("proj_speed", None)
        self.fill_pos()
        self.sm.moves_changed()

    def on_test(self):
        if not sg._frames(self.sp):
            QMessageBox.information(self, APP_NAME, tr('Primero pon la animación de tu personaje.'))
            return
        from ui.special_test import SpecialTest
        dlg = SpecialTest(self.sm, self.sp)
        dlg.positionChanged.connect(self.fill_pos)
        dlg.positionChanged.connect(self.sm.moves_changed)
        dlg.exec()

    def sync_ender_of(self):
        """Remate de un especial: el comando y el botón son los de ese especial (no se escogen aparte)."""
        sp = self.sp
        base = sg.ender_base(sp, self.sm.cfg.get("specials", []))
        on = base is not None
        if on:
            for w, key in ((self.motion, "motion"), (self.family, "family")):
                w.blockSignals(True)
                i = w.findData(base.get(key))
                if i >= 0:
                    w.setCurrentIndex(i)
                w.blockSignals(False)
            sp["motion"], sp["family"] = base.get("motion"), base.get("family")
        for w in (self.motion, self.family):
            w.setEnabled(not on)
        for c in getattr(self, "versions", []):
            c.setEnabled(not on)            # el remate de un especial sale solo con el botón fuerte
            c.setToolTip(tr('El remate de un especial sale solo con el botón fuerte.') if on else "")

    def on_ender_of(self, *_a):
        self.sp["ender_of"] = self.ender_of.currentData() or ""
        self.sync_ender_of()
        self.refresh_head()
        self.sm.moves_changed()

    def on_opts(self, *_a):
        sp = self.sp
        self.remember_motion(self.motion.currentData())
        sp["name"] = self.name.text().strip() or sp.get("name", "")
        sp["motion"] = self.motion.currentData()
        sp["family"] = self.family.currentData()
        if self.type.currentData() != sp.get("type") and self.type.currentData() != "converted":
            # otro «Qué hace»: sus eventos reemplazan los del tipo anterior
            sg.set_type(sp, self.type.currentData())
            self.events.bind()
        sp["type"] = self.type.currentData()
        if sp["type"] != "converted":
            sp["damage"] = self.damage.value()
        if self.versions:
            sp["versions"] = [1 if c.isChecked() else 0 for c in self.versions]
        self.update_tabs()
        self.refresh_head()
        self.sm.moves_changed()


class SpecialsPage(Page):
    def __init__(self, sm):
        super().__init__(sm, tr('🔥 Especiales y súper'), tr(
            'Movimientos con comando, como una bola de fuego (↓↘→ + puño). Elige qué hace, pon la animación de '
            'tu personaje (y la del proyectil si lanza uno) y listo. Se pueden hacer cancelando un golpe '
            'normal que conectó.'))
        row = QHBoxLayout()
        add = QPushButton(tr('🔥 Agregar especial'))
        add.setObjectName("primary")
        add.clicked.connect(lambda: self.add("special"))
        add2 = QPushButton(tr('⚡ Agregar súper'))
        add2.clicked.connect(lambda: self.add("super"))
        add3 = QPushButton(tr('💥 Agregar remate'))
        add3.setToolTip(tr('Ender: el golpe que cierra un combo de autodobles (pestaña «🔗 Combos»).'))
        add3.clicked.connect(lambda: self.add("ender"))
        row.addWidget(add)
        row.addWidget(add2)
        row.addWidget(add3)
        row.addStretch(1)
        for txt, on in ((tr('⊞ Abrir todos'), True), (tr('⊟ Cerrar todos'), False)):
            b = QPushButton(txt)
            b.clicked.connect(lambda _c, on=on: [c.set_open(on) for c in self.cards])
            row.addWidget(b)
        self.lay.addLayout(row)
        self.host = QVBoxLayout()
        self.host.setSpacing(10)
        self.lay.addLayout(self.host)
        self.empty = muted(tr('Todavía no tiene especiales. Toca «🔥 Agregar especial».'))
        self.lay.addWidget(self.empty)
        self.orig_title = QLabel(tr('🎮 Los que ya tiene el personaje'))
        self.orig_title.setObjectName("SectionTitle")
        self.lay.addWidget(self.orig_title)
        self.orig_desc = muted(tr('Especiales y súper que el personaje ya trae en su código. Ábrelos para cambiarles '
                                  'la animación, el daño o el comando ahí mismo, o tócale «📋 Pasar al modo simple» '
                                  'para editarlo todo (eventos, efectos, condiciones) sin perder sus combos. Quítale '
                                  'el tick a uno para apagarlo.'))
        self.lay.addWidget(self.orig_desc)
        orow = QHBoxLayout()
        self.copy_all_btn = QPushButton(tr('📋 Pasar todos al modo simple'))
        self.copy_all_btn.setToolTip(tr('Pasa al modo simple todos los especiales y súper prendidos del personaje, '
                                        'con todo su código (partido en eventos), sus condiciones y sus combos.'))
        self.copy_all_btn.clicked.connect(self.copy_all_originals)
        orow.addWidget(self.copy_all_btn)
        self.restore_btn = QPushButton(tr('↩ Devolver los originales'))
        self.restore_btn.setToolTip(tr('Quita los especiales que se rehicieron en el modo simple y vuelve a prender '
                                       'los del personaje, como estaban.'))
        self.restore_btn.clicked.connect(self.restore_all)
        orow.addWidget(self.restore_btn)
        orow.addStretch(1)
        self.lay.addLayout(orow)
        self.orig_host = QGridLayout()
        self.orig_host.setSpacing(10)
        for c in range(2):
            self.orig_host.setColumnStretch(c, 1)
        self.lay.addLayout(self.orig_host)
        self.finish()
        self.cards = []
        self.orig_cards = []

    def bind(self, cfg):
        for c in self.cards:
            self.sm.forget_previews(c)
            c.setParent(None)
            c.deleteLater()
        self.cards = []
        import uuid
        for i, sp in enumerate(cfg.get("specials", [])):
            sp.setdefault("uid", uuid.uuid4().hex[:10])
            sg.migrate_special(sp)
            c = SpecialCard(self.sm, self, sp, i)
            self.host.addWidget(c)
            self.cards.append(c)
        self.empty.setVisible(not self.cards)
        self.bind_originals()

    def bind_originals(self):
        for c in self.orig_cards:
            self.sm.forget_previews(c)
            c.setParent(None)
            c.deleteLater()
        self.orig_cards = []
        groups = {}
        for f in self.sm.originals():
            if f.kind in ("special", "super"):
                groups.setdefault(f.group, []).append(f)
        for i, lst in enumerate(sorted(groups.values(), key=lambda l: (l[0].kind == "super", min(x.state for x in l)))):
            c = OriginalSpecialCard(self.sm, self, sorted(lst, key=lambda x: x.state))
            self.orig_host.addWidget(c, i // 2, i % 2, Qt.AlignmentFlag.AlignTop)
            self.orig_cards.append(c)
        on = bool(self.orig_cards)
        self.orig_title.setVisible(on)
        self.orig_desc.setVisible(on)
        self.copy_all_btn.setVisible(on)
        self.restore_btn.setVisible(on and bool(self.remade()))
        off = set(self.sm.cfg.get("orig_off", []))
        self.copy_all_btn.setEnabled(any(not all(x.state in off for x in c.versions) for c in self.orig_cards))

    def copy_original(self, versions):
        """Rehace un especial del personaje con el modo simple (con su animación) y apaga el viejo."""
        if not self.make_simple(versions):
            QMessageBox.information(self, APP_NAME, tr('No encontré la animación de ese movimiento.'))
            return
        self.bind(self.sm.cfg)
        self.sm.moves_changed()
        QTimer.singleShot(50, lambda: self.ensureWidgetVisible(self.cards[-1]))

    def remade(self):
        """Especiales del modo simple que salieron de uno del personaje."""
        from core import detect_moves as dm
        off = set(self.sm.cfg.get("orig_off", []))
        names = {}
        for c in self.orig_cards:
            if all(x.state in off for x in c.versions):
                names[dm.nice_name(c.versions[0].label)] = [x.state for x in c.versions]
        out = []
        for sp in self.sm.cfg.get("specials", []):
            if sp.get("from_orig"):
                out.append((sp, list(sp["from_orig"])))
            elif sp.get("name") in names:
                out.append((sp, names[sp["name"]]))
        return out

    def unconvert(self, sp):
        """Devuelve el [Statedef] original de un especial convertido (y su comando en el .cmd)."""
        from core import special_events as sev
        cmd = self.sm.main.project.file("cmd")
        for key, st in (sp.get("vstates") or {}).items():
            f = (sp.get("vfile") or {}).get(key)
            if f:
                self.sm.edit_code(Path(f), lambda t, st=st: sev.restore_statedef(t, 900000 + int(st)))
            old = (sp.get("vcmdname") or {}).get(key)
            if old:
                cur = f"sm_cv{sp.get('uid')}_{key}"
                self.sm.edit_code(cmd, lambda t, st=st, cur=cur, old=old: sev.retarget_entries(t, st, cur, old))

    def restore_one(self, sp):
        states = list(sp.get("from_orig") or [])
        self.unconvert(sp)
        lst = self.sm.cfg.get("specials", [])
        if sp in lst:
            lst.remove(sp)
        self.sm.cfg["orig_off"] = sorted(set(self.sm.cfg.get("orig_off", [])) - set(states))
        self.bind(self.sm.cfg)
        self.sm.moves_changed()

    def restore_all(self):
        todo = self.remade()
        if not todo:
            return
        if QMessageBox.question(self, APP_NAME, tr(
                'Se van a quitar {0} especiales del modo simple y se vuelven a prender los del personaje. '
                '¿Seguir?').format(len(todo))) != QMessageBox.StandardButton.Yes:
            return
        lst = self.sm.cfg.get("specials", [])
        off = set(self.sm.cfg.get("orig_off", []))
        for sp, states in todo:
            self.unconvert(sp)
            if sp in lst:
                lst.remove(sp)
            off -= set(states)
        self.sm.cfg["orig_off"] = sorted(off)
        self.bind(self.sm.cfg)
        self.sm.moves_changed()

    def copy_all_originals(self):
        """Rehace de una vez todos los especiales y súper del personaje que están prendidos."""
        off = set(self.sm.cfg.get("orig_off", []))
        todo = [c.versions for c in self.orig_cards if not all(x.state in off for x in c.versions)]
        if not todo:
            return
        if QMessageBox.question(self, APP_NAME, tr(
                'Se van a pasar {0} movimientos al modo simple. Su código se conserva entero (partido en eventos que '
                'puedes editar) junto con sus condiciones y números de estado, así sus combos siguen funcionando. '
                'Puedes deshacerlo con «↩ Devolver los originales». ¿Seguir?').format(len(todo))) != \
                QMessageBox.StandardButton.Yes:
            return
        done, skipped = 0, []
        for versions in todo:
            if self.make_simple(versions, open_=False):
                done += 1
            else:
                from core import detect_moves as dm
                skipped.append(dm.nice_name(versions[0].label))
        self.bind(self.sm.cfg)
        self.sm.moves_changed()
        msg = tr('Listo: {0} pasados al modo simple.').format(done)
        if skipped:
            msg += "\n\n" + tr('Sin animación (se quedaron como estaban): {0}').format(", ".join(skipped))
        QMessageBox.information(self, APP_NAME, msg)

    def make_simple(self, versions, open_=True):
        """Pasa un especial del personaje al modo simple SIN perder nada: su código se parte en eventos
        editables (lo que no se conoce queda como «Código propio»), conserva sus números de estado y sus
        condiciones del .cmd (combos, cancelaciones). El [Statedef] original se guarda renombrado para poder
        devolverlo. False si no se pudo."""
        import uuid
        from core import detect_moves as dm
        from core import special_events as sev
        from core.textio import read_text
        p = self.sm.main.project
        sm = self.sm
        first = versions[0]
        super_ = first.kind == "super"
        cmd_path = p.file("cmd")
        cmd_text = sm.main.code.get_open(cmd_path).doc.toPlainText()
        k = sm.motion.k()
        vmap = {}
        for x in versions:
            toks = [t.strip() for t in x.command.split(",") if t.strip()]
            btn = dm._strip(toks[-1]) if toks else "x"
            parts = [b for b in btn.split("+") if b in dm.BUTTONS]
            if super_:
                v = 2
            elif len(parts) >= 2:
                v = 3
            else:
                v = {"x": 0, "a": 0, "y": 1, "b": 1, "z": 2, "c": 2}.get(parts[0] if parts else "y", 1)
            if v not in vmap and x.file is not None:
                vmap[v] = (x, btn)
        if not vmap:
            return False

        def text_of(path):
            of = sm.main.code.open.get(str(path))
            return of.doc.toPlainText() if of else read_text(path)[0]
        vstates, vhead, vevents, ventry, vbutton, vcmd, vfile = {}, {}, {}, {}, {}, {}, {}
        for v, (x, btn) in vmap.items():
            sd = sev.statedef_text(text_of(x.file), x.state)
            if sd is None:
                continue
            head, events = sev.convert_state(sd, k)
            key = str(v)
            vstates[key] = x.state
            vhead[key] = head
            vevents[key] = events
            vbutton[key] = btn
            vcmd[key] = sev.exact_command_name(cmd_text, x.state, x.cmd_name)
            vfile[key] = str(x.file)
        if not vstates:
            return False
        # el comando: el del personaje, con {b} en el botón
        cmd = dm.command_template(first.command)
        motion = next((kk for kk, c in sg.MOTION_CMD.items() if c.replace(" ", "") == cmd.replace(" ", "")), None)
        cfg = sm.cfg
        if motion is None:
            mots = cfg.setdefault("custom_motions", [])
            same = next((m for m in mots if m.get("cmd") == cmd), None)
            if same is None:
                same = {"key": "C" + uuid.uuid4().hex[:8], "label": dm.arrows(cmd.replace("{b}", "x"))
                        .replace(" + x", " + " + tr('botón')), "cmd": cmd}
                mots.append(same)
            motion = same["key"]
        ctime = None
        m = re.search(r'(?ims)^\s*name\s*=\s*"%s"\s*$\s*command\s*=[^\n]*\n\s*time\s*=\s*(\d+)'
                      % re.escape(first.cmd_name or "@@"), cmd_text)
        if m:
            ctime = int(m.group(1))
        a = p.air.find(first.anim) if first.anim is not None else None
        frames = [[f.group, f.number] for f in a.frames] if a is not None and a.frames else []
        sp = dict(name=dm.nice_name(first.label), kind=first.kind, type="converted", motion=motion,
                  family="kick" if first.button in ("a", "b", "c") else "punch",
                  damage=int(first.damage or 0), frames=frames,
                  time=typical_time(a.frames, 4) if a is not None and a.frames else 4,
                  vstates=vstates, vhead=vhead, vevents=vevents, ventry=ventry, vbutton=vbutton, vcmdname=vcmd,
                  vfile=vfile, cmd_time=ctime, open=open_, from_orig=[int(x) for x in vstates.values()],
                  uid=uuid.uuid4().hex[:10])
        # guardar los originales renombrados (para que no choquen y se puedan devolver) y hacer que sus
        # entradas del .cmd (que se quedan en su lugar, con sus condiciones) usen el comando del modo simple
        for key, st in vstates.items():
            sm.edit_code(Path(vfile[key]), lambda t, st=st: sev.rename_statedef(t, int(st), 900000 + int(st)))
            if vcmd[key]:
                new = f"sm_cv{sp['uid']}_{key}"
                sm.edit_code(cmd_path, lambda t, st=st, key=key, new=new: sev.retarget_entries(t, st, vcmd[key], new))
        if open_:
            for other in cfg.setdefault("specials", []):
                other["open"] = False
        cfg.setdefault("specials", []).append(sp)
        return True

    def add(self, kind):
        if not self.sm.main.project:
            return
        lst = self.sm.cfg.setdefault("specials", [])
        if kind == "super":
            preset = dict(sg.SUPER_PRESET)
        elif kind == "ender":
            preset = dict(sg.ENDER_PRESET)
            # un comando que no use otro movimiento
            used = {(s.get("motion"), s.get("family")) for s in lst}
            free = [(m, f) for m in ("HCF", "HCB", "DD", "QCB", "DP", "QCF") for f in ("punch", "kick")
                    if (m, f) not in used]
            if free:
                preset["motion"], preset["family"] = free[0]
        else:
            n = sum(1 for s in lst if s.get("kind") not in ("super", "ender"))
            preset = dict(sg.SPECIAL_PRESETS[n % len(sg.SPECIAL_PRESETS)])
        preset["name"] = tr(preset["name"])
        preset["versions"] = [1, 1, 1]
        preset["open"] = True
        # lo que hace el tipo («Qué hace») viene puesto como eventos que se pueden cambiar
        preset["events"] = sg.type_events(preset)
        preset["evmode"] = sg.EVMODE
        for other in lst:
            other["open"] = False
        lst.append(preset)
        self.bind(self.sm.cfg)
        self.sm.mark()
        QTimer.singleShot(50, lambda: self.ensureWidgetVisible(self.cards[-1]))

    def remove(self, sp):
        if QMessageBox.question(self, APP_NAME, tr('¿Quitar «{0}»?').format(sp.get("name", ""))) != \
                QMessageBox.StandardButton.Yes:
            return
        if sp.get("type") == "converted":
            self.unconvert(sp)
            self.sm.cfg["orig_off"] = sorted(set(self.sm.cfg.get("orig_off", [])) - set(sp.get("from_orig") or []))
        lst = self.sm.cfg.get("specials", [])
        if sp in lst:
            lst.remove(sp)
        self.bind(self.sm.cfg)
        self.sm.moves_changed()


class OriginalSpecialCard(FoldCard):
    """Un especial o súper que el personaje ya trae (con sus versiones). Se edita en su propio código."""

    def __init__(self, sm, page, versions):
        from core import detect_moves as dm
        first = versions[0]
        title = dm.nice_name(first.label) + ("  ⚡" if first.kind == "super" else "")
        super().__init__(sm, title)
        self.page = None
        self.versions = versions
        self.states = [x.state for x in versions]
        self.add_tick_states(self.states)
        self.fb = FramesBox(sm, title, first.anim or 1000, default_time=4, small=True)
        self.fb.orig_provider = lambda: sm.originals_by_states(self.states)
        self.fb.status_hook = lambda *_a: None
        self.v.addWidget(self.fb)
        grid = QGridLayout()
        grid.setSpacing(4)
        self.dmg = {}
        for i, x in enumerate(versions):
            grid.addWidget(muted(f"{x.label}: <b>{x.arrows}</b>"), i, 0)
            d = QSpinBox()
            d.setRange(0, 9999)
            d.setKeyboardTracking(False)
            d.setEnabled(x.damage is not None)
            d.setValue(int(x.damage or 0))
            d.setPrefix(tr('Daño: '))
            d.valueChanged.connect(lambda val, st=x.state: sm.set_original_damage(
                sm.originals_by_states([st]), int(val)))
            grid.addWidget(d, i, 1)
        grid.setColumnStretch(0, 1)
        self.v.addLayout(grid)
        row = QHBoxLayout()
        cmd = QPushButton(tr('🎮 Cambiar comando…'))
        cmd.setToolTip(tr('Elige las flechas nuevas; cada versión se queda con su botón.'))
        cmd.clicked.connect(self.on_command)
        row.addWidget(cmd)
        cp = QPushButton(tr('📋 Pasar al modo simple'))
        cp.setToolTip(tr('Lo pasa al modo simple con todo su código (partido en eventos que puedes editar), sus '
                         'condiciones y sus combos. Se puede devolver.'))
        cp.clicked.connect(lambda: page.copy_original(versions))
        row.addWidget(cp)
        self.v.addLayout(row)
        arr = " · ".join(dict.fromkeys(x.arrows for x in versions))
        a = sm.main.project.air.find(first.anim) if first.anim is not None else None
        thumb = (a.frames[0].group, a.frames[0].number) if a is not None and a.frames else None
        off = all(n in sm.cfg.get("orig_off", []) for n in self.states)
        conv = {int(x) for o in sm.cfg.get("specials", []) for x in (o.get("from_orig") or [])}
        if all(n in conv for n in self.states):
            self.set_status("ok", tr('✅ Pasado al modo simple') + "  ·  " + arr, thumb)
            self.tick.setEnabled(False)
            for w in self.body.findChildren(QPushButton) + self.body.findChildren(QSpinBox) + \
                    self.body.findChildren(QComboBox):
                w.setEnabled(False)
        elif off:
            self.set_status("off", tr('⭘ Apagado') + "  ·  " + arr, thumb)
        else:
            self.set_status("info", arr, thumb)
        self.fb.refresh()

    def on_command(self):
        from ui.command_builder import CommandBuilder
        saved = self.sm.cfg.setdefault("custom_motions", [])
        dlg = CommandBuilder(self.sm.main, saved)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.result_motion:
            return
        self.sm.set_original_command(self.sm.originals_by_states(self.states), dlg.result_motion["cmd"])
        self.sm.mark()
        self.sm.specials_page.bind_originals()

    def add_tick_states(self, states):
        self.tick = QCheckBox(tr('Lo tiene'))
        self.tick.setChecked(not all(n in self.sm.cfg.get("orig_off", []) for n in states))
        self.tick.setToolTip(tr('Quítale el tick para apagar este movimiento del personaje.'))
        self.tick.toggled.connect(lambda on: self.sm.set_orig_off(states, not on))
        self.hl.addWidget(self.tick, 0, Qt.AlignmentFlag.AlignTop)


class VoicePicker(QWidget):
    """Una voz: lista de los sonidos del personaje, 📂 WAV… y ▶. Con «inherit» (especiales) tiene además
    «la general de su tipo»."""
    changed = pyqtSignal()

    def __init__(self, sm, get, put, slot, inherit=None):
        super().__init__()
        self.sm, self.get, self.put, self.slot, self.inherit = sm, get, put, slot, inherit
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.setMinimumWidth(170)
        self.combo.currentIndexChanged.connect(self.on_combo)
        imp = QPushButton(tr('📂 Sonido…'))
        imp.setToolTip(tr('Pon un sonido tuyo: WAV, OGG, MP3, FLAC… (se guarda como WAV en los sonidos del '
                          'personaje, que es lo que IKEMEN GO acepta ahí).'))
        imp.clicked.connect(self.import_wav)
        play = QPushButton("▶")
        play.setFixedWidth(34)
        play.setToolTip(tr('Escuchar'))
        play.clicked.connect(self.play)
        row.addWidget(self.combo, 1)
        row.addWidget(imp)
        row.addWidget(play)
        self._binding = False
        self.refresh()

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()      # pudo cambiar desde la otra página

    def refresh(self):
        self._binding = True
        p = self.sm.main.project
        try:
            sounds = sorted(p.snd.sounds, key=lambda s: s.key) if p else []
        except Exception:
            sounds = []
        self.combo.clear()
        if self.inherit:
            self.combo.addItem(self.inherit(), "inherit")
        self.combo.addItem(tr('(ninguna)'), "none")
        for snd in sounds:
            inf = snd.info()
            self.combo.addItem(f"{snd.group}, {snd.number}" + (f"  ({inf[0]:.1f} s)" if inf else ""),
                               [snd.group, snd.number])
        cur = self.get()
        if cur is None:
            cur = "inherit" if self.inherit else "none"
        self.combo.setCurrentIndex(max(0, self.combo.findData(cur)))
        self._binding = False

    def value(self):
        d = self.combo.currentData()
        if d == "inherit" or (d == "none" and not self.inherit):
            return None
        return d

    def on_combo(self, _i):
        if self._binding:
            return
        self.put(self.value())
        self.sm.moves_changed()
        self.changed.emit()

    def import_wav(self):
        p = self.sm.main.project
        if not p:
            return
        from ui.common import audio_filter, read_audio
        f, _ = QFileDialog.getOpenFileName(self, tr('Elige un sonido'), str(p.folder), audio_filter())
        if not f:
            return
        data = read_audio(self, f)
        if data is None:
            return
        from core.snd import Sound
        g, n = self.slot() if callable(self.slot) else self.slot
        snd = p.snd
        new = Sound(g, n, data)
        before = list(snd.sounds)
        after = [x for x in before if x.key != new.key] + [new]
        self.sm.main.sounds.push(tr('Voz'), lambda: snd.sounds.__setitem__(slice(None), after),
                                 lambda: snd.sounds.__setitem__(slice(None), before), new)
        self.put([g, n])
        self.refresh()
        self.sm.moves_changed()
        self.changed.emit()

    def play(self):
        p = self.sm.main.project
        v = self.combo.currentData()
        if v == "inherit":
            v = self.inherit_value() if hasattr(self, "inherit_value") else None
        if not p or not isinstance(v, list):
            return
        play_sound(self, p, v)


def play_sound(owner, p, v):
    s = p.snd.find(*v)
    if s is None:
        return
    try:
        from PyQt6.QtMultimedia import QSoundEffect
    except ImportError:
        QMessageBox.information(owner, APP_NAME, tr('Tu instalación de PyQt6 no trae sonido (QtMultimedia).'))
        return
    import tempfile
    tmp = Path(tempfile.gettempdir()) / "easyfighter_voice.wav"
    tmp.write_bytes(s.data)
    owner._player = QSoundEffect(owner)
    owner._player.setSource(QUrl.fromLocalFile(str(tmp)))
    owner._player.play()


def free_combo_slot(sm, item):
    """Dónde guardar el sonido de una voz del combo: su lugar de antes o uno libre del grupo 903."""
    p = sm.main.project
    cur = item.get("snd")
    others = [o.get("snd") for o in sm.cfg.get("combo_voices", []) if o is not item]
    if isinstance(cur, list) and cur[0] == 903 and cur not in others:
        return tuple(cur)
    used = {(x.group, x.number) for x in p.snd.sounds} if p else set()
    n = 0
    while (903, n) in used:
        n += 1
    return 903, n


def free_voice_slot(sm, sp):
    """Dónde guardar el WAV propio de un especial: su lugar de antes si era suyo, o uno libre del grupo 900."""
    p = sm.main.project
    cur = sp.get("voice")
    others = [o.get("voice") for o in sm.cfg.get("specials", []) if o is not sp]
    if isinstance(cur, list) and cur[0] == 900 and cur[1] >= sg.VOICE_FREE_FROM and cur not in others:
        return tuple(cur)
    used = {(x.group, x.number) for x in p.snd.sounds} if p else set()
    n = sg.VOICE_FREE_FROM
    while (900, n) in used:
        n += 1
    return 900, n


def special_voice_picker(sm, sp):
    """La voz de un especial / súper / remate (o la general de su tipo)."""
    cat = sg.voice_category(sp)
    cat_title = dict((k, t) for k, t, _g, _n in sg.VOICES)[cat]

    def inherit_label():
        v = sm.cfg["voices"].get(cat) or (sm.cfg["voices"].get("special") if cat == "ender" else None)
        return tr('(la general: «{0}»{1})').format(tr(cat_title), f" — {v[0]}, {v[1]}" if v else " — " + tr('ninguna'))

    def put(v):
        if v is None:
            sp.pop("voice", None)
        else:
            sp["voice"] = v

    w = VoicePicker(sm, lambda: sp.get("voice"), put, lambda: free_voice_slot(sm, sp), inherit=inherit_label)
    w.inherit_value = lambda: sm.cfg["voices"].get(cat) or (sm.cfg["voices"].get("special") if cat == "ender" else None)
    w.setToolTip(tr('La voz de este movimiento. «La general» es la de su tipo en la página «🔊 Voces».'))
    return w


VOICE_SECTIONS = [
    ("hits", '👊 Golpes', ["atk_light", "atk_medium", "atk_strong", "throw"]),
    ("specials", '🔥 Especiales, súper y remates', ["special", "super", "ender"]),
    ("hurt", '🤕 Recibir golpes y perder', ["hurt", "ko"]),
    ("win", '🏆 Ganar e intro', ["win", "intro"]),
]


class VoicesPage(Page):
    def __init__(self, sm):
        super().__init__(sm, tr('🔊 Voces'), tr(
            'Las voces de tu personaje: pon un sonido (WAV, OGG, MP3…) en cada cosa (o elige uno de los sonidos que ya tiene) y '
            'el editor hace que suene en el momento justo. Los golpes y cubrirse ya suenan solos con los '
            'sonidos del juego.'))
        top = QHBoxLayout()
        top.addStretch(1)
        for txt, on in ((tr('⊞ Abrir todos'), True), (tr('⊟ Cerrar todos'), False)):
            b = QPushButton(txt)
            b.clicked.connect(lambda _c, on=on: self.set_all_sections(on))
            top.addWidget(b)
        self.lay.addLayout(top)
        from ui.mainwindow import load_settings
        folded = set(load_settings().get("voices_folded", []))
        self.vsections = {}
        self.pickers = {}
        info = {k: (t, g, n) for k, t, g, n in sg.VOICES}
        for skey, stitle, keys in VOICE_SECTIONS:
            head = QToolButton()
            head.setObjectName("SectionTitle")
            head.setAutoRaise(True)
            head.setCheckable(True)
            head.setCursor(Qt.CursorShape.PointingHandCursor)
            head.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            head.setStyleSheet("QToolButton { background: transparent; border: none; padding: 2px 0; }"
                               "QToolButton:hover { text-decoration: underline; }")
            head.setToolTip(tr('Clic para abrir o cerrar esta sección.'))
            body = QWidget()
            bl = QVBoxLayout(body)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(8)
            grid = QGridLayout()
            grid.setSpacing(10)
            for c in range(2):
                grid.setColumnStretch(c, 1)
            for i, key in enumerate(keys):
                title, g, n = info[key]
                box, v = card(tr(title) + (" " + tr('(general)') if skey == "specials" else ""))
                pk = VoicePicker(sm, lambda key=key: getattr(self.sm, "cfg", {}).get("voices", {}).get(key),
                                 lambda val, key=key: self.put_general(key, val), (g, n))
                pk.changed.connect(self.update_heads)
                pk.changed.connect(self.refresh_moves)
                v.addWidget(pk)
                grid.addWidget(box, i // 2, i % 2)
                self.pickers[key] = pk
            bl.addLayout(grid)
            if skey == "specials":
                bl.addWidget(muted(tr('Cada especial, súper o remate puede tener su propia voz (aquí abajo o en su '
                                      'pestaña «📋 Datos»). Si no tiene la suya, usa la general de su tipo.')))
                self.moves_box = QFrame()
                self.moves_box.setObjectName("Card")
                self.moves_grid = QGridLayout(self.moves_box)
                self.moves_grid.setContentsMargins(10, 10, 10, 10)
                self.moves_grid.setHorizontalSpacing(14)
                self.moves_grid.setColumnStretch(1, 1)
                bl.addWidget(self.moves_box)
            head.toggled.connect(lambda on, body=body, skey=skey: self.on_fold(skey, on))
            self.lay.addWidget(head)
            self.lay.addWidget(body)
            self.vsections[skey] = (head, body, stitle, keys)
            head.setChecked(skey not in folded)
            body.setVisible(skey not in folded)
        # voces del combo: una casilla por cada cantidad de golpes (se agregan con el botón)
        head, body = self.fold_section("combos", folded)
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        bl.addWidget(muted(tr('Un sonido cuando tu combo llega a cierta cantidad de golpes (por ejemplo, a los 3 '
                              'golpes dice «¡Bien!» y a los 5 «¡Increíble!»). Toca «➕ Agregar» para cada cantidad. '
                              'Si un golpe salta varias cantidades a la vez, suena solo la más alta.')))
        self.combo_box = QFrame()
        self.combo_box.setObjectName("Card")
        self.combo_grid = QGridLayout(self.combo_box)
        self.combo_grid.setContentsMargins(10, 10, 10, 10)
        self.combo_grid.setHorizontalSpacing(14)
        self.combo_grid.setColumnStretch(1, 1)
        bl.addWidget(self.combo_box)
        arow = QHBoxLayout()
        add = QPushButton(tr('➕ Agregar cantidad de golpes'))
        add.clicked.connect(self.add_combo_voice)
        arow.addWidget(add)
        arow.addStretch(1)
        bl.addLayout(arow)
        self.update_heads()
        self.finish()

    def fold_section(self, skey, folded, stitle='🔗 Combos (por cantidad de golpes)'):
        head = QToolButton()
        head.setObjectName("SectionTitle")
        head.setAutoRaise(True)
        head.setCheckable(True)
        head.setCursor(Qt.CursorShape.PointingHandCursor)
        head.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        head.setStyleSheet("QToolButton { background: transparent; border: none; padding: 2px 0; }"
                           "QToolButton:hover { text-decoration: underline; }")
        head.setToolTip(tr('Clic para abrir o cerrar esta sección.'))
        body = QWidget()
        head.toggled.connect(lambda on, skey=skey: self.on_fold(skey, on))
        self.lay.addWidget(head)
        self.lay.addWidget(body)
        self.vsections[skey] = (head, body, stitle, [])
        head.setChecked(skey not in folded)
        body.setVisible(skey not in folded)
        return head, body

    # ---- voces del combo
    def combo_list(self):
        return self.sm.cfg.setdefault("combo_voices", [])

    def add_combo_voice(self):
        lst = self.combo_list()
        n = max([int(x.get("hits", 0)) for x in lst] + [1]) + 1
        lst.append({"hits": min(99, n)})
        self.fill_combo_voices()
        self.update_heads()
        self.sm.moves_changed()

    def remove_combo_voice(self, item):
        lst = self.combo_list()
        if item in lst:
            lst.remove(item)
        self.fill_combo_voices()
        self.update_heads()
        self.sm.moves_changed()

    def fill_combo_voices(self):
        g = self.combo_grid
        while g.count():
            it = g.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        lst = self.combo_list() if hasattr(self.sm, "cfg") else []
        self.combo_box.setVisible(bool(lst))
        for r, item in enumerate(lst):
            lead = QWidget()
            ll = QHBoxLayout(lead)
            ll.setContentsMargins(0, 0, 0, 0)
            ll.addWidget(QLabel(tr('Al llegar a')))
            sp = QSpinBox()
            sp.setRange(2, 99)
            sp.setValue(int(item.get("hits", 3)))
            sp.setSuffix(" " + tr('golpes'))
            sp.setKeyboardTracking(False)
            sp.valueChanged.connect(lambda v, item=item: (item.__setitem__("hits", int(v)), self.sm.moves_changed()))
            ll.addWidget(sp)
            pk = VoicePicker(self.sm, lambda item=item: item.get("snd"),
                             lambda val, item=item: item.__setitem__("snd", val) if val else item.pop("snd", None),
                             lambda item=item: free_combo_slot(self.sm, item))
            pk.changed.connect(self.update_heads)
            rm = QPushButton("🗑")
            rm.setFixedWidth(34)
            rm.setToolTip(tr('Quitar esta casilla'))
            rm.clicked.connect(lambda _c, item=item: self.remove_combo_voice(item))
            g.addWidget(lead, r, 0)
            g.addWidget(pk, r, 1)
            g.addWidget(rm, r, 2)

    # ---- secciones plegables
    def on_fold(self, skey, on):
        head, body, _t, _k = self.vsections[skey]
        body.setVisible(on)
        self.update_heads()
        from ui.mainwindow import save_settings
        save_settings({"voices_folded": [k for k, (h, _b, _t, _k) in self.vsections.items() if not h.isChecked()]})

    def set_all_sections(self, on):
        for head, _b, _t, _k in self.vsections.values():
            head.setChecked(on)

    def update_heads(self):
        voices = self.sm.cfg.get("voices", {}) if hasattr(self.sm, "cfg") else {}
        for skey, (head, _b, stitle, keys) in self.vsections.items():
            done = sum(1 for k in keys if voices.get(k))
            total = len(keys)
            if skey == "combos":
                lst = self.sm.cfg.get("combo_voices", []) if hasattr(self.sm, "cfg") else []
                done, total = sum(1 for x in lst if x.get("snd")), len(lst)
                head.setText(f"{'▾' if head.isChecked() else '▸'}  {tr(stitle)}   "
                             f"({tr('{0} de {1} puestas').format(done, total)})")
                continue
            if skey == "specials":
                moves = [o for o in self.sm.cfg.get("specials", []) if o.get("type") != "converted"] \
                    if hasattr(self.sm, "cfg") else []
                own = sum(1 for o in moves if isinstance(o.get("voice"), list))
                extra = "  ·  " + tr('{0} de {1} con voz propia').format(own, len(moves)) if moves else ""
            else:
                extra = ""
            head.setText(f"{'▾' if head.isChecked() else '▸'}  {tr(stitle)}   "
                         f"({tr('{0} de {1} puestas').format(done, total)}){extra}")

    # ---- datos
    def put_general(self, key, val):
        self.sm.cfg["voices"][key] = val

    def bind(self, cfg):
        for pk in self.pickers.values():
            pk.refresh()
        self.fill_moves()
        self.fill_combo_voices()
        self.update_heads()

    def refresh_moves(self):
        for pk in getattr(self, "move_pickers", []):
            pk.refresh()

    def fill_moves(self):
        self.move_pickers = []
        g = self.moves_grid
        while g.count():
            it = g.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        moves = [o for o in self.sm.cfg.get("specials", []) if o.get("type") != "converted"]
        if not moves:
            g.addWidget(muted(tr('Todavía no tienes especiales, súper ni remates (página «🔥 Especiales y súper»).')),
                        0, 0, 1, 2)
            return
        for r, sp in enumerate(moves):
            icon = {"super": "⚡", "ender": "💥"}.get(sp.get("kind"), "🔥")
            lab = QLabel(f"{icon} {sp.get('name') or '?'}")
            lab.setMinimumWidth(170)
            pk = special_voice_picker(self.sm, sp)
            pk.changed.connect(self.update_heads)
            self.move_pickers.append(pk)
            g.addWidget(lab, r, 0)
            g.addWidget(pk, r, 1)


class ColorsHost(Page):
    def __init__(self, sm):
        super().__init__(sm, tr('🎨 Colores'), tr(
            'Colores alternativos de tu personaje: los que salen al elegirlo con otro botón en la selección '
            '(paletas 1 a 12). Crea una paleta, toca una parte (piel, ropa, pelo…) y escoge su color: las '
            'sombras y los brillos se ajustan solos.'))
        from ui.colors_page import ColorsPage
        self.colors = ColorsPage(self)
        self.lay.addWidget(self.colors, 1)

    def bind(self, cfg):
        # se arma al verla (revisar todos los sprites toma un momento)
        if self.sm.main.project and self.isVisible():
            self.colors.bind()

    def showEvent(self, e):
        super().showEvent(e)
        if self.sm.main.project:
            self.colors.bind()


class BodyPreview(QWidget):
    """El personaje parado con su tamaño, el ancho del cuerpo, la altura y la sombra."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setMinimumSize(QSize(260, 240))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.CANVAS))
        p.drawRoundedRect(r, 8, 8)
        sm = self.page.sm
        pr = sm.main.project
        if not pr:
            p.end()
            return
        b = {k: w.value() for k, w in self.page.body.items()}
        scale = b.get("size", 100) / 100.0
        a = pr.air.find(0)
        spr = None
        if a and a.frames:
            fr = a.frames[0]
            spr = sm.sprite(fr.group, fr.number)
        sw, sh = (spr.pixels().shape[1], spr.pixels().shape[0]) if spr is not None else (40, 90)
        ax, ay = (spr.x, spr.y) if spr is not None else (20, 90)
        height = max(1.0, b.get("height", 60))
        top_units = max(ay * scale, height, 10) * 1.15
        half_w = max(sw * scale, (b.get("front", 16) + b.get("back", 15)) * 2, 30) * 0.8
        z = min((r.height() - 30) / top_units, (r.width() - 20) / (half_w * 2), 4.0)
        ox = r.center().x()
        oy = r.bottom() - 18
        # suelo
        p.setPen(QPen(QColor(255, 107, 53, 140), 1))
        p.drawLine(int(r.left() + 8), int(oy), int(r.right() - 8), int(oy))
        # sombra
        sy = oy + b.get("shadow", 0) * z
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawEllipse(QRectF(ox - sw * scale * z * 0.45, sy - 4, sw * scale * z * 0.9, 8))
        # sprite
        if spr is not None:
            pm = sm.pixmap(spr.group, spr.number)
            if pm is not None:
                p.drawPixmap(QRectF(ox - ax * scale * z, oy - ay * scale * z, sw * scale * z, sh * scale * z),
                             pm, QRectF(pm.rect()))
        # cuerpo
        back, front = b.get("back", 15), b.get("front", 16)
        p.setBrush(QColor(110, 231, 183, 50))
        p.setPen(QPen(QColor("#6ee7b7"), 1))
        p.drawRect(QRectF(ox - back * z, oy - height * z, (back + front) * z, height * z))
        # altura
        p.setPen(QPen(QColor("#ff6b6b"), 2, Qt.PenStyle.DashLine))
        p.drawLine(int(r.left() + 10), int(oy - height * z), int(r.right() - 10), int(oy - height * z))
        p.setPen(QColor(theme.MUTED))
        p.drawText(r.adjusted(8, 4, -8, -2), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
                   f"{int(b.get('size', 100))} %")
        p.end()


class CharPage(Page):
    k_now = 1.0     # resolución del personaje abierto / 320
    # clave, etiqueta, máximo, decimales, sufijo, ayuda
    BODY = [
        ("size", 'Tamaño', 1000, 0, " %", 'Qué tan grande se ve en el juego (100 % = tamaño de los sprites).'),
        ("front", 'Ancho del cuerpo (adelante)', 999, 0, "", 'Hasta dónde llega su cuerpo hacia adelante: lo cerca '
         'que se le puede pegar el rival.'),
        ("back", 'Ancho del cuerpo (atrás)', 999, 0, "", 'Hasta dónde llega su cuerpo hacia atrás.'),
        ("height", 'Altura', 9999, 0, "", 'Hasta dónde lo puede pasar por encima un rival que salta.'),
        ("power", 'Barras de poder', 9, 0, "", 'Cuántas barras de súper puede llenar (1 barra = 1000).'),
        ("shadow", 'Sombra (más abajo / arriba)', 999, 0, "", 'Mueve la sombra hacia abajo (+) o hacia arriba (−).'),
        ("bounce", 'Rebote al caer', 500, 0, " %", 'Qué tanto rebota cuando cae al suelo (100 % = normal).'),
    ]
    STATS = [
        ("life", 'Vida', "Data", "life", 0, 1, 99999, 0),
        ("attack", 'Ataque (%)', "Data", "attack", 0, 1, 9999, 0),
        ("defence", 'Defensa (%)', "Data", "defence", 0, 1, 9999, 0),
        ("airjumps", 'Saltos extra en el aire', "Movement", "airjump.num", 0, 0, 9, 0),
        ("liedown", 'Tiempo tirado en el suelo', "Data", "liedown.time", 0, 1, 600, 0),
    ]
    STAT_TIPS = {
        "liedown": 'Cuánto se queda tirado después de caer, antes de levantarse (60 ticks = 1 segundo; lo normal '
                   'es 60). Menos = se levanta antes. Apretando botones el jugador se levanta más rápido. Para que '
                   'la animación de levantarse sea más rápida, cambia su rapidez en «🤕 Recibir golpes».',
    }
    STAT_DEFAULTS = {"liedown": 60}     # si el .cns no la trae, el juego usa esto

    def __init__(self, sm):
        super().__init__(sm, tr('👤 Personaje'), tr(
            'Lo básico de tu personaje: nombre, qué tan fuerte y rápido es, y su música. Para ver cómo va, '
            'toca «▶ Probar en IKEMEN GO» abajo a la izquierda.'))
        grid = self.section(tr('Datos'), cols=2)
        box, v = card(tr('Nombre'))
        f = QFormLayout()
        self.name = QLineEdit()
        self.author = QLineEdit()
        self.name.editingFinished.connect(self.on_names)
        self.author.editingFinished.connect(self.on_names)
        f.addRow(tr('Nombre:'), self.name)
        f.addRow(tr('Autor:'), self.author)
        v.addLayout(f)
        self.res = muted("")
        v.addWidget(self.res)
        v.addStretch(1)
        grid.addWidget(box, 0, 0)
        box, v = card(tr('Fuerza'))
        f = QFormLayout()
        self.stats = {}
        for key, label, _s, _k, _i, step, top, dec in self.STATS:
            sp = QDoubleSpinBox() if dec else QSpinBox()
            if dec:
                sp.setDecimals(dec)
                sp.setSingleStep(step)
            sp.setRange(0, top)
            sp.valueChanged.connect(self.on_stat)
            if key == "liedown":
                sp.setSuffix(" " + tr('ticks'))
            lab = QLabel(tr(label) + ":")
            if key in self.STAT_TIPS:
                sp.setToolTip(tr(self.STAT_TIPS[key]))
                lab.setToolTip(tr(self.STAT_TIPS[key]))
            f.addRow(lab, sp)
            self.stats[key] = sp
        v.addLayout(f)
        self.stats_warn = muted("")
        v.addWidget(self.stats_warn)
        grid.addWidget(box, 0, 1)
        self.stat_timer = QTimer(self)
        self.stat_timer.setSingleShot(True)
        self.stat_timer.setInterval(500)
        self.stat_timer.timeout.connect(self.apply_stats)

        grid = self.section(tr('Tamaño y cuerpo'), cols=2)
        box, v = card(tr('Medidas'), tr('Las medidas van en las unidades del personaje (las de su resolución).'))
        f = QFormLayout()
        self.body = {}
        for key, label, top, dec, suffix, tip in self.BODY:
            sp = QDoubleSpinBox() if dec else QSpinBox()
            if dec:
                sp.setDecimals(dec)
            sp.setRange(0 if key != "shadow" else -999, top)
            if suffix:
                sp.setSuffix(suffix)
            sp.setToolTip(tr(tip))
            sp.valueChanged.connect(self.on_body)
            lab = QLabel(tr(label) + ":")
            lab.setToolTip(tr(tip))
            f.addRow(lab, sp)
            self.body[key] = sp
        self.hurt_count = QComboBox()
        self.hurt_count.addItem(tr('2 cajas (cuerpo y cabeza)'), 2)
        self.hurt_count.addItem(tr('1 caja (todo el cuerpo)'), 1)
        tip = tr('Las cajas azules: donde le pueden pegar. El editor las pone solas en cada dibujo; aquí escoges '
                 'cuántas. Para dibujarlas tú en una animación: «🟦 Cuerpo» en su casilla.')
        self.hurt_count.setToolTip(tip)
        self.hurt_count.currentIndexChanged.connect(self.on_hurt_count)
        lab = QLabel(tr('Cajas del cuerpo (automáticas):'))
        lab.setToolTip(tip)
        f.addRow(lab, self.hurt_count)
        v.addLayout(f)
        self.bake_btn = QPushButton(tr('🔍 Agrandar los sprites a este tamaño'))
        self.bake_btn.setToolTip(tr('Agranda de verdad todos los sprites, animaciones y cajas a este tamaño y deja '
                                    'el tamaño en 100 %. Sirve cuando la hoja de sprites es muy chiquita.'))
        self.bake_btn.clicked.connect(self.bake_size)
        v.addWidget(self.bake_btn)
        v.addStretch(1)
        grid.addWidget(box, 0, 0)
        box, v = card(tr('Vista previa'), tr('Verde: el cuerpo (lo cerca que se le puede pegar el rival) · '
                                             'línea roja: la altura · gris: la sombra.'))
        self.body_view = BodyPreview(self)
        v.addWidget(self.body_view, 1)
        grid.addWidget(box, 0, 1)

        grid = self.section(tr('En el juego'), cols=1)
        box, v = card(tr('Pantalla de selección y música'), tr(
            'IKEMEN GO toma la música del personaje de data/select.def. La música de su escenario suena en el '
            'modo arcade cuando peleas contra él; la de victoria, cuando gana.'))
        self.game_info = QLabel()
        self.game_info.setWordWrap(True)
        v.addWidget(self.game_info)
        self.add_btn = QPushButton(tr('➕ Ponerlo en la pantalla de selección'))
        self.add_btn.clicked.connect(self.add_to_roster)
        v.addWidget(self.add_btn)
        f = QFormLayout()
        self.music = {}
        for key, label in (("music", 'Música de su escenario'), ("victory.music", 'Música de victoria'),
                           ("life.music", 'Música con poca vida')):
            row = QHBoxLayout()
            lab = QLabel()
            lab.setObjectName("CardPath")
            b = QPushButton(tr('📂 Elegir…'))
            b.clicked.connect(lambda _c, key=key: self.pick_music(key))
            rm = QPushButton("🗑")
            rm.setFixedWidth(34)
            rm.clicked.connect(lambda _c, key=key: self.set_music(key, ""))
            row.addWidget(lab, 1)
            row.addWidget(b)
            row.addWidget(rm)
            f.addRow(tr(label) + ":", row)
            self.music[key] = (lab, b, rm)
        v.addLayout(f)
        self.fold(box, grid, 0, 0)
        box, v = card(tr('🏆 Frases de victoria'), tr(
            'Lo que dice tu personaje en la pantalla de victoria (el juego escoge una al azar). Una frase por '
            'línea, hasta 100.'))
        self.quotes = QPlainTextEdit()
        self.quotes.setPlaceholderText(tr('Ej.: ¡Entrena más y vuelve a buscarme!'))
        self.quotes.setMinimumHeight(110)
        self.quotes.textChanged.connect(lambda: None if self._binding else self.quote_timer.start())
        self.quote_timer = QTimer(self)
        self.quote_timer.setSingleShot(True)
        self.quote_timer.setInterval(600)
        self.quote_timer.timeout.connect(self.apply_quotes)
        v.addWidget(self.quotes)
        grid.addWidget(box, 1, 0)
        self.finish()
        self._binding = False

    def apply_quotes(self):
        doc = self.cns_doc()
        if doc is None:
            return
        old = doc.toPlainText()
        text = sg.write_quotes(old, self.quotes.toPlainText().splitlines())
        if text != old:
            set_doc_text(doc, text)

    # ---- datos del .def
    def bind(self, _cfg):
        p = self.sm.main.project
        if not p:
            return
        self._binding = True
        self.name.setText(p.defs.get("Info", "name"))
        self.author.setText(p.defs.get("Info", "author"))
        lw, lh = p.localcoord()
        CharPage.k_now = lw / 320
        self.res.setText(tr('Resolución: {0}×{1}').format(lw, lh))
        consts = self.read_consts()
        missing = []
        for key, _label, _s, ck, i, _st, _t, _d in self.STATS:
            sp = self.stats[key]
            sp.blockSignals(True)
            name = f"{_s.lower()}.{ck}" + (".y" if i == 1 else "")
            if name in consts or key in self.STAT_DEFAULTS:
                val = consts.get(name, self.STAT_DEFAULTS.get(key))
                val = -val if key == "jump" else val
                sp.setValue(val if isinstance(sp, QDoubleSpinBox) else int(round(val)))
                sp.setEnabled(True)
            else:
                sp.setEnabled(False)
                missing.append(key)
            sp.blockSignals(False)
        bvals = self.body_values(consts)
        for key, sp in self.body.items():
            sp.blockSignals(True)
            if key in bvals:
                val = bvals[key]
                sp.setValue(val if isinstance(sp, QDoubleSpinBox) else int(round(val)))
                sp.setEnabled(True)
            else:
                sp.setEnabled(False)
                missing.append(key)
            sp.blockSignals(False)
        self.body_view.update()
        self.hurt_count.blockSignals(True)
        self.hurt_count.setCurrentIndex(max(0, self.hurt_count.findData(sg.hurt_count(self.sm.cfg))))
        self.hurt_count.blockSignals(False)
        self.bake_btn.setEnabled(self.body["size"].isEnabled() and self.body["size"].value() != 100)
        self.stats_warn.setText(tr('Algunos datos no están en el .cns del personaje.') if missing else "")
        doc = self.cns_doc()
        self.quotes.setPlainText("\n".join(sg.read_quotes(doc.toPlainText())) if doc is not None else "")
        self.quotes.setEnabled(doc is not None)
        self._binding = False
        self.refresh_game()

    def cns_doc(self):
        p = self.sm.main.project
        f = p.file("cns") if p else None
        if f is None or f.suffix.lower() == ".zss":
            return None
        return self.sm.main.code.get_open(f).doc

    def read_consts(self):
        from core.simulate import parse_constants
        doc = self.cns_doc()
        return parse_constants(doc.toPlainText()) if doc is not None else {}

    def bake_size(self):
        """Pasa el «tamaño» a los sprites: los agranda de verdad y deja xscale/yscale en 1."""
        from core.rescale import scale_action, scale_sprite
        sm = self.sm
        p = sm.main.project
        f = self.body["size"].value() / 100.0
        if not p or f == 1:
            return
        if QMessageBox.question(self, APP_NAME, tr(
                'Se van a agrandar todos los sprites y animaciones (con sus cajas) al {0} % y el tamaño queda en '
                '100 %. En el juego se ve igual, pero el personaje queda hecho a su tamaño de verdad. Las imágenes '
                'de la pantalla de selección (9000) no se tocan. ¿Seguir?').format(int(f * 100))) != \
                QMessageBox.StandardButton.Yes:
            return
        sm.flush()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            sff = p.sff
            before = list(sff.sprites)
            done = {}
            after = []
            for s in before:
                if s.group == 9000:
                    after.append(s)
                    continue
                done[id(s)] = scale_sprite(s, f)
                after.append(done[id(s)])
            sm.main.sprites.push(tr('Agrandar sprites'), lambda: sff.sprites.__setitem__(slice(None), after),
                                 lambda: sff.sprites.__setitem__(slice(None), before), refresh_list=True)
            new_list = [scale_action(a, f) for a in p.air.actions]
            sm.main.anims.edit_list(tr('Agrandar sprites'), new_list)
            self.body["size"].blockSignals(True)
            self.body["size"].setValue(100)
            self.body["size"].blockSignals(False)
            doc = self.cns_doc()
            if doc is not None:
                text = set_const(doc.toPlainText(), "Size", "xscale", 0, 1)
                text = set_const(text, "Size", "yscale", 0, 1)
                set_doc_text(doc, text)
            sm.cache = {}
            sm.motion.forget()
            if sg.has_moves(sm.cfg):
                sm.sync_moves()
        finally:
            QApplication.restoreOverrideCursor()
        self.body_view.update()
        self.bake_btn.setEnabled(False)
        sm.main.update_title()
        QMessageBox.information(self, APP_NAME,
                                tr('✅ Listo: los sprites quedaron al {0} % y el tamaño en 100 %.').format(int(f * 100)))

    @staticmethod
    def body_values(c):
        out = {}
        if "size.xscale" in c:
            out["size"] = c["size.xscale"] * 100
        for key, name in (("front", "size.ground.front"), ("back", "size.ground.back"), ("height", "size.height"),
                          ("shadow", "size.shadowoffset")):
            if name in c:
                out[key] = c[name]
        if "data.power" in c:
            out["power"] = round(c["data.power"] / 1000)
        y = c.get("movement.down.bounce.yaccel")
        if y:
            out["bounce"] = 0.4 * CharPage.k_now / y * 100
        return out

    def on_hurt_count(self, _i):
        if self._binding:
            return
        self.sm.cfg["hurt_boxes"] = int(self.hurt_count.currentData())
        self.sm.hurt_changed()

    def on_body(self, *_a):
        self.body_view.update()
        self.bake_btn.setEnabled(self.body["size"].isEnabled() and self.body["size"].value() != 100)
        self.on_stat()

    def apply_body(self, text, consts):
        cur = self.body_values(consts)
        for key, sp in self.body.items():
            if not sp.isEnabled():
                continue
            v = sp.value()
            if key in cur and abs(cur[key] - v) < 0.5:
                continue
            if key == "size":
                text = set_const(text, "Size", "xscale", 0, round(v / 100, 3))
                text = set_const(text, "Size", "yscale", 0, round(v / 100, 3))
            elif key in ("front", "back"):
                text = set_const(text, "Size", f"ground.{key}", 0, int(v))
            elif key == "height":
                text = set_const(text, "Size", "height", 0, int(v))
            elif key == "shadow":
                text = set_const(text, "Size", "shadowoffset", 0, int(v))
            elif key == "power":
                text = set_const(text, "Data", "power", 0, int(v) * 1000)
            elif key == "bounce" and v > 0:
                text = set_const(text, "Movement", "down.bounce.yaccel", 0, round(0.4 * self.k_now * 100 / v, 3))
        return text

    def on_stat(self, *_a):
        if not self._binding:
            self.stat_timer.start()

    def apply_stats(self):
        doc = self.cns_doc()
        if doc is None:
            return
        text = old = doc.toPlainText()
        consts = self.read_consts()
        for key, _label, sec, ck, i, _st, _t, dec in self.STATS:
            sp = self.stats[key]
            if not sp.isEnabled():
                continue
            val = sp.value()
            if key in self.STAT_DEFAULTS and f"{sec.lower()}.{ck}" not in consts and val == self.STAT_DEFAULTS[key]:
                continue        # no la trae el .cns y sigue como la del juego: no hace falta escribirla
            if key == "jump":
                oldy = consts.get("velocity.jump.neu.y", 0) or -1
                newy = -val
                ratio = newy / oldy if oldy else 1
                text = set_const(text, sec, "jump.neu", 1, newy)
                for other in ("runjump.fwd", "runjump.back", "airjump.neu"):
                    ov = consts.get(f"velocity.{other}.y")
                    if ov is not None:
                        text = set_const(text, sec, other, 1, round(ov * ratio, 2))
            elif key == "walk":
                ob = consts.get("velocity.walk.back.x")
                of = consts.get("velocity.walk.fwd.x") or 1
                text = set_const(text, sec, ck, 0, val)
                if ob is not None:
                    text = set_const(text, sec, "walk.back", 0, round(ob * val / of, 2))
            else:
                text = set_const(text, sec, ck, i, int(val) if not dec else val)
        text = self.apply_body(text, consts)
        if text != old:
            set_doc_text(doc, text)
            self.sm.main.sim.states = {}
            self.sm.motion.forget()

    def on_names(self):
        p = self.sm.main.project
        if not p or self._binding:
            return
        name, author = self.name.text().strip(), self.author.text().strip()
        changed = False
        if name and name != p.defs.get("Info", "name"):
            p.defs.set("Info", "name", name, quote=True)
            p.defs.set("Info", "displayname", name, quote=True)
            changed = True
        if author != p.defs.get("Info", "author"):
            p.defs.set("Info", "author", author, quote=True)
            changed = True
        if changed:
            p.defs_dirty = True
            self.sm.main.def_tab.load_form_only()
            self.sm.main.def_tab.set_modified()
            self.sm.main.refresh_header()
            self.sm.main.update_title()

    # ---- select.def
    def select_info(self):
        from core import selectdef
        from ui.mainwindow import load_settings
        p = self.sm.main.project
        root = selectdef.game_root(p, load_settings().get("ikemen_dir"))
        if root is None:
            return None, None, None
        sd = selectdef.SelectDef(root / "data" / "select.def")
        return root, sd, sd.find(p, root)

    def refresh_game(self):
        p = self.sm.main.project
        if not p:
            return
        try:
            root, sd, line = self.select_info()
        except OSError:
            root = sd = line = None
        ok = root is not None
        self.add_btn.setVisible(ok and line is None)
        if not ok:
            self.game_info.setText(tr('⚠ Este personaje no está dentro de la carpeta «chars» de IKEMEN GO, así que '
                                      'no se puede poner su música aquí. Cópialo a IKEMEN GO/chars y ábrelo desde '
                                      'ahí.'))
        elif line is None:
            self.game_info.setText(tr('Todavía no está en la pantalla de selección de {0}.').format(root))
        else:
            self.game_info.setText(tr('✅ Está en la pantalla de selección ({0}).').format(root / "data" / "select.def"))
        params = sd.params(line) if (ok and line is not None) else {}
        for key, (lab, b, rm) in self.music.items():
            val = params.get(key, "")
            lab.setText(val.split(" ")[0] if val else tr('(la del escenario)') if key == "music" else tr('(ninguna)'))
            b.setEnabled(ok)
            rm.setEnabled(ok and bool(val))

    def add_to_roster(self):
        from core import selectdef
        root, sd, line = self.select_info()
        if root is None or line is not None:
            return
        p = self.sm.main.project
        p.backup(sd.path)
        sd.add_char(selectdef.char_ref(p, root))
        sd.save()
        self.refresh_game()
        self.sm.main.status.setText(tr('✅ Agregado a {0}').format(sd.path))

    def pick_music(self, key):
        p = self.sm.main.project
        f, _ = QFileDialog.getOpenFileName(self, tr('Elige la música'), str(p.folder), tr(SOUND_FILTER))
        if f:
            self.set_music(key, f)

    def set_music(self, key, src):
        import shutil
        from core import selectdef
        root, sd, line = self.select_info()
        if root is None:
            return
        p = self.sm.main.project
        if line is None:
            if not src:
                return
            if QMessageBox.question(self, APP_NAME, tr('Para tener música, el personaje tiene que estar en la '
                                                       'pantalla de selección. ¿Agregarlo?')) != \
                    QMessageBox.StandardButton.Yes:
                return
            p.backup(sd.path)
            line = sd.add_char(selectdef.char_ref(p, root))
        value = ""
        if src:
            src = Path(src)
            dst_dir = p.folder / "music"
            dst_dir.mkdir(exist_ok=True)
            clean = re.sub(r"[^\w.\-]+", "_", src.name)
            dst = dst_dir / clean
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            try:
                value = dst.resolve().relative_to(Path(root).resolve()).as_posix()
            except ValueError:
                value = dst.as_posix()
        p.backup(sd.path)
        sd.set_param(line, key, value)
        sd.save()
        self.refresh_game()
        self.sm.main.status.setText(tr('✅ Música guardada en {0}').format(sd.path))


def set_const(text, section, key, index, value):
    """Cambia el valor (índice index de la lista separada por comas) de 'key' dentro de [section]."""
    lines = text.split("\n")
    sec = None
    last = None              # última línea con algo de [section] (para agregar la clave si no está)
    for i, ln in enumerate(lines):
        m = re.match(r"^\s*\[\s*([^\]]+?)\s*\]", ln)
        if m:
            sec = m.group(1).lower()
            if sec == section.lower():
                last = i
            continue
        if sec != section.lower():
            continue
        if ln.split(";", 1)[0].strip():
            last = i
        body = ln.split(";", 1)[0]
        if "=" not in body or body.partition("=")[0].strip().lower() != key.lower():
            continue
        k, _, vals = body.partition("=")
        parts = [x.strip() for x in vals.split(",")]
        while len(parts) <= index:
            parts.append("0")
        parts[index] = f"{value:g}" if isinstance(value, float) else str(value)
        comment = ln[len(body):]
        lines[i] = f"{k.rstrip()} = {', '.join(parts)}" + (("  " + comment.lstrip()) if comment.strip() else "")
        break
    else:
        if last is not None:     # la clave no estaba: se agrega al final de su sección
            parts = ["0"] * index + [f"{value:g}" if isinstance(value, float) else str(value)]
            lines.insert(last + 1, f"{key} = {', '.join(parts)}")
    return "\n".join(lines)


def set_doc_text(doc, text):
    cur = QTextCursor(doc)
    cur.beginEditBlock()
    cur.select(QTextCursor.SelectionType.Document)
    cur.insertText(text)
    cur.endEditBlock()


# ---------------------------------------------------------------- el controlador
class SimpleMode(QObject):
    modifiedChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.cfg = sg._fill({})
        self.dirty = False
        self.tick = 0
        self.cache = {}
        self.previews = []
        self.pending_drop = []
        self.show_boxes = False
        self._box_checks = []
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.on_tick)
        self.timer.start()
        self.code_timer = QTimer(self)
        self.code_timer.setSingleShot(True)
        self.code_timer.setInterval(400)
        self.code_timer.timeout.connect(self.sync_moves)
        self.motion = Motion(self)
        self.char_page = CharPage(self)
        self.moves_page = AnimsPage(self, tr('🚶 Moverse y saltar'), tr(
            'Las animaciones básicas. Para cada casilla pon tus imágenes (en orden) o elige sprites que ya '
            'tiene. Las cajas para recibir golpes se ponen solas (o dibújalas tú con «🟦 Cuerpo»).'),
            ("basic", "jump", "show"))
        self.attacks_page = AttacksPage(self)
        self.specials_page = SpecialsPage(self)
        self.hurt_page = AnimsPage(self, tr('🤕 Recibir golpes y cubrirse'), tr(
            'Cómo reacciona tu personaje cuando le pegan, cuando cae y cuando se cubre. Si dejas una vacía, '
            'usa lo que ya tenía.'), ("guard", "hurt"))
        self.voices_page = VoicesPage(self)
        self.colors_page = ColorsHost(self)
        from ui.combos_page import CombosPage
        self.combos_page = CombosPage(self)
        from ui.extra_pages import AIPage, FinishPage
        self.ai_page = AIPage(self)
        self.finish_page = FinishPage(self)
        self.import_mode = QComboBox()
        self.pages = [self.char_page, self.moves_page, self.attacks_page, self.specials_page, self.combos_page,
                      self.hurt_page, self.colors_page, self.voices_page, self.ai_page, self.finish_page]
        for pg in (self.moves_page, self.attacks_page, self.specials_page, self.hurt_page):
            pg.lay.insertLayout(2, self.colors_row(pg))

    def colors_row(self, page=None):
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Colores al poner imágenes:')))
        c = QComboBox()
        c.addItem(tr('Exactos, como en la imagen (recomendado)'), "rgba")
        c.addItem(tr('Con la paleta del personaje (permite cambiarle los colores)'), "char")
        c.currentIndexChanged.connect(lambda _i, c=c: self.set_import_mode(c.currentData()))
        row.addWidget(c)
        row.addSpacing(16)
        bc = QCheckBox(tr('Ver cajas de golpe'))
        bc.setToolTip(tr('Azul: donde le pueden pegar · rojo: donde pega'))
        bc.toggled.connect(self.set_show_boxes)
        row.addWidget(bc)
        row.addStretch(1)
        al = QPushButton(tr('🎯 Alinear todas con la de parado'))
        al.setToolTip(tr('Reconoce el cuerpo y los pies de cada cuadro y alinea todas las animaciones del modo '
                         'simple con la de parado. Antes de cambiar nada te enseña cómo quedan.'))
        al.clicked.connect(self.align_all)
        row.addWidget(al)
        if page is not None and getattr(page, "folds", None):
            for txt, on in ((tr('⊞ Abrir todos'), True), (tr('⊟ Cerrar todos'), False)):
                b = QPushButton(txt)
                b.clicked.connect(lambda _c, on=on, page=page: page.set_all_open(on))
                row.addWidget(b)
        self._mode_combos = getattr(self, "_mode_combos", []) + [c]
        self._box_checks = getattr(self, "_box_checks", []) + [bc]
        return row

    def set_show_boxes(self, on):
        self.show_boxes = bool(on)
        for b in self._box_checks:
            b.blockSignals(True)
            b.setChecked(self.show_boxes)
            b.blockSignals(False)
        for w in self.previews:
            try:
                w.update()
            except RuntimeError:
                pass

    def ref_sprite(self, kind="S"):
        """Pose normal (de pie «S», agachado «C», en el aire «A») para encontrar lo que pega."""
        key = ("ref", kind)
        if key not in self.cache:
            p = self.main.project
            self.cache[key] = sg.reference_sprites(self.cfg, p.sff.index(), p.air).get(kind) if p else None
        return self.cache[key]

    def auto_boxes_of(self, g, n, hit=False, ref_kind="S", body_auto=False):
        """(caja de golpe, cajas del cuerpo) como las pone el modo simple. body_auto: las del cuerpo
        automáticas aunque ese dibujo tenga unas dibujadas a mano."""
        two = sg.HURT["two"]
        key = ("boxes", g, n, hit, ref_kind if hit else None, two)
        if key not in self.cache:
            s = self.sprite(g, n)
            if s is None:
                self.cache[key] = None
            else:
                from ui.align_dialog import boxes_for
                self.cache[key] = boxes_for(s, s.x, s.y, hit, self.ref_sprite(ref_kind) if hit else None, two=two)
        res = self.cache[key]
        mh = None if body_auto else sg.HURT["by_key"].get((int(g), int(n)))
        if res is not None and mh is not None:
            res = (res[0], list(mh))
        return res

    def hurt_changed(self):
        """Cambiaron las cajas del cuerpo (cuántas automáticas o las de una animación): se rehacen las
        animaciones del modo simple y el código."""
        sg.set_hurt(self.cfg)
        self.cache = {}
        if not self.main.project:
            return
        for key in sg.ANIM_SLOTS:
            if sg.own_frames(self.cfg, key)[0]:
                try:
                    self.anim_slot_changed(key)
                except Exception:
                    import traceback
                    traceback.print_exc()
        self.moves_changed()
        for pg in self.pages:
            for w in pg.findChildren(FramesBox):
                w.preview.update()

    def align_all(self):
        p = self.main.project
        if not p:
            return
        if self.reference_frame() is None:
            QMessageBox.information(self.main, APP_NAME, tr('Primero pon la animación de parado: es la guía para '
                                                             'alinear las demás.'))
            return
        from ui.align_all import AlignAllDialog
        dlg = AlignAllDialog(self)
        if not dlg.rows:
            QMessageBox.information(self.main, APP_NAME, tr('Todavía no hay animaciones del modo simple para '
                                                             'alinear.'))
            return
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        ch = dlg.changes()
        if not ch:
            self.main.status.setText(tr('✅ Ya estaban alineadas.'))
            return
        self.apply_axes(ch)
        self.cache = {}
        for kind, key in dlg.touched():
            if kind == "anim":
                self.anim_slot_changed(key)
        self.moves_changed()
        for pg in (self.moves_page, self.attacks_page, self.specials_page, self.hurt_page):
            for w in pg.findChildren(FramesBox):
                w.refresh()
        self.main.status.setText(tr('🎯 Alineados {0} cuadros con la de parado (Ctrl+Z para deshacer).').format(
            len(ch)))

    def reference_frame(self):
        """El primer cuadro de la animación de parado (la guía para alinear), o None."""
        idle = (self.cfg.get("anims") or {}).get("idle") or {}
        fr = idle.get("frames") or []
        if fr:
            return (int(fr[0][0]), int(fr[0][1]))
        p = self.main.project
        a = p.air.find(0) if p else None
        if a is not None and a.frames:
            k = (a.frames[0].group, a.frames[0].number)
            return k if self.sprite(*k) is not None else None
        return None

    def mirror_sprites(self, keys):
        """Voltea (espejo) los sprites de izquierda a derecha, con su eje (con deshacer)."""
        sff = self.main.project.sff
        idx = sff.index()
        olds = {}
        for k in dict.fromkeys(tuple(x) for x in keys):
            s = idx.get(k)
            if s is not None:
                olds[k] = (s.pixels().copy(), s.x, s.y, s.palidx)

        def flip():
            ix = sff.index()
            for k, (pix, x, y, pal) in olds.items():
                s = ix.get(k)
                if s is None:
                    continue
                s.set_pixels(np.ascontiguousarray(pix[:, ::-1]))
                s.x, s.y, s.palidx = pix.shape[1] - x, y, pal

        def back():
            ix = sff.index()
            for k, (pix, x, y, pal) in olds.items():
                s = ix.get(k)
                if s is None:
                    continue
                s.set_pixels(pix)
                s.x, s.y, s.palidx = x, y, pal
        self.main.sprites.push(tr('Modo simple: voltear'), flip, back, refresh_list=True)
        self.cache = {}

    def apply_axes(self, changes):
        """Nuevos ejes {(g, n): (x, y)} para los sprites (con deshacer)."""
        sff = self.main.project.sff
        idx = sff.index()
        old = {k: (idx[k].x, idx[k].y) for k in changes if k in idx}

        def put(vals):
            def fn():
                ix = sff.index()
                for k, (x, y) in vals.items():
                    if k in ix:
                        ix[k].x, ix[k].y = x, y
                self.cache = {}
            return fn
        self.main.sprites.push(tr('Alinear cuadros'), put(dict(changes)), put(old))
        self.cache = {}
        return old

    def refit_action_boxes(self, num, changes, old):
        """Una animación que no es del modo simple: al mover el eje de un cuadro, sus cajas se corren igual
        para seguir pegadas al dibujo."""
        p = self.main.project
        a = p.air.find(num) if num is not None else None
        if a is None:
            return
        from ui.anim_tab import clone_action
        b = clone_action(a)
        b.raw = None
        changed = False
        for f in b.frames:
            k = (f.group, f.number)
            if k in changes and k in old:
                dx, dy = changes[k][0] - old[k][0], changes[k][1] - old[k][1]
                f.clsn1 = [(x1 - dx, y1 - dy, x2 - dx, y2 - dy) for x1, y1, x2, y2 in f.clsn1]
                f.clsn2 = [(x1 - dx, y1 - dy, x2 - dx, y2 - dy) for x1, y1, x2, y2 in f.clsn2]
                changed = True
        if changed:
            self.apply_actions([b])

    def set_import_mode(self, mode):
        if self.cfg.get("import_mode") != mode:
            self.cfg["import_mode"] = mode
            self.mark()
        for c in self._mode_combos:
            c.blockSignals(True)
            c.setCurrentIndex(max(0, c.findData(mode)))
            c.blockSignals(False)

    def nav_pages(self):
        return [(self.char_page, tr('👤 Personaje')), (self.moves_page, tr('🚶 Moverse y saltar')),
                (self.attacks_page, tr('👊 Golpes')), (self.specials_page, tr('🔥 Especiales y súper')),
                (self.combos_page, tr('🔗 Combos')), (self.hurt_page, tr('🤕 Recibir golpes')), (self.colors_page, tr('🎨 Colores')),
                (self.voices_page, tr('🔊 Voces')), (self.ai_page, tr('🤖 IA (CPU)'))]

    def nav_pages_end(self):
        """Las que van después de «Selección»."""
        return [(self.finish_page, tr('🏁 Revisar y compartir'))]

    # ---- como una pestaña
    def is_modified(self):
        return self.dirty

    def mark(self):
        self.dirty = True
        self.modifiedChanged.emit()

    def save(self):
        self.flush()
        p = self.main.project
        if p and self.dirty:
            try:
                sg.save_config(p.def_path, self.cfg)
            except OSError as e:
                QMessageBox.warning(self.main, APP_NAME, tr('No pude guardar {0}: {1}').format(
                    sg.config_path(p.def_path).name, e))
                return False
        self.dirty = False
        self.modifiedChanged.emit()
        return True

    def load(self):
        p = self.main.project
        self.code_timer.stop()
        self.cfg = sg.load_config(p.def_path) if p else sg._fill({})
        sg.set_hurt(self.cfg)
        self.pending_drop = []
        self._orig = None
        self.motion.forget()
        self.cache = {}
        self.dirty = False
        self.set_import_mode(self.cfg.get("import_mode", "rgba"))
        self.bind_all()
        if p and self.cfg.pop("pending_apply", False):
            self.apply_imported()

    def apply_imported(self):
        """Personaje recién sacado de otro (Archivo → Personaje nuevo con los sprites de otro): arma las
        animaciones de cada casilla y el código, y lo deja listo para guardar."""
        for key in sg.ANIM_SLOTS:
            if sg.own_frames(self.cfg, key)[0]:
                try:
                    self.anim_slot_changed(key)
                except Exception:
                    import traceback
                    traceback.print_exc()
        self.bind_all()
        self.mark()
        self.sync_moves()
        msg = tr('✅ Sprites puestos en las casillas del modo simple. Revisa cada casilla, usa '
                 '«🎯 Alinear todas con la de parado» si hace falta, y guarda.')
        QTimer.singleShot(300, lambda: self.main.status.setText(msg))

    def bind_all(self):
        for pg in self.pages:
            try:
                pg.bind(self.cfg)
            except Exception:
                import traceback
                traceback.print_exc()
        self.update_warnings()

    def motion_changed(self):
        self.moves_page.bind_moves()
        self.main.update_title()

    def refresh_page(self, page):
        if not self.main.project:
            return
        self.cache = {}
        self._orig = None
        self.motion.forget()
        if page is self.moves_page:
            page.bind_moves()
        if page is self.specials_page:
            page.bind_originals()
        if page in (self.voices_page, self.char_page, self.combos_page, self.colors_page):
            page.bind(self.cfg)
        else:
            for w in page.findChildren(FramesBox):
                w.refresh()
        if page is self.attacks_page:
            for key in page.boxes:
                page.show_damage(key)
                page.show_step(key)
                page.show_more(key)
        self.update_warnings()

    def refresh_theme(self):
        """Vuelve a pintar los avisos de las casillas con los colores del tema nuevo."""
        if not self.main.project:
            return
        for pg in (self.moves_page, self.hurt_page, self.attacks_page):
            for w in pg.findChildren(FramesBox):
                w.refresh()
            pg.update_counts()

    def update_warnings(self):
        p = self.main.project
        msg = ""
        if p:
            cmd = p.file("cmd")
            if cmd is None or cmd.suffix.lower() == ".zss":
                msg = tr('⚠ Este personaje no tiene un archivo .cmd normal: los golpes y especiales del modo simple '
                         'no se pueden agregar.')
        for pg in (self.attacks_page, self.specials_page, self.combos_page, self.voices_page):
            pg.warn.setText(msg)
            pg.warn.setVisible(bool(msg))

    def flush(self):
        if self.code_timer.isActive():
            self.code_timer.stop()
            self.sync_moves()

    # ---- sprites para las vistas
    def sprite(self, g, n):
        p = self.main.project
        if not p:
            return None
        idx = self.cache.get("_index")
        if idx is None:
            idx = self.cache["_index"] = p.sff.index()
        return idx.get((g, n))

    def pixmap(self, g, n):
        key = (g, n)
        if key in self.cache:
            return self.cache[key]
        s = self.sprite(g, n)
        pm = None
        if s is not None:
            try:
                img = sprite_qimage(self.main.project.sff, s)
                pm = QPixmap.fromImage(img) if not img.isNull() else None
            except Exception:
                pm = None
        self.cache[key] = pm
        return pm

    def on_tick(self):
        self.tick += 2
        for w in self.previews:
            try:
                if w.isVisible() and w.frames and len(w.frames) > 1:
                    w.update()
            except RuntimeError:
                pass

    def forget_previews(self, parent):
        gone = set(id(w) for w in parent.findChildren(AnimPreview))
        self.previews = [w for w in self.previews if id(w) not in gone]

    # ---- poner imágenes
    def choose_group(self, hint, old_keys, old_group):
        sff = self.main.project.sff
        counts = Counter(s.group for s in sff.sprites)
        old = set(old_keys)
        if old_group is not None and counts.get(old_group):
            mine = {s.key for s in sff.sprites if s.group == old_group}
            if mine <= old:
                return old_group, True
        reserved = {g for _sec, _t, lst in sg.ANIM_SECTIONS for _k, _ti, _d, g, _f in lst}
        reserved |= {sg.normal_info(k)[4] for k in sg.NORMAL_KEYS}
        g = hint
        while counts.get(g) or (g != hint and g in reserved):
            g += 1
        return g, False

    def import_frames(self, title, hint, old_keys, old_group):
        p = self.main.project
        if not p:
            return None
        from ui.mainwindow import load_settings, save_settings
        start = load_settings().get("last_img_dir", str(p.folder))
        files, _ = QFileDialog.getOpenFileNames(self.main, tr('{0}: elige las imágenes (en orden)').format(title),
                                                start, tr(IMAGE_FILTER))
        if not files:
            return None
        save_settings({"last_img_dir": str(Path(files[0]).parent)})
        files = sorted(files, key=natural_key)
        imgs = []
        for f in files:
            img = QImage(f)
            if img.isNull():
                continue
            rgba = qimage_rgba(img)
            if (rgba[:, :, 3] == 255).all():
                # sin transparencia: el color de la esquina es el fondo
                corner = rgba[0, 0, :3].copy()
                rgba[np.all(rgba[:, :, :3] == corner, axis=2), 3] = 0
            imgs.append((img, rgba))
        if not imgs:
            QMessageBox.warning(self.main, APP_NAME, tr('No pude abrir esas imágenes.'))
            return None
        same = len({r.shape[:2] for _i, r in imgs}) == 1

        def vis(rgba):
            m = rgba[:, :, 3] > 0
            if not m.any():
                h, w = m.shape
                return 0, 0, w, h
            ys, xs = np.where(m)
            return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        frames = []
        if same:
            x0, _y0, x1, _y1 = vis(imgs[0][1])
            bottom = max(vis(r)[3] for _i, r in imgs)
            frames = [(rgba, ((x0 + x1) // 2, bottom)) for _i, rgba in imgs]
        else:
            for _i, rgba in imgs:
                x0, _y0, x1, y1 = vis(rgba)
                frames.append((rgba, ((x0 + x1) // 2, y1)))
        return self.add_frames(frames, hint, old_keys, old_group)

    def cut_frames(self, title, hint, old_keys, old_group):
        """Cuadros sacados de una hoja de sprites con el cortador."""
        if not self.main.project:
            return None
        from ui.sheet_cutter import SheetCutter
        dlg = SheetCutter(self.main, slot_title=title)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        frames = [(c, ax) for c, ax, _row in dlg.frames()]
        if not frames:
            return None
        # un cuadro repetido en la animación se guarda una sola vez como sprite
        ids = dlg.frame_ids() if hasattr(dlg, "frame_ids") else list(range(len(frames)))
        first = {}
        for i, fid in enumerate(ids):
            first.setdefault(fid, i)
        uniq = sorted(first.values())
        res = self.add_frames([frames[i] for i in uniq], hint, old_keys, old_group)
        if not res:
            return None
        keys, group = res
        slot = {ids[i]: keys[n] for n, i in enumerate(uniq)}
        return [slot[fid] for fid in ids], group

    def char_palette_rgb(self):
        p = self.main.project
        sff = p.sff
        if not sff.palettes:
            return None
        pals = p.char_palettes()
        ov = pals[0][2] if pals and pals[0][2] is not None else None
        return (ov or sff.palettes[0]).colors[:, :3]

    def add_frames(self, frames, hint, old_keys, old_group):
        """Agrega [(rgba, (eje_x, eje_y))] como sprites de un grupo (con deshacer). Devuelve (claves, grupo)."""
        p = self.main.project
        sff = p.sff
        group, replace = self.choose_group(hint, old_keys, old_group)
        char_pal = self.char_palette_rgb() if self.cfg.get("import_mode", "rgba") == "char" else None
        created = []
        for i, (rgba, (ax, ay)) in enumerate(frames):
            s = Sprite(group, i)
            if char_pal is not None:
                q = QImage(rgba.tobytes(), rgba.shape[1], rgba.shape[0], rgba.shape[1] * 4,
                           QImage.Format.Format_RGBA8888).copy()
                idx, _rgb = image_to_indices(q, char_pal, None)
                s.set_pixels(idx)
                s.palidx = 0
            else:
                s.set_pixels(np.ascontiguousarray(rgba))
            s.x, s.y = int(ax), int(ay)
            created.append(s)
        keys = [s.key for s in created]
        before = list(sff.sprites)
        drop = {s.key for s in sff.sprites if s.group == group} if replace else set()
        drop |= set(keys)

        def redo():
            sff.sprites[:] = [x for x in before if x.key not in drop] + created
        self.main.sprites.push(tr('Modo simple: poner imágenes'), redo,
                               lambda: sff.sprites.__setitem__(slice(None), before), refresh_list=True)
        self.cache = {}
        return keys, group

    # ---- aplicar
    def apply_actions(self, new_actions, remove=()):
        p = self.main.project
        air = p.air
        nums = {a.number for a in new_actions} | set(remove)
        if not new_actions and not [a for a in air.actions if a.number in nums]:
            return
        new_list = sorted([a for a in air.actions if a.number not in nums] + list(new_actions), key=lambda a: a.number)
        self.main.anims.edit_list(tr('Modo simple'), new_list)

    def fallback_source(self, key):
        """Cuadros y rapidez de la casilla de donde sale `key` cuando está vacía."""
        return self.slot_source(sg.FALLBACK[key][0])

    def slot_source(self, src):
        """Cuadros y rapidez de una casilla: lo puesto en el modo simple o, si no, la animación que el
        personaje ya tenía."""
        keys, t = sg.own_frames(self.cfg, src)
        if keys:
            return keys, t
        a = self.main.project.air.find(sg.anim_slot_numbers(src)[0])
        if a is None or not a.frames or self.is_placeholder(a):
            return [], 5
        t = next((f.time for f in a.frames if f.time > 0), 5)
        return [(f.group, f.number) for f in a.frames], t

    def is_placeholder(self, action):
        """La acción solo usa la figura provisional (0,0) o no tiene nada."""
        return all((f.group, f.number) == (0, 0) for f in action.frames)

    def placeholder(self, num, title):
        a = sg.make_action(num, title, [(0, 0)], 6, "hold", self.main.project.sff.index())
        return a

    def forget_sprites(self, keys, group):
        """Al vaciar una casilla: sus sprites importados se borran después (si nadie más los usa)."""
        if keys and group is not None:
            self.pending_drop.append((set(map(tuple, keys)), group))

    def drop_unused(self):
        p = self.main.project
        if not p or not self.pending_drop:
            return
        used = {(f.group, f.number) for a in p.air.actions for f in a.frames}

        def entries():
            for e in self.cfg["anims"].values():
                yield e
            for e in self.cfg["normals"].values():
                yield e
            yield self.cfg.get("throw") or {}
            for sp in self.cfg.get("specials", []):
                yield sp
                yield sp.get("proj") or {}
                yield sp.get("proj_hit") or {}
            for lst in (self.cfg.get("ad_anims") or {}).values():
                for e in lst or []:
                    yield e
        for e in entries():
            used |= {tuple(k) for k in (e or {}).get("frames", [])}
        drop = set()
        for keys, group in self.pending_drop:
            mine = {s.key for s in p.sff.sprites if s.group == group}
            if mine and mine <= keys:
                drop |= {k for k in mine if k not in used}
        self.pending_drop = []
        if not drop:
            return
        sff = p.sff
        before = list(sff.sprites)
        self.main.sprites.push(tr('Modo simple: vaciar'), lambda: sff.sprites.__setitem__(
            slice(None), [x for x in before if x.key not in drop]),
            lambda: sff.sprites.__setitem__(slice(None), before), refresh_list=True)
        self.cache = {}

    def anim_slot_changed(self, key):
        p = self.main.project
        if not p:
            return
        self.cache = {}
        # las casillas vacías o apagadas se llenan con otra (lo puesto en el modo simple o lo que ya tenía)
        acts = sg.anim_slot_actions(key, self.cfg, p.sff.index(), self.slot_source)
        # lo que quedó sin animación (casilla vaciada) vuelve a la figura provisional
        nums = list(sg.anim_slot_numbers(key))
        for dst, (src, _rev, _pick) in sg.fallbacks(self.cfg).items():
            if src == key and not sg.own_frames(self.cfg, dst)[0]:
                nums += sg.anim_slot_numbers(dst)
        if key == "crouch" and sg.own_frames(self.cfg, "crouch_idle")[0]:
            nums = [x for x in nums if x != 11]          # la pone «Agachado (respirando)»
        have = {a.number for a in acts}
        title = tr(sg.ANIM_SLOTS[key][1])
        acts += [self.placeholder(n, title) for n in nums if n not in have]
        self.apply_actions(acts)
        self.drop_unused()
        self.mark()
        for pg in (self.moves_page, self.hurt_page):
            for _b, fb in pg.boxes.values():
                fb.refresh()
        if key in ("idle", "win", "select_pose"):
            self.main.select.refresh()
        if key == "crouch_idle" and not getattr(self, "_crouch_sync", False):
            self._crouch_sync = True
            try:
                self.anim_slot_changed("crouch")
            finally:
                self._crouch_sync = False

    def is_off(self, key):
        return sg.is_off(self.cfg, key)

    # ---- lo que el personaje ya tiene en su código
    def originals(self):
        if getattr(self, "_orig", None) is None:
            self._orig = self.detect_originals()
        return self._orig

    def detect_originals(self):
        p = self.main.project
        if not p:
            return []
        from core.detect_moves import find_moves
        from core.textio import read_text
        cmd = p.file("cmd")
        if cmd is None or cmd.suffix.lower() == ".zss":
            return []
        want = f"{p.def_path.stem}_simple.st".lower()

        def text_of(path):
            of = self.main.code.open.get(str(path))
            try:
                return of.doc.toPlainText() if of else read_text(path)[0]
            except OSError:
                return ""
        paths = [path for k, path in p.code_files()
                 if k and k.lower() not in ("def", "cmd", "stcommon") and path.name.lower() != want
                 and path.suffix.lower() != ".zss"]
        try:
            return find_moves(text_of(cmd), [text_of(x) for x in paths], sg.ENT_BEGIN, sg.ENT_END,
                              state_files=paths, cmd_file=cmd)
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    def original_move(self, key):
        """El golpe normal (S_x…) o el agarre («throw») que el personaje ya tiene, o None."""
        if key is None:
            return None
        for f in self.originals():
            if (key == "throw" and f.kind == "throw") or (f.kind == "normal" and f.key == key):
                return f
        return None

    def originals_by_states(self, states):
        st = set(states)
        return sorted([f for f in self.originals() if f.state in st and f.kind != "normal_extra"],
                      key=lambda f: f.state)

    def edit_code(self, path, fn):
        """Cambia un archivo de código del personaje (con deshacer en su pestaña)."""
        if path is None:
            return False
        of = self.main.code.get_open(path)
        old = of.doc.toPlainText()
        new = fn(old)
        if new is None or new == old:
            return False
        set_doc_text(of.doc, new)
        self._orig = None
        self.main.update_title()
        return True

    def set_original_damage(self, origs, value):
        from core import detect_moves as dm
        ok = False
        for f in origs[:1]:
            ok |= self.edit_code(f.file, lambda t, f=f: dm.set_damage(t, f.state, value))
        if ok:
            self.main.status.setText(tr('Daño cambiado en el código del personaje.'))

    def set_original_command(self, origs, template):
        from core import detect_moves as dm
        cmd = self.main.project.file("cmd")
        for name in dict.fromkeys(f.cmd_name for f in origs if f.cmd_name):
            self.edit_code(cmd, lambda t, name=name: dm.set_command(t, name, template))

    def replace_original_anims(self, origs, keys, time):
        """Pone cuadros nuevos en las animaciones de un movimiento del personaje (mismo número, mismo código)."""
        p = self.main.project
        idx = p.sff.index()
        hit = sg.best_hit_frame(keys, idx) if keys else None
        acts = []
        for num in dict.fromkeys(f.anim for f in origs if f.anim is not None):
            old = p.air.find(num)
            hold = bool(old and old.frames and old.frames[-1].time == -1)
            a = sg.make_action(num, (old.title if old and getattr(old, "title", None) else origs[0].label), keys,
                               time, "hold" if hold else "once", idx, hit_index=hit)
            acts.append(a)
        if acts:
            self.apply_actions(acts)
            self.cache = {}
            self.mark()

    def retime_originals(self, origs, time):
        from ui.anim_tab import clone_action
        p = self.main.project
        acts = []
        for num in dict.fromkeys(f.anim for f in origs if f.anim is not None):
            old = p.air.find(num)
            if old is None or not old.frames:
                continue
            a = clone_action(old)
            a.raw = None
            for fr in a.frames:
                if fr.time > 0:
                    fr.time = int(time)
            acts.append(a)
        if acts:
            self.apply_actions(acts)
            self.mark()

    def replaced_states(self):
        """Estados del personaje cuyas entradas del .cmd se apagan: los golpes que se rehicieron (o se
        apagaron) en el modo simple y los especiales apagados."""
        out = set(int(n) for n in self.cfg.get("orig_off", []))
        for f in self.originals():
            if f.kind == "normal":
                e = self.cfg["normals"].get(f.key) or {}
                if e.get("frames") or self.is_off(f.key):
                    out.add(f.state)
            elif f.kind == "throw":
                if (self.cfg.get("throw") or {}).get("frames") or self.is_off("throw"):
                    out.add(f.state)
        return out

    def set_orig_off(self, states, off):
        cur = set(self.cfg.get("orig_off", []))
        if off:
            cur |= set(states)
        else:
            cur -= set(states)
        self.cfg["orig_off"] = sorted(cur)
        self.moves_changed()
        self.specials_page.bind_originals()

    def set_off(self, key, off):
        """Tick de una casilla opcional: el personaje tiene (o no) ese movimiento."""
        cur = set(self.cfg.get("off", []))
        if (key in cur) == bool(off):
            return
        if off:
            cur.add(key)
        else:
            cur.discard(key)
        self.cfg["off"] = sorted(cur)
        if key in sg.ANIM_SLOTS:
            self.anim_slot_changed(key)
            if key == "jump_fwd":
                for k2 in ("jump_up", "jump_down"):
                    self.anim_slot_changed(k2)
        if key in sg.OPTIONAL_MOVES or key in sg.CMD_STATES:
            self.moves_changed()
        self.mark()
        for pg in (self.moves_page, self.hurt_page, self.attacks_page):
            for w in pg.findChildren(FramesBox):
                w.refresh()

    def moves_changed(self):
        if not self.main.project:
            return
        self.mark()
        self.code_timer.start()

    def st_path(self):
        p = self.main.project
        want = f"{p.def_path.stem}_simple.st"
        for k, v in p.defs.keys("Files"):
            if v and Path(v).name.lower() == want.lower():
                f = p.file(k)
                if f is not None:
                    return f
        path = p.folder / want
        if not path.exists():
            path.write_text("; " + tr('Movimientos del modo simple') + "\n", encoding="utf-8")
        keys = {k.lower() for k, _v in p.defs.keys("Files")}
        key = "st" if "st" not in keys else next(f"st{i}" for i in range(1, 100) if f"st{i}" not in keys)
        p.defs.set("Files", key, want)
        p.defs_dirty = True
        self.main.def_tab.load_form_only()
        self.main.def_tab.set_modified()
        return path

    def sync_moves(self):
        p = self.main.project
        if not p:
            return
        from core.codeinfo import statedefs_in
        from core.textio import read_text
        sprites = p.sff.index()
        st_file = None
        want = f"{p.def_path.stem}_simple.st".lower()
        taken_states = set()
        for _k, path in p.code_files():
            if path.name.lower() == want:
                st_file = path
                continue
            if path.suffix.lower() == ".def":
                continue
            of = self.main.code.open.get(str(path))
            try:
                taken_states |= statedefs_in(of.doc.toPlainText() if of else read_text(path)[0])
            except OSError:
                pass
        owned = set(self.cfg.get("owned", []))
        taken_actions = {a.number for a in p.air.actions} - owned
        k = p.localcoord()[0] / 320
        gen = sg.generate(self.cfg, sprites, k, taken_states, taken_actions, tr, self.motion.scale(), air=p.air)
        new_owned = {a.number for a in gen.actions}
        self.apply_actions(gen.actions, owned - new_owned)
        cmd = p.file("cmd")
        if cmd is not None and cmd.suffix.lower() != ".zss":
            of = self.main.code.get_open(cmd)
            old = of.doc.toPlainText()
            new = sg.cmd_text(old, gen, tr('Esto lo escribe el modo simple del editor: no lo cambies a mano, '
                                           'se rehace solo.'))
            new = sg.toggle_cmd_entries(new, self.cfg, self.replaced_states())
            if new != old:
                set_doc_text(of.doc, new)
        if gen.states or st_file is not None or sg.has_moves(self.cfg):
            path = st_file or self.st_path()
            of = self.main.code.get_open(path)
            text = sg.st_text(gen, "; " + tr('Movimientos del modo simple del editor. Este archivo se rehace '
                                             'solo cada vez que cambias algo en el modo simple: no lo edites a '
                                             'mano (los cambios se perderían).'))
            if of.doc.toPlainText() != text:
                set_doc_text(of.doc, text)
        self.main.sim.states = {}
        self._orig = None
        self.drop_unused()
        self.last_problems = list(gen.problems)
        if gen.problems:
            self.main.status.setText(tr('⚠ No encontré números libres para: {0}').format(", ".join(gen.problems)))
        self.main.update_title()

    # ---- ir a una casilla
    def goto_slot(self, key):
        for pg in (self.moves_page, self.hurt_page):
            if key in pg.boxes:
                self.main.tabs.setCurrentWidget(pg)
                box = pg.boxes[key][0]
                box.set_open(True)
                QTimer.singleShot(60, lambda: pg.ensureWidgetVisible(box, 50, 50))
                return
