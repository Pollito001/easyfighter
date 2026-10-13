"""
Encuentra los golpes, el agarre, los especiales y los súper que un personaje ya tiene en su código (.cmd y
archivos de estados). Así el modo simple puede mostrarlos aunque no se hayan hecho con él.

Solo lee: mira las entradas de [Statedef -1] del .cmd (qué comando lleva a qué estado), los [Command]
(qué teclas son) y el [Statedef] de destino (animación, daño, proyectil, velocidades).
"""
import re
from dataclasses import dataclass, field

BUTTONS = ["x", "y", "z", "a", "b", "c"]
DIRS = {"D": "↓", "F": "→", "B": "←", "U": "↑", "DF": "↘", "DB": "↙", "UF": "↗", "UB": "↖"}
OFF_MARK = "triggerall = 0 ; SIMPLE-MODE: off"


@dataclass
class Found:
    kind: str                # normal / throw / special / super
    label: str               # nombre de la entrada [State -1, nombre]
    state: int
    key: str = ""            # golpe normal: S_x, C_a…
    command: str = ""        # texto del comando (~D, DF, F, x)
    arrows: str = ""         # ↓↘→ + x
    anim: int = None
    damage: int = None
    typ: str = "hit"         # proj / hit / dash / rise
    proj_anim: int = None
    proj_hit_anim: int = None
    button: str = ""
    disabled: bool = False   # el modo simple apagó esta entrada
    group: str = ""          # especiales con el mismo movimiento (versiones débil / fuerte…)
    states: list = field(default_factory=list)
    cmd_name: str = ""       # nombre del [Command] que lo hace
    file: object = None      # archivo donde está su [Statedef]


def _clean(line):
    return line.split(";", 1)[0].strip()


def _blocks(text):
    """[(cabecera, [líneas])] de un archivo MUGEN."""
    out = []
    cur = None
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("["):
            cur = (s, [])
            out.append(cur)
        elif cur is not None:
            cur[1].append(raw)
    return out


def _kv(lines):
    d = {}
    for ln in lines:
        c = _clean(ln)
        if "=" in c:
            k, v = c.split("=", 1)
            d.setdefault(k.strip().lower(), v.strip())
    return d


def _int(v):
    try:
        return int(str(v).strip().split(",")[0].strip())
    except (ValueError, AttributeError):
        return None


def parse_commands(text):
    """nombre (en minúsculas) → [textos del comando]."""
    cmds = {}
    for head, lines in _blocks(text):
        if head.lower().startswith("[command]"):
            kv = _kv(lines)
            name = kv.get("name", "").strip('"').strip()
            if name and kv.get("command"):
                cmds.setdefault(name.lower(), []).append(kv["command"])
    return cmds


def _tokens(cmd):
    return [t.strip() for t in cmd.split(",") if t.strip()]


def _strip(tok):
    """Una tecla sin modificadores: ~30$B → B."""
    return re.sub(r"^[~/$>\d]+", "", tok.strip()).replace("$", "")


def button_of(cmd):
    """El botón de un comando de una sola tecla (x, y…) o None."""
    toks = _tokens(cmd)
    if len(toks) != 1:
        return None
    t = _strip(toks[0]).lower()
    parts = [p.strip() for p in t.split("+")]
    return parts[0] if parts and all(p in BUTTONS for p in parts) else None


def motion_parts(cmd):
    """(direcciones, botones) de un comando como ~D, DF, F, x."""
    dirs, buttons = [], []
    for tok in _tokens(cmd):
        t = _strip(tok)
        for part in t.split("+"):
            p = part.strip()
            if p in DIRS:
                dirs.append(p)
            elif p in BUTTONS:
                buttons.append(p)
    return dirs, buttons


def arrows(cmd):
    """Texto bonito del comando: ↓↘→ + x."""
    out = []
    for tok in _tokens(cmd):
        charge = re.match(r"^~\d+\$?", tok.strip()) or tok.strip().startswith("/")
        t = _strip(tok)
        parts = []
        for part in t.split("+"):
            p = part.strip()
            parts.append(DIRS.get(p, p))
        s = "+".join(parts)
        out.append(f"[{s}]" if charge else s)
    txt = ""
    for s in out:
        if txt and (s[0] in "xyzabc" or txt[-1] in "xyzabc"):
            txt += " + "
        txt += s
    return txt


def parse_statedefs(texts, files=None):
    """estado → datos útiles del [Statedef]: anim, tipo, daño, proyectil, velocidades."""
    states = {}
    for ti, text in enumerate(texts):
        cur = None
        for head, lines in _blocks(text):
            m = re.match(r"\[\s*statedef\s+(-?\d+)", head, re.I)
            if m:
                n = int(m.group(1))
                kv = _kv(lines)
                cur = states.setdefault(n, dict(anim=_int(kv.get("anim")), type=(kv.get("type") or "S")[:1].upper(),
                                                damage=None, proj=None, proj_hit=None, vel=[], power=None,
                                                velset=kv.get("velset"), throw=False,
                                                file=files[ti] if files and ti < len(files) else None))
                continue
            if cur is None or not re.match(r"\[\s*state\b", head, re.I):
                if not re.match(r"\[\s*state\b", head, re.I):
                    cur = None
                continue
            kv = _kv(lines)
            t = kv.get("type", "").lower()
            if t == "hitdef":
                if cur["damage"] is None:
                    cur["damage"] = _int(kv.get("damage"))
                if "t" in kv.get("attr", "").split(",")[-1].strip().lower()[1:]:
                    cur["throw"] = True
            elif t == "projectile" and cur["proj"] is None:
                cur["proj"] = _int(kv.get("projanim")) if kv.get("projanim") else -1
                cur["proj_hit"] = _int(kv.get("projhitanim"))
                if cur["damage"] is None:
                    cur["damage"] = _int(kv.get("damage"))
            elif t == "helper" and cur["proj"] is None:
                cur["proj"] = -1
            elif t in ("velset", "veladd"):
                try:
                    x = float(kv.get("x", "0") or 0)
                except ValueError:
                    x = 0.0
                try:
                    y = float(kv.get("y", "0") or 0)
                except ValueError:
                    y = 0.0
                cur["vel"].append((x, y))
            elif t == "superpause":
                cur["power"] = cur["power"] or 1000
    return states


def _type_of(st):
    if st is None:
        return "hit"
    if st["proj"] is not None:
        return "proj"
    vels = list(st["vel"])
    if st.get("velset"):
        try:
            vx, vy = [float(v) for v in st["velset"].split(",")[:2]]
            vels.append((vx, vy))
        except ValueError:
            pass
    if any(y < 0 for _x, y in vels):
        return "rise"
    if any(x > 0 for x, _y in vels):
        return "dash"
    return "hit"


VERSION_WORDS = r"light|strong|fast|medium|heavy|weak|hard|far|near|close|ex|es|lp|mp|hp|lk|mk|hk|jab|fierce|" \
                r"d[ée]bil|medi[oa]|fuerte|liger[oa]|r[áa]pid[oa]|lejos|cerca|\(\w\)|\d+"


def nice_name(label):
    """Nombre sin la versión: «Light Kung Fu Palm» → «Kung Fu Palm»."""
    n = re.sub(r"\b(" + VERSION_WORDS + r")\b", " ", label, flags=re.I)
    n = re.sub(r"\s+", " ", n).strip(" -_:")
    return n or label


def find_moves(cmd_text, state_texts, simple_begin=None, simple_end=None, state_files=None, cmd_file=None):
    """Lista de Found con lo que el personaje ya tiene. No incluye lo que escribe el modo simple."""
    if simple_begin and simple_begin in cmd_text and simple_end in cmd_text:
        a = cmd_text.index(simple_begin)
        b = cmd_text.index(simple_end, a)
        cmd_text = cmd_text[:a] + cmd_text[b + len(simple_end):]
    commands = parse_commands(cmd_text)
    states = parse_statedefs(state_texts + [cmd_text], list(state_files or [None] * len(state_texts)) + [cmd_file])
    found = []
    seen_normals = set()
    for head, lines in _blocks(cmd_text):
        m = re.match(r"\[\s*state\s+-1\s*,?\s*(.*?)\]?\s*$", head, re.I)
        if not m:
            continue
        label = m.group(1).strip().rstrip("]").strip() or "?"
        kv = _kv(lines)
        if kv.get("type", "").lower() != "changestate":
            continue
        st = _int(kv.get("value"))
        if st is None or st < 0:
            continue
        disabled = any(ln.strip() == OFF_MARK for ln in lines)
        trig = [_clean(ln).lower() for ln in lines if _clean(ln).lower().startswith("trigger")]
        pos_cmds, neg_cmds = [], []
        for t in trig:
            for mm in re.finditer(r'command\s*(!?=)\s*"([^"]+)"', t):
                (pos_cmds if mm.group(1) == "=" else neg_cmds).append(mm.group(2))
        if not pos_cmds:
            continue
        joined = " ".join(trig)
        sd = states.get(st)
        # el comando principal: el que tiene botón
        main = None
        main_name = ""
        for name in pos_cmds:
            for c in commands.get(name.lower(), []):
                if motion_parts(c)[1] or button_of(c):
                    main = c
                    main_name = name
                    break
            if main:
                break
        if main is None:
            continue
        holds = {n.lower() for n in pos_cmds}
        b = button_of(main)
        dirs, btns = motion_parts(main)
        power = re.search(r"power\s*>=?\s*(\d+)", joined)
        f = Found(kind="special", label=label, state=st, command=main, arrows=arrows(main), disabled=disabled,
                  anim=sd["anim"] if sd else None, damage=sd["damage"] if sd else None, cmd_name=main_name,
                  file=sd["file"] if sd else None)
        if b is not None:
            f.button = b
            # agarre: el estado tiene un HitDef de agarre (o, si no se encontró el estado, adelante/atrás + botón)
            throw = sd.get("throw") if sd else ("holdfwd" in holds or "holdback" in holds)
            if throw:
                f.kind = "throw"
                found.append(f)
                continue
            if "holddown" in holds or re.search(r"statetype\s*=\s*c\b", joined):
                pos = "C"
            elif re.search(r"statetype\s*=\s*a\b", joined) or (sd and sd["type"] == "A"):
                pos = "A"
            else:
                pos = "S"
            key = f"{pos}_{b}"
            f.kind = "normal"
            f.key = key
            if key in seen_normals:
                f.kind = "normal_extra"
            seen_normals.add(key)
            found.append(f)
            continue
        if not dirs or not btns:
            continue
        super_ = (power and int(power.group(1)) >= 1000) or (sd is not None and sd.get("power"))
        f.kind = "super" if super_ else "special"
        f.typ = _type_of(sd)
        if sd and sd["proj"] not in (None, -1):
            f.proj_anim = sd["proj"]
            f.proj_hit_anim = sd["proj_hit"]
        fam = "kick" if btns[-1] in ("a", "b", "c") else "punch"
        f.button = btns[-1]
        f.group = ",".join(dirs) + "|" + fam + "|" + f.kind + "|" + nice_name(label).lower()
        found.append(f)
    # agrupar las versiones (débil / fuerte / ex) de cada especial
    groups = {}
    for f in found:
        if f.kind in ("special", "super"):
            groups.setdefault(f.group, []).append(f)
    for lst in groups.values():
        states_ = [x.state for x in lst]
        for x in lst:
            x.states = states_
    return found


def command_template(cmd):
    """El comando con {b} en lugar del botón (para usarlo como movimiento del modo simple)."""
    toks = _tokens(cmd)
    out = []
    for i, tok in enumerate(toks):
        t = _strip(tok)
        if i == len(toks) - 1 and all(p.strip().lower() in BUTTONS for p in t.split("+")):
            out.append("{b}")
        else:
            out.append(tok.strip())
    if "{b}" not in out:
        out.append("{b}")
    return ", ".join(out)


# ---------------------------------------------------------------- editar en el lugar (sin rehacer el código)
def _statedef_span(text, state):
    """(inicio, fin) del texto de un [Statedef n] (hasta el siguiente [Statedef])."""
    m = re.search(r"^[ \t]*\[\s*statedef\s+%d\s*[\],]" % state, text, re.I | re.M)
    if not m:
        return None
    n = re.search(r"^[ \t]*\[\s*statedef\b", text[m.end():], re.I | re.M)
    return m.start(), (m.end() + n.start()) if n else len(text)


def set_damage(text, state, new_first):
    """Cambia el daño de los HitDef / Projectile de un estado. Si tiene varios, los cambia en la misma
    proporción que el primero (así un golpe de varios impactos sigue igual de repartido)."""
    span = _statedef_span(text, state)
    if span is None:
        return None
    a, b = span
    body = text[a:b]
    blocks = re.split(r"(?m)^(?=[ \t]*\[)", body)
    old_first = None
    out = []
    for blk in blocks:
        if re.search(r"(?im)^\s*type\s*=\s*(hitdef|projectile)\b", blk):
            m = re.search(r"(?im)^(\s*damage\s*=\s*)(-?\d+)", blk)
            if m:
                old = int(m.group(2))
                if old_first is None:
                    old_first = old
                    new = int(new_first)
                else:
                    new = round(old * new_first / old_first) if old_first else old
                blk = blk[:m.start(2)] + str(new) + blk[m.end(2):]
        out.append(blk)
    if old_first is None:
        return None
    return text[:a] + "".join(out) + text[b:]


def set_command(text, name, template):
    """Cambia las teclas de un [Command] (todas sus formas) a `template` (con {b}), dejando su botón."""
    def fix(m):
        line = m.group(0)
        mm = re.match(r"(\s*command\s*=\s*)([^;\n]*)(.*)", line, re.I)
        toks = _tokens(mm.group(2))
        btn = toks[-1].strip() if toks else "x"
        if not all(p.strip() in BUTTONS for p in _strip(btn).split("+")):
            btn = "x"
        return mm.group(1) + template.replace("{b}", btn) + mm.group(3)
    out, changed = [], False
    for blk in re.split(r"(?m)^(?=[ \t]*\[)", text):
        if re.match(r"\s*\[command\]", blk, re.I):
            nm = re.search(r'(?im)^\s*name\s*=\s*"([^"]+)"', blk)
            if nm and nm.group(1).lower() == name.lower():
                blk2 = re.sub(r"(?im)^[ \t]*command\s*=[^\n]*", fix, blk, count=1)
                if re.match(r"\s*/\$?[UDFB]{1,2}\s*,\s*\{b\}\s*$", template):
                    # aguantar y apretar: time = 1 (si no, soltar la flecha antes del botón también cuenta)
                    if re.search(r"(?im)^[ \t]*time\s*=", blk2):
                        blk2 = re.sub(r"(?im)^([ \t]*time\s*=\s*)[^;\n]*", lambda m: m.group(1) + "1", blk2, count=1)
                    else:
                        blk2 = re.sub(r"(?im)^([ \t]*command\s*=[^\n]*\n?)", lambda m: m.group(1).rstrip("\n") + "\ntime = 1\n",
                                      blk2, count=1)
                changed |= blk2 != blk
                blk = blk2
        out.append(blk)
    return "".join(out) if changed else None
