"""
Animaciones de MUGEN / IKEMEN GO (.air).

Cada acción guarda su texto original; solo las acciones que se editan se vuelven a escribir,
así los comentarios y el formato del autor se conservan en todo lo demás.
"""
import re

from core.textio import read_text, write_text

BEGIN = re.compile(r"^\s*\[\s*begin\s+action\s+(-?\d+)\s*\]", re.IGNORECASE)
CLSN_HEAD = re.compile(r"^\s*clsn([12])(default)?\s*:\s*(\d+)", re.IGNORECASE)
CLSN_BOX = re.compile(r"^\s*clsn([12])\s*\[\s*\d+\s*\]\s*=\s*(.+)$", re.IGNORECASE)
LOOPSTART = re.compile(r"^\s*loopstart\b", re.IGNORECASE)
FRAME = re.compile(r"^\s*-?\d+\s*,\s*-?\d+\s*,")


def _strip(line):
    return line.split(";", 1)[0].rstrip()


def _num(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _fnum(v, default=1.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


class Frame:
    def __init__(self, group=0, number=0, x=0, y=0, time=1, flip="", trans="", xscale=None, yscale=None, angle=None):
        self.group, self.number = group, number
        self.x, self.y, self.time = x, y, time
        self.flip, self.trans = flip, trans
        self.xscale, self.yscale, self.angle = xscale, yscale, angle
        self.clsn1 = []   # [(x1,y1,x2,y2)] que valen para este cuadro
        self.clsn2 = []
        self.extra = []   # líneas raras (Interpolate…) que iban antes de este cuadro

    def copy(self):
        f = Frame(self.group, self.number, self.x, self.y, self.time, self.flip, self.trans,
                  self.xscale, self.yscale, self.angle)
        f.clsn1 = [tuple(b) for b in self.clsn1]
        f.clsn2 = [tuple(b) for b in self.clsn2]
        f.extra = list(self.extra)
        return f

    def line(self):
        parts = [str(self.group), str(self.number), str(self.x), str(self.y), str(self.time)]
        tail = [self.flip or "", self.trans or ""]
        if self.xscale is not None or self.yscale is not None or self.angle is not None:
            tail += [_fmt(self.xscale if self.xscale is not None else 1),
                     _fmt(self.yscale if self.yscale is not None else 1),
                     _fmt(self.angle if self.angle is not None else 0)]
        while tail and tail[-1] == "":
            tail.pop()
        return ", ".join(parts + tail)


def _fmt(v):
    v = float(v)
    return str(int(v)) if v == int(v) else f"{v:g}"


def parse_frame(body):
    p = [x.strip() for x in body.split(",")]
    while len(p) < 10:
        p.append("")
    f = Frame(_num(p[0]), _num(p[1]), _num(p[2]), _num(p[3]), _num(p[4], 1))
    f.flip = p[5].upper()
    f.trans = p[6]
    if p[7] != "":
        f.xscale = _fnum(p[7])
    if p[8] != "":
        f.yscale = _fnum(p[8])
    if p[9] != "":
        f.angle = _fnum(p[9], 0)
    return f


class Action:
    def __init__(self, number):
        self.number = number
        self.frames = []
        self.loopstart = 0
        self.header = []     # comentarios justo antes de [Begin Action]
        self.title = ""      # 1ª línea de comentario (nombre de la acción)
        self.raw = None      # texto original (None = editada, se regenera)

    def duration(self):
        if any(f.time < 0 for f in self.frames):
            return -1
        return sum(f.time for f in self.frames)

    def text(self):
        if self.raw is not None:
            return self.raw
        out = list(self.header) + [f"[Begin Action {self.number}]"]
        norm = [{k: [tuple(int(v) for v in bx) for bx in (f.clsn1 if k == "1" else f.clsn2)] for k in "12"}
                for f in self.frames]
        defaults = {}
        for k in "12":
            sets = [tuple(n[k]) for n in norm]
            if sets and all(sets):
                defaults[k] = list(max(set(sets), key=sets.count))  # la más usada
            else:
                defaults[k] = []  # algún cuadro no tiene cajas: cada cuadro lleva las suyas
        for k in "21":
            if defaults[k]:
                out.append(f"Clsn{k}Default: {len(defaults[k])}")
                for i, bx in enumerate(defaults[k]):
                    out.append(f" Clsn{k}[{i}] = {', '.join(str(v) for v in bx)}")
        for i, f in enumerate(self.frames):
            if i == self.loopstart and i > 0:
                out.append("Loopstart")
            for k in "21":
                boxes = norm[i][k]
                if not boxes or boxes == defaults[k]:
                    continue
                out.append(f"Clsn{k}: {len(boxes)}")
                for j, bx in enumerate(boxes):
                    out.append(f" Clsn{k}[{j}] = {', '.join(str(v) for v in bx)}")
            out += f.extra
            out.append(f.line())
        return "\n".join(out) + "\n"


class AirFile:
    def __init__(self):
        self.path = None
        self.preamble = ""
        self.actions = []
        self.enc, self.nl = "utf-8", "\r\n"
        self.modified = False

    @classmethod
    def load(cls, path):
        a = cls()
        a.path = path
        text, a.enc, a.nl = read_text(path)
        a.parse(text)
        return a

    @classmethod
    def from_text(cls, text):
        a = cls()
        a.parse(text)
        return a

    def parse(self, text):
        lines = text.split("\n")
        starts = [i for i, ln in enumerate(lines) if BEGIN.match(ln)]
        if not starts:
            self.preamble = text
            return
        # los comentarios justo antes de cada [Begin Action] son de esa acción
        bounds = []
        for k, s in enumerate(starts):
            h = s
            prev_end = starts[k - 1] + 1 if k else 0
            while h - 1 >= prev_end and (lines[h - 1].strip().startswith(";") or not lines[h - 1].strip()):
                h -= 1
            # no quitarle a la acción anterior sus líneas vacías del final: dejar los comentarios pegados
            while h < s and not lines[h].strip():
                h += 1
            bounds.append((h, s))
        self.preamble = "\n".join(lines[:bounds[0][0]])
        if self.preamble:
            self.preamble += "\n"
        for k, (h, s) in enumerate(bounds):
            end = bounds[k + 1][0] if k + 1 < len(bounds) else len(lines)
            block = lines[h:end]
            act = self._parse_action(int(BEGIN.match(lines[s]).group(1)), lines[h:s], lines[s + 1:end])
            act.raw = "\n".join(block) + ("\n" if k + 1 < len(bounds) else "")
            self.actions.append(act)

    def _parse_action(self, number, header, body):
        act = Action(number)
        act.header = header
        for ln in header:
            t = ln.strip().lstrip(";").strip(" -=;")
            if t:
                act.title = t if len(t) <= 40 else t[:38] + "…"
        d = {"1": [], "2": []}
        nxt = {"1": None, "2": None}
        pending_kind, pending_default = None, False
        extra = []
        for ln in body:
            b = _strip(ln)
            if not b.strip():
                continue
            m = CLSN_HEAD.match(b)
            if m:
                pending_kind, pending_default = m.group(1), bool(m.group(2))
                if pending_default:
                    d[pending_kind] = []
                else:
                    nxt[pending_kind] = []
                continue
            m = CLSN_BOX.match(b)
            if m:
                vals = [_num(v) for v in m.group(2).split(",")[:4]]
                while len(vals) < 4:
                    vals.append(0)
                box = tuple(vals)
                kind = m.group(1)
                if pending_default and pending_kind == kind:
                    d[kind].append(box)
                elif nxt[kind] is not None:
                    nxt[kind].append(box)
                else:
                    d[kind].append(box)
                continue
            if LOOPSTART.match(b):
                act.loopstart = len(act.frames)
                continue
            if FRAME.match(b):
                f = parse_frame(b)
                f.clsn1 = list(nxt["1"]) if nxt["1"] is not None else list(d["1"])
                f.clsn2 = list(nxt["2"]) if nxt["2"] is not None else list(d["2"])
                nxt = {"1": None, "2": None}
                f.extra = extra
                extra = []
                act.frames.append(f)
                continue
            extra.append(ln.rstrip())
        return act

    def find(self, number):
        return next((a for a in self.actions if a.number == number), None)

    def text(self):
        parts = [self.preamble]
        for k, a in enumerate(self.actions):
            t = a.text()
            if parts and parts[-1] and not parts[-1].endswith("\n\n") and k:
                if not t.startswith("\n") and a.raw is None:
                    parts.append("\n")
            parts.append(t)
        return "".join(parts)

    def save(self, path=None):
        write_text(path or self.path, self.text(), self.enc, self.nl)
        if path:
            self.path = path
        self.modified = False
