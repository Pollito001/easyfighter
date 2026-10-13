"""Estilo visual: varios temas (oscuro, claro, medianoche, arcade, bosque, alto contraste)."""
from PyQt6.QtGui import QColor, QPalette

# temas: nombre que se ve, y sus colores
THEMES = {
    "dark": ("🌑 Oscuro (naranja)", dict(
        BG="#14161b", PANEL="#1b1e25", PANEL2="#22262f", LINE="#2d323d", TEXT="#e7eaf0", MUTED="#8b93a3",
        ACCENT="#ff6b35", ACCENT2="#ffb547", SELECT="#3a2a24", INPUT="#101217", CANVAS="#101217",
        HOVER="#2a2f3a", ALT="#15181e", ITEMHOVER="#1e222a", SCROLL="#343a46", SPINHOVER="#2f3541",
        OFF="#5b6270", OFFLINE="#262a33", ARROWOFF="#4a505c", ONACC="#111111", GRAD1="#1a1214", GRAD2="#10141c",
        OK="#6ee7b7", INFO="#7dd3fc", WARN="#ffb547", ERR="#ff6b6b")),
    "light": ("☀ Claro", dict(
        BG="#eef0f4", PANEL="#ffffff", PANEL2="#f3f4f7", LINE="#d3d8e1", TEXT="#1c2028", MUTED="#5d6676",
        ACCENT="#e4571e", ACCENT2="#b45a06", SELECT="#fde4d8", INPUT="#ffffff", CANVAS="#dfe3ea",
        HOVER="#e8ebf0", ALT="#f7f8fa", ITEMHOVER="#eceff3", SCROLL="#c4cad4", SPINHOVER="#e3e6eb",
        OFF="#a3a9b4", OFFLINE="#e1e4ea", ARROWOFF="#b5bac3", ONACC="#ffffff", GRAD1="#fff1ea", GRAD2="#e9eef7",
        OK="#13875c", INFO="#0e6ea6", WARN="#b36200", ERR="#c62828")),
    "midnight": ("🌌 Medianoche (azul)", dict(
        BG="#0d1220", PANEL="#131a2b", PANEL2="#1a2337", LINE="#27324b", TEXT="#e3eaf7", MUTED="#8594ae",
        ACCENT="#4c8dff", ACCENT2="#8ab8ff", SELECT="#1b2c4f", INPUT="#0a0e18", CANVAS="#0a0e18",
        HOVER="#212c45", ALT="#10172a", ITEMHOVER="#18213a", SCROLL="#2e3a56", SPINHOVER="#263250",
        OFF="#536079", OFFLINE="#1d2538", ARROWOFF="#3f4b63", ONACC="#0b1020", GRAD1="#0f1a35", GRAD2="#0d1220",
        OK="#6ee7b7", INFO="#7dd3fc", WARN="#ffc65c", ERR="#ff7070")),
    "arcade": ("🕹 Arcade (morado y rosa)", dict(
        BG="#130b1f", PANEL="#1b1029", PANEL2="#251736", LINE="#3a2553", TEXT="#f5ecff", MUTED="#a693c0",
        ACCENT="#ff3ea5", ACCENT2="#ffd23f", SELECT="#3d1641", INPUT="#0d0716", CANVAS="#0d0716",
        HOVER="#2f1d45", ALT="#180e26", ITEMHOVER="#22143a", SCROLL="#43295f", SPINHOVER="#352150",
        OFF="#5f4d78", OFFLINE="#2a1b3c", ARROWOFF="#54436b", ONACC="#12081c", GRAD1="#2a0d2e", GRAD2="#0f0b26",
        OK="#5ef0b0", INFO="#6fd6ff", WARN="#ffd23f", ERR="#ff6b81")),
    "forest": ("🌲 Bosque (verde)", dict(
        BG="#0f1712", PANEL="#152019", PANEL2="#1c2a21", LINE="#2a3d30", TEXT="#e6f2e9", MUTED="#8ea597",
        ACCENT="#3ecf6e", ACCENT2="#b8e05a", SELECT="#1d3a26", INPUT="#0a110c", CANVAS="#0a110c",
        HOVER="#22362a", ALT="#121c16", ITEMHOVER="#1a2a20", SCROLL="#2f4637", SPINHOVER="#27392d",
        OFF="#4f6657", OFFLINE="#1e2c23", ARROWOFF="#425a4a", ONACC="#08110b", GRAD1="#14251a", GRAD2="#0d1510",
        OK="#7cf0a8", INFO="#7dd3fc", WARN="#f5c451", ERR="#ff7a6b")),
    "contrast": ("◐ Alto contraste", dict(
        BG="#000000", PANEL="#0a0a0a", PANEL2="#161616", LINE="#8a8a8a", TEXT="#ffffff", MUTED="#d0d0d0",
        ACCENT="#ffd400", ACCENT2="#ffd400", SELECT="#3a3200", INPUT="#000000", CANVAS="#000000",
        HOVER="#262626", ALT="#0d0d0d", ITEMHOVER="#1f1f1f", SCROLL="#9a9a9a", SPINHOVER="#333333",
        OFF="#7a7a7a", OFFLINE="#444444", ARROWOFF="#6a6a6a", ONACC="#000000", GRAD1="#000000", GRAD2="#000000",
        OK="#4dff88", INFO="#66ccff", WARN="#ffd400", ERR="#ff5050")),
}
DEFAULT = "dark"
NAME = DEFAULT
CUR = dict(THEMES[DEFAULT][1])
globals().update(CUR)


def set_theme(key):
    """Cambia los colores del módulo (BG, ACCENT, CANVAS…) al tema `key`."""
    global NAME
    NAME = key if key in THEMES else DEFAULT
    CUR.clear()
    CUR.update(THEMES[NAME][1])
    globals().update(CUR)


def qss():
    """Hoja de estilo con los colores del tema actual."""
    c = dict(CUR, NAME=NAME, ARROWS="@ARROWS@")
    return """
* {{ font-size: 10pt; }}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget {{ color: {TEXT}; }}
QToolTip {{ background: {PANEL2}; color: {TEXT}; border: 1px solid {ACCENT}; padding: 6px; border-radius: 6px; }}

QMenuBar {{ background: {BG}; border-bottom: 1px solid {LINE}; }}
QMenuBar::item {{ padding: 6px 12px; background: transparent; border-radius: 6px; }}
QMenuBar::item:selected {{ background: {PANEL2}; }}
QMenu {{ background: {PANEL}; border: 1px solid {LINE}; padding: 6px; border-radius: 8px; }}
QMenu::item {{ padding: 6px 22px 6px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {ACCENT}; color: {ONACC}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 6px 4px; }}

QStatusBar {{ background: {BG}; color: {MUTED}; border-top: 1px solid {LINE}; }}

QGroupBox {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 10px; margin-top: 14px; padding: 12px 8px 8px 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {ACCENT2}; font-weight: bold; }}

QPushButton, QToolButton {{ background: {PANEL2}; border: 1px solid {LINE}; border-radius: 8px; padding: 6px 12px; }}
QPushButton:hover, QToolButton:hover {{ border-color: {ACCENT}; background: {HOVER}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {SELECT}; }}
QPushButton:checked, QToolButton:checked {{ background: {ACCENT}; color: {ONACC}; border-color: {ACCENT}; font-weight: bold; }}
QPushButton:disabled, QToolButton:disabled {{ color: {OFF}; border-color: {OFFLINE}; }}
QPushButton#primary {{ background: {ACCENT}; color: {ONACC}; border: none; font-weight: bold; }}
QPushButton#primary:hover {{ background: {ACCENT2}; }}

QToolBar {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 10px; padding: 4px; spacing: 4px; }}
QToolBar QToolButton {{ background: transparent; border: 1px solid transparent; padding: 5px 9px; }}
QToolBar QToolButton:hover {{ background: {PANEL2}; border-color: {LINE}; }}
QToolBar QToolButton:checked {{ background: {ACCENT}; color: {ONACC}; }}
QToolBar::separator {{ background: {LINE}; width: 1px; margin: 4px 6px; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {INPUT}; border: 1px solid {LINE}; border-radius: 7px; padding: 4px 6px;
    selection-background-color: {ACCENT}; selection-color: {ONACC}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: url({ARROWS}/{NAME}_down.png); width: 10px; height: 10px; margin-right: 6px; }}
QComboBox::down-arrow:hover, QComboBox::down-arrow:on {{ image: url({ARROWS}/{NAME}_down_hot.png); }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {LINE}; selection-background-color: {ACCENT}; selection-color: {ONACC}; }}
QSpinBox, QDoubleSpinBox {{ padding-right: 20px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 18px;
    border: none; border-left: 1px solid {LINE}; border-top-right-radius: 7px; background: {PANEL2}; }}
QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 18px;
    border: none; border-left: 1px solid {LINE}; border-bottom-right-radius: 7px; background: {PANEL2}; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover {{ background: {SPINHOVER}; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url({ARROWS}/{NAME}_up.png); width: 8px; height: 8px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url({ARROWS}/{NAME}_down.png); width: 8px; height: 8px; }}
QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {{ image: url({ARROWS}/{NAME}_up_hot.png); }}
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{ image: url({ARROWS}/{NAME}_down_hot.png); }}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{ image: url({ARROWS}/{NAME}_up_off.png); }}
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{ image: url({ARROWS}/{NAME}_down_off.png); }}
QToolButton#Nudge {{ padding: 0px; font-size: 9pt; }}

QListView, QListWidget, QTableWidget, QTreeWidget {{ background: {INPUT}; border: 1px solid {LINE}; border-radius: 8px;
    alternate-background-color: {ALT}; outline: none; }}
QListView::item, QListWidget::item {{ padding: 3px; border-radius: 6px; }}
QListView::item:hover, QListWidget::item:hover {{ background: {ITEMHOVER}; }}
QListView::item:selected, QListWidget::item:selected {{ background: {SELECT}; color: {TEXT};
    border-left: 3px solid {ACCENT}; }}
QTableWidget::item:selected {{ background: {SELECT}; color: {TEXT}; }}
QHeaderView::section {{ background: {PANEL2}; color: {MUTED}; border: none; border-right: 1px solid {LINE};
    padding: 5px; font-weight: bold; }}
QTableWidget {{ gridline-color: {LINE}; }}
QTableCornerButton::section {{ background: {PANEL2}; border: none; }}

QTabWidget::pane {{ border: 1px solid {LINE}; border-radius: 8px; top: -1px; background: {PANEL}; }}
QTabBar::tab {{ background: transparent; padding: 7px 14px; margin-right: 2px; border-top-left-radius: 8px;
    border-top-right-radius: 8px; color: {MUTED}; }}
QTabBar::tab:selected {{ background: {PANEL}; color: {TEXT}; border: 1px solid {LINE}; border-bottom: 2px solid {ACCENT}; }}

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SCROLL}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SCROLL}; border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {ACCENT}; }}
QSlider::groove:horizontal {{ height: 5px; background: {LINE}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {TEXT}; width: 14px; margin: -5px 0; border-radius: 7px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QCheckBox::indicator {{ border: 1px solid {LINE}; border-radius: 4px; background: {INPUT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QProgressBar {{ border: 1px solid {LINE}; border-radius: 6px; background: {INPUT}; text-align: center; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}

/* barra lateral */
#Sidebar {{ background: {PANEL}; border-right: 1px solid {LINE}; }}
#SideName {{ font-size: 13pt; font-weight: bold; }}
#SideSub {{ color: {MUTED}; }}
#NavList {{ background: transparent; border: none; }}
#NavList::item {{ padding: 10px 12px; margin: 2px 6px; border-radius: 9px; color: {MUTED}; }}
#NavList::item:hover {{ background: {PANEL2}; color: {TEXT}; }}
#NavList::item:selected {{ background: {SELECT}; color: {TEXT}; border-left: 3px solid {ACCENT}; font-weight: bold; }}
#Portrait {{ background: {INPUT}; border: 2px solid {ACCENT}; border-radius: 12px; }}

/* bienvenida */
#Welcome {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {GRAD1}, stop:0.5 {BG}, stop:1 {GRAD2}); }}
#Hero {{ font-size: 30pt; font-weight: 800; color: {TEXT}; }}
#HeroAccent {{ font-size: 30pt; font-weight: 800; color: {ACCENT}; }}
#HeroSub {{ color: {MUTED}; font-size: 11pt; }}
#Card {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 12px; }}
#Card:hover {{ border-color: {ACCENT}; }}
#CardTitle {{ font-weight: bold; font-size: 11pt; }}
#CardPath {{ color: {MUTED}; font-size: 9pt; }}

/* casillas del modo simple y otros */
#Thumb {{ background: {CANVAS}; border-radius: 6px; }}
#Pic {{ background: {CANVAS}; border: 1px solid {LINE}; border-radius: 8px; }}
#Warn {{ color: {WARN}; }}
#Error {{ color: {ERR}; }}
#SectionTitle {{ font-size: 12.5pt; font-weight: bold; color: {ACCENT2}; margin-top: 6px; }}
#CmdShow {{ background: {CANVAS}; border-radius: 10px; color: {ACCENT2}; font-size: 26pt; font-weight: bold; }}
""".format(**c)


def _arrows():
    """Dibuja las flechitas de las cajas numéricas y listas (PNG pequeños en la carpeta de ajustes)."""
    import tempfile
    from pathlib import Path
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtGui import QImage, QPainter, QPolygonF
    try:
        import i18n
        folder = Path(i18n.CONFIG_DIR) / "theme"
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        folder = Path(tempfile.gettempdir()) / "ikemen_chareditor_theme"
        folder.mkdir(parents=True, exist_ok=True)
    for name, up, col in (("up", True, CUR["TEXT"]), ("down", False, CUR["TEXT"]), ("up_hot", True, CUR["ACCENT"]),
                          ("down_hot", False, CUR["ACCENT"]), ("up_off", True, CUR["ARROWOFF"]), ("down_off", False, CUR["ARROWOFF"])):
        img = QImage(20, 20, QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(col))
        pts = [(3, 14), (17, 14), (10, 5)] if up else [(3, 6), (17, 6), (10, 15)]
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))
        p.end()
        img.save(str(folder / f"{NAME}_{name}.png"))
    return folder.as_posix()


def saved():
    try:
        import json
        import i18n
        return json.loads(i18n.SETTINGS_FILE.read_text(encoding="utf-8")).get("theme", DEFAULT)
    except Exception:
        return DEFAULT


def apply(app, key=None):
    """Pone el tema (el guardado en los ajustes si no se dice cuál). Se puede llamar otra vez para cambiarlo."""
    set_theme(key or saved())
    app.setStyle("Fusion")
    pal = QPalette()
    for role, col in ((QPalette.ColorRole.Window, CUR["BG"]), (QPalette.ColorRole.WindowText, CUR["TEXT"]),
                      (QPalette.ColorRole.Base, CUR["INPUT"]), (QPalette.ColorRole.AlternateBase, CUR["PANEL"]),
                      (QPalette.ColorRole.Text, CUR["TEXT"]), (QPalette.ColorRole.Button, CUR["PANEL2"]),
                      (QPalette.ColorRole.ButtonText, CUR["TEXT"]), (QPalette.ColorRole.Highlight, CUR["ACCENT"]),
                      (QPalette.ColorRole.HighlightedText, CUR["ONACC"]), (QPalette.ColorRole.ToolTipBase, CUR["PANEL2"]),
                      (QPalette.ColorRole.ToolTipText, CUR["TEXT"]), (QPalette.ColorRole.PlaceholderText, CUR["MUTED"]),
                      (QPalette.ColorRole.Link, CUR["ACCENT2"])):
        pal.setColor(role, QColor(col))
    app.setPalette(pal)
    try:
        arrows = _arrows()
    except Exception:
        arrows = ""
    app.setStyleSheet(qss().replace("@ARROWS@", arrows))
