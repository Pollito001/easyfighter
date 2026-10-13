"""Pestaña Simulador: ver cómo se mueve un estado (.cns/.st) sin abrir el juego."""
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainterPath, QPixmap, QTransform
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from core.simulate import Simulator, parse_constants, parse_states
from core.textio import read_text
from i18n import tr
from ui.common import ZoomView, axis_pen, cosmetic, rectf, sprite_qimage


class SimTab(QWidget):
    modifiedChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.states, self.const = {}, {}
        self.sim = None
        self._pix = {}
        self._sprites = {}
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.player = None
        lay = QHBoxLayout(self)
        split = QSplitter()
        lay.addWidget(split)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr('Buscar estado'))
        self.filter.textChanged.connect(lambda _t: self.fill())
        ll.addWidget(self.filter)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(lambda it, _p: self.start(it.data(Qt.ItemDataRole.UserRole)) if it else None)
        ll.addWidget(self.list, 1)
        reload_btn = QPushButton(tr('⟳ Volver a leer el código'))
        reload_btn.clicked.connect(self.load)
        ll.addWidget(reload_btn)
        split.addWidget(left)
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        self.scene = QGraphicsScene()
        self.view = ZoomView(self.scene)
        cl.addWidget(self.view, 1)
        ctl = QHBoxLayout()
        self.play_btn = QPushButton(tr('▶ Simular'))
        self.play_btn.setObjectName("primary")
        self.play_btn.clicked.connect(self.toggle)
        ctl.addWidget(self.play_btn)
        for txt, fn in ((tr('⏭ Un tick'), self.tick), (tr('⟲ Reiniciar'), self.restart)):
            b = QPushButton(txt.split(" ", 1)[0])
            b.setToolTip(txt)
            b.clicked.connect(fn)
            ctl.addWidget(b)
        self.speed = QComboBox()
        for txt, v in (("¼×", 0.25), ("½×", 0.5), ("1×", 1.0), ("2×", 2.0)):
            self.speed.addItem(txt, v)
        self.speed.setCurrentIndex(2)
        self.speed.currentIndexChanged.connect(self.update_timer)
        ctl.addWidget(self.speed)
        self.loop = QCheckBox(tr('Repetir al terminar'))
        self.loop.setChecked(True)
        ctl.addWidget(self.loop)
        self.sound = QCheckBox(tr('Sonidos'))
        self.sound.setChecked(True)
        ctl.addWidget(self.sound)
        self.show_boxes = QCheckBox(tr('Cajas'))
        self.show_boxes.setChecked(True)
        self.show_boxes.toggled.connect(lambda _c: self.draw())
        ctl.addWidget(self.show_boxes)
        ctl.addStretch(1)
        cl.addLayout(ctl)
        from ui.backgrounds import BackdropPicker
        self.bg_picker = BackdropPicker(main)
        brow = QHBoxLayout()
        brow.addWidget(self.bg_picker)
        brow.addStretch(1)
        cl.addLayout(brow)
        split.addWidget(center)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        g = QGroupBox(tr('Al empezar'))
        f = QFormLayout(g)
        self.start_type = QComboBox()
        for txt, v in ((tr('Parado (S)'), "S"), (tr('Agachado (C)'), "C"), (tr('En el aire (A)'), "A")):
            self.start_type.addItem(txt, v)
        f.addRow(tr('Posición:'), self.start_type)
        self.cmds = QLineEdit()
        self.cmds.setPlaceholderText('holdfwd, a')
        self.cmds.setToolTip(tr('Comandos que cuentan como presionados (los nombres del .cmd), separados por comas'))
        f.addRow(tr('Botones presionados:'), self.cmds)
        rl.addWidget(g)
        g2 = QGroupBox(tr('Ahora'))
        v2 = QVBoxLayout(g2)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.TextFormat.RichText)
        v2.addWidget(self.info)
        rl.addWidget(g2)
        g3 = QGroupBox(tr('Qué pasó'))
        v3 = QVBoxLayout(g3)
        self.log = QListWidget()
        self.log.itemDoubleClicked.connect(self.goto_code)
        v3.addWidget(self.log)
        rl.addWidget(g3, 1)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName("CardPath")
        rl.addWidget(self.note)
        split.addWidget(right)
        split.setSizes([220, 800, 340])

    def is_modified(self):
        return False

    def save(self):
        return True

    def load(self):
        p = self.main.project
        self.states, self.const = {}, {}
        if not p:
            return
        files = [path for k, path in p.code_files() if path.suffix.lower() in (".cns", ".st") or k.lower().startswith("st")
                 or k.lower() == "cns"]
        seen = set()
        for path in files:
            if path in seen or path.suffix.lower() == ".zss":
                continue
            seen.add(path)
            of = self.main.code.open.get(str(path))
            try:
                text = of.doc.toPlainText() if of else read_text(path)[0]
            except OSError:
                continue
            for num, st in parse_states(text, str(path)).items():
                self.states.setdefault(num, st)
            self.const.update({k: v for k, v in parse_constants(text).items() if k not in self.const})
        self.fill()
        self.note.setText(tr('Simula la física, la animación y los controladores más usados. Los estados comunes '
                             '(parado, caminar, recibir golpes…) son del juego: al llegar a uno, la simulación termina.'))

    def activated(self):
        p = self.main.project
        self._sprites = p.sff.index() if p else {}
        self._pix.clear()
        if not self.states:
            self.load()

    def fill(self):
        flt = self.filter.text().strip().lower()
        self.list.blockSignals(True)
        self.list.clear()
        for num in sorted(self.states):
            if num < 0:
                continue
            st = self.states[num]
            name = st.get("title", "")
            label = f"{num}   {name}" if name else str(num)
            if flt and flt not in label.lower():
                continue
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, num)
            self.list.addItem(it)
        self.list.blockSignals(False)

    # ---- simulación
    def start(self, num):
        p = self.main.project
        if p is None or num is None:
            return
        cmds = [c for c in self.cmds.text().split(",")]
        self.sim = Simulator(self.states, p.air, self.const, cmds)
        self.sim.reset(num, self.start_type.currentData())
        self.current = num
        self.log.clear()
        self.add_log(self.sim.events)
        self.draw()
        if self.view.zoom < 1.5:
            self.view.set_zoom(2)
        self.view.centerOn(0, -60)

    def restart(self):
        if self.sim is not None:
            self.start(self.current)

    def toggle(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_btn.setText(tr('▶ Simular'))
        else:
            if self.sim is None:
                it = self.list.currentItem()
                if not it:
                    return
                self.start(it.data(Qt.ItemDataRole.UserRole))
            self.update_timer()
            self.timer.start()
            self.play_btn.setText(tr('⏸ Pausa'))

    def update_timer(self):
        self.timer.setInterval(max(1, int(1000 / (60 * (self.speed.currentData() or 1.0)))))

    def tick(self):
        if self.sim is None:
            return
        if self.sim.finished is not None:
            if self.loop.isChecked() and self.timer.isActive():
                self.start(self.current)
            else:
                self.timer.stop()
                self.play_btn.setText(tr('▶ Simular'))
            return
        self.sim.step()
        self.add_log(self.sim.events)
        self.draw()

    def add_log(self, events):
        s = self.sim
        for ev in events:
            if ev[0] == "ctrl":
                _k, line, typ, name = ev
                if typ in ("null",):
                    continue
                it = QListWidgetItem(f"t={s.time:<3} {typ}" + (f"  «{name}»" if name else ""))
                it.setData(Qt.ItemDataRole.UserRole, line)
                it.setForeground(QBrush(QColor("#c792ea")))
            elif ev[0] == "state":
                it = QListWidgetItem(tr('→ estado {0}').format(ev[1]))
                it.setForeground(QBrush(QColor("#ffb547")))
            elif ev[0] == "end":
                it = QListWidgetItem(tr('■ pasa al estado {0} (del juego o no está en el código): fin').format(ev[1]))
                it.setForeground(QBrush(QColor("#ff6b35")))
            elif ev[0] == "land":
                it = QListWidgetItem(tr('■ toca el suelo (el juego lo pasa al estado 52): fin'))
                it.setForeground(QBrush(QColor("#ff6b35")))
            elif ev[0] == "sound":
                it = QListWidgetItem(tr('🔊 sonido {0}').format(ev[1]))
                self.play_sound(ev[1])
            else:
                continue
            self.log.addItem(it)
        self.log.scrollToBottom()

    def play_sound(self, value):
        if not self.sound.isChecked():
            return
        v = value.strip()
        if v[:1].upper() in ("F", "S"):
            return  # sonidos del juego
        try:
            g, n = [int(float(x)) for x in v.split(",")[:2]]
        except ValueError:
            return
        p = self.main.project
        snd = p.snd if p and (p.snd_loaded() or p.file("sound")) else None
        s = snd.find(g, n) if snd else None
        if s is None:
            return
        try:
            import tempfile
            from PyQt6.QtMultimedia import QSoundEffect
            tmp = Path(tempfile.gettempdir()) / f"ikemen_chareditor_sim_{g}_{n}.wav"
            tmp.write_bytes(s.data)
            self.player = QSoundEffect(self)
            self.player.setSource(QUrl.fromLocalFile(str(tmp)))
            self.player.play()
        except Exception:
            pass

    def goto_code(self, item):
        line = item.data(Qt.ItemDataRole.UserRole)
        st = self.states.get(self.current)
        if not line or not st:
            return
        code = self.main.code
        for i in range(code.files.count()):
            if code.files.item(i).data(Qt.ItemDataRole.UserRole) == st["source"]:
                code.files.setCurrentRow(i)
                break
        self.main.tabs.setCurrentWidget(code)
        code.editor.go_line(line)

    # ---- dibujo
    def pixmap(self, g, n):
        s = self._sprites.get((g, n))
        if s is None:
            return None, None
        if id(s) not in self._pix:
            img = sprite_qimage(self.main.project.sff, s)
            self._pix[id(s)] = QPixmap.fromImage(img) if not img.isNull() else None
        return self._pix[id(s)], s

    def draw(self):
        self.scene.clear()
        s = self.sim
        lim = 700
        if self.view.backdrop_key == "checker":
            floor = QGraphicsRectItem(-lim, 0, lim * 2, 200)
            floor.setBrush(QBrush(QColor(255, 107, 53, 22)))
            floor.setPen(cosmetic("#ff6b35"))
            self.scene.addItem(floor)
        else:
            self.scene.addLine(-lim, 0, lim, 0, cosmetic("#ff6b35"))
        for x in range(-600, 601, 100):
            self.scene.addLine(x, 0, x, 6, cosmetic("#5b6270"))
        if s is not None:
            if len(s.trail) > 1:
                path = QPainterPath(QPointF(*s.trail[0]))
                for pt in s.trail[1:]:
                    path.lineTo(QPointF(*pt))
                self.scene.addPath(path, cosmetic("#ffb547", 1, Qt.PenStyle.DashLine))
            a = s.action()
            if a and a.frames:
                i, _t, animtime = s.anim_info()
                f = a.frames[i]
                pm, spr = self.pixmap(f.group, f.number)
                t = QTransform()
                t.translate(s.pos[0], s.pos[1])
                t.scale(s.facing, 1)
                if pm is not None:
                    it = QGraphicsPixmapItem(pm)
                    ft = QTransform()
                    fx = -1 if "H" in (f.flip or "").upper() else 1
                    fy = -1 if "V" in (f.flip or "").upper() else 1
                    ft.translate(f.x, f.y)
                    ft.scale(fx * (f.xscale or 1), fy * (f.yscale or 1))
                    ft.translate(-spr.x, -spr.y)
                    it.setTransform(ft * t)
                    self.scene.addItem(it)
                if self.show_boxes.isChecked():
                    for kind, boxes in ((2, f.clsn2), (1, f.clsn1)):
                        col = QColor(60, 140, 255) if kind == 2 else QColor(255, 60, 60)
                        for b in boxes:
                            r = QGraphicsRectItem(rectf(*b))
                            r.setTransform(t)
                            r.setPen(cosmetic(col))
                            fill = QColor(col)
                            fill.setAlpha(50)
                            r.setBrush(QBrush(fill))
                            self.scene.addItem(r)
            self.scene.addLine(s.pos[0] - 6, s.pos[1], s.pos[0] + 6, s.pos[1], axis_pen())
            self.scene.addLine(s.pos[0], s.pos[1] - 6, s.pos[0], s.pos[1] + 6, axis_pen())
            info = [
                tr('Estado <b>{0}</b> · tiempo <b>{1}</b>').format(s.stateno, s.time),
                tr('Animación <b>{0}</b> · cuadro {1} · AnimTime {2}').format(
                    s.anim_no, s.anim_info()[0] + 1, s.anim_info()[2]),
                tr('Posición {0:.1f}, {1:.1f} · velocidad {2:.2f}, {3:.2f}').format(s.pos[0], s.pos[1], s.vel[0], s.vel[1]),
                tr('Tipo {0} · movimiento {1} · física {2} · control {3}').format(s.statetype, s.movetype, s.physics, s.ctrl),
            ]
            if s.hitdef:
                info.append("<span style='color:#ff6b35'><b>" + tr('🥊 Golpe activo (HitDef)') + "</b></span>")
            if s.var:
                info.append("var: " + ", ".join(f"{k}={v}" for k, v in sorted(s.var.items())))
            if s.unsupported:
                info.append("<span style='color:#8b93a3'>" + tr('No simulado: {0}').format(
                    ", ".join(sorted(s.unsupported))[:200]) + "</span>")
            self.info.setText("<br>".join(info))
        self.scene.setSceneRect(QRectF(-lim, -lim * 0.8, lim * 2, lim))
