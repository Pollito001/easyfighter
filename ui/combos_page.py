"""Página «🔗 Combos» del modo simple: estilos de combos y sus opciones (sin tocar código)."""
import copy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QToolButton,
    QVBoxLayout, QWidget,
)

from core import combos
from core import simple_gen as sg
from i18n import tr
from ui.simple_mode import Page, muted, title_label

KEEP = ("ad_state", "x_state")     # números ya elegidos: no se pierden al cambiar de estilo
BUTTON_CHOICES = [("any", 'Puño o patada'), ("punch", 'Solo puño'), ("kick", 'Solo patada')]
_OPEN = {}                         # tarjetas abiertas / cerradas (mientras el editor está abierto)


def fold_card(key, title, desc=None, opened=True):
    """Tarjeta que se minimiza: clic en el título. Devuelve (tarjeta, layout del cuerpo, etiqueta del título)."""
    box = QFrame()
    box.setObjectName("Card")
    outer = QVBoxLayout(box)
    outer.setContentsMargins(10, 8, 10, 8)
    outer.setSpacing(6)
    head = QHBoxLayout()
    arrow = QToolButton()
    arrow.setAutoRaise(True)
    arrow.setStyleSheet("QToolButton { border: none; font-size: 12pt; }")
    lab = title_label(title)
    lab.setCursor(Qt.CursorShape.PointingHandCursor)
    head.addWidget(arrow)
    head.addWidget(lab, 1)
    outer.addLayout(head)
    body = QWidget()
    v = QVBoxLayout(body)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(6)
    if desc:
        v.addWidget(muted(desc))
    outer.addWidget(body)

    def set_open(on):
        _OPEN[key] = on
        body.setVisible(on)
        arrow.setText("▾" if on else "▸")

    arrow.clicked.connect(lambda: set_open(not body.isVisible()))
    lab.mousePressEvent = lambda _e: set_open(not body.isVisible())
    box.set_open = set_open
    box.head = head
    set_open(_OPEN.get(key, opened))
    return box, v, lab


class AutoDoubleCard(QFrame):
    """Un autodoble de la lista: fuerza, botón, con qué especial inicia, sus golpes y el daño."""

    def __init__(self, page, ad, index):
        super().__init__()
        self.page = page
        self.ad = ad
        self.index = index
        self._binding = True
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.box, v, self.title = fold_card(f"ad:{ad.get('id')}", "", opened=False)
        lay.addWidget(self.box)
        g = QGridLayout()
        g.setColumnStretch(1, 1)
        self.name = QLineEdit(ad.get("name", ""))
        self.name.setPlaceholderText(tr('Autodoble'))
        self.name.textChanged.connect(self.on_change)
        g.addWidget(QLabel(tr('Nombre:')), 0, 0)
        g.addWidget(self.name, 0, 1, 1, 2)
        self.strength = QComboBox()
        for s in range(3):
            self.strength.addItem(tr(sg.STRENGTH[s]), s)
        self.strength.setCurrentIndex(int(ad.get("strength", 1)))
        self.strength.currentIndexChanged.connect(self.on_change)
        self.button = QComboBox()
        for k, t in BUTTON_CHOICES:
            self.button.addItem(tr(t), k)
        self.button.setCurrentIndex(max(0, self.button.findData(ad.get("button", "any"))))
        self.button.currentIndexChanged.connect(self.on_change)
        row = QHBoxLayout()
        row.addWidget(self.strength)
        row.addWidget(self.button, 1)
        g.addWidget(QLabel(tr('Botón:')), 1, 0)
        g.addLayout(row, 1, 1, 1, 2)
        self.opener = QComboBox()
        self.opener.addItem(tr('(cualquier especial)'), "")
        for ref, t, _n in page.opener_items():
            self.opener.addItem(t, ref)
        i = self.opener.findData(ad.get("open", ""))
        self.opener.setCurrentIndex(max(0, i))
        self.opener.currentIndexChanged.connect(self.on_change)
        g.addWidget(QLabel(tr('Inicia con:')), 2, 0)
        g.addWidget(self.opener, 2, 1, 1, 2)
        v.addLayout(g)
        v.addWidget(QLabel(tr('Golpes (en orden):')))
        self.hits_box = QVBoxLayout()
        v.addLayout(self.hits_box)
        self.hit_rows = []
        for h in ad.get("hits") or []:
            self.add_hit_row(h)
        row = QHBoxLayout()
        addh = QPushButton(tr('➕ Golpe'))
        addh.clicked.connect(lambda: (self.add_hit_row({"ref": "", "speed": 100}), self.on_change()))
        row.addWidget(addh)
        row.addStretch(1)
        row.addWidget(QLabel(tr('Daño de cada golpe:')))
        self.damage = QSpinBox()
        self.damage.setRange(1, 300)
        self.damage.setValue(int(ad.get("damage") or 20))
        self.damage.valueChanged.connect(self.on_change)
        row.addWidget(self.damage)
        v.addLayout(row)
        self.warn = QLabel()
        self.warn.setObjectName("Warn")
        self.warn.setWordWrap(True)
        self.warn.hide()
        v.addWidget(self.warn)
        row = QHBoxLayout()
        for txt, fn in ((tr('🎨 Editar visual'), lambda: page.visual(self.index)),
                        (tr('⧉ Duplicar'), lambda: page.duplicate_ad(self.index)),
                        (tr('🗑 Quitar autodoble'), lambda: page.remove_ad(self.index))):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self._binding = False
        self.refresh_title()

    def add_hit_row(self, h):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        num = QLabel(f"{len(self.hit_rows) + 1}.")
        num.setFixedWidth(22)
        c = QComboBox()
        c.addItem(tr('(ninguno)'), "")
        for ref, t, _n in self.page.anims_cache:
            c.addItem(t, ref)
        ref = h.get("ref", "")
        if ref and ":" not in ref:
            ref = "N:" + ref
        i = c.findData(ref)
        if ref and i < 0:
            c.addItem(tr('{0} (no tiene sprites)').format(self.page.ref_name(ref)), ref)
            i = c.count() - 1
        c.setCurrentIndex(max(0, i))
        c.currentIndexChanged.connect(self.on_change)
        spd = QSpinBox()
        spd.setRange(25, 400)
        spd.setSingleStep(25)
        spd.setSuffix(" %")
        spd.setPrefix(tr('Rapidez:') + " ")
        spd.setToolTip(tr('Qué tan rápido va esta animación en el autodoble: 100 % es como está, 200 % el '
                          'doble de rápido, 50 % la mitad. La animación original no cambia.'))
        spd.setValue(int(h.get("speed") or 100))
        spd.valueChanged.connect(self.on_change)
        rm = QPushButton("✖")
        rm.setFixedWidth(30)
        rm.setToolTip(tr('Quitar este golpe'))
        rm.clicked.connect(lambda: self.remove_hit(w))
        row.addWidget(num)
        row.addWidget(c, 1)
        row.addWidget(spd)
        row.addWidget(rm)
        self.hits_box.addWidget(w)
        self.hit_rows.append((w, num, c, spd))

    def remove_hit(self, w):
        self.hit_rows = [r for r in self.hit_rows if r[0] is not w]
        w.setParent(None)
        for i, r in enumerate(self.hit_rows):
            r[1].setText(f"{i + 1}.")
        self.on_change()

    def refresh_title(self):
        a = self.ad
        name = a.get("name") or tr('Autodoble')
        n = len([h for h in a.get("hits") or [] if h.get("ref")])
        btn = dict(BUTTON_CHOICES).get(a.get("button", "any"), "")
        self.title.setText(f"🔁 {name}  ·  {tr(sg.STRENGTH[int(a.get('strength', 1))])}  ·  {tr(btn)}  ·  "
                           f"{tr('{0} golpes').format(n)}")

    def on_change(self, *_a):
        if self._binding:
            return
        a = self.ad
        a["name"] = self.name.text().strip()
        a["strength"] = int(self.strength.currentData())
        a["button"] = self.button.currentData()
        a["open"] = self.opener.currentData() or ""
        a["hits"] = [{"ref": c.currentData() or "", "speed": int(spd.value())} for _w, _n, c, spd in self.hit_rows]
        a["damage"] = int(self.damage.value())
        self.refresh_title()
        self.page.save_ads()


class CombosPage(Page):
    def __init__(self, sm):
        super().__init__(sm, tr('🔗 Combos'), tr(
            'Cómo se juntan los golpes de tu personaje en combos. Escoge un estilo parecido a un juego de peleas '
            'conocido y, si quieres, cambia cualquier cosa de abajo. Todo vale para los golpes y especiales del '
            'modo simple. Clic en el título de una tarjeta para minimizarla.'))
        self._binding = False
        self.w = {}
        self.ad_list = []
        self.ad_cards = []
        self.anims_cache = []
        self.folds = []
        row = QHBoxLayout()
        row.addStretch(1)
        for txt, on in ((tr('⊞ Abrir todos'), True), (tr('⊟ Cerrar todos'), False)):
            b = QPushButton(txt)
            b.clicked.connect(lambda _c, on=on: self.set_all_open(on))
            row.addWidget(b)
        self.lay.insertLayout(2, row)

        # ---- estilo
        grid = self.section(tr('Estilo'), cols=1)
        box, v, _l = self.card("style", tr('Estilo de combos'))
        self.style = QComboBox()
        for key, name, _d, _c in combos.STYLES:
            self.style.addItem(tr(name), key)
        self.style.addItem(tr('Personalizado'), "custom")
        self.style.currentIndexChanged.connect(self.on_style)
        v.addWidget(self.style)
        self.style_desc = muted("")
        v.addWidget(self.style_desc)
        grid.addWidget(box, 0, 0)

        # ---- cadenas
        grid = self.section(tr('Cadenas (un golpe normal sigue con otro)'), cols=2)
        box, v, _l = self.card("chain", tr('Cómo se encadenan'), tr(
            'Si el golpe pega (o el rival se cubre), aprietas el próximo botón y sale enseguida, sin esperar a '
            'que termine.'))
        self.combo(v, "chain", [(k, tr(t)) for k, t in combos.CHAINS])
        self.check(v, "chain_mix", tr('Mezclar de pie y agachado (débil agachado → medio de pie…)'))
        self.check(v, "repeat_light", tr('Repetir los débiles (débil, débil, débil…)'))
        self.check(v, "air_chain", tr('Cadenas en el aire también'))
        grid.addWidget(box, 0, 0, Qt.AlignmentFlag.AlignTop)
        box, v, _l = self.card("cancel", tr('Cancelar en especiales'), tr(
            'Qué golpes normales se pueden cortar con un especial cuando pegan. Cada especial tiene además su '
            'ajuste «Se puede hacer cancelando un golpe».'))
        self.w["cancel_from"] = []
        for i, name in enumerate(('Golpes débiles', 'Golpes medios', 'Golpes fuertes')):
            cb = QCheckBox(tr(name))
            cb.toggled.connect(self.on_cancel)
            v.addWidget(cb)
            self.w["cancel_from"].append(cb)
        grid.addWidget(box, 0, 1, Qt.AlignmentFlag.AlignTop)

        # ---- lanzador y saltar
        grid = self.section(tr('Lanzador y combos en el aire'), cols=2)
        box, v, _l = self.card("launcher", tr('Lanzador'), tr(
            'Un golpe normal que manda al rival bien alto (y no se puede recuperar hasta caer).'))
        self.launcher = self.combo(v, "launcher", [])
        grid.addWidget(box, 0, 0, Qt.AlignmentFlag.AlignTop)
        box, v, _l = self.card("jump", tr('Saltar para seguir el combo'), tr(
            'Después de pegar, aprieta ↑ y el personaje salta enseguida para seguir pegando en el aire.'))
        self.combo(v, "jump_cancel", [(k, tr(t)) for k, t in combos.JUMPS])
        grid.addWidget(box, 0, 1, Qt.AlignmentFlag.AlignTop)

        # ---- autodobles
        grid = self.section(tr('Autodobles (estilo Killer Instinct)'), cols=1)
        box, v, _l = self.card("ad", tr('Autodobles'), tr(
            'Cuando un especial pega, aprieta un puño o una patada: sale un autodoble, golpes seguidos solos. '
            'Cada golpe usa una animación que ya tiene tu personaje (de sus golpes, especiales o súper). Mientras '
            'dura, el rival no se empuja. El autodoble sale después del último golpe del especial (no lo corta), y solo '
            'si el rival recibió el golpe en el suelo (no en el aire ni cubriéndose). '
            'Después puedes cancelar en otro especial y seguir.'))
        self.check(v, "autodouble", tr('Usar autodobles'))
        self.spin(v, "ad_limit", 0, 99, tr('Límite del combo (golpes):'))
        self.w["ad_limit"].setSpecialValueText(tr('Sin límite'))
        v.addWidget(muted(tr('Cuando el combo llega a esa cantidad de golpes, el próximo golpe de autodoble sí '
                             'empuja y tumba al rival, y el combo se acaba.')))
        self.spin(v, "ad_max", 0, 20, tr('Autodobles por combo (máximo):'))
        self.w["ad_max"].setSpecialValueText(tr('Sin límite'))
        v.addWidget(muted(tr('Killer Instinct 2 deja 4: el último que se permite tumba al rival con su último '
                             'golpe, y ya solo queda el remate.')))
        self.check(v, "ad_air_open", tr('Caer encima con un golpe en el aire también abre un autodoble'))
        self.combo(v, "ad_rule", [(k_, tr(t_)) for k_, t_ in combos.AD_RULES], tr('Botón del autodoble:'))
        self.check(v, "enders", tr('Remate (Ender): la versión fuerte de un especial, después de un autodoble, '
                                   'tumba al rival y cierra el combo'))
        self.spin(v, "ender_bonus", 0, 200, tr('Daño extra del remate (%):'), 5)
        v.addWidget(muted(tr('También puedes hacer remates propios en «Especiales y súper» (💥 Agregar remate).')))
        grid.addWidget(box, 0, 0)
        # la lista de autodobles
        lb, lv, _l = self.card("adlist", tr('Lista de autodobles'), tr(
            'Agrega los que quieras, de cualquier fuerza. Si dos salen con lo mismo (fuerza, botón y especial), '
            'gana el primero de la lista. Los que inician con un especial escogido ganan sobre los de «cualquier '
            'especial».'))
        self.ad_host = QVBoxLayout()
        lv.addLayout(self.ad_host)
        row = QHBoxLayout()
        add = QPushButton(tr('➕ Agregar autodoble'))
        add.clicked.connect(self.add_ad)
        vis = QPushButton(tr('🎨 Crear combo visual'))
        vis.setToolTip(tr('Escoge las animaciones mirándolas, pruébalo animado y agrégalo a la lista.'))
        vis.clicked.connect(lambda: self.visual(None))
        test = QPushButton(tr('▶ Probar combo'))
        test.setObjectName("primary")
        test.setToolTip(tr('Arma un combo entero (especial → autodoble → especial…) y míralo animado.'))
        test.clicked.connect(self.on_test)
        for b in (add, vis):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(test)
        lv.addLayout(row)
        grid.addWidget(lb, 1, 0)

        # ---- defensa y energía
        grid = self.section(tr('Romper y cancelar combos'), cols=2)
        box, v, _l = self.card("breaker", tr('Combo breaker'), tr(
            'El que está recibiendo el combo aprieta estos botones juntos y lo rompe: destella, se vuelve '
            'invencible un momento y empuja al atacante.'))
        self.check(v, "breaker", tr('Se puede romper el combo'))
        self.combo(v, "breaker_mode", [(k_, tr(t_)) for k_, t_ in combos.BREAKER_MODES], tr('Cómo:'))
        self.combo(v, "breaker_btn", [(p, p) for p in combos.PRESS], tr('Botones:'))
        self.spin(v, "breaker_lockout", 0, 600, tr('Si falla, bloqueado (ticks, 60 = 1 s):'), 30)
        self.w["breaker_lockout"].setSpecialValueText(tr('Sin bloqueo'))
        self.spin(v, "breaker_hits", 1, 30, tr('Después de cuántos golpes:'))
        self.spin(v, "breaker_cost", 0, 3000, tr('Energía que gasta (1000 = 1 barra):'), 250)
        grid.addWidget(box, 0, 0, Qt.AlignmentFlag.AlignTop)
        box, v, _l = self.card("rc", tr('Cancelar con energía («Roman cancel»)'), tr(
            'Cuando cualquier golpe pega, aprieta estos botones: el golpe se corta al instante, el rival se '
            'queda quieto un momentito y tú quedas libre para seguir el combo. Gasta energía.'))
        self.check(v, "rc", tr('Se puede cancelar con energía'))
        self.combo(v, "rc_btn", [(p, p) for p in combos.PRESS], tr('Botones:'))
        self.spin(v, "rc_cost", 0, 3000, tr('Energía que gasta (1000 = 1 barra):'), 250)
        grid.addWidget(box, 0, 1, Qt.AlignmentFlag.AlignTop)

        # ---- balance
        grid = self.section(tr('Balance'), cols=2)
        box, v, _l = self.card("scaling", tr('Menos daño en combos largos'), tr(
            'Para que un combo largo no mate de un golpe: después de unos golpes, cada golpe quita un poco menos.'))
        self.check(v, "scaling", tr('Bajar el daño en combos largos'))
        self.spin(v, "scale_free", 0, 30, tr('Golpes con daño completo:'))
        self.spin(v, "scale_step", 1, 50, tr('Cuánto baja por golpe (%):'))
        self.spin(v, "scale_min", 0, 100, tr('Nunca menos de (%):'))
        grid.addWidget(box, 0, 0, Qt.AlignmentFlag.AlignTop)
        box, v, _l = self.card("stun", tr('Ayuda para combos'), tr(
            'El rival se queda aturdido unos ticks más después de cada golpe, así es más fácil conectar el '
            'próximo (60 ticks = 1 segundo).'))
        self.spin(v, "extra_stun", 0, 30, tr('Ticks de más:'))
        grid.addWidget(box, 0, 1, Qt.AlignmentFlag.AlignTop)
        self.finish()

    # ---- widgets
    def card(self, key, title, desc=None):
        box, v, lab = fold_card(key, title, desc)
        self.folds.append(box)
        return box, v, lab

    def set_all_open(self, on):
        for b in self.folds + [c.box for c in self.ad_cards]:
            b.set_open(on)

    def combo(self, v, key, items, label=None):
        c = QComboBox()
        for k, t in items:
            c.addItem(t, k)
        c.currentIndexChanged.connect(lambda _i, key=key, c=c: self.set(key, c.currentData()))
        if label:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(c, 1)
            v.addLayout(row)
        else:
            v.addWidget(c)
        self.w[key] = c
        return c

    def check(self, v, key, text):
        c = QCheckBox(text)
        c.toggled.connect(lambda on, key=key: self.set(key, bool(on)))
        v.addWidget(c)
        self.w[key] = c
        return c

    def spin(self, v, key, lo, hi, label, step=1):
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setSingleStep(step)
        s.valueChanged.connect(lambda val, key=key: self.set(key, int(val)))
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(s)
        row.addStretch(1)
        host = QWidget()
        host.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        v.addWidget(host)
        self.w[key] = s
        return s

    # ---- datos
    def current(self):
        return combos.get(self.sm.cfg) or combos.preset("basic")

    def normal_items(self, ground=True):
        out = []
        names = dict((p, t) for p, t, _n in sg.POSITIONS)
        for key in sg.NORMAL_KEYS:
            pos, b, _s, _k, _base = sg.normal_info(key)
            if ground and pos == "A":
                continue
            e = self.sm.cfg["normals"].get(key) or {}
            if not e.get("frames") or sg.is_off(self.sm.cfg, key):
                continue
            out.append((key, f"{tr(names[pos])}: {tr(sg.NORMAL_NAMES[b])} ({b})"))
        return out

    def bind(self, cfg):
        self._binding = True
        c = self.current()
        self.style.setCurrentIndex(max(0, self.style.findData(c.get("style", "basic"))))
        self.style_desc.setText(self.style_text(c.get("style", "basic")))
        items = self.normal_items()
        self.launcher.clear()
        self.launcher.addItem(tr('(ninguno)'), "")
        for k, t in items:
            self.launcher.addItem(t, k)
        if c["launcher"] and self.launcher.findData(c["launcher"]) < 0:
            self.launcher.addItem(tr('{0} (no tiene sprites)').format(c["launcher"]), c["launcher"])
        for key, w in self.w.items():
            if key == "cancel_from":
                for i, cb in enumerate(w):
                    cb.setChecked(i in c["cancel_from"])
            elif isinstance(w, QCheckBox):
                w.setChecked(bool(c[key]))
            elif isinstance(w, QSpinBox):
                w.setValue(int(c[key]))
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(max(0, w.findData(c[key])))
        self.ad_list = copy.deepcopy(c["ad_list"])
        self.rebuild_ads()
        self.enable(c)
        self._binding = False

    def rebuild_ads(self):
        for card_ in self.ad_cards:
            card_.setParent(None)
        self.ad_cards = []
        self.anims_cache = self.anim_items()
        for i, ad in enumerate(self.ad_list):
            card_ = AutoDoubleCard(self, ad, i)
            self.ad_host.addWidget(card_)
            self.ad_cards.append(card_)
        self.check_conflicts()

    def check_conflicts(self):
        seen = {}
        for card_ in self.ad_cards:
            a = card_.ad
            btns = {"any": ("p", "k"), "punch": ("p",), "kick": ("k",)}.get(a.get("button", "any"), ("p", "k"))
            msg = ""
            for b in btns:
                key = (int(a.get("strength", 1)), b, a.get("open", ""))
                if key in seen and seen[key] is not card_:
                    msg = tr('⚠ «{0}» sale con lo mismo y va antes en la lista: este no saldría así.').format(
                        seen[key].ad.get("name") or tr('Autodoble'))
                seen.setdefault(key, card_)
            if not [h for h in a.get("hits") or [] if h.get("ref")]:
                msg = tr('⚠ Ponle al menos un golpe.')
            card_.warn.setText(msg)
            card_.warn.setVisible(bool(msg))

    def save_ads(self):
        if self._binding:
            return
        c = self.current()
        c["ad_list"] = copy.deepcopy(self.ad_list)
        self.check_conflicts()
        self.store(c)

    def add_ad(self, ad=None):
        n = len(self.ad_list)
        self.ad_list.append(ad or combos.new_ad(1, [], name=tr('Autodoble {0}').format(n + 1)))
        self.save_ads()
        self.rebuild_ads()
        self.ad_cards[-1].box.set_open(True)

    def duplicate_ad(self, i):
        a = copy.deepcopy(self.ad_list[i])
        a["id"] = combos.new_ad()["id"]
        a.pop("state", None)
        a.pop("anim", None)
        a["name"] = (a.get("name") or tr('Autodoble')) + " (2)"
        self.ad_list.insert(i + 1, a)
        self.save_ads()
        self.rebuild_ads()

    def remove_ad(self, i):
        if 0 <= i < len(self.ad_list):
            del self.ad_list[i]
            self.save_ads()
            self.rebuild_ads()

    def visual(self, i):
        from ui.combo_visual import VisualCombo
        self.sm.flush()
        ad = copy.deepcopy(self.ad_list[i]) if i is not None and 0 <= i < len(self.ad_list) else None
        dlg = VisualCombo(self, ad)
        if dlg.exec() and dlg.result_ad is not None:
            if i is None:
                self.add_ad(dlg.result_ad)
            else:
                self.ad_list[i] = dlg.result_ad
                self.save_ads()
                self.rebuild_ads()
                self.ad_cards[i].box.set_open(True)

    def enable(self, c):
        for key in ("breaker_mode", "breaker_hits", "breaker_cost"):
            self.w[key].setEnabled(c["breaker"])
        self.w["breaker_btn"].setEnabled(c["breaker"] and c.get("breaker_mode") == "buttons")
        self.w["breaker_lockout"].setEnabled(c["breaker"] and c.get("breaker_mode") in ("strength", "ki2"))
        for key in ("ad_rule", "enders", "ad_limit", "ad_max", "ad_air_open"):
            self.w[key].setEnabled(c["autodouble"])
        self.w["ender_bonus"].setEnabled(c["autodouble"] and bool(c.get("enders")))
        for key in ("rc_btn", "rc_cost"):
            self.w[key].setEnabled(c["rc"])
        for key in ("scale_free", "scale_step", "scale_min"):
            self.w[key].setEnabled(c["scaling"])
        for card_ in self.ad_cards:
            card_.setEnabled(c["autodouble"])

    def style_text(self, style):
        for k, _n, d, _c in combos.STYLES:
            if k == style:
                return tr(d)
        return tr('Tus propias opciones (cambiaste algo de un estilo).')

    def store(self, c):
        """Guarda las opciones y pone el estilo que les toca (o «Personalizado»)."""
        old = self.sm.cfg.get("combos") or {}
        c["style"] = next((k for k in combos.STYLE_KEYS if combos.matches(c, k)), "custom")
        for k in KEEP:
            if k in old:
                c[k] = old[k]
        self.sm.cfg["combos"] = c
        self._binding = True
        self.style.setCurrentIndex(max(0, self.style.findData(c["style"])))
        self.style_desc.setText(self.style_text(c["style"]))
        self.enable(c)
        self._binding = False
        self.sm.moves_changed()

    def set(self, key, value):
        if self._binding:
            return
        c = self.current()
        c[key] = value
        c["ad_list"] = copy.deepcopy(self.ad_list)
        self.store(c)

    def on_cancel(self, _on=None):
        if self._binding:
            return
        c = self.current()
        c["cancel_from"] = [i for i, cb in enumerate(self.w["cancel_from"]) if cb.isChecked()]
        self.store(c)

    def anim_items(self):
        """[(ref, texto, nº de animación)] de golpes, especiales y súper (del modo simple y del personaje)."""
        cfg = self.sm.cfg
        out, seen = [], set()
        for key, t in self.normal_items():
            out.append(("N:" + key, "👊 " + t, (cfg["normals"].get(key) or {}).get("state")))
        for i, sp in enumerate(cfg.get("specials", [])):
            num = sg.special_anim(sp)
            if num is None and not sg._frames(sp):
                continue
            kind = sp.get("kind")
            icon = ("⭐ " + tr('Súper')) if kind == "super" else ("💥 " + tr('Remate')) if kind == "ender" else \
                ("🔥 " + tr('Especial'))
            out.append((sg.special_ref(i, sp), f"{icon}: {sp.get('name') or '?'}", num))
            seen.add(num)
        for f in self.originals():
            if f.anim is None or f.anim in seen or f.kind not in ("normal", "special", "super", "throw"):
                continue
            seen.add(f.anim)
            out.append((f"O:{f.anim}", f"🥋 {tr('Del personaje')}: {f.label}", f.anim))
        # avisar las que no tienen caja de golpe: con esa el autodoble no pega
        return [(r, t + ("  · " + tr('no pega') if self.hits(n) is False else ""), n) for r, t, n in out]

    def ref_name(self, ref):
        """Nombre legible de una referencia que ya no está en la lista."""
        kind, _, key = str(ref).partition(":")
        if kind == "N" and key in sg.NORMAL_KEYS:
            pos, b, *_r = sg.normal_info(key)
            names = dict((p, t) for p, t, _n in sg.POSITIONS)
            return f"{tr(names[pos])}: {tr(sg.NORMAL_NAMES[b])} ({b})"
        return str(ref)

    def hits(self, num):
        """¿La animación tiene caja de golpe (rojo)? None si no se sabe."""
        p = self.sm.main.project
        a = p.air.find(int(num)) if (p is not None and num is not None) else None
        if a is None:
            return None
        return any(f.clsn1 for f in a.frames)

    def opener_items(self):
        """Especiales y súper con los que puede iniciar un autodoble: [(ref, texto, nº de animación)]."""
        cfg = self.sm.cfg
        out = []
        for i, sp in enumerate(cfg.get("specials", [])):
            if not sg.opens_autodouble(sp) or not (sg._frames(sp) or sp.get("type") == "converted"):
                continue
            icon = "⭐" if sp.get("kind") == "super" else "🔥"
            out.append((sg.special_ref(i, sp), f"{icon} {sp.get('name') or '?'}", sg.special_anim(sp)))
        for f in self.originals():
            if f.kind in ("special", "super") and f.states and not f.disabled:
                out.append(("S:" + ",".join(str(x) for x in f.states), f"🥋 {tr('Del personaje')}: {f.label}",
                            f.anim))
        return out

    def originals(self):
        try:
            return list(self.sm.originals() or [])
        except Exception:
            return []

    def on_test(self):
        from ui.combo_test import ComboTest
        self.sm.flush()
        ComboTest(self).exec()

    def on_style(self, _i=None):
        if self._binding:
            return
        key = self.style.currentData()
        if key == "custom":
            c = self.current()
            c["style"] = "custom"
            self.style_desc.setText(self.style_text("custom"))
            return
        old = self.sm.cfg.get("combos") or {}
        c = combos.preset(key)
        for k in KEEP:
            if k in old:
                c[k] = old[k]
        # la lista de autodobles es tuya: no se pierde al cambiar de estilo
        if isinstance(old.get("ad_list"), list) or "ad" in old:
            c["ad_list"] = combos.migrate_ads(old)
        self.sm.cfg["combos"] = c
        self.bind(self.sm.cfg)
        self.sm.moves_changed()
