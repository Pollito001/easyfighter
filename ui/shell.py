"""Barra lateral de navegación y pantalla de bienvenida."""
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QStackedWidget, QVBoxLayout, QWidget,
)

from i18n import tr


class NavTabs(QWidget):
    """Como QTabWidget, pero con las secciones en una barra lateral."""
    currentChanged = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.side = QFrame()
        self.side.setObjectName("Sidebar")
        self.side.setFixedWidth(230)
        sl = QVBoxLayout(self.side)
        sl.setContentsMargins(10, 14, 10, 12)
        sl.setSpacing(8)
        head = QHBoxLayout()
        self.portrait = QLabel()
        self.portrait.setObjectName("Portrait")
        self.portrait.setFixedSize(64, 64)
        self.portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
        head.addWidget(self.portrait)
        names = QVBoxLayout()
        self.name = QLabel("")
        self.name.setObjectName("SideName")
        self.name.setWordWrap(True)
        self.sub = QLabel("")
        self.sub.setObjectName("SideSub")
        self.sub.setWordWrap(True)
        names.addWidget(self.name)
        names.addWidget(self.sub)
        names.addStretch(1)
        head.addLayout(names, 1)
        sl.addLayout(head)
        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setIconSize(QSize(20, 20))
        self.nav.currentRowChanged.connect(self._on_row)
        sl.addWidget(self.nav, 1)
        self.bottom = QVBoxLayout()
        sl.addLayout(self.bottom)
        lay.addWidget(self.side)
        self.stack = QStackedWidget()
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(10, 10, 10, 6)
        wl.addWidget(self.stack)
        lay.addWidget(wrap, 1)

    def addTab(self, w, label):
        self.stack.addWidget(w)
        it = QListWidgetItem(label)
        self.nav.addItem(it)
        if self.nav.count() == 1:
            self.nav.setCurrentRow(0)

    def add_bottom(self, w):
        self.bottom.addWidget(w)

    def set_visible(self, widgets):
        """Muestra en la barra solo estas secciones (las demás quedan escondidas)."""
        ids = {id(w) for w in widgets}
        first = None
        for i in range(self.stack.count()):
            show = id(self.stack.widget(i)) in ids
            self.nav.item(i).setHidden(not show)
            if show and first is None:
                first = i
        cur = self.nav.currentRow()
        if (cur < 0 or self.nav.item(cur).isHidden()) and first is not None:
            self.setCurrentIndex(first)

    def _on_row(self, r):
        if r >= 0:
            self.stack.setCurrentIndex(r)
            self.currentChanged.emit(r)

    def setCurrentIndex(self, i):
        self.nav.setCurrentRow(i)

    def setCurrentWidget(self, w):
        self.setCurrentIndex(self.stack.indexOf(w))

    def currentIndex(self):
        return self.stack.currentIndex()

    def currentWidget(self):
        return self.stack.currentWidget()

    def widget(self, i):
        return self.stack.widget(i)

    def count(self):
        return self.stack.count()

    def set_character(self, name, sub, pixmap=None):
        self.name.setText(name)
        self.sub.setText(sub)
        if pixmap is not None and not pixmap.isNull():
            self.portrait.setPixmap(pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation))
        else:
            self.portrait.setText("🥋")


class Card(QFrame):
    clicked = pyqtSignal()
    removeRequested = pyqtSignal()
    folderRequested = pyqtSignal()

    def __init__(self, title, path, pixmap=None, removable=False):
        super().__init__()
        self.removable = removable
        self.setObjectName("Card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        pic = QLabel()
        pic.setFixedSize(52, 52)
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if pixmap is not None and not pixmap.isNull():
            pic.setPixmap(pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))
        else:
            pic.setText("🥋")
        lay.addWidget(pic)
        txt = QVBoxLayout()
        t = QLabel(title)
        t.setObjectName("CardTitle")
        p = QLabel(path)
        p.setObjectName("CardPath")
        p.setWordWrap(True)
        txt.addWidget(t)
        txt.addWidget(p)
        lay.addLayout(txt, 1)
        self.x_btn = None
        if removable:
            from PyQt6.QtWidgets import QToolButton
            x = QToolButton()
            x.setText("✕")
            x.setAutoRaise(True)
            x.setCursor(Qt.CursorShape.ArrowCursor)
            x.setToolTip(tr('Quitar de recientes (no borra el personaje)'))
            x.clicked.connect(self.removeRequested)
            x.setVisible(False)
            lay.addWidget(x, 0, Qt.AlignmentFlag.AlignTop)
            self.x_btn = x

    def enterEvent(self, e):
        if self.x_btn is not None:
            self.x_btn.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.x_btn is not None:
            self.x_btn.setVisible(False)
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def contextMenuEvent(self, e):
        if not self.removable:
            return
        from PyQt6.QtWidgets import QMenu
        m = QMenu(self)
        m.addAction(tr('📂 Abrir'), self.clicked.emit)
        m.addAction(tr('📁 Abrir la carpeta'), self.folderRequested.emit)
        m.addSeparator()
        m.addAction(tr('✕ Quitar de recientes'), self.removeRequested.emit)
        m.exec(e.globalPos())


def open_folder(path):
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QDesktopServices
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def portrait_of(def_path):
    """Retrato (9000,1 o 9000,0) del personaje, sin abrirlo entero."""
    try:
        from core.deffile import DefFile
        from core.sff import SffFile
        from core.textio import ci_find
        from ui.common import sprite_qimage
        d = DefFile(def_path)
        sp = ci_find(Path(def_path).parent, d.get("Files", "sprite"))
        if not sp:
            return None, d.get("Info", "displayname") or d.get("Info", "name")
        sff = SffFile.load(sp)
        s = sff.find(9000, 1) or sff.find(9000, 0)
        name = d.get("Info", "displayname") or d.get("Info", "name")
        if s is None:
            return None, name
        return QPixmap.fromImage(sprite_qimage(sff, s)), name
    except Exception:
        return None, None


class Welcome(QWidget):
    openRequested = pyqtSignal(str)
    newRequested = pyqtSignal()
    browseRequested = pyqtSignal()
    exampleRequested = pyqtSignal(str)
    removeRequested = pyqtSignal(str)
    clearRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Welcome")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(60, 50, 60, 40)
        title = QHBoxLayout()
        title.setSpacing(0)
        a = QLabel("Easy")
        a.setObjectName("HeroAccent")
        b = QLabel("Fighter")
        b.setObjectName("Hero")
        title.addWidget(a)
        title.addWidget(b)
        title.addStretch(1)
        outer.addLayout(title)
        sub = QLabel(tr('Crea personajes para IKEMEN GO y MUGEN sin escribir código.') + "\n" +
                     tr('Sprites, paletas, animaciones con cajas de golpe, código, sonidos y movimientos especiales.'))
        sub.setObjectName("HeroSub")
        outer.addWidget(sub)
        outer.addSpacing(24)
        row = QHBoxLayout()
        nb = QPushButton(tr('✨  Personaje nuevo'))
        nb.setObjectName("primary")
        nb.setMinimumHeight(44)
        nb.clicked.connect(self.newRequested)
        ob = QPushButton(tr('📂  Abrir personaje…'))
        ob.setMinimumHeight(44)
        ob.clicked.connect(self.browseRequested)
        eb = QPushButton(tr('🥋  Personaje de ejemplo'))
        eb.setMinimumHeight(44)
        eb.setToolTip(tr('Abre un personaje completo hecho con el modo simple, para ver cómo está hecho y probarlo.'))
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(eb)
        from ui.mainwindow import EXAMPLES
        for key, label in EXAMPLES:
            a = menu.addAction(f"{key} — {tr(label)}")
            a.triggered.connect(lambda _c=False, key=key: self.exampleRequested.emit(key))
        eb.setMenu(menu)
        row.addWidget(nb)
        row.addWidget(ob)
        row.addWidget(eb)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addSpacing(26)
        rh = QHBoxLayout()
        lbl = QLabel(tr('Recientes'))
        lbl.setObjectName("CardTitle")
        rh.addWidget(lbl)
        rh.addStretch(1)
        self.clear_btn = QPushButton(tr('🧹 Limpiar la lista'))
        self.clear_btn.setFlat(True)
        self.clear_btn.setToolTip(tr('Quita todos de recientes (no borra ningún personaje). Para quitar uno solo, '
                                     'pasa el ratón por encima y toca ✕, o clic derecho.'))
        self.clear_btn.clicked.connect(self.clearRequested)
        rh.addWidget(self.clear_btn)
        outer.addLayout(rh)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(12)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setStyleSheet("background: transparent;")
        sc.setWidget(self.grid_host)
        outer.addWidget(sc, 1)

    def set_recent(self, paths):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        shown = 0
        for p in paths:
            if not Path(p).is_file():
                continue
            pm, name = portrait_of(p)
            c = Card(name or Path(p).stem, str(Path(p).parent), pm, removable=True)
            c.clicked.connect(lambda p=p: self.openRequested.emit(p))
            c.removeRequested.connect(lambda p=p: self.removeRequested.emit(p))
            c.folderRequested.connect(lambda p=p: open_folder(Path(p).parent))
            self.grid.addWidget(c, shown // 3, shown % 3)
            shown += 1
            if shown >= 9:
                break
        self.clear_btn.setVisible(bool(shown))
        if not shown:
            empty = QLabel(tr('Todavía no has abierto ningún personaje.'))
            empty.setObjectName("CardPath")
            self.grid.addWidget(empty, 0, 0)
        self.grid.setRowStretch(self.grid.rowCount(), 1)
