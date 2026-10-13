"""Ventana con el código (.air) de la acción elegida: se puede leer y editar a mano."""
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QMessageBox, QVBoxLayout

from core.air import AirFile
from i18n import tr
from ui.common import APP_NAME


class ActionCodeDialog(QDialog):
    def __init__(self, parent, action, air_name):
        super().__init__(parent)
        from ui.code_tab import CodeEditor, Highlighter
        self.setWindowTitle(tr('Código de la acción {0}').format(action.number))
        self.resize(760, 640)
        self.result_action = None
        lay = QVBoxLayout(self)
        info = QLabel(tr('Así se ve la acción en «{0}». Puedes cambiarla a mano; al aceptar se revisa y se '
                         'actualiza la animación (con deshacer).').format(air_name))
        info.setWordWrap(True)
        lay.addWidget(info)
        self.editor = CodeEditor()
        self._hl = Highlighter(self.editor.document())
        self.editor.setPlainText(action.text().rstrip("\n") + "\n")
        lay.addWidget(self.editor, 1)
        self.original = self.editor.toPlainText()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.check)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.number = action.number

    def check(self):
        text = self.editor.toPlainText()
        if text == self.original:
            self.reject()
            return
        air = AirFile.from_text(text)
        if len(air.actions) != 1:
            QMessageBox.warning(self, APP_NAME, tr('Tiene que quedar exactamente una acción ([Begin Action …]); '
                                                   'encontré {0}.').format(len(air.actions)))
            return
        a = air.actions[0]
        if not a.frames:
            QMessageBox.warning(self, APP_NAME, tr('La acción no tiene cuadros.'))
            return
        # comentarios de arriba incluidos, tal cual los escribió
        a.raw = (air.preamble or "") + (a.raw or "")
        a.raw = a.raw.rstrip("\n") + "\n\n"
        self.result_action = a
        self.accept()
