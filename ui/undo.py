"""Deshacer / rehacer con funciones simples."""
from PyQt6.QtGui import QUndoCommand


class FnCommand(QUndoCommand):
    def __init__(self, text, redo, undo, after=None):
        super().__init__(text)
        self._redo, self._undo, self._after = redo, undo, after

    def redo(self):
        self._redo()
        if self._after:
            self._after()

    def undo(self):
        self._undo()
        if self._after:
            self._after()


def set_attrs(obj, **values):
    """(redo, undo) que cambian atributos de obj."""
    old = {k: getattr(obj, k) for k in values}

    def redo():
        for k, v in values.items():
            setattr(obj, k, v)

    def undo():
        for k, v in old.items():
            setattr(obj, k, v)
    return redo, undo
