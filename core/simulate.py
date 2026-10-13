"""
Simulador de estados (.cns / .st de MUGEN): ejecuta un [Statedef] tick a tick con la física básica,
para ver cómo se mueve un ataque o un movimiento sin abrir el juego.

Simula: tiempo, animación (AnimTime, AnimElem…), VelSet/VelAdd/VelMul, PosSet/PosAdd, ChangeState,
ChangeAnim, CtrlSet, VarSet/VarAdd, StateTypeSet, Turn, Gravity, PlaySnd, HitDef (se marca), la física
S / C / A / N y una evaluación de expresiones con los triggers más usados. Lo que no simula, lo anota.
"""
import math
import random
import re

from core.codeinfo import strip_comment

# ---------------------------------------------------------------- lectura de estados
SEC = re.compile(r"^\s*\[\s*(statedef|state)\s*([^\]]*)\]?", re.IGNORECASE)


def parse_states(text, source=""):
    """{número: {"params": {}, "ctrls": [ {type, params, triggers, line, name} ], "line": n, "source": …}}"""
    states, cur, ctrl = {}, None, None
    block, gap = [], False
    for n, raw in enumerate(text.split("\n"), 1):
        line = strip_comment(raw).strip()
        if not line:
            if not raw.strip():
                gap = True
                continue
            c = raw.strip().lstrip(";").strip(" -=;*")
            if gap:
                block, gap = [], False
            if c:
                block.append(c if len(c) <= 40 else c[:38] + "…")
            continue
        gap = False
        last_comment = block[0] if block else ""
        block = []
        m = SEC.match(line)
        if m:
            kind, rest = m.group(1).lower(), m.group(2).strip()
            if kind == "statedef":
                try:
                    num = int(rest.split(",")[0].split()[0])
                except (ValueError, IndexError):
                    cur = None
                    continue
                cur = {"params": {}, "ctrls": [], "line": n, "source": source, "title": last_comment}
                states[num] = cur
                ctrl = None
            elif cur is not None:
                name = rest.split(",", 1)[1].strip() if "," in rest else rest
                ctrl = {"type": "", "params": {}, "triggers": {}, "line": n, "name": name}
                cur["ctrls"].append(ctrl)
            continue
        if line.startswith("["):
            cur, ctrl = None, None
            continue
        if cur is None or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip().lower(), val.strip()
        if ctrl is None:
            cur["params"][key] = val
            continue
        if key == "type":
            ctrl["type"] = val.lower()
        elif key == "triggerall":
            ctrl["triggers"].setdefault(0, []).append(val)
        elif re.match(r"trigger\d+$", key):
            ctrl["triggers"].setdefault(int(key[7:]), []).append(val)
        else:
            ctrl["params"][key] = val
    return states


def parse_constants(text):
    """Constantes de [Velocity], [Movement], [Size], [Data] como {"velocity.walk.fwd.x": 2.4, …}."""
    out, sec = {}, ""
    for raw in text.split("\n"):
        line = strip_comment(raw).strip()
        m = re.match(r"^\[\s*(\w+)\s*\]", line)
        if m:
            sec = m.group(1).lower()
            continue
        if sec in ("velocity", "movement", "size", "data") and "=" in line:
            k, _, v = line.partition("=")
            k = k.strip().lower()
            vals = []
            for x in v.split(","):
                try:
                    vals.append(float(x))
                except ValueError:
                    pass
            if not vals:
                continue
            if len(vals) >= 2 or sec in ("velocity",):
                out[f"{sec}.{k}.x"] = vals[0]
                if len(vals) >= 2:
                    out[f"{sec}.{k}.y"] = vals[1]
            out[f"{sec}.{k}"] = vals[0]
    return out


# ---------------------------------------------------------------- expresiones
TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|(\"[^\"]*\")|(&&|\|\||\^\^|!=|<=|>=|:=|\*\*|[-+*/%()<>=!,\[\]&|^~:])|([A-Za-z_][\w.]*))")


class Undefined(Exception):
    pass


class Expr:
    def __init__(self, text, sim):
        self.text = text
        self.sim = sim
        self.toks = []
        pos = 0
        while pos < len(text):
            m = TOKEN.match(text, pos)
            if not m or m.end() == pos:
                if text[pos:].strip() == "":
                    break
                raise Undefined(f"no entiendo «{text[pos:pos + 12]}»")
            pos = m.end()
            num, s, op, ident = m.groups()
            if num is not None:
                self.toks.append(("num", float(num) if "." in num else int(num)))
            elif s is not None:
                self.toks.append(("str", s[1:-1]))
            elif op is not None:
                self.toks.append(("op", op))
            elif ident is not None:
                self.toks.append(("id", ident))
        self.i = 0

    def peek(self, k=0):
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else (None, None)

    def take(self):
        t = self.peek()
        self.i += 1
        return t

    def accept(self, op):
        if self.peek() == ("op", op):
            self.i += 1
            return True
        return False

    def value(self):
        v = self.parse_or()
        return v

    def parse_or(self):
        v = self.parse_and()
        while self.peek() in (("op", "||"), ("op", "^^")):
            op = self.take()[1]
            r = self.parse_and()
            v = int(bool(v) or bool(r)) if op == "||" else int(bool(v) != bool(r))
        return v

    def parse_and(self):
        v = self.parse_bitor()
        while self.accept("&&"):
            r = self.parse_bitor()
            v = int(bool(v) and bool(r))
        return v

    def parse_bitor(self):
        v = self.parse_eq()
        while self.peek() in (("op", "|"), ("op", "&"), ("op", "^")):
            op = self.take()[1]
            r = self.parse_eq()
            a, b = int(v), int(r)
            v = a | b if op == "|" else (a & b if op == "&" else a ^ b)
        return v

    def parse_eq(self):
        v = self.parse_rel()
        while self.peek() in (("op", "="), ("op", "!=")):
            op = self.take()[1]
            # intervalo: = [a, b) / (a, b]
            if self.peek() in (("op", "["), ("op", "(")) and self._is_interval():
                lo_inc = self.take()[1] == "["
                a = self.parse_add()
                self.accept(",")
                b = self.parse_add()
                hi_inc = self.take()[1] == "]"
                inside = (v >= a if lo_inc else v > a) and (v <= b if hi_inc else v < b)
                v = int(inside if op == "=" else not inside)
                continue
            r = self.parse_rel()
            v = int((v == r) if op == "=" else (v != r))
        return v

    def _is_interval(self):
        depth, j = 0, self.i
        while j < len(self.toks):
            t = self.toks[j]
            if t[0] == "op" and t[1] in "([":
                depth += 1
            elif t[0] == "op" and t[1] in ")]":
                depth -= 1
                if depth == 0:
                    return False
            elif t == ("op", ",") and depth == 1:
                return True
            j += 1
        return False

    def parse_rel(self):
        v = self.parse_add()
        while self.peek() in (("op", "<"), ("op", ">"), ("op", "<="), ("op", ">=")):
            op = self.take()[1]
            r = self.parse_add()
            v = int({"<": v < r, ">": v > r, "<=": v <= r, ">=": v >= r}[op])
        return v

    def parse_add(self):
        v = self.parse_mul()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            r = self.parse_mul()
            v = v + r if op == "+" else v - r
        return v

    def parse_mul(self):
        v = self.parse_pow()
        while self.peek() in (("op", "*"), ("op", "/"), ("op", "%")):
            op = self.take()[1]
            r = self.parse_pow()
            if op == "*":
                v = v * r
            elif op == "/":
                if r == 0:
                    raise Undefined("división entre 0")
                v = v / r if isinstance(v, float) or isinstance(r, float) else int(v / r)
            else:
                v = int(v) % int(r) if r else 0
        return v

    def parse_pow(self):
        v = self.parse_unary()
        if self.accept("**"):
            v = v ** self.parse_pow()
        return v

    def parse_unary(self):
        if self.accept("-"):
            return -self.parse_unary()
        if self.accept("+"):
            return self.parse_unary()
        if self.accept("!"):
            return int(not self.parse_unary())
        if self.accept("~"):
            return ~int(self.parse_unary())
        return self.parse_atom()

    def args(self):
        out = []
        if not self.accept("("):
            return out
        if self.accept(")"):
            return out
        while True:
            out.append(self.parse_or())
            if self.accept(")"):
                return out
            if not self.accept(","):
                raise Undefined("falta «)»")

    def raw_args(self):
        """Argumentos como texto (para const(), command…)."""
        if not self.accept("("):
            return ""
        depth, parts = 1, []
        while self.i < len(self.toks):
            t = self.take()
            if t == ("op", "("):
                depth += 1
            elif t == ("op", ")"):
                depth -= 1
                if depth == 0:
                    break
            parts.append(str(t[1]))
        return "".join(parts)

    def parse_atom(self):
        kind, val = self.take()
        if kind == "num":
            return val
        if kind == "str":
            return val
        if kind == "op" and val == "(":
            v = self.parse_or()
            self.accept(")")
            return v
        if kind == "id":
            return self.sim.trigger(val.lower(), self)
        raise Undefined(f"no entiendo «{val}»")


# ---------------------------------------------------------------- simulador
class Simulator:
    def __init__(self, states, air, constants=None, commands=()):
        self.states = states
        self.air = air
        self.const = constants or {}
        self.commands = {c.strip() for c in commands if c.strip()}
        self.log = []
        self.unsupported = set()
        self.reset(0)

    # ---- estado
    def reset(self, stateno, statetype="S"):
        self.pos = [0.0, 0.0 if statetype != "A" else -40.0]
        self.vel = [0.0, 0.0]
        self.facing = 1
        self.var = {}
        self.fvar = {}
        self.sysvar = {}
        self.power = 0
        self.life = int(self.const.get("data.life", 1000))
        self.gametime = 0
        self.ctrl = 1
        self.statetype, self.movetype, self.physics = statetype, "I", "S"
        self.stateno = self.prevstateno = stateno
        self.anim_no = None
        self.anim_t = 0
        self.anim_loops = 0
        self.hitdef = False
        self.events = []
        self.finished = None
        self.trail = []
        self.persist = {}
        self.enter(stateno, first=True)

    def enter(self, num, ctrl=None, anim=None, first=False):
        if num not in self.states:
            self.finished = num
            self.events.append(("end", num))
            return
        st = self.states[num]
        if not first:
            self.prevstateno = self.stateno
        self.stateno = num
        self.time = 0
        self.persist = {}
        self.hitdef = False
        p = st["params"]
        t = (p.get("type", "") or "").strip().upper()[:1]
        if t in ("S", "C", "A", "L"):
            self.statetype = t
        mt = (p.get("movetype", "") or "").strip().upper()[:1]
        if mt in ("A", "I", "H"):
            self.movetype = mt
        ph = (p.get("physics", "") or "").strip().upper()[:1]
        if ph in ("S", "C", "A", "N"):
            self.physics = ph
        if "anim" in p:
            self.change_anim(self.num(p["anim"], self.anim_no or 0))
        if "velset" in p:
            vx, vy = self.pair(p["velset"])
            if vx is not None:
                self.vel[0] = vx
            if vy is not None:
                self.vel[1] = vy
        if "ctrl" in p:
            self.ctrl = int(self.num(p["ctrl"], self.ctrl))
        if "poweradd" in p:
            self.power += self.num(p["poweradd"], 0)
        if ctrl is not None:
            self.ctrl = int(ctrl)
        if anim is not None:
            self.change_anim(int(anim))
        if self.anim_no is None:
            self.change_anim(num if self.air and self.air.find(num) else 0)
        self.events.append(("state", num))

    def change_anim(self, n, elem=1):
        self.anim_no = int(n)
        self.anim_t = 0
        self.anim_loops = 0
        a = self.action()
        if a and elem > 1:
            self.anim_t = sum(max(0, f.time) for f in a.frames[:elem - 1])

    def action(self):
        return self.air.find(self.anim_no) if self.air and self.anim_no is not None else None

    # ---- animación
    def anim_info(self):
        """(índice del cuadro, tiempo dentro del cuadro, AnimTime)."""
        a = self.action()
        if not a or not a.frames:
            return 0, 0, 0
        frames = a.frames
        infinite = any(f.time < 0 for f in frames)
        total = sum(max(0, f.time) for f in frames)
        t = self.anim_t
        animtime = -1 if infinite and t >= sum(max(0, f.time) for f in frames[:next(
            i for i, f in enumerate(frames) if f.time < 0)]) else t + 1 - total
        if t >= total and not infinite:
            ls = a.loopstart if 0 <= a.loopstart < len(frames) else 0
            lead = sum(max(0, f.time) for f in frames[:ls])
            loop_len = max(1, total - lead)
            t = lead + (t - lead) % loop_len
        acc = 0
        for i, f in enumerate(frames):
            if f.time < 0 or t < acc + max(1, f.time):
                return i, t - acc, animtime
            acc += max(1, f.time)
        return len(frames) - 1, 0, animtime

    def elem_start(self, n):
        a = self.action()
        if not a:
            return None
        return sum(max(0, f.time) for f in a.frames[:max(0, n - 1)])

    # ---- triggers
    def trigger(self, name, e):
        name = name.lower()
        xy = None
        if e.peek()[0] == "id" and e.peek()[1].lower() in ("x", "y"):
            xy = e.peek()[1].lower()
        if name in ("time", "statetime"):
            return self.time
        if name == "gametime":
            return self.gametime
        if name == "animtime":
            return self.anim_info()[2]
        if name == "animelem":
            # AnimElem = n [, op t]
            if not e.accept("="):
                return self.anim_info()[0] + 1
            n = int(e.parse_add())
            start = self.elem_start(n)
            if start is None:
                return 0
            elapsed = self.anim_t - start
            if e.accept(","):
                op = e.take()[1]
                if op in ("<", ">", "<=", ">=", "=", "!="):
                    t = e.parse_add()
                    return int({"<": elapsed < t, ">": elapsed > t, "<=": elapsed <= t, ">=": elapsed >= t,
                                "=": elapsed == t, "!=": elapsed != t}[op])
            return int(elapsed == 0)
        if name == "animelemno":
            a = e.args()
            return self.anim_info()[0] + 1
        if name == "animelemtime":
            a = e.args()
            st = self.elem_start(int(a[0]) if a else 1)
            return self.anim_t - st if st is not None else 0
        if name == "anim":
            return self.anim_no or 0
        if name in ("stateno",):
            return self.stateno
        if name == "prevstateno":
            return self.prevstateno
        if name == "ctrl":
            return self.ctrl
        if name in ("vel", "pos"):
            if xy:
                e.take()
            v = self.vel if name == "vel" else self.pos
            return v[1] if xy == "y" else v[0] * (self.facing if name == "vel" else 1)
        if name == "facing":
            return self.facing
        if name in ("statetype", "movetype", "p2statetype", "p2movetype"):
            if e.accept("="):
                want = str(e.take()[1]).upper()
                cur = {"statetype": self.statetype, "movetype": self.movetype}.get(name, "S")
                return int(cur == want)
            if e.accept("!="):
                want = str(e.take()[1]).upper()
                cur = {"statetype": self.statetype, "movetype": self.movetype}.get(name, "S")
                return int(cur != want)
            return 0
        if name in ("var", "fvar", "sysvar", "sysfvar"):
            a = e.args()
            d = self.var if name in ("var", "sysvar") else self.fvar
            return d.get(int(a[0]) if a else 0, 0)
        if name == "power":
            return self.power
        if name in ("powermax",):
            return int(self.const.get("data.power", 3000))
        if name == "life":
            return self.life
        if name == "lifemax":
            return int(self.const.get("data.life", 1000))
        if name == "command":
            neg = False
            if e.accept("="):
                pass
            elif e.accept("!="):
                neg = True
            v = e.take()[1]
            res = str(v) in self.commands
            return int(res != neg)
        if name == "const":
            k = e.raw_args().lower()
            if k in self.const:
                return self.const[k]
            self.unsupported.add(f"const({k})")
            return 0
        if name == "random":
            return random.randint(0, 999)
        if name in ("abs", "floor", "ceil", "sin", "cos", "tan", "exp", "ln", "log", "min", "max", "ifelse", "cond",
                    "sign", "clamp"):
            a = e.args()
            try:
                return {"abs": lambda: abs(a[0]), "floor": lambda: math.floor(a[0]), "ceil": lambda: math.ceil(a[0]),
                        "sin": lambda: math.sin(a[0]), "cos": lambda: math.cos(a[0]), "tan": lambda: math.tan(a[0]),
                        "exp": lambda: math.exp(a[0]), "ln": lambda: math.log(a[0]),
                        "log": lambda: math.log(a[1], a[0]), "min": lambda: min(a[0], a[1]),
                        "max": lambda: max(a[0], a[1]), "ifelse": lambda: a[1] if a[0] else a[2],
                        "cond": lambda: a[1] if a[0] else a[2],
                        "sign": lambda: (a[0] > 0) - (a[0] < 0),
                        "clamp": lambda: max(a[1], min(a[2], a[0]))}[name]()
            except (IndexError, ValueError, ZeroDivisionError):
                raise Undefined(name)
        if name == "pi":
            return math.pi
        if name == "e":
            return math.e
        if name in ("movecontact", "movehit", "moveguarded", "movereversed", "hitcount", "uniqhitcount", "numhelper",
                    "numexplod", "numproj", "numtarget", "numprojid", "hitshakeover", "hitover", "hitfall",
                    "canrecover", "isHelper", "ishelper", "numenemy", "roundstate", "matchover", "win", "lose",
                    "inguarddist", "p2life", "p2stateno", "alive", "roundno", "teamside", "ailevel", "ishometeam",
                    "projhit", "projcontact", "projguarded", "selfanimexist", "animexist", "hitdefattr",
                    "p2bodydist", "p2dist", "rootdist", "parentdist", "frontedgedist", "backedgedist",
                    "frontedgebodydist", "backedgebodydist", "screenpos", "gethitvar", "palno", "teammode"):
            # sin rival ni pelea: valores neutros
            if name in ("selfanimexist", "animexist"):
                a = e.args()
                return int(bool(self.air and a and self.air.find(int(a[0]))))
            if name in ("p2bodydist", "p2dist", "rootdist", "parentdist", "screenpos"):
                if xy:
                    e.take()
                return 80 if name.startswith("p2") else 0
            if name in ("frontedgedist", "backedgedist", "frontedgebodydist", "backedgebodydist"):
                return 160
            if name == "hitdefattr":
                # «hitdefattr = SC, NA» → falso
                while self.peek_more(e):
                    e.take()
                return 0
            if name == "gethitvar":
                e.raw_args()
                return 0
            if name in ("alive", "roundstate"):
                return 1 if name == "alive" else 2
            if name == "palno":
                return 1
            e.args() if e.peek() == ("op", "(") else None
            return 0
        self.unsupported.add(name)
        if e.peek() == ("op", "("):
            e.raw_args()
        return 0

    @staticmethod
    def peek_more(e):
        t = e.peek()
        return t[0] is not None and not (t[0] == "op" and t[1] in ("&&", "||", ")"))

    def eval(self, text, default=0):
        try:
            e = Expr(text, self)
            v = e.value()
            return v
        except Undefined as ex:
            self.unsupported.add(f"{text} ({ex})")
            return default
        except (TypeError, ValueError, IndexError, KeyError, ZeroDivisionError, OverflowError):
            return default

    def num(self, text, default=0):
        v = self.eval(text, default)
        return v if isinstance(v, (int, float)) else default

    def pair(self, text):
        parts = split_top(text)
        a = self.num(parts[0], None) if parts and parts[0].strip() else None
        b = self.num(parts[1], None) if len(parts) > 1 and parts[1].strip() else None
        return a, b

    # ---- un tick
    def triggered(self, c):
        trig = c["triggers"]
        for t in trig.get(0, []):
            if not self.eval(t):
                return False
        groups = sorted(k for k in trig if k > 0)
        if not groups:
            return False
        for g in groups:
            if all(self.eval(t) for t in trig[g]):
                return True
        return False

    def step(self):
        if self.finished is not None:
            return False
        self.events = []
        st = self.states.get(self.stateno)
        changed = False
        for idx, c in enumerate(st["ctrls"] if st else []):
            if not self.triggered(c):
                continue
            pers = c["params"].get("persistent")
            if pers is not None:
                key = idx
                every = int(self.num(pers, 1))
                if every == 0 and self.persist.get(key):
                    continue
                if every > 1:
                    cnt = self.persist.get(key, 0)
                    self.persist[key] = cnt + 1
                    if cnt % every:
                        continue
                self.persist[key] = self.persist.get(key, 0) + (1 if every == 0 else 0)
            if self.run(c):
                changed = True
                break
            if self.finished is not None:
                return False
        if not changed:
            self.time += 1
        # movimiento y física
        self.pos[0] += self.vel[0] * self.facing
        self.pos[1] += self.vel[1]
        if self.physics == "S" and self.pos[1] >= 0:
            self.vel[0] *= self.const.get("movement.stand.friction", 0.85)
        elif self.physics == "C" and self.pos[1] >= 0:
            self.vel[0] *= self.const.get("movement.crouch.friction", 0.82)
        elif self.physics == "A":
            self.vel[1] += self.const.get("movement.yaccel", 0.44)
            if self.pos[1] >= 0 and self.vel[1] > 0 and self.time > 0:
                self.pos[1] = 0
                self.events.append(("land", 52))
                self.finished = 52
        if not changed:
            self.anim_t += 1
        self.gametime += 1
        self.trail.append(tuple(self.pos))
        self.trail = self.trail[-240:]
        return self.finished is None

    def run(self, c):
        t, p = c["type"], c["params"]
        self.events.append(("ctrl", c["line"], t, c.get("name", "")))
        if t in ("changestate", "selfstate"):
            v = int(self.num(p.get("value", "0")))
            ctrl = self.num(p["ctrl"]) if "ctrl" in p else None
            anim = self.num(p["anim"]) if "anim" in p else None
            self.enter(v, ctrl, anim)
            return True
        if t in ("changeanim", "changeanim2"):
            self.change_anim(int(self.num(p.get("value", "0"))), int(self.num(p.get("elem", "1"), 1)))
        elif t in ("velset", "veladd", "velmul", "posset", "posadd"):
            vx, vy = self.num(p["x"], None) if "x" in p else None, self.num(p["y"], None) if "y" in p else None
            tgt = self.vel if t.startswith("vel") else self.pos
            for i, v in ((0, vx), (1, vy)):
                if v is None:
                    continue
                if t in ("velset", "posset"):
                    tgt[i] = v
                elif t in ("veladd", "posadd"):
                    tgt[i] += v * (self.facing if (i == 0 and t == "posadd") else 1)
                else:
                    tgt[i] *= v
        elif t == "ctrlset":
            self.ctrl = int(self.num(p.get("value", "1")))
        elif t in ("varset", "varadd"):
            for k, v in p.items():
                m = re.match(r"^(f?v|f?var\s*\(\s*(\d+)\s*\))$", k)
                if k in ("v", "fv") and "value" in p:
                    num = int(self.num(p[k]))
                    d = self.fvar if k == "fv" else self.var
                    val = self.num(p["value"])
                elif m and m.group(2) is not None:
                    num = int(m.group(2))
                    d = self.fvar if k.startswith("f") else self.var
                    val = self.num(v)
                else:
                    continue
                d[num] = (d.get(num, 0) + val) if t == "varadd" else val
        elif t == "statetypeset":
            for key, attr in (("statetype", "statetype"), ("movetype", "movetype"), ("physics", "physics")):
                if key in p:
                    setattr(self, attr, p[key].strip().upper()[:1])
        elif t == "turn":
            self.facing = -self.facing
        elif t == "gravity":
            self.vel[1] += self.const.get("movement.yaccel", 0.44)
        elif t == "poweradd":
            self.power += self.num(p.get("value", "0"))
        elif t == "lifeadd":
            self.life += self.num(p.get("value", "0"))
        elif t == "hitdef":
            self.hitdef = True
        elif t == "playsnd":
            self.events.append(("sound", p.get("value", "")))
        elif t in COSMETIC:
            pass
        elif t == "destroyself":
            self.finished = "destroy"
        else:
            self.unsupported.add(t)
        return False


COSMETIC = set("null sprpriority width playerpush screenbound posfreeze afterimage afterimagetime envshake explod "
               "makedust palfx allpalfx bgpalfx superpause pause nothitby hitby hitoverride assertspecial "
               "attackmulset defencemulset angledraw angleset angleadd anglemul trans offset removeexplod "
               "modifyexplod gamemakeanim envcolor fallenvshake forcefeedback displaytoclipboard appendtoclipboard "
               "clearclipboard sndpan stopsnd movehitreset attackdist explodbindtime remappal zoom "
               "printtoconsole".split())


def split_top(text):
    """Separa por comas de primer nivel (sin romper paréntesis)."""
    out, depth, cur = [], 0, []
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out
