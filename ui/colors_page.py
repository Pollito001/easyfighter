"""Página «🎨 Colores» del modo simple: colores alternativos del personaje (paletas 1 a 12)."""
import numpy as np
from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QColorDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QSpinBox, QToolButton, QVBoxLayout, QWidget, QComboBox,
)

from core import palettes as P
from core.sff import Palette
from i18n import tr
from ui import theme
from ui.common import APP_NAME
from ui.palette_widget import PaletteGrid

MAX_PALS = 12
POSES = [(0, 'Parado'), (20, 'Caminando'), (11, 'Agachado'), (41, 'Saltando'), (200, 'Puño débil'),
         (230, 'Patada débil'), (210, 'Puño medio'), (1000, 'Especial'), (5000, 'Recibiendo un golpe'),
         (180, 'Ganar'), (190, 'Intro')]


def pad256(rgb):
    """Paleta de 256 colores (algunas del SFF traen menos)."""
    a = np.asarray(rgb, np.uint8)[:256, :3]
    out = np.zeros((256, 3), np.uint8)
    out[:len(a)] = a
    return out


def rgb_to_rgba(rgb):
    cols = np.zeros((256, 4), np.uint8)
    cols[:, :3] = pad256(rgb)
    cols[:, 3] = 255
    cols[0, 3] = 0
    return cols


class Preview(QWidget):
    """El personaje con una paleta. Clic: elige la parte que está debajo del ratón; doble clic: la cambia."""
    picked = pyqtSignal(int)
    edit = pyqtSignal(int)

    def __init__(self, title):
        super().__init__()
        self.title = title
        self.img = None
        self.idx = None
        self.setMinimumSize(QSize(220, 280))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_image(self, img, idx, title=None):
        self.img, self.idx = img, idx
        if title:
            self.title = title
        self.update()

    def _geom(self):
        r = QRectF(self.rect()).adjusted(6, 26, -6, -6)
        if self.img is None or self.img.isNull():
            return r, 1.0
        z = min(r.width() / self.img.width(), r.height() / self.img.height(), 4.0)
        w, h = self.img.width() * z, self.img.height() * z
        return QRectF(r.center().x() - w / 2, r.bottom() - h, w, h), z

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.CANVAS))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 8, 8)
        p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(10, 4, self.width() - 20, 20), Qt.AlignmentFlag.AlignLeft, self.title)
        if self.img is not None and not self.img.isNull():
            r, _z = self._geom()
            p.drawImage(r, self.img)
        p.end()

    def index_at(self, pos):
        if self.idx is None:
            return -1
        r, z = self._geom()
        x, y = int((pos.x() - r.left()) / z), int((pos.y() - r.top()) / z)
        h, w = self.idx.shape
        if 0 <= x < w and 0 <= y < h:
            return int(self.idx[y, x])
        return -1

    def mousePressEvent(self, e):
        i = self.index_at(e.position())
        if i > 0:
            self.picked.emit(i)

    def mouseDoubleClickEvent(self, e):
        i = self.index_at(e.position())
        if i > 0:
            self.edit.emit(i)


class ColorsPage(QWidget):
    """Va dentro de una página del modo simple (ver SimpleMode)."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.sm = page.sm
        self.counts = np.zeros(256, np.int64)
        self.labels = -np.ones(256, np.int64)
        self.sel_part = -1
        self._key = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        # aviso: sprites de 32 bits
        self.tc_box = QFrame()
        self.tc_box.setObjectName("Card")
        tl = QHBoxLayout(self.tc_box)
        self.tc_label = QLabel()
        self.tc_label.setWordWrap(True)
        tl.addWidget(self.tc_label, 1)
        self.tc_btn = QPushButton(tr('🎨 Pasar los sprites a la paleta del personaje'))
        self.tc_btn.setObjectName("primary")
        self.tc_btn.clicked.connect(self.convert_true_color)
        tl.addWidget(self.tc_btn)
        lay.addWidget(self.tc_box)
        body = QHBoxLayout()
        body.setSpacing(14)
        lay.addLayout(body, 1)
        # ---- izquierda: paletas
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>" + tr('Paletas') + "</b>"))
        self.list = QListWidget()
        self.list.setIconSize(QSize(96, 22))
        self.list.setMinimumWidth(230)
        self.list.setMaximumWidth(290)
        self.list.currentRowChanged.connect(lambda _r: self.show_current())
        left.addWidget(self.list, 1)
        g = QGridLayout()
        self.b_new = QPushButton(tr('➕ Nueva'))
        self.b_new.setToolTip(tr('Una paleta nueva igual a la original, para cambiarle los colores.'))
        self.b_new.clicked.connect(lambda: self.new_palette("copy"))
        self.b_rand = QPushButton(tr('🎲 Nueva al azar'))
        self.b_rand.setToolTip(tr('Una paleta nueva con colores al azar que combinan (los negros y contornos se quedan).'))
        self.b_rand.clicked.connect(lambda: self.new_palette("random"))
        self.b_dup = QPushButton(tr('📋 Duplicar'))
        self.b_dup.setToolTip(tr('Copia de la paleta elegida.'))
        self.b_dup.clicked.connect(lambda: self.new_palette("dup"))
        self.b_del = QPushButton(tr('🗑 Borrar'))
        self.b_del.clicked.connect(self.delete_palette)
        for i, b in enumerate((self.b_new, self.b_rand, self.b_dup, self.b_del)):
            g.addWidget(b, i // 2, i % 2)
        left.addLayout(g)
        left.addWidget(self._muted(tr('En la selección de personajes cada botón elige una de estas paletas. '
                                      'La 1 es la original.')))
        body.addLayout(left)
        # ---- centro: el personaje
        mid = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Pose:')))
        self.pose = QComboBox()
        self.pose.currentIndexChanged.connect(lambda _i: self.redraw())
        row.addWidget(self.pose, 1)
        self.hl = QToolButton()
        self.hl.setText(tr('Resaltar la parte'))
        self.hl.setCheckable(True)
        self.hl.setChecked(True)
        self.hl.toggled.connect(lambda _c: self.redraw())
        row.addWidget(self.hl)
        mid.addLayout(row)
        pv = QHBoxLayout()
        self.orig = Preview(tr('Original (paleta 1)'))
        self.cur = Preview("")
        for v in (self.orig, self.cur):
            v.picked.connect(self.pick_index)
            v.edit.connect(self.edit_index)
            pv.addWidget(v, 1)
        mid.addLayout(pv, 1)
        mid.addWidget(self._muted(tr('Clic en el personaje: elige esa parte · doble clic: cámbiale el color.')))
        body.addLayout(mid, 1)
        # ---- derecha: partes y colores
        right = QVBoxLayout()
        hr = QHBoxLayout()
        hr.addWidget(QLabel("<b>" + tr('Partes') + "</b>"))
        hr.addStretch(1)
        hr.addWidget(QLabel(tr('Cuántas:')))
        self.k = QSpinBox()
        self.k.setRange(2, 16)
        self.k.setToolTip(tr('En cuántas partes se agrupan los colores (piel, ropa, pelo…). Si dos cosas que '
                             'quieres por separado salen juntas, sube el número.'))
        self.k.valueChanged.connect(self.on_k)
        hr.addWidget(self.k)
        right.addLayout(hr)
        self.parts_box = QWidget()
        self.parts_lay = QGridLayout(self.parts_box)
        self.parts_lay.setContentsMargins(0, 0, 0, 0)
        self.parts_lay.setHorizontalSpacing(8)
        self.parts_lay.setVerticalSpacing(4)
        right.addWidget(self.parts_box)
        br = QHBoxLayout()
        self.b_rand_this = QPushButton(tr('🎲 Al azar'))
        self.b_rand_this.setToolTip(tr('Colores al azar para esta paleta.'))
        self.b_rand_this.clicked.connect(self.randomize_current)
        self.b_reset = QPushButton(tr('↺ Como la original'))
        self.b_reset.clicked.connect(self.reset_current)
        br.addWidget(self.b_rand_this)
        br.addWidget(self.b_reset)
        right.addLayout(br)
        right.addWidget(QLabel("<b>" + tr('Colores uno por uno') + "</b>"))
        self.grid = PaletteGrid()
        self.grid.setToolTip(tr('Doble clic en un color para cambiar solo ese. Los oscurecidos no se usan.'))
        self.grid.edited.connect(self.on_single)
        self.grid.picked.connect(self.pick_index)
        right.addWidget(self.grid)
        self.ro_note = self._muted(tr('La paleta 1 es la original: para cambiar colores crea una nueva '
                                      '(➕ Nueva o 🎲 Nueva al azar).'))
        right.addWidget(self.ro_note)
        right.addStretch(1)
        rw = QWidget()
        rw.setLayout(right)
        rw.setMaximumWidth(330)
        body.addWidget(rw)

    @staticmethod
    def _muted(text):
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setStyleSheet(f"color: {theme.MUTED};")
        return lab

    # ---------------------------------------------------------------- datos
    def project(self):
        return self.sm.main.project

    def store(self):
        return self.sm.cfg.setdefault("colors", {"k": 8, "pals": {}})

    def entries(self):
        """{n: (nombre, Palette|None, "act"|"sff")}"""
        p = self.project()
        out = {}
        for n, name, pal in p.char_palettes():
            if 1 <= n <= MAX_PALS:
                out[n] = (name, pal, "sff" if str(name).startswith("SFF ") else "act")
        if 1 not in out and p.sff.palettes:
            out[1] = ("SFF 1,1", p.sff.palettes[0], "sff")
        return out

    def colors_of(self, n):
        e = self.entries().get(n)
        if e and e[1] is not None:
            return pad256(e[1].colors)
        return self.base1()

    def base1(self):
        e = self.entries().get(1)
        if e and e[1] is not None:
            return pad256(e[1].colors)
        return np.zeros((256, 3), np.uint8)

    def write(self, n, rgb):
        """Guarda los colores de la paleta n donde la lee el juego (.act del .def o la 1,n del SFF)."""
        p = self.project()
        sff = p.sff
        e = self.entries().get(n)
        cols = rgb_to_rgba(rgb)
        if e and e[2] == "act" and e[1] is not None:
            e[1].colors = cols
            self.sm.main.act_modified(e[1])
        else:
            # del mismo tamaño que la del personaje (IKEMEN GO no cambia a una paleta de otro tamaño)
            i = sff.find_palette(1, n)
            i1 = sff.find_palette(1, 1)
            size = 256 if (n == 1 or i1 is None) else len(sff.palettes[i1].colors)
            cols = cols[:max(1, min(256, size))]
            if i is None:
                sff.palettes.append(Palette(1, n, cols))
            else:
                sff.palettes[i].colors = cols
            sff.modified = True
        self.touched()

    def touched(self):
        self.sm.cache = {}
        main = self.sm.main
        try:
            main.anims._pix.clear()
        except AttributeError:
            pass
        main.sprites.modifiedChanged.emit()
        main.update_title()

    def recipe(self, n, create=False):
        pals = self.store().setdefault("pals", {})
        rec = pals.get(str(n))
        if rec is None and create:
            rec = pals[str(n)] = {"parts": {}, "singles": {}}
            if n in self.entries():
                rec["base"] = self.colors_of(n).tolist()     # paleta que ya tenía: se parte de ella
        return rec

    def apply(self, n):
        rec = self.recipe(n, create=True)
        base = np.asarray(rec["base"], np.uint8) if rec.get("base") else self.base1()
        rgb = P.recolor(base, self.counts, self.labels, rec.get("parts"), rec.get("singles"))
        self.write(n, rgb)
        self.sm.mark()

    # ---------------------------------------------------------------- mostrar
    def bind(self):
        p = self.project()
        if not p:
            return
        st = self.store()
        self.k.blockSignals(True)
        self.k.setValue(int(st.get("k", 8)))
        self.k.blockSignals(False)
        self.analyze()
        self.fill_poses()
        self.fill_list()

    def analyze(self, force=False):
        p = self.project()
        sff = p.sff
        key = (id(sff), len(sff.sprites), sum(1 for s in sff.sprites if s.base()._pix is not None and
                                                s.base()._pix.ndim == 2), int(self.k.value()))
        if key != self._key or force:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                self.counts = P.usage(sff)
                self.labels = P.find_parts(self.base1(), self.counts, int(self.k.value()))
                self.tc = P.true_color_sprites(sff)
            finally:
                QApplication.restoreOverrideCursor()
            self._key = key
        n8 = len(P.char_sprites(sff))
        if self.tc:
            self.tc_label.setText(tr(
                '⚠ <b>{0} sprites están en color verdadero (32 bits)</b> y las paletas no les cambian el color '
                '(así funciona IKEMEN GO). Pásalos a la paleta del personaje: se ven igual (hasta 255 colores '
                'compartidos) y ya se les pueden hacer colores alternativos. Los retratos (grupo 9000) se quedan '
                'como están.').format(len(self.tc)) + ("" if not n8 else " " + tr('{0} sprites ya usan la paleta.').format(n8)))
            self.tc_box.show()
        else:
            self.tc_box.hide()

    def fill_poses(self):
        p = self.project()
        cur = self.pose.currentData()
        self.pose.blockSignals(True)
        self.pose.clear()
        for num, label in POSES:
            a = p.air.find(num)
            if a and a.frames:
                self.pose.addItem(tr(label), num)
        self.pose.setCurrentIndex(max(0, self.pose.findData(cur)))
        self.pose.blockSignals(False)

    def fill_list(self, select=None):
        ents = self.entries()
        cur = select if select is not None else self.current()
        self.list.blockSignals(True)
        self.list.clear()
        for n in sorted(ents):
            name, pal, kind = ents[n]
            label = tr('Paleta {0}').format(n) + ("  " + tr('(original)') if n == 1 else "")
            if pal is None:
                label += "  " + tr('(falta {0})').format(name)
            it = QListWidgetItem(self.swatch_icon(self.colors_of(n)), label)
            it.setData(Qt.ItemDataRole.UserRole, n)
            it.setToolTip(tr('Se guarda en: {0}').format(name if kind == "act" else f"SFF 1,{n}"))
            self.list.addItem(it)
        self.list.blockSignals(False)
        rows = [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]
        self.list.setCurrentRow(rows.index(cur) if cur in rows else 0)
        self.b_new.setEnabled(len(ents) < MAX_PALS)
        self.b_rand.setEnabled(len(ents) < MAX_PALS)
        self.b_dup.setEnabled(len(ents) < MAX_PALS)
        self.show_current()

    def swatch_icon(self, rgb):
        pm = QPixmap(96, 22)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        nparts = int(self.labels.max()) + 1 if (self.labels >= 0).any() else 0
        cols = [P.part_color(rgb, self.counts, self.labels, j) for j in range(min(nparts, 8))] or [(60, 60, 60)]
        w = 96 / len(cols)
        for i, c in enumerate(cols):
            p.fillRect(QRectF(i * w, 0, w + 1, 22), QColor(*c))
        p.setPen(QPen(QColor(0, 0, 0, 120), 1))
        p.drawRect(0, 0, 95, 21)
        p.end()
        return QIcon(pm)

    def current(self):
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else 1

    def show_current(self):
        n = self.current()
        ro = n == 1
        self.ro_note.setVisible(ro)
        self.b_rand_this.setEnabled(not ro)
        self.b_reset.setEnabled(not ro)
        ents = self.entries()
        self.b_del.setEnabled(not ro and n in ents and ents[n][2] == "sff")
        self.b_del.setToolTip(tr('Quita esta paleta.') if n in ents and ents[n][2] == "sff" else
                              tr('Esta paleta viene de un archivo .act del .def: quítala en «Datos» (modo avanzado).'))
        self.cur.title = tr('Paleta {0}').format(n)
        self.fill_parts()
        pal = Palette(1, n, rgb_to_rgba(self.colors_of(n)))
        self.grid.set_palette(pal, self.counts > 0)
        self.grid.setEnabled(not ro)
        self.redraw()

    def fill_parts(self):
        lay = self.parts_lay
        while lay.count():
            it = lay.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        n = self.current()
        rgb = self.colors_of(n)
        orig = self.base1()
        nparts = int(self.labels.max()) + 1 if (self.labels >= 0).any() else 0
        if not nparts:
            lay.addWidget(self._muted(tr('Todavía no hay sprites que usen la paleta del personaje.')), 0, 0)
            return
        rec = self.recipe(n) or {}
        for j in range(nparts):
            ncol = int((self.labels == j).sum())
            o = QToolButton()
            o.setFixedSize(26, 22)
            o.setStyleSheet(f"background: rgb{P.part_color(orig, self.counts, self.labels, j)}; border: 1px solid rgba(0,0,0,130);")
            o.setToolTip(tr('Así es en la original'))
            o.clicked.connect(lambda _c, j=j: self.select_part(j))
            arrow = QLabel("→")
            b = QPushButton(tr('Parte {0}').format(j + 1) + f"  ·  {ncol}")
            c = P.part_color(rgb, self.counts, self.labels, j)
            lum = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
            b.setStyleSheet(f"QPushButton {{ background: rgb{c}; color: {'#000' if lum > 140 else '#fff'};"
                            f" border: {'3px solid ' + theme.ACCENT if j == self.sel_part else '1px solid rgba(0,0,0,130)'};"
                            " border-radius: 5px; padding: 3px 8px; text-align: left; }")
            b.setToolTip(tr('Clic: cambiar el color de esta parte ({0} colores de la paleta)').format(ncol))
            b.setEnabled(n != 1)
            b.clicked.connect(lambda _c, j=j: self.edit_part(j))
            r = QToolButton()
            r.setText("↺")
            r.setToolTip(tr('Devolverla como la original'))
            r.setEnabled(n != 1 and str(j) in (rec.get("parts") or {}))
            r.clicked.connect(lambda _c, j=j: self.reset_part(j))
            lay.addWidget(o, j, 0)
            lay.addWidget(arrow, j, 1)
            lay.addWidget(b, j, 2)
            lay.addWidget(r, j, 3)
        lay.setColumnStretch(2, 1)

    def pose_sprite(self):
        p = self.project()
        num = self.pose.currentData()
        a = p.air.find(num) if num is not None else None
        if not a or not a.frames:
            for s in P.char_sprites(p.sff) or p.sff.sprites:
                return s
            return None
        fr = a.frames[len(a.frames) // 2]
        return self.sm.sprite(fr.group, fr.number)

    def render(self, s, rgb):
        pix = s.pixels()
        if pix.ndim == 3:
            h, w = pix.shape[:2]
            return QImage(pix.tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888).copy(), None
        p = self.project()
        mine = s.base().palidx == P.char_index(p.sff)
        if mine:
            cols = rgb_to_rgba(rgb).astype(np.float32)
        else:
            cols = p.sff.palette_for(s).colors.astype(np.float32).copy()
        out = cols[pix]
        out[pix == 0, 3] = 0
        if self.hl.isChecked() and self.sel_part >= 0 and mine:
            dim = (self.labels[pix] != self.sel_part) & (pix != 0)
            out[dim, :3] = out[dim, :3] * 0.28 + 20
        out = np.ascontiguousarray(out.astype(np.uint8))
        h, w = pix.shape
        return QImage(out.tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888).copy(), pix

    def redraw(self):
        if not self.project():
            return
        s = self.pose_sprite()
        if s is None:
            self.orig.set_image(None, None)
            self.cur.set_image(None, None)
            return
        n = self.current()
        self.orig.set_image(*self.render(s, self.base1()))
        img, idx = self.render(s, self.colors_of(n))
        self.cur.set_image(img, idx, tr('Paleta {0}').format(n))

    # ---------------------------------------------------------------- editar
    def ask_color(self, start, title):
        c = QColorDialog.getColor(QColor(*[int(v) for v in start]), self, title)
        return [c.red(), c.green(), c.blue()] if c.isValid() else None

    def select_part(self, j):
        self.sel_part = -1 if self.sel_part == j else j
        self.fill_parts()
        self.redraw()

    def pick_index(self, i):
        j = int(self.labels[i]) if 0 <= i < 256 else -1
        if j >= 0:
            self.sel_part = j
            self.fill_parts()
            self.redraw()

    def edit_index(self, i):
        j = int(self.labels[i]) if 0 <= i < 256 else -1
        if j >= 0:
            self.edit_part(j)

    def edit_part(self, j):
        n = self.current()
        if n == 1:
            QMessageBox.information(self, APP_NAME, tr('La paleta 1 es la original: para cambiar colores crea una '
                                                       'nueva (➕ Nueva o 🎲 Nueva al azar).'))
            return
        self.sel_part = j
        c = self.ask_color(P.part_color(self.colors_of(n), self.counts, self.labels, j),
                           tr('Color de la parte {0}').format(j + 1))
        if c is None:
            self.fill_parts()
            self.redraw()
            return
        rec = self.recipe(n, create=True)
        rec.setdefault("parts", {})[str(j)] = c
        self.apply(n)
        self.refresh_after_edit()

    def reset_part(self, j):
        n = self.current()
        rec = self.recipe(n, create=True)
        (rec.get("parts") or {}).pop(str(j), None)
        self.apply(n)
        self.refresh_after_edit()

    def on_single(self, i):
        n = self.current()
        if n == 1:
            return
        c = self.grid.palette.colors[i][:3]
        rec = self.recipe(n, create=True)
        rec.setdefault("singles", {})[str(i)] = [int(v) for v in c]
        self.apply(n)
        self.refresh_after_edit()

    def randomize_current(self):
        n = self.current()
        if n == 1:
            return
        rec = self.recipe(n, create=True)
        rec["parts"] = P.random_parts(self.base1(), self.counts, self.labels)
        rec["singles"] = {}
        rec.pop("base", None)
        self.apply(n)
        self.refresh_after_edit()

    def reset_current(self):
        n = self.current()
        if n == 1:
            return
        rec = self.recipe(n, create=True)
        rec["parts"], rec["singles"] = {}, {}
        rec.pop("base", None)
        self.apply(n)
        self.refresh_after_edit()

    def refresh_after_edit(self):
        n = self.current()
        it = self.list.currentItem()
        if it is not None:
            it.setIcon(self.swatch_icon(self.colors_of(n)))
        self.show_current()

    def new_palette(self, how):
        ents = self.entries()
        free = [n for n in range(2, MAX_PALS + 1) if n not in ents]
        if not free:
            QMessageBox.information(self, APP_NAME, tr('Ya tiene las {0} paletas.').format(MAX_PALS))
            return
        n = free[0]
        pals = self.store().setdefault("pals", {})
        src = self.current()
        if how == "dup" and src != 1:
            old = self.recipe(src)
            rec = {"parts": dict((old or {}).get("parts") or {}), "singles": dict((old or {}).get("singles") or {})}
            if not old or old.get("base"):
                rec["base"] = (old or {}).get("base") or self.colors_of(src).tolist()
        elif how == "random":
            rec = {"parts": P.random_parts(self.base1(), self.counts, self.labels), "singles": {}}
        else:
            rec = {"parts": {}, "singles": {}}
        pals[str(n)] = rec
        self.apply(n)
        self.fill_list(select=n)

    def delete_palette(self):
        n = self.current()
        ents = self.entries()
        if n == 1 or n not in ents or ents[n][2] != "sff":
            return
        if QMessageBox.question(self, APP_NAME, tr('¿Borrar la paleta {0}?').format(n)) != \
                QMessageBox.StandardButton.Yes:
            return
        sff = self.project().sff
        i = sff.find_palette(1, n)
        if i is not None and i > 0:
            del sff.palettes[i]
            for s in sff.sprites:          # los índices de las paletas de después bajan uno
                b = s.base()
                if b.palidx == i:
                    b.palidx = 0
                elif b.palidx > i:
                    b.palidx -= 1
            sff.modified = True
        self.store().setdefault("pals", {}).pop(str(n), None)
        self.sm.mark()
        self.touched()
        self.fill_list(select=1)

    def on_k(self, k):
        """Otro número de partes: las paletas hechas aquí guardan sus colores tal cual (para no cambiarlas)."""
        st = self.store()
        for key, rec in (st.get("pals") or {}).items():
            n = int(key)
            if rec.get("parts") or rec.get("singles"):
                rec["base"] = self.colors_of(n).tolist()
                rec["parts"], rec["singles"] = {}, {}
        st["k"] = int(k)
        self.sm.mark()
        self.sel_part = -1
        self.analyze()
        self.fill_list()

    # ---------------------------------------------------------------- 32 bits → paleta
    def convert_true_color(self):
        p = self.project()
        sff = p.sff
        tc = P.true_color_sprites(sff)
        if not tc:
            return
        if QMessageBox.question(self, APP_NAME, tr(
                'Se van a pasar {0} sprites a la paleta del personaje (hasta 255 colores compartidos). Se ven '
                'casi igual y desde ahí se les pueden hacer colores alternativos. Las imágenes que pongas '
                'después también irán a la paleta.\n\nSe puede deshacer (Ctrl+Z en «Sprites»). ¿Seguir?').format(
                len(tc))) != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            counts = P.usage(sff)
            has8 = bool(counts.sum())
            pal, maps = P.to_shared_palette(tc, self.base1() if has8 else None, counts if has8 else None)
        finally:
            QApplication.restoreOverrideCursor()
        old_pix = {id(s): (s, s.pixels(), s.palidx) for s in tc}
        old_pals = [(x, x.colors.copy()) for x in sff.palettes]
        old_n = len(sff.palettes)
        ents = self.entries()
        old_acts = [(e[1], e[1].colors.copy()) for e in ents.values() if e[2] == "act" and e[1] is not None]
        new_slots = (counts == 0) if has8 else np.ones(256, bool)
        new_slots[0] = False
        others = {n: self.colors_of(n).copy() for n in ents if n != 1}
        if sff.find_palette(1, 1) is None:
            sff.palettes.append(Palette(1, 1, rgb_to_rgba(pal)))     # (se quita al deshacer)
        idx11 = P.char_index(sff)

        def redo():
            for s in tc:
                s.set_pixels(maps[id(s)])
                s.palidx = idx11
            self.write(1, pal)
            for n, rgb in others.items():       # en las otras paletas, los colores nuevos van igual que en la 1
                rgb = rgb.copy()
                rgb[new_slots] = pal[new_slots]
                self.write(n, rgb)
            self.sm.set_import_mode("char")

        def undo():
            for s, pix, pidx in old_pix.values():
                s.set_pixels(pix)
                s.palidx = pidx
            del sff.palettes[old_n:]
            for x, cols in old_pals:
                x.colors = cols.copy()
            for x, cols in old_acts:
                x.colors = cols.copy()
            self.touched()
        redo()
        self.sm.main.sprites.push(tr('Pasar sprites a la paleta del personaje'), redo, undo, refresh_list=True)
        self.sm.mark()
        self._key = None
        self.bind()
        self.sm.main.status.setText(tr('✅ {0} sprites pasados a la paleta del personaje.').format(len(tc)))
