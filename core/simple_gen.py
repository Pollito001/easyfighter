"""
Modo simple: a partir de lo que el usuario llenó (sprites de cada animación, golpes, especiales,
voces…) arma las animaciones (.air) y el código (.cmd y un archivo de estados propio).

La configuración se guarda en «<personaje>.simple.json» junto al .def. El código generado vive
en un archivo aparte (<personaje>_simple.st) y en dos bloques marcados del .cmd, que se rehacen
completos cada vez: así nunca se duplica nada.
"""
import copy
import json
import re
from pathlib import Path

from core.air import Action, Frame
from core import combos
from core import special_events as sev
from core.boxes import auto_boxes, hit_box

CMD_BEGIN = "; >>> SIMPLE-MODE commands >>>"
CMD_END = "; <<< SIMPLE-MODE commands <<<"
ENT_BEGIN = "; >>> SIMPLE-MODE moves >>>"
ENT_END = "; <<< SIMPLE-MODE moves <<<"

# ---------------------------------------------------------------- animaciones simples
# (clave, título, descripción, grupo de sprites sugerido, cómo se arma)
# Formas: ("loop", n) se repite · ("hold", n) se queda en el último cuadro · ("once", n) una vez
#         ("rev", n) al revés una vez · ("last", n) solo el último cuadro, quieto
#         ("most", n) todos menos el último · ("revmost", n) todos menos el último, al revés
#         ("first_half", n) / ("second_half", n) mitades, quietas al final
ANIM_SECTIONS = [
    ("basic", "Moverse", [
        ("idle", "Parado", "Respirando, sin hacer nada. Es la animación más importante.", 0, [("loop", 0)]),
        ("walk_f", "Caminar adelante", "Se repite mientras camina hacia el rival.", 20, [("loop", 20)]),
        ("walk_b", "Caminar atrás", "Si la dejas vacía se usa «Caminar adelante» al revés.", 21, [("loop", 21)]),
        ("run", "Correr", "Al tocar → → rápido.", 100, [("loop", 100)]),
        ("hop", "Salto hacia atrás", "Al tocar ← ← rápido.", 105, [("hold", 105)]),
        ("crouch", "Agacharse", "Del primer cuadro (de pie) al último (agachado). Al pararse se usa al revés.",
         10, [("most", 10), ("last", 11), ("revmost", 12)]),
        ("crouch_idle", "Agachado (respirando)", "Opcional: se repite mientras está agachado. Si la dejas vacía "
         "se queda quieto en el último cuadro de «Agacharse».", 11, [("loop", 11)]),
        ("turn", "Voltearse", "Cuando el rival le pasa por encima.", 5, [("once", 5), ("once", 6)]),
    ]),
    ("jump", "Saltar", [
        ("jump_start", "Preparar salto y aterrizar", "Agacharse un poquito antes de saltar y al caer.",
         40, [("once", 40), ("once", 47), ("once", 106)]),
        ("jump_up", "Salto (subiendo)", "Mientras sube.", 41, [("hold", 41), ("hold", 42), ("hold", 43)]),
        ("jump_down", "Salto (bajando)", "Mientras baja.", 44, [("hold", 44), ("hold", 45), ("hold", 46)]),
        ("jump_fwd", "Salto adelante (voltereta)", "Opcional: si la llenas, el salto hacia adelante usa esta "
         "(primera mitad subiendo, segunda bajando).", 42, [("first_half", 42), ("second_half", 45)]),
        ("air_dash", "Dash en el aire", "Opcional: en el aire, → → (o ← ←) avanza (o retrocede) rápido, una vez "
         "por salto. Si la dejas vacía, no tiene dash en el aire.", 115, [("hold", 115)]),
    ]),
    ("guard", "Cubrirse", [
        ("guard_s", "Cubrirse de pie", "Del primer cuadro (normal) al último (cubierto).",
         120, [("most", 120), ("last", 130), ("revmost", 140), ("last", 150), ("last", 151)]),
        ("guard_c", "Cubrirse agachado", "Del primer cuadro (normal) al último (cubierto).",
         121, [("most", 121), ("last", 131), ("revmost", 141), ("last", 152), ("last", 153)]),
        ("guard_a", "Cubrirse en el aire", "Del primer cuadro (normal) al último (cubierto).",
         122, [("most", 122), ("last", 132), ("revmost", 142), ("last", 154), ("last", 155)]),
    ]),
    ("hurt", "Recibir golpes", [
        ("hit_high", "Golpe en la cara", "Echa la cabeza para atrás. Al recuperarse se usa al revés.", 5000,
         [("hold", 5000), ("hold", 5001), ("hold", 5002), ("rev", 5005), ("rev", 5006), ("rev", 5007)]),
        ("hit_low", "Golpe en la panza", "Se dobla. Al recuperarse se usa al revés.", 5010,
         [("hold", 5010), ("hold", 5011), ("hold", 5012), ("rev", 5015), ("rev", 5016), ("rev", 5017)]),
        ("hit_crouch", "Golpe agachado", "Recibe un golpe estando agachado.", 5020,
         [("hold", 5020), ("hold", 5021), ("hold", 5022), ("rev", 5025), ("rev", 5026), ("rev", 5027)]),
        ("fly", "Sale volando", "Lo lanzan por el aire (subiendo).", 5030,
         [("once", 5030), ("once", 5035), ("hold", 5050)]),
        ("fall", "Cayendo", "Bajando de cabeza o de espalda hacia el suelo.", 5060, [("hold", 5060)]),
        ("ground_hit", "Choca con el suelo", "Al caer de golpe (rebota).", 5100,
         [("once", 5100), ("hold", 5101), ("hold", 5160), ("hold", 5170)]),
        ("lie", "Tirado en el suelo", "Acostado, quieto.", 5110, [("last", 5110), ("last", 5080)]),
        ("getup", "Levantarse", "Del suelo hasta quedar de pie.", 5120, [("once", 5120)]),
        ("trip", "Tropezar", "Cuando le hacen una barrida.", 5070, [("hold", 5070)]),
        ("air_recover", "Recuperarse en el aire", "Da una vuelta en el aire y cae de pie.", 5040,
         [("hold", 5040), ("hold", 5200), ("once", 5210)]),
        ("dizzy", "Mareado", "Se repite mientras está mareado.", 5300, [("loop", 5300)]),
    ]),
    ("show", "Intro y final", [
        ("intro", "Intro", "Al empezar la pelea.", 190, [("once", 190), ("once", 191)]),
        ("win", "Ganar", "Pose de victoria.", 180, [("hold", 180)]),
        ("select_pose", "Pose al elegirlo", "La de la pantalla de selección al elegirlo. Si la dejas vacía se usa "
         "la de «Ganar».", 181, [("hold", 181)]),
        ("lose", "Perder por tiempo", "Si se acaba el tiempo y va perdiendo.", 170, [("hold", 170)]),
        ("draw", "Empate", "Si empatan.", 175, [("hold", 175)]),
        ("taunt", "Burla", "Opcional: provoca al rival con el botón Start (s). Si la dejas vacía, no tiene burla.",
         195, [("once", 195)]),
        ("win2", "Ganar (otra pose 2)", "Opcional: otra pose de victoria. Al ganar sale una al azar.", 182,
         [("hold", 182)]),
        ("win3", "Ganar (otra pose 3)", "Opcional: otra pose de victoria. Al ganar sale una al azar.", 183,
         [("hold", 183)]),
        ("win4", "Ganar (otra pose 4)", "Opcional: otra pose de victoria. Al ganar sale una al azar.", 184,
         [("hold", 184)]),
        ("lose2", "Perder (otra pose 2)", "Opcional: otra pose de derrota por tiempo. Sale una al azar.", 176,
         [("hold", 176)]),
        ("lose3", "Perder (otra pose 3)", "Opcional: otra pose de derrota por tiempo. Sale una al azar.", 177,
         [("hold", 177)]),
    ]),
]
ANIM_SLOTS = {s[0]: s for _sec, _t, lst in ANIM_SECTIONS for s in lst}
# poses de más (opcionales): casilla → la casilla principal con la que se sortean
EXTRA_POSES = {"win2": "win", "win3": "win", "win4": "win", "lose2": "lose", "lose3": "lose"}
# casillas opcionales que no avisan si están vacías (algo más llena su animación)
OPTIONAL_EMPTY = set(EXTRA_POSES) | {"crouch_idle", "air_dash", "taunt"}

# ---------------------------------------------------------------- golpes normales
BUTTONS = ["x", "y", "z", "a", "b", "c"]
STRENGTH = ["Débil", "Medio", "Fuerte"]
POSITIONS = [("S", "De pie", 200), ("C", "Agachado", 400), ("A", "En el aire", 600)]
NORMAL_NAMES = {"x": "Puño débil", "y": "Puño medio", "z": "Puño fuerte",
                "a": "Patada débil", "b": "Patada media", "c": "Patada fuerte"}
# daño base por botón (puños x y z, patadas a b c)
BASE_DAMAGE = {"x": 25, "y": 40, "z": 60, "a": 28, "b": 45, "c": 65}
PAUSE = [8, 11, 14]
PUSH = [3.0, 4.5, 6.0]
ANIMTYPE = ["Light", "Medium", "Heavy"]


def normal_key(pos, button):
    return f"{pos}_{button}"


def normal_info(key):
    """(posición, botón, fuerza 0..2, ¿patada?, estado base)."""
    pos, b = key.split("_")
    i = BUTTONS.index(b)
    base = dict((p, n) for p, _t, n in POSITIONS)[pos] + i * 10
    return pos, b, i % 3, i >= 3, base


NORMAL_KEYS = [normal_key(p, b) for p, _t, _n in POSITIONS for b in BUTTONS]

# ---------------------------------------------------------------- especiales
MOTIONS = [
    ("QCF", "↓↘→ + botón", "~D, DF, F, {b}"),
    ("QCB", "↓↙← + botón", "~D, DB, B, {b}"),
    ("DP", "→↓↘ + botón", "~F, D, DF, {b}"),
    ("HCF", "←↙↓↘→ + botón", "~B, DB, D, DF, F, {b}"),
    ("HCB", "→↘↓↙← + botón", "~F, DF, D, DB, B, {b}"),
    ("DD", "↓↓ + botón", "~D, D, {b}"),
    ("CHG", "Cargar ← y luego → + botón", "~30$B, F, {b}"),
    ("CHGU", "Cargar ↓ y luego ↑ + botón", "~30$D, U, {b}"),
    ("QCF2", "↓↘→↓↘→ + botón", "~D, DF, F, D, DF, F, {b}"),
    ("QCB2", "↓↙←↓↙← + botón", "~D, DB, B, D, DB, B, {b}"),
]
MOTION_CMD = {k: c for k, _t, c in MOTIONS}
SPECIAL_TYPES = [
    ("proj", "Lanza un proyectil"),
    ("hit", "Golpe en el lugar"),
    ("dash", "Golpe avanzando (embestida)"),
    ("rise", "Golpe que sube (gancho)"),
    ("grab", "Agarre especial (de cerca, no se puede cubrir)"),
    ("helper", "Llama a un ayudante (entra y pega)"),
    ("counter", "Contraataque (atrapa el golpe del rival)"),
    ("none", "Sin golpe (solo movimiento o efectos)"),
    ("converted", "Del personaje (convertido)"),
]
LAUNCH_MODES = [("no", "No"), ("last", "Sí, con el último golpe"), ("all", "Sí, con cada golpe")]
USE_WHERE = [("ground", "En el suelo"), ("air", "En el aire"), ("both", "En el suelo y en el aire")]
FAMILIES = [("punch", "Puños (x, y, z)", ["x", "y", "z"]), ("kick", "Patadas (a, b, c)", ["a", "b", "c"])]
FAMILY_BUTTONS = {k: b for k, _t, b in FAMILIES}

SPECIAL_PRESETS = [
    dict(name="Bola de fuego", kind="special", motion="QCF", family="punch", type="proj", damage=60),
    dict(name="Gancho volador", kind="special", motion="DP", family="punch", type="rise", damage=80),
    dict(name="Patada embestida", kind="special", motion="QCB", family="kick", type="dash", damage=70),
    dict(name="Golpe especial", kind="special", motion="HCF", family="kick", type="hit", damage=75),
]
SUPER_PRESET = dict(name="Súper", kind="super", motion="QCF2", family="punch", type="proj", damage=220)
# remate (Ender): sale después de un autodoble, tumba al rival y cierra el combo
ENDER_PRESET = dict(name="Remate", kind="ender", motion="HCF", family="punch", type="hit", damage=90)

# voces: clave → (título, grupo, número donde se guarda si se importa)
VOICES = [
    ("atk_light", "Al pegar (débil)", 900, 0),
    ("atk_medium", "Al pegar (medio)", 900, 1),
    ("atk_strong", "Al pegar (fuerte)", 900, 2),
    ("throw", "Al agarrar", 900, 3),
    ("special", "Al hacer un especial", 900, 4),
    ("super", "Al hacer el súper", 900, 5),
    ("ender", "Al hacer un remate", 900, 6),
    ("hurt", "Al recibir un golpe", 901, 0),
    ("ko", "Al perder (KO)", 901, 1),
    ("win", "Al ganar", 902, 0),
    ("intro", "En la intro", 902, 1),
]


VOICE_FREE_FROM = 10      # voces propias de cada especial: grupo 900, desde el 10


def voice_category(sp):
    """Qué voz general usa un especial si no tiene la suya: special / super / ender."""
    return {"super": "super", "ender": "ender"}.get(sp.get("kind"), "special")


# ---------------------------------------------------------------- configuración
def config_path(def_path):
    p = Path(def_path)
    return p.with_name(p.stem + ".simple.json")


def load_config(def_path):
    try:
        data = json.loads(config_path(def_path).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return _fill(data)
    except (OSError, ValueError):
        pass
    return _fill({})


def _fill(d):
    d.setdefault("version", 1)
    d.setdefault("anims", {})
    d.setdefault("normals", {})
    d.setdefault("throw", {})
    d.setdefault("specials", [])
    d.setdefault("voices", {})
    d.setdefault("owned", [])
    d.setdefault("import_mode", "rgba")
    return d


def save_config(def_path, cfg):
    config_path(def_path).write_text(json.dumps(cfg, indent=1, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- armar acciones
def _frames(entry):
    return [(int(g), int(n)) for g, n in entry.get("frames", [])]


def _shape(form, keys):
    if not keys:
        return [], "once"
    if form == "loop":
        return keys, "loop"
    if form == "hold":
        return keys, "hold"
    if form == "once":
        return keys, "once"
    if form == "rev":
        return keys[::-1], "once"
    if form == "last":
        return keys[-1:], "hold"
    if form == "most":
        return (keys[:-1] or keys), "once"
    if form == "revmost":
        return (keys[:-1] or keys)[::-1], "once"
    half = max(1, (len(keys) + 1) // 2)
    if form == "first_half":
        return keys[:half], "hold"
    if form == "second_half":
        return (keys[half:] or keys[-1:]), "hold"
    return keys, "once"


def step_range(entry, nframes, hit_frame):
    """(desde, hasta) cuadros (desde 0, los dos incluidos) en que el golpe avanza, o None si no avanza."""
    step = int((entry or {}).get("step") or 0)
    if not step or nframes <= 0:
        return None
    sf = int(entry.get("step_frame") or 0)
    a = sf - 1 if 1 <= sf <= nframes else max(0, hit_frame - 1)
    b = max(a, min(nframes - 1, hit_frame if hit_frame >= a else a))
    return a, b


def step_offsets(entry, nframes, hit_frame):
    """Cuánto se ha movido el personaje (en píxeles) al terminar cada cuadro: para la vista del editor."""
    rng = step_range(entry, nframes, hit_frame)
    if rng is None:
        return [0] * nframes
    a, b = rng
    step = int(entry.get("step") or 0)
    n = b - a + 1
    return [0 if i < a else (step if i > b else round(step * (i - a + 1) / n)) for i in range(nframes)]


def step_lines(sd, st, entry, nframes, hit_frame, time):
    """Código para que el golpe avance «step» píxeles, repartidos tick a tick entre esos cuadros (PosAdd: no lo
    frena el roce del suelo)."""
    rng = step_range(entry, nframes, hit_frame)
    if rng is None:
        return sd
    a, b = rng
    step = int(entry.get("step") or 0)
    ticks = max(1, int(time) * (b - a + 1))
    cond = [f"trigger1 = AnimElemTime({a + 1}) >= 0"]
    if b + 2 <= nframes:
        cond.append(f"trigger1 = AnimElemTime({b + 2}) < 0")
    return sd + [f"[State {st}, Avanzar]", "type = PosAdd"] + cond + [f"x = {_fmt(round(step / ticks, 3))}", ""]


class ManualBoxes(dict):
    """{cuadro: cajas}. strict = modo «a mano»: los cuadros que no están no pegan (no se pone la automática)."""
    strict = False


def box_mode(entry):
    """«auto» (el editor pone la caja de daño) o «manual» (solo las dibujadas). Los personajes de antes, con
    cajas dibujadas pero sin modo, mezclan: las dibujadas mandan y en los demás cuadros va la automática."""
    m = (entry or {}).get("box_mode")
    return m if m in ("auto", "manual") else ("mixed" if (entry or {}).get("boxes") else "auto")


def manual_boxes(entry):
    """Cajas de golpe puestas a mano en una casilla: {cuadro (desde 0): [(x1, y1, x2, y2)…]} (relativo al eje).
    Un cuadro con la lista vacía no pega aunque sea el cuadro del golpe. En modo automático, ninguna."""
    out = ManualBoxes()
    mode = box_mode(entry)
    if mode == "auto":
        return out
    out.strict = mode == "manual"
    for k, v in ((entry or {}).get("boxes") or {}).items():
        try:
            out[int(k)] = [tuple(int(round(float(c))) for c in b[:4]) for b in v if len(b) >= 4]
        except (TypeError, ValueError):
            pass
    return out


# cajas del cuerpo (las azules, donde le pueden pegar): cuántas pone el editor solo y las dibujadas a mano.
# Se arman de la configuración del personaje antes de generar (set_hurt).
HURT = {"two": True, "by_key": {}}


def hurt_count(cfg):
    """Cajas del cuerpo automáticas: 1 (todo el cuerpo) o 2 (cuerpo y cabeza, lo de siempre)."""
    try:
        return 1 if int((cfg or {}).get("hurt_boxes", 2)) == 1 else 2
    except (TypeError, ValueError):
        return 2


def manual_hurt(entry):
    """Cajas del cuerpo puestas a mano en una casilla: {cuadro (desde 0): [(x1, y1, x2, y2)…]}, o None si son
    automáticas. Un cuadro con la lista vacía no tiene cuerpo (no le pueden pegar)."""
    if (entry or {}).get("hurt_mode") != "manual":
        return None
    out = {}
    for k, v in ((entry or {}).get("hurt") or {}).items():
        try:
            out[int(k)] = [tuple(int(round(float(c))) for c in b[:4]) for b in v if len(b) >= 4]
        except (TypeError, ValueError):
            pass
    return out


def set_hurt(cfg):
    """Prepara HURT con lo del personaje: la cantidad automática y las cajas a mano de cada dibujo."""
    by_key = {}

    def walk(o):
        if isinstance(o, dict):
            mh = manual_hurt(o) if o.get("frames") else None
            if mh is not None:
                keys = _frames(o)
                for i, bx in mh.items():
                    if 0 <= i < len(keys):
                        by_key[keys[i]] = list(bx)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(cfg or {})
    HURT["two"] = hurt_count(cfg) == 2
    HURT["by_key"] = by_key


def reference_sprites(cfg, sprites, air=None):
    """Poses normales para encontrar la parte que pega: de pie (parado), agachado y en el aire."""
    out = {}
    for kind, slot, num, which in (("S", "idle", 0, 0), ("C", "crouch", 11, -1), ("A", "jump_up", 41, 0)):
        keys = own_frames(cfg, slot)[0]
        k = keys[which] if keys else None
        if k is None and air is not None:
            a = air.find(num)
            if a is not None and a.frames:
                f = a.frames[which]
                k = (f.group, f.number)
        out[kind] = sprites.get(k) if k is not None else None
    if out.get("C") is None:
        out["C"] = out.get("S")
    if out.get("A") is None:
        out["A"] = out.get("S")
    return out


def make_action(number, title, keys, time, mode, sprites, hit_index=None, kind="body", hit_frames=None, ref=None,
                manual=None):
    """Acción con cajas automáticas. mode: loop / hold (último cuadro quieto) / once.
    hit_index: cuadro (desde 0) con la caja de golpe. kind="proj": la misma caja golpea y recibe.
    ref: pose normal (para poner la caja de golpe solo en el puño o el pie que pega).
    manual: cajas de golpe puestas a mano por cuadro (mandan sobre las automáticas)."""
    a = Action(number)
    a.title = title
    a.header = [f"; {title}"]
    a.raw = None
    for i, (g, n) in enumerate(keys):
        f = Frame(g, n, 0, 0, max(1, int(time)))
        s = sprites.get((g, n))
        if s is not None:
            try:
                if kind == "proj":
                    box = auto_boxes(s, two=False)
                    f.clsn1, f.clsn2 = list(box), list(box)
                else:
                    mh = HURT["by_key"].get((int(g), int(n)))
                    f.clsn2 = list(mh) if mh is not None else auto_boxes(s, two=HURT["two"])
                    if manual is not None and getattr(manual, "strict", False):
                        f.clsn1 = list(manual.get(i, []))
                    elif manual and i in manual:
                        f.clsn1 = list(manual[i])
                    elif (hit_index is not None and i == hit_index) or (hit_frames and i in hit_frames):
                        f.clsn1 = hit_box(s, ref)
            except Exception:
                pass
        a.frames.append(f)
    if a.frames and mode == "hold":
        a.frames[-1].time = -1
    return a


def rise_hitbox(act, manual=None):
    """Gancho que sube: la caja automática de la punta (el puño arriba) baja hasta el hombro y va desde el
    centro del cuerpo, para que le pegue al rival que está enfrente y no solo por encima de su cabeza."""
    manual = manual or {}
    for i, f in enumerate(act.frames):
        if not f.clsn1 or i in manual or getattr(manual, "strict", False):
            continue
        tops = [b[1] for b in f.clsn2] + [b[1] for b in f.clsn1]
        h = -min(tops) if tops and min(tops) < 0 else 0
        if h <= 0:
            continue
        out = []
        for x1, y1, x2, y2 in f.clsn1:
            out.append((min(x1, 0), y1, x2, max(y2, int(round(y1 + 0.45 * h)))))
        f.clsn1 = out


# casillas que, si quedan vacías, se llenan con otra: destino → (origen, al revés)
FALLBACK = {"walk_b": ("walk_f", True), "select_pose": ("win", False)}

# movimientos que no todos los personajes tienen (se les quita el tick). Para que el juego nunca se quede
# sin animación, la casilla apagada usa otra: clave → (casilla que la reemplaza, al revés, qué cuadros)
SUBSTITUTE = {
    "run": ("walk_f", False, "all"),
    "hop": ("jump_up", False, "all"),
    "turn": ("idle", False, "first"),
    "jump_start": ("crouch", False, "last"),
    "guard_a": ("guard_s", False, "all"),
    "trip": ("fly", False, "all"),
    "air_recover": ("jump_down", False, "all"),
    "dizzy": ("hit_high", False, "all"),
    "intro": ("idle", False, "all"),
    "win": ("idle", False, "all"),
    "lose": ("idle", False, "all"),
    "draw": ("idle", False, "all"),
}
# la voltereta apagada no se reemplaza: el salto adelante usa el salto normal
OPTIONAL_ANIMS = set(SUBSTITUTE) | {"jump_fwd"}
# golpes que no todos tienen: agachado, en el aire y el agarre
OPTIONAL_MOVES = {k for k in NORMAL_KEYS if not k.startswith("S_")} | {"throw"}
# entradas del .cmd de la plantilla que se apagan junto con la casilla: casilla → estado
CMD_STATES = {"run": 100, "hop": 105}
OFF_MARK = "triggerall = 0 ; SIMPLE-MODE: off"


def is_off(cfg, key):
    return key in (OPTIONAL_ANIMS | OPTIONAL_MOVES) and key in cfg.get("off", [])


def fallbacks(cfg):
    """Casilla → (de dónde sale, al revés, qué cuadros) para las vacías y las apagadas."""
    out = {k: (src, rev, "all") for k, (src, rev) in FALLBACK.items()}
    for k, v in SUBSTITUTE.items():
        if is_off(cfg, k):
            out[k] = v
    return out


def own_frames(cfg, key):
    """Cuadros que el usuario puso en la casilla (nada si está apagada) y su rapidez."""
    e = cfg["anims"].get(key) or {}
    return ([] if is_off(cfg, key) else _frames(e)), e.get("time", 5)


def _pick(keys, pick):
    if pick == "first":
        return keys[:1]
    if pick == "last":
        return keys[-1:]
    return keys


def _slot_build(key, keys, time, sprites):
    slot = ANIM_SLOTS[key]
    out = []
    for form, num in slot[4]:
        fk, mode = _shape(form, keys)
        out.append(make_action(num, slot[1], fk, time, mode, sprites))
    return out


def anim_slot_actions(key, cfg, sprites, source=None):
    """Acciones (Action) que salen de una casilla de animación (y de las que dependen de ella).
    source(k) → (cuadros, rapidez) de lo que el personaje ya tenía, para casillas no puestas en el modo simple."""
    set_hurt(cfg)
    fb = fallbacks(cfg)

    def src_of(k):
        keys, t = own_frames(cfg, k)
        if not keys and source is not None:
            keys, t = source(k)
        return keys, t

    def build_from(dst):
        src, rev, pick = fb[dst]
        sk, t = src_of(src)
        sk = _pick(sk[::-1] if rev else sk, pick)
        return _slot_build(dst, sk, t, sprites) if sk else []
    keys, t = own_frames(cfg, key)
    out = []
    if key == "crouch_idle" and not keys:
        # sin «agachado respirando»: quieto en el último cuadro de «Agacharse»
        ck, ct = src_of("crouch")
        return [a for a in _slot_build("crouch", ck, ct, sprites) if a.number == 11] if ck else []
    if keys:
        out += _slot_build(key, keys, t, sprites)
    elif key in fb:
        out += build_from(key)
    elif key == "jump_fwd":
        # sin voltereta: el salto hacia adelante usa el salto normal
        fwd = anim_slot_numbers("jump_fwd")
        for k2 in ("jump_up", "jump_down"):
            sk, t2 = src_of(k2)
            if sk:
                out += [a for a in _slot_build(k2, sk, t2, sprites) if a.number in fwd]
    for dst, (src, _rev, _pk) in fb.items():
        if src == key and keys and not own_frames(cfg, dst)[0]:
            out += build_from(dst)
    if key == "crouch" and own_frames(cfg, "crouch_idle")[0]:
        out = [a for a in out if a.number != 11]          # la acción 11 la pone «Agachado (respirando)»
    if key in ("jump_up", "jump_down") and own_frames(cfg, "jump_fwd")[0]:
        # la voltereta manda en las acciones del salto hacia adelante
        fwd = anim_slot_numbers("jump_fwd")
        out = [a for a in out if a.number not in fwd]
    return out


def toggle_cmd_entries(text, cfg, extra_off=()):
    """Apaga (o vuelve a prender) en el .cmd las entradas de la plantilla de correr y salto hacia atrás, y las
    del personaje que el modo simple reemplazó o que se apagaron (extra_off: números de estado)."""
    states = {n: True for k, n in CMD_STATES.items() if is_off(cfg, k)}
    states.update({int(n): True for n in extra_off})
    # lo que escribe el modo simple no se toca (sus entradas pueden ir a los mismos estados)
    if ENT_BEGIN in text and ENT_END in text:
        a = text.index(ENT_BEGIN)
        b = text.index(ENT_END, a) + len(ENT_END)
        return (toggle_cmd_entries(text[:a], cfg, extra_off) + text[a:b] +
                toggle_cmd_entries(text[b:], cfg, extra_off))
    lines = text.split("\n")
    heads = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("[")] + [len(lines)]
    out = lines[:heads[0]]
    for a, b in zip(heads, heads[1:]):
        block = lines[a:b]
        head = block[0].strip().lower()
        if re.match(r"\[state\s+-1\b", head):
            body = [ln for ln in block[1:] if ln.strip() != OFF_MARK]
            vals = [re.match(r"\s*value\s*=\s*(\d+)\s*(;.*)?$", ln, re.I) for ln in body]
            vals = [int(m.group(1)) for m in vals if m]
            ctype = any(re.match(r"\s*type\s*=\s*changestate\b", ln, re.I) for ln in body)
            block = [block[0]] + body
            if ctype and vals and states.get(vals[0]):
                block = [block[0], OFF_MARK] + body
        out += block
    return "\n".join(out)


def anim_slot_numbers(key):
    return [num for _f, num in ANIM_SLOTS[key][4]]


def best_hit_frame(keys, sprites):
    """El cuadro donde el sprite se estira más (de los que no son el primero)."""
    import numpy as np
    best, bi = -1, max(0, len(keys) // 2)
    for i, k in enumerate(keys):
        if i == 0 and len(keys) > 1:
            continue
        s = sprites.get(k)
        if s is None:
            continue
        try:
            pix = s.pixels()
            mask = pix[:, :, 3] > 0 if pix.ndim == 3 else pix != 0
            if not mask.any():
                continue
            xs = np.where(mask.any(axis=0))[0]
            reach = int(xs.max()) + 1 - s.x
            if reach > best:
                best, bi = reach, i
        except Exception:
            pass
    return bi


def hit_frame_of(entry, keys, sprites):
    hf = int(entry.get("hit", 0) or 0)
    if 1 <= hf <= len(keys):
        return hf - 1
    return best_hit_frame(keys, sprites)


# ---------------------------------------------------------------- código
def _fmt(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


_HOLD_RE = re.compile(r"/\$?([UDFB]{1,2})\s*,\s*\{b\}\s*$")


def held_dir(motion):
    """La flecha que hay que estar aguantando al apretar el botón («/F, {b}» → "F"), o None."""
    m = _HOLD_RE.search(motion or "")
    return m.group(1) if m else None


def cmd_time(motion, normal):
    """Ticks del [Command]. «Aguantar y apretar» solo (/F, x) va con time = 1, como en el KFM:
    con más tiempo, soltar la flecha justo antes del botón también contaba."""
    if held_dir(motion) and motion.count(",") == 1:
        return 1
    return normal


def motion_cmd(cfg, key):
    """Texto del comando (con {b} para el botón) de un movimiento de la lista o uno creado por el usuario."""
    if key in MOTION_CMD:
        return MOTION_CMD[key]
    for m in cfg.get("custom_motions", []):
        if m.get("key") == key:
            return m.get("cmd", MOTION_CMD["QCF"])
    return MOTION_CMD["QCF"]


PROJ_SPEEDS = [3.5, 5.0, 6.5]


# ajustes editables de los especiales: (clave, etiqueta, tipo, mínimo, máximo, para qué, ayuda)
# para qué: all / proj / body (no proyectil) / dash / rise / special / super
SPECIAL_FIELDS = [
    ("use_where", 'Se puede hacer', ("choice", USE_WHERE), 0, 0, "all", 'En el suelo, en el aire (saltando) o en los dos.'),
    ("hits", 'Golpes', int, 1, 30, "hitting", 'Cuántas veces pega (el daño total se reparte entre los golpes).'),
    ("hit_gap", 'Ticks entre golpes', int, 1, 60, "hitting", 'Cada cuántos ticks vuelve a pegar (60 ticks = 1 segundo).'),
    ("pause", 'Pausa al pegar (ticks)', int, 0, 60, "hitting", 'Cuánto se congelan los dos al pegar.'),
    ("push", 'Empuje', float, 0, 30, "hitting", 'Cuánto empuja al rival hacia atrás.'),
    ("guard_pct", 'Daño si se cubre (%)', int, 0, 100, "hitting", 'Parte del daño que le quita aunque se cubra.'),
    ("launch", 'Lo tumba / lo lanza', ("choice", LAUNCH_MODES), 0, 0, "hitting",
     'El rival sale volando y cae al suelo. «Con el último golpe»: los golpes de antes lo dejan aturdido de pie '
     'y el último lo manda a volar (lo normal en un súper de varios golpes).'),
    ("height", 'Cómo se cubre', "height", 0, 0, "hitting", 'De pie, agachado, solo de pie (desde arriba) o no se puede cubrir.'),
    ("wall_bounce", 'Rebota en la pared', bool, 0, 1, "hitting",
     'Cuando lo tumba / lo lanza, el rival sale disparado hacia atrás, rebota contra la orilla de la pantalla y '
     'cae. Sirve para seguir el combo. Solo si «Lo tumba / lo lanza» no está en «No».'),
    ("juggle", 'Puntos de combo (juggle)', int, 0, 30, "all", 'Cuánto «gasta» para pegarle a alguien que va por el aire.'),
    ("invuln", 'Invencible al empezar (ticks)', int, 0, 120, "all", 'No le pueden pegar durante esos ticks.'),
    ("proj_hits_life", 'El proyectil desaparece tras (ticks)', int, 0, 999, "proj", '0 = sigue hasta salir de la pantalla.'),
    ("dash_speed", 'Velocidad de avance', float, 0, 50, "dash", 'Qué tan rápido avanza.'),
    ("stop_on_hit", 'Se detiene al pegar', bool, 0, 1, "stop",
     'Al pegarle (o si se cubre) se queda en ese lugar en vez de seguir de largo empujando al rival.'),
    ("rise_x", 'Avance hacia adelante', float, -20, 30, "rise", 'Qué tan lejos va hacia adelante mientras sube.'),
    ("rise_y", 'Fuerza hacia arriba', float, 0, 40, "rise", 'Qué tan alto sube.'),
    ("rise_frame", 'Sube en el cuadro', int, 1, 60, "rise", 'Antes de ese cuadro se queda en el suelo preparando el golpe; en ese cuadro sale disparado hacia arriba.'),
    ("rise_speed", 'Rapidez de la subida (%)', int, 25, 400, "rise", '100 = normal. Más = sube y baja más rápido; menos = más lento, como flotando. La altura y la distancia no cambian.'),
    ("power_gain", 'Poder que gana', int, 0, 3000, "special", 'Cuánta barra de súper llena al hacerlo (1000 = 1 barra).'),
    ("power_cost", 'Barras que gasta', int, 1, 9, "super", 'Cuántas barras de súper hacen falta.'),
    ("superpause", 'Pausa de súper (ticks)', int, 0, 180, "super_old", 'Cuánto se congela todo al empezar.'),
    ("darken", 'Oscurecer la pantalla', bool, 0, 1, "super_old", 'Oscurece el fondo durante la pausa.'),
    ("cancel", 'Se puede hacer cancelando un golpe', bool, 0, 1, "all", 'Se puede hacer justo después de un golpe normal que conectó.'),
    ("cancel_specials", 'Se puede hacer cancelando un especial', bool, 0, 1, "super", 'El súper sale justo después de un especial que conectó.'),
    ("ad_open", 'Abre autodobles', bool, 0, 1, "adopen",
     'Solo con un estilo de combos con autodobles: después de que pega (con el rival cerca) puedes seguir el '
     'combo con un autodoble. En un súper, el rival se queda de pie; si no lo marcas, el súper cierra el combo y '
     'lo tumba.'),
    ("proj_vy", 'Velocidad hacia arriba', float, -40, 40, "proj", 'El proyectil sube (positivo) o baja (negativo).'),
    ("proj_count", 'Cantidad de proyectiles', int, 1, 5, "proj",
     'Cuántos lanza a la vez, en abanico (uno más arriba que otro).'),
    ("proj_spread", 'Separación del abanico', float, 0, 10, "proj",
     'Con varios proyectiles: qué tan separados salen (velocidad hacia arriba / abajo entre uno y otro).'),
    ("proj_beam", 'Rayo (se queda delante)', bool, 0, 1, "proj",
     'El proyectil no avanza: se queda delante del personaje como un rayo largo y pega varias veces '
     '(«Golpes»). El personaje se queda quieto mientras dura. Dibuja el rayo largo en «El proyectil».'),
    ("beam_time", 'Duración del rayo (ticks)', int, 5, 300, "proj", 'Cuánto dura el rayo (60 ticks = 1 segundo).'),
    ("helper_speed", 'Velocidad del ayudante', float, -20, 30, "helper",
     'Qué tan rápido avanza el ayudante (0 = se queda donde aparece).'),
    ("helper_life", 'El ayudante se va tras (ticks)', int, 10, 600, "helper",
     'Se va al terminar su animación o al pasar este tiempo, lo que pase primero.'),
    ("proj_ax", 'Aceleración', float, -5, 5, "proj", 'El proyectil va más rápido (o más lento) con el tiempo.'),
    ("proj_ay", 'Caída', float, -5, 5, "proj", 'Negativo = cae como una granada.'),
    ("ex_cost", 'Poder de la versión EX', int, 0, 3000, "special", 'Cuánta barra gasta la versión EX (dos botones juntos). 1000 = 1 barra.'),
    ("counter_window", 'Ventana del contraataque (ticks)', int, 1, 120, "counter", 'Cuánto tiempo puede atrapar el golpe del rival.'),
    ("grab_range", 'Alcance del agarre', int, 5, 200, "grab", 'Qué tan cerca tiene que estar el rival.'),
]
def opens_autodouble(sp):
    """¿Después de este especial / súper puede salir un autodoble? (los remates nunca; el súper si se escoge)"""
    kind = sp.get("kind") or "special"
    if kind == "ender":
        return False
    return bool(spec(sp, "ad_open"))


def launch_mode(sp, cb=None):
    """Cuándo tumba / lanza el especial: "no", "last" (con el último golpe) o "all" (con cada golpe)."""
    v = sp.get("launch")
    if v is None:
        super_ = sp.get("kind") == "super"
        if super_ and cb is not None and cb.get("autodouble") and opens_autodouble(sp):
            return "no"      # el súper abre autodobles: el rival se queda de pie para seguir
        if sp.get("type") == "rise":
            return "all"     # el gancho se lo lleva para arriba desde el primer golpe
        return "last" if super_ else "no"
    if v is True:
        return "all" if sp.get("type") == "rise" else "last"
    if v in ("no", "last", "all"):
        return v
    return "no"


HEIGHTS = [("high", 'De pie o agachado'), ("low", 'Solo agachado (bajo)'), ("overhead", 'Solo de pie (desde arriba)'),
           ("unblockable", 'No se puede cubrir')]
VERSION_DMG = [0.8, 1.0, 1.2, 1.3]
VERSION_SPEED = [0.75, 1.0, 1.25, 1.15]
VERSION_NAMES = STRENGTH + ["EX"]


def spec(sp, key):
    """Valor de un ajuste del especial (el guardado o el de fábrica según el tipo)."""
    if key in sp and sp[key] is not None:
        return sp[key]
    super_ = sp.get("kind") == "super"
    typ = sp.get("type", "proj")
    if key == "proj_vel" and sp.get("proj_speed") is not None:
        return (7.0 if super_ else 5.0) * float(sp["proj_speed"]) / 100.0
    return {"hits": 1, "hit_gap": 6, "pause": 14 if super_ else 12, "push": 4.5, "guard_pct": 12,
            "launch": typ == "rise" or super_, "height": "high", "juggle": 4, "invuln": 4 if typ == "rise" else 0,
            "proj_hits_life": 0, "dash_speed": 6.5, "rise_x": 1.8, "rise_y": 8.5, "rise_frame": 1, "rise_speed": 100, "power_gain": 40, "power_cost": 1,
            "superpause": 30, "darken": True, "cancel": True, "proj_vel": 7.0 if super_ else 5.0,
            "use_where": "ground", "cancel_specials": True, "proj_vy": 0.0, "proj_ax": 0.0, "proj_ay": 0.0,
            "ex_cost": 500, "counter_window": 14, "grab_range": 25, "stop_on_hit": False, "wall_bounce": False,
            "proj_count": 1, "proj_spread": 2.0, "proj_beam": False, "beam_time": 60, "helper_speed": 4.0,
            "helper_life": 120,
            "ad_open": not super_}.get(key)


def throws_proj(sp):
    """¿El especial lanza su proyectil principal?"""
    if sp.get("type") != "proj" or not _frames(sp.get("proj") or {}):
        return False
    return not sp.get("evmode") or any(isinstance(e, dict) and e.get("main") for e in sp.get("events") or [])


def special_after_hit(sp, sprites):
    """Condición (con «{st}» por el estado) de «ya pegó su último golpe» de un especial hecho en el modo simple,
    o None si no se sabe (proyectiles, golpes puestos como eventos, código propio)."""
    typ = sp.get("type", "proj")
    keys = _frames(sp)
    if typ not in ("hit", "dash", "rise") or not keys:
        return None
    if any(isinstance(e, dict) and e.get("type") in ("hit", "proj", "custom", "followup") and not e.get("tpl")
           for e in sp.get("events") or []):
        return None
    user_hf = sorted({int(f) - 1 for f in sp.get("hit_frames") or [] if 1 <= int(f) <= len(keys)})
    if user_hf:
        last = user_hf[-1]
        while last - 1 in user_hf:
            last -= 1
        return f"(StateNo = {{st}} && AnimElemTime({last + 1}) > 0)"
    hits = max(1, int(spec(sp, "hits")))
    if hits == 1:
        return "StateNo = {st}"
    hf = hit_frame_of(sp, keys, sprites)
    gap = max(1, int(spec(sp, "hit_gap")))
    return f"(StateNo = {{st}} && AnimElemTime({hf + 1}) > {(hits - 1) * gap})"


def field_applies(where, sp):
    super_ = sp.get("kind") == "super"
    typ = sp.get("type", "proj")
    if typ == "converted":
        return False
    if sp.get("evmode") and where in ("dash", "rise", "super_old"):
        return False   # eso ahora son eventos (pestaña «⏱ Eventos»)
    if where == "super_old":
        return super_
    if where == "adopen":
        return sp.get("kind") != "ender"
    return (where == "all" or (where == "hitting" and typ not in ("none", "grab")) or
            (where == "proj" and typ == "proj") or (where == "dash" and typ == "dash") or
            (where == "rise" and typ == "rise") or (where == "special" and not super_) or
            (where == "super" and super_) or (where == "stop" and typ in ("dash", "hit")) or (where == typ))


def type_events(sp, typ=None):
    """Los eventos que hacen el movimiento de cada tipo («Qué hace»), con los valores de fábrica o los que ya
    tenía en «Ajustes». Quedan marcados como «del tipo» y se pueden cambiar como cualquier evento."""
    typ = typ or sp.get("type", "proj")
    super_ = sp.get("kind") == "super"
    out = []
    if super_:
        out.append({"type": "superpause", "frame": 1, "ticks": int(spec(sp, "superpause")),
                    "darken": bool(spec(sp, "darken")), "tpl": True})
    if typ == "proj":
        # el proyectil principal: sus datos son los de la pestaña «🔥 Proyectil» (los dos se editan igual)
        out.append({"type": "proj", "main": True, "tpl": True})
    if typ == "rise":
        out.append({"type": "move", "frame": int(spec(sp, "rise_frame")), "mode": "set",
                    "x": float(spec(sp, "rise_x")), "y": float(spec(sp, "rise_y")), "air": True,
                    "speed": int(spec(sp, "rise_speed")), "by_version": True, "tpl": True})
    elif typ == "dash":
        out.append({"type": "move", "frame": 1, "mode": "set", "x": float(spec(sp, "dash_speed")), "y": 0.0,
                    "by_version": True, "tpl": True})
        out.append({"type": "move", "frame": 99, "mode": "set", "x": 0.0, "y": 0.0, "tpl": True})
    return out


EVMODE = 2


def migrate_special(sp):
    """Especiales de antes (el movimiento salía de «Ajustes»): ahora el tipo se hace con eventos."""
    if sp.get("type") == "converted" or int(sp.get("evmode") or 0) >= EVMODE:
        return
    evs = list(sp.get("events") or [])
    if not sp.get("evmode"):
        evs = type_events(sp) + evs
    elif sp.get("type") == "proj" and not any(e.get("main") for e in evs):
        evs = [{"type": "proj", "main": True, "tpl": True}] + evs
    sp["events"] = evs
    sp["evmode"] = EVMODE


# el evento del proyectil principal ↔ los datos del especial
MAIN_PROJ = {"damage": "damage", "vx": "proj_vel", "vy": "proj_vy", "ax": "proj_ax", "ay": "proj_ay",
             "hits": "hits", "gap": "hit_gap", "life": "proj_hits_life", "height": "height", "launch": "launch"}


def main_proj_view(sp, sprites, k):
    """El proyectil principal visto como un evento (para la lista y su diálogo)."""
    keys = _frames(sp)
    prm = special_params(sp, 1, sprites, k) if keys else {"px": 40, "py": -60, "hf": 0}
    ev = {"type": "proj", "main": True, "tpl": True, "frame": prm["hf"] + 1 if keys else 1,
          "x": int(prm["px"]), "y": int(prm["py"]),
          "anim": sp.setdefault("proj", {}), "anim_hit": sp.setdefault("proj_hit", {})}
    for f, key in MAIN_PROJ.items():
        ev[f] = spec(sp, key) if key != "damage" else int(sp.get("damage", 60))
    ev["launch"] = launch_mode(sp) != "no"
    return ev


def apply_main_proj(sp, before, after):
    """Guarda en el especial lo que se cambió en el diálogo del proyectil principal."""
    for f, key in MAIN_PROJ.items():
        if after.get(f) != before.get(f):
            sp[key] = after[f]
    if after.get("frame") != before.get("frame"):
        sp["hit"] = int(after.get("frame") or 0)
    if (after.get("x"), after.get("y")) != (before.get("x"), before.get("y")):
        sp["proj_x"], sp["proj_y"] = int(after["x"]), int(after["y"])
    for f, key in (("anim", "proj"), ("anim_hit", "proj_hit")):
        if isinstance(after.get(f), dict):
            sp[key] = after[f]


def set_type(sp, typ):
    """Cambia «Qué hace»: quita los eventos del tipo anterior y pone los del nuevo."""
    migrate_special(sp)
    keep = [e for e in sp.get("events") or [] if not e.get("tpl")]
    sp["type"] = typ
    for key in ("rise_x", "rise_y", "rise_frame", "rise_speed", "dash_speed"):
        sp.pop(key, None)
    sp["events"] = type_events(sp, typ) + keep


def special_params(sp, v, sprites, k):
    """Números de un especial para la versión v (0 débil, 1 medio, 2 fuerte): cuadro que pega, de dónde
    sale el proyectil (relativo al eje) y velocidades. Lo usan el código y la prueba."""
    keys = _frames(sp)
    vv = min(3, max(0, int(v)))
    hf = hit_frame_of(sp, keys, sprites) if keys else 0
    spr = sprites.get(keys[hf]) if keys and 0 <= hf < len(keys) else None
    try:
        front = hit_box(spr) if spr is not None else []
    except Exception:
        front = []
    px = round(front[0][2]) if front else round(40 * k)
    py = round((front[0][1] + front[0][3]) / 2) if front else -round(60 * k)
    if sp.get("proj_x") is not None:
        px = int(sp["proj_x"])
    if sp.get("proj_y") is not None:
        py = int(sp["proj_y"])
    m = VERSION_SPEED[vv]
    if sp.get("evmode"):
        # la prueba usa los eventos de moverse
        mv = [e for e in sp.get("events") or [] if e.get("type") == "move"]
        air = next((e for e in mv if e.get("air")), None)
        if air is not None:
            rs = max(0.25, float(air.get("speed", 100)) / 100)
            mul = (m, 0.85 + 0.15 * min(vv, 2)) if air.get("by_version") else (1.0, 1.0)
            return dict(hf=hf, front=front, px=px, py=py, speed=float(spec(sp, "proj_vel")) * k * m,
                        rise_frame=int(air.get("frame") or 1), rise_speed=rs, dash=0.0,
                        rise=(float(air.get("x", 0)) * k * mul[0], -float(air.get("y", 0)) * k * mul[1]))
        dmv = next((e for e in mv if float(e.get("x", 0)) != 0), None)
        dash = float(dmv.get("x", 0)) * k * (m if dmv.get("by_version") else 1.0) if dmv else 0.0
        return dict(hf=hf, front=front, px=px, py=py, speed=float(spec(sp, "proj_vel")) * k * m,
                    rise_frame=1, rise_speed=1.0, dash=dash, rise=(0.0, 0.0))
    return dict(hf=hf, front=front, px=px, py=py, speed=float(spec(sp, "proj_vel")) * k * m,
                rise_frame=max(1, int(spec(sp, "rise_frame"))), rise_speed=max(0.25, float(spec(sp, "rise_speed")) / 100),
                dash=float(spec(sp, "dash_speed")) * k * m,
                rise=(float(spec(sp, "rise_x")) * k * m, -float(spec(sp, "rise_y")) * k * (0.85 + 0.15 * vv)))


class Gen:
    """Resultado: bloques del .cmd, archivo de estados y acciones a poner en el .air."""

    def __init__(self):
        self.commands = []
        self.entries = []
        self.states = []
        self.actions = []
        self.problems = []


class _Alloc:
    def __init__(self, taken_states, taken_actions):
        self.ts, self.ta = set(taken_states), set(taken_actions)

    def get(self, wanted, base, st_offs, an_offs):
        for start in ([wanted] if wanted is not None else []) + [base]:
            n = start
            for _ in range(2000):
                if not any((n + o) in self.ts for o in st_offs) and not any((n + o) in self.ta for o in an_offs):
                    self.ts |= {n + o for o in st_offs}
                    self.ta |= {n + o for o in an_offs}
                    return n
                if start == wanted:
                    break
                n += 1
        return None


def _lbl(s):
    """Texto seguro para la etiqueta de [State n, …] y comentarios."""
    return re.sub(r"[\[\],;\n\r]+", " ", str(s)).strip()


def _play(st, label, snd, trigger="Time = 0"):
    if not snd:
        return []
    return [f"[State {st}, {label}]", "type = PlaySnd", f"trigger1 = {trigger}", f"value = {snd[0]}, {snd[1]}",
            "channel = 0", ""]


def _sparkxy(box, k):
    if box:
        x1, y1, x2, y2 = box[0]
        return f"sparkxy = {-round(5 * k)}, {round((y1 + y2) / 2)}"
    return f"sparkxy = {-round(10 * k)}, {-round(60 * k)}"


AD_CANCEL = "@@AUTODOBLES@@"
KI_GRACE = 20                 # ticks de margen para seguir el combo justo después de un movimiento
AD_CANCEL_JOIN = " || @@AUTODOBLES@@"


def sp_versions(sp):
    """Versiones que tiene un especial, súper o remate: 0 débil, 1 medio, 2 fuerte, 3 EX (solo especiales).
    El remate de un especial («Remate de») sale solo con el botón fuerte."""
    kind = sp.get("kind") or "special"
    if kind == "ender" and sp.get("ender_of"):
        return [2]
    vflags = list(sp.get("versions", [1, 1, 1])) + [0, 0, 0, 0]
    top = 3 if kind in ("super", "ender") else 4
    return [i for i in range(top) if vflags[i]] or [1]


def ender_base(sp, specials):
    """El especial del que es remate (mismo comando) o None."""
    ref = sp.get("ender_of") if sp.get("kind") == "ender" else None
    if not ref:
        return None
    for i, o in enumerate(specials):
        if o is not sp and special_ref(i, o) == ref and o.get("kind") not in ("super", "ender") and \
                o.get("type") != "converted":
            return o
    return None


def special_ref(idx, sp):
    """Referencia estable a un especial / súper: «P:<uid>» (o «P#<posición>» si es viejo)."""
    return f"P:{sp['uid']}" if sp.get("uid") else f"P:#{idx}"


def special_anim(sp):
    """Número de la animación del cuerpo de un especial (o la original si es uno convertido)."""
    if sp.get("type") == "converted":
        if sp.get("anim_changed") and _frames(sp):
            return sp.get("state")
        for h in (sp.get("vhead") or {}).values():
            m = re.search(r"(?im)^\s*anim\s*=\s*(\d+)", h or "")
            if m:
                return int(m.group(1))
        return None
    return sp.get("state") if _frames(sp) else None


def ender_text(text, st, est, extra_pct, k, tr=lambda s: s):
    """El estado de un especial convertido en remate: otro número, más daño y sus golpes tumban al rival
    (sin poder recuperarse en el aire). Así el combo se cierra."""
    out = []
    lines = text.split("\n")
    in_hit = False
    has_fall = False

    def close():
        if in_hit and not has_fall:
            out[-1:-1] = ["fall = 1", "air.fall = 1", "fall.recover = 0"]

    for ln in lines:
        ln = ln.replace(f"[Statedef {st}]", f"[Statedef {est}]").replace(f"[State {st},", f"[State {est},")
        if ln.startswith("; ") and not out:
            ln = ln + f" ({tr('Remate')})"
        if ln.strip() == "" and in_hit:
            out.append(ln)
            close()
            in_hit = False
            continue
        if ln.strip().lower() == "type = hitdef":
            in_hit, has_fall = True, False
        elif ln.startswith("[") and in_hit:
            close()
            in_hit = False
        if in_hit:
            m = re.match(r"(?i)^damage\s*=\s*(\d+)(.*)$", ln)
            if m:
                ln = f"damage = {int(round(int(m.group(1)) * (100 + extra_pct) / 100.0))}{m.group(2)}"
            if re.match(r"(?i)^ground\.velocity\s*=", ln):
                ln = f"ground.velocity = {_fmt(round(-4.5 * k, 2))}, {_fmt(round(-6 * k, 2))}"
            elif re.match(r"(?i)^air\.velocity\s*=", ln):
                ln = f"air.velocity = {_fmt(round(-4.5 * k, 2))}, {_fmt(round(-5 * k, 2))}"
            elif re.match(r"(?i)^fall\.recover\s*=", ln):
                ln = "fall.recover = 0"
            elif re.match(r"(?i)^fall\s*=", ln):
                has_fall = True
                ln = "fall = 1"
        out.append(ln)
    if in_hit:
        out.append("")
        close()
    return "\n".join(out)


def generate(cfg, sprites, k, taken_states, taken_actions, tr=lambda s: s, scale=1.0, air=None):
    """Arma todo. taken_*: números que ya usa el personaje fuera del modo simple.
    Escribe en cfg los números elegidos (para que no cambien la próxima vez)."""
    g = Gen()
    set_hurt(cfg)
    al = _Alloc(taken_states, taken_actions)
    refs = reference_sprites(cfg, sprites, air)     # poses normales: la caja de golpe va en lo que pega
    voices = cfg.get("voices", {})

    def voice(key):
        v = voices.get(key)
        return tuple(v) if v else None

    def move_voice(sp):
        """La voz propia del especial / súper / remate, o la general de su tipo."""
        own = sp.get("voice")
        if own == "none":
            return None
        if isinstance(own, (list, tuple)) and len(own) == 2:
            return tuple(own)
        cat = voice_category(sp)
        return voice(cat) or (voice("special") if cat == "ender" else None)

    commands = [f'[Command]\nname = "sm_{b}"\ncommand = {b}\ntime = 1\n' for b in BUTTONS]
    # los autodobles: el botón se guarda unos ticks (como en Killer Instinct, se aprieta mientras termina el especial)
    commands += [f'[Command]\nname = "sm_{b}_ad"\ncommand = {b}\ntime = 1\nbuffer.time = 12\n' for b in BUTTONS]
    commands += ['[Command]\nname = "sm_hd"\ncommand = /$D\ntime = 1\n',
                 '[Command]\nname = "sm_hf"\ncommand = /$F\ntime = 1\n']
    # «aguantando → / ← justo ahora» (para los comandos «mientras caminas»)
    commands += [f'[Command]\nname = "sm_hold_{d}"\ncommand = /{d}\ntime = 1\n' for d in ("F", "B")]
    commands += ['[Command]\nname = "sm_FF"\ncommand = F, F\ntime = 10\n',
                 '[Command]\nname = "sm_BB"\ncommand = B, B\ntime = 10\n',
                 '[Command]\nname = "sm_s"\ncommand = s\ntime = 1\n']
    ent_special, ent_throw, ent_air, ent_crouch, ent_stand = [], [], [], [], []

    def hitdef(attr, dmg, gdmg, strength, guardflag, gtype, k, box, extra=(), fall=False, air=False, proj=False):
        push = PUSH[strength] * k
        h = [f"attr = {attr}", f"damage = {dmg}, {gdmg}", f"animtype = {ANIMTYPE[strength]}",
             f"guardflag = {guardflag}", "hitflag = MAF",
             f"priority = {4 if proj else 3 + strength}, Hit", f"pausetime = {PAUSE[strength]}, {PAUSE[strength]}",
             f"sparkno = {strength}", "guard.sparkno = 40", f"hitsound = 5, {strength}", "guardsound = 6, 0",
             f"ground.type = {gtype}", f"ground.slidetime = {PAUSE[strength]}", f"ground.hittime = {PAUSE[strength] + 4}"]
        if not proj:
            h.append(_sparkxy(box, k))
        if fall:
            h += [f"ground.velocity = {_fmt(round(-push * 0.8, 2))}, {_fmt(round(-6.5 * k, 2))}",
                  f"air.velocity = {_fmt(round(-push * 0.7, 2))}, {_fmt(round(-6 * k, 2))}", "fall = 1", "air.fall = 1",
                  "fall.recover = 0" if gtype == "Trip" else "fall.recover = 1"]
        else:
            h += [f"ground.velocity = {_fmt(round(-push, 2))}",
                  f"air.velocity = {_fmt(round(-push * 0.6, 2))}, {_fmt(round(-3 * k, 2))}"]
        return h + list(extra)

    # -------- golpes normales
    cb = combos.get(cfg)          # None → como siempre
    chain = {}
    norm = {}                     # key → (estado, posición, botón, fuerza, ¿patada?)
    norm_act = {}                 # key → (acción, caja que pega, daño, título)
    norm_ent = []
    launcher = (cb or {}).get("launcher") or ""
    chain_more = {}               # key → [(estado, entrada, cuadros)] de «al apretar otra vez»
    ent_rep = []                  # entradas del .cmd de «al apretar otra vez» (van antes que las normales)
    extra_states = []
    def attack_state(key, n, title, entry, keys, pos, b, strength):
        """Statedef de un golpe normal (o de su repetición): (líneas, acción, caja que pega, daño, final)."""
        hf = hit_frame_of(entry, keys, sprites)
        act = make_action(n, title, keys, entry.get("time", 3 + strength), "hold" if pos == "A" else "once",
                          sprites, hit_index=hf, ref=refs.get(pos), manual=manual_boxes(entry))
        g.actions.append(act)
        box = act.frames[hf].clsn1 if 0 <= hf < len(act.frames) else []
        dmg = int(entry.get("damage", BASE_DAMAGE[b]))
        sweep = pos == "C" and b == "c"
        if pos == "S":
            head = ["type = S", "movetype = A", "physics = S", "juggle = 1", "velset = 0, 0"]
            guard, gtype, attr = "MA", "High", "S, NA"
            end = [f"[State {n}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0", "value = 0", "ctrl = 1", ""]
        elif pos == "C":
            head = ["type = C", "movetype = A", "physics = C", "juggle = 1", "velset = 0, 0"]
            guard, gtype, attr = "L", ("Trip" if sweep else "Low"), "C, NA"
            end = [f"[State {n}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0", "value = 11", "ctrl = 1", ""]
        else:
            head = ["type = A", "movetype = A", "physics = A", "juggle = 2"]
            guard, gtype, attr = "HA", "High", "A, NA"
            end = []
        sd = [f"; {title}", f"[Statedef {n}]"] + head + ["ctrl = 0", f"anim = {n}",
                                                        f"poweradd = {[10, 18, 25][strength]}", "sprpriority = 2", ""]
        sd += _play(n, tr("Voz"), voice(["atk_light", "atk_medium", "atk_strong"][strength]))
        sd += [f"[State {n}, {tr('Golpe')}]", "type = HitDef", "trigger1 = Time = 0"]
        if key == launcher and pos != "A":
            # lanzador: lo manda bien alto y no se puede recuperar en el aire hasta que caiga
            push = PUSH[strength] * k
            hd_ = [x for x in hitdef(attr, dmg, 0, strength, guard, "High", k, box)
                   if not x.startswith(("ground.velocity", "air.velocity", "animtype"))]
            sd += hd_ + ["animtype = Up", f"ground.velocity = {_fmt(round(-push * 0.25, 2))}, {_fmt(round(-10 * k, 2))}",
                         f"air.velocity = {_fmt(round(-push * 0.25, 2))}, {_fmt(round(-9 * k, 2))}",
                         "fall = 1", "air.fall = 1", "fall.recover = 0", ""]
        else:
            hd_ = hitdef(attr, dmg, 0, strength, guard, gtype, k, box, fall=sweep, air=pos == "A")
            if pos == "A" and cb is not None and cb["autodouble"] and cb.get("ad_air_open"):
                # golpe en el aire que abre un autodoble: el rival sigue aturdido hasta que caes
                hd_ = [f"ground.hittime = {max(PAUSE[strength] + 4, 28)}" if x.startswith("ground.hittime") else x
                       for x in hd_] + ["air.hittime = 28"]
            sd += hd_ + [""]
        # avanzar (o retroceder) mientras golpea: un paso, como muchos puños y patadas fuertes
        sd = step_lines(sd, n, entry, len(keys), hf, entry.get("time", 3 + strength)) if pos != "A" else sd
        return sd, act, box, dmg, end

    for key in NORMAL_KEYS:
        entry = cfg["normals"].get(key) or {}
        keys = _frames(entry)
        if not keys or is_off(cfg, key):
            continue
        pos, b, strength, kick, base = normal_info(key)
        n = al.get(entry.get("state"), base, (0,), (0,))
        if n is None:
            g.problems.append(key)
            continue
        entry["state"] = n
        label = tr(NORMAL_NAMES[b])
        title = _lbl(f"{tr(dict((p, t) for p, t, _n in POSITIONS)[pos])}: {label} ({b})")
        sd, act, box, dmg, end = attack_state(key, n, title, entry, keys, pos, b, strength)
        # al apretar el mismo botón otra vez: otra animación (y otra, y vuelve a la primera)
        more_states = []
        for j, fu in enumerate(entry.get("more") or []):
            fk = _frames(fu)
            if not fk:
                continue
            nj = al.get(fu.get("state"), n + 1 + j, (0,), (0,))
            if nj is None:
                g.problems.append(f"{key} +{j + 1}")
                continue
            fu["state"] = nj
            fu.setdefault("damage", entry.get("damage", BASE_DAMAGE[b]))
            fu.setdefault("time", entry.get("time", 3 + strength))
            sdj, _actj, _boxj, _dj, endj = attack_state(key, nj, f"{title} +{j + 1}", fu, fk, pos, b, strength)
            more_states.append((nj, fu, fk))
            extra_states.append("\n".join(sdj + endj))
        chain_more[key] = more_states
        sd += end
        g.states.append("\n".join(sd))
        if pos == "S":
            chain[b] = n
        norm[key] = (n, pos, b, strength, kick)
        norm_act[key] = (act, box, dmg, title)
        norm_ent.append((key, n, pos, b, strength, kick, title))

    g.states += extra_states
    for key, n, pos, b, strength, kick, title in norm_ent:
        # «al apretar otra vez»: del golpe (ya pasado su cuadro que pega) a la siguiente animación
        more = chain_more.get(key) or []
        if more:
            src_e = cfg["normals"].get(key) or {}
            seq = [(n, src_e, _frames(src_e))] + more
            stops = list(range(len(seq) - 1))
            if src_e.get("more_cycle", True):
                stops.append(len(seq) - 1)
            for i in stops:
                frm, fe, fk = seq[i]
                to = seq[(i + 1) % len(seq)][0]
                if to == frm:
                    continue
                hf_ = hit_frame_of(fe, fk, sprites)
                back = {"S": 0, "C": 11}.get(pos)
                rep = [f"[State -1, SM: {title} ({tr('otra vez')} → {to})]", "type = ChangeState", f"value = {to}",
                       f'triggerall = command = "sm_{b}"',
                       # mientras da el golpe, desde el cuadro que pega…
                       f"trigger1 = StateNo = {frm}", f"trigger1 = AnimElemTime({hf_ + 1}) >= 0"]
                if src_e.get("more_hit"):
                    rep.append("trigger1 = movecontact")
                if back is not None:
                    # … o apenas termina (apretando seguido el botón)
                    rep += [f"trigger2 = StateNo = {back}", f"trigger2 = PrevStateNo = {frm}", "trigger2 = ctrl",
                            "trigger2 = Time <= 10"]
                    if src_e.get("more_hit"):
                        rep.append("trigger2 = NumEnemy")
                        rep.append("trigger2 = EnemyNear, MoveType = H || EnemyNear, StateNo = [150, 155]")
                if pos == "C":
                    rep.insert(4, 'triggerall = command = "sm_hd"')
                ent_rep.append("\n".join(rep) + "\n")
        e = [f"[State -1, SM: {title}]", "type = ChangeState", f"value = {n}", f'triggerall = command = "sm_{b}"']
        if cb is None:
            weaker = ([chain[x] for x in BUTTONS[(3 if kick else 0):(3 if kick else 0) + strength] if x in chain]
                      if pos == "S" else [])
        else:
            weaker = combos.chain_sources(cb, key, norm)
        if pos == "S":
            e += ['triggerall = command != "sm_hd"', "trigger1 = statetype = S", "trigger1 = ctrl"]
            if weaker:
                # se puede encadenar desde un golpe más débil que conectó
                e += ["trigger2 = statetype != A", "trigger2 = movecontact", "trigger2 = " + combos.state_list(weaker)]
            ent_stand.append("\n".join(e) + "\n")
        elif pos == "C":
            e += ['triggerall = command = "sm_hd"', "trigger1 = statetype = C", "trigger1 = ctrl"]
            if weaker:
                e += ["trigger2 = statetype != A", "trigger2 = movecontact", "trigger2 = " + combos.state_list(weaker)]
            ent_crouch.append("\n".join(e) + "\n")
        else:
            e += ["trigger1 = statetype = A", "trigger1 = ctrl"]
            if weaker:
                e += ["trigger2 = statetype = A", "trigger2 = movecontact", "trigger2 = " + combos.state_list(weaker)]
            ent_air.append("\n".join(e) + "\n")

    # -------- agarre
    th = cfg.get("throw") or {}
    keys = [] if is_off(cfg, "throw") else _frames(th)
    if keys:
        n = al.get(th.get("state"), 800, (0, 10, 20, 21), (0, 10))
        if n is None:
            g.problems.append("throw")
        else:
            th["state"] = n
            title = _lbl(tr("Agarre"))
            rel = int(th.get("hit", 0) or 0)
            if not (1 <= rel <= len(keys)):
                rel = max(1, (len(keys) * 2 + 2) // 3)
            reach = make_action(n, title + " (" + tr("intento") + ")", keys[:1], 4, "once", sprites, hit_index=0,
                                ref=refs.get("S"), manual={0: manual_boxes(th)[0]} if 0 in manual_boxes(th) else (
                                    manual_boxes(th) if box_mode(th) == "manual" else None))
            full = make_action(n + 10, title, keys, th.get("time", 5), "once", sprites)
            g.actions += [reach, full]
            dmg = int(th.get("damage", 80))
            b = th.get("button", "y")
            dist = round(30 * k)
            sd = [f"; {title}", f"[Statedef {n}]", "type = S", "movetype = A", "physics = S", "juggle = 0",
                  "velset = 0, 0", "ctrl = 0", f"anim = {n}", "sprpriority = 2", "",
                  f"[State {n}, {tr('Agarrar')}]", "type = HitDef", "trigger1 = Time = 0", "attr = S, NT",
                  "hitflag = M-", "priority = 1, Miss", "sparkno = -1", "p1sprpriority = 1", "p2sprpriority = 0",
                  "p1facing = 1", "p2facing = 1", f"p1stateno = {n + 10}", f"p2stateno = {n + 20}",
                  "guard.dist = 0", "fall = 1", "",
                  f"[State {n}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0", "value = 0",
                  "ctrl = 1", "",
                  f"; {title} ({tr('lo tiene agarrado')})", f"[Statedef {n + 10}]", "type = S", "movetype = A",
                  "physics = N", "velset = 0, 0", "ctrl = 0", f"anim = {n + 10}", "poweradd = 40",
                  "sprpriority = 2", ""]
            sd += _play(n + 10, tr("Voz"), voice("throw"))
            sd += [f"[State {n + 10}, {tr('Sujetar')}]", "type = TargetBind", f"trigger1 = AnimElemTime({rel}) < 0",
                   f"pos = {dist}, 0", "",
                   f"[State {n + 10}, {tr('Daño')}]", "type = TargetLifeAdd", f"trigger1 = AnimElem = {rel}",
                   f"value = {-dmg}", "",
                   f"[State {n + 10}, {tr('Lanzar')}]", "type = TargetState", f"trigger1 = AnimElem = {rel}",
                   f"value = {n + 21}", "",
                   f"[State {n + 10}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0", "value = 0",
                   "ctrl = 1", "",
                   f"; {title} ({tr('el rival, agarrado')})", f"[Statedef {n + 20}]", "type = A", "movetype = H",
                   "physics = N", "velset = 0, 0", "",
                   f"[State {n + 20}, {tr('Animación')}]", "type = ChangeAnim", "trigger1 = Time = 0",
                   "value = 5000", "",
                   f"; {title} ({tr('el rival, lanzado')})", f"[Statedef {n + 21}]", "type = A", "movetype = H",
                   "physics = N", "",
                   f"[State {n + 21}, {tr('Volar')}]", "type = VelSet", "trigger1 = Time = 0",
                   f"x = {_fmt(round(-4 * k, 2))}", f"y = {_fmt(round(-7 * k, 2))}", "",
                   f"[State {n + 21}, {tr('Caer')}]", "type = HitFallSet", "trigger1 = Time = 0", "value = 1", "",
                   f"[State {n + 21}, {tr('Caer')} 2]", "type = SelfState", "trigger1 = Time = 0", "value = 5050", ""]
            g.states.append("\n".join(sd))
            ent_throw.append("\n".join([
                f"[State -1, SM: {title}]", "type = ChangeState", f"value = {n}", f'triggerall = command = "sm_{b}"',
                'triggerall = command = "sm_hf"', "trigger1 = statetype = S", "trigger1 = ctrl",
                f"trigger1 = p2bodydist X < {round(12 * k)}", "trigger1 = p2statetype != A",
                "trigger1 = p2movetype != H"]) + "\n")

    # -------- agarre en el aire: agarra a un rival que va por el aire y lo estrella contra el suelo
    ath = cfg.get("air_throw") or {}
    akeys = _frames(ath)
    if akeys:
        n = al.get(ath.get("state"), 850, (0, 10, 20, 21), (0, 10))
        if n is None:
            g.problems.append("air_throw")
        else:
            ath["state"] = n
            title = _lbl(tr("Agarre en el aire"))
            rel = int(ath.get("hit", 0) or 0)
            if not (1 <= rel <= len(akeys)):
                rel = max(1, (len(akeys) * 2 + 2) // 3)
            mb = manual_boxes(ath)
            reach = make_action(n, title + " (" + tr("intento") + ")", akeys[:1], 4, "hold", sprites, hit_index=0,
                                ref=refs.get("A"), manual={0: mb[0]} if 0 in mb else (mb if box_mode(ath) == "manual"
                                                                                       else None))
            reach.frames[-1].time = 6
            full = make_action(n + 10, title, akeys, ath.get("time", 4), "hold", sprites)
            g.actions += [reach, full]
            dmg = int(ath.get("damage", 70))
            b = ath.get("button", "y")
            dist = round(26 * k)
            g.states.append("\n".join([
                f"; {title}", f"[Statedef {n}]", "type = A", "movetype = A", "physics = A", "juggle = 0", "ctrl = 0",
                f"anim = {n}", "sprpriority = 2", "",
                f"[State {n}, {tr('Agarrar')}]", "type = HitDef", "trigger1 = Time = 0", "attr = A, NT",
                "hitflag = A-", "priority = 1, Miss", "sparkno = -1", "p1sprpriority = 1", "p2sprpriority = 0",
                "p1facing = 1", "p2facing = 1", f"p1stateno = {n + 10}", f"p2stateno = {n + 20}", "guard.dist = 0",
                "fall = 1", "",
                f"[State {n}, {tr('Fin')}]", "type = ChangeState", "trigger1 = Time >= 6", "value = 50", "ctrl = 0",
                "",
                f"; {title} ({tr('lo tiene agarrado')})", f"[Statedef {n + 10}]", "type = A", "movetype = A",
                "physics = N", "velset = 0, 0", "ctrl = 0", f"anim = {n + 10}", "poweradd = 40", "sprpriority = 2",
                ""] + _play(n + 10, tr("Voz"), voice("throw")) + [
                f"[State {n + 10}, {tr('Sujetar')}]", "type = TargetBind", f"trigger1 = AnimElemTime({rel}) < 0",
                f"pos = {dist}, 0", "",
                f"[State {n + 10}, {tr('Daño')}]", "type = TargetLifeAdd", f"trigger1 = AnimElem = {rel}",
                f"value = {-dmg}", "",
                f"[State {n + 10}, {tr('Lanzar')}]", "type = TargetState", f"trigger1 = AnimElem = {rel}",
                f"value = {n + 21}", "",
                f"[State {n + 10}, {tr('Caer')}]", "type = ChangeState", f"trigger1 = AnimElemTime({rel}) >= 6",
                "trigger2 = Time >= 90", "value = 50", "ctrl = 0", "",
                f"; {title} ({tr('el rival, agarrado')})", f"[Statedef {n + 20}]", "type = A", "movetype = H",
                "physics = N", "velset = 0, 0", "",
                f"[State {n + 20}, {tr('Animación')}]", "type = ChangeAnim", "trigger1 = Time = 0",
                "value = ifelse(SelfAnimExist(5030), 5030, 5000)", "",
                f"; {title} ({tr('el rival, contra el suelo')})", f"[Statedef {n + 21}]", "type = A",
                "movetype = H", "physics = N", "",
                f"[State {n + 21}, {tr('Volar')}]", "type = VelSet", "trigger1 = Time = 0",
                f"x = {_fmt(round(-2.5 * k, 2))}", f"y = {_fmt(round(6 * k, 2))}", "",
                f"[State {n + 21}, {tr('Caer')}]", "type = HitFallSet", "trigger1 = Time = 0", "value = 1", "",
                f"[State {n + 21}, {tr('Caer')} 2]", "type = SelfState", "trigger1 = Time = 0", "value = 5050", ""]))
            ent_throw.append("\n".join([
                f"[State -1, SM: {title}]", "type = ChangeState", f"value = {n}", f'triggerall = command = "sm_{b}"',
                'triggerall = command = "sm_hf"', "trigger1 = statetype = A", "trigger1 = ctrl",
                f"trigger1 = p2bodydist X < {round(14 * k)}", f"trigger1 = abs(p2dist Y) < {round(30 * k)}",
                "trigger1 = p2statetype = A", "trigger1 = p2movetype != H"]) + "\n")

    # -------- burla (botón Start)
    if own_frames(cfg, "taunt")[0]:
        n = al.get(cfg.get("taunt_state"), 195, (0,), ())
        if n is not None:
            cfg["taunt_state"] = n
            title = _lbl(tr("Burla"))
            g.states.append("\n".join([
                f"; {title}", f"[Statedef {n}]", "type = S", "movetype = I", "physics = S", "ctrl = 0",
                f"anim = {ANIM_SLOTS['taunt'][3]}", "velset = 0, 0", "sprpriority = 2", "",
                f"[State {n}, {tr('Poder')}]", "type = PowerAdd", "trigger1 = Time = 0", "value = 50", "",
                f"[State {n}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0", "value = 0",
                "ctrl = 1", ""]))
            ent_stand.append("\n".join([
                f"[State -1, SM: {title}]", "type = ChangeState", f"value = {n}", 'trigger1 = command = "sm_s"',
                "trigger1 = statetype = S", "trigger1 = ctrl"]) + "\n")

    # -------- dash en el aire (→ → o ← ←), una vez por salto
    if own_frames(cfg, "air_dash")[0]:
        n = al.get(cfg.get("air_dash_state"), 115, (0, 1), ())
        if n is not None:
            cfg["air_dash_state"] = n
            title = _lbl(tr("Dash en el aire"))
            spd = float(cfg.get("air_dash_speed", 6.0))
            dur = 18
            sd = []
            for j, (sign, cmd) in enumerate(((1, "sm_FF"), (-1, "sm_BB"))):
                st = n + j
                sd += [f"; {title}" + ("" if j == 0 else f" ({tr('atrás')})"), f"[Statedef {st}]", "type = A",
                       "movetype = I", "physics = N", "ctrl = 0", f"anim = {ANIM_SLOTS['air_dash'][3]}",
                       "sprpriority = 2", "",
                       f"[State {st}, {tr('Una vez por salto')}]", "type = MapSet", "trigger1 = Time = 0",
                       'map = "sm_adsh"', "value = 1", "",
                       f"[State {st}, {tr('Impulso')}]", "type = VelSet", "trigger1 = Time = 0",
                       f"x = {_fmt(round(sign * spd * k, 2))}", "y = 0", "",
                       f"[State {st}, {tr('Fin')}]", "type = ChangeState", f"trigger1 = Time >= {dur}", "value = 50",
                       "ctrl = 1", ""]
                ent_air.append("\n".join([
                    f"[State -1, SM: {title}" + ("" if j == 0 else f" ({tr('atrás')})") + "]", "type = ChangeState",
                    f"value = {st}", f'trigger1 = command = "{cmd}"', "trigger1 = statetype = A", "trigger1 = ctrl",
                    "trigger1 = Map(sm_adsh) = 0", f"trigger1 = Pos Y < {round(-12 * k)}"]) + "\n")
            g.states.append("\n".join(sd))
            ent_air.insert(0, "\n".join([
                f"[State -1, SM: {title}: {tr('en el suelo otra vez')}]", "type = MapSet", 'map = "sm_adsh"',
                "value = 0", "trigger1 = statetype != A", "trigger1 = Map(sm_adsh) != 0"]) + "\n")

    # -------- especiales y súper
    specials = cfg.get("specials", [])
    # primero los números de todos (los «seguir con otro especial» necesitan saber a dónde van)
    for sp in specials:
        migrate_special(sp)
        for st_ in (sp.get("vstates") or {}).values():
            al.ts.add(int(st_))
    # rebote en la pared: un estado para el rival (lo usa cualquier especial que lo tenga)
    wb_state = None
    if any(sp.get("type") != "converted" and _frames(sp) and spec(sp, "wall_bounce") for sp in specials):
        wb_state = al.get(cfg.get("wb_state"), 880, (0,), ())
        if wb_state is not None:
            cfg["wb_state"] = wb_state
            w_ = wb_state
            title = _lbl(tr("Rebota en la pared"))
            g.states.append("\n".join([
                f"; {title} ({tr('el rival')})", f"[Statedef {w_}]", "type = A", "movetype = H", "physics = N",
                "ctrl = 0", "",
                f"[State {w_}, {tr('Animación')}]", "type = ChangeAnim", "trigger1 = Time = 0",
                "value = ifelse(SelfAnimExist(5030), 5030, ifelse(SelfAnimExist(5050), 5050, 5000))", "",
                f"[State {w_}, {tr('Sale disparado')}]", "type = VelSet", "trigger1 = Time = 0",
                f"x = {_fmt(round(-11 * k, 2))}", f"y = {_fmt(round(-4 * k, 2))}", "",
                f"[State {w_}, {tr('Cae')}]", "type = VelAdd", "trigger1 = Time > 0", f"y = {_fmt(round(0.4 * k, 3))}",
                "",
                f"[State {w_}, {tr('Choca con la pared')}]", "type = EnvShake", "trigger1 = BackEdgeBodyDist <= 0",
                "trigger1 = Time > 1", "time = 10", "",
                f"[State {w_}, {tr('Choca con la pared')} 2]", "type = PlaySnd", "trigger1 = BackEdgeBodyDist <= 0",
                "trigger1 = Time > 1", "value = F5, 2", "",
                f"[State {w_}, {tr('Rebota')}]", "type = VelSet", "trigger1 = BackEdgeBodyDist <= 0",
                "trigger1 = Time > 1", f"x = {_fmt(round(3 * k, 2))}", f"y = {_fmt(round(-6.5 * k, 2))}", "",
                f"[State {w_}, {tr('Cae')} 2]", "type = HitFallSet", "trigger1 = BackEdgeBodyDist <= 0",
                "trigger1 = Time > 1", "trigger2 = Time >= 45", "trigger3 = Pos Y >= 0", "trigger3 = Vel Y > 0",
                "trigger3 = Time > 2", "value = 1", "",
                f"[State {w_}, {tr('Cae')} 3]", "type = SelfState", "trigger1 = BackEdgeBodyDist <= 0",
                "trigger1 = Time > 1", "trigger2 = Time >= 45", "value = 5050", "",
                f"[State {w_}, {tr('Choca con el suelo')}]", "type = SelfState", "trigger1 = Pos Y >= 0",
                "trigger1 = Vel Y > 0", "trigger1 = Time > 2", "value = 5100", ""]))
    smain = {}
    for idx, sp in enumerate(specials):
        conv = sp.get("type") == "converted"
        if not conv and not _frames(sp):
            continue
        super_ = sp.get("kind") == "super"
        base = (3000 if super_ else (3500 if sp.get("kind") == "ender" else 1000)) + 100 * idx
        n = al.get(sp.get("state"), base, (0, 1, 2, 3, 10, 20, 21), (0, 5, 50, 60) + tuple(range(70, 90)))
        if n is None:
            g.problems.append(sp.get("name", "?"))
            sp["_n"] = None
            continue
        sp["state"] = n
        sp["_n"] = n
        vst = {int(a): int(b) for a, b in (sp.get("vstates") or {}).items()}
        if conv:
            main = vst.get(1, vst.get(2, next(iter(vst.values()), n)))
        else:
            vs_ = sp_versions(sp)
            main = n + (1 if 1 in vs_ else vs_[0])
        if sp.get("uid"):
            smain[sp["uid"]] = main
    special_states = []           # especiales (no súper ni remates): para cancelar y «el súper cancela especiales»
    opener_states = []            # lo que puede abrir un autodoble: especiales y súper
    states_by_v = {}              # fuerza del especial → sus estados (el súper y el EX cuentan como fuerte)
    spec_states = {}              # «P:<especial>» → sus estados (para «el autodoble inicia con…»)
    state_anim = {}               # estado de un especial → su animación (para no cortarle el último golpe)
    state_after = {}              # estado de un especial → condición «ya pegó su último golpe» (si se sabe)
    state_proj = {}               # estado de un especial que lanza proyectil → su projid (MoveContact no lo ve)
    for idx, sp in enumerate(specials):
        if sp.get("_n") is None:
            continue
        kind_ = sp.get("kind") or "special"
        vst = {int(a): int(b) for a, b in (sp.get("vstates") or {}).items()}
        if sp.get("type") == "converted":
            mine = list(vst.values())
            for v_, st_ in vst.items():
                h = (sp.get("vhead") or {}).get(str(v_)) or (sp.get("vhead") or {}).get(v_) or ""
                m = re.search(r"(?im)^\s*anim\s*=\s*(\d+)", h)
                if m:
                    state_anim[st_] = sp["_n"] if (sp.get("anim_changed") and _frames(sp)) else int(m.group(1))
        elif kind_ in ("super", "ender"):
            mine = [sp["_n"] + v for v in sp_versions(sp)]
            for st_ in mine:
                state_anim[st_] = sp["_n"]
                state_after[st_] = special_after_hit(sp, sprites)
                if throws_proj(sp):
                    state_proj[st_] = sp["_n"]
        else:
            mine = [sp["_n"] + v for v in range(4)]
            for st_ in mine:
                state_anim[st_] = sp["_n"]
                state_after[st_] = special_after_hit(sp, sprites)
                if throws_proj(sp):
                    state_proj[st_] = sp["_n"]
        spec_states[special_ref(idx, sp)] = mine
        if kind_ == "ender":
            continue
        if opens_autodouble(sp):
            opener_states += mine
        if kind_ == "super":
            for v_ in sp_versions(sp):
                states_by_v.setdefault(min(2, v_), []).append(sp["_n"] + v_)
            continue
        special_states += mine
        if sp.get("type") == "converted":
            for v_, st_ in vst.items():
                states_by_v.setdefault(min(2, int(v_)), []).append(st_)
        else:
            for v_ in range(4):
                states_by_v.setdefault(min(2, v_), []).append(sp["_n"] + v_)
    if cb is not None and cb["autodouble"] and cb.get("ad_air_open"):
        # caer encima con un golpe en el aire también abre un autodoble (según su fuerza)
        for _k, (n_, pos_, _b, s_, _kick) in norm.items():
            if pos_ == "A":
                opener_states.append(n_)
                states_by_v.setdefault(s_, []).append(n_)

    # -------- sistema de combos (autodobles, saltar para seguir, combo breaker, cancelar con energía…)
    ent_combo = []
    ender_src = []                # versiones fuertes de los especiales: remates (Ender) después de un autodoble
    ender_items = []              # remates hechos como tales (en Especiales y súper, igual que un súper)
    ad_cancel = []                # hay autodobles: la expresión de cancelar lleva un marcador
    conv_idx = set()              # estados copiados del personaje (no se tocan)
    cancel_expr = "stateno = [200, 699]"
    if cb is not None:
        cs = combos.state_list
        # autodobles: se arman después de los especiales (usan sus animaciones); aquí solo se sabe si hay
        if cb["autodouble"] and opener_states and any((ad.get("hits") or []) for ad in cb["ad_list"]):
            ad_cancel.append(AD_CANCEL)
        # qué golpes se pueden cancelar en especiales
        frm = [x for x in cb["cancel_from"] if x in (0, 1, 2)]
        if sorted(frm) == [0, 1, 2]:
            cancel_expr = "(stateno = [200, 699]" + (AD_CANCEL_JOIN if ad_cancel else "") + ")"
        else:
            parts = [cs([v[0] for v in norm.values() if v[3] in frm] +
                        [x[0] for kk, v in norm.items() if v[3] in frm for x in chain_more.get(kk) or []])] \
                if any(v[3] in frm for v in norm.values()) else []
            if ad_cancel:
                cancel_expr = "(" + (" || ".join(parts) + AD_CANCEL_JOIN if parts else AD_CANCEL) + ")"
            else:
                cancel_expr = "(" + (" || ".join(parts) or "0") + ")"
        # saltar para seguir el combo
        jc = cb["jump_cancel"]
        if jc != "none":
            src = ([norm[launcher][0]] if launcher in norm and norm[launcher][1] != "A" else []) if jc == "launcher" \
                else [v[0] for v in norm.values() if v[1] != "A"]
            if src:
                commands.append('[Command]\nname = "sm_hu"\ncommand = /$U\ntime = 1\n')
                ent_combo.append("\n".join([
                    f"[State -1, SM: {tr('Saltar para seguir el combo')}]", "type = ChangeState", "value = 40",
                    'triggerall = command = "sm_hu"', "triggerall = statetype != A",
                    "trigger1 = movehit", "trigger1 = " + cs(src)]) + "\n")
        extra_st = al.get(cb.get("x_state"), 770, (0, 1), ()) if (cb["breaker"] or cb["rc"]) else None
        if extra_st is not None:
            cfg.setdefault("combos", {})["x_state"] = extra_st
        # combo breaker: el que recibe el combo lo rompe
        if cb["breaker"] and extra_st is not None:
            sx = norm_act.get("S_x") or next((v for kk, v in norm_act.items() if kk.startswith("S_")), None)
            if sx is not None:
                st = extra_st
                cost = int(cb["breaker_cost"])
                ki2 = cb.get("breaker_mode") == "ki2"
                by_strength = cb.get("breaker_mode") in ("strength", "ki2")
                if ki2:
                    pass     # Killer Instinct 2: un solo botón (los de siempre: sm_x … sm_c)
                elif by_strength:
                    # Killer Instinct: puño + patada de la MISMA fuerza que el golpe que te están dando
                    for s_, pair in enumerate(("x+a", "y+b", "z+c")):
                        commands.append(f'[Command]\nname = "sm_brk{s_}"\ncommand = {pair}\ntime = 1\n')
                else:
                    commands.append(f'[Command]\nname = "sm_brk"\ncommand = {combos.press_cmd(cb["breaker_btn"])}\n'
                                    'time = 1\n')
                sd = [f"; {tr('Combo breaker')}", f"[Statedef {st}]", "type = U", "movetype = A", "physics = N",
                      "juggle = 0", "velset = 0, 0", "ctrl = 0", f"anim = {sx[0].number}", "sprpriority = 2", "",
                      f"[State {st}, {tr('Invencible')}]", "type = NotHitBy", "trigger1 = Time = 0", "value = SCA",
                      "time = 30", "",
                      f"[State {st}, {tr('Destello')}]", "type = PalFX", "trigger1 = Time = 0", "time = 12",
                      "add = 160, 160, 255", "mul = 256, 256, 256", "",
                      f"[State {st}, {tr('Temblor')}]", "type = EnvShake", "trigger1 = Time = 0", "time = 12",
                      "ampl = 4", ""]
                if cost:
                    sd += [f"[State {st}, {tr('Energía')}]", "type = PowerAdd", "trigger1 = Time = 0",
                           f"value = {-cost}", ""]
                sd += [f"[State {st}, {tr('Empujar')}]", "type = HitDef", "trigger1 = Time = 0", "attr = S, NA",
                       "damage = 0", "animtype = Heavy", "hitflag = MAFD", "priority = 7, Hit", "pausetime = 0, 12",
                       "sparkno = 2", "hitsound = 5, 2", "ground.type = High", "ground.slidetime = 12",
                       "ground.hittime = 16", f"ground.velocity = {_fmt(round(-7 * k, 2))}, {_fmt(round(-4 * k, 2))}",
                       f"air.velocity = {_fmt(round(-7 * k, 2))}, {_fmt(round(-4 * k, 2))}", "fall = 1",
                       "air.fall = 1", "fall.recover = 1", _sparkxy(sx[1], k), "",
                       f"[State {st}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0",
                       "value = ifelse(Pos Y < -1, 50, 0)", "ctrl = 1", ""]
                g.states.append("\n".join(sd))
                base_t = ["triggerall = Alive", "triggerall = movetype = H", "triggerall = stateno = [5000, 5099]",
                          f"triggerall = GetHitVar(hitcount) >= {max(1, int(cb['breaker_hits']))}"]
                if cost:
                    base_t.append(f"triggerall = power >= {cost}")
                lock = int(cb.get("breaker_lockout", 180)) if by_strength else 0
                if lock:
                    base_t.append("triggerall = Map(sm_brklock) <= 0")
                if not by_strength:
                    e = [f"[State -1, SM: {tr('Combo breaker')}]", "type = ChangeState", f"value = {st}",
                         'triggerall = command = "sm_brk"'] + base_t
                    ent_combo.insert(0, "\n".join(e + ["trigger1 = 1"]) + "\n")
                else:
                    # la fuerza del golpe que estás recibiendo: animtype 0 débil, 1 medio, 2+ fuerte (o lanzado)
                    same = ["GetHitVar(animtype) = 0", "GetHitVar(animtype) = 1", "GetHitVar(animtype) >= 2"]
                    blocks = []
                    if ki2:
                        # KI2: puño de esa fuerza si el golpe fue alto o medio, patada si fue bajo (groundtype 2)
                        keys_ = [(b_, s_, b_ in "abc") for s_ in range(3) for b_ in (BUTTONS[s_], BUTTONS[s_ + 3])]
                        conds = {b_: f"{same[s_]} && GetHitVar(groundtype) {'>=' if kick_ else '<'} 2"
                                 for b_, s_, kick_ in keys_}
                        for b_, s_, kick_ in keys_:
                            blocks.append("\n".join([
                                f"[State -1, SM: {tr('Combo breaker')} ({b_})]", "type = ChangeState",
                                f"value = {st}", f'triggerall = command = "sm_{b_}"'] + base_t +
                                [f"trigger1 = {conds[b_]}"]) + "\n")
                        wrong = [f'(command = "sm_{b_}" && !({conds[b_]}))' for b_, _s, _k in keys_]
                    else:
                        for s_ in range(3):
                            blocks.append("\n".join([
                                f"[State -1, SM: {tr('Combo breaker')} ({tr(STRENGTH[s_])})]", "type = ChangeState",
                                f"value = {st}", f'triggerall = command = "sm_brk{s_}"'] + base_t +
                                [f"trigger1 = {same[s_]}"]) + "\n")
                        wrong = [f'(command = "sm_brk{s_}" && !({same[s_]}))' for s_ in range(3)]
                    if lock:
                        # fallar: bloqueado unos segundos (o hasta que se acabe el combo)
                        blocks.append("\n".join([
                            f"[State -1, SM: {tr('Combo breaker')}: {tr('falló')}]", "type = MapSet"] + base_t +
                            ["trigger1 = " + " || ".join(wrong), 'map = "sm_brklock"', f"value = {lock}"]) + "\n")
                        blocks.append("\n".join([
                            f"[State -1, SM: {tr('Combo breaker')}: {tr('bloqueado')}]", "type = MapAdd",
                            "trigger1 = Map(sm_brklock) > 0", 'map = "sm_brklock"', "value = -1"]) + "\n")
                        blocks.append("\n".join([
                            f"[State -1, SM: {tr('Combo breaker')}: {tr('se acabó el combo')}]", "type = MapSet",
                            "trigger1 = Map(sm_brklock) > 0", "trigger1 = movetype != H", 'map = "sm_brklock"',
                            "value = 0"]) + "\n")
                        blocks.append("\n".join([
                            f"[State -1, SM: {tr('Combo breaker')}: {tr('se ve bloqueado')}]", "type = PalFX",
                            "trigger1 = Map(sm_brklock) > 0", "time = 2", "add = 40, 0, 0", "mul = 256, 170, 170"])
                            + "\n")
                    ent_combo[0:0] = blocks
        # cancelar con energía («Roman cancel»): al pegar, corta el golpe y te deja libre
        if cb["rc"] and extra_st is not None:
            st = extra_st + 1
            cost = max(0, int(cb["rc_cost"]))
            commands.append(f'[Command]\nname = "sm_rc"\ncommand = {combos.press_cmd(cb["rc_btn"])}\ntime = 1\n')
            sd = [f"; {tr('Cancelar con energía')}", f"[Statedef {st}]", "type = U", "movetype = I", "physics = N",
                  "ctrl = 0", "sprpriority = 2", "",
                  f"[State {st}, {tr('Energía')}]", "type = PowerAdd", "trigger1 = Time = 0", f"value = {-cost}", "",
                  f"[State {st}, {tr('Quieto')}]", "type = VelSet", "trigger1 = Time = 0", "x = 0", "y = 0", "",
                  f"[State {st}, {tr('Destello')}]", "type = PalFX", "trigger1 = Time = 0", "time = 14",
                  "add = 200, 60, 60", "mul = 256, 256, 256", "",
                  f"[State {st}, {tr('Estela')}]", "type = AfterImage", "trigger1 = Time = 0", "time = 14",
                  "length = 8", "palcolor = 256", "paladd = 60, 0, 0", "palmul = 0.6, 0.4, 0.4", "",
                  f"[State {st}, {tr('Pausa')}]", "type = Pause", "trigger1 = Time = 0", "time = 10",
                  "movetime = 10", "",
                  f"[State {st}, {tr('Fin')}]", "type = ChangeState", "trigger1 = Time >= 2",
                  "value = ifelse(Pos Y < -1, 50, 0)", "ctrl = 1", ""]
            g.states.append("\n".join(sd))
            ent_combo.insert(0, "\n".join([
                f"[State -1, SM: {tr('Cancelar con energía')}]", "type = ChangeState", f"value = {st}",
                'triggerall = command = "sm_rc"', f"triggerall = power >= {cost}", "triggerall = movetype = A",
                f"triggerall = stateno != {st}", "trigger1 = movecontact"]) + "\n")
        # el daño baja poco a poco en combos largos (un AttackMulSet por escalón: el último que cumple manda)
        if cb["scaling"]:
            free = max(0, int(cb["scale_free"]))
            step = max(1, int(cb["scale_step"]))
            low = min(100, max(0, int(cb["scale_min"])))
            lines = [f"[State -1, SM: {tr('Daño en combos largos')}]", "type = AttackMulSet", "trigger1 = 1",
                     "value = 1", ""]
            i = 1
            while i <= 30:
                pct = max(low, 100 - step * i)
                lines += [f"[State -1, SM: {tr('Daño en combos largos')} {pct}%]", "type = AttackMulSet",
                          "trigger1 = NumEnemy", "trigger1 = EnemyNear, MoveType = H",
                          f"trigger1 = EnemyNear, GetHitVar(hitcount) >= {free + i}", f"value = {_fmt(pct / 100)}", ""]
                if pct <= low:
                    break
                i += 1
            ent_combo.insert(0, "\n".join(lines).rstrip() + "\n")

    def button_cmd(b):
        return f"sm_{b}"

    # con un estilo de combos, los especiales «recuerdan» el comando unos ticks (para enlazar en combos)
    buf = "buffer.time = 8\n" if cb is not None else ""

    for idx, sp in enumerate(specials):
        n = sp.pop("_n", None)
        if n is None:
            continue
        super_ = sp.get("kind") == "super"
        typ = sp.get("type", "proj")
        name = _lbl(sp.get("name") or tr("Especial")) or "Special"
        keys = _frames(sp)
        cname = f"sm_sp{idx}"
        # remate de un especial: el mismo comando que ese especial (con el botón fuerte, como en Killer Instinct)
        base_sp = ender_base(sp, specials)
        if base_sp is not None:
            sp["motion"], sp["family"] = base_sp.get("motion", "QCF"), base_sp.get("family", "punch")
        motion = motion_cmd(cfg, sp.get("motion", "QCF"))
        # animaciones de los eventos (efectos, proyectiles extra): acciones n+70…
        ev_anims = {}
        slot = [70]

        def anim_of(ev, field, n=n, name=name, ev_anims=ev_anims, slot=slot):
            ent = ev.get(field) or {}
            fk = _frames(ent) if isinstance(ent, dict) else []
            if not fk:
                return ev.get(field + "_num")
            key = id(ent)
            if key not in ev_anims:
                if slot[0] >= 90:
                    return None
                num = n + slot[0]
                slot[0] += 1
                mode = "loop" if ev.get("type") == "proj" and field == "anim" else "once"
                g.actions.append(make_action(num, f"{name} ({tr('efecto')})", fk, ent.get("time", 4), mode, sprites,
                                             kind="proj" if ev.get("type") == "proj" and field == "anim" else "body"))
                ev_anims[key] = num
            return ev_anims[key]

        def ev_lines(events, st, strength, n=n, anim_of=anim_of, vv=1, nframes=len(keys)):
            out = []
            for j, ev in enumerate(events or []):
                if ev.get("main"):
                    continue   # el proyectil principal lo escribe el especial mismo
                ev = dict(ev, _nframes=nframes)
                ctx = dict(st=st, k=k, scale=scale, tr=tr, anim_of=anim_of, strength=strength, vv=vv,
                           state_of=lambda ref: smain.get(ref), button_cmd=button_cmd, projid=n + 200 + j)
                try:
                    out += sev.event_code(ev, ctx)
                except Exception:
                    g.problems.append(f"{name}: {ev.get('type')}")
            return out

        # ---------- convertido del personaje: su código original, en eventos
        if typ == "converted":
            vst = {int(a): int(b) for a, b in (sp.get("vstates") or {}).items()}
            new_anim = sp.get("anim_changed") and keys
            if new_anim:
                g.actions.append(make_action(n, name, keys, sp.get("time", 4), "once", sprites,
                                             hit_index=hit_frame_of(sp, keys, sprites), ref=refs.get("S"),
                                             manual=manual_boxes(sp)))
            vbut = {int(a): b for a, b in (sp.get("vbutton") or {}).items()}
            ccname = f"sm_cv{sp.get('uid', idx)}"
            ctime = cmd_time(motion, int(sp.get("cmd_time") or (30 if motion.count(",") >= 4 else 20)))
            for v, st in sorted(vst.items()):
                head = (sp.get("vhead") or {}).get(str(v)) or (sp.get("vhead") or {}).get(v) or ""
                hl = head.split("\n")
                hl[0] = f"[Statedef {st}] ; {name}"
                if new_anim:
                    hl = [re.sub(r"(?i)^(\s*anim\s*=\s*)[^;\n]*", lambda m: m.group(1) + str(n), x) for x in hl]
                events = (sp.get("vevents") or {}).get(str(v)) or (sp.get("vevents") or {}).get(v) or []
                conv_idx.add(len(g.states))
                g.states.append("\n".join([f"; {name}"] + hl + [""] + ev_lines(events, st, min(2, v))))
                b = vbut.get(v) or FAMILY_BUTTONS.get(sp.get("family", "punch"), ["x", "y", "z"])[min(2, v)]
                cn = f"{ccname}_{v}"
                bl = FAMILY_BUTTONS.get(sp.get("family", "punch"), ["x", "y", "z"]) if super_ and "+" not in b else [b]
                for b_ in bl:
                    commands.append(f'[Command]\nname = "{cn}"\ncommand = {motion.format(b=b_)}\ntime = {ctime}\n')
            continue

        # ---------- especial del modo simple
        helper = typ == "helper"
        if helper and not _frames(sp.get("proj") or {}):
            continue
        helper_done = False
        proj = typ == "proj"
        if proj and sp.get("evmode") and not any(e.get("main") for e in sp.get("events") or []):
            proj = False   # le quitaron el evento del proyectil: no lanza nada
        pkeys = _frames(sp.get("proj") or {}) if proj else []
        if proj and not pkeys:
            continue
        hf = hit_frame_of(sp, keys, sprites)
        hits = max(1, int(spec(sp, "hits")))
        hit_frames = set()
        # cuadros que pegan elegidos a mano: cada grupo de cuadros seguidos es un golpe
        user_hf = []
        if typ in ("hit", "dash", "rise"):
            user_hf = sorted({int(f) - 1 for f in sp.get("hit_frames") or [] if 1 <= int(f) <= len(keys)})
        runs = []
        for f in user_hf:
            if not runs or f != runs[-1][-1] + 1:
                runs.append([f])
            else:
                runs[-1].append(f)
        if user_hf:
            hits = len(runs)
            hit_frames = set(user_hf)
        elif typ in ("hit", "dash", "rise", "counter"):
            hit_frames = set(range(hf, len(keys))) if hits > 1 else {hf}
        elif typ == "grab":
            hit_frames = {hf}
        for ev in sp.get("events") or []:
            if ev.get("type") == "hit" and ev.get("frame"):
                f0 = int(ev["frame"]) - 1
                hit_frames |= set(range(f0, len(keys))) if int(sev.val(ev, "hits")) > 1 else {f0}
        use = spec(sp, "use_where")
        flies = any(e.get("type") == "move" and e.get("air") for e in sp.get("events") or [])
        hold = (typ == "rise" and not sp.get("evmode")) or use == "air" or (sp.get("evmode") and flies)
        body = make_action(n, name, keys, sp.get("time", 4), "hold" if hold else "once", sprites,
                           hit_frames=hit_frames, ref=refs.get("A" if use == "air" else "S"), manual=manual_boxes(sp))
        if typ == "rise":
            rise_hitbox(body, manual_boxes(sp))
        g.actions.append(body)
        if proj:
            g.actions.append(make_action(n + 50, f"{name} ({tr('proyectil')})", pkeys,
                                         (sp.get("proj") or {}).get("time", 4), "loop", sprites, kind="proj"))
            hkeys = _frames(sp.get("proj_hit") or {})
            if hkeys:
                g.actions.append(make_action(n + 60, f"{name} ({tr('al chocar')})", hkeys,
                                             (sp.get("proj_hit") or {}).get("time", 3), "once", sprites))
        if helper:
            hk = _frames(sp.get("proj") or {})
            hhf = hit_frame_of(sp.get("proj") or {}, hk, sprites)
            g.actions.append(make_action(n + 50, f"{name} ({tr('ayudante')})", hk,
                                         (sp.get("proj") or {}).get("time", 4), "once", sprites, hit_index=hhf,
                                         ref=refs.get("S")))
        if typ == "grab" and hf + 1 < len(keys):
            g.actions.append(make_action(n + 5, f"{name} ({tr('lo tiene agarrado')})", keys[hf:],
                                         sp.get("time", 4), "once", sprites))
        buttons = FAMILY_BUTTONS.get(sp.get("family", "punch"), ["x", "y", "z"])
        if base_sp is not None:
            buttons = buttons[2:3]         # débil y medio siguen siendo el especial (linker)
        ender_ = sp.get("kind") == "ender"
        single = super_ or ender_          # el súper y el remate (no tienen EX ni hacen remates)
        versions = sp_versions(sp)
        # para el autodoble: el rival sigue aturdido hasta que termina el especial (y un poquito más)
        after_hit = 0
        if cb is not None and cb["autodouble"] and opens_autodouble(sp) and not ender_ and body.frames:
            t_, last = 0, None
            for f_ in body.frames:
                if f_.clsn1:
                    last = t_
                t_ += max(1, f_.time) if f_.time > 0 else 10
            if last is not None:
                after_hit = (t_ - last) + KI_GRACE + 6
            if throws_proj(sp):
                # el proyectil: aturdido lo justo para seguir con el autodoble si estás cerca (no para llegar corriendo)
                after_hit = max(after_hit, KI_GRACE + 12)
        if user_hf and len(runs) > 1 and body.frames:
            # cuadros que pegan escogidos a mano: el rival sigue aturdido hasta el próximo golpe (cuenta en el combo)
            starts, t_, prev_red = [], 0, False
            for f_ in body.frames:
                if f_.clsn1 and not prev_red:
                    starts.append(t_)
                prev_red = bool(f_.clsn1)
                t_ += max(1, f_.time) if f_.time > 0 else 10
            gaps = [b_ - a_ for a_, b_ in zip(starts, starts[1:])]
            if gaps:
                after_hit = max(after_hit, max(gaps) + 6)
        for v in versions:
            ctime = cmd_time(motion, 30 if (single or motion.count(",") >= 4) else 20)
            b = f"{buttons[0]}+{buttons[1]}" if v == 3 else (buttons[v] if len(buttons) == 3 else buttons[-1])
            commands.append(f'[Command]\nname = "{cname}_{v}"\ncommand = {motion.format(b=b)}\ntime = {ctime}\n{buf}')
        for v in versions:
            prm = special_params(sp, v, sprites, k)
            front = prm["front"]
            st = n + v
            vv = v
            total = int(round(int(sp.get("damage", 60)) * VERSION_DMG[vv]))
            dmg = max(1, int(round(total / hits)))
            gdmg = int(round(dmg * int(spec(sp, "guard_pct")) / 100.0))
            strength = 2 if v == 3 else v
            lbl = name if len(versions) == 1 else f"{name} ({tr(VERSION_NAMES[v]).lower() if v < 3 else 'EX'})"
            evmode = bool(sp.get("evmode"))
            air_mode = (typ == "rise" and not evmode) or use == "air"
            rise_f = max(1, min(len(keys), int(spec(sp, "rise_frame")))) if typ == "rise" else 1
            rise_s = max(0.25, float(spec(sp, "rise_speed")) / 100.0)
            cost = max(1, int(spec(sp, "power_cost")))
            if evmode and use != "air" and use != "both":
                # empieza en el suelo; los eventos «moverse» lo despegan si hace falta
                head = ["type = S", "movetype = " + ("I" if typ == "counter" else "A"),
                        "physics = " + ("N" if typ in ("dash", "grab") else "S"), "velset = 0, 0"]
            elif typ == "rise" and rise_f > 1 and use != "air":
                # se queda en el suelo hasta el cuadro de la subida
                head = ["type = S", "movetype = A", "physics = S", "velset = 0, 0"]
            elif use == "both":
                head = ["type = U", "movetype = A", "physics = U"]
            else:
                physics = "A" if air_mode else ("N" if typ in ("dash", "grab") else "S")
                head = [f"type = {'A' if air_mode else 'S'}", f"movetype = {'I' if typ == 'counter' else 'A'}",
                        f"physics = {physics}"]
                if not air_mode:
                    head.append("velset = 0, 0")
            head.append(f"juggle = {int(spec(sp, 'juggle'))}")
            if super_:
                gain = -1000 * cost
            elif v == 3:
                gain = -int(spec(sp, "ex_cost"))
            else:
                gain = int(spec(sp, "power_gain"))
            sd = [f"; {lbl}", f"[Statedef {st}]"] + head + [
                "ctrl = 0", f"anim = {n}", f"poweradd = {gain}", "sprpriority = 2", ""]
            if super_ and not evmode:
                sd += [f"[State {st}, {tr('Pausa de súper')}]", "type = SuperPause", "trigger1 = Time = 0",
                       f"time = {int(spec(sp, 'superpause'))}", f"movetime = {int(spec(sp, 'superpause'))}",
                       f"darken = {1 if spec(sp, 'darken') else 0}", ""]
            elif v == 3:
                sd += [f"[State {st}, {tr('Destello EX')}]", "type = SuperPause", "trigger1 = Time = 0",
                       "time = 10", "movetime = 0", "darken = 0", "",
                       f"[State {st}, {tr('Brillo EX')}]", "type = PalFX", "trigger1 = Time = 0", "time = 14",
                       "add = 90, 90, 140", "mul = 256, 256, 256", ""]
            inv = int(spec(sp, "invuln"))
            if inv > 0:
                sd += [f"[State {st}, {tr('Invencible')}]", "type = NotHitBy", "trigger1 = Time = 0", "value = SCA",
                       f"time = {inv}", ""]
            sd += _play(st, tr("Voz"), move_voice(sp))
            if typ == "dash" and not evmode:
                sd += [f"[State {st}, {tr('Avanzar')}]", "type = VelSet", "trigger1 = Time = 0",
                       f"x = {_fmt(round(prm['dash'], 2))}", "",
                       f"[State {st}, {tr('Frenar')}]", "type = VelSet", f"trigger1 = AnimElem = {len(keys)}",
                       "x = 0", ""]
            if typ == "rise" and not evmode:
                rt = "trigger1 = Time = 0" if rise_f == 1 else f"trigger1 = AnimElem = {rise_f}"
                if rise_f > 1 and use != "air":
                    sd += [f"[State {st}, {tr('Despegar')}]", "type = StateTypeSet", rt, "statetype = A",
                           "physics = A", ""]
                sd += [f"[State {st}, {tr('Impulso')}]", "type = VelSet", rt,
                       f"x = {_fmt(round(prm['rise'][0] * rise_s, 2))}",
                       f"y = {_fmt(round(prm['rise'][1] * rise_s, 2))}", ""]
                if abs(rise_s - 1.0) > 0.001:
                    # más (o menos) gravedad en la misma proporción: misma altura y distancia, otra rapidez
                    sd += [f"[State {st}, {tr('Rapidez de la subida')}]", "type = VelAdd",
                           "trigger1 = statetype = A", "trigger1 = Time > 0",
                           f"y = const(movement.yaccel) * {_fmt(round(rise_s * rise_s - 1, 4))}", ""]
            level = ("HP" if super_ else "SP") if proj else ("HA" if super_ else "SA")
            hgt = spec(sp, "height")
            guardflag = {"high": "MA", "low": "L", "overhead": "HA", "unblockable": None}.get(hgt, "MA")
            gtype = "Low" if hgt == "low" else "High"
            pause = int(spec(sp, "pause"))
            push = float(spec(sp, "push")) * k
            hd = [f"attr = S, {level}", f"damage = {dmg}, {gdmg}", f"animtype = {ANIMTYPE[strength]}"]
            if guardflag:
                hd.append(f"guardflag = {guardflag}")
            hd += ["hitflag = MAF", f"priority = {4 if proj else 5}, Hit", f"pausetime = {pause}, {pause}",
                   f"sparkno = {strength}", "guard.sparkno = 40", f"hitsound = 5, {strength}", "guardsound = 6, 0",
                   f"ground.type = {gtype}", f"ground.slidetime = {pause}", f"ground.hittime = {pause + 4}"]
            if not proj:
                hd.append(_sparkxy(front, k))
            mode = launch_mode(sp, cb)
            hd_stun = hd + [f"ground.velocity = {_fmt(round(-push, 2))}",
                            f"air.velocity = {_fmt(round(-push * 0.6, 2))}, {_fmt(round(-3 * k, 2))}"]
            hd_fly = hd + [f"ground.velocity = {_fmt(round(-push * 0.8, 2))}, {_fmt(round(-6.5 * k, 2))}",
                           f"air.velocity = {_fmt(round(-push * 0.7, 2))}, {_fmt(round(-6 * k, 2))}",
                           "fall = 1", "air.fall = 1", "fall.recover = 1"]
            if wb_state is not None and spec(sp, "wall_bounce") and mode != "no":
                hd_fly = hd_fly + [f"p2stateno = {wb_state}", "p2getp1state = 1"]
            hd = hd_fly if mode != "no" else hd_stun
            gap = max(1, int(spec(sp, "hit_gap")))
            if proj:
                px, py, speed = round(prm["px"] * scale), round(prm["py"] * scale), prm["speed"]
                vy = -float(spec(sp, "proj_vy")) * k * VERSION_SPEED[vv]
                ax, ay = float(spec(sp, "proj_ax")) * k, -float(spec(sp, "proj_ay")) * k
                life = int(spec(sp, "proj_hits_life"))
                extra = [f"projid = {n}", f"projanim = {n + 50}", "projremove = 1", f"projhits = {hits}",
                         f"projmisstime = {gap}", f"velocity = {_fmt(round(speed, 2))}, {_fmt(round(vy, 2))}",
                         f"accel = {_fmt(round(ax, 3))}, {_fmt(round(ay, 3))}", f"offset = {px}, {py}",
                         "projpriority = 1", "projsprpriority = 3", f"projremovetime = {life if life > 0 else -1}",
                         # el proyectil crece igual que el personaje (si el .cns no lo hace ya con proj.doscale)
                         "projscale = ifelse(const(size.proj.doscale), 1, const(size.xscale)), "
                         "ifelse(const(size.proj.doscale), 1, const(size.yscale))"]
                if _frames(sp.get("proj_hit") or {}):
                    extra.append(f"projhitanim = {n + 60}")
                    extra.append(f"projremanim = {n + 60}")
                beam = bool(spec(sp, "proj_beam"))
                cnt = 1 if beam else max(1, min(5, int(spec(sp, "proj_count"))))
                spread = float(spec(sp, "proj_spread")) * k
                if beam:
                    btime = max(5, int(spec(sp, "beam_time")))
                    extra = [x for x in extra if not x.startswith(("velocity", "accel", "projremovetime",
                                                                   "projremove ="))]
                    extra += ["velocity = 0, 0", "accel = 0, 0", f"projremovetime = {btime}", "projremove = 0"]
                for j in range(cnt):
                    ex = extra
                    if cnt > 1:
                        vyj = vy + (j - (cnt - 1) / 2.0) * -spread
                        ex = [f"velocity = {_fmt(round(speed, 2))}, {_fmt(round(vyj, 2))}"
                              if x.startswith("velocity") else x for x in extra]
                    sd += [f"[State {st}, {tr('Proyectil')}" + (f" {j + 1}" if cnt > 1 else "") + "]",
                           "type = Projectile", f"trigger1 = AnimElem = {hf + 1}"]
                    sd += ex + hd + [""]
                if beam:
                    # el personaje se queda quieto mientras dura el rayo
                    t_hf = sum(max(1, kf.time) if kf.time > 0 else 10 for kf in body.frames[:hf])
                    sd += [f"[State {st}, {tr('Quieto mientras dura el rayo')}]", "type = ChangeAnim",
                           f"trigger1 = Time < {t_hf + btime}", "trigger1 = AnimTime >= 0", f"value = {n}",
                           f"elem = {len(keys)}", "",
                           f"[State {st}, {tr('Fin del rayo')}]", "type = ChangeState",
                           f"trigger1 = Time >= {t_hf + btime}", "trigger1 = statetype != A", "value = 0",
                           "ctrl = 1", ""]
            elif helper:
                hp = sp.get("proj") or {}
                hk = _frames(hp)
                hhf = hit_frame_of(hp, hk, sprites)
                hx = round(prm["px"] * scale)
                hy = round(prm["py"] * scale) if sp.get("proj_y") is not None else 0
                sd += [f"[State {st}, {tr('Llama al ayudante')}]", "type = Helper", f"trigger1 = AnimElem = {hf + 1}",
                       "helpertype = normal", f'name = "{_lbl(name)}"', f"ID = {n}", f"stateno = {n + 20}",
                       f"pos = {hx}, {hy}", "postype = p1", "facing = 1", "keyctrl = 0", "ownpal = 1", ""]
                if not helper_done:
                    helper_done = True
                    hspeed = float(spec(sp, "helper_speed")) * k
                    life = max(10, int(spec(sp, "helper_life")))
                    hst = n + 20
                    hs = [f"; {_lbl(name)} ({tr('ayudante')})", f"[Statedef {hst}]", "type = S", "movetype = A",
                          "physics = N", "ctrl = 0", f"anim = {n + 50}", "velset = 0, 0", "sprpriority = 3", "",
                          f"[State {hst}, {tr('No le pueden pegar')}]", "type = NotHitBy", "trigger1 = 1",
                          "value = SCA", "time = 1", "",
                          f"[State {hst}, {tr('Avanza')}]", "type = VelSet", "trigger1 = Time = 0",
                          f"x = {_fmt(round(hspeed, 2))}", ""]
                    hd_h = [x for x in hd if not x.startswith("sparkxy")]
                    if hits > 1:
                        t0 = f"AnimElemTime({hhf + 1})"
                        hs += [f"[State {hst}, {tr('Golpe')}]", "type = HitDef", f"trigger1 = {t0} >= 0",
                               f"trigger1 = ({t0} % {gap}) = 0", f"trigger1 = {t0} < {hits * gap}"] + hd_h + [""]
                    else:
                        hs += [f"[State {hst}, {tr('Golpe')}]", "type = HitDef",
                               f"trigger1 = AnimElem = {hhf + 1}"] + hd_h + [""]
                    hs += [f"[State {hst}, {tr('Se va')}]", "type = DestroySelf", "trigger1 = AnimTime = 0",
                           f"trigger2 = Time >= {life}", ""]
                    g.states.append("\n".join(hs))
            elif typ == "grab":
                sd += [f"[State {st}, {tr('Agarrar')}]", "type = HitDef", "trigger1 = Time = 0", "attr = S, ST",
                       "hitflag = M-", "priority = 6, Miss", "sparkno = -1", "p1sprpriority = 1",
                       "p2sprpriority = 0", "p1facing = 1", "p2facing = 1", f"p1stateno = {n + 10}",
                       f"p2stateno = {n + 20}", "guard.dist = 0", "fall = 1", ""]
            elif typ == "counter":
                win = int(spec(sp, "counter_window"))
                hd2 = [x for x in hd if not x.startswith(("attr", "guardflag", "hitflag", "priority"))]
                sd += [f"[State {st}, {tr('Contraataque')}]", "type = ReversalDef", "trigger1 = Time = 0",
                       "reversal.attr = SCA, AA"] + hd2 + ["",
                       f"[State {st}, {tr('Fin del contraataque')}]", "type = ReversalDef",
                       f"trigger1 = Time = {win}", "reversal.attr =", ""]
            elif typ == "none":
                pass
            elif user_hf and mode == "last" and len(runs) > 1:
                # los golpes de antes lo dejan aturdido; el último lo tumba / lo lanza
                trig = [f"trigger{i + 1} = AnimElem = {run[0] + 1}" for i, run in enumerate(runs[:-1])]
                sd += [f"[State {st}, {tr('Golpe')}]", "type = HitDef"] + trig + hd_stun + [""]
                sd += [f"[State {st}, {tr('Último golpe (lo tumba)')}]", "type = HitDef",
                       f"trigger1 = AnimElem = {runs[-1][0] + 1}"] + hd_fly + [""]
            elif user_hf:
                trig = [f"trigger{i + 1} = AnimElem = {run[0] + 1}" for i, run in enumerate(runs)]
                sd += [f"[State {st}, {tr('Golpe')}]", "type = HitDef"] + trig + hd + [""]
            elif hits > 1 and mode == "last":
                t0 = f"AnimElemTime({hf + 1})"
                sd += [f"[State {st}, {tr('Golpe')}]", "type = HitDef", f"trigger1 = {t0} >= 0",
                       f"trigger1 = ({t0} % {gap}) = 0", f"trigger1 = {t0} < {(hits - 1) * gap}"] + hd_stun + [""]
                sd += [f"[State {st}, {tr('Último golpe (lo tumba)')}]", "type = HitDef",
                       f"trigger1 = {t0} = {(hits - 1) * gap}"] + hd_fly + [""]
            elif hits > 1:
                t0 = f"AnimElemTime({hf + 1})"
                sd += [f"[State {st}, {tr('Golpe')}]", "type = HitDef", f"trigger1 = {t0} >= 0",
                       f"trigger1 = ({t0} % {gap}) = 0", f"trigger1 = {t0} < {hits * gap}"] + hd + [""]
            else:
                sd += [f"[State {st}, {tr('Golpe')}]", "type = HitDef", "trigger1 = Time = 0"] + hd + [""]
            sd += ev_lines(sp.get("events"), st, strength, vv=vv)
            if spec(sp, "stop_on_hit") and typ in ("dash", "hit"):
                # al pegar (o al cubrirse el rival) se queda en ese lugar: no sigue de largo empujándolo
                sd += [f"[State {st}, {tr('Se detiene al pegar')}]", "type = VelSet", "trigger1 = MoveContact",
                       "x = 0", ""]
            if use == "both" or (evmode and not air_mode):
                # termina al acabar la animación si está en el suelo (si salió volando, aterriza solo)
                sd += [f"[State {st}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0",
                       "trigger1 = statetype != A", "value = 0", "ctrl = 1", ""]
            elif not air_mode:
                sd += [f"[State {st}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0",
                       "value = 0", "ctrl = 1", ""]
            if after_hit:
                sd = [re.sub(r"^((?:ground|air)\.hittime = )(\d+)$",
                             lambda m: m.group(1) + str(max(int(m.group(2)), after_hit)), x) for x in sd]
                # sin «air.hittime» el rival en el aire se recupera a los 20 ticks
                sd = [x + (f"\nair.hittime = {after_hit}" if x.startswith("ground.hittime = ") and
                           not any(y.startswith("air.hittime") for y in sd) else "") for x in sd]
            if ender_:
                # remate: más daño y tumba al rival; su entrada va con los autodobles (solo sale después de uno)
                g.states.append(ender_text("\n".join(sd), st, st, max(0, int(cb.get("ender_bonus", 30)))
                                           if cb is not None else 30, k, tr))
                ender_items.append(dict(st=st, name=lbl, cmd=f"{cname}_{v}", hold=held_dir(motion), use=use))
                continue
            g.states.append("\n".join(sd))
            if (cb is not None and cb.get("enders") and not single and v == 2 and typ in ("hit", "dash", "rise")
                    and not any(ender_base(o, specials) is sp for o in specials)):
                ender_src.append(dict(sp=sp, idx=idx, st=st, text="\n".join(sd), name=name,
                                      cmd=f"{cname}_{v}", hold=held_dir(motion), use=use))
            e = [f"[State -1, SM: {lbl}]", "type = ChangeState", f"value = {st}",
                 f'triggerall = command = "{cname}_{v}"']
            hd_ = held_dir(motion)
            if hd_ in ("F", "B"):
                # la flecha tiene que seguir aguantada en el mismo tick del botón
                e.append(f'triggerall = command = "sm_hold_{hd_}"')
            if super_:
                e.append(f"triggerall = power >= {1000 * cost}")
            elif v == 3:
                e.append(f"triggerall = power >= {int(spec(sp, 'ex_cost'))}")
            if proj:
                e.append(f"triggerall = NumProjID({n}) = 0")
            if helper:
                e.append(f"triggerall = NumHelper({n}) = 0")
            if typ == "grab":
                e += [f"triggerall = p2bodydist X < {round(int(spec(sp, 'grab_range')) * k)}",
                      "triggerall = p2statetype != A", "triggerall = p2movetype != H"]
            st_cond = {"ground": "statetype != A", "air": "statetype = A", "both": "statetype != L"}[use]
            e += [f"trigger1 = {st_cond}", "trigger1 = ctrl"]
            if spec(sp, "cancel"):
                e += [f"trigger2 = {st_cond}", "trigger2 = movecontact", f"trigger2 = {cancel_expr}"]
            if super_ and spec(sp, "cancel_specials") and special_states:
                e += [f"trigger3 = {st_cond}", "trigger3 = movecontact",
                      "trigger3 = " + " || ".join(f"stateno = {x}" for x in special_states)]
            ent_special.append(("0" if super_ else "1", "\n".join(e) + "\n"))
        if typ == "grab":
            dmgg = int(sp.get("damage", 60))
            dist = round(int(spec(sp, "grab_range")) * 0.6 * k)
            anim_hold = n + 5 if hf + 1 < len(keys) else n
            sd = [f"; {name} ({tr('lo tiene agarrado')})", f"[Statedef {n + 10}]", "type = S", "movetype = A",
                  "physics = N", "velset = 0, 0", "ctrl = 0", f"anim = {anim_hold}", "sprpriority = 2", "",
                  f"[State {n + 10}, {tr('Sujetar')}]", "type = TargetBind", "trigger1 = AnimTime < 0",
                  f"pos = {dist}, 0", "",
                  f"[State {n + 10}, {tr('Daño')}]", "type = TargetLifeAdd", "trigger1 = AnimTime = 0",
                  f"value = {-dmgg}", "",
                  f"[State {n + 10}, {tr('Lanzar')}]", "type = TargetState", "trigger1 = AnimTime = 0",
                  f"value = {n + 21}", ""]
            sd += ev_lines([e_ for e_ in sp.get("events") or [] if e_.get("type") in ("shake", "sound", "flash")],
                           n + 10, 2)
            sd += [f"[State {n + 10}, {tr('Fin')}]", "type = ChangeState", "trigger1 = AnimTime = 0", "value = 0",
                   "ctrl = 1", "",
                   f"; {name} ({tr('el rival, agarrado')})", f"[Statedef {n + 20}]", "type = A", "movetype = H",
                   "physics = N", "velset = 0, 0", "",
                   f"[State {n + 20}, {tr('Animación')}]", "type = ChangeAnim", "trigger1 = Time = 0",
                   "value = 5000", "",
                   f"; {name} ({tr('el rival, lanzado')})", f"[Statedef {n + 21}]", "type = A", "movetype = H",
                   "physics = N", "",
                   f"[State {n + 21}, {tr('Volar')}]", "type = VelSet", "trigger1 = Time = 0",
                   f"x = {_fmt(round(-4 * k, 2))}", f"y = {_fmt(round(-7 * k, 2))}", "",
                   f"[State {n + 21}, {tr('Caer')}]", "type = HitFallSet", "trigger1 = Time = 0", "value = 1", "",
                   f"[State {n + 21}, {tr('Caer')} 2]", "type = SelfState", "trigger1 = Time = 0", "value = 5050", ""]
            g.states.append("\n".join(sd))

    # -------- autodobles (estilo Killer Instinct): cada golpe usa una animación que ya tiene el personaje
    ad_cancel_real = []
    ad_clock = []                 # MapSet con GameTime: hasta cuándo se puede seguir el combo
    ad_clock_states = []
    ad_first, ad_rest = [], []
    raw_list = None
    if cb is not None and cb["autodouble"] and opener_states:
        # la lista guardada (los números elegidos se escriben aquí para que no cambien)
        raw_list = cfg.setdefault("combos", {}).setdefault("ad_list", copy.deepcopy(cb["ad_list"]))
    if raw_list:
        acts = {a.number: a for a in g.actions}
        limit = max(0, int(cb.get("ad_limit", 0)))
        ad_max = max(0, int(cb.get("ad_max", 0) or 0))   # autodobles por combo (KI2: 4); el último tumba
        cs = combos.state_list

        def find_act(num):
            if num is None:
                return None
            a_ = acts.get(num) or (air.find(num) if air is not None else None)
            return a_ if (a_ is not None and a_.frames) else None

        def resolve(ref):
            """«N:S_x» / «P:<especial>» / «O:<acción>» → acción o None."""
            ref = str(ref or "")
            if not ref:
                return None
            if ":" not in ref:
                ref = "N:" + ref                       # versiones viejas: solo la clave del golpe normal
            kind, _, key = ref.partition(":")
            if kind == "N":
                return norm_act[key][0] if (key in norm_act and norm[key][1] != "A") else None
            if kind == "P":
                for i_, sp_ in enumerate(specials):
                    if special_ref(i_, sp_) == ref:
                        return find_act(special_anim(sp_))
                return None
            if kind == "O" and key.lstrip("-").isdigit():
                return find_act(int(key))
            return None

        def timing(a):
            """(tick donde empieza a pegar, tick donde empieza el último cuadro que pega, duración)."""
            t, first, last = 0, None, None
            for f in a.frames:
                if f.clsn1:
                    first = t if first is None else first
                    last = t
                t += max(1, f.time) if f.time > 0 else 10
            return (first or 0), (last or 0), t

        def after_last_hit(states):
            """Condición «ya pasó el último golpe» para cada estado (el autodoble no corta el especial)."""
            out = []
            for st_ in states:
                a_ = find_act(state_anim.get(st_))
                reds = [i for i, f in enumerate(a_.frames) if f.clsn1] if a_ is not None else []
                if state_after.get(st_):
                    out.append(state_after[st_].format(st=st_))
                elif not reds:
                    out.append(f"StateNo = {st_}")          # no se sabe: como antes
                elif reds[-1] + 1 < len(a_.frames):
                    out.append(f"(StateNo = {st_} && AnimElemTime({reds[-1] + 2}) >= 0)")
                # si el último cuadro pega, el autodoble sale apenas termina (con el reloj)
            return " || ".join(out) if out else "0"

        # lo que tarda en pegar el especial más lento (el «enlace» tiene que llegar con el rival aturdido)
        link_time = 14
        for sp_ in specials:
            fk_ = _frames(sp_)
            if sp_.get("kind") in ("super",) or not fk_ or sp_.get("type") in ("converted", "none", "counter"):
                continue
            link_time = max(link_time, min(40, (hit_frame_of(sp_, fk_, sprites) + 1) * int(sp_.get("time", 4)) + 4))
        step_max = _fmt(round(3 * k, 2))
        near = round(10 * k)
        ad_step = 12              # lo que se puede acercar con el pasito del primer golpe
        buttons_of = {"punch": lambda s_: [BUTTONS[s_]], "kick": lambda s_: [BUTTONS[s_ + 3]],
                      "any": lambda s_: [BUTTONS[s_], BUTTONS[s_ + 3]]}
        for i, ad in enumerate(raw_list):
            s_ = min(2, max(0, int(ad.get("strength", 1))))
            hits_cfg = [h for h in (ad.get("hits") or []) if h.get("ref")]
            hits = [(resolve(h["ref"]), int(h.get("speed") or 100)) for h in hits_cfg]
            hits = [(a_, pct) for a_, pct in hits if a_ is not None]
            if not hits:
                continue
            st = al.get(ad.get("state"), 750 + i, (0,), ())
            abase = al.get(ad.get("anim"), 7500 + 20 * i, (), tuple(range(20)))
            if st is None or abase is None:
                g.problems.append(tr("Autodoble"))
                continue
            ad["state"], ad["anim"] = st, abase
            name_ = _lbl(ad.get("name") or f"{tr('Autodoble')} ({tr(STRENGTH[s_])})")
            dmg_ = max(1, int(ad.get("damage") or [15, 22, 30][s_]))
            # cada golpe con su animación (copia si cambia la rapidez, se repite o tiene un cuadro infinito)
            used = set()
            anims = []
            for j, (a_, pct) in enumerate(hits[:20]):
                if pct != 100 or any(f.time <= 0 for f in a_.frames) or a_.number in used:
                    b_ = copy.deepcopy(a_)
                    b_.number = abase + j
                    b_.raw = None
                    for f in b_.frames:
                        t_ = f.time if f.time > 0 else 10
                        f.time = max(1, int(round(t_ * 100.0 / max(10, pct))))
                    g.actions.append(b_)
                    a_ = b_
                used.add(a_.number)
                anims.append(a_)
            if len(anims) == 1:
                b_ = copy.deepcopy(anims[0])            # un solo golpe: igual son dos (autodoble)
                b_.number = abase + 19
                b_.raw = None
                g.actions.append(b_)
                anims.append(b_)
            # golpes bajos (los agachados): cuentan como bajos para el combo breaker de KI2
            lows = [str(h_.get("ref", "")).startswith("N:C_") for h_ in hits_cfg][:len(anims)]
            lows += [lows[-1] if lows else False] * (len(anims) - len(lows))
            tim = [timing(a_) for a_ in anims]
            stun = []
            for j in range(len(anims)):
                h1, _l, d1 = tim[j]
                nxt = tim[j + 1][0] if j + 1 < len(anims) else link_time
                stun.append((d1 - h1) + nxt + 6)
            sd = [f"; {name_}", f"[Statedef {st}]", "type = S", "movetype = A", "physics = S", "juggle = 0",
                  "velset = 0, 0", "ctrl = 0", f"anim = {anims[0].number}", "poweradd = 15", "sprpriority = 2", ""]
            if ad_max:
                sd += [f"[State {st}, {tr('Cuenta de autodobles')}]", "type = MapAdd", "trigger1 = Time = 0",
                       'map = "sm_adn"', "value = 1", ""]

            def ad_hit(lbl, trig, box_, n_hit, sd=sd, st=st, s_=s_, stun=stun, dmg_=dmg_, n_all=len(anims),
                       low=lows):
                # sin empujar (el rival se queda pegado) … salvo pasado el límite del combo
                base_ = [x for x in hitdef("S, NA", dmg_, 0, s_, "MA", "Low" if low[n_hit] else "High", k, box_)
                         if not x.startswith(("ground.velocity", "air.velocity", "ground.hittime"))]
                base_ += [f"ground.hittime = {max(PAUSE[s_] + 4, stun[n_hit])}",
                          f"air.hittime = {max(PAUSE[s_] + 4, stun[n_hit])}"]
                stay = base_ + ["ground.velocity = 0", f"air.velocity = 0, {_fmt(round(-2.5 * k, 2))}"]
                if ad_max and n_hit == n_all - 1:
                    # el último autodoble que se permite en el combo: su último golpe tumba al rival
                    push = PUSH[2] * k
                    sd += [f"[State {st}, {lbl} ({tr('último autodoble del combo')})]", "type = HitDef"] + trig + \
                        [f"trigger1 = Map(sm_adn) >= {ad_max}"] + base_ + \
                        [f"ground.velocity = {_fmt(round(-push * 0.6, 2))}, {_fmt(round(-6 * k, 2))}",
                         f"air.velocity = {_fmt(round(-push * 0.6, 2))}, {_fmt(round(-6 * k, 2))}",
                         "fall = 1", "air.fall = 1", "fall.recover = 0", ""]
                    trig = trig + [f"trigger1 = Map(sm_adn) < {ad_max}"]
                if not limit:
                    sd += [f"[State {st}, {lbl}]", "type = HitDef"] + trig + stay + [""]
                    return
                t2 = [x.replace("trigger1", "trigger2") for x in trig]
                sd += [f"[State {st}, {lbl}]", "type = HitDef"] + trig + ["trigger1 = EnemyNear, MoveType != H"] + \
                    t2 + [f"trigger2 = EnemyNear, GetHitVar(hitcount) < {limit}"] + stay + [""]
                push = PUSH[2] * k
                sd += [f"[State {st}, {lbl} ({tr('pasó del límite')})]", "type = HitDef"] + trig + \
                    ["trigger1 = EnemyNear, MoveType = H",
                     f"trigger1 = EnemyNear, GetHitVar(hitcount) >= {limit}"] + base_ + \
                    [f"ground.velocity = {_fmt(round(-push, 2))}, {_fmt(round(-5 * k, 2))}",
                     f"air.velocity = {_fmt(round(-push, 2))}, {_fmt(round(-5 * k, 2))}",
                     "fall = 1", "air.fall = 1", "fall.recover = 0", ""]

            # acercarse al rival (si quedó lejos, por ejemplo después de una embestida)
            # un pasito si quedó un poco separado (nunca corre: de lejos el autodoble no sale)
            approach = (f"x = ifelse(P2BodyDist X > {near}, "
                        f"ifelse((P2BodyDist X - {near}) / 5.0 > {step_max}, {step_max}, (P2BodyDist X - {near}) / 5.0), 0)")
            for j, a_ in enumerate(anims):
                box_ = next((f.clsn1 for f in a_.frames if f.clsn1), [])
                if j == 0:
                    first_ = a_.number
                    sd += [f"[State {st}, {tr('Acercarse')}]", "type = VelSet", "trigger1 = Time = 0", approach, ""]
                    ad_hit(f"{tr('Golpe')} 1", [f"trigger1 = Anim = {first_}", "trigger1 = AnimElemTime(1) = 0"],
                           box_, 0)
                else:
                    prev = anims[j - 1].number
                    sd += [f"[State {st}, {tr('Golpe')} {j + 1}: {tr('animación')}]", "type = ChangeAnim",
                           f"trigger1 = Anim = {prev}", "trigger1 = AnimTime = 0", f"value = {a_.number}", "",
                           f"[State {st}, {tr('Acercarse')} {j + 1}]", "type = VelSet", f"trigger1 = Anim = {a_.number}",
                           "trigger1 = AnimElemTime(1) = 0", approach, ""]
                    ad_hit(f"{tr('Golpe')} {j + 1}", [f"trigger1 = Anim = {a_.number}", "trigger1 = AnimElemTime(1) = 0",
                                                      "trigger1 = Time > 0"], box_, j)
            last = anims[-1].number
            sd += [f"[State {st}, {tr('Fin')}]", "type = ChangeState", f"trigger1 = Anim = {last}",
                   "trigger1 = AnimTime = 0", "trigger1 = Time > 0", "value = 0", "ctrl = 1", ""]
            g.states.append("\n".join(sd))
            # se cancela (linker, remate, súper) solo después de que pega su último golpe: no se interrumpe
            red_ = next((j for j, f in enumerate(anims[-1].frames) if f.clsn1), None)
            ad_cancel_real.append(f"(StateNo = {st} && Anim = {last}" +
                                  (f" && AnimElemTime({red_ + 1}) > 0)" if red_ is not None else ")"))
            ad_clock_states.append(st)
            # con qué especial inicia (o cualquiera) y la regla de botones
            opener = str(ad.get("open") or "")
            if opener.startswith("P:") and opener in spec_states:
                from_states = spec_states[opener]
            elif opener.startswith("S:"):
                from_states = [int(x) for x in opener[2:].split(",") if x.strip().lstrip("-").isdigit()]
            else:
                from_states = opener_states
            if cb.get("ad_rule") == "classic":
                # Killer Instinct clásico: fuerte → medio, medio → débil, débil → fuerte
                allowed = set(states_by_v.get((s_ + 1) % 3, []))
                if opener.startswith("S:"):
                    allowed |= set(from_states)       # los del personaje: no se sabe su fuerza
                from_states = [x for x in from_states if x in allowed]
            if not from_states:
                continue
            btns = buttons_of.get(ad.get("button", "any"), buttons_of["any"])(s_)
            # alcance: hasta dónde llega la caja roja del primer golpe (más un pasito); más lejos no sale
            box0 = next((f.clsn1 for f in anims[0].frames if f.clsn1), [])
            reach_px = max([max(bx[0], bx[2]) for bx in box0] or [round(40 * k)])
            reach = (f"P2BodyDist X <= {reach_px} * const(size.xscale) - const(size.ground.front) + "
                     f"{round(ad_step * k)}")
            # especiales y súper con proyectil: el golpe lo da el proyectil (MoveContact no lo cuenta)
            pids = sorted({state_proj[x] for x in from_states if x in state_proj})
            proj_hit = " || ".join(f"(ProjHitTime({pid}) >= 0 && ProjHitTime({pid}) <= {KI_GRACE})" for pid in pids)
            proj_trig = ([f"trigger3 = {proj_hit}",
                          "trigger3 = ctrl || " + cs([x for x in from_states if x in state_proj]),
                          "trigger3 = NumEnemy", "trigger3 = EnemyNear, MoveType = H"] if pids else [])
            # los que inician con un especial escogido van primero: ganan sobre los de «cualquier especial»
            (ad_first if opener else ad_rest).append("\n".join([
                f"[State -1, SM: {name_}]", "type = ChangeState", f"value = {st}",
                "triggerall = " + " || ".join(f'command = "sm_{b}_ad"' for b in btns), "triggerall = statetype != A",
                "triggerall = Map(sm_end) = 0"] + ([f"triggerall = Map(sm_adn) < {ad_max}"] if ad_max else []) + [
                # solo con el rival en el suelo recibiendo el golpe (de pie o agachado): no en el aire ni cubriéndose
                "triggerall = NumEnemy", "triggerall = EnemyNear, StateType != A",
                "triggerall = EnemyNear, StateNo = [5000, 5019]",
                # cerca: el autodoble es parte del combo, no corre hasta el rival
                "triggerall = " + reach,
                # después del último golpe del especial (no lo corta)…
                "trigger1 = movehit", "trigger1 = " + after_last_hit(from_states),
                # … o apenas termina, con el rival todavía aturdido
                "trigger2 = ctrl", f"trigger2 = GameTime - Map(sm_ad{i}t) <= {KI_GRACE}",
                "trigger2 = NumEnemy", "trigger2 = EnemyNear, MoveType = H"] + proj_trig) + "\n")
            # el reloj: cuándo pegó por última vez un especial que abre este autodoble (Map: no usa var)
            ad_clock.append("\n".join([
                f"[State -1, SM: {name_}: {tr('reloj')}]", "type = MapSet", "trigger1 = movehit",
                "trigger1 = " + cs(from_states), f'map = "sm_ad{i}t"', "value = GameTime"]) + "\n")
    ent_combo += ad_first + ad_rest
    if ad_clock_states:
        ad_clock.append("\n".join([
            f"[State -1, SM: {tr('Autodoble')}: {tr('reloj')}]", "type = MapSet",
            "trigger1 = " + combos.state_list(ad_clock_states), 'map = "sm_adt"', "value = GameTime"]) + "\n")
    ent_combo[0:0] = ad_clock

    # -------- remates (Ender): después de un autodoble tumban y cierran el combo
    def ender_entry(est, name, cmd, hold, use):
        st_cond = {"ground": "statetype != A", "air": "statetype = A", "both": "statetype != L"}[use]
        e = [f"[State -1, SM: {_lbl(name)} ({tr('Remate')})]", "type = ChangeState", f"value = {est}",
             f'triggerall = command = "{cmd}"']
        if hold in ("F", "B"):
            e.append(f'triggerall = command = "sm_hold_{hold}"')
        e += [f"trigger1 = {st_cond}", "trigger1 = movecontact", "trigger1 = " + " || ".join(ad_cancel_real),
              # o justo después del autodoble, con el rival todavía aturdido (como en KI, con margen)
              f"trigger2 = {st_cond}", "trigger2 = ctrl", f"trigger2 = GameTime - Map(sm_adt) <= {KI_GRACE}",
              "trigger2 = NumEnemy", "trigger2 = EnemyNear, MoveType = H"]
        ent_special.insert(0, ("0", "\n".join(e) + "\n"))

    ender_states = []
    if ad_cancel_real:
        for ei in ender_items:
            ender_entry(ei["st"], ei["name"], ei["cmd"], ei["hold"], ei["use"])
            ender_states.append(ei["st"])
    if cb is not None and cb.get("enders") and ad_cancel_real:
        extra_pct = max(0, int(cb.get("ender_bonus", 30)))
        for ed in ender_src:
            sp_ = ed["sp"]
            est = al.get(sp_.get("ender_state"), 4000 + 10 * ed["idx"], (0,), ())
            if est is None:
                continue
            sp_["ender_state"] = est
            g.states.append(ender_text(ed["text"], ed["st"], est, extra_pct, k, tr))
            ender_entry(est, ed["name"], ed["cmd"], ed["hold"], ed["use"])
            ender_states.append(est)
    if ad_clock_states:
        # el combo se cierra: después de un remate que pegó no sale otro autodoble, especial ni remate hasta que
        # el rival se recupere; y la cuenta de autodobles vuelve a 0 cuando el combo se acaba
        free_ = ["trigger1 = !NumEnemy", "trigger2 = NumEnemy", "trigger2 = EnemyNear, MoveType != H"]
        ent_combo[0:0] = ["\n".join([f"[State -1, SM: {tr('Autodoble')}: {tr('fin del combo')}]", "type = MapSet",
                                      'map = "sm_adn"', "value = 0"] + free_) + "\n"]
        if ender_states:
            ent_combo[0:0] = [
                "\n".join([f"[State -1, SM: {tr('Remate')}: {tr('cierra el combo')}]", "type = MapSet",
                           "trigger1 = movecontact", "trigger1 = " + combos.state_list(ender_states),
                           'map = "sm_end"', "value = 1"]) + "\n",
                "\n".join([f"[State -1, SM: {tr('Remate')}: {tr('fin del combo')}]", "type = MapSet",
                           'map = "sm_end"', "value = 0"] + free_) + "\n"]
            ent_special = [(o, e.replace("type = ChangeState\n", "type = ChangeState\ntriggerall = Map(sm_end) = 0\n", 1))
                           for o, e in ent_special]

    # de un autodoble solo se cancela en especial desde su segundo golpe
    real = "".join(" || " + x for x in ad_cancel_real)
    ent_special = [(o, e.replace(AD_CANCEL_JOIN, real).replace(AD_CANCEL, real[4:] if real else "0"))
                   for o, e in ent_special]

    # -------- voces de golpes recibidos, KO, victoria e intro
    ent_voice = []
    for vkey, trig in (("hurt", "Alive"), ("ko", "!Alive")):
        snd = voice(vkey)
        if snd:
            ent_voice.append("\n".join([
                f"[State -1, SM: {tr('Voz')} {vkey}]", "type = PlaySnd", f"value = {snd[0]}, {snd[1]}", "channel = 0",
                "trigger1 = Time = 0", f"trigger1 = {trig}",
                "trigger1 = StateNo = 5000 || StateNo = 5010 || StateNo = 5020"]) + "\n")
    for vkey, stn in (("win", "180"), ("intro", "190")):
        snd = voice(vkey)
        if snd:
            ent_voice.append("\n".join([
                f"[State -1, SM: {tr('Voz')} {vkey}]", "type = PlaySnd", f"value = {snd[0]}, {snd[1]}", "channel = 0",
                "trigger1 = Time = 0", f"trigger1 = StateNo = {stn}"]) + "\n")

    # voces del combo: al llegar a cierta cantidad de golpes (la más alta que se alcanzó, una sola vez)
    cv = sorted([x for x in cfg.get("combo_voices", []) if isinstance(x.get("snd"), list) and int(x.get("hits", 0)) > 1],
                key=lambda x: -int(x["hits"]))
    if cv:
        ent_voice.append("\n".join([
            f"[State -1, SM: {tr('Voz del combo')}: {tr('fin del combo')}]", "type = MapSet", 'map = "sm_cv"',
            "value = 0", "trigger1 = Map(sm_cv) > 0", "trigger1 = !NumEnemy", "trigger2 = Map(sm_cv) > 0",
            "trigger2 = NumEnemy", "trigger2 = EnemyNear, MoveType != H"]) + "\n")
        for x in cv:
            n_, snd = int(x["hits"]), x["snd"]
            trig = ["trigger1 = NumEnemy", "trigger1 = EnemyNear, MoveType = H",
                    f"trigger1 = EnemyNear, GetHitVar(hitcount) >= {n_}", f"trigger1 = Map(sm_cv) < {n_}"]
            ent_voice.append("\n".join([
                f"[State -1, SM: {tr('Voz del combo')} {n_}]", "type = PlaySnd", f"value = {snd[0]}, {snd[1]}",
                "channel = 0", "ignorehitpause = 1"] + trig) + "\n")
            ent_voice.append("\n".join([
                f"[State -1, SM: {tr('Voz del combo')} {n_} ({tr('ya sonó')})]", "type = MapSet", 'map = "sm_cv"',
                f"value = {n_}", "ignorehitpause = 1"] + trig) + "\n")

    # ayuda para combos: el rival se queda aturdido unos ticks más después de cada golpe
    extra = int(cb["extra_stun"]) if cb is not None else 0
    if extra > 0:
        g.states = [t if i in conv_idx else
                    re.sub(r"(?m)^(ground\.hittime = )(\d+)", lambda m: m.group(1) + str(int(m.group(2)) + extra), t)
                    for i, t in enumerate(g.states)]
    # -------- movimientos apagados («Lo tiene» sin tick): aunque algo los dispare (otra entrada del .cmd, la
    # computadora o el juego mismo), el personaje sale enseguida de ese estado
    ent_off = []
    for key, states, back, label in (("run", "100, 101", "0", tr("Correr")),
                                     ("hop", "105, 106", "0", tr("Salto hacia atrás")),
                                     ("air_recover", "5200, 5210", "5050", tr("Recuperarse en el aire"))):
        if is_off(cfg, key):
            ent_off.append("\n".join([
                f"[State -1, SM: {_lbl(label)} ({tr('apagado')})]", "type = ChangeState",
                f"trigger1 = StateNo = [{states}]", f"value = {back}"] + (["ctrl = 1"] if back == "0" else [])) + "\n")
    off_orig = sorted({int(x) for x in cfg.get("orig_off", [])})
    if off_orig:
        ent_off.append("\n".join([
            f"[State -1, SM: {tr('Movimientos del personaje apagados')}]", "type = ChangeState",
            "trigger1 = " + combos.state_list(off_orig), "value = ifelse(statetype = A, 50, 0)", "ctrl = 1"]) + "\n")

    # -------- varias poses de victoria / derrota: el juego escoge una al azar
    for main_, stn, extra_lines in (("win", 180, []), ("lose", 170, ["[State 170, SM]", "type = NotHitBy",
                                                                   "trigger1 = 1", "value = SCA", "time = 1", ""])):
        nums = [ANIM_SLOTS[main_][3]] + [ANIM_SLOTS[x][3] for x, m in EXTRA_POSES.items()
                                         if m == main_ and own_frames(cfg, x)[0]]
        if len(nums) < 2 or stn in al.ts:
            continue
        al.ts.add(stn)
        pick = str(nums[-1])
        for j in range(len(nums) - 2, -1, -1):
            pick = f"ifelse(Random % {len(nums) - j} = 0, {nums[j]}, {pick})"
        g.states.append("\n".join([
            f"; {_lbl(tr('Poses al azar'))}: {', '.join(str(x) for x in nums)}",
            f"[Statedef {stn}]", "type = S", "movetype = I", "physics = S", "ctrl = 0", "velset = 0, 0",
            f"anim = {nums[0]}", "",
            f"[State {stn}, SM: {_lbl(tr('Pose al azar'))}]", "type = ChangeAnim", "trigger1 = Time = 0",
            f"value = {pick}", ""] + extra_lines) + "\n")

    ent_ai = ai_entries(cfg, specials, norm, k, tr)

    g.commands = commands
    g.entries = (ent_off + ent_ai + [e for o, e in sorted(ent_special, key=lambda x: x[0])] + ent_combo + ent_throw + ent_rep + ent_air + ent_crouch +
                 ent_stand[::-1] + ent_voice)
    owned = {a.number for a in g.actions}
    cfg["owned"] = sorted(owned)
    return g


# ---------------------------------------------------------------- IA de la computadora
AI_RANGES = [("auto", "Automático (según lo que hace)"), ("near", "De cerca"), ("mid", "A media distancia"),
             ("far", "De lejos"), ("air", "Contra un rival que salta"), ("never", "Nunca")]


def ai_auto_range(sp):
    typ = sp.get("type", "proj")
    if sp.get("kind") == "super":
        return "mid" if typ in ("proj", "helper") else "near"
    return {"proj": "far", "rise": "air", "dash": "mid", "hit": "near", "grab": "near", "helper": "mid",
            "counter": "never", "none": "never"}.get(typ, "mid")


def ai_entries(cfg, specials, norm, k, tr=lambda s: s):
    """Entradas del .cmd para la computadora (solo cuando la maneja el CPU: AILevel > 0)."""
    ai = cfg.get("ai") or {}
    if not ai.get("on"):
        return []
    aggr = max(1, min(10, int(ai.get("aggr", 5))))
    chance = aggr * 4                       # de 1000 por tick, a nivel de IA 4
    near, mid = round(30 * k), round(110 * k)
    rng = {"near": f"P2BodyDist X < {near}", "mid": f"P2BodyDist X = [{near}, {mid}]",
           "far": f"P2BodyDist X > {mid}",
           "air": f"P2StateType = A && P2BodyDist X < {round(70 * k)} && P2Dist Y < {round(-20 * k)}"}
    base = ["triggerall = AILevel > 0", "triggerall = RoundState = 2", "triggerall = NumEnemy",
            "triggerall = EnemyNear, Alive"]
    out = []
    by = ai.get("moves") or {}
    for idx, sp in enumerate(specials):
        n = sp.get("state")
        if n is None or sp.get("type") == "converted" or sp.get("kind") == "ender" or not _frames(sp):
            continue
        r = by.get(sp.get("uid") or str(idx), "auto")
        r = ai_auto_range(sp) if r == "auto" else r
        if r not in rng:
            continue
        vs = [v for v in sp_versions(sp) if v < 3] or sp_versions(sp)
        st = n + max(vs)
        use = spec(sp, "use_where")
        where = "statetype = A" if use == "air" else ("statetype != L" if use == "both" else "statetype != A")
        e = [f"[State -1, SM: {tr('IA')}: {_lbl(sp.get('name') or '?')}]", "type = ChangeState", f"value = {st}"]
        e += base
        if sp.get("kind") == "super":
            e.append(f"triggerall = power >= {1000 * max(1, int(spec(sp, 'power_cost')))}")
            if not ai.get("supers", True):
                continue
        if sp.get("type") == "proj":
            e.append(f"triggerall = NumProjID({n}) = 0")
        if sp.get("type") == "helper":
            e.append(f"triggerall = NumHelper({n}) = 0")
        e += [f"trigger1 = {where}", "trigger1 = ctrl", f"trigger1 = {rng[r]}",
              f"trigger1 = Random < {chance * (2 if r == 'air' else 1)} * AILevel / 4"]
        if ai.get("combos", True) and r in ("near", "mid") and sp.get("type") in ("hit", "dash", "rise", "proj", "helper"):
            # combo: cancela un golpe normal que pegó en este especial
            e += ["trigger2 = MoveHit", "trigger2 = StateNo = [200, 699]", f"trigger2 = {where}",
                  f"trigger2 = Random < {150 + chance * 10} * AILevel / 8"]
        out.append("\n".join(e) + "\n")
    # golpes normales de cerca (y el agarre)
    stand = [v[0] for key, v in norm.items() if v[1] == "S"]
    if stand:
        pick = str(stand[-1])
        for j in range(len(stand) - 2, -1, -1):
            pick = f"ifelse(Random % {len(stand) - j} = 0, {stand[j]}, {pick})"
        out.append("\n".join([f"[State -1, SM: {tr('IA')}: {tr('golpes de cerca')}]", "type = ChangeState",
                               f"value = {pick}"] + base + [
            "trigger1 = statetype = S", "trigger1 = ctrl", f"trigger1 = P2BodyDist X < {near}",
            f"trigger1 = Random < {chance * 3} * AILevel / 4"]) + "\n")
    th = cfg.get("throw") or {}
    if _frames(th) and th.get("state") is not None and not is_off(cfg, "throw"):
        out.append("\n".join([f"[State -1, SM: {tr('IA')}: {tr('Agarre')}]", "type = ChangeState",
                               f"value = {int(th['state'])}"] + base + [
            "trigger1 = statetype = S", "trigger1 = ctrl", f"trigger1 = P2BodyDist X < {round(12 * k)}",
            "trigger1 = P2StateType != A", "trigger1 = P2MoveType != H", f"trigger1 = Random < {chance} * AILevel / 4"])
                   + "\n")
    return out


def has_moves(cfg):
    return bool(any(_frames(e or {}) for e in cfg["normals"].values()) or _frames(cfg.get("throw") or {}) or
                any(_frames(s) for s in cfg.get("specials", [])) or any(cfg.get("voices", {}).values()) or
                any(x.get("snd") for x in cfg.get("combo_voices", [])))


# ---------------------------------------------------------------- frases de victoria ([Quotes] del .cns)
_QUOTES_SEC = re.compile(r"(?im)^[ \t]*\[\s*quotes\s*\][^\n]*\n(.*?)(?=^[ \t]*\[|\Z)", re.DOTALL)


def read_quotes(cns_text):
    """Las frases de victoria del .cns (sección [Quotes], el idioma de siempre), en orden."""
    m = _QUOTES_SEC.search(cns_text or "")
    if not m:
        return []
    out = []
    for ln in m.group(1).splitlines():
        q = re.match(r'\s*victory(\d+)\s*=\s*"?(.*?)"?\s*(;.*)?$', ln, re.IGNORECASE)
        if q and q.group(2).strip() and q.group(2).strip() not in ("...", "…"):
            out.append((int(q.group(1)), q.group(2).strip()))
    return [t for _n, t in sorted(out)]


def write_quotes(cns_text, quotes):
    """El .cns con su [Quotes] al día (hasta 100 frases). Sin frases, la sección se quita."""
    quotes = [q.replace('"', "'").strip() for q in quotes if q and q.strip()][:100]
    body = "".join(f'victory{i + 1} = "{q}"\n' for i, q in enumerate(quotes))
    sec = ("[Quotes]\n; " + "frases de victoria (EasyFighter)" + "\n" + body + "\n") if quotes else ""
    m = re.search(r"(?im)^[ \t]*\[\s*quotes\s*\][^\n]*\n.*?(?=^[ \t]*\[|\Z)", cns_text, re.DOTALL)
    if m:
        return cns_text[:m.start()] + sec + cns_text[m.end():]
    if not sec:
        return cns_text
    st = re.search(r"(?im)^[ \t]*\[\s*statedef\b", cns_text)
    pos = st.start() if st else len(cns_text)
    pre = cns_text[:pos]
    if pre and not pre.endswith("\n\n"):
        sec = ("\n" if pre.endswith("\n") else "\n\n") + sec
    return pre + sec + cns_text[pos:]


# ---------------------------------------------------------------- texto de los archivos
def block(begin, end, body, note):
    return f"{begin}\n; {note}\n{body.rstrip()}\n{end}\n"


def replace_block(text, begin, end, new_block, insert_at, before="", after=""):
    """Cambia el bloque marcado (o lo inserta en insert_at si no existe). Devuelve el texto nuevo."""
    pat = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"[^\n]*\n?", re.DOTALL)
    if pat.search(text):
        return pat.sub(lambda _m: new_block, text, count=1)
    pos = insert_at(text)
    return text[:pos] + before + new_block + after + text[pos:]


def cmd_text(text, gen, note):
    """El .cmd con los bloques del modo simple al día."""
    nl = "\n"
    cmds = block(CMD_BEGIN, CMD_END, nl.join(gen.commands), note)
    ents = block(ENT_BEGIN, ENT_END, nl.join(gen.entries), note)

    # quitar los bloques viejos primero para buscar bien dónde va cada uno
    def first_statedef(t):
        m = re.search(r"^[ \t]*\[\s*statedef\b", t, re.IGNORECASE | re.MULTILINE)
        return m.start() if m else len(t)

    text = replace_block(text, CMD_BEGIN, CMD_END, cmds, first_statedef, after=nl)

    def after_minus1(t):
        m = re.search(r"^[ \t]*\[\s*statedef\s+-1\s*\][^\n]*\n", t, re.IGNORECASE | re.MULTILINE)
        return m.end() if m else len(t)

    if not re.search(r"^[ \t]*\[\s*statedef\s+-1\s*\]", text, re.IGNORECASE | re.MULTILINE) and ENT_BEGIN not in text:
        text = text.rstrip("\n") + "\n\n[Statedef -1]\n"
    text = replace_block(text, ENT_BEGIN, ENT_END, ents, after_minus1, before=nl, after=nl)
    return text


def st_text(gen, header):
    return header + "\n\n" + "\n;---------------------------------------------------------------------------\n".join(
        gen.states) + "\n"
