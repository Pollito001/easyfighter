"""«🎯 Alinear todas con la de parado»: alinea los cuadros de todas las casillas del modo simple de una vez,
con vista previa (antes / después) y la de parado de guía."""
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import autoalign as AA
from core import simple_gen as sg
from i18n import tr
from ui import theme


def collect(sm):
    """Casillas con cuadros: [(tipo, clave, título, cuadros, modo)] — parado primero."""
    cfg = sm.cfg
    rows = []
    for _sec, _t, lst in sg.ANIM_SECTIONS:
        for key, title, _d, _g, _f in lst:
            fr = sg._frames((cfg.get("anims") or {}).get(key) or {})
            if fr:
                rows.append(("anim", key, tr(title), fr, AA.mode_for_slot("anim", key)))
    rows.sort(key=lambda r: r[1] != "idle")
    names = dict((p, t) for p, t, _n in sg.POSITIONS)
    for key in sg.NORMAL_KEYS:
        fr = sg._frames(cfg["normals"].get(key) or {})
        if fr:
            pos, b, *_r = sg.normal_info(key)
            rows.append(("normal", key, f"{tr(names[pos])}: {tr(sg.NORMAL_NAMES[b])} ({b})", fr,
                         AA.mode_for_slot("normal", key)))
    fr = sg._frames(cfg.get("throw") or {})
    if fr:
        rows.append(("throw", "throw", tr('Agarre'), fr, "ground"))
    for i, sp in enumerate(cfg.get("specials", [])):
        fr = sg._frames(sp)
        if fr and sp.get("type") != "converted":
            rows.append(("special", i, sp.get("name") or tr('Especial'), fr, AA.mode_for_slot("special", sp=sp)))
    return rows


class Preview(QWidget):
    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg
        self.setMinimumSize(QSize(420, 380))
        self.tick = 0

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.CANVAS))
        dlg = self.dlg
        row = dlg.current_row()
        o = QPointF(self.width() / 2, self.height() - 40)
        p.setPen(QPen(QColor(255, 107, 53, 170), 1))
        p.drawLine(0, int(o.y()), self.width(), int(o.y()))
        p.setPen(QPen(QColor(255, 255, 255, 50), 1, Qt.PenStyle.DashLine))
        p.drawLine(int(o.x()), 0, int(o.x()), self.height())
        if row is None:
            p.end()
            return
        after = dlg.after.isChecked()
        keys = row[3]
        z = dlg.zoom
        # guía: la de parado
        ref = dlg.ref
        if ref is not None and dlg.ghost.isChecked():
            self.draw(p, ref, dlg.axis(ref, True), o, z, 0.3)
        i = (self.tick // 8) % len(keys) if dlg.playing else dlg.frame % len(keys)
        k = tuple(keys[i])
        self.draw(p, k, dlg.axis(k, after), o, z, 1.0)
        p.setPen(QColor(theme.MUTED))
        p.drawText(10, 20, (tr('Después') if after else tr('Antes')) + f" · {i + 1}/{len(keys)}")
        p.end()

    def draw(self, p, key, axis, o, z, op):
        pm = self.dlg.sm.pixmap(*key)
        if pm is None or axis is None:
            return
        ax, ay = axis
        p.setOpacity(op)
        p.drawPixmap(QRectF(o.x() - ax * z, o.y() - ay * z, pm.width() * z, pm.height() * z), pm, QRectF(pm.rect()))
        p.setOpacity(1.0)


class AlignAllDialog(QDialog):
    def __init__(self, sm):
        super().__init__(sm.main)
        self.sm = sm
        self.setWindowTitle(tr('🎯 Alinear todas con la de parado'))
        self.resize(1100, 680)
        self.rows = collect(sm)
        self.ref = sm.reference_frame()
        self.result = {}
        self.frame = 0
        self.playing = True
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel(tr(
            'El editor reconoce el cuerpo y los pies de cada cuadro y alinea todas las animaciones con la de parado '
            '(su primer cuadro no se mueve). Quita el tick de las que no quieras tocar y cambia el modo si alguna no '
            'quedó bien. Puedes deshacer con Ctrl+Z.')))
        left.itemAt(0).widget().setWordWrap(True)
        self.table = QTableWidget(len(self.rows), 3)
        self.table.setHorizontalHeaderLabels([tr('Animación'), tr('Cómo alinearla'), tr('Cuadros')])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.modes = []
        for r, (kind, key, title, keys, mode) in enumerate(self.rows):
            it = QTableWidgetItem(title)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(r, 0, it)
            c = QComboBox()
            for i_, (k, t) in enumerate(AA.MODES):
                c.addItem(tr(t), k)
                c.setItemData(i_, tr(AA.MODE_TIPS[k]), Qt.ItemDataRole.ToolTipRole)
            c.setCurrentIndex(max(0, c.findData(mode)))
            c.currentIndexChanged.connect(self.compute)
            self.table.setCellWidget(r, 1, c)
            self.modes.append(c)
            n = QTableWidgetItem(str(len(keys)))
            n.setFlags(n.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 2, n)
        self.table.itemChanged.connect(lambda _it: self.compute())
        self.table.currentCellChanged.connect(lambda *_a: self.preview.update())
        left.addWidget(self.table, 1)
        lay.addLayout(left, 1)

        right = QVBoxLayout()
        self.preview = Preview(self)
        right.addWidget(self.preview, 1)
        row = QHBoxLayout()
        self.after = QCheckBox(tr('Ver cómo queda'))
        self.after.setChecked(True)
        self.after.setToolTip(tr('Quítale el tick para ver cómo estaba antes.'))
        self.after.toggled.connect(lambda _c: self.preview.update())
        self.ghost = QCheckBox(tr('Parado de guía'))
        self.ghost.setChecked(True)
        self.ghost.toggled.connect(lambda _c: self.preview.update())
        row.addWidget(self.after)
        row.addWidget(self.ghost)
        row.addStretch(1)
        right.addLayout(row)
        row = QHBoxLayout()
        self.play = QPushButton(tr('⏸ Parar'))
        self.play.clicked.connect(self.toggle_play)
        prev_b = QPushButton("◀")
        prev_b.clicked.connect(lambda: self.step(-1))
        next_b = QPushButton("▶")
        next_b.clicked.connect(lambda: self.step(1))
        row.addWidget(self.play)
        row.addWidget(prev_b)
        row.addWidget(next_b)
        row.addStretch(1)
        ok = QPushButton(tr('✔ Alinear'))
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        cancel = QPushButton(tr('Cancelar'))
        cancel.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        right.addLayout(row)
        lay.addLayout(right, 1)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.on_tick)
        self.timer.start()
        tall = 60
        for r in self.rows:
            for k in r[3]:
                s = sm.sprite(*k)
                if s is not None:
                    tall = max(tall, s.size()[1])
        self.zoom = max(0.4, min(3.0, 320 / tall))
        self.compute()
        if self.rows:
            self.table.selectRow(0)

    # ---- datos
    def current_row(self):
        r = self.table.currentRow()
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def axis(self, key, after=True):
        key = tuple(key)
        if after and key in self.result:
            return self.result[key]
        s = self.sm.sprite(*key)
        return (s.x, s.y) if s is not None else None

    def checked(self, r):
        it = self.table.item(r, 0)
        return it is not None and it.checkState() == Qt.CheckState.Checked

    def compute(self, *_a):
        al = AA.Aligner(lambda k: self.sm.sprite(*k))
        ref = self.ref
        if ref is not None:
            s = self.sm.sprite(*ref)
            if s is not None:
                al.done[tuple(ref)] = (s.x, s.y)     # el primer cuadro de parado no se mueve
            al.set_reference(ref)
        res = {}
        for r, (_kind, _key, _t, keys, _m) in enumerate(self.rows):
            if not self.checked(r):
                continue
            res.update(al.align(keys, self.modes[r].currentData()))
        self.result = res
        self.preview.update()

    def changes(self):
        out = {}
        for k, v in self.result.items():
            s = self.sm.sprite(*k)
            if s is not None and (s.x, s.y) != tuple(v):
                out[k] = tuple(v)
        return out

    def touched(self):
        """Casillas marcadas (para rehacer sus animaciones después)."""
        return [(kind, key) for r, (kind, key, _t, _k, _m) in enumerate(self.rows) if self.checked(r)]

    # ---- vista previa
    def toggle_play(self):
        self.playing = not self.playing
        self.play.setText(tr('⏸ Parar') if self.playing else tr('▶ Ver animado'))
        self.preview.update()

    def step(self, d):
        self.playing = False
        self.play.setText(tr('▶ Ver animado'))
        self.frame += d
        self.preview.update()

    def on_tick(self):
        if self.playing and self.isVisible():
            self.preview.tick += 1
            self.preview.update()
