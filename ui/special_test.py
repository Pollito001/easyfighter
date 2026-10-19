"""Prueba de un especial o súper del modo simple: el personaje hace el movimiento con todos sus eventos
(impulsos, despegue, teletransporte, proyectiles, efectos, estela, destellos, sacudidas…) y choca con un rival
de prueba. En los proyectiles se puede tocar donde quieres que salga."""
import random

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core import simple_gen as sg
from core import special_events as sev
from i18n import tr
from ui import theme

VX_MUL = [0.75, 1.0, 1.25, 1.15]


def _frames_of(ent):
    if not isinstance(ent, dict):
        return [], 4
    return sg._frames(ent), max(1, int(ent.get("time", 4)))


def _at(frames, time, t, loop=False):
    """Cuadro de una animación en el tick t (None si ya terminó y no se repite)."""
    if not frames:
        return None
    total = len(frames) * time
    if loop:
        t %= max(1, total)
    if t < 0 or t >= total:
        return None
    return frames[int(t // time)]


class Sim:
    """Simula el especial tick por tick (como lo haría el juego, sin el rival)."""

    def __init__(self, dlg, version):
        self.d = d = dlg
        sp = d.sp
        self.sp = sp
        self.v = version
        vv = version
        self.vv = vv
        self.k = d.k
        self.g = d.gravity
        self.keys = sg._frames(sp)
        self.time = max(1, int(sp.get("time", 4)))
        self.n = len(self.keys)
        self.prm = d.params()
        self.events = [e for e in (sp.get("events") or []) if isinstance(e, dict)]
        self.hit_frames = self.hits()
        self.frames = []
        self.run()

    def tick_of(self, ev):
        f = ev.get("frame")
        if not f:
            return 0
        f = max(1, min(int(f), max(1, self.n)))
        return (f - 1) * self.time + int(ev.get("delay") or 0)

    def hits(self):
        sp = self.sp
        typ = sp.get("type", "proj")
        out = set()
        if typ in ("hit", "dash", "rise"):
            manual = {int(f) - 1 for f in sp.get("hit_frames") or [] if 1 <= int(f) <= self.n}
            if manual:
                out |= manual
            elif self.n:
                hf = self.prm["hf"]
                out |= set(range(hf, self.n)) if int(sg.spec(sp, "hits")) > 1 else {hf}
        for ev in self.events:
            if ev.get("type") == "hit" and ev.get("frame"):
                f0 = int(ev["frame"]) - 1
                out |= set(range(f0, self.n)) if int(sev.val(ev, "hits")) > 1 else {f0}
        return out

    def run(self):
        d, sp, k = self.d, self.sp, self.k
        x = y = vx = vy = 0.0
        air = sp.get("type") == "rise" and not sp.get("evmode")
        gmul = 1.0
        frozen = 0
        facing = 1
        projs = []      # {keys, time, hit, x, y, vx, vy, ax, ay, t0, hit_t}
        effects = []    # {keys, time, x, y, follow, dx, dy, t0, dur, scale, ontop, pos}
        timed = []      # (tipo, desde, hasta, datos)
        trail = []
        badges = []
        body_len = self.n * self.time
        total = self.d.cycle()
        target = d.target_dist
        evs = sorted(((self.tick_of(e), i, e) for i, e in enumerate(self.events)), key=lambda t: (t[0], t[1]))
        t = 0           # tiempo del especial (no corre durante una pausa que congela al personaje)
        paused = 0
        pause_ev = None
        pause_n = 0
        stop_on_hit = bool(sg.spec(sp, "stop_on_hit")) and sp.get("type") in ("dash", "hit")
        stopped = False
        last = None
        for _rt in range(total):
            if paused > 0 and last is not None:
                # pausa con destello: todo se queda quieto en ese cuadro
                paused -= 1
                fr = dict(last)
                kind = "selfpause" if pause_ev.get("type") == "selfpause" else "superpause"
                fr["fx"] = [f for f in last["fx"] if f[0] not in ("superpause", "selfpause")] + [
                    (kind, pause_ev, pause_n - paused - 1, pause_n)]
                self.frames.append(fr)
                continue
            for tt, _i, ev in evs:
                if tt != t:
                    continue
                typ = ev.get("type")
                if ev.get("main") or (ev.get("raw") and typ not in ("move", "posadd", "sound")):
                    if ev.get("raw") and typ in ("hit", "proj", "effect"):
                        badges.append((t, t + 30, sev.summary(ev, tr)))
                    continue
                if typ == "move":
                    s = max(0.25, float(sev.val(ev, "speed")) / 100.0)
                    mx = my = 1.0
                    if sev.val(ev, "by_version"):
                        mx, my = VX_MUL[self.vv], 0.85 + 0.15 * min(self.vv, 2)
                    nx = float(sev.val(ev, "x")) * k * mx * s * facing
                    ny = -float(sev.val(ev, "y")) * k * my * s
                    if sev.val(ev, "mode") == "set":
                        vx = nx
                        if float(sev.val(ev, "y")) != 0 or sev.val(ev, "air"):
                            vy = ny
                    else:
                        vx += nx
                        vy += ny
                    if sev.val(ev, "air"):
                        air = True
                        gmul = s * s
                elif typ == "posadd":
                    x += float(sev.val(ev, "x")) * k * facing
                    y -= float(sev.val(ev, "y")) * k
                elif typ == "teleport":
                    dist = float(sev.val(ev, "dist")) * k
                    w = sev.val(ev, "where")
                    if w == "fwd":
                        x += dist * facing
                    elif w == "front":
                        x = target - dist
                    else:
                        x = target + dist
                        facing = -facing
                elif typ == "turn":
                    facing = -facing
                elif typ == "freeze":
                    frozen = max(frozen, int(sev.val(ev, "ticks")))
                elif typ == "proj":
                    pk, ptime = _frames_of(ev.get("anim"))
                    hk, htime = _frames_of(ev.get("anim_hit"))
                    if pk:
                        sc = d.scale
                        projs.append(dict(keys=pk, time=ptime, hit=hk, htime=htime,
                                          x=x + int(sev.val(ev, "x")) * k * sc * facing,
                                          y=y + int(sev.val(ev, "y")) * k * sc,
                                          vx=float(sev.val(ev, "vx")) * k * facing,
                                          vy=-float(sev.val(ev, "vy")) * k,
                                          ax=float(sev.val(ev, "ax")) * k * facing,
                                          ay=-float(sev.val(ev, "ay")) * k, t0=t, hit_t=None, facing=facing))
                elif typ == "effect":
                    ek, etime = _frames_of(ev.get("anim"))
                    if ek:
                        dur = int(sev.val(ev, "time"))
                        dur = len(ek) * etime if dur < 0 else dur
                        effects.append(dict(keys=ek, time=etime, dx=int(sev.val(ev, "x")) * k,
                                            dy=int(sev.val(ev, "y")) * k, pos=sev.val(ev, "pos"),
                                            follow=bool(sev.val(ev, "follow")), x=x, y=y, t0=t, dur=max(1, dur),
                                            scale=float(sev.val(ev, "scale")), ontop=bool(sev.val(ev, "ontop")),
                                            facing=facing))
                elif (typ == "superpause" and sev.val(ev, "hold")) or typ == "selfpause":
                    paused = int(sev.val(ev, "ticks"))
                    pause_ev, pause_n = ev, paused
                elif typ in ("afterimage", "flash", "shake", "superpause", "invuln", "counter", "screencolor",
                             "trans"):
                    n = int(sev.val(ev, "ticks"))
                    timed.append((typ, t, t + n, ev))
                elif typ == "followup":
                    badges.append((t, t + 40, "➡ " + tr('Seguir con otro especial')))
                elif typ == "custom":
                    badges.append((t, t + 30, "🧩 " + tr('Código propio')))
            # moverse
            if stopped:
                vx = 0.0            # «Se detiene al pegar»
            if frozen > 0:
                frozen -= 1
            else:
                x += vx
                y += vy
                if air:
                    vy += self.g * gmul
                    if y >= 0 and vy > 0:
                        y = 0.0
                        vx = vy = 0.0
                        air = False
            # proyectiles
            for pj in projs:
                if pj["hit_t"] is not None:
                    continue
                pj["x"] += pj["vx"]
                pj["y"] += pj["vy"]
                pj["vx"] += pj["ax"]
                pj["vy"] += pj["ay"]
                if (pj["facing"] > 0 and pj["x"] >= target) or (pj["facing"] < 0 and pj["x"] <= target) or pj["y"] > 0:
                    pj["hit_t"] = t
            # cuadro del cuerpo
            if t < body_len:
                fi = int(t // self.time)
            elif air:
                fi = self.n - 1
            else:
                fi = None
            key = self.keys[fi] if (fi is not None and self.keys) else (self.keys[-1] if self.keys else None)
            if stop_on_hit and fi in self.hit_frames:
                stopped = True
            trail.append((x, y, key, facing))
            frame = dict(t=t, x=x, y=y, key=key, fi=fi, facing=facing, hit=fi in self.hit_frames,
                         projs=[], effects=[], fx=[], badges=[b[2] for b in badges if b[0] <= t < b[1]])
            for pj in projs:
                if t < pj["t0"]:
                    continue
                if pj["hit_t"] is None:
                    kk = _at(pj["keys"], pj["time"], t - pj["t0"], loop=True)
                    if kk is not None:
                        frame["projs"].append((kk, pj["x"], pj["y"], pj["facing"]))
                elif pj["hit"]:
                    kk = _at(pj["hit"], pj["htime"], t - pj["hit_t"])
                    if kk is not None:
                        frame["projs"].append((kk, pj["x"], pj["y"], pj["facing"]))
            for ef in effects:
                if not (ef["t0"] <= t < ef["t0"] + ef["dur"]):
                    continue
                kk = _at(ef["keys"], ef["time"], t - ef["t0"], loop=True)
                if kk is None:
                    continue
                if ef["pos"] == "p2":
                    bx, by = target, 0.0
                elif ef["pos"] == "front":
                    bx, by = None, 0.0
                elif ef["follow"]:
                    bx, by = x, y
                else:
                    bx, by = ef["x"], ef["y"]
                frame["effects"].append((kk, bx, by, ef["dx"] * ef["facing"], ef["dy"], ef["scale"], ef["ontop"]))
            for typ, a, b, ev in timed:
                if a <= t < b:
                    frame["fx"].append((typ, ev, t - a, b - a))
            frame["trail"] = trail[-24:]
            self.frames.append(frame)
            last = frame
            t += 1


class SpecialCanvas(QWidget):
    picked = pyqtSignal(int, int)

    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg
        self.tick = 0
        self.setMinimumSize(QSize(760, 380))
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.step)
        self.timer.start()
        self.tint_cache = {}

    def step(self):
        from ui.common import advance
        advance(self)

    # ---- escala
    def layout_(self):
        d = self.dlg
        tall = max(60.0, d.char_h * d.scale)
        z = min((self.height() - 70) / (tall * 1.9), 3.0)
        oy = self.height() - 40
        ox = 90 + d.char_w * d.scale * z * 0.6
        return z, ox, oy

    def mousePressEvent(self, e):
        d = self.dlg
        if not d.pick.isChecked():
            return
        z, ox, oy = self.layout_()
        px = (e.position().x() - ox) / (z * d.scale)
        py = (e.position().y() - oy) / (z * d.scale)
        self.picked.emit(int(round(px)), int(round(py)))

    def frame_at(self, frames, time, t, loop=False, hold=True):
        if not frames:
            return None, True
        total = len(frames) * time
        if loop:
            t %= max(1, total)
        if t >= total:
            return (frames[-1] if hold else None), True
        return frames[int(t // time)], False

    def tinted(self, key, color):
        ck = (key, color)
        if ck not in self.tint_cache:
            pm = self.dlg.sm.pixmap(*key)
            if pm is None:
                return None
            out = QPixmap(pm)
            p = QPainter(out)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            p.fillRect(out.rect(), QColor(*color))
            p.end()
            self.tint_cache[ck] = out
        return self.tint_cache[ck]

    def draw_sprite(self, p, key, x, y, z, scale, alpha=1.0, facing=1, pm=None):
        sm = self.dlg.sm
        s = sm.sprite(*key)
        pm = pm or (sm.pixmap(*key) if s is not None else None)
        if pm is None or s is None:
            return
        p.save()
        p.setOpacity(alpha)
        p.translate(x, y)
        if facing < 0:
            p.scale(-1, 1)
        p.drawPixmap(QRectF(-s.x * scale * z, -s.y * scale * z, pm.width() * scale * z, pm.height() * scale * z),
                     pm, QRectF(pm.rect()))
        p.restore()

    def draw_beam(self, p, sp, pk, ptime, hit_t, x0, y0, z, sc, ground=None, rival_x=None):
        """El rayo como en el juego: carga → boca, cuerpo estirado y punta → se apaga. Puede caer del cielo o
        salir del piso (girado) y ser varios, uno tras otro."""
        d = self.dlg
        parts = {key: (sg._frames(sp.get(key) or {}), max(1, int((sp.get(key) or {}).get("time", 3))))
                 for key in ("beam_charge", "beam_head", "beam_tip")}
        ck, ct = parts["beam_charge"]
        c = len(ck) * ct if ck else 0
        t_ = int(sg.spec(sp, "beam_time"))
        end = sg.spec(sp, "beam_end") or "axis"
        fade = 0 if end == "none" else 10
        bdir = sg.spec(sp, "beam_dir") or "forward"
        vert = bdir != "forward"
        length = (int(sg.spec(sp, "beam_len")) or (230 if vert else 420) * d.k) * sc * z
        count = max(1, min(8, int(sg.spec(sp, "beam_count"))))
        delay = max(0, int(sg.spec(sp, "beam_delay"))) if count > 1 else 0
        step = int(sg.spec(sp, "beam_step")) * d.k * sc * z
        aim = sg.spec(sp, "beam_aim") or "front"
        s0 = d.sm.sprite(*pk[0]) if pk else None
        standing = False
        if s0 is not None:
            ph, pw = s0.pixels().shape[:2]
            standing = sg.beam_standing(sp, pw, ph)
        total = c + t_ + fade
        loop = max(len(d.sim().frames), hit_t + total + (count - 1) * delay + 15)
        t0 = self.tick % loop - hit_t
        if ground is None:
            ground = y0
        for j in range(count):
            bt = t0 - j * delay
            if bt < 0 or bt >= total:
                continue
            if vert:
                if aim == "rival" and rival_x is not None:
                    bx = rival_x + (j - (count - 1) / 2.0) * step
                else:
                    bx = x0 + j * step
                by = ground - length if bdir == "down" else ground
            else:
                bx, by = x0 + j * step, y0
            p.save()
            p.translate(bx, by)
            if vert and not standing:
                p.rotate(90 if bdir == "down" else -90)      # dibujado acostado y girado, como en el juego
            self.draw_beam_one(p, sp, pk, ptime, parts, bt, c, t_, fade, end, length, z, sc, vert, standing, bdir)
            p.restore()

    def draw_beam_one(self, p, sp, pk, ptime, parts, bt, c, t_, fade, end, length, z, sc, vert=False,
                      standing=False, bdir="forward"):
        """Un rayo, dibujado desde (0, 0) hacia la derecha (el que llama lo pone en su sitio y lo gira)."""
        import math
        d = self.dlg
        x0 = y0 = 0
        ck, ct = parts["beam_charge"]
        grow = max(1, int(sg.spec(sp, "beam_grow")))
        if bt < c:
            k2, _ = self.frame_at(ck, ct, bt)
            if k2 is not None:
                self.draw_sprite(p, k2, x0, y0, z, sc)
            return
        tt = bt - c
        cur = length * min(1.0, (tt + 1) / grow)
        fx = sg.spec(sp, "beam_fx") or "none"
        rate = max(1, int(sg.spec(sp, "beam_fx_rate")))
        alpha, thick = 1.0, 1.0
        if fx == "blink" and (tt // rate) % 2 == 1:
            alpha = 0.0
        if fx == "pulse":
            alpha = (165 + 90 * math.sin(tt * 3.1416 / rate)) / 256
        if fx == "wobble":
            thick = 1 + 0.2 * math.sin(tt * 3.1416 / rate)
        if bt >= c + t_ and fade:
            k_ = (c + t_ + fade - bt) / fade
            alpha = alpha * k_
            if end in ("axis", "center"):
                thick = thick * k_
        kb, _ = self.frame_at(pk, ptime, tt, loop=True)
        s = d.sm.sprite(*kb) if kb else None
        pm = d.sm.pixmap(*kb) if s is not None else None
        if standing:
            # dibujado de pie: no se gira; se estira hacia abajo (cae) o hacia arriba (sube) y se afina de lado
            down = bdir == "down"
            if pm is not None and alpha > 0:
                p.save()
                p.setOpacity(max(0.0, min(1.0, alpha)))
                left = x0 - (pm.width() / 2 if end == "center" else s.x) * sc * z
                p.translate(x0, 0)
                p.scale(thick, 1)
                p.translate(-x0, 0)
                r = QRectF(left, y0 if down else y0 - cur, pm.width() * sc * z, cur)
                p.drawPixmap(r, pm, QRectF(pm.rect()))
                p.restore()
            for key, yy in (("beam_head", y0), ("beam_tip", y0 + cur if down else y0 - cur)):
                keys, tm = parts[key]
                if keys and alpha > 0 and thick > 0:
                    k3, _ = self.frame_at(keys, tm, tt, loop=True)
                    p.save()
                    p.translate(x0, 0)
                    p.scale(thick, 1)
                    p.translate(-x0, 0)
                    self.draw_sprite(p, k3, x0, yy, z, sc, alpha=max(0.0, min(1.0, alpha)))
                    p.restore()
            return
        # la línea hacia la que se achica todo: el eje del cuerpo, o el centro de su dibujo
        line = y0
        shift = 0.0
        if end == "center" and pm is not None:
            line = y0 + (pm.height() / 2 - s.y) * sc * z
            if vert:
                # girado: en el juego la mitad de la columna queda justo donde sale
                shift = y0 - line
                line = y0
        if pm is not None and alpha > 0:
            p.save()
            p.setOpacity(max(0.0, min(1.0, alpha)))
            h = pm.height() * sc * z
            top = y0 - s.y * sc * z + shift
            p.translate(0, line)
            p.scale(1, thick)
            p.translate(0, -line)
            p.drawPixmap(QRectF(x0, top, cur, h), pm, QRectF(pm.rect()))
            p.restore()
        for key, xx in (("beam_head", x0), ("beam_tip", x0 + cur)):
            keys, tm = parts[key]
            if keys and alpha > 0 and thick > 0:
                k3, _ = self.frame_at(keys, tm, tt, loop=True)
                p.save()
                p.translate(0, line)
                p.scale(1, thick)
                p.translate(0, -line)
                self.draw_sprite(p, k3, xx, y0, z, sc, alpha=max(0.0, min(1.0, alpha)))
                p.restore()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.CANVAS))
        d = self.dlg
        sim = d.sim()
        z, ox, oy = self.layout_()
        sc = d.scale
        if not sim.frames:
            p.end()
            return
        fr = sim.frames[self.tick % len(sim.frames)]
        fx = {t: (ev, a, n) for t, ev, a, n in fr["fx"]}
        # sacudir la pantalla
        if "shake" in fx:
            ev, _a, _n = fx["shake"]
            amp = int(sev.val(ev, "ampl")) * z * 0.6
            p.translate(random.uniform(-amp, amp), random.uniform(-amp, amp))
        # pausa con destello: todo se oscurece
        if "superpause" in fx and sev.val(fx["superpause"][0], "darken"):
            p.fillRect(self.rect().adjusted(-40, -40, 40, 40), QColor(0, 0, 0, 150))
        # color en la pantalla (por detrás: antes de dibujar al personaje)
        if "screencolor" in fx:
            ev, a, n = fx["screencolor"]
            p.fillRect(self.rect().adjusted(-40, -40, 40, 40),
                       QColor(int(sev.val(ev, "r")), int(sev.val(ev, "g")), int(sev.val(ev, "b")),
                              90 if sev.val(ev, "under") else 170))
        p.setPen(QPen(QColor(255, 107, 53, 160), 1))
        p.drawLine(0, int(oy), self.width(), int(oy))
        # rival de prueba
        target_x = d.target_dist
        tx = ox + target_x * z
        p.setPen(QPen(QColor(139, 147, 163, 160), 1, Qt.PenStyle.DashLine))
        p.setBrush(QColor(139, 147, 163, 40))
        th = d.char_h * sc * z
        p.drawRect(QRectF(tx, oy - th, 34 * d.k * z, th))
        p.setBrush(Qt.BrushStyle.NoBrush)
        bx, by = ox + fr["x"] * z, oy + fr["y"] * z

        def effect(e):
            kk, ex, ey, dx, dy, escale, _top = e
            if ex is None:
                px_ = self.width() - 60 + dx * z
            else:
                px_ = ox + (ex + dx) * z
            self.draw_sprite(p, kk, px_, oy + (ey + dy) * z, z, sc * escale)
        for e in fr["effects"]:
            if not e[6]:
                effect(e)
        # estela
        if "afterimage" in fx:
            for i, (x0, y0, k0, f0) in enumerate(fr["trail"][:-1:3]):
                if k0 is not None:
                    self.draw_sprite(p, k0, ox + x0 * z, oy + y0 * z, z, sc, alpha=0.12 + 0.05 * i, facing=f0,
                                     pm=self.tinted(k0, (90, 120, 255, 150)))
        # el personaje
        trans = fx.get("trans")
        hidden = trans is not None and sev.val(trans[0], "mode") == "invisible"
        if fr["key"] is not None and not hidden:
            pm = None
            alpha = 1.0
            if "flash" in fx:
                ev, a, n = fx["flash"]
                r, g, b = (max(0, min(255, int(sev.val(ev, c)) + 128)) for c in ("r", "g", "b"))
                pm = self.tinted(fr["key"], (r, g, b, int(150 * (1 - a / max(1, n)))))
            if "selfpause" in fx and sev.val(fx["selfpause"][0], "flash"):
                pm = self.tinted(fr["key"], (255, 255, 255, 110))
            if trans is not None:
                if sev.val(trans[0], "mode") == "add":
                    pm = self.tinted(fr["key"], (255, 255, 255, 120))
                    alpha = 0.75
                else:
                    alpha = 0.5
            self.draw_sprite(p, fr["key"], bx, by, z, sc, facing=fr["facing"], pm=pm, alpha=alpha)
            # caja de golpe en los cuadros que pegan
            if fr["hit"]:
                bxs = d.sm.auto_boxes_of(*fr["key"], True)
                if bxs and bxs[0]:
                    p.setPen(QPen(QColor(255, 70, 70, 230), 2))
                    p.setBrush(QColor(255, 70, 70, 60))
                    for x1, y1, x2, y2 in bxs[0]:
                        if fr["facing"] < 0:
                            x1, x2 = -x2, -x1
                        p.drawRect(QRectF(bx + x1 * sc * z, by + y1 * sc * z, (x2 - x1) * sc * z,
                                          (y2 - y1) * sc * z))
                    p.setBrush(Qt.BrushStyle.NoBrush)
        for e in fr["effects"]:
            if e[6]:
                effect(e)
        # el proyectil principal (pestaña «Proyectil»)
        sp = d.sp
        prm = sim.prm
        time = sim.time
        t = self.tick % len(sim.frames)
        main_on = sp.get("type", "proj") == "proj" and (
            not sp.get("evmode") or any(e.get("main") for e in sp.get("events") or []))
        if main_on:
            hit_t = prm["hf"] * time
            sx, sy = ox + prm["px"] * sc * z, oy + prm["py"] * sc * z
            p.setPen(QPen(QColor("#7CFC00"), 2))
            p.drawLine(int(sx - 8), int(sy), int(sx + 8), int(sy))
            p.drawLine(int(sx), int(sy - 8), int(sx), int(sy + 8))
            pk = sg._frames(sp.get("proj") or {})
            hk = sg._frames(sp.get("proj_hit") or {})
            ptime = max(1, int((sp.get("proj") or {}).get("time", 4)))
            htime = max(1, int((sp.get("proj_hit") or {}).get("time", 3)))
            beam = bool(sg.spec(sp, "proj_beam"))
            if beam and pk:
                self.draw_beam(p, sp, pk, ptime, hit_t, ox + prm["px"] * sc * z, oy + prm["py"] * sc * z, z, sc,
                               ground=oy, rival_x=tx + 17 * d.k * z)
            cnt = max(1, min(5, int(sg.spec(sp, "proj_count"))))
            spread = float(sg.spec(sp, "proj_spread")) * d.k
            if t >= hit_t and pk and not beam and cnt > 1:
                # abanico: los de más (el del medio lo dibuja lo de abajo)
                dt = t - hit_t
                vy0 = -float(sg.spec(sp, "proj_vy")) * d.k
                for j in range(cnt):
                    off = (j - (cnt - 1) / 2.0) * -spread
                    if abs(off) < 1e-6:
                        continue
                    x = prm["px"] * sc + prm["speed"] * dt
                    y = prm["py"] * sc + (vy0 + off) * dt
                    if x < target_x and y < 0:
                        k2, _ = self.frame_at(pk, ptime, dt, loop=True)
                        self.draw_sprite(p, k2, ox + x * z, oy + y * z, z, sc)
            if t >= hit_t and pk and not beam and not (cnt % 2 == 0):
                dt = t - hit_t
                vy = -float(sg.spec(sp, "proj_vy")) * d.k
                ax_, ay_ = float(sg.spec(sp, "proj_ax")) * d.k, -float(sg.spec(sp, "proj_ay")) * d.k
                x = prm["px"] * sc + prm["speed"] * dt + ax_ * dt * dt / 2
                y = prm["py"] * sc + vy * dt + ay_ * dt * dt / 2
                if x < target_x and y < 0:
                    k2, _ = self.frame_at(pk, ptime, dt, loop=True)
                    self.draw_sprite(p, k2, ox + x * z, oy + y * z, z, sc)
                else:
                    # cuándo llegó: se busca hacia atrás
                    tt = 0
                    while tt < dt:
                        xx = prm["px"] * sc + prm["speed"] * tt + ax_ * tt * tt / 2
                        yy = prm["py"] * sc + vy * tt + ay_ * tt * tt / 2
                        if xx >= target_x or yy >= 0:
                            break
                        tt += 1
                    k3, done = self.frame_at(hk, htime, dt - tt, hold=False)
                    if k3 is not None and not done:
                        xx = prm["px"] * sc + prm["speed"] * tt + ax_ * tt * tt / 2
                        yy = prm["py"] * sc + vy * tt + ay_ * tt * tt / 2
                        self.draw_sprite(p, k3, ox + xx * z, oy + min(0.0, yy) * z, z, sc)
        # el ayudante: aparece delante y avanza
        if sp.get("type") == "helper":
            hk = sg._frames(sp.get("proj") or {})
            if hk:
                htime_ = max(1, int((sp.get("proj") or {}).get("time", 4)))
                hit_t = prm["hf"] * time
                dt = t - hit_t
                life = min(int(sg.spec(sp, "helper_life")), len(hk) * htime_)
                if 0 <= dt < life:
                    k2, _ = self.frame_at(hk, htime_, dt, hold=True)
                    x = prm["px"] * sc + float(sg.spec(sp, "helper_speed")) * d.k * dt
                    y = prm["py"] * sc if sp.get("proj_y") is not None else 0
                    if k2 is not None:
                        self.draw_sprite(p, k2, ox + x * z, oy + y * z, z, sc)
        # proyectiles de los eventos
        for kk, x, y, f in fr["projs"]:
            self.draw_sprite(p, kk, ox + x * z, oy + y * z, z, sc, facing=f)
        # avisos
        p.resetTransform()
        y0 = 40
        marks = []
        if "invuln" in fx:
            marks.append("🛡 " + tr('Invencible'))
        if "counter" in fx:
            marks.append("🔁 " + tr('Contraataque'))
        if "selfpause" in fx:
            marks.append("⏯ " + tr('Pausa del personaje'))
        if fr["hit"]:
            marks.append("💥 " + tr('Pega'))
        for txt in marks + fr["badges"]:
            p.setPen(QColor(theme.ACCENT2))
            p.drawText(10, y0, txt)
            y0 += 18
        p.setPen(QColor(theme.MUTED))
        p.drawText(10, 20, d.info_text())
        p.end()


class SpecialTest(QDialog):
    positionChanged = pyqtSignal()

    def __init__(self, sm, sp):
        super().__init__(sm.main)
        self.sm = sm
        self.sp = sp
        self.k = sm.motion.k()
        self.scale = sm.motion.scale()
        self.gravity = sm.motion.gravity()
        self.target_dist = 220 * self.k
        self.char_h, self.char_w = self.char_size()
        self._sim = None
        self.setWindowTitle(tr('▶ Probar: {0}').format(sp.get("name", "")))
        self.resize(960, 600)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.version = QComboBox()
        for i in sg.sp_versions(sp):
            self.version.addItem(tr(sg.VERSION_NAMES[i]), i)
        row.addWidget(QLabel(tr('Versión:')))
        row.addWidget(self.version)
        self.pick = QCheckBox(tr('Tocar en la pantalla para elegir de dónde sale el proyectil'))
        self.pick.setVisible(sp.get("type", "proj") == "proj")
        row.addWidget(self.pick)
        row.addStretch(1)
        auto = QPushButton(tr('↺ Automático'))
        auto.setToolTip(tr('Vuelve a calcular de dónde sale el proyectil (de la mano o el pie que pega).'))
        auto.setVisible(sp.get("type", "proj") == "proj")
        auto.clicked.connect(self.auto_pos)
        row.addWidget(auto)
        lay.addLayout(row)
        self.canvas = SpecialCanvas(self)
        self.canvas.picked.connect(self.on_pick)
        lay.addWidget(self.canvas, 1)
        from ui.common import PlaybackBar
        lay.addWidget(PlaybackBar(self.canvas))
        hint = QLabel(tr('Verde: de dónde sale el proyectil · gris: un rival de prueba · rojo: la caja de golpe. '
                         'Se ven los eventos (impulsos, proyectiles, efectos, estela, destellos, sacudidas…). '
                         'La prueba se repite sola.'))
        hint.setWordWrap(True)
        hint.setObjectName("CardPath")
        lay.addWidget(hint)
        b = QPushButton(tr('Cerrar'))
        b.clicked.connect(self.accept)
        lay.addWidget(b, 0, Qt.AlignmentFlag.AlignRight)
        self.version.currentIndexChanged.connect(self.restart)

    def restart(self, *_a):
        self._sim = None
        self.canvas.tick = 0

    def sim(self):
        if self._sim is None:
            v = self.version.currentData()
            self._sim = Sim(self, 1 if v is None else int(v))
        return self._sim

    def char_size(self):
        p = self.sm.main.project
        a = p.air.find(0)
        if a and a.frames:
            s = self.sm.sprite(a.frames[0].group, a.frames[0].number)
            if s is not None:
                return float(s.y), float(s.pixels().shape[1])
        return 100.0 * self.k, 50.0 * self.k

    def params(self):
        v = self.version.currentData()
        return sg.special_params(self.sp, 1 if v is None else int(v), self.sm.main.project.sff.index(), self.k)

    def cycle(self):
        """Cuántos ticks dura una vuelta de la prueba (hasta que todo terminó, más un respiro)."""
        sp = self.sp
        time = max(1, int(sp.get("time", 4)))
        body = len(sg._frames(sp)) * time
        prm = self.params()
        extra = 40
        if sp.get("type") == "proj":
            dist = max(0.0, self.target_dist - prm["px"] * self.scale)
            extra = max(extra, int(dist / max(0.1, prm["speed"])) + prm["hf"] * time - body + 40)
        for ev in sp.get("events") or []:
            t0 = (max(1, int(ev.get("frame") or 1)) - 1) * time + int(ev.get("delay") or 0)
            typ = ev.get("type")
            if typ == "move" and ev.get("air"):
                s = max(0.25, float(sev.val(ev, "speed")) / 100.0)
                vy = float(sev.val(ev, "y")) * self.k * s
                air = int(2 * vy / max(0.01, self.gravity * s * s)) if vy > 0 else 0
                extra = max(extra, t0 + air - body + 30)
            elif typ == "proj":
                vx = abs(float(sev.val(ev, "vx"))) * self.k
                extra = max(extra, t0 + int(self.target_dist / max(0.5, vx)) - body + 40)
            elif typ in ("effect",):
                dur = int(sev.val(ev, "time"))
                extra = max(extra, t0 + (dur if dur > 0 else 60) - body + 20)
            elif typ in ("freeze", "afterimage", "flash", "shake", "superpause", "selfpause", "screencolor",
                         "trans"):
                extra = max(extra, t0 + int(sev.val(ev, "ticks")) - body + 20)
        # las pausas que congelan al personaje alargan la prueba
        held = sum(int(sev.val(e, "ticks")) for e in sp.get("events") or []
                   if not e.get("raw") and ((e.get("type") == "superpause" and sev.val(e, "hold"))
                                            or e.get("type") == "selfpause"))
        return min(1500, max(30, body + max(30, extra)) + held)

    def info_text(self):
        prm = self.params()
        if self.sp.get("type") == "proj":
            return tr('Sale desde: {0}, {1} · velocidad {2:.1f}').format(prm["px"], prm["py"], prm["speed"])
        return ""

    def on_pick(self, x, y):
        self.sp["proj_x"], self.sp["proj_y"] = x, y
        self.restart()
        self.positionChanged.emit()

    def auto_pos(self):
        self.sp.pop("proj_x", None)
        self.sp.pop("proj_y", None)
        self.restart()
        self.positionChanged.emit()

