"""Ventana principal."""
import json
from pathlib import Path

from PyQt6.QtGui import QAction, QActionGroup, QKeySequence
from PyQt6.QtWidgets import QDialog, QFileDialog, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget

import i18n
from core.project import Project
from core.sff import write_act
from i18n import tr
from ui.common import APP_NAME

VERSION = "0.2"


# personajes de ejemplo (carpeta «ejemplos»): nombre → de qué sirve
EXAMPLES = [("Kaito", 'combos al estilo Killer Instinct (autodobles, remate)'),
            ("Saya", 'combos al estilo Street Fighter, dibujo más detallado')]


def load_settings():
    try:
        return json.loads(i18n.SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        i18n.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cur = load_settings()
        cur.update(data)
        i18n.SETTINGS_FILE.write_text(json.dumps(cur, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        from ui.anim_tab import AnimTab
        from ui.code_tab import CodeTab
        from ui.def_tab import DefTab
        from ui.sounds_tab import SoundsTab
        from ui.move_wizard import MoveWizard
        from ui.select_tab import SelectTab
        from ui.sim_tab import SimTab
        from ui.sprites_tab import SpritesTab
        self.project = None
        self.modified_acts = []
        self.resize(1400, 880)
        from ui.shell import NavTabs, Welcome
        self.tabs = NavTabs()
        self.welcome = Welcome()
        self.welcome.newRequested.connect(self.new_character)
        self.welcome.browseRequested.connect(self.open_dialog)
        self.welcome.exampleRequested.connect(self.open_example)
        self.welcome.openRequested.connect(lambda p: self.open_project(p, ask=True))
        self.welcome.removeRequested.connect(self.remove_recent)
        self.welcome.clearRequested.connect(self.clear_recent)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.welcome)
        self.pages.addWidget(self.tabs)
        self.setCentralWidget(self.pages)
        self.def_tab = DefTab(self)
        self.sprites = SpritesTab(self)
        self.anims = AnimTab(self)
        self.code = CodeTab(self)
        self.sounds = SoundsTab(self)
        self.sim = SimTab(self)
        self.moves = MoveWizard(self)
        self.select = SelectTab(self)
        from ui.simple_mode import SimpleMode
        self.simple = SimpleMode(self)
        # modo simple
        for w, label in self.simple.nav_pages():
            self.tabs.addTab(w, label)
        self.tabs.addTab(self.select, tr('🎴 Selección'))
        # modo avanzado
        self.tabs.addTab(self.def_tab, tr('📝 Datos'))
        self.tabs.addTab(self.sprites, tr('🖼 Sprites'))
        self.tabs.addTab(self.anims, tr('🎞 Animaciones'))
        self.tabs.addTab(self.code, tr('💻 Código'))
        self.tabs.addTab(self.sim, tr('🧪 Simulador'))
        self.tabs.addTab(self.moves, tr('🥊 Movimientos'))
        self.tabs.addTab(self.sounds, tr('🔊 Sonidos'))
        self.tabs.currentChanged.connect(self.on_tab)
        # el avanzado se abre desde el menú; este botón solo sale estando en él, para volver
        self.mode_btn = QPushButton(tr('🧸  Volver al modo simple'))
        self.mode_btn.setMinimumHeight(34)
        self.mode_btn.setToolTip(tr('Simple: casillas para poner los sprites de cada cosa, sin código.'))
        self.mode_btn.clicked.connect(self.toggle_mode)
        self.tabs.add_bottom(self.mode_btn)
        save_btn = QPushButton(tr('💾  Guardar todo'))
        save_btn.setObjectName("primary")
        save_btn.setMinimumHeight(38)
        save_btn.clicked.connect(self.save_all)
        test_btn = QPushButton(tr('▶  Probar en IKEMEN GO'))
        test_btn.setMinimumHeight(36)
        test_btn.clicked.connect(self.test_in_game)
        self.tabs.add_bottom(test_btn)
        self.tabs.add_bottom(save_btn)
        for t in self.all_tabs():
            t.modifiedChanged.connect(self.update_title)
        st = load_settings()
        self.backdrop = (st.get("background", "dojo"), int(st.get("background_dim", 0)))
        self.bg_pickers = []
        self.status = QLabel()
        self.statusBar().addWidget(self.status, 1)
        self.build_menu()
        self.update_title()
        self.welcome.set_recent(load_settings().get("recent", []))
        for t in (self.sprites, self.anims, self.sim):
            self.register_picker(t.bg_picker)
        self.set_backdrop(*self.backdrop)
        self.mode = "simple"        # siempre arranca en simple; el avanzado hay que pedirlo cada vez
        self.apply_mode()

    # ---- modo simple / avanzado
    def simple_widgets(self):
        return [w for w, _l in self.simple.nav_pages()] + [self.select]

    def advanced_widgets(self):
        return [self.def_tab, self.sprites, self.anims, self.code, self.sim, self.moves, self.sounds]

    def apply_mode(self):
        simple = self.mode == "simple"
        self.tabs.set_visible(self.simple_widgets() if simple else self.advanced_widgets())
        self.mode_btn.setVisible(not simple)
        if hasattr(self, "adv_action"):
            self.adv_action.setText(tr('🧸 Volver al modo simple') if not simple else tr('🛠 Herramientas avanzadas…'))

    def toggle_mode(self):
        if self.mode == "simple":
            r = QMessageBox.warning(
                self, tr('Herramientas avanzadas'),
                tr('Las herramientas avanzadas son para quien ya conoce cómo funcionan los personajes de '
                   'IKEMEN / MUGEN: sprites, animaciones y código a mano, como en Fighter Factory.\n\n'
                   'Lo que hace el modo simple (sus animaciones y el archivo «_simple.st») se vuelve a armar cada '
                   'vez que cambias algo en el modo simple, así que lo que edites a mano ahí se pierde.\n\n'
                   '¿Entrar de todos modos?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if r != QMessageBox.StandardButton.Yes:
                return
        self.simple.flush()
        self.mode = "advanced" if self.mode == "simple" else "simple"
        self.apply_mode()
        self.on_tab(0)

    def all_tabs(self):
        return [self.def_tab, self.sprites, self.anims, self.code, self.sim, self.moves, self.select, self.sounds,
                self.simple]

    # ---- menú
    def build_menu(self):
        m = self.menuBar().addMenu(tr('&Archivo'))
        m.setToolTipsVisible(True)

        def add(menu, text, fn, key=None):
            a = QAction(text, self)
            a.triggered.connect(fn)
            if key:
                a.setShortcut(QKeySequence(key))
            menu.addAction(a)
            return a
        add(m, tr('✨ Personaje nuevo…'), self.new_character, "Ctrl+N")
        add(m, tr('📂 Abrir personaje (.def)…'), self.open_dialog, "Ctrl+O")
        em = m.addMenu(tr('🥋 Personajes de ejemplo'))
        for key, label in EXAMPLES:
            add(em, f"{key} — {tr(label)}", lambda _c=False, key=key: self.open_example(key))
        self.recent_menu = m.addMenu(tr('Recientes'))
        self.fill_recent()
        m.addSeparator()
        add(m, tr('💾 Guardar todo'), self.save_all, "Ctrl+S")
        add(m, tr('📁 Abrir la carpeta del personaje'), self.open_folder)
        m.addSeparator()
        self.adv_action = add(m, tr('🛠 Herramientas avanzadas…'), self.toggle_mode)
        self.adv_action.setToolTip(tr('Avanzado: sprites, animaciones y código a mano, como en Fighter Factory.'))
        m.addSeparator()
        add(m, tr('Salir'), self.close, "Ctrl+Q")
        lm = self.menuBar().addMenu(tr('&Idioma'))
        grp = QActionGroup(self)
        for code, name in i18n.available():
            a = QAction(name, self, checkable=True)
            a.setChecked(code == i18n.LANG)
            a.triggered.connect(lambda _c, code=code: self.set_language(code))
            grp.addAction(a)
            lm.addAction(a)
        tm = self.menuBar().addMenu(tr('&Tema'))
        from ui import theme
        tgrp = QActionGroup(self)
        for key, (name, _c) in theme.THEMES.items():
            a = QAction(tr(name), self, checkable=True)
            a.setChecked(key == theme.NAME)
            a.triggered.connect(lambda _c, key=key: self.set_theme(key))
            tgrp.addAction(a)
            tm.addAction(a)
        hm = self.menuBar().addMenu(tr('Ay&uda'))
        add(hm, tr('Acerca de…'), self.about)

    def fill_recent(self):
        self.recent_menu.clear()
        recent = load_settings().get("recent", [])[:10]
        for p in recent:
            a = QAction(p, self)
            a.triggered.connect(lambda _c, p=p: self.open_project(p))
            self.recent_menu.addAction(a)
        if recent:
            self.recent_menu.addSeparator()
            a = QAction(tr('🧹 Limpiar la lista'), self)
            a.triggered.connect(self.clear_recent)
            self.recent_menu.addAction(a)
        self.recent_menu.setEnabled(bool(recent))

    def remove_recent(self, path):
        """Lo quita de «Recientes» (el personaje no se toca)."""
        rec = [r for r in load_settings().get("recent", []) if r != path]
        save_settings({"recent": rec})
        self.welcome.set_recent(rec)
        self.fill_recent()

    def clear_recent(self):
        if QMessageBox.question(self, APP_NAME, tr('¿Quitar todos los personajes de «Recientes»? No se borra '
                                                   'ninguno, solo la lista.')) != QMessageBox.StandardButton.Yes:
            return
        save_settings({"recent": []})
        self.welcome.set_recent([])
        self.fill_recent()

    def set_language(self, code):
        save_settings({"language": code})
        QMessageBox.information(self, APP_NAME, tr('El idioma cambia al volver a abrir el programa.'))

    def set_theme(self, key):
        """Cambia los colores del editor al momento (y se queda guardado)."""
        from PyQt6.QtWidgets import QApplication
        from ui import theme
        save_settings({"theme": key})
        app = QApplication.instance()
        theme.apply(app, key)
        try:
            self.simple.refresh_theme()
        except Exception:
            pass
        for w in app.allWidgets():
            w.update()

    def about(self):
        QMessageBox.about(self, APP_NAME, f"<b>{APP_NAME}</b> {VERSION}<br><br>" + tr(
            'Editor de personajes para IKEMEN GO (y MUGEN): sprites, paletas, animaciones con cajas de golpe, '
            'código, sonidos y datos del personaje.'))

    # ---- abrir / guardar
    def open_dialog(self):
        if not self.confirm_discard():
            return
        start = load_settings().get("last_dir", str(Path.home()))
        p, _ = QFileDialog.getOpenFileName(self, tr('Abrir personaje'), start, tr('Personaje (*.def)'))
        if p:
            self.open_project(p)

    def open_project(self, path, ask=False):
        if ask and not self.confirm_discard():
            return
        try:
            proj = Project(path)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, tr('No pude abrir el personaje: {0}').format(e))
            return
        self.project = proj
        self.modified_acts = []
        rec = [str(Path(path))] + [r for r in load_settings().get("recent", []) if r != str(Path(path))]
        save_settings({"recent": rec[:10], "last_dir": str(Path(path).parent)})
        self.fill_recent()
        self.pages.setCurrentWidget(self.tabs)
        for t in self.all_tabs():
            try:
                t.load()
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.warning(self, APP_NAME, tr('Problema al cargar una parte del personaje: {0}').format(e))
        self.update_title()
        self.refresh_header()
        self.set_backdrop(*self.backdrop)
        self.status.setText(str(proj.def_path))
        self.repair_template_bug()

    def repair_template_bug(self):
        """Los personajes HD hechos con la plantilla vieja tenían la fricción multiplicada (se teletransportaban
        al caminar o al caer de un salto). Se arregla solo al abrirlos."""
        p = self.project
        f = p.file("cns") if p else None
        if f is None or f.suffix.lower() == ".zss":
            return
        try:
            from core.simulate import parse_constants
            from core.template import fix_scaled_constants
            from ui.simple_mode import set_const, set_doc_text
            doc = self.code.get_open(f).doc
            text = doc.toPlainText()
            fixes = fix_scaled_constants(parse_constants(text), p.localcoord()[0] / 320)
            if not fixes:
                return
            for sec, key, i, v in fixes:
                text = set_const(text, sec, key, i, v)
            set_doc_text(doc, text)
            self.simple.motion.forget()
            self.update_title()
            QMessageBox.information(self, APP_NAME, tr(
                'Arreglé un error de la plantilla HD en este personaje: la fricción estaba multiplicada y por eso '
                'se teletransportaba al caminar o al caer de un salto. Guarda (Ctrl+S) para que quede arreglado.'))
        except Exception:
            import traceback
            traceback.print_exc()

    # ---- fondo de las vistas
    def backdrop_views(self):
        return [self.sprites.view, self.anims.view, self.sim.view]

    def register_picker(self, picker):
        self.bg_pickers.append(picker)
        picker.fill(self.backdrop[0])
        picker.dim.blockSignals(True)
        picker.dim.setValue(self.backdrop[1])
        picker.dim.blockSignals(False)

    def set_backdrop(self, key, dim=None):
        from ui import backgrounds
        if key.startswith("file:"):
            from PyQt6.QtGui import QImage
            if QImage(key[5:]).isNull():
                key = "checker"
        dim = self.backdrop[1] if dim is None else int(dim)
        self.backdrop = (key, dim)
        save_settings({"background": key, "background_dim": dim})
        for p in self.bg_pickers:
            p.fill(key)
            p.dim.blockSignals(True)
            p.dim.setValue(dim)
            p.dim.blockSignals(False)
        lc = self.project.localcoord() if self.project else (320, 240)
        rect = backgrounds.scene_rect(lc)
        for v in self.backdrop_views():
            v.set_backdrop(key, rect, dim)

    def refresh_header(self):
        p = self.project
        if not p:
            return
        pm = None
        try:
            from PyQt6.QtGui import QPixmap
            from ui.common import sprite_qimage
            s = p.sff.find(9000, 1) or p.sff.find(9000, 0)
            if s is not None:
                pm = QPixmap.fromImage(sprite_qimage(p.sff, s))
        except Exception:
            pm = None
        lw, lh = p.localcoord()
        author = p.defs.get("Info", "author")
        self.tabs.set_character(p.name(), (tr('por {0}').format(author) + " · " if author else "") + f"{lw}×{lh}", pm)

    def on_tab(self, _i):
        w = self.tabs.currentWidget()
        if hasattr(w, "activated"):
            w.activated()

    def is_modified(self):
        return bool(self.modified_acts) or any(t.is_modified() for t in self.all_tabs())

    def update_title(self):
        name = self.project.name() if self.project else ""
        star = "● " if self.project and self.is_modified() else ""
        self.setWindowTitle(f"{star}{name + ' — ' if name else ''}{APP_NAME}")

    def act_modified(self, pal):
        if pal is not None and not any(pal is p for p in self.modified_acts):
            self.modified_acts.append(pal)
        self.update_title()

    def save_all(self):
        if not self.project:
            return True
        self.simple.flush()
        ok = True
        for t in self.all_tabs():
            if t.is_modified():
                ok = t.save() and ok
        # paletas .act cambiadas
        for n, v, pal in self.project.acts or []:
            if any(pal is p for p in self.modified_acts):
                from core.textio import ci_find
                path = ci_find(self.project.folder, v) or (self.project.folder / v)
                self.project.backup(path)
                write_act(path, pal)
        self.modified_acts = []
        if self.def_tab.is_modified() or self.project.defs_dirty:
            self.def_tab.save()
        self.update_title()
        if ok:
            self.status.setText(tr('✅ Guardado: {0}').format(self.project.folder))
        return ok

    def confirm_discard(self):
        if not self.project or not self.is_modified():
            return True
        r = QMessageBox.question(self, APP_NAME, tr('Hay cambios sin guardar. ¿Guardarlos?'),
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self.save_all()
        return r == QMessageBox.StandardButton.Discard

    def closeEvent(self, e):
        if self.confirm_discard():
            e.accept()
        else:
            e.ignore()

    def open_folder(self):
        if self.project:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.project.folder)))

    def open_example(self, key="Kaito"):
        """Copia un personaje de ejemplo (hecho con el modo simple) a la carpeta que escojas y lo abre."""
        import sys
        from pathlib import Path
        if not self.confirm_discard():
            return
        src = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "ejemplos" / key
        if not (src / f"{key}.def").is_file():
            QMessageBox.warning(self, APP_NAME, tr('No encontré el personaje de ejemplo (carpeta «ejemplos»).'))
            return
        from ui.newchar import ExampleDialog
        dlg = ExampleDialog(self, key)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, folder, author, dest = dlg.result_
        from core.char_copy import copy_character
        try:
            new_def = copy_character(src / f"{key}.def", dest, folder, name if name != key else None, author or None)
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, tr('No pude copiarlo: {0}').format(e))
            return
        self.open_project(new_def)
        about = {
            "Kaito": tr('Kaito está hecho completo con el modo simple: todas sus animaciones, golpes, agarre, especiales '
                        '(bola de energía ↓↘→+puño, gancho →↓↘+puño, patada voladora ↓↙←+patada), súper (↓↘→↓↘→+puño), '
                        'remate y combos al estilo Killer Instinct. Mira cada pestaña del modo simple para ver cómo está '
                        'hecho, y pruébalo con «▶ Probar en IKEMEN GO».'),
            "Saya": tr('Saya está hecha completa con el modo simple, con combos al estilo Street Fighter (sin '
                       'autodobles): llama ↓↘→+puño, patada que sube →↓↘+patada, patadas girando ↓↙←+patada y súper '
                       '↓↘→↓↘→+patada. Prueba: agachada + patada débil dos veces y enseguida ↓↙←+patada. La lista '
                       'completa está en LEEME.txt, en su carpeta.'),
        }.get(key)
        if about:
            QMessageBox.information(self, APP_NAME, about)

    def new_character(self):
        if not self.confirm_discard():
            return
        from ui.newchar import NewCharDialog
        dlg = NewCharDialog(self)
        if dlg.exec() and dlg.created:
            self.open_project(dlg.created)

    # ---- probar en el juego
    def test_in_game(self):
        if not self.project:
            return
        from ui.testgame import test_character
        if self.is_modified():
            r = QMessageBox.question(self, APP_NAME, tr('Hay cambios sin guardar. ¿Guardar antes de probar?'))
            if r == QMessageBox.StandardButton.Yes:
                self.save_all()
        test_character(self, self.project)
