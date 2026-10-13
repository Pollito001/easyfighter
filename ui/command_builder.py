"""Creador de comandos: tocas las flechas en orden y queda guardado en la lista de comandos."""
import uuid

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QVBoxLayout,
)

from i18n import tr
from ui.common import APP_NAME

# flecha → dirección de MUGEN (mirando a la derecha: → es adelante)
PAD = [("↖", "UB"), ("↑", "U"), ("↗", "UF"),
       ("←", "B"), (None, None), ("→", "F"),
       ("↙", "DB"), ("↓", "D"), ("↘", "DF")]
ARROW = {d: a for a, d in PAD if d}


# mantener una flecha mientras aprietas el botón (o sea, caminando): "/F, x"
HOLDS = [(None, 'No'), ("F", '→ Caminando hacia adelante'), ("B", '← Caminando hacia atrás')]


def build(dirs, charge=False, hold=None):
    """(texto del comando con {b}, etiqueta) a partir de las direcciones.
    hold: "F"/"B" → hay que estar aguantando esa flecha (caminando) cuando aprietas el botón."""
    parts, label = [], ""
    if dirs:
        if charge:
            first = ("~30$" if len(dirs[0]) == 1 else "~30") + dirs[0]
        else:
            first = "~" + dirs[0]
        parts = [first] + dirs[1:]
        label = ("[" + tr('cargar') + " " + ARROW[dirs[0]] + "] " if charge else ARROW[dirs[0]]) + \
            "".join(ARROW[d] for d in dirs[1:])
    if hold:
        parts.append("/" + hold)
        label = (label.rstrip() + " " if label else "") + "[" + tr('caminando') + " " + ARROW[hold] + "]"
    cmd = ", ".join(parts + ["{b}"])
    return cmd, label + " + " + tr('botón')


class CommandBuilder(QDialog):
    def __init__(self, parent, saved):
        """saved: lista de comandos guardados [{"key", "label", "cmd"}] (se edita en el lugar)."""
        super().__init__(parent)
        self.saved = saved
        self.dirs = []
        self.result_motion = None
        self.setWindowTitle(tr('🎮 Crear comando'))
        self.resize(560, 560)
        lay = QVBoxLayout(self)
        intro = QLabel(tr('Toca las flechas en el orden del comando (como si el personaje mirara a la '
                                'derecha). El botón (puño o patada) se pone solo al final. Para un golpe que sale caminando, '
                                'escoge «Apretar el botón mientras caminas».'))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.show_lbl = QLabel()
        f = QFont()
        f.setPointSize(26)
        f.setBold(True)
        self.show_lbl.setFont(f)
        self.show_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.show_lbl.setMinimumHeight(70)
        self.show_lbl.setObjectName("CmdShow")
        lay.addWidget(self.show_lbl)
        mid = QHBoxLayout()
        pad = QGridLayout()
        pad.setSpacing(6)
        for i, (a, d) in enumerate(PAD):
            if a is None:
                lab = QLabel("●")
                lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pad.addWidget(lab, i // 3, i % 3)
                continue
            b = QPushButton(a)
            b.setFixedSize(64, 64)
            b.setStyleSheet("font-size: 24pt; padding: 0px;")
            b.clicked.connect(lambda _c, d=d: self.add(d))
            pad.addWidget(b, i // 3, i % 3)
        mid.addLayout(pad)
        side = QVBoxLayout()
        self.charge = QCheckBox(tr('Cargar la primera flecha\n(mantenerla un momento)'))
        self.charge.toggled.connect(self.refresh)
        side.addWidget(self.charge)
        side.addWidget(QLabel(tr('Apretar el botón mientras caminas:')))
        self.hold = QComboBox()
        for d, t in HOLDS:
            self.hold.addItem(tr(t), d)
        self.hold.setToolTip(tr('El botón sale solo si estás aguantando esa flecha (caminando) cuando lo '
                                'aprietas. Puedes usarlo solo (sin tocar flechas) o al final de las flechas.'))
        self.hold.currentIndexChanged.connect(self.refresh)
        side.addWidget(self.hold)
        back = QPushButton(tr('⌫ Borrar la última'))
        back.clicked.connect(self.undo)
        clear = QPushButton(tr('🗑 Empezar de nuevo'))
        clear.clicked.connect(self.clear)
        side.addWidget(back)
        side.addWidget(clear)
        side.addStretch(1)
        mid.addLayout(side)
        lay.addLayout(mid)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Nombre (opcional):')))
        self.name = QLineEdit()
        row.addWidget(self.name, 1)
        lay.addLayout(row)
        save = QPushButton(tr('💾 Guardar en la lista y usarlo'))
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        lay.addWidget(save)
        lay.addWidget(QLabel(tr('Comandos que ya creaste:')))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.use_saved)
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        use = QPushButton(tr('✔ Usar el elegido'))
        use.clicked.connect(lambda: self.use_saved(self.list.currentItem()))
        rm = QPushButton(tr('🗑 Quitar de la lista'))
        rm.clicked.connect(self.remove_saved)
        close = QPushButton(tr('Cerrar'))
        close.clicked.connect(self.reject)
        row.addWidget(use)
        row.addWidget(rm)
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)
        self.fill()
        self.refresh()

    def fill(self):
        self.list.clear()
        for m in self.saved:
            it = QListWidgetItem(m.get("label", "?"))
            it.setData(Qt.ItemDataRole.UserRole, m.get("key"))
            self.list.addItem(it)

    def add(self, d):
        if len(self.dirs) < 12:
            self.dirs.append(d)
        self.refresh()

    def undo(self):
        if self.dirs:
            self.dirs.pop()
        self.refresh()

    def clear(self):
        self.dirs = []
        self.refresh()

    def refresh(self, *_a):
        hold = self.hold.currentData()
        self.charge.setEnabled(bool(self.dirs))
        if not self.dirs and not hold:
            self.show_lbl.setText(tr('(toca las flechas)'))
            return
        _cmd, label = build(self.dirs, self.charge.isChecked() and bool(self.dirs), hold)
        self.show_lbl.setText(label)

    def save(self):
        hold = self.hold.currentData()
        if not self.dirs and not hold:
            QMessageBox.information(self, APP_NAME, tr('Toca al menos una flecha o escoge caminar.'))
            return
        cmd, label = build(self.dirs, self.charge.isChecked() and bool(self.dirs), hold)
        name = self.name.text().strip()
        if name:
            label = f"{name}: {label}"
        same = next((m for m in self.saved if m.get("cmd") == cmd), None)
        if same is None:
            same = {"key": "C" + uuid.uuid4().hex[:8], "label": label, "cmd": cmd}
            self.saved.append(same)
        elif name:
            same["label"] = label
        self.result_motion = same
        self.accept()

    def use_saved(self, it):
        if it is None:
            return
        key = it.data(Qt.ItemDataRole.UserRole)
        self.result_motion = next((m for m in self.saved if m.get("key") == key), None)
        if self.result_motion:
            self.accept()

    def remove_saved(self):
        it = self.list.currentItem()
        if it is None:
            return
        key = it.data(Qt.ItemDataRole.UserRole)
        self.saved[:] = [m for m in self.saved if m.get("key") != key]
        self.fill()
