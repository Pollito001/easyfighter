"""Asistente de movimientos: arma el comando (.cmd), el estado con su golpe (.cns/.st) y la animación (.air)."""
import re

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFontDatabase, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from core.air import Action, Frame
from core.boxes import auto_boxes, hit_box  # noqa: F401 (las usan otras partes)
from i18n import tr
from ui.common import APP_NAME

MOTIONS = [
    ('↓↘→ + botón (bola de fuego)', "~D, DF, F, {b}", "QCF"),
    ('→↓↘ + botón (gancho)', "~F, D, DF, {b}", "DP"),
    ('↓↙← + botón', "~D, DB, B, {b}", "QCB"),
    ('←↙↓↘→ + botón (medio círculo)', "~B, DB, D, DF, F, {b}", "HCF"),
    ('↓↓ + botón', "~D, D, {b}", "DD"),
    ('→→ + botón', "~F, F, {b}", "FF"),
    ('Cargar ← y luego → + botón', "~30$B, F, {b}", "CHG"),
    ('↓↘→↓↘→ + botón (súper)', "~D, DF, F, D, DF, F, {b}", "QCF2"),
    ('Solo el botón', "{b}", "BTN"),
]
BUTTONS = ["a", "b", "c", "x", "y", "z", "a+b", "x+y", "a+x"]
KINDS = [('Especial', "special"), ('Súper (gasta 1 barra)', "super"), ('Golpe normal', "normal")]
HEIGHTS = [('Alto (se cubre de pie)', "High", "S, SA", "MA"), ('Bajo (se cubre agachado)', "Low", "C, SA", "L"),
           ('Medio / desde arriba (se cubre de pie)', "High", "S, SA", "H")]


class MoveWizard(QWidget):
    modifiedChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        lay = QHBoxLayout(self)
        split = QSplitter()
        lay.addWidget(split)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_w = QWidget()
        scroll.setWidget(form_w)
        fl = QVBoxLayout(form_w)
        intro = QLabel(tr('Crea un movimiento completo: el comando, el estado con su golpe y la animación con sus '
                          'cajas. Después lo puedes ajustar en Código y Animaciones, y probarlo en el Simulador.'))
        intro.setWordWrap(True)
        fl.addWidget(intro)

        g = QGroupBox(tr('Movimiento'))
        f = QFormLayout(g)
        self.name = QLineEdit(tr('Bola de fuego'))
        self.kind = QComboBox()
        for txt, v in KINDS:
            self.kind.addItem(tr(txt), v)
        self.motion = QComboBox()
        for txt, cmd, _short in MOTIONS:
            self.motion.addItem(tr(txt), cmd)
        self.button = QComboBox()
        self.button.addItems(BUTTONS)
        self.button.setEditable(True)
        self.pos = QComboBox()
        for txt, v in ((tr('De pie'), "S"), (tr('Agachado'), "C"), (tr('En el aire'), "A")):
            self.pos.addItem(txt, v)
        self.stateno = QSpinBox()
        self.stateno.setRange(0, 999999)
        self.cancel = QCheckBox(tr('Se puede hacer cancelando un golpe normal que conectó'))
        self.cancel.setChecked(True)
        f.addRow(tr('Nombre:'), self.name)
        f.addRow(tr('Tipo:'), self.kind)
        f.addRow(tr('Comando:'), self.motion)
        f.addRow(tr('Botón:'), self.button)
        f.addRow(tr('Se hace:'), self.pos)
        f.addRow(tr('Número de estado:'), self.stateno)
        f.addRow(self.cancel)
        fl.addWidget(g)

        g = QGroupBox(tr('Animación'))
        f = QFormLayout(g)
        self.group = QComboBox()
        self.frame_time = QSpinBox()
        self.frame_time.setRange(1, 60)
        self.frame_time.setValue(4)
        self.hit_frame = QSpinBox()
        self.hit_frame.setRange(1, 99)
        self.hit_frame.setValue(3)
        self.action_no = QSpinBox()
        self.action_no.setRange(0, 999999)
        f.addRow(tr('Grupo de sprites:'), self.group)
        f.addRow(tr('Tiempo de cada cuadro:'), self.frame_time)
        f.addRow(tr('Cuadro que pega / lanza:'), self.hit_frame)
        f.addRow(tr('Número de la acción (.air):'), self.action_no)
        fl.addWidget(g)

        g = QGroupBox(tr('Golpe'))
        f = QFormLayout(g)
        self.damage = QSpinBox()
        self.damage.setRange(0, 9999)
        self.damage.setValue(70)
        self.height = QComboBox()
        for txt, *_r in HEIGHTS:
            self.height.addItem(tr(txt))
        self.strength = QComboBox()
        for txt, v in ((tr('Leve'), "Light"), (tr('Medio'), "Medium"), (tr('Fuerte'), "Heavy")):
            self.strength.addItem(txt, v)
        self.strength.setCurrentIndex(1)
        self.knock = QDoubleSpinBox()
        self.knock.setRange(0, 30)
        self.knock.setValue(5)
        self.launch = QCheckBox(tr('Lo tira al suelo (lo lanza por el aire)'))
        self.pause = QSpinBox()
        self.pause.setRange(0, 60)
        self.pause.setValue(12)
        f.addRow(tr('Daño:'), self.damage)
        f.addRow(tr('Altura:'), self.height)
        f.addRow(tr('Fuerza:'), self.strength)
        f.addRow(tr('Lo empuja hacia atrás:'), self.knock)
        f.addRow(tr('Pausa al pegar (ticks):'), self.pause)
        f.addRow(self.launch)
        fl.addWidget(g)

        g = QGroupBox(tr('Movimiento del personaje'))
        f = QFormLayout(g)
        self.forward = QDoubleSpinBox()
        self.forward.setRange(-30, 30)
        self.jump = QDoubleSpinBox()
        self.jump.setRange(0, 30)
        self.sound = QComboBox()
        f.addRow(tr('Avanza al empezar (velocidad):'), self.forward)
        f.addRow(tr('Salta al empezar (fuerza):'), self.jump)
        f.addRow(tr('Sonido al empezar:'), self.sound)
        fl.addWidget(g)

        g = QGroupBox(tr('Proyectil'))
        f = QFormLayout(g)
        self.proj = QCheckBox(tr('Lanza un proyectil (en vez de pegar con el cuerpo)'))
        self.proj_group = QComboBox()
        self.proj_speed = QDoubleSpinBox()
        self.proj_speed.setRange(0.5, 40)
        self.proj_speed.setValue(5)
        self.proj_y = QSpinBox()
        self.proj_y.setRange(-1000, 1000)
        self.proj_y.setValue(-60)
        f.addRow(self.proj)
        f.addRow(tr('Grupo de sprites del proyectil:'), self.proj_group)
        f.addRow(tr('Velocidad:'), self.proj_speed)
        f.addRow(tr('Altura desde los pies:'), self.proj_y)
        fl.addWidget(g)
        fl.addStretch(1)
        split.addWidget(scroll)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel(tr('Lo que se va a agregar:')))
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.preview.setStyleSheet("QPlainTextEdit { background: #1e2228; color: #d6deeb; }")
        rl.addWidget(self.preview, 1)
        self.where = QLabel()
        self.where.setWordWrap(True)
        self.where.setObjectName("CardPath")
        rl.addWidget(self.where)
        go = QPushButton(tr('🥊  Agregar al personaje'))
        go.setObjectName("primary")
        go.setMinimumHeight(40)
        go.clicked.connect(self.apply)
        rl.addWidget(go)
        split.addWidget(right)
        split.setSizes([480, 700])
        from ui.code_tab import Highlighter
        self._hl = Highlighter(self.preview.document())
        for w in (self.name, self.button):
            (w.textChanged if isinstance(w, QLineEdit) else w.currentTextChanged).connect(self.refresh)
        for w in (self.kind, self.motion, self.pos, self.group, self.height, self.strength, self.sound, self.proj_group):
            w.currentIndexChanged.connect(self.refresh)
        for w in (self.stateno, self.frame_time, self.hit_frame, self.action_no, self.damage, self.pause, self.proj_y):
            w.valueChanged.connect(self.refresh)
        for w in (self.knock, self.forward, self.jump, self.proj_speed):
            w.valueChanged.connect(self.refresh)
        for w in (self.cancel, self.launch, self.proj):
            w.toggled.connect(self.refresh)
        self.kind.currentIndexChanged.connect(self.suggest_numbers)
        self.pos.currentIndexChanged.connect(self.suggest_numbers)

    def is_modified(self):
        return False

    def save(self):
        return True

    # ---- datos del personaje
    def load(self):
        p = self.main.project
        self.group.blockSignals(True)
        self.proj_group.blockSignals(True)
        self.sound.blockSignals(True)
        self.group.clear()
        self.proj_group.clear()
        self.sound.clear()
        self.sound.addItem(tr('(ninguno)'), None)
        if p:
            groups = sorted({s.group for s in p.sff.sprites})
            for g in groups:
                n = sum(1 for s in p.sff.sprites if s.group == g)
                self.group.addItem(tr('Grupo {0} ({1} sprites)').format(g, n), g)
                self.proj_group.addItem(tr('Grupo {0} ({1} sprites)').format(g, n), g)
            try:
                for s in p.snd.sounds if (p.snd_loaded() or p.file("sound")) else []:
                    self.sound.addItem(f"{s.group}, {s.number}", s.key)
            except Exception:
                pass
            for i in range(self.group.count()):
                if self.group.itemData(i) in (1000, 1100, 200):
                    self.group.setCurrentIndex(i)
                    break
        self.group.blockSignals(False)
        self.proj_group.blockSignals(False)
        self.sound.blockSignals(False)
        self.suggest_numbers()

    def activated(self):
        self.refresh()

    def used_states(self):
        from core.codeinfo import statedefs_in
        p = self.main.project
        used = set()
        for _k, path in p.code_files():
            of = self.main.code.open.get(str(path))
            try:
                from core.textio import read_text
                used |= statedefs_in(of.doc.toPlainText() if of else read_text(path)[0])
            except OSError:
                pass
        return used

    def suggest_numbers(self):
        p = self.main.project
        if not p:
            return
        kind = self.kind.currentData()
        base = {"special": 1000, "super": 3000, "normal": 200}[kind]
        if kind == "normal":
            base += {"S": 0, "C": 200, "A": 400}[self.pos.currentData()]
        used = self.used_states()
        n = base
        while n in used or p.air.find(n) is not None:
            n += 10
        self.stateno.setValue(n)
        a = n
        while p.air.find(a) is not None:
            a += 1
        self.action_no.setValue(a)
        self.refresh()

    # ---- generar
    def cmd_name(self):
        return re.sub(r"[^\w]+", "_", self.name.text().strip()) or "move"

    def command_text(self):
        b = self.button.currentText().strip() or "x"
        return self.motion.currentData().format(b=b)

    def pieces(self):
        """(comando, entrada en Statedef -1, statedef, acciones [Action])."""
        p = self.main.project
        st = self.stateno.value()
        kind = self.kind.currentData()
        pos = self.pos.currentData()
        name = self.name.text().strip() or "Move"
        cname = self.cmd_name()
        cmd = (f'[Command]\nname = "{cname}"\ncommand = {self.command_text()}\n'
               f'time = {30 if self.motion.currentIndex() == 7 else 15}\n')
        entry = [f"[State -1, {name}]", "type = ChangeState", f"value = {st}", f'triggerall = command = "{cname}"']
        if kind == "super":
            entry.append("triggerall = power >= 1000")
        entry += [f"trigger1 = statetype = {pos}", "trigger1 = ctrl"]
        if self.cancel.isChecked() and kind != "normal":
            entry += [f"trigger2 = statetype = {pos}", "trigger2 = stateno = [200, 699]", "trigger2 = movecontact"]
        entry = "\n".join(entry) + "\n"
        air_mode = pos == "A" or self.jump.value() > 0
        physics = "A" if air_mode else pos
        sd = [f"; {name}", f"[Statedef {st}]", f"type = {'A' if air_mode else pos}", "movetype = A",
              f"physics = {physics}", "juggle = 4"]
        if not air_mode:
            sd.append("velset = 0, 0")
        sd += ["ctrl = 0", f"anim = {self.action_no.value()}",
               f"poweradd = {-1000 if kind == 'super' else (30 if kind == 'special' else 15)}", "sprpriority = 2", ""]
        if kind == "super":
            sd += [f"[State {st}, {tr('Pausa de súper')}]", "type = SuperPause", "trigger1 = Time = 0", "time = 30",
                   "movetime = 30", "darken = 1", ""]
        if self.forward.value() or self.jump.value():
            sd += [f"[State {st}, {tr('Impulso')}]", "type = VelSet", "trigger1 = Time = 0"]
            if self.forward.value():
                sd.append(f"x = {self.forward.value():g}")
            if self.jump.value():
                sd.append(f"y = {-self.jump.value():g}")
            sd.append("")
        snd = self.sound.currentData()
        if snd:
            sd += [f"[State {st}, {tr('Sonido')}]", "type = PlaySnd", "trigger1 = Time = 0", f"value = {snd[0]}, {snd[1]}", ""]
        _t, gtype, guard_attr, guardflag = HEIGHTS[self.height.currentIndex()]
        attr_pos = "A" if pos == "A" else pos
        level = {"special": "SA", "super": "HA", "normal": {"Light": "NA", "Medium": "NA", "Heavy": "NA"}[
            self.strength.currentData()]}[kind]
        if self.proj.isChecked():
            level = {"special": "SP", "super": "HP", "normal": "NP"}[kind]
        anim_type = self.strength.currentData()
        hit = [f"attr = {attr_pos}, {level}", f"damage = {self.damage.value()}, {max(0, self.damage.value() // 10)}",
               f"animtype = {anim_type}", f"guardflag = {guardflag if pos != 'A' else 'HA'}", "hitflag = MAF",
               f"priority = {5 if kind != 'normal' else 3}, Hit", f"pausetime = {self.pause.value()}, {self.pause.value()}",
               f"sparkno = {1 if anim_type == 'Light' else (2 if anim_type == 'Medium' else 3)}",
               "sparkxy = -10, -70", f"hitsound = 5, {0 if anim_type == 'Light' else (1 if anim_type == 'Medium' else 2)}",
               "guardsound = 6, 0", f"ground.type = {gtype}", f"ground.slidetime = {self.pause.value()}",
               f"ground.hittime = {self.pause.value() + 4}", f"ground.velocity = {-self.knock.value():g}",
               f"air.velocity = {-self.knock.value() * 0.6:g}, -4"]
        if self.launch.isChecked():
            hit += ["fall = 1", f"ground.velocity = {-self.knock.value():g}, -6", "air.fall = 1"]
            hit = [h for h in hit if not (h.startswith("ground.velocity") and "," not in h)]
        hf = self.hit_frame.value()
        if self.proj.isChecked():
            pa = self.action_no.value() + 1
            while p.air.find(pa) is not None:
                pa += 1
            self._proj_action = pa
            sd += [f"[State {st}, {tr('Proyectil')}]", "type = Projectile", f"trigger1 = AnimElem = {hf}",
                   f"projid = {st}", f"projanim = {pa}", "projremove = 1", "projhits = 1",
                   f"velocity = {self.proj_speed.value():g}, 0", f"offset = 40, {self.proj_y.value()}",
                   "projpriority = 1", "projsprpriority = 3"] + [h for h in hit if not h.startswith("sparkxy")] + [""]
        else:
            sd += [f"[State {st}, {tr('Golpe')}]", "type = HitDef", f"trigger1 = AnimElem = {hf}"] + hit + [""]
        if air_mode:
            sd += [f"[State {st}, {tr('Aterrizar')}]", "type = ChangeState", "trigger1 = Vel Y > 0",
                   "trigger1 = Pos Y >= 0", "value = 52", ""]
        else:
            sd += [f"[State {st}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0",
                   f"value = {11 if pos == 'C' else 0}", "ctrl = 1", ""]
        actions = self.make_actions(air_mode)
        return cmd, entry, "\n".join(sd), actions

    def frames_of(self, group):
        p = self.main.project
        nums = sorted(s.number for s in p.sff.sprites if s.group == group)
        return [(group, n) for n in nums]

    def make_actions(self, air_mode):
        p = self.main.project
        out = []
        g = self.group.currentData()
        if g is None:
            return out
        a = Action(self.action_no.value())
        a.title = self.name.text().strip()
        a.header = [f"; {a.title}"]
        a.raw = None
        sprites = p.sff.index()
        keys = self.frames_of(g)
        hf = self.hit_frame.value()
        for i, (gg, nn) in enumerate(keys):
            f = Frame(gg, nn, 0, 0, self.frame_time.value())
            s = sprites.get((gg, nn))
            if s is not None:
                f.clsn2 = auto_boxes(s, two=True)
                if i + 1 == hf and not self.proj.isChecked():
                    f.clsn1 = hit_box(s)
            a.frames.append(f)
        if a.frames and air_mode:
            a.frames[-1].time = -1
        out.append(a)
        if self.proj.isChecked() and self.proj_group.currentData() is not None:
            pa = Action(getattr(self, "_proj_action", self.action_no.value() + 1))
            pa.title = self.name.text().strip() + " (" + tr('proyectil') + ")"
            pa.header = [f"; {pa.title}"]
            pa.raw = None
            for gg, nn in self.frames_of(self.proj_group.currentData()):
                f = Frame(gg, nn, 0, 0, 4)
                s = sprites.get((gg, nn))
                if s is not None:
                    box = auto_boxes(s, two=False)
                    f.clsn1, f.clsn2 = list(box), list(box)
                pa.frames.append(f)
            out.append(pa)
        return out

    def target_files(self):
        """(archivo .cmd, archivo de estados, ¿hay que crear el de estados?)."""
        p = self.main.project
        cmd = p.file("cmd")
        if cmd is not None and cmd.suffix.lower() == ".zss":
            cmd = None
        st = None
        for k, v in p.defs.keys("Files"):
            if re.match(r"st\d*$", k, re.IGNORECASE) and v:
                f = p.file(k)
                if f is not None and f.suffix.lower() in (".cns", ".st"):
                    st = f
        if st is None:
            f = p.file("cns")
            if f is not None and f.suffix.lower() in (".cns", ".st"):
                st = f
        create = st is None
        if create:
            st = p.folder / f"{p.def_path.stem}_moves.st"
        return cmd, st, create

    def refresh(self):
        p = self.main.project
        if not p:
            return
        try:
            cmd, entry, sd, actions = self.pieces()
        except Exception as e:
            self.preview.setPlainText(str(e))
            return
        air_txt = "".join(a.text() + "\n" for a in actions)
        cmdf, stf, create = self.target_files()
        self.preview.setPlainText(
            f"; ---- {cmdf.name if cmdf else '.cmd'}: {tr('comando')}\n{cmd}\n"
            f"; ---- {cmdf.name if cmdf else '.cmd'}: {tr('dentro de [Statedef -1]')}\n{entry}\n"
            f"; ---- {stf.name}\n{sd}\n; ---- {p.air.path.name if p.air.path else '.air'}\n{air_txt}")
        warn = []
        if cmdf is None:
            warn.append(tr('⚠ El personaje no tiene un .cmd normal: el comando no se agregará.'))
        if create:
            warn.append(tr('Se creará «{0}» y se agregará al .def.').format(stf.name))
        if self.stateno.value() in self.used_states():
            warn.append(tr('⚠ El estado {0} ya existe.').format(self.stateno.value()))
        self.where.setText(" ".join(warn))

    def apply(self):
        p = self.main.project
        if not p:
            return
        if self.group.currentData() is None:
            QMessageBox.warning(self, APP_NAME, tr('Elige el grupo de sprites de la animación.'))
            return
        if self.stateno.value() in self.used_states():
            if QMessageBox.question(self, APP_NAME, tr('El estado {0} ya existe. ¿Agregarlo de todos modos?').format(
                    self.stateno.value())) != QMessageBox.StandardButton.Yes:
                return
        cmd, entry, sd, actions = self.pieces()
        cmdf, stf, create = self.target_files()
        code = self.main.code
        # .cmd
        if cmdf is not None:
            of = code.get_open(cmdf)
            text = of.doc.toPlainText()
            m = re.search(r"^[ \t]*\[\s*statedef\s+-1\s*\][^\n]*\n", text, re.IGNORECASE | re.MULTILINE)
            cur = QTextCursor(of.doc)
            cur.beginEditBlock()
            if m:
                # comando antes de [Statedef -1] y la entrada justo después (prioridad sobre los normales)
                cur.setPosition(m.end())
                cur.insertText("\n" + entry + "\n")
                cur.setPosition(m.start())
                cur.insertText(cmd + "\n")
            else:
                cur.movePosition(QTextCursor.MoveOperation.End)
                cur.insertText("\n" + cmd + "\n[Statedef -1]\n\n" + entry)
            cur.endEditBlock()
        # estados
        if create:
            stf.write_text("; " + tr('Movimientos creados con el asistente') + "\n", encoding="utf-8")
            keys = {k.lower() for k, _v in p.defs.keys("Files")}
            key = "st" if "st" not in keys else next(f"st{i}" for i in range(1, 10) if f"st{i}" not in keys)
            p.defs.set("Files", key, stf.name)
            p.defs_dirty = True
            self.main.def_tab.load_form_only()
            self.main.def_tab.set_modified()
        of = code.get_open(stf)
        cur = QTextCursor(of.doc)
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertText(("\n" if not of.doc.toPlainText().endswith("\n") else "") +
                       "\n;---------------------------------------------------------------------------\n" + sd + "\n")
        # animaciones
        anims = self.main.anims
        air = p.air
        new_list = sorted([a for a in air.actions if a.number not in {x.number for x in actions}] + actions,
                          key=lambda a: a.number)
        anims.edit_list(tr('Asistente de movimientos'), new_list, actions[0] if actions else None)
        self.main.sim.states = {}
        self.main.update_title()
        QMessageBox.information(self, APP_NAME, tr('✅ «{0}» agregado: comando, estado {1} y animación {2}. '
                                                   'Revísalo en Código y Animaciones, pruébalo en el Simulador '
                                                   'y guarda con Ctrl+S.').format(
            self.name.text().strip(), self.stateno.value(), self.action_no.value()))
        self.suggest_numbers()
