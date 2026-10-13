"""«🎨 Crear combo visual»: armas un autodoble escogiendo las animaciones con dibujitos, lo ves animado
después del especial con que inicia y lo agregas a la lista de combos."""
import copy

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap, QTransform
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from core import combos
from core import simple_gen as sg
from i18n import tr
from ui import theme
from ui.combo_test import ComboCanvas, ad_actions, find_action, make_timeline, setup_stage
from ui.combos_page import BUTTON_CHOICES
from ui.common import PlaybackBar, advance

THUMB = 72


class VisualCombo(QDialog):
    def __init__(self, page, ad=None):
        super().__init__(page.sm.main)
        self.page = page
        self.result_ad = None
        self.editing = ad is not None
        self.ad = copy.deepcopy(ad) if ad else combos.new_ad(1, [])
        self.setWindowTitle(tr('🎨 Crear combo visual') if not self.editing else tr('🎨 Editar autodoble'))
        self.resize(1180, 720)
        setup_stage(self, page.sm)
        items = page.anim_items()
        self.anims = {ref: (t, num) for ref, t, num in items}
        self.openers = page.opener_items()
        self._binding = True

        lay = QHBoxLayout(self)
        # ---- izquierda: la galería de animaciones
        left = QVBoxLayout()
        hint = QLabel(tr('Animaciones (doble clic o «➕» para ponerla en el combo):'))
        hint.setWordWrap(True)
        left.addWidget(hint)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr('Buscar…'))
        self.filter.textChanged.connect(self.apply_filter)
        left.addWidget(self.filter)
        self.gallery = QListWidget()
        self.gallery.setViewMode(QListWidget.ViewMode.IconMode)
        self.gallery.setIconSize(QSize(THUMB, THUMB))
        self.gallery.setGridSize(QSize(THUMB + 46, THUMB + 44))
        self.gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.gallery.setMovement(QListWidget.Movement.Static)
        self.gallery.setWordWrap(True)
        for ref, t, num in items:
            it = QListWidgetItem(self.icon(num), self.short(t))
            it.setToolTip(t + (f"  [{num}]" if num is not None else ""))
            it.setData(Qt.ItemDataRole.UserRole, ref)
            self.gallery.addItem(it)
        self.gallery.itemDoubleClicked.connect(lambda it: self.add_hit(it.data(Qt.ItemDataRole.UserRole)))
        left.addWidget(self.gallery, 1)
        b = QPushButton(tr('➕ Poner en el combo'))
        b.clicked.connect(lambda: self.gallery.currentItem() and
                          self.add_hit(self.gallery.currentItem().data(Qt.ItemDataRole.UserRole)))
        left.addWidget(b)
        lw = QWidget()
        lw.setLayout(left)
        lw.setFixedWidth(360)
        lay.addWidget(lw)

        # ---- derecha: datos, la tira de golpes y la vista animada
        right = QVBoxLayout()
        g = QGridLayout()
        g.setColumnStretch(1, 1)
        self.name = QLineEdit(self.ad.get("name", ""))
        self.name.setPlaceholderText(tr('Autodoble'))
        g.addWidget(QLabel(tr('Nombre:')), 0, 0)
        g.addWidget(self.name, 0, 1)
        self.strength = QComboBox()
        for s in range(3):
            self.strength.addItem(tr(sg.STRENGTH[s]), s)
        self.strength.setCurrentIndex(int(self.ad.get("strength", 1)))
        self.button = QComboBox()
        for k, t in BUTTON_CHOICES:
            self.button.addItem(tr(t), k)
        self.button.setCurrentIndex(max(0, self.button.findData(self.ad.get("button", "any"))))
        row = QHBoxLayout()
        row.addWidget(self.strength)
        row.addWidget(self.button, 1)
        row.addWidget(QLabel(tr('Daño de cada golpe:')))
        self.damage = QSpinBox()
        self.damage.setRange(1, 300)
        self.damage.setValue(int(self.ad.get("damage") or 20))
        row.addWidget(self.damage)
        g.addWidget(QLabel(tr('Botón:')), 1, 0)
        g.addLayout(row, 1, 1)
        self.opener = QComboBox()
        self.opener.addItem(tr('(cualquier especial)'), "")
        for ref, t, _n in self.openers:
            self.opener.addItem(t, ref)
        self.opener.setCurrentIndex(max(0, self.opener.findData(self.ad.get("open", ""))))
        self.opener.currentIndexChanged.connect(self.build)
        g.addWidget(QLabel(tr('Inicia con:')), 2, 0)
        g.addWidget(self.opener, 2, 1)
        right.addLayout(g)

        right.addWidget(QLabel(tr('Golpes del autodoble (en orden; arrástralos para cambiar el orden):')))
        self.seq = QListWidget()
        self.seq.setViewMode(QListWidget.ViewMode.IconMode)
        self.seq.setFlow(QListWidget.Flow.LeftToRight)
        self.seq.setWrapping(False)
        self.seq.setIconSize(QSize(THUMB, THUMB))
        self.seq.setGridSize(QSize(THUMB + 46, THUMB + 44))
        self.seq.setFixedHeight(THUMB + 66)
        self.seq.setMovement(QListWidget.Movement.Snap)
        self.seq.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.seq.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.seq.model().rowsMoved.connect(lambda *_a: self.build())
        self.seq.currentRowChanged.connect(self.on_pick)
        right.addWidget(self.seq)
        row = QHBoxLayout()
        for txt, fn in (("◀", lambda: self.move(-1)), ("▶", lambda: self.move(1)),
                        (tr('⧉ Repetir'), self.dup_hit), (tr('✖ Quitar golpe'), self.del_hit)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(QLabel(tr('Rapidez del golpe escogido:')))
        self.speed = QSpinBox()
        self.speed.setRange(25, 400)
        self.speed.setSuffix(" %")
        self.speed.setSingleStep(10)
        self.speed.valueChanged.connect(self.on_speed)
        row.addWidget(self.speed)
        right.addLayout(row)
        self.warn = QLabel()
        self.warn.setObjectName("Warn")
        self.warn.setWordWrap(True)
        right.addWidget(self.warn)

        self.canvas = ComboCanvas(self)
        right.addWidget(self.canvas, 1)
        right.addWidget(PlaybackBar(self.canvas))
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton(tr('Cancelar'))
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        ok = QPushButton(tr('✔ Guardar') if self.editing else tr('➕ Agregar a la lista de combos'))
        ok.setDefault(True)
        ok.clicked.connect(self.on_ok)
        row.addWidget(ok)
        right.addLayout(row)
        lay.addLayout(right, 1)

        for h in self.ad.get("hits") or []:
            self.add_hit(h.get("ref") or "", int(h.get("speed") or 100), rebuild=False)
        self._binding = False
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(lambda: advance(self.canvas))
        self.timer.start()
        self.build()

    # ---- dibujitos
    def short(self, t):
        t = t.split("  · ")[0]
        return t if len(t) <= 26 else t[:24] + "…"

    def icon(self, num):
        """El primer cuadro de la animación (o el que pega) como dibujito."""
        pm = QPixmap(THUMB, THUMB)
        pm.fill(QColor(theme.CANVAS))
        a = find_action(self, num)
        if a is not None:
            f = next((f for f in a.frames if f.clsn1), a.frames[0])
            src = self.sm.pixmap(f.group, f.number)
            if src is not None and not src.isNull():
                src = src.scaled(THUMB - 4, THUMB - 4, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
                if "h" in (f.flip or "").lower():
                    src = src.transformed(QTransform().scale(-1, 1))
                p = QPainter(pm)
                p.drawPixmap((THUMB - src.width()) // 2, THUMB - src.height() - 2, src)
                p.end()
        return QIcon(pm)

    def apply_filter(self, text):
        t = text.strip().lower()
        for i in range(self.gallery.count()):
            it = self.gallery.item(i)
            it.setHidden(bool(t) and t not in it.toolTip().lower())

    # ---- la tira de golpes
    def add_hit(self, ref, speed=100, rebuild=True):
        if not ref:
            return
        t, num = self.anims.get(ref, (self.page.ref_name(ref), None))
        it = QListWidgetItem(self.icon(num), self.label(t, speed))
        it.setData(Qt.ItemDataRole.UserRole, ref)
        it.setData(Qt.ItemDataRole.UserRole + 1, int(speed))
        it.setToolTip(t)
        self.seq.addItem(it)
        self.seq.setCurrentItem(it)
        if rebuild:
            self.build()

    def label(self, t, speed):
        return self.short(t) + (f"\n{speed} %" if speed != 100 else "")

    def hits(self):
        out = []
        for i in range(self.seq.count()):
            it = self.seq.item(i)
            out.append({"ref": it.data(Qt.ItemDataRole.UserRole),
                        "speed": int(it.data(Qt.ItemDataRole.UserRole + 1) or 100)})
        return out

    def on_pick(self, r):
        it = self.seq.item(r) if r >= 0 else None
        self.speed.blockSignals(True)
        self.speed.setValue(int(it.data(Qt.ItemDataRole.UserRole + 1) or 100) if it else 100)
        self.speed.setEnabled(it is not None)
        self.speed.blockSignals(False)

    def on_speed(self, v):
        it = self.seq.currentItem()
        if it is None:
            return
        it.setData(Qt.ItemDataRole.UserRole + 1, int(v))
        it.setText(self.label(it.toolTip(), int(v)))
        self.build()

    def move(self, d):
        r = self.seq.currentRow()
        n = r + d
        if r < 0 or not (0 <= n < self.seq.count()):
            return
        it = self.seq.takeItem(r)
        self.seq.insertItem(n, it)
        self.seq.setCurrentRow(n)
        self.build()

    def dup_hit(self):
        it = self.seq.currentItem()
        if it is not None:
            self.add_hit(it.data(Qt.ItemDataRole.UserRole), int(it.data(Qt.ItemDataRole.UserRole + 1) or 100))

    def del_hit(self):
        r = self.seq.currentRow()
        if r >= 0:
            self.seq.takeItem(r)
            self.build()

    # ---- la vista animada: el especial con que inicia y el autodoble
    def build(self, *_a):
        if self._binding:
            return
        ad = {"hits": self.hits()}
        acts = ad_actions(self, ad)
        segs = []
        ref = self.opener.currentData()
        if not ref:
            ref = next((r for r, _t, n in self.openers if self.page.hits(n)), None)
        if ref:
            t, num = next(((t, n) for r, t, n in self.openers if r == ref), (ref, None))
            a = find_action(self, num)
            if a is not None:
                segs.append((t, [(a, 100)], "sp", None))
        name = self.name.text().strip() or tr('Autodoble')
        segs.append(("🔁 " + name, acts, "ad", None))
        warn = []
        if not self.hits():
            warn.append(tr('Pon por lo menos un golpe.'))
        nohit = [self.short(self.anims.get(h["ref"], (h["ref"], None))[0]) for h in self.hits()
                 if self.page.hits(self.anims.get(h["ref"], (None, None))[1]) is False]
        if nohit:
            warn.append(tr('Estas no tienen caja de golpe (rojo) y no van a pegar: {0}').format(", ".join(nohit)))
        self.warn.setText("⚠ " + " ".join(warn) if warn else "")
        self.warn.setVisible(bool(warn))
        self.timeline = make_timeline(self, segs) if acts else []
        self.canvas.tick = 0
        self.canvas.update()

    def on_ok(self):
        hits = self.hits()
        if not hits:
            self.warn.setText("⚠ " + tr('Pon por lo menos un golpe.'))
            self.warn.show()
            return
        ad = self.ad
        ad["name"] = self.name.text().strip()
        ad["strength"] = int(self.strength.currentData())
        ad["button"] = self.button.currentData()
        ad["open"] = self.opener.currentData() or ""
        ad["hits"] = hits
        ad["damage"] = int(self.damage.value())
        self.result_ad = ad
        self.accept()
