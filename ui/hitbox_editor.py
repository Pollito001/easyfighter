"""«🟥 Caja de golpe»: dónde pega cada cuadro de un golpe o especial (el puño, el pie…), con el ratón.

La caja roja es la que hace daño. Si no la tocas, el editor la pone solo en la punta de lo que pega; si la
mueves, la estiras o dibujas otra, ese cuadro queda con tus cajas («a mano»).

Con body=True edita las cajas azules (el cuerpo: donde le pueden pegar) de cualquier animación."""
import copy

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from i18n import tr
from ui import theme
from ui.align_dialog import CLSN1, CLSN2
from ui.common import APP_NAME

HANDLE = 7          # px de pantalla para agarrar una esquina o un borde


class BoxCanvas(QWidget):
    changed = pyqtSignal()

    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg
        self.zoom = 2.5
        self.sel = None          # índice de la caja escogida
        self.drag = None         # (modo, índice, punto inicial, caja inicial)
        self.setMinimumSize(QSize(560, 460))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ---- coordenadas
    def origin(self):
        s = self.dlg.sprite()
        if s is None:
            return QPointF(self.width() / 2, self.height() - 40)
        h, w = s.pixels().shape[:2]
        z = self.zoom
        # el sprite centrado: el eje donde quede
        return QPointF(self.width() / 2 - (w / 2 - s.x) * z, self.height() / 2 + (s.y - h / 2) * z)

    def to_box(self, p):
        o = self.origin()
        return (p.x() - o.x()) / self.zoom, (p.y() - o.y()) / self.zoom

    def rect_of(self, b):
        o = self.origin()
        z = self.zoom
        x1, y1, x2, y2 = b
        return QRectF(o.x() + min(x1, x2) * z, o.y() + min(y1, y2) * z, abs(x2 - x1) * z, abs(y2 - y1) * z)

    def wheelEvent(self, e):
        self.zoom = max(0.5, min(10.0, self.zoom * (1.15 if e.angleDelta().y() > 0 else 1 / 1.15)))
        self.update()

    # ---- dibujar
    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.CANVAS))
        s = self.dlg.sprite()
        if s is None:
            p.end()
            return
        o = self.origin()
        z = self.zoom
        pm = self.dlg.sm.pixmap(s.group, s.number)
        if pm is not None:
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, z < 1)
            p.drawPixmap(QRectF(o.x() - s.x * z, o.y() - s.y * z, pm.width() * z, pm.height() * z), pm,
                         QRectF(pm.rect()))
        # suelo y eje
        p.setPen(QPen(QColor(255, 107, 53, 120), 1))
        p.drawLine(QPointF(0, o.y()), QPointF(self.width(), o.y()))
        p.drawLine(QPointF(o.x(), o.y() - 8), QPointF(o.x(), o.y() + 8))
        # de guía: el cuerpo (azul) al editar la de golpe, o la de golpe (roja) al editar el cuerpo
        guide, edit = (CLSN1, CLSN2) if self.dlg.body else (CLSN2, CLSN1)
        for b in self.dlg.body_boxes():
            c = QColor(guide)
            c.setAlpha(40)
            p.setBrush(c)
            p.setPen(QPen(QColor(guide), 1, Qt.PenStyle.DotLine))
            p.drawRect(self.rect_of(b))
        # las que se editan: las tuyas sólidas, las automáticas punteadas
        manual = self.dlg.is_manual()
        for i, b in enumerate(self.dlg.boxes()):
            c = QColor(edit)
            c.setAlpha(80 if manual else 50)
            p.setBrush(c)
            p.setPen(QPen(QColor(255, 255, 255) if i == self.sel else QColor(edit), 2,
                          Qt.PenStyle.SolidLine if manual else Qt.PenStyle.DashLine))
            r = self.rect_of(b)
            p.drawRect(r)
            if i == self.sel:
                p.setBrush(QColor(255, 255, 255))
                for c_ in (r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight()):
                    p.drawRect(QRectF(c_.x() - 3, c_.y() - 3, 6, 6))
        if self.drag and self.drag[0] == "new":
            p.setPen(QPen(QColor(255, 255, 255), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self.rect_of(self.drag[3]))
        p.setPen(QColor(theme.MUTED))
        if self.dlg.body:
            txt = tr('Muévelas, estíralas o dibuja otra. Solo le pueden pegar en lo azul.')
            if not self.dlg.boxes():
                txt = tr('En este cuadro no le pueden pegar. Arrastra en el dibujo para ponerle una caja.')
        else:
            txt = tr('Muévela, estírala o dibuja otra. Solo pega lo que está en rojo.')
            if not self.dlg.boxes():
                txt = tr('Este cuadro no pega. Arrastra en el dibujo para ponerle una caja.')
        p.drawText(10, 20, txt)
        p.end()

    # ---- ratón
    def hit_test(self, pos):
        """(índice, parte) de la caja bajo el ratón: parte = «move» o una combinación de l/r/t/b."""
        for i, b in reversed(list(enumerate(self.dlg.boxes()))):
            r = self.rect_of(b)
            if not r.adjusted(-HANDLE, -HANDLE, HANDLE, HANDLE).contains(pos):
                continue
            part = ""
            if abs(pos.x() - r.left()) <= HANDLE:
                part += "l"
            elif abs(pos.x() - r.right()) <= HANDLE:
                part += "r"
            if abs(pos.y() - r.top()) <= HANDLE:
                part += "t"
            elif abs(pos.y() - r.bottom()) <= HANDLE:
                part += "b"
            if part or r.contains(pos):
                return i, part or "move"
        return None, None

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self.drag is None:
            _i, part = self.hit_test(pos)
            cur = {None: Qt.CursorShape.CrossCursor, "move": Qt.CursorShape.SizeAllCursor,
                   "l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor,
                   "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
                   "lt": Qt.CursorShape.SizeFDiagCursor, "rb": Qt.CursorShape.SizeFDiagCursor,
                   "rt": Qt.CursorShape.SizeBDiagCursor, "lb": Qt.CursorShape.SizeBDiagCursor}.get(part)
            self.setCursor(cur or Qt.CursorShape.CrossCursor)
            return
        mode, i, start, b0 = self.drag
        x, y = self.to_box(pos)
        sx, sy = self.to_box(start)
        dx, dy = x - sx, y - sy
        x1, y1, x2, y2 = b0
        if mode == "new":
            self.drag = (mode, i, start, (min(sx, x), min(sy, y), max(sx, x), max(sy, y)))
        else:
            if mode == "move":
                x1, x2, y1, y2 = x1 + dx, x2 + dx, y1 + dy, y2 + dy
            else:
                if "l" in mode:
                    x1 += dx
                if "r" in mode:
                    x2 += dx
                if "t" in mode:
                    y1 += dy
                if "b" in mode:
                    y2 += dy
            self.dlg.set_box(i, (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self.dlg.sprite() is None:
            return
        pos = e.position()
        i, part = self.hit_test(pos)
        if i is not None:
            self.dlg.make_manual()
            self.sel = i
            self.drag = (part, i, pos, tuple(self.dlg.boxes()[i]))
        else:
            x, y = self.to_box(pos)
            self.sel = None
            self.drag = ("new", None, pos, (x, y, x, y))
        self.update()

    def mouseReleaseEvent(self, _e):
        if self.drag is None:
            return
        mode, _i, _s, b = self.drag
        self.drag = None
        if mode == "new":
            x1, y1, x2, y2 = b
            if (x2 - x1) * self.zoom >= 6 and (y2 - y1) * self.zoom >= 6:
                self.dlg.make_manual()
                self.sel = self.dlg.add_box(b)
        self.changed.emit()
        self.update()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.sel is not None:
            self.dlg.make_manual()
            self.dlg.del_box(self.sel)
            self.sel = None
            self.changed.emit()
            self.update()
            return
        if e.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self.dlg.step(-1)
            return
        if e.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self.dlg.step(1)
            return
        super().keyPressEvent(e)


class HitboxEditor(QDialog):
    def __init__(self, sm, title, keys, hits, entry, ref_kind="S", body=False):
        super().__init__(sm.main)
        self.sm = sm
        self.keys = list(keys)
        self.hits = set(hits)
        self.ref_kind = ref_kind
        self.body = body
        from core import simple_gen as sg
        # cajas de golpe de la animación (de guía al editar el cuerpo)
        self.red = sg.manual_boxes(entry)
        if body:
            # el cuerpo: lo ya dibujado (aunque esté en «Automático») y las automáticas en los demás cuadros
            drawn = {}
            for k_, v in (entry.get("hurt") or {}).items():
                try:
                    drawn[int(k_)] = [[int(round(float(c))) for c in b[:4]] for b in v if len(b) >= 4]
                except (TypeError, ValueError):
                    pass
            self.manual = {i: drawn[i] if i in drawn else self.auto(i) for i in range(len(self.keys))}
        else:
            self.manual = {i: [list(b) for b in v] for i, v in self.red.items()}
            if sg.box_mode(entry) != "manual":
                # empieza con lo que había: las automáticas en los cuadros que pegan (y lo ya dibujado)
                for i in self.hits:
                    if 0 <= i < len(self.keys) and i not in self.manual:
                        self.manual[i] = self.auto(i)
        self.result = None
        self.setWindowTitle((tr('✏ Cajas del cuerpo a mano: {0}') if body else
                             tr('✏ Cajas de daño a mano: {0}')).format(title))
        self.resize(1000, 640)
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        lab = QLabel(tr('Cuadros (💥 = el del golpe · 🟦 = tiene cajas del cuerpo):') if body else
                     tr('Cuadros (💥 = el del golpe · 🟥 = tiene caja de daño):'))
        lab.setWordWrap(True)
        left.addWidget(lab)
        self.list = QListWidget()
        self.list.setIconSize(QSize(48, 48))
        self.list.currentRowChanged.connect(self.on_frame)
        left.addWidget(self.list, 1)
        lw = QWidget()
        lw.setLayout(left)
        lw.setFixedWidth(220)
        lay.addWidget(lw)
        right = QVBoxLayout()
        hint = QLabel(tr('Las cajas azules son el cuerpo: donde le pueden pegar. Cúbrelo con una, dos o las que '
                         'quieras. Arrastra una caja para moverla, sus bordes o esquinas para estirarla, o arrastra '
                         'en un lugar vacío para dibujar otra. Supr borra la escogida. Rueda del ratón: zoom.')
                      if body else
                      tr('La caja roja es la que hace daño. Ponla solo en lo que pega (el puño, el pie…). '
                         'Arrastra la caja para moverla, sus bordes o esquinas para estirarla, o arrastra en un '
                         'lugar vacío para dibujar otra. Supr borra la escogida. Rueda del ratón: zoom.'))
        hint.setWordWrap(True)
        right.addWidget(hint)
        self.canvas = BoxCanvas(self)
        self.canvas.changed.connect(self.fill_list)
        right.addWidget(self.canvas, 1)
        row = QHBoxLayout()
        if body:
            btns = ((tr('↺ Como la automática'), tr('Pone en este cuadro las cajas que pondría el editor.'),
                     self.on_auto),
                    (tr('▭ Una sola caja'), tr('Una caja que cubre todo el dibujo de este cuadro.'), self.on_one),
                    (tr('🚫 Sin caja'), tr('En este cuadro no le pueden pegar (es invencible).'), self.on_none),
                    (tr('⧉ Igual en el siguiente'), tr('Copia las cajas de este cuadro al siguiente.'),
                     self.on_copy_next),
                    (tr('↺ Empezar de nuevo'), tr('Todos los cuadros con las cajas automáticas.'), self.on_all_auto))
        else:
            btns = ((tr('↺ Como la automática'), tr('Pone en este cuadro la caja que pondría el editor.'),
                     self.on_auto),
                    (tr('🚫 Sin caja'), tr('Este cuadro no pega (aunque sea el cuadro del golpe).'),
                     self.on_none),
                    (tr('⧉ Igual en el siguiente'), tr('Copia las cajas de este cuadro al siguiente.'),
                     self.on_copy_next),
                    (tr('↺ Empezar de nuevo'), tr('Todos los cuadros como los pondría el editor: la caja '
                                                  'automática en los que pegan y nada en los demás.'),
                     self.on_all_auto))
        for txt, tip, fn in btns:
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        cancel = QPushButton(tr('Cancelar'))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr('✔ Guardar'))
        ok.setObjectName("primary")
        ok.setDefault(True)
        ok.clicked.connect(self.on_ok)
        row.addWidget(cancel)
        row.addWidget(ok)
        right.addLayout(row)
        lay.addLayout(right, 1)
        self.cur = 0
        self.fill_list()
        first = min(self.hits) if (self.hits and not body) else 0
        self.list.setCurrentRow(max(0, min(first, len(self.keys) - 1)))

    # ---- datos del cuadro actual
    def sprite(self):
        if not (0 <= self.cur < len(self.keys)):
            return None
        return self.sm.sprite(*self.keys[self.cur])

    def is_manual(self):
        return True             # aquí todo es a mano: lo que ves es lo que pega

    def auto(self, i):
        g, n = self.keys[i]
        bx = self.sm.auto_boxes_of(g, n, i in self.hits, self.ref_kind, body_auto=True)
        return [list(b) for b in ((bx[1] if self.body else bx[0]) if bx else [])]

    def body_boxes(self):
        """Las de guía: el cuerpo al editar la de golpe, o la de golpe al editar el cuerpo."""
        g, n = self.keys[self.cur]
        if self.body:
            if self.cur in self.red or getattr(self.red, "strict", False):
                return self.red.get(self.cur, [])
            if self.cur not in self.hits:
                return []
            bx = self.sm.auto_boxes_of(g, n, True, self.ref_kind)
            return bx[0] if bx else []
        bx = self.sm.auto_boxes_of(g, n, False, self.ref_kind)
        return bx[1] if bx else []

    def boxes(self):
        return self.manual.get(self.cur, [])

    def make_manual(self):
        if self.cur not in self.manual:
            self.manual[self.cur] = []

    def set_box(self, i, b):
        self.manual[self.cur][i] = [int(round(v)) for v in b]

    def add_box(self, b):
        self.manual[self.cur].append([int(round(v)) for v in b])
        return len(self.manual[self.cur]) - 1

    def del_box(self, i):
        del self.manual[self.cur][i]

    # ---- lista
    def fill_list(self):
        row = self.list.currentRow()
        self.list.blockSignals(True)
        self.list.clear()
        for i, (g, n) in enumerate(self.keys):
            mark = []
            if i in self.hits:
                mark.append("💥")
            if self.manual.get(i):
                mark.append("🟦" if self.body else "🟥")
            elif self.body:
                mark.append("🚫")
            it = QListWidgetItem(f"{tr('Cuadro {0}').format(i + 1)}  {' '.join(mark)}")
            pm = self.sm.pixmap(g, n)
            if pm is not None:
                it.setIcon(QIcon(pm.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)))
            self.list.addItem(it)
        self.list.setCurrentRow(row if row >= 0 else self.cur)
        self.list.blockSignals(False)

    def on_frame(self, r):
        if r < 0:
            return
        self.cur = r
        self.canvas.sel = None
        self.canvas.update()

    def step(self, d):
        self.list.setCurrentRow(max(0, min(len(self.keys) - 1, self.cur + d)))

    # ---- botones
    def on_auto(self):
        self.manual[self.cur] = self.auto(self.cur)
        self.canvas.sel = None
        self.fill_list()
        self.canvas.update()

    def on_one(self):
        g, n = self.keys[self.cur]
        s = self.sm.sprite(g, n)
        if s is None:
            return
        from core.boxes import auto_boxes
        self.manual[self.cur] = [list(b) for b in auto_boxes(s, two=False)]
        self.canvas.sel = None
        self.fill_list()
        self.canvas.update()

    def on_none(self):
        self.manual[self.cur] = []
        self.canvas.sel = None
        self.fill_list()
        self.canvas.update()

    def on_copy_next(self):
        if self.cur + 1 >= len(self.keys):
            return
        self.manual[self.cur + 1] = copy.deepcopy(self.boxes())
        self.fill_list()
        self.step(1)

    def on_all_auto(self):
        if self.manual and QMessageBox.question(self, APP_NAME, tr('¿Empezar de nuevo? Se pierden las cajas que '
                                                                   'dibujaste.')) != QMessageBox.StandardButton.Yes:
            return
        if self.body:
            self.manual = {i: self.auto(i) for i in range(len(self.keys))}
        else:
            self.manual = {i: self.auto(i) for i in self.hits if 0 <= i < len(self.keys)}
        self.canvas.sel = None
        self.fill_list()
        self.canvas.update()

    def on_ok(self):
        if self.body:
            # todos los cuadros (uno sin cajas es a propósito: ahí no le pueden pegar)
            self.result = {str(i): self.manual.get(i, []) for i in range(len(self.keys))}
            self.accept()
            return
        self.result = {str(i): v for i, v in sorted(self.manual.items()) if v}
        self.accept()
