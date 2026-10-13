"""Pestaña Datos: lo del .def (nombre, autor, archivos, paletas…)."""
import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog, QFormLayout, QGridLayout, QGroupBox, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)

from core.textio import ci_find
from i18n import tr

INFO = [("name", 'Nombre interno:'), ("displayname", 'Nombre que se muestra:'), ("author", 'Autor:'),
        ("versiondate", 'Fecha de versión:'), ("mugenversion", 'Versión de MUGEN:'),
        ("ikemenversion", 'Versión de IKEMEN:'), ("localcoord", 'Resolución (localcoord):'),
        ("pal.defaults", 'Paletas por defecto:')]
FILES = [("cmd", 'Comandos (.cmd):'), ("cns", 'Constantes (.cns):'), ("st", 'Estados (st):'),
         ("st1", 'Estados 2 (st1):'), ("st2", 'Estados 3 (st2):'), ("stcommon", 'Estados comunes:'),
         ("sprite", 'Sprites (.sff):'), ("anim", 'Animaciones (.air):'), ("sound", 'Sonidos (.snd):'),
         ("ai", 'IA (opcional):'), ("movelist", 'Lista de movimientos:')]
ARCADE = [("intro.storyboard", 'Intro (storyboard):'), ("ending.storyboard", 'Final (storyboard):')]
FILTERS = {"sprite": "SFF (*.sff)", "anim": "AIR (*.air)", "sound": "SND (*.snd)"}


class DefTab(QWidget):
    modifiedChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.modified = False
        self._block = False
        self.edits = {}
        lay = QVBoxLayout(self)
        self.sub = QTabWidget()
        lay.addWidget(self.sub)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_w = QWidget()
        scroll.setWidget(form_w)
        fl = QVBoxLayout(form_w)
        self.sub.addTab(scroll, tr('Formulario'))
        self.text = QPlainTextEdit()
        self.text.setFont(QFont("monospace"))
        self.text.textChanged.connect(self.on_text_changed)
        self.sub.addTab(self.text, tr('Texto del .def'))
        self.sub.currentChanged.connect(self.on_sub)
        self._text_dirty = False

        g = QGroupBox(tr('Información'))
        f = QFormLayout(g)
        for key, label in INFO:
            e = QLineEdit()
            e.textEdited.connect(lambda _t, key=key: self.on_edit("Info", key))
            self.edits[("Info", key)] = e
            f.addRow(tr(label), e)
        hint = QLabel(tr('Resolución: 320,240 para personajes de MUGEN clásico; 640,480 o 1280,720 para HD. '
                         'Paletas por defecto: los números de paleta en orden de preferencia, p. ej. 1,2,3,4.'))
        hint.setWordWrap(True)
        f.addRow(hint)
        fl.addWidget(g)

        g = QGroupBox(tr('Archivos'))
        grid = QGridLayout(g)
        self.status = {}
        rows = FILES + [(f"pal{n}", tr('Paleta {0}:').format(n)) for n in range(1, 13)]
        for r, (key, label) in enumerate(rows):
            e = QLineEdit()
            e.textEdited.connect(lambda _t, key=key: self.on_edit("Files", key))
            self.edits[("Files", key)] = e
            b = QPushButton("…")
            b.setFixedWidth(32)
            b.clicked.connect(lambda _c, key=key: self.browse(key))
            st = QLabel()
            self.status[key] = st
            grid.addWidget(QLabel(tr(label) if not key.startswith("pal") else label), r, 0)
            grid.addWidget(e, r, 1)
            grid.addWidget(b, r, 2)
            grid.addWidget(st, r, 3)
        fl.addWidget(g)

        g = QGroupBox(tr('Arcade'))
        f = QFormLayout(g)
        for key, label in ARCADE:
            e = QLineEdit()
            e.textEdited.connect(lambda _t, key=key: self.on_edit("Arcade", key))
            self.edits[("Arcade", key)] = e
            f.addRow(tr(label), e)
        fl.addWidget(g)
        fl.addStretch(1)

    def load(self):
        self._block = True
        p = self.main.project
        for (sec, key), e in self.edits.items():
            e.setText(p.defs.get(sec, key, "") if p else "")
        self.text.setPlainText(p.defs.text() if p else "")
        self._text_dirty = False
        self._block = False
        self.modified = False
        self.check_files()

    def check_files(self):
        p = self.main.project
        for key, st in self.status.items():
            v = self.edits[("Files", key)].text().strip()
            if not v:
                st.setText("")
            elif key == "stcommon" and not (p and ci_find(p.folder, v)):
                st.setText(tr('(del juego)'))
            elif p and ci_find(p.folder, v):
                st.setText("✅")
            elif key in ("ai", "movelist"):
                st.setText(tr('(opcional, no está)'))
            else:
                st.setText("❌ " + tr('no existe'))

    def on_edit(self, sec, key):
        if self._block:
            return
        p = self.main.project
        v = self.edits[(sec, key)].text()
        quote = sec == "Info" and key in ("name", "displayname", "author")
        if v.strip():
            p.defs.set(sec, key, v.strip().strip('"'), quote=quote)
        else:
            p.defs.remove(sec, key)
        if key.startswith("pal"):
            p.acts = None
        self.set_modified()
        self.check_files()

    def browse(self, key):
        p = self.main.project
        if not p:
            return
        flt = FILTERS.get(key, "ACT (*.act)" if key.startswith("pal") else tr('Todos (*)'))
        path, _ = QFileDialog.getOpenFileName(self, key, str(p.folder), flt)
        if not path:
            return
        try:
            rel = os.path.relpath(path, p.folder).replace(os.sep, "/")
        except ValueError:
            rel = path
        self.edits[("Files", key)].setText(rel)
        self.on_edit("Files", key)

    def on_text_changed(self):
        if not self._block:
            self._text_dirty = True
            self.set_modified()

    def on_sub(self, i):
        p = self.main.project
        if not p:
            return
        if i == 1:
            self._block = True
            self.text.setPlainText(p.defs.text())
            self._block = False
            self._text_dirty = False
        elif self._text_dirty:
            self.apply_text()
            self.load_form_only()

    def apply_text(self):
        p = self.main.project
        p.defs.lines = self.text.toPlainText().split("\n")
        p.acts = None
        self._text_dirty = False

    def load_form_only(self):
        mod = self.modified
        self.load()
        self.modified = mod

    def set_modified(self):
        self.modified = True
        self.modifiedChanged.emit()

    def is_modified(self):
        return self.modified

    def save(self):
        p = self.main.project
        if not p:
            return True
        if self.sub.currentIndex() == 1 and self._text_dirty:
            self.apply_text()
        p.backup(p.def_path)
        p.defs.save()
        p.defs_dirty = False
        self.modified = False
        self.modifiedChanged.emit()
        return True
