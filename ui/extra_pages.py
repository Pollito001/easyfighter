"""Páginas del modo simple: «🤖 IA (CPU)» y «🏁 Revisar y compartir»."""
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSlider, QTableWidget,
    QTableWidgetItem,
)

from core import finish
from core import simple_gen as sg
from i18n import tr
from ui import theme
from ui.common import APP_NAME
from ui.simple_mode import Page, card, muted

AGGR_NAMES = {1: 'Muy tranquila', 3: 'Tranquila', 5: 'Normal', 7: 'Agresiva', 9: 'Muy agresiva'}


# ---------------------------------------------------------------- IA de la computadora
class AIPage(Page):
    def __init__(self, sm):
        super().__init__(sm, tr('🤖 IA (CPU)'), tr(
            'Cómo pelea tu personaje cuando lo maneja la computadora (en arcade o contra el CPU). Sin esto, la '
            'computadora aprieta comandos casi al azar. A ti, cuando juegas con él, no te cambia nada.'))
        self._binding = True
        box, v = card(tr('🤖 La computadora'))
        self.on = QCheckBox(tr('Usar la IA de EasyFighter'))
        self.on.setToolTip(tr('La computadora usa los especiales según la distancia, hace combos y usa el súper '
                              'cuando tiene poder. La dificultad del juego (nivel de IA) la hace más o menos lista.'))
        self.on.toggled.connect(self.on_change)
        v.addWidget(self.on)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Agresividad:')))
        self.aggr = QSlider(Qt.Orientation.Horizontal)
        self.aggr.setRange(1, 10)
        self.aggr.setPageStep(1)
        self.aggr.setToolTip(tr('Qué tanto ataca: tranquila espera y pega de vez en cuando; agresiva no para.'))
        self.aggr.valueChanged.connect(self.on_change)
        row.addWidget(self.aggr, 1)
        self.aggr_lbl = QLabel()
        self.aggr_lbl.setMinimumWidth(120)
        row.addWidget(self.aggr_lbl)
        v.addLayout(row)
        self.combos = QCheckBox(tr('Hace combos (cancela golpes que pegan en especiales)'))
        self.combos.toggled.connect(self.on_change)
        v.addWidget(self.combos)
        self.supers = QCheckBox(tr('Usa el súper cuando tiene poder'))
        self.supers.toggled.connect(self.on_change)
        v.addWidget(self.supers)
        self.lay.addWidget(box)
        box, v = card(tr('🔥 Cuándo usa cada especial'), tr(
            '«Automático» escoge según lo que hace: los proyectiles de lejos, los ganchos contra un rival que '
            'salta, los golpes de cerca…'))
        self.moves_box = QFrame()
        self.moves_grid = QGridLayout(self.moves_box)
        self.moves_grid.setContentsMargins(0, 0, 0, 0)
        self.moves_grid.setHorizontalSpacing(14)
        self.moves_grid.setColumnStretch(1, 1)
        v.addWidget(self.moves_box)
        self.lay.addWidget(box)
        self.lay.addStretch(1)
        self._binding = False

    def ai(self):
        return self.sm.cfg.setdefault("ai", {})

    def bind(self, cfg):
        self._binding = True
        ai = cfg.setdefault("ai", {})
        self.on.setChecked(bool(ai.get("on", False)))
        self.aggr.setValue(int(ai.get("aggr", 5)))
        self.combos.setChecked(bool(ai.get("combos", True)))
        self.supers.setChecked(bool(ai.get("supers", True)))
        self.update_label()
        self.fill_moves()
        self.enable()
        self._binding = False

    def showEvent(self, e):
        super().showEvent(e)
        self._binding = True
        self.fill_moves()
        self.enable()
        self._binding = False

    def update_label(self):
        v = self.aggr.value()
        name = AGGR_NAMES.get(v) or AGGR_NAMES.get(v - 1) or ""
        self.aggr_lbl.setText(f"{v} · {tr(name)}")

    def enable(self):
        on = self.on.isChecked()
        for w in (self.aggr, self.combos, self.supers, self.moves_box):
            w.setEnabled(on)

    def on_change(self, *_a):
        self.update_label()
        self.enable()
        if self._binding:
            return
        ai = self.ai()
        ai["on"] = self.on.isChecked()
        ai["aggr"] = self.aggr.value()
        ai["combos"] = self.combos.isChecked()
        ai["supers"] = self.supers.isChecked()
        self.sm.moves_changed()

    def fill_moves(self):
        g = self.moves_grid
        while g.count():
            it = g.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        moves = [(i, sp) for i, sp in enumerate(self.sm.cfg.get("specials", []))
                 if sp.get("type") != "converted" and sp.get("kind") != "ender"]
        if not moves:
            g.addWidget(muted(tr('Todavía no tienes especiales ni súper (página «🔥 Especiales y súper»).')), 0, 0, 1, 2)
            return
        by = self.ai().setdefault("moves", {})
        names = dict(sg.AI_RANGES)
        for r, (i, sp) in enumerate(moves):
            icon = "⚡" if sp.get("kind") == "super" else "🔥"
            lab = QLabel(f"{icon} {sp.get('name') or '?'}")
            lab.setMinimumWidth(170)
            c = QComboBox()
            for key, text in sg.AI_RANGES:
                t = tr(text)
                if key == "auto":
                    t = tr('Automático ({0})').format(tr(names[sg.ai_auto_range(sp)]).lower())
                c.addItem(t, key)
            key_ = sp.get("uid") or str(i)
            c.setCurrentIndex(max(0, c.findData(by.get(key_, "auto"))))
            c.currentIndexChanged.connect(lambda _x, c=c, key_=key_: self.on_move(key_, c.currentData()))
            g.addWidget(lab, r, 0)
            g.addWidget(c, r, 1)

    def on_move(self, key, val):
        if self._binding:
            return
        by = self.ai().setdefault("moves", {})
        if val == "auto":
            by.pop(key, None)
        else:
            by[key] = val
        self.sm.moves_changed()


# ---------------------------------------------------------------- revisar y compartir
def _fmt_adv(v):
    if v is None:
        return "—"
    return f"+{v}" if v > 0 else str(v)


class FinishPage(Page):
    def __init__(self, sm):
        super().__init__(sm, tr('🏁 Revisar y compartir'), tr(
            'Antes de compartir tu personaje: revisa si le falta algo, mira los datos de cuadros de cada golpe, '
            'guarda versiones para poder volver atrás y arma un .zip limpio para pasárselo a otros.'))
        # ---- revisar
        box, v = card(tr('✅ Revisar el personaje'), tr(
            'Busca animaciones vacías, especiales a medias, comandos repetidos, sonidos que faltan y errores en '
            'el código. Doble clic en un problema para ir a arreglarlo.'))
        row = QHBoxLayout()
        b = QPushButton(tr('🔍 Revisar ahora'))
        b.setObjectName("primary")
        b.clicked.connect(self.run_check)
        row.addWidget(b)
        self.check_sum = QLabel()
        row.addWidget(self.check_sum, 1)
        v.addLayout(row)
        self.issues = QListWidget()
        self.issues.setMinimumHeight(150)
        self.issues.itemDoubleClicked.connect(self.goto_issue)
        v.addWidget(self.issues)
        self.lay.addWidget(box)
        # ---- datos de cuadros
        box, v = card(tr('📊 Datos de cuadros'), tr(
            'En ticks (60 = 1 segundo). «Sale en»: cuándo empieza a pegar · «Pega»: cuánto dura pegando · '
            '«Recupera»: lo que tarda después · «Al pegar» / «Bloqueado»: ventaja (+) o desventaja (−) cuando '
            'termina, aproximada. Se calcula de lo guardado: guarda antes de mirar.'))
        row = QHBoxLayout()
        b = QPushButton(tr('📊 Calcular'))
        b.clicked.connect(self.run_frames)
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([tr('Movimiento'), tr('Sale en'), tr('Pega'), tr('Recupera'),
                                              tr('Total'), tr('Al pegar'), tr('Bloqueado')])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(220)
        v.addWidget(self.table)
        self.lay.addWidget(box)
        # ---- historial
        box, v = card(tr('🕘 Historial de versiones'), tr(
            'Fotos de cómo estaba tu personaje. Si algo se daña, vuelves a una. Se guardan en la carpeta '
            '«_editor_history» del personaje (no van en el .zip para compartir).'))
        self.auto_snap = QCheckBox(tr('Guardar una foto sola al guardar (como mucho cada 15 minutos; se quedan las '
                                      '20 más nuevas)'))
        self.auto_snap.toggled.connect(self.on_auto_snap)
        v.addWidget(self.auto_snap)
        self.snaps = QListWidget()
        self.snaps.setMinimumHeight(130)
        v.addWidget(self.snaps)
        row = QHBoxLayout()
        for txt, fn in ((tr('📸 Guardar una foto ahora'), self.take_snap), (tr('↩ Volver a esta'), self.restore_snap),
                        (tr('📂 Abrir la carpeta'), self.open_snap), (tr('🗑 Borrar'), self.delete_snap)):
            bb = QPushButton(txt)
            bb.clicked.connect(fn)
            row.addWidget(bb)
        row.addStretch(1)
        v.addLayout(row)
        self.lay.addWidget(box)
        # ---- compartir
        box, v = card(tr('📦 Compartir'), tr(
            'Arma un .zip con la carpeta del personaje lista para copiar a «chars» de IKEMEN GO, sin las copias '
            'del editor, y con un archivo «COMANDOS.txt» con sus movimientos.'))
        row = QHBoxLayout()
        b = QPushButton(tr('📦 Crear el .zip…'))
        b.setObjectName("primary")
        b.clicked.connect(self.make_zip)
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.lay.addWidget(box)
        self.lay.addStretch(1)

    def bind(self, cfg):
        from ui.mainwindow import load_settings
        self.auto_snap.blockSignals(True)
        self.auto_snap.setChecked(bool(load_settings().get("auto_snapshot", True)))
        self.auto_snap.blockSignals(False)
        self.issues.clear()
        self.check_sum.setText("")
        self.table.setRowCount(0)
        self.fill_snaps()

    def showEvent(self, e):
        super().showEvent(e)
        self.fill_snaps()

    # ---- revisar
    def run_check(self):
        sm = self.sm
        p = sm.main.project
        self.issues.clear()
        if not p:
            return
        sm.flush()
        found = []    # (gravedad, texto, página, qué)

        def add(level, text, page=None, what=None):
            found.append((level, text, page, what))
        # animaciones y golpes vacíos
        for pg in (sm.moves_page, sm.attacks_page, sm.hurt_page):
            for _lab, _text, cards in getattr(pg, "_sections", []):
                for c in cards:
                    if getattr(c, "state", None) == "empty":
                        add("error", tr('Falta la animación: «{0}»').format(c.title_lbl.text()), pg, c)
        # especiales
        seen = {}
        for sp in sm.cfg.get("specials", []):
            name = sp.get("name") or "?"
            typ = sp.get("type", "proj")
            if typ == "converted":
                continue
            if not sg._frames(sp):
                add("error", tr('«{0}» no tiene animación (no sale en el juego).').format(name), sm.specials_page, sp)
                continue
            if typ in ("proj", "helper") and not sg._frames(sp.get("proj") or {}):
                add("error", tr('«{0}» no tiene la animación del proyectil o del ayudante.').format(name),
                    sm.specials_page, sp)
            key = (sp.get("motion"), sp.get("family"), sp.get("kind") == "super")
            if sp.get("kind") != "ender" and not str(sp.get("motion", "")).startswith("custom"):
                if key in seen:
                    add("aviso", tr('«{0}» y «{1}» tienen el mismo comando: solo sale uno.').format(seen[key], name),
                        sm.specials_page, sp)
                else:
                    seen[key] = name
        # voces que apuntan a sonidos que ya no están
        have = {(s.group, s.number) for s in p.snd.sounds}
        vals = [(k, v) for k, v in sm.cfg.get("voices", {}).items() if isinstance(v, list)]
        vals += [(sp.get("name"), sp.get("voice")) for sp in sm.cfg.get("specials", [])
                 if isinstance(sp.get("voice"), list)]
        vals += [(tr('combo de {0}').format(x.get("hits")), x.get("snd")) for x in sm.cfg.get("combo_voices", [])
                 if isinstance(x.get("snd"), list)]
        for k_, v_ in vals:
            if tuple(v_) not in have:
                add("aviso", tr('La voz «{0}» usa el sonido {1}, {2}, que ya no está.').format(k_, v_[0], v_[1]),
                    sm.voices_page)
        # pantalla de selección
        if p.sff.find(9000, 0) is None:
            add("aviso", tr('No tiene la cara chiquita para la pantalla de selección (9000, 0).'), sm.main.select)
        if p.sff.find(9000, 1) is None:
            add("aviso", tr('No tiene el retrato grande (9000, 1).'), sm.main.select)
        # números que no se pudieron poner
        for prob in getattr(sm, "last_problems", []) or []:
            add("error", tr('No encontré números libres para: {0}').format(prob))
        # el código
        from core.codeinfo import check
        from core.textio import read_text
        for _k, path in p.code_files():
            if path.suffix.lower() not in (".cns", ".cmd", ".st", ".air") or path.suffix.lower() == ".air":
                continue
            of = sm.main.code.open.get(str(path))
            try:
                text = of.doc.toPlainText() if of else read_text(path)[0]
            except OSError:
                continue
            kind = "cmd" if path.suffix.lower() == ".cmd" else "cns"
            for ln, level, msg in check(text, kind):
                if level == "error":
                    add("error", f"{path.name}:{ln}: {msg}", sm.main.code, (path, ln))
        # resultado
        errs = sum(1 for x in found if x[0] == "error")
        warns = len(found) - errs
        if not found:
            self.check_sum.setText(f"<span style='color:{theme.OK}'>" + tr('✅ No encontré problemas.') + "</span>")
            return
        self.check_sum.setText(tr('{0} problema(s) y {1} aviso(s)').format(errs, warns))
        for level, text, page, what in sorted(found, key=lambda x: x[0] != "error"):
            it = QListWidgetItem(("❌ " if level == "error" else "⚠ ") + text)
            it.setForeground(QColor(theme.WARN if level != "error" else "#ff6b6b"))
            it.setData(Qt.ItemDataRole.UserRole, (page, what))
            self.issues.addItem(it)

    def goto_issue(self, it):
        page, what = it.data(Qt.ItemDataRole.UserRole) or (None, None)
        if page is None:
            return
        main = self.sm.main
        if page is main.code and isinstance(what, tuple):
            if getattr(main, "mode", "simple") == "simple":
                main.toggle_mode()          # pregunta antes de abrir las herramientas avanzadas
                if main.mode == "simple":
                    return
            main.tabs.setCurrentWidget(main.code)
            code = main.code
            code.get_open(what[0])
            for i in range(code.files.count()):
                if code.files.item(i).data(Qt.ItemDataRole.UserRole) == str(Path(what[0])):
                    code.files.setCurrentRow(i)
                    break
            try:
                code.editor.go_line(int(what[1]))
            except Exception:
                pass
            return
        main.tabs.setCurrentWidget(page)
        if hasattr(what, "set_open"):
            what.set_open(True)
            QTimer.singleShot(60, lambda: page.ensureWidgetVisible(what, 50, 50))
        elif isinstance(what, dict) and hasattr(page, "cards"):
            for c in page.cards:
                if getattr(c, "sp", None) is what:
                    c.set_open(True)
                    QTimer.singleShot(60, lambda c=c: page.ensureWidgetVisible(c, 50, 50))

    # ---- datos de cuadros
    def run_frames(self):
        sm = self.sm
        p = sm.main.project
        self.table.setRowCount(0)
        if not p:
            return
        sm.flush()
        st = sm.st_path() if sg.has_moves(sm.cfg) else None
        if st is None:
            return
        of = sm.main.code.get_open(st)
        rows = finish.frame_data(of.doc.toPlainText(), p.air)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            name = row["name"] + ("  ⤵" if row["knockdown"] else "") + ("  🎯" if row["kind"] == "projectile" else "") + \
                ("  🧍" if row["kind"] == "helper" else "")
            vals = [name, row["startup"], row["active"], row["recovery"], row["total"],
                    _fmt_adv(row["on_hit"]) if not row["knockdown"] else tr('lo tumba'), _fmt_adv(row["on_block"])]
            for c, v in enumerate(vals):
                it = QTableWidgetItem("—" if v is None else str(v))
                if c >= 5 and isinstance(v, str) and v.startswith("-"):
                    it.setForeground(QColor("#ff8a8a"))
                elif c >= 5 and isinstance(v, str) and v.startswith("+"):
                    it.setForeground(QColor(theme.OK))
                if c:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    # ---- historial
    def folder(self):
        p = self.sm.main.project
        return p.folder if p else None

    def fill_snaps(self):
        self.snaps.clear()
        f = self.folder()
        if f is None:
            return
        for d, when, note in finish.snapshots(f):
            it = QListWidgetItem(f"🕘 {when:%Y-%m-%d %H:%M:%S}" + (f"  —  {note}" if note else ""))
            it.setData(Qt.ItemDataRole.UserRole, str(d))
            self.snaps.addItem(it)
        if not self.snaps.count():
            it = QListWidgetItem(tr('Todavía no hay fotos.'))
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.snaps.addItem(it)

    def on_auto_snap(self, on):
        from ui.mainwindow import save_settings
        save_settings({"auto_snapshot": bool(on)})

    def take_snap(self):
        f = self.folder()
        if f is None:
            return
        main = self.sm.main
        if main.is_modified() and QMessageBox.question(self, APP_NAME, tr(
                'Hay cambios sin guardar. ¿Guardarlos antes de la foto?')) == QMessageBox.StandardButton.Yes:
            main.save_all()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            finish.snapshot(f, tr('A mano'))
            finish.prune(f, 20)
        finally:
            QApplication.restoreOverrideCursor()
        self.fill_snaps()

    def current_snap(self):
        it = self.snaps.currentItem()
        d = it.data(Qt.ItemDataRole.UserRole) if it is not None else None
        if not d:
            QMessageBox.information(self, APP_NAME, tr('Escoge una foto de la lista.'))
            return None
        return Path(d)

    def restore_snap(self):
        d = self.current_snap()
        f = self.folder()
        if d is None or f is None:
            return
        if QMessageBox.question(self, APP_NAME, tr(
                '¿Volver a la foto del {0}? Antes se guarda otra foto de cómo está ahora, así que puedes '
                'deshacerlo. Los cambios sin guardar se pierden.').format(d.name)) != QMessageBox.StandardButton.Yes:
            return
        main = self.sm.main
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            finish.restore(f, d)
        finally:
            QApplication.restoreOverrideCursor()
        main.open_project(str(main.project.def_path))
        main.tabs.setCurrentWidget(self)
        self.fill_snaps()

    def open_snap(self):
        d = self.current_snap()
        if d is not None:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def delete_snap(self):
        d = self.current_snap()
        if d is None:
            return
        if QMessageBox.question(self, APP_NAME, tr('¿Borrar la foto del {0}?').format(d.name)) != \
                QMessageBox.StandardButton.Yes:
            return
        import shutil
        shutil.rmtree(d, ignore_errors=True)
        self.fill_snaps()

    # ---- compartir
    def commands_text(self):
        sm = self.sm
        p = sm.main.project
        cfg = sm.cfg
        name = p.defs.get("Info", "displayname") or p.defs.get("Info", "name") or p.folder.name
        author = p.defs.get("Info", "author") or ""
        motions = {k: t for k, t, _c in sg.MOTIONS}
        lines = [f"{name}" + (f" — {author}" if author else ""), "=" * 40, "",
                 tr('Botones: x y z = puños (débil, medio, fuerte) · a b c = patadas · s = Start'), ""]
        sp_lines = []
        for sp in cfg.get("specials", []):
            if sp.get("type") == "converted" or not sg._frames(sp):
                continue
            fam = dict((k, b) for k, _t, b in sg.FAMILIES).get(sp.get("family", "punch"), ["x", "y", "z"])
            btn = "/".join(fam)
            m = motions.get(sp.get("motion"), str(sp.get("motion") or ""))
            m = tr(m).replace(tr('botón'), btn)
            extra = ""
            if sp.get("kind") == "super":
                extra = "  (" + tr('{0} barra(s)').format(int(sg.spec(sp, "power_cost"))) + ")"
            elif sp.get("kind") == "ender":
                extra = "  (" + tr('remate: después de un autodoble') + ")"
            icon = {"super": "⚡", "ender": "💥"}.get(sp.get("kind"), "🔥")
            sp_lines.append(f"{icon} {sp.get('name') or '?'}: {m}{extra}")
        if sp_lines:
            lines += [tr('Especiales y súper:')] + sp_lines + [""]
        other = []
        th = cfg.get("throw") or {}
        if sg._frames(th) and not sg.is_off(cfg, "throw"):
            other.append(tr('Agarre: → + {0} (de cerca)').format(th.get("button", "y")))
        ath = cfg.get("air_throw") or {}
        if sg._frames(ath):
            other.append(tr('Agarre en el aire: → + {0} (en el aire, cerca)').format(ath.get("button", "y")))
        if sg.own_frames(cfg, "air_dash")[0]:
            other.append(tr('Dash en el aire: → → o ← ← (en el aire)'))
        if sg.own_frames(cfg, "taunt")[0]:
            other.append(tr('Burla: s (Start)'))
        if not sg.is_off(cfg, "run"):
            other.append(tr('Correr: → →'))
        if other:
            lines += [tr('Otros:')] + other + [""]
        pals = sum(1 for k, v in p.defs.keys("Files") if k.lower().startswith("pal") and v)
        if pals:
            lines += [tr('Colores: {0} (se escogen con el botón al elegirlo)').format(pals), ""]
        lines += [tr('Hecho con EasyFighter.')]
        return "\n".join(lines) + "\n"

    def make_zip(self):
        sm = self.sm
        main = sm.main
        p = main.project
        if not p:
            return
        if main.is_modified():
            r = QMessageBox.question(self, APP_NAME, tr('Hay cambios sin guardar. ¿Guardarlos antes de armar el .zip?'))
            if r == QMessageBox.StandardButton.Yes:
                main.save_all()
        default = str(Path.home() / f"{p.folder.name}.zip")
        out, _ = QFileDialog.getSaveFileName(self, tr('Guardar el .zip'), default, "ZIP (*.zip)")
        if not out:
            return
        if not out.lower().endswith(".zip"):
            out += ".zip"
        try:
            finish.make_zip(p.folder, out, {"COMANDOS.txt": self.commands_text()})
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, tr('No pude crear el .zip: {0}').format(e))
            return
        QMessageBox.information(self, APP_NAME, tr('✅ Listo: {0}\n\nPara jugarlo, se descomprime dentro de la '
                                                  'carpeta «chars» de IKEMEN GO y se agrega a data/select.def.')
                                .format(out))
