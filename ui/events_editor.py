"""Editor de los eventos de un especial: una lista (en orden) y un diálogo para cada evento."""
import copy

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMenu, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from core import simple_gen as sg
from core import special_events as sev
from i18n import tr


class EventDialog(QDialog):
    def __init__(self, sm, sp, ev, nframes):
        super().__init__(sm.main)
        self.sm, self.sp = sm, sp
        self.orig = ev
        self.ev = copy.deepcopy(ev)
        e = sev.EVENT[ev["type"]]
        self.setWindowTitle(f"{e[1]} {tr('Proyectil') if ev.get('main') else tr(e[2])}")
        self.resize(620, 640)
        outer = QVBoxLayout(self)
        if e[3]:
            lab = QLabel(tr(e[3]))
            lab.setWordWrap(True)
            lab.setObjectName("CardPath")
            outer.addWidget(lab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        scroll.setWidget(host)
        outer.addWidget(scroll, 1)
        form = QFormLayout(host)
        raw = bool(ev.get("raw"))
        # cuándo
        self.frame = QSpinBox()
        self.frame.setRange(0, max(1, nframes))
        self.frame.setSpecialValueText(tr('Desde el principio'))
        self.frame.setValue(int(ev.get("frame") or 0))
        self.delay = QSpinBox()
        self.delay.setRange(0, 600)
        self.delay.setValue(int(ev.get("delay") or 0))
        self.delay.setSuffix(" " + tr('ticks'))
        if raw and not ev.get("frame"):
            form.addRow(tr('Cuándo:'), QLabel(tr('Con la condición de su código (abajo).')))
        else:
            form.addRow(tr('En el cuadro:'), self.frame)
            if not raw:
                form.addRow(tr('Y después de:'), self.delay)
        # campos
        self.widgets = {}
        patchable = sev.PATCH.get(ev["type"], {})
        for key, label, kind, lo, hi, dflt, tip in e[4]:
            if raw and key not in patchable:
                continue
            w = self.make_widget(key, kind, lo, hi, sev.val(self.ev, key))
            if w is None:
                continue
            if tip:
                w.setToolTip(tr(tip))
            if kind is bool:
                form.addRow(w)
            else:
                form.addRow(tr(label) + ":", w)
            self.widgets[key] = (kind, w)
        if raw:
            form.addRow(QLabel(tr('Su código original (se escribe tal cual, con los cambios de arriba):')))
            self.code = QPlainTextEdit(ev["raw"])
            self.code.setMinimumHeight(180)
            form.addRow(self.code)
        else:
            self.code = None
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        outer.addWidget(bb)

    def make_widget(self, key, kind, lo, hi, value):
        if kind is bool:
            w = QCheckBox(tr(dict((f[0], f[1]) for f in sev.EVENT[self.ev["type"]][4])[key]))
            w.setChecked(bool(value))
            return w
        if kind is int or kind is float:
            w = QDoubleSpinBox() if kind is float else QSpinBox()
            if kind is float:
                w.setDecimals(2)
                w.setSingleStep(0.5)
            w.setRange(lo, hi)
            try:
                w.setValue(kind(value))
            except (TypeError, ValueError):
                pass
            return w
        if isinstance(kind, tuple) and kind[0] == "choice":
            w = QComboBox()
            for v, t in kind[1]:
                w.addItem(tr(t), v)
            w.setCurrentIndex(max(0, w.findData(value)))
            return w
        if kind == "button":
            w = QComboBox()
            for b in sg.BUTTONS:
                w.addItem(b, b)
            w.setCurrentIndex(max(0, w.findData(value)))
            return w
        if kind == "special":
            w = QComboBox()
            for o in self.sm.cfg.get("specials", []):
                if o is self.sp or not o.get("uid"):
                    continue
                w.addItem(o.get("name") or "?", o["uid"])
            w.setCurrentIndex(max(0, w.findData(value)))
            return w
        if kind == "sound":
            w = QComboBox()
            w.addItem(tr('(ninguno)'), None)
            p = self.sm.main.project
            try:
                for s in sorted(p.snd.sounds, key=lambda s: s.key):
                    w.addItem(f"{s.group}, {s.number}", [s.group, s.number])
            except Exception:
                pass
            if value:
                want = [str(x).strip() for x in value]
                i = next((j for j in range(w.count()) if w.itemData(j) is not None and
                          [str(x) for x in w.itemData(j)] == want), -1)
                if i < 0:
                    w.addItem(", ".join(str(x) for x in value), list(value))
                    i = w.count() - 1
                w.setCurrentIndex(i)
            return w
        if kind == "code":
            w = QPlainTextEdit(str(value or ""))
            w.setMinimumHeight(220)
            w.setPlaceholderText("[State {st}, ...]\ntype = ...\ntrigger1 = ...")
            return w
        if kind == "anim":
            from ui.simple_mode import FramesBox
            ent = self.ev.setdefault(key, {})
            if not isinstance(ent, dict):
                ent = self.ev[key] = {}
            fb = FramesBox(self.sm, tr('Efecto'), 9000, default_time=4, small=True)
            fb.bind(ent)
            return fb
        return None

    def accept(self):
        ev = self.ev
        if not (ev.get("raw") and not self.orig.get("frame")):
            f = self.frame.value()
            if f != int(self.orig.get("frame") or 0):
                ev.setdefault("edited", []).append("frame")
            ev["frame"] = f or None
            ev["delay"] = self.delay.value() or None
        for key, (kind, w) in self.widgets.items():
            if kind is bool:
                v = w.isChecked()
            elif kind in (int, float):
                v = w.value()
            elif kind == "code":
                v = w.toPlainText()
            elif kind == "anim":
                continue
            else:
                v = w.currentData()
            if v != self.orig.get(key):
                if self.orig.get("raw"):
                    ev.setdefault("edited", [])
                    if key not in ev["edited"]:
                        ev["edited"].append(key)
            ev[key] = v
        if self.code is not None:
            ev["raw"] = self.code.toPlainText().rstrip("\n") + "\n"
        if ev.get("edited"):
            ev["edited"] = sorted(set(ev["edited"]))
        self.orig.clear()
        self.orig.update(ev)
        super().accept()


class EventsEditor(QWidget):
    """Lista de eventos de un especial (o de cada versión, si viene del personaje)."""

    def __init__(self, sm, card):
        super().__init__()
        self.sm, self.card = sm, card
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.vlabel = QLabel(tr('Versión:'))
        self.version = QComboBox()
        self.version.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.vlabel)
        top.addWidget(self.version)
        top.addStretch(1)
        v.addLayout(top)
        intro = QLabel(tr('Cosas que pasan en un cuadro de la animación, en orden: moverse, otro golpe, otro '
                          'proyectil, efectos, sonidos, sacudir la pantalla, seguir con otro especial… Los marcados '
                          '«del tipo» los pone «Qué hace» (por ejemplo, el impulso del gancho): cámbialos aquí.'))
        intro.setWordWrap(True)
        intro.setObjectName("CardPath")
        v.addWidget(intro)
        self.list = QListWidget()
        self.list.setMinimumHeight(170)
        self.list.itemDoubleClicked.connect(lambda _it: self.edit())
        v.addWidget(self.list, 1)
        row = QHBoxLayout()
        add = QPushButton(tr('➕ Agregar evento'))
        add.setObjectName("primary")
        menu = QMenu(add)
        for key, icon, label, _h, _f in sev.EVENTS:
            a = menu.addAction(f"{icon} {tr(label)}")
            a.triggered.connect(lambda _c, key=key: self.add(key))
        add.setMenu(menu)
        row.addWidget(add)
        for txt, fn in ((tr('✏ Editar'), self.edit), (tr('🗑 Quitar'), self.remove), ("▲", lambda: self.move(-1)),
                        ("▼", lambda: self.move(1)), (tr('⧉ Duplicar'), self.duplicate)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.bind()

    def bind(self):
        sp = self.card.sp
        self.version.blockSignals(True)
        self.version.clear()
        conv = sp.get("type") == "converted"
        if conv:
            for key in sorted((sp.get("vevents") or {}).keys(), key=lambda x: int(x)):
                vi = int(key)
                self.version.addItem(tr(sg.VERSION_NAMES[vi]) if vi < 4 else str(vi), key)
        self.version.blockSignals(False)
        self.vlabel.setVisible(conv)
        self.version.setVisible(conv)
        self.fill()

    def events(self):
        sp = self.card.sp
        if sp.get("type") == "converted":
            key = self.version.currentData()
            return (sp.setdefault("vevents", {})).setdefault(key, []) if key is not None else []
        return sp.setdefault("events", [])

    def view(self, ev):
        """Lo que se muestra de un evento (el del proyectil principal sale de los datos del especial)."""
        if ev.get("main"):
            p = self.sm.main.project
            return sg.main_proj_view(self.card.sp, p.sff.index() if p else {}, self.sm.motion.k())
        return ev

    def fill(self):
        row = self.list.currentRow()
        self.list.clear()
        for ev in self.events():
            it = QListWidgetItem(sev.summary(self.view(ev), tr))
            if ev.get("type") == "custom" and ev.get("raw"):
                first = ev["raw"].strip().split("\n")
                it.setText(it.text() + "  ·  " + (first[1].strip() if len(first) > 1 else first[0].strip()))
            self.list.addItem(it)
        if 0 <= row < self.list.count():
            self.list.setCurrentRow(row)

    def nframes(self):
        return max(1, len(sg._frames(self.card.sp)))

    def changed(self):
        self.fill()
        self.card.refresh_head()
        self.sm.moves_changed()

    def add(self, key):
        ev = {"type": key, "frame": 1}
        if key == "custom":
            ev["frame"] = None
        dlg = EventDialog(self.sm, self.card.sp, ev, self.nframes())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.events().append(ev)
            self.changed()
            self.list.setCurrentRow(self.list.count() - 1)

    def current(self):
        i = self.list.currentRow()
        evs = self.events()
        return (i, evs[i]) if 0 <= i < len(evs) else (None, None)

    def edit(self):
        i, ev = self.current()
        if ev is None:
            return
        if ev.get("main"):
            before = self.view(ev)
            after = dict(before)
            dlg = EventDialog(self.sm, self.card.sp, after, self.nframes())
            if dlg.exec() == QDialog.DialogCode.Accepted:
                sg.apply_main_proj(self.card.sp, before, after)
                if hasattr(self.card, "refresh_proj"):
                    self.card.refresh_proj()
                self.changed()
            return
        dlg = EventDialog(self.sm, self.card.sp, ev, self.nframes())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.changed()

    def remove(self):
        i, ev = self.current()
        if ev is None:
            return
        del self.events()[i]
        self.changed()

    def duplicate(self):
        i, ev = self.current()
        if ev is None:
            return
        if ev.get("main"):
            # la copia es un proyectil más, independiente
            ev = {k: v for k, v in self.view(ev).items() if k not in ("main", "tpl")}
        self.events().insert(i + 1, copy.deepcopy(ev))
        self.changed()
        self.list.setCurrentRow(i + 1)

    def move(self, d):
        i, ev = self.current()
        if ev is None:
            return
        evs = self.events()
        j = i + d
        if 0 <= j < len(evs):
            evs[i], evs[j] = evs[j], evs[i]
            self.changed()
            self.list.setCurrentRow(j)

