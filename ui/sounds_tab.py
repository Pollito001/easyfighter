"""Pestaña Sonidos: escuchar, agregar, exportar y numerar los sonidos (.snd)."""
import re
import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QUndoStack
from PyQt6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.snd import Sound
from i18n import tr
from ui.common import APP_NAME, audio_filter
from ui.undo import FnCommand

NAME_RE = re.compile(r"(\d+)\s*[-_, ]\s*(\d+)\D*$")


class SoundsTab(QWidget):
    modifiedChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.undo = QUndoStack(self)
        self.undo.cleanChanged.connect(self.modifiedChanged)
        self.player = None
        self._tmp = Path(tempfile.gettempdir()) / "ikemen_chareditor_preview.wav"
        self._block = False
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr('Filtrar: grupo o «grupo,número»'))
        self.filter.textChanged.connect(lambda _t: self.fill())
        top.addWidget(self.filter, 1)
        for txt, fn, key in ((tr('▶ Escuchar'), self.play, "Space"), (tr('⏹'), self.stop, None),
                             (tr('➕ Agregar sonidos…'), self.add, "Ins"), (tr('🔁 Reemplazar…'), self.replace, None),
                             (tr('💾 Exportar…'), self.export, None), (tr('📤 Exportar todos…'), self.export_all, None),
                             (tr('🗑 Borrar'), self.delete, "Del")):
            keep = txt.startswith(("▶", "➕"))
            b = QPushButton(txt if keep else txt.split(" ", 1)[0])
            if not keep:
                b.setToolTip(txt)
            b.clicked.connect(fn)
            if key:
                b.setShortcut(QKeySequence(key))
            top.addWidget(b)
        for txt, fn, key in ((tr('↶ Deshacer'), self.undo.undo, QKeySequence.StandardKey.Undo),
                             (tr('↷ Rehacer'), self.undo.redo, QKeySequence.StandardKey.Redo)):
            b = QPushButton(txt.split(" ", 1)[0])
            b.setToolTip(txt)
            b.clicked.connect(fn)
            b.setEnabled(False)
            (self.undo.canUndoChanged if key == QKeySequence.StandardKey.Undo else self.undo.canRedoChanged).connect(b.setEnabled)
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr('Grupo'), tr('Número'), tr('Duración'), tr('Formato')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(lambda _i: self.play())
        self.table.currentCellChanged.connect(lambda r, *_: self.show_sound(r))
        lay.addWidget(self.table, 1)
        g = QGroupBox(tr('Sonido'))
        f = QFormLayout(g)
        self.group = QSpinBox()
        self.group.setRange(0, 2147483647)
        self.number = QSpinBox()
        self.number.setRange(0, 2147483647)
        self.group.editingFinished.connect(self.rename)
        self.number.editingFinished.connect(self.rename)
        f.addRow(tr('Grupo:'), self.group)
        f.addRow(tr('Número:'), self.number)
        hint = QLabel(tr('En el código: PlaySnd con value = grupo, número usa estos sonidos; con «F» delante '
                         '(p. ej. F5,0) usa los comunes del juego. En HitDef es al revés: hitsound = S5,0 usa los de '
                         'aquí. Dentro del .snd los sonidos son WAV (es lo único que IKEMEN GO toca ahí): si agregas OGG, MP3, '
                         'FLAC… se convierten solos a WAV PCM de 16 bits.'))
        hint.setWordWrap(True)
        f.addRow(hint)
        lay.addWidget(g)
        self.rows = []

    def snd(self):
        p = self.main.project
        return p.snd if p else None

    def is_modified(self):
        p = self.main.project
        return bool(p and p.snd_loaded() and (p.snd.modified or not self.undo.isClean()))

    def load(self):
        self.undo.clear()
        self.fill()

    def fill(self, select=None):
        snd = self.snd()
        flt = self.filter.text().replace(" ", "")
        self.rows = []
        for s in snd.sounds if snd else []:
            if flt:
                g, _, n = flt.partition(",")
                if g and str(s.group) != g and not (not n and str(s.group).startswith(g)):
                    continue
                if n and str(s.number) != n:
                    continue
            self.rows.append(s)
        self._block = True
        self.table.setRowCount(len(self.rows))
        sel = 0
        for r, s in enumerate(self.rows):
            info = s.info()
            vals = [s.group, s.number, f"{info[0]:.2f} s" if info else "?",
                    f"{info[1]} Hz · {tr('estéreo') if info[2] == 2 else tr('mono')} · {info[3]} bits" if info else tr('no es WAV')]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))
            if s is select:
                sel = r
        self._block = False
        if self.rows:
            self.table.selectRow(sel)
            self.show_sound(sel)

    def current(self):
        r = self.table.currentRow()
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def show_sound(self, r):
        if self._block:
            return
        s = self.rows[r] if 0 <= r < len(self.rows) else None
        self._block = True
        self.group.setValue(s.group if s else 0)
        self.number.setValue(s.number if s else 0)
        self._block = False

    def push(self, text, redo, undo, select=None):
        self.undo.push(FnCommand(text, redo, undo, after=lambda: (self.fill(select), self.modifiedChanged.emit())))

    # ---- acciones
    def play(self):
        s = self.current()
        if not s:
            return
        try:
            from PyQt6.QtMultimedia import QSoundEffect
        except ImportError:
            QMessageBox.information(self, APP_NAME, tr('Tu instalación de PyQt6 no trae sonido (QtMultimedia).'))
            return
        self.stop()
        self._tmp.write_bytes(s.data)
        self.player = QSoundEffect(self)
        self.player.setSource(QUrl.fromLocalFile(str(self._tmp)))
        self.player.play()

    def stop(self):
        if self.player is not None:
            self.player.stop()

    def _read_wavs(self, files):
        """Los sonidos elegidos como WAV (los OGG, MP3, FLAC… se convierten: el .snd solo lleva WAV)."""
        from ui.common import read_audio
        out = []
        for f in files:
            data = read_audio(self, f)
            if data is not None:
                out.append((f, data))
        return out

    def add(self):
        p = self.main.project
        if not p:
            return
        files, _ = QFileDialog.getOpenFileNames(self, tr('Agregar sonidos'), str(p.folder), audio_filter())
        if not files:
            return
        snd = self.snd()
        cur = self.current()
        g = cur.group if cur else 0
        new = []
        for f, data in self._read_wavs(files):
            m = NAME_RE.search(Path(f).stem)
            if m:
                gg, nn = int(m.group(1)), int(m.group(2))
            else:
                gg, nn = g, 0
                while snd.find(gg, nn) or any(x.key == (gg, nn) for x in new):
                    nn += 1
            new.append(Sound(gg, nn, data))
        if not new:
            return
        before = list(snd.sounds)
        keys = {s.key for s in new}
        after = [s for s in before if s.key not in keys] + new
        self.push(tr('Agregar sonidos'), lambda: snd.sounds.__setitem__(slice(None), after),
                  lambda: snd.sounds.__setitem__(slice(None), before), new[0])

    def replace(self):
        s = self.current()
        if not s:
            return
        f, _ = QFileDialog.getOpenFileName(self, tr('Reemplazar sonido'), str(self.main.project.folder), audio_filter())
        if not f:
            return
        got = self._read_wavs([f])
        if not got:
            return
        new, old = got[0][1], s.data
        self.push(tr('Reemplazar sonido'), lambda: setattr(s, "data", new), lambda: setattr(s, "data", old), s)

    def export(self):
        s = self.current()
        if not s:
            return
        f, _ = QFileDialog.getSaveFileName(self, tr('Exportar sonido'),
                                           str(self.main.project.folder / f"{s.group}-{s.number}.wav"), "WAV (*.wav)")
        if f:
            Path(f).write_bytes(s.data)

    def export_all(self):
        snd = self.snd()
        if not snd or not snd.sounds:
            return
        folder = QFileDialog.getExistingDirectory(self, tr('Carpeta para exportar'), str(self.main.project.folder))
        if not folder:
            return
        for s in snd.sounds:
            (Path(folder) / f"{s.group}-{s.number}.wav").write_bytes(s.data)
        QMessageBox.information(self, APP_NAME, tr('✅ {0} sonidos exportados.').format(len(snd.sounds)))

    def delete(self):
        s = self.current()
        if not s:
            return
        snd = self.snd()
        before = list(snd.sounds)
        self.push(tr('Borrar sonido'), lambda: snd.sounds.remove(s) if s in snd.sounds else None,
                  lambda: snd.sounds.__setitem__(slice(None), before))

    def rename(self):
        s = self.current()
        if self._block or not s:
            return
        g, n = self.group.value(), self.number.value()
        if (g, n) == s.key:
            return
        other = self.snd().find(g, n)
        if other is not None and other is not s:
            QMessageBox.warning(self, APP_NAME, tr('Ya hay un sonido {0},{1}.').format(g, n))
            self.show_sound(self.table.currentRow())
            return
        og, on = s.group, s.number
        self.push(tr('Renumerar sonido'), lambda: (setattr(s, "group", g), setattr(s, "number", n)),
                  lambda: (setattr(s, "group", og), setattr(s, "number", on)), s)

    def save(self):
        p = self.main.project
        if not p or not p.snd_loaded():
            return True
        try:
            p.backup(p.snd.path)
            p.snd.save()
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, tr('No pude guardar los sonidos: {0}').format(e))
            return False
        if not p.file_value("sound"):
            p.defs.set("Files", "sound", p.snd.path.name)
            p.defs_dirty = True
        self.undo.setClean()
        return True
