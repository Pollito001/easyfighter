"""Probar el personaje en IKEMEN GO (pelea rápida con las opciones de línea de comandos del juego)."""
import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QWidget,
)

from i18n import tr
from ui.common import APP_NAME
from ui.mainwindow import load_settings, save_settings

EXE_NAMES = ["Ikemen_GO.exe", "Ikemen_GO_Linux", "Ikemen_GO", "Ikemen_GO_MacOS", "Ikemen_GO_Mac"]


def find_exe(folder):
    folder = Path(folder)
    for n in EXE_NAMES:
        p = folder / n
        if p.is_file():
            return p
    app = folder / "Ikemen_GO.app" / "Contents" / "MacOS"
    if app.is_dir():
        for p in app.iterdir():
            if p.is_file():
                return p
    return None


def guess_ikemen(char_folder):
    """La carpeta de IKEMEN GO: la que contiene al personaje (…/chars/<personaje>) o la última usada."""
    p = Path(char_folder).resolve()
    for parent in [p] + list(p.parents):
        if find_exe(parent):
            return parent
    last = load_settings().get("ikemen_dir")
    if last and find_exe(last):
        return Path(last)
    return None


def char_arg(ikemen, def_path):
    """Nombre del personaje para -p1: relativo a chars/ si está dentro, si no la ruta completa."""
    chars = (Path(ikemen) / "chars").resolve()
    d = Path(def_path).resolve()
    try:
        rel = d.relative_to(chars)
        if d.parent.name.lower() == d.stem.lower() and len(rel.parts) == 2:
            return d.parent.name
        return rel.as_posix()
    except ValueError:
        return str(d)


class TestDialog(QDialog):
    def __init__(self, parent, project):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr('Probar en IKEMEN GO'))
        self.setMinimumWidth(560)
        s = load_settings()
        form = QFormLayout(self)
        row = QHBoxLayout()
        ik = guess_ikemen(project.folder)
        self.ik = QLineEdit(str(ik) if ik else s.get("ikemen_dir", ""))
        b = QPushButton("…")
        b.clicked.connect(self.browse)
        row.addWidget(self.ik, 1)
        row.addWidget(b)
        w = QWidget()
        w.setLayout(row)
        form.addRow(tr('Carpeta de IKEMEN GO:'), w)
        self.opp = QComboBox()
        self.opp.setEditable(True)
        self.stage = QComboBox()
        self.stage.setEditable(True)
        form.addRow(tr('Rival:'), self.opp)
        form.addRow(tr('Escenario:'), self.stage)
        self.ai = QSpinBox()
        self.ai.setRange(0, 8)
        self.ai.setValue(int(s.get("test_ai", 4)))
        self.ai.setSpecialValueText(tr('nadie (quieto)'))
        form.addRow(tr('Nivel de la CPU del rival:'), self.ai)
        self.color = QSpinBox()
        self.color.setRange(1, 12)
        form.addRow(tr('Paleta de tu personaje:'), self.color)
        self.notime = QCheckBox(tr('Sin límite de tiempo'))
        self.notime.setChecked(s.get("test_notime", True))
        self.power = QCheckBox(tr('Barra de poder siempre llena'))
        self.power.setChecked(s.get("test_power", False))
        self.nodie = QCheckBox(tr('Nadie se muere (la vida se rellena sola, como en el modo entrenamiento)'))
        self.nodie.setToolTip(tr('Cuando nadie le está pegando a un personaje, su vida vuelve a llenarse, y nadie '
                                 'cae KO. También se rellena el poder si no lo usa.'))
        self.nodie.setChecked(s.get("test_nodie", False))
        self.windowed = QCheckBox(tr('En ventana'))
        self.windowed.setChecked(s.get("test_windowed", True))
        for c in (self.notime, self.power, self.nodie, self.windowed):
            form.addRow(c)
        hint = QLabel(tr('Se abre una pelea rápida con tu personaje como jugador 1. El registro del juego se '
                         'guarda en «save/editor_test.log» de IKEMEN.'))
        hint.setWordWrap(True)
        form.addRow(hint)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText(tr('▶ Pelear'))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.ik.textChanged.connect(lambda _t: self.fill_lists())
        self.fill_lists()

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, tr('Carpeta de IKEMEN GO'), self.ik.text())
        if d:
            self.ik.setText(d)

    def fill_lists(self):
        ik = Path(self.ik.text())
        s = load_settings()
        self.opp.clear()
        self.opp.addItem(tr('(el mismo personaje)'), "")
        chars = ik / "chars"
        if chars.is_dir():
            for d in sorted(chars.iterdir(), key=lambda p: p.name.lower()):
                if d.is_dir() and any(d.glob("*.def")):
                    self.opp.addItem(d.name, d.name)
        i = self.opp.findData(s.get("test_opp", ""))
        self.opp.setCurrentIndex(max(0, i))
        self.stage.clear()
        stages = ik / "stages"
        if stages.is_dir():
            for f in sorted(stages.glob("*.def"), key=lambda p: p.name.lower()):
                self.stage.addItem(f"stages/{f.name}", f"stages/{f.name}")
        i = self.stage.findData(s.get("test_stage", "stages/kfm.def"))
        self.stage.setCurrentIndex(max(0, i))

    def args(self):
        ik = Path(self.ik.text())
        me = char_arg(ik, self.project.def_path)
        opp = self.opp.currentData() if self.opp.currentIndex() >= 0 and self.opp.currentText() == self.opp.itemText(self.opp.currentIndex()) else self.opp.currentText()
        opp = opp or me
        a = ["-p1", me, "-p2", opp, "-p1.color", str(self.color.value())]
        if self.ai.value() > 0:
            a += ["-p2.ai", str(self.ai.value())]
        st = self.stage.currentData() or self.stage.currentText()
        if st:
            a += ["-s", st]
        if self.notime.isChecked():
            a += ["-time", "-1"]
        if self.power.isChecked():
            a += ["-maxpowermode"]
        if self.nodie.isChecked():
            # -loadmotif: así IKEMEN carga los módulos (external/mods) antes de empezar la pelea
            a += ["-chareditor_nodie", "1", "-loadmotif"]
        if self.windowed.isChecked():
            a += ["-windowed"]
        return a


MOD_NAME = "chareditor_test.lua"
MOD_CODE = """-- IKEMEN GO Character Editor: modo de prueba.
-- Solo hace algo si el juego se abre desde el editor con «Nadie se muere» (bandera -chareditor_nodie):
-- la pelea va en modo entrenamiento (la vida se rellena sola y nadie cae KO). Se puede borrar sin problema.
if getCommandLineValue('-chareditor_nodie') ~= nil then
\thook.add('main.f_commandLine', 'chareditor_nodie', function()
\t\tsetGameMode('training')
\t\t-- los valores del menú de entrenamiento (normalmente los pone la pantalla de selección)
\t\tif menu ~= nil and menu.t_valuename ~= nil then
\t\t\tfor k, _ in pairs(menu.t_valuename) do
\t\t\t\tmenu[k] = 1
\t\t\tend
\t\t\tlocal ai = tonumber(getCommandLineValue('-p2.ai') or '0') or 0
\t\t\tif ai > 0 then
\t\t\t\tmenu.dummycontrol = 2
\t\t\t\tmenu.ailevel = math.min(8, ai)
\t\t\tend
\t\tend
\tend)
end
"""


def install_test_mod(ik):
    """Pone (o actualiza) el pequeño módulo de Lua que activa «Nadie se muere». IKEMEN carga solo lo que hay en
    external/mods; sin la bandera del editor no hace nada."""
    folder = Path(ik) / "external" / "mods"
    path = folder / MOD_NAME
    try:
        if path.exists() and path.read_text(encoding="utf-8") == MOD_CODE:
            return True
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(MOD_CODE, encoding="utf-8")
        return True
    except OSError:
        return False


def test_character(parent, project):
    dlg = TestDialog(parent, project)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return
    ik = Path(dlg.ik.text())
    exe = find_exe(ik)
    if not exe:
        QMessageBox.warning(parent, APP_NAME, tr('No encontré el ejecutable de IKEMEN GO en esa carpeta.'))
        return
    save_settings({"ikemen_dir": str(ik), "test_opp": dlg.opp.currentData() or "", "test_ai": dlg.ai.value(),
                   "test_stage": dlg.stage.currentData() or dlg.stage.currentText(),
                   "test_notime": dlg.notime.isChecked(), "test_power": dlg.power.isChecked(),
                   "test_nodie": dlg.nodie.isChecked(),
                   "test_windowed": dlg.windowed.isChecked()})
    args = [str(exe)] + dlg.args()
    if dlg.nodie.isChecked() and not install_test_mod(ik):
        QMessageBox.warning(parent, APP_NAME, tr('No pude preparar «Nadie se muere» (no se puede escribir en la '
                                                 'carpeta external/mods de IKEMEN). La pelea se abre normal.'))
    try:
        if sys.platform != "win32":
            try:
                os.chmod(exe, os.stat(exe).st_mode | 0o111)
            except OSError:
                pass
        (ik / "save").mkdir(exist_ok=True)
        log = open(ik / "save" / "editor_test.log", "w")
        flags = {}
        if sys.platform == "win32":
            flags["creationflags"] = 0x00000008  # DETACHED_PROCESS
        else:
            flags["start_new_session"] = True
        subprocess.Popen(args, cwd=str(ik), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **flags)
        if hasattr(parent, "status"):
            parent.status.setText(tr('▶ IKEMEN GO abierto: {0}').format(" ".join(args[1:])))
    except OSError as e:
        QMessageBox.warning(parent, APP_NAME, tr('No pude abrir IKEMEN GO: {0}').format(e))
