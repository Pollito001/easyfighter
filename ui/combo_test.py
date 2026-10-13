"""«▶ Probar combo»: arma un combo entero (especial → autodoble → especial…) y lo enseña animado,
con el rival de muñeco y la cuenta de golpes."""
from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QTransform
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget,
)

from core import simple_gen as sg
from i18n import tr
from ui import theme
from ui.common import PlaybackBar, advance

HITPAUSE = 8          # ticks que se congela al pegar (como en el juego)
END_WAIT = 50         # ticks quieto al final antes de repetir


class ComboCanvas(QWidget):
    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg
        self.tick = 0
        self.setMinimumSize(520, 380)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.CANVAS))
        tl = self.dlg.timeline
        gy = self.height() - 50
        p.setPen(QPen(QColor(255, 107, 53, 170), 1))
        p.drawLine(0, gy, self.width(), gy)
        if not tl:
            p.setPen(QColor(theme.MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr('Agrega pasos al combo (a la izquierda).'))
            p.end()
            return
        z = self.dlg.zoom
        x0 = self.width() * 0.36
        fr = tl[self.tick % len(tl)]
        # el rival (de muñeco): parado, o recibiendo el golpe
        dummy = self.dlg.dummy_hurt if fr["hurt"] > 0 and self.dlg.dummy_hurt else self.dlg.dummy_idle
        if dummy is not None:
            shake = (2 if (fr["hurt"] % 4) < 2 else -2) if fr["hurt"] > HITPAUSE else 0
            self.draw_frame(p, dummy, x0 + self.dlg.dist * z + shake, gy, z, mirror=True)
        if fr["frame"] is not None:
            self.draw_frame(p, fr["frame"], x0, gy, z)
        # chispa del golpe
        if fr["spark"] is not None:
            sx, sy = fr["spark"]
            p.setPen(QPen(QColor(255, 230, 90), 3))
            c = QPointF(x0 + sx * z, gy + sy * z)
            for dx, dy in ((-10, 0), (10, 0), (0, -10), (0, 10), (-7, -7), (7, 7), (-7, 7), (7, -7)):
                p.drawLine(c, c + QPointF(dx, dy))
        # textos
        p.setPen(QColor(theme.MUTED))
        p.drawText(10, 20, fr["label"])
        if fr["hits"] >= 2:
            f = QFont()
            f.setPointSize(26)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor(255, 200, 60))
            p.drawText(14, 70, tr('{0} GOLPES').format(fr["hits"]))
        p.end()

    def draw_frame(self, p, f, x, gy, z, mirror=False):
        s = self.dlg.sm.sprite(f.group, f.number)
        pm = self.dlg.sm.pixmap(f.group, f.number)
        if s is None or pm is None:
            return
        flip_h = "h" in (f.flip or "").lower()
        if mirror:
            flip_h = not flip_h
        sx = -1 if flip_h else 1
        fx = -f.x if mirror else f.x
        t = QTransform()
        t.translate(x + fx * z, gy + f.y * z)
        t.scale(z * sx, z)
        p.save()
        p.setTransform(t)
        p.drawPixmap(-s.x, -s.y, pm)
        p.restore()


def setup_stage(dlg, sm):
    """Lo que necesita el lienzo: el .air, el rival de muñeco, el zoom y la distancia."""
    dlg.sm = sm
    dlg.timeline = []
    p = sm.main.project
    dlg.air = p.air if p else None
    idle = dlg.air.find(0) if dlg.air else None
    dlg.dummy_idle = idle.frames[0] if idle and idle.frames else None
    hurt = dlg.air.find(5000) if dlg.air else None
    dlg.dummy_hurt = hurt.frames[0] if hurt and hurt.frames else None
    h = 100
    if dlg.dummy_idle is not None:
        s = sm.sprite(dlg.dummy_idle.group, dlg.dummy_idle.number)
        if s is not None:
            _w, h = s.size()
    dlg.zoom = max(0.5, min(3.0, 260 / max(40, h)))
    dlg.dist = 70 * max(1.0, (p.localcoord()[0] / 320) if p else 1.0)


def find_action(dlg, num):
    if num is None or dlg.air is None:
        return None
    a = dlg.air.find(int(num))
    return a if a is not None and a.frames else None


def ad_actions(dlg, ad):
    """[(acción, rapidez %)] de los golpes de un autodoble de la lista."""
    out = []
    for h in ad.get("hits") or []:
        ref = h.get("ref") or ""
        if ref and ":" not in ref:
            ref = "N:" + ref
        a = find_action(dlg, dlg.anims.get(ref, (None, None))[1])
        if a is not None:
            out.append((a, int(h.get("speed") or 100)))
    if len(out) == 1:
        out = out * 2
    return out


def make_timeline(dlg, segments):
    """segments: [(texto, [(acción, rapidez %)], tipo «sp» / «ad» / «end», problema o None)] → cuadros por tick."""
    tl = []
    hits = 0
    hurt = 0
    for label, acts, kind, why in segments:
        if why:
            # en el juego esto no sale: el combo se corta aquí
            for _ in range(40):
                tl.append(dict(frame=None, hits=hits, hurt=0, spark=None, label="⚠ " + why))
            hits = 0
        for a, pct in acts:
            prev_hit = False
            for f in a.frames:
                n = f.time if f.time > 0 else (10 if kind == "ad" else 20)
                n = max(1, int(round(n * 100.0 / max(10, pct))))
                starts = bool(f.clsn1) and not prev_hit
                prev_hit = bool(f.clsn1)
                if starts:
                    hits += 1
                    hurt = HITPAUSE + 16
                    x1, y1, x2, y2 = f.clsn1[0]
                    spark = (f.x + max(x1, x2), f.y + (y1 + y2) / 2)
                    for _ in range(HITPAUSE):         # se congela al pegar
                        tl.append(dict(frame=f, hits=hits, hurt=hurt, spark=spark, label=label))
                        hurt = max(0, hurt - 1)
                for _ in range(n):
                    tl.append(dict(frame=f, hits=hits, hurt=hurt, spark=None, label=label))
                    hurt = max(0, hurt - 1)
        if kind == "end" and acts:
            last = acts[-1][0].frames[-1]
            for j in range(30):     # el rival sale volando: el combo se cerró
                tl.append(dict(frame=last, hits=hits, hurt=40 - j, spark=None, label="💥 " + tr('¡Remate!')))
    if tl:
        idle = find_action(dlg, 0)
        idle_frames = idle.frames if idle is not None else [None]
        for i in range(END_WAIT):
            f = idle_frames[(i // 6) % len(idle_frames)]
            tl.append(dict(frame=f, hits=hits, hurt=max(0, hurt - i), spark=None, label=tr('Fin del combo')))
    return tl


class ComboTest(QDialog):
    """Pasos: («sp», especial, fuerza) · («ad», id del autodoble) · («end», remate)."""

    def __init__(self, page):
        super().__init__(page.sm.main)
        self.page = page
        self.setWindowTitle(tr('▶ Probar combo'))
        self.resize(1040, 640)
        setup_stage(self, page.sm)
        self.anims = {ref: (t, num) for ref, t, num in page.anim_items()}
        self.specials = page.opener_items()
        self.special_map = {ref: (t, num) for ref, t, num in self.specials}
        cfg = self.sm.cfg
        self.kind = {}
        self.enders = []        # remates: los hechos como tales y (si está prendido) los especiales que pegan
        for i, sp in enumerate(cfg.get("specials", [])):
            ref = sg.special_ref(i, sp)
            self.kind[ref] = sp.get("kind") or "special"
            self.kind[ref + "#type"] = sp.get("type", "proj")
            if sp.get("kind") == "ender" and sg._frames(sp):
                t = f"💥 {sp.get('name') or tr('Remate')}"
                self.enders.append((ref, t, sg.special_anim(sp)))
                self.special_map[ref] = (t, sg.special_anim(sp))
        self.ads = [a for a in page.current()["ad_list"] if a.get("hits")]
        self.ad_map = {a["id"]: a for a in self.ads}
        self.steps = []

        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel(tr('Pasos del combo (en orden):')))
        self.list = QListWidget()
        left.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.sp_box = QComboBox()
        for ref, t, _num in self.specials:
            self.sp_box.addItem(t, ref)
        row.addWidget(self.sp_box, 1)
        self.sp_v = QComboBox()
        for v_ in range(3):
            self.sp_v.addItem(tr(sg.STRENGTH[v_]), v_)
        self.sp_v.setCurrentIndex(2)
        row.addWidget(self.sp_v)
        b = QPushButton(tr('➕ Especial'))
        b.setToolTip(tr('Opener (para empezar) o linker (después de un autodoble).'))
        b.clicked.connect(self.add_special)
        row.addWidget(b)
        left.addLayout(row)
        row = QHBoxLayout()
        self.ad_box = QComboBox()
        for a in self.ads:
            self.ad_box.addItem(self.ad_name(a), a["id"])
        row.addWidget(self.ad_box, 1)
        b = QPushButton(tr('➕ Autodoble'))
        b.clicked.connect(lambda: self.ad_box.currentData() and self.add(("ad", self.ad_box.currentData())))
        row.addWidget(b)
        left.addLayout(row)
        row = QHBoxLayout()
        self.end_box = QComboBox()
        for ref, t, _num in self.enders + [(r, t, n) for r, t, n in self.specials
                                           if self.kind.get(r + "#type") in ("hit", "dash", "rise")]:
            self.end_box.addItem(t, ref)
        row.addWidget(self.end_box, 1)
        b = QPushButton(tr('💥 Remate'))
        b.setToolTip(tr('Ender: después de un autodoble. Tumba y cierra el combo.'))
        b.clicked.connect(lambda: self.end_box.currentData() and self.add(("end", self.end_box.currentData())))
        row.addWidget(b)
        left.addLayout(row)
        row = QHBoxLayout()
        b = QPushButton(tr('🗑 Quitar'))
        b.clicked.connect(self.remove)
        row.addWidget(b)
        b = QPushButton(tr('↺ Combo de ejemplo'))
        b.setToolTip(tr('Especial → autodoble → especial → autodoble… con lo que escogiste en cada autodoble.'))
        b.clicked.connect(self.example)
        row.addWidget(b)
        left.addLayout(row)
        note = QLabel(tr('El rival es un muñeco: solo se ve cuándo pega cada golpe y cuántos van. '
                         'Las distancias y los empujones son los del juego solo en «Probar en IKEMEN».'))
        note.setWordWrap(True)
        left.addWidget(note)
        lw = QWidget()
        lw.setLayout(left)
        lw.setFixedWidth(400)
        lay.addWidget(lw)
        right = QVBoxLayout()
        self.canvas = ComboCanvas(self)
        right.addWidget(self.canvas, 1)
        right.addWidget(PlaybackBar(self.canvas))
        close = QPushButton(tr('Cerrar'))
        close.clicked.connect(self.accept)
        right.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        lay.addLayout(right, 1)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(lambda: advance(self.canvas))
        self.timer.start()
        self.example()

    # ---- pasos
    def ad_name(self, a):
        return f"🔁 {a.get('name') or tr('Autodoble')} ({tr(sg.STRENGTH[int(a.get('strength', 1))]).lower()})"

    def problem(self, i):
        """Por qué este paso no saldría en el juego (o None)."""
        c = self.page.current()
        st = self.steps[i]
        prev = self.steps[i - 1] if i > 0 else None
        if st[0] == "ad":
            ad = self.ad_map.get(st[1])
            if ad is None:
                return tr('ese autodoble ya no está')
            if prev is None or prev[0] != "sp":
                return tr('el autodoble va después de un especial')
            if self.kind.get(prev[1] + "#type") == "rise":
                return tr('el gancho deja al rival en el aire: el autodoble solo sale con el rival en el suelo')
            if ad.get("open") and ad["open"] != prev[1]:
                return tr('este autodoble inicia con «{0}»').format(
                    self.special_map.get(ad["open"], (ad["open"], None))[0].lstrip("🔥⭐🥋 "))
            if c.get("ad_rule") == "classic":
                pv = 2 if self.kind.get(prev[1]) == "super" else int(prev[2])
                want = (pv - 1) % 3
                if want != int(ad.get("strength", 1)):
                    return tr('con la regla clásica, después de un especial {0} va el autodoble {1}').format(
                        tr(sg.STRENGTH[pv]).lower(), tr(sg.STRENGTH[want]).lower())
        if st[0] == "end":
            if prev is None or prev[0] != "ad":
                return tr('el remate va después de un autodoble')
            if self.kind.get(st[1]) != "ender":
                if not c.get("enders"):
                    return tr('el remate está apagado')
                if self.kind.get(st[1] + "#type") not in ("hit", "dash", "rise"):
                    return tr('solo rematan los especiales que pegan con el cuerpo (golpe, embestida o gancho)')
        if st[0] == "sp" and prev is not None and prev[0] == "end":
            return tr('después del remate el combo ya se acabó')
        mx = int(c.get("ad_max") or 0)
        if mx:
            n_ad = sum(1 for x in self.steps[:i + 1] if x[0] == "ad")
            if st[0] == "ad" and n_ad > mx:
                return tr('solo se permiten {0} autodobles por combo').format(mx)
            if st[0] == "sp" and prev is not None and prev[0] == "ad" and n_ad >= mx:
                return tr('el autodoble número {0} tumba al rival: ahí solo queda el remate').format(mx)
        return None

    def step_text(self, st):
        if st[0] == "ad":
            ad = self.ad_map.get(st[1])
            return self.ad_name(ad) if ad else "🔁 ?"
        name = self.special_map.get(st[1], (st[1], None))[0]
        if st[0] == "end":
            return "💥 " + tr('Remate') + ": " + name.lstrip("🔥⭐🥋💥 ")
        if self.kind.get(st[1]) == "super":
            return name
        return f"{name} ({tr(sg.STRENGTH[int(st[2])]).lower()})"

    def refresh(self):
        self.list.clear()
        for i, st in enumerate(self.steps):
            why = self.problem(i)
            self.list.addItem(self.step_text(st) + (f"   ⚠ {why}" if why else ""))
        self.build()

    def add(self, st):
        self.steps.append(st)
        self.refresh()

    def add_special(self):
        ref = self.sp_box.currentData()
        if ref:
            self.add(("sp", ref, int(self.sp_v.currentData())))

    def remove(self):
        r = self.list.currentRow()
        if 0 <= r < len(self.steps):
            del self.steps[r]
            self.refresh()

    def example(self):
        """Opener → autodoble → linker → autodoble… → remate, según las reglas que escogiste."""
        c = self.page.current()
        prio = {"hit": 0, "dash": 1}                 # el gancho que sube deja en el aire: no abre autodobles
        normal_sp = [(ref, t, num) for ref, t, num in self.specials if self.kind.get(ref) != "super"]
        body = sorted([ref for ref, _t, num in normal_sp
                       if self.kind.get(ref + "#type") in prio and self.page.hits(num)],
                      key=lambda r: prio[self.kind[r + "#type"]])
        hitting = body or [ref for ref, _t, num in normal_sp if self.page.hits(num)
                           and self.kind.get(ref + "#type") != "rise"]
        first = hitting[0] if hitting else next(iter(self.special_map), None)
        classic = c.get("ad_rule") == "classic"
        steps = []
        for ad in self.ads:
            if not ad_actions(self, ad):
                continue
            opener = ad.get("open") or first
            if not opener:
                continue
            steps.append(("sp", opener, (int(ad.get("strength", 1)) + 1) % 3 if classic else 2))
            steps.append(("ad", ad["id"]))
        if steps:
            if self.enders:
                steps.append(("end", self.enders[0][0]))
            elif c.get("enders") and body:
                steps.append(("end", body[0]))
        self.steps = steps
        self.refresh()

    # ---- la animación entera
    def build(self):
        segs = []
        for i, st in enumerate(self.steps):
            if st[0] == "ad":
                acts = ad_actions(self, self.ad_map.get(st[1]) or {})
            else:
                a = find_action(self, self.special_map.get(st[1], (None, None))[1])
                acts = [(a, 100)] if a is not None else []
            segs.append((self.step_text(st), acts, st[0], self.problem(i)))
        self.timeline = make_timeline(self, segs)
        self.canvas.tick = 0
        self.canvas.update()
