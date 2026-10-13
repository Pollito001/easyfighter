"""Asistente para crear un personaje: desde la plantilla o copiando otro."""
import re
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from core import template
from core.char_copy import safe_base
from core.sff import SffFile, Sprite, palette_from_rgb
from core.snd import SndFile
from core.textio import write_text
from i18n import tr
from ui.common import APP_NAME, image_to_indices
from ui.mainwindow import load_settings, save_settings


def figure(w, h, k, portrait=False):
    """Figura provisional (dibujada aquí) para que el personaje se vea en el juego."""
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    body, skin, belt, dark = QColor(60, 110, 200), QColor(240, 200, 160), QColor(30, 30, 40), QColor(20, 40, 90)
    if portrait:
        p.fillRect(0, 0, w, h, QColor(40, 50, 70))
        p.setBrush(skin)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(w * 0.2, h * 0.12, w * 0.6, h * 0.62))
        p.setBrush(dark)
        p.drawRect(QRectF(w * 0.2, h * 0.12, w * 0.6, h * 0.16))
        p.setBrush(body)
        p.drawRect(QRectF(w * 0.08, h * 0.78, w * 0.84, h * 0.22))
        p.end()
        return img
    p.setPen(Qt.PenStyle.NoPen)
    cx = w / 2
    p.setBrush(dark)
    p.drawRect(QRectF(cx - 12 * k, h - 40 * k, 9 * k, 40 * k))
    p.drawRect(QRectF(cx + 3 * k, h - 40 * k, 9 * k, 40 * k))
    p.setBrush(body)
    path = QPainterPath()
    path.addRoundedRect(QRectF(cx - 14 * k, h - 78 * k, 28 * k, 42 * k), 6 * k, 6 * k)
    p.drawPath(path)
    p.drawRect(QRectF(cx + 10 * k, h - 72 * k, 16 * k, 7 * k))
    p.setBrush(belt)
    p.drawRect(QRectF(cx - 14 * k, h - 42 * k, 28 * k, 4 * k))
    p.setBrush(skin)
    p.drawEllipse(QRectF(cx - 9 * k, h - 96 * k, 18 * k, 18 * k))
    p.drawEllipse(QRectF(cx + 24 * k, h - 73 * k, 8 * k, 8 * k))
    p.end()
    return img


class ExampleDialog(QDialog):
    """Usar un personaje de ejemplo como base: tú decides su nombre (carpeta y archivos se llaman así)."""

    def __init__(self, parent, key):
        super().__init__(parent)
        self.key = key
        self.setWindowTitle(tr('Usar a {0} de base').format(key))
        self.setMinimumWidth(560)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr('Se hace una copia de {0} para que la cambies. Puedes dejarle su nombre o ponerle '
                                'el tuyo: la carpeta y los archivos se llaman igual que el personaje.').format(key)))
        lay.itemAt(0).widget().setWordWrap(True)
        form = QFormLayout()
        self.name = QLineEdit(key)
        self.name.textChanged.connect(lambda t: self.folder.setText(safe_base(t) if t.strip() else ""))
        self.folder = QLineEdit(key)
        self.folder.setToolTip(tr('Nombre de la carpeta y de los archivos (.def, .sff, .air…). Sin espacios.'))
        self.author = QLineEdit(load_settings().get("author", ""))
        self.author.setPlaceholderText(tr('(se queda el de {0})').format(key))
        row = QHBoxLayout()
        self.parent_dir = QLineEdit(load_settings().get("chars_dir", str(Path.home())))
        b = QPushButton("…")
        b.clicked.connect(self.browse)
        row.addWidget(self.parent_dir, 1)
        row.addWidget(b)
        w = QWidget()
        w.setLayout(row)
        form.addRow(tr('Nombre:'), self.name)
        form.addRow(tr('Carpeta y archivos:'), self.folder)
        form.addRow(tr('Autor:'), self.author)
        form.addRow(tr('Crear dentro de:'), w)
        lay.addLayout(form)
        hint = QLabel(tr('Consejo: créalo dentro de la carpeta «chars» de IKEMEN GO para probarlo enseguida.'))
        hint.setWordWrap(True)
        lay.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.check)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.name.selectAll()

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, tr('Crear dentro de'), self.parent_dir.text())
        if d:
            self.parent_dir.setText(d)

    def check(self):
        name, folder = self.name.text().strip(), safe_base(self.folder.text())
        if not name or not self.folder.text().strip():
            QMessageBox.warning(self, APP_NAME, tr('Escribe el nombre y la carpeta.'))
            return
        if not Path(self.parent_dir.text()).is_dir():
            QMessageBox.warning(self, APP_NAME, tr('Escoge dónde crearlo.'))
            return
        dest = Path(self.parent_dir.text()) / folder
        if dest.exists() and any(dest.iterdir()):
            QMessageBox.warning(self, APP_NAME, tr('La carpeta «{0}» ya existe y no está vacía.').format(dest))
            return
        self.result_ = (name, folder, self.author.text().strip(), dest)
        save_settings({"chars_dir": self.parent_dir.text()} | ({"author": self.author.text().strip()}
                                                              if self.author.text().strip() else {}))
        self.accept()


class NewCharDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.created = None
        self.setWindowTitle(tr('Personaje nuevo'))
        self.setMinimumWidth(560)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText(tr('Ej.: Kaito Oscuro'))
        self.name.textChanged.connect(self.suggest_folder)
        self.folder_name = QLineEdit()
        self.author = QLineEdit(load_settings().get("author", ""))
        row = QHBoxLayout()
        self.parent_dir = QLineEdit(load_settings().get("chars_dir", str(Path.home())))
        b = QPushButton("…")
        b.clicked.connect(self.browse)
        row.addWidget(self.parent_dir, 1)
        row.addWidget(b)
        w = QWidget()
        w.setLayout(row)
        self.res = QComboBox()
        for txt, lc in ((tr('320×240 (MUGEN clásico)'), (320, 240)), (tr('640×480'), (640, 480)),
                        (tr('1280×720 (HD)'), (1280, 720))):
            self.res.addItem(txt, lc)
        form.addRow(tr('Nombre:'), self.name)
        form.addRow(tr('Carpeta:'), self.folder_name)
        form.addRow(tr('Autor:'), self.author)
        form.addRow(tr('Crear dentro de:'), w)
        form.addRow(tr('Resolución:'), self.res)
        lay.addLayout(form)
        hint = QLabel(tr('Consejo: créalo dentro de la carpeta «chars» de IKEMEN GO para probarlo enseguida.'))
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.from_tpl = QRadioButton(tr('Desde la plantilla: se puede jugar ya (figura provisional, golpe de ejemplo con «a»)'))
        self.from_copy = QRadioButton(tr('Copiando otro personaje (.def) para usarlo de base'))
        self.from_sprites = QRadioButton(tr('Con los sprites de otro personaje (.def): sus animaciones van a las '
                                            'casillas del modo simple, con el código de la plantilla'))
        self.from_tpl.setChecked(True)
        lay.addWidget(self.from_tpl)
        lay.addWidget(self.from_copy)
        lay.addWidget(self.from_sprites)
        crow = QHBoxLayout()
        self.copy_src = QLineEdit()
        self.copy_src.setPlaceholderText(tr('.def del otro personaje'))
        cb = QPushButton("…")
        cb.clicked.connect(self.browse_src)
        crow.addWidget(self.copy_src, 1)
        crow.addWidget(cb)
        lay.addLayout(crow)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.create)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def suggest_folder(self, t):
        self.folder_name.setText(re.sub(r"[^\w\-]+", "_", t.strip()).strip("_"))

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, tr('Crear dentro de'), self.parent_dir.text())
        if d:
            self.parent_dir.setText(d)

    def browse_src(self):
        f, _ = QFileDialog.getOpenFileName(self, tr('Personaje a copiar'), self.parent_dir.text(), tr('Personaje (*.def)'))
        if f:
            self.copy_src.setText(f)
            if self.from_tpl.isChecked():
                self.from_copy.setChecked(True)

    def create(self):
        name = self.name.text().strip()
        folder = self.folder_name.text().strip()
        if not name or not folder:
            QMessageBox.warning(self, APP_NAME, tr('Escribe el nombre y la carpeta.'))
            return
        dest = Path(self.parent_dir.text()) / folder
        if dest.exists() and any(dest.iterdir()):
            QMessageBox.warning(self, APP_NAME, tr('La carpeta «{0}» ya existe y no está vacía.').format(dest))
            return
        save_settings({"author": self.author.text().strip(), "chars_dir": self.parent_dir.text()})
        try:
            if self.from_sprites.isChecked():
                self.created = self.from_other(dest, name)
            elif self.from_copy.isChecked():
                self.created = self.copy_char(dest, folder, name)
            else:
                self.created = self.make_template(dest, folder, name)
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, APP_NAME, tr('No pude crear el personaje: {0}').format(e))
            return
        if self.created:
            self.accept()

    def make_template(self, dest, base, name):
        dest.mkdir(parents=True, exist_ok=True)
        lw, lh = self.res.currentData()
        k = lw / 320
        write_text(dest / f"{base}.def", template.make_def(name, self.author.text().strip(), lw, lh, base), "utf-8", "\r\n")
        write_text(dest / f"{base}.cns", template.make_cns(k), "utf-8", "\r\n")
        write_text(dest / f"{base}.cmd", template.CMD, "utf-8", "\r\n")
        write_text(dest / f"{base}.air", template.make_air(k), "utf-8", "\r\n")
        sff = SffFile()
        imgs = [((0, 0), figure(int(60 * k), int(100 * k), k), "feet"),
                ((9000, 0), figure(int(25 * k), int(25 * k), k, True), "zero"),
                ((9000, 1), figure(int(120 * k), int(140 * k), k, True), "zero")]
        rgb = None
        for (g, n), img, ax in imgs:
            if rgb is None:
                idx, rgb = image_to_indices(img)
            else:
                idx, _ = image_to_indices(img, rgb)
            s = Sprite(g, n)
            s.set_pixels(idx)
            h, w = idx.shape
            if ax == "feet":
                s.x, s.y = w // 2, h
            sff.sprites.append(s)
        sff.palettes = [palette_from_rgb(rgb, 1, 1)]
        sff.save(dest / f"{base}.sff")
        SndFile().save(dest / f"{base}.snd")
        return dest / f"{base}.def"

    def from_other(self, dest, name):
        from core.char_extract import extract
        src = Path(self.copy_src.text().strip())
        if not src.is_file():
            QMessageBox.warning(self, APP_NAME, tr('Elige el .def del otro personaje.'))
            return None
        new_def, done = extract(src, dest, name, self.author.text().strip(), tr=tr)
        QMessageBox.information(self, APP_NAME, tr(
            'Listo: {0} animaciones, {1} golpes y {2} especiales puestos en el modo simple. Al abrirse, revisa '
            'cada casilla y guarda.').format(done["anims"], done["normals"], done["specials"]))
        return new_def

    def copy_char(self, dest, base, name):
        src = Path(self.copy_src.text().strip())
        if not src.is_file():
            QMessageBox.warning(self, APP_NAME, tr('Elige el .def del personaje a copiar.'))
            return None
        from core.char_copy import copy_character
        return copy_character(src, dest, base, name, self.author.text().strip() or None)
