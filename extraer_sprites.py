#!/usr/bin/env python3
"""Saca los sprites de un personaje y los pone en uno nuevo del editor (modo simple).

Con doble clic: te pregunta el personaje, dónde crear el nuevo y su nombre, y lo abre en el editor.
Desde la terminal:
    ./extraer_sprites.py  origen.def  carpeta_nueva  [nombre]  [--sin-sonidos]  [--no-abrir]
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from i18n import tr  # noqa: E402


def open_editor(new_def):
    subprocess.Popen([sys.executable, str(HERE / "main.py"), str(new_def)])


def run_cli(args):
    from core.char_extract import extract
    flags = {a for a in args if a.startswith("--")}
    args = [a for a in args if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 1
    src, dest = Path(args[0]), Path(args[1])
    name = args[2] if len(args) > 2 else dest.name
    new_def, done = extract(src, dest, name, copy_sounds="--sin-sonidos" not in flags, tr=tr)
    print(tr('Listo: {0} animaciones, {1} golpes y {2} especiales puestos en el modo simple. Al abrirse, revisa '
             'cada casilla y guarda.').format(done["anims"], done["normals"], done["specials"]))
    print(new_def)
    if "--no-abrir" not in flags:
        open_editor(new_def)
    return 0


def run_gui():
    from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
    app = QApplication(sys.argv)
    from ui import theme
    theme.apply(app)
    from core.char_extract import extract
    title = tr('Sacar sprites a un personaje nuevo')
    src, _ = QFileDialog.getOpenFileName(None, tr('Personaje del que sacar los sprites'), str(Path.home()),
                                         tr('Personaje (*.def)'))
    if not src:
        return 0
    parent = QFileDialog.getExistingDirectory(None, tr('Crear el personaje nuevo dentro de'),
                                              str(Path(src).parent.parent))
    if not parent:
        return 0
    name, ok = QInputDialog.getText(None, title, tr('Nombre del personaje nuevo:'),
                                    text=Path(src).stem + "_nuevo")
    if not ok or not name.strip():
        return 0
    import re
    folder = re.sub(r"[^\w\-]+", "_", name.strip()).strip("_") or "Personaje"
    dest = Path(parent) / folder
    try:
        new_def, done = extract(src, dest, name.strip(), tr=tr)
    except FileExistsError:
        QMessageBox.warning(None, title, tr('La carpeta «{0}» ya existe y no está vacía.').format(dest))
        return 1
    except Exception as e:
        QMessageBox.warning(None, title, tr('No pude crear el personaje: {0}').format(e))
        return 1
    QMessageBox.information(None, title, tr(
        'Listo: {0} animaciones, {1} golpes y {2} especiales puestos en el modo simple. Al abrirse, revisa '
        'cada casilla y guarda.').format(done["anims"], done["normals"], done["specials"]))
    open_editor(new_def)
    return 0


if __name__ == "__main__":
    sys.exit(run_cli(sys.argv[1:]) if len(sys.argv) > 1 else run_gui())
