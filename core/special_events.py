"""
Eventos de los especiales y súper del modo simple: cosas que pasan en un cuadro de la animación (moverse,
otro golpe, otro proyectil, un efecto, un sonido, sacudir la pantalla, seguir con otro especial…).

Cada evento es un diccionario: {"type": ..., "frame": cuadro (desde 1), "delay": ticks después, campos…}.
Los eventos que vienen de un personaje convertido traen "raw" (su código original): se escribe tal cual y
solo se le cambian los campos que el usuario tocó (así no se pierde nada de lo que tenía).
"""
import re

# (clave, nombre, ayuda, [(campo, etiqueta, tipo, mínimo, máximo, valor de fábrica, ayuda)])
# tipos: int / float / bool / ("choice", [(valor, etiqueta)]) / "anim" / "sound" / "special" / "button" / "code"
WHERE_POS = [("p1", "Desde el personaje"), ("p2", "Desde el rival"), ("front", "Desde el borde de la pantalla")]
TELEPORT = [("behind", "Detrás del rival"), ("front", "Delante del rival"), ("fwd", "Hacia adelante")]
FOLLOW_IF = [("hit", "Si el golpe conecta"), ("button", "Si aprietas un botón"), ("end", "Siempre, al terminar")]
MOVE_MODE = [("set", "Poner esa velocidad"), ("add", "Sumarle a la que lleva")]
TRANS_MODES = [("half", "Medio transparente"), ("add", "Brillante (como luz)"), ("invisible", "Invisible")]
HEIGHTS = [("high", "De pie o agachado"), ("low", "Solo agachado (bajo)"), ("overhead", "Solo de pie (desde arriba)"),
           ("unblockable", "No se puede cubrir")]

EVENTS = [
    ("move", "🏃", "Moverse / impulso", "Cambia la velocidad del personaje (avanzar, saltar, frenar).", [
        ("mode", "Cómo", ("choice", MOVE_MODE), 0, 0, "set", ""),
        ("x", "Hacia adelante", float, -60, 60, 4.0, "Negativo = hacia atrás."),
        ("y", "Hacia arriba", float, -60, 60, 0.0, "Positivo = sube. 0 = no cambia la altura."),
        ("air", "Sale volando (pasa a estar en el aire)", bool, 0, 1, False,
         "Despega del suelo en ese cuadro: sube, cae y aterriza solo (como un gancho volador)."),
        ("speed", "Rapidez (%)", int, 25, 400, 100,
         "100 = normal. Más = sube y baja más rápido; menos = más lento, como flotando. Si sale volando, la "
         "altura y la distancia no cambian."),
        ("by_version", "Cambia con la versión (débil más corto, fuerte más largo)", bool, 0, 1, False, ""),
    ]),
    ("posadd", "↔", "Moverse de golpe", "Lo corre de lugar en ese momento (sin velocidad): un pasito, un brinco.", [
        ("x", "Hacia adelante", float, -300, 300, 10.0, "Negativo = hacia atrás."),
        ("y", "Hacia arriba", float, -300, 300, 0.0, "Positivo = sube."),
    ]),
    ("teleport", "✨", "Teletransporte", "Aparece de golpe junto al rival o más adelante.", [
        ("where", "A dónde", ("choice", TELEPORT), 0, 0, "behind", ""),
        ("dist", "Distancia", float, 0, 300, 30.0, "Qué tan lejos del rival (o cuánto avanza)."),
    ]),
    ("turn", "🔄", "Voltearse", "Se voltea hacia el otro lado.", []),
    ("freeze", "🧊", "Quedarse quieto", "No se mueve (ni cae) durante un rato: para flotar en el aire.", [
        ("ticks", "Cuánto (ticks)", int, 1, 600, 20, "60 ticks = 1 segundo."),
    ]),
    ("hit", "👊", "Otro golpe", "Un golpe más en ese cuadro (con su propio daño).", [
        ("damage", "Daño", int, 0, 9999, 40, ""),
        ("hits", "Golpes", int, 1, 30, 1, "Cuántas veces pega desde ese cuadro."),
        ("gap", "Ticks entre golpes", int, 1, 60, 5, ""),
        ("pause", "Pausa al pegar", int, 0, 60, 10, "Cuánto se congelan los dos al pegar."),
        ("push", "Empuje", float, 0, 30, 4.0, ""),
        ("launch", "Lo tumba / lo lanza", bool, 0, 1, False, ""),
        ("height", "Cómo se cubre", ("choice", HEIGHTS), 0, 0, "high", ""),
    ]),
    ("proj", "🔥", "Otro proyectil", "Lanza un proyectil más (con su animación, velocidad y daño).", [
        ("anim", "Animación", "anim", 0, 0, None, ""),
        ("anim_hit", "Al chocar (opcional)", "anim", 0, 0, None, ""),
        ("damage", "Daño", int, 0, 9999, 40, ""),
        ("vx", "Velocidad adelante", float, -40, 40, 5.0, ""),
        ("vy", "Velocidad arriba", float, -40, 40, 0.0, "Positivo = sube."),
        ("ax", "Aceleración adelante", float, -5, 5, 0.0, "Va más rápido (o más lento) con el tiempo."),
        ("ay", "Aceleración arriba", float, -5, 5, 0.0, "Negativo = cae como una piedra."),
        ("x", "Sale adelante", int, -500, 500, 40, ""),
        ("y", "Sale a la altura", int, -500, 500, -60, "Negativo = más arriba."),
        ("hits", "Golpes", int, 1, 30, 1, ""),
        ("gap", "Ticks entre golpes", int, 1, 60, 6, ""),
        ("life", "Desaparece tras (ticks)", int, 0, 999, 0, "0 = sigue hasta salir de la pantalla."),
        ("height", "Cómo se cubre", ("choice", HEIGHTS), 0, 0, "high", ""),
        ("launch", "Lo tumba / lo lanza", bool, 0, 1, False, ""),
    ]),
    ("effect", "💥", "Efecto", "Una animación aparte (fuego, chispas, aura…) que no pega.", [
        ("anim", "Animación", "anim", 0, 0, None, ""),
        ("pos", "Dónde", ("choice", WHERE_POS), 0, 0, "p1", ""),
        ("x", "Adelante", int, -800, 800, 0, ""),
        ("y", "Altura", int, -800, 800, 0, "Negativo = más arriba."),
        ("follow", "Sigue al personaje", bool, 0, 1, True, ""),
        ("ontop", "Por delante del personaje", bool, 0, 1, True, ""),
        ("time", "Dura (ticks)", int, -2, 999, -2, "-2 = hasta que termine su animación."),
        ("scale", "Tamaño", float, 0.1, 10, 1.0, ""),
        ("remove_hit", "Se quita si le pegan", bool, 0, 1, True, ""),
    ]),
    ("sound", "🔊", "Sonido", "Suena un sonido del personaje.", [
        ("snd", "Sonido", "sound", 0, 0, None, ""),
    ]),
    ("invuln", "🛡", "Invencible", "No le pueden pegar durante un rato.", [
        ("ticks", "Cuánto (ticks)", int, 1, 600, 10, ""),
    ]),
    ("counter", "🔁", "Contraataque", "Si el rival le pega en este momento, lo atrapa y le devuelve el golpe.", [
        ("ticks", "Ventana (ticks)", int, 1, 120, 12, "Cuánto tiempo puede atrapar el golpe."),
        ("damage", "Daño", int, 0, 9999, 60, ""),
        ("launch", "Lo tumba / lo lanza", bool, 0, 1, True, ""),
    ]),
    ("shake", "📳", "Sacudir la pantalla", "", [
        ("ticks", "Cuánto (ticks)", int, 1, 300, 15, ""),
        ("ampl", "Fuerza", int, 1, 30, 4, ""),
    ]),
    ("flash", "🌈", "Destello de color", "El personaje brilla de un color.", [
        ("ticks", "Cuánto (ticks)", int, 1, 300, 12, ""),
        ("r", "Rojo", int, -255, 255, 120, ""),
        ("g", "Verde", int, -255, 255, 120, ""),
        ("b", "Azul", int, -255, 255, 120, ""),
    ]),
    ("afterimage", "👥", "Estela", "Deja copias transparentes detrás (como al moverse muy rápido).", [
        ("ticks", "Cuánto (ticks)", int, 1, 300, 30, ""),
    ]),
    ("superpause", "⏸", "Pausa con destello", "Todo se congela un momento (como al empezar un súper).", [
        ("ticks", "Cuánto (ticks)", int, 1, 180, 20, ""),
        ("darken", "Oscurecer la pantalla", bool, 0, 1, True, ""),
        ("hold", "El personaje se queda quieto en ese cuadro durante la pausa", bool, 0, 1, True,
         "Como en los súper de los juegos: el personaje se queda en un sprite mientras pasa el destello y después "
         "sigue. Sin marcar, su animación sigue corriendo durante la pausa."),
        ("spark", "Con destello (la chispa de luz)", bool, 0, 1, True,
         "La chispa que sale en el personaje al empezar la pausa. Desmárcalo para que solo se congele todo."),
    ]),
    ("selfpause", "⏯", "Pausa del personaje", "Solo el personaje se congela un momento: el rival, los proyectiles y "
     "todo lo demás siguen moviéndose (como la pausa al pegar, pero solo él).", [
        ("ticks", "Cuánto (ticks)", int, 1, 180, 12, "60 ticks = 1 segundo."),
        ("flash", "Con destello (brilla mientras está en pausa)", bool, 0, 1, True,
         "Desmárcalo para que solo se congele, sin brillar."),
    ]),
    ("screencolor", "🎆", "Color en la pantalla", "Toda la pantalla se pinta de un color un momento (un fogonazo).", [
        ("ticks", "Cuánto (ticks)", int, 1, 120, 6, ""),
        ("r", "Rojo", int, 0, 255, 255, ""),
        ("g", "Verde", int, 0, 255, 255, ""),
        ("b", "Azul", int, 0, 255, 255, ""),
        ("under", "Por detrás de los personajes", bool, 0, 1, False,
         "Marcado: se pinta solo el fondo y los personajes se siguen viendo encima."),
    ]),
    ("trans", "👻", "Transparente / invisible", "El personaje se ve transparente, brillante como luz o desaparece "
     "un rato (bueno para teletransportes y fantasmas).", [
        ("mode", "Cómo", ("choice", TRANS_MODES), 0, 0, "half", ""),
        ("ticks", "Cuánto (ticks)", int, 1, 600, 20, ""),
    ]),
    ("power", "⚡", "Poder", "Le da (o le quita) barra de súper. 1000 = 1 barra.", [
        ("amount", "Cuánto", int, -9000, 9000, 100, ""),
    ]),
    ("life", "❤", "Vida", "Le da (o le quita) vida.", [
        ("amount", "Cuánto", int, -9999, 9999, 50, ""),
    ]),
    ("followup", "➡", "Seguir con otro especial", "Pasa a otro especial (para hacer combos o cadenas).", [
        ("target", "Especial", "special", 0, 0, None, ""),
        ("cond", "Cuándo", ("choice", FOLLOW_IF), 0, 0, "hit", ""),
        ("button", "Botón", "button", 0, 0, "x", "Solo si es «Si aprietas un botón»."),
    ]),
    ("custom", "🧩", "Código propio", "Código de IKEMEN escrito a mano (para lo que no está en la lista).", [
        ("code", "Código", "code", 0, 0, "", "Usa {st} donde va el número del estado."),
    ]),
]
EVENT = {e[0]: e for e in EVENTS}
FIELDS = {e[0]: {f[0]: f for f in e[4]} for e in EVENTS}

# en los eventos que vienen del código original, qué campo cambia qué parámetro: campo → (parámetro, posición)
PATCH = {
    "hit": {"damage": ("damage", 0), "pause": ("pausetime", None)},
    "proj": {"damage": ("damage", 0), "vx": ("velocity", 0), "vy": ("velocity", 1), "x": ("offset", 0),
             "y": ("offset", 1)},
    "move": {"x": ("x", None), "y": ("y", None)},
    "posadd": {"x": ("x", None), "y": ("y", None)},
    "sound": {"snd": ("value", None)},
    "invuln": {"ticks": ("time", None)},
    "shake": {"ticks": ("time", None), "ampl": ("ampl", None)},
    "flash": {"ticks": ("time", None)},
    "afterimage": {"ticks": ("time", None)},
    "superpause": {"ticks": ("time", None)},
    "power": {"amount": ("value", None)},
    "life": {"amount": ("value", None)},
    "freeze": {},
    "effect": {"x": ("pos", 0), "y": ("pos", 1)},
}
# tipo de controlador → tipo de evento (al convertir)
SCTRL_EVENT = {"hitdef": "hit", "projectile": "proj", "velset": "move", "veladd": "move", "playsnd": "sound",
               "nothitby": "invuln", "envshake": "shake", "palfx": "flash", "afterimage": "afterimage",
               "superpause": "superpause", "poweradd": "power", "lifeadd": "life", "posfreeze": "freeze",
               "turn": "turn", "explod": "effect", "reversaldef": "counter",
               "posadd": "posadd", "envcolor": "screencolor"}


def default(ev_type, field):
    f = FIELDS.get(ev_type, {}).get(field)
    return f[5] if f else None


def val(ev, field):
    v = ev.get(field)
    return default(ev.get("type"), field) if v is None else v


def _fmt(v):
    if isinstance(v, float):
        return f"{round(v, 3):g}"
    return str(v)


def summary(ev, tr=lambda s: s):
    """Texto corto de un evento para la lista."""
    e = EVENT.get(ev.get("type"))
    if e is None:
        return "?"
    when = tr('cuadro {0}').format(ev["frame"]) if ev.get("frame") else tr('con su condición')
    if ev.get("delay"):
        when += f" +{ev['delay']}t"
    bits = []
    t = ev.get("type")
    if t in ("hit", "proj", "counter"):
        bits.append(tr('daño {0}').format(val(ev, "damage")))
    if t in ("move", "posadd"):
        bits.append(f"→{_fmt(val(ev, 'x'))} ↑{_fmt(val(ev, 'y'))}")
        if ev.get("air"):
            bits.append(tr('sale volando'))
        if int(val(ev, "speed") or 100) != 100 and t == "move":
            bits.append(f"{val(ev, 'speed')}%")
    if t in ("invuln", "freeze", "shake", "flash", "afterimage", "superpause", "counter", "selfpause",
             "screencolor", "trans"):
        bits.append(tr('{0} ticks').format(val(ev, "ticks")))
    if t in ("power", "life"):
        bits.append(f"{val(ev, 'amount'):+d}")
    if ev.get("raw"):
        bits.append(tr('del personaje'))
    if ev.get("tpl"):
        bits.append(tr('del tipo'))
    name = tr('Proyectil') if ev.get("main") else tr(e[2])
    return f"{e[1]} {name} · {when}" + (" · " + ", ".join(bits) if bits else "")


# ---------------------------------------------------------------- código
def _trigger(ev):
    f = ev.get("frame")
    if f and ev.get("_nframes"):
        f = min(int(f), int(ev["_nframes"]))
    d = int(ev.get("delay") or 0)
    if not f:
        return ["trigger1 = Time = 0"]
    if d:
        return [f"trigger1 = AnimElemTime({int(f)}) = {d}"]
    return [f"trigger1 = AnimElem = {int(f)}"]


def hitdef_lines(dmg, strength, pause, push, launch, height, k, proj=False, guard_pct=12, air=False):
    animtype = ["Light", "Medium", "Heavy"][max(0, min(2, strength))]
    gdmg = int(round(dmg * guard_pct / 100.0))
    guardflag = {"high": "MA", "low": "L", "overhead": "HA", "unblockable": None}.get(height, "MA")
    gtype = "Low" if height == "low" else "High"
    attr = "S, SP" if proj else "S, SA"
    h = [f"attr = {attr}", f"damage = {int(dmg)}, {gdmg}", f"animtype = {animtype}"]
    if guardflag:
        h.append(f"guardflag = {guardflag}")
    h += ["hitflag = MAF", f"priority = {4 if proj else 5}, Hit", f"pausetime = {pause}, {pause}",
          f"sparkno = {strength}", "guard.sparkno = 40", f"hitsound = 5, {strength}", "guardsound = 6, 0",
          f"ground.type = {gtype}", f"ground.slidetime = {pause}", f"ground.hittime = {pause + 4}"]
    p = push * k
    if launch:
        h += [f"ground.velocity = {_fmt(round(-p * 0.8, 2))}, {_fmt(round(-6.5 * k, 2))}",
              f"air.velocity = {_fmt(round(-p * 0.7, 2))}, {_fmt(round(-6 * k, 2))}",
              "fall = 1", "air.fall = 1", "fall.recover = 1"]
    else:
        h += [f"ground.velocity = {_fmt(round(-p, 2))}",
              f"air.velocity = {_fmt(round(-p * 0.6, 2))}, {_fmt(round(-3 * k, 2))}"]
    return h


def patch_raw(raw, ev):
    """El código original del evento con los campos que el usuario cambió."""
    out = raw
    t = ev.get("type")
    for field in ev.get("edited", []):
        if field == "frame":
            out = re.sub(r"(?im)^(\s*trigger\w*\s*=\s*AnimElem\s*=\s*)\d+", lambda m: m.group(1) + str(ev["frame"]),
                         out, count=1)
            continue
        spec = PATCH.get(t, {}).get(field)
        if spec is None:
            continue
        param, pos = spec
        v = ev.get(field)
        if isinstance(v, (list, tuple)):
            v = ", ".join(str(x) for x in v)
        elif isinstance(v, float):
            v = _fmt(v)
        m = re.search(r"(?im)^(\s*%s\s*=\s*)([^;\n]*)" % re.escape(param), out)
        if m is None:
            out = out.rstrip("\n") + f"\n{param} = {v}\n"
            continue
        parts = [x.strip() for x in m.group(2).split(",")]
        if pos is None:
            if param == "pausetime":
                parts = [str(v), str(v)]
            else:
                parts = [str(v)]
        else:
            while len(parts) <= pos:
                parts.append("0")
            parts[pos] = str(v)
        out = out[:m.start(2)] + ", ".join(parts) + " " + out[m.end(2):].lstrip(" ")
    return out


def event_code(ev, ctx):
    """Líneas de código de un evento. ctx: st, k, scale, label, anim_of(ev, campo), state_of(ref),
    button_cmd(b), strength, tr."""
    st = ctx["st"]
    tr = ctx.get("tr", lambda s: s)
    t = ev.get("type")
    if ev.get("raw"):
        return [patch_raw(ev["raw"], ev).rstrip("\n"), ""]
    k = ctx["k"]
    e = EVENT.get(t)
    if e is None:
        return []
    head = [f"[State {st}, {tr(e[2])}]"]
    trig = _trigger(ev)
    if t == "move":
        s = max(0.25, float(val(ev, "speed")) / 100.0)
        vx = vy = 1.0
        if val(ev, "by_version"):
            vv = ctx.get("vv", 1)
            vx = [0.75, 1.0, 1.25, 1.15][vv]
            vy = 0.85 + 0.15 * min(vv, 2)
        x = float(val(ev, "x")) * k * vx * s
        y = -float(val(ev, "y")) * k * vy * s
        typ = "VelSet" if val(ev, "mode") == "set" else "VelAdd"
        out = []
        if val(ev, "air"):
            out += [f"[State {st}, {tr('Despegar')}]", "type = StateTypeSet"] + trig + ["statetype = A",
                                                                                        "physics = A", ""]
        lines = [f"type = {typ}"] + trig + [f"x = {_fmt(round(x, 3))}"]
        if float(val(ev, "y")) != 0 or typ == "VelAdd" or val(ev, "air"):
            lines.append(f"y = {_fmt(round(y, 3))}")
        out += head + lines + [""]
        if val(ev, "air") and abs(s - 1.0) > 0.001:
            f = int(ev.get("frame") or 1)
            out += [f"[State {st}, {tr('Rapidez de la subida')}]", "type = VelAdd", "trigger1 = statetype = A",
                    f"trigger1 = AnimElemTime({f}) > 0", f"y = const(movement.yaccel) * {_fmt(round(s * s - 1, 4))}",
                    ""]
        return out
    if t == "posadd":
        x = float(val(ev, "x")) * k
        y = -float(val(ev, "y")) * k
        lines = ["type = PosAdd"] + trig + [f"x = {_fmt(round(x, 3))}"]
        if y:
            lines.append(f"y = {_fmt(round(y, 3))}")
        return head + lines + [""]
    if t == "teleport":
        d = float(val(ev, "dist")) * k
        w = val(ev, "where")
        if w == "fwd":
            x = f"{_fmt(round(d, 2))}"
        elif w == "front":
            x = f"P2Dist X - {_fmt(round(d, 2))}"
        else:
            x = f"P2Dist X + {_fmt(round(d, 2))}"
        out = head + ["type = PosAdd"] + trig + [f"x = {x}", ""]
        if w == "behind":
            out += [f"[State {st}, {tr('Voltearse')}]", "type = Turn"] + trig + [""]
        return out
    if t == "turn":
        return head + ["type = Turn"] + trig + [""]
    if t == "freeze":
        f = int(ev.get("frame") or 1)
        n = int(val(ev, "ticks"))
        return head + ["type = PosFreeze", f"trigger1 = AnimElemTime({f}) >= 0", f"trigger1 = AnimElemTime({f}) < {n}",
                       "value = 1", "", f"[State {st}, {tr('Quieto (velocidad)')}]", "type = VelSet",
                       f"trigger1 = AnimElemTime({f}) >= 0", f"trigger1 = AnimElemTime({f}) < {n}", "y = 0", ""]
    if t == "hit":
        hits = max(1, int(val(ev, "hits")))
        gap = max(1, int(val(ev, "gap")))
        dmg = max(0, int(round(int(val(ev, "damage")) / hits)))
        hd = hitdef_lines(dmg, ctx.get("strength", 1), int(val(ev, "pause")), float(val(ev, "push")),
                          bool(val(ev, "launch")), val(ev, "height"), k)
        f = int(ev.get("frame") or 1)
        d = int(ev.get("delay") or 0)
        t0 = f"AnimElemTime({f})"
        if hits > 1:
            trig = [f"trigger1 = {t0} >= {d}", f"trigger1 = (({t0} - {d}) % {gap}) = 0",
                    f"trigger1 = {t0} < {d + hits * gap}"]
        return head + ["type = HitDef"] + trig + hd + [""]
    if t == "proj":
        an = ctx["anim_of"](ev, "anim")
        if an is None:
            return []
        hn = ctx["anim_of"](ev, "anim_hit")
        sc = ctx.get("scale", 1.0)
        hits = max(1, int(val(ev, "hits")))
        dmg = max(0, int(round(int(val(ev, "damage")) / hits)))
        life = int(val(ev, "life"))
        lines = ["type = Projectile"] + trig + [
            f"projid = {ctx['projid']}", f"projanim = {an}", "projremove = 1", f"projhits = {hits}",
            f"projmisstime = {max(1, int(val(ev, 'gap')))}",
            f"velocity = {_fmt(round(float(val(ev, 'vx')) * k, 3))}, {_fmt(round(-float(val(ev, 'vy')) * k, 3))}",
            f"accel = {_fmt(round(float(val(ev, 'ax')) * k, 3))}, {_fmt(round(-float(val(ev, 'ay')) * k, 3))}",
            f"offset = {round(int(val(ev, 'x')) * k * sc)}, {round(int(val(ev, 'y')) * k * sc)}",
            "projpriority = 1", "projsprpriority = 3", f"projremovetime = {life if life > 0 else -1}",
            "projscale = ifelse(const(size.proj.doscale), 1, const(size.xscale)), "
            "ifelse(const(size.proj.doscale), 1, const(size.yscale))"]
        if hn is not None:
            lines += [f"projhitanim = {hn}", f"projremanim = {hn}"]
        lines += hitdef_lines(dmg, ctx.get("strength", 1), 10, 4.0, bool(val(ev, "launch")), val(ev, "height"), k,
                              proj=True)
        return head + lines + [""]
    if t == "effect":
        an = ctx["anim_of"](ev, "anim")
        if an is None:
            return []
        sc = float(val(ev, "scale")) * ctx.get("scale", 1.0)
        pos = val(ev, "pos")
        lines = ["type = Explod"] + trig + [
            f"anim = {an}", f"pos = {round(int(val(ev, 'x')) * k)}, {round(int(val(ev, 'y')) * k)}",
            f"postype = {pos}", "facing = 1", f"bindtime = {-1 if val(ev, 'follow') and pos == 'p1' else 1}",
            f"removetime = {int(val(ev, 'time'))}", f"scale = {_fmt(round(sc, 3))}, {_fmt(round(sc, 3))}",
            f"sprpriority = {4 if val(ev, 'ontop') else -1}", "ownpal = 1",
            f"removeongethit = {1 if val(ev, 'remove_hit') else 0}"]
        return head + lines + [""]
    if t == "sound":
        snd = ev.get("snd")
        if not snd:
            return []
        return head + ["type = PlaySnd"] + trig + [f"value = {int(snd[0])}, {int(snd[1])}", "channel = -1", ""]
    if t == "invuln":
        return head + ["type = NotHitBy"] + trig + ["value = SCA", f"time = {int(val(ev, 'ticks'))}", ""]
    if t == "counter":
        f = int(ev.get("frame") or 1)
        n = int(val(ev, "ticks"))
        hd = hitdef_lines(int(val(ev, "damage")), 2, 14, 5.0, bool(val(ev, "launch")), "unblockable", k)
        hd = [x for x in hd if not x.startswith(("attr", "guardflag", "hitflag", "priority"))]
        return head + ["type = ReversalDef", f"trigger1 = AnimElemTime({f}) = 0", "reversal.attr = SCA, AA"] + hd + [
            "", f"[State {st}, {tr('Fin del contraataque')}]", "type = ReversalDef",
            f"trigger1 = AnimElemTime({f}) = {n}", "reversal.attr =", ""]
    if t == "shake":
        return head + ["type = EnvShake"] + trig + [f"time = {int(val(ev, 'ticks'))}",
                                                    f"ampl = {int(val(ev, 'ampl'))}", "freq = 60", ""]
    if t == "flash":
        return head + ["type = PalFX"] + trig + [f"time = {int(val(ev, 'ticks'))}",
                                                 f"add = {int(val(ev, 'r'))}, {int(val(ev, 'g'))}, {int(val(ev, 'b'))}",
                                                 "mul = 256, 256, 256", "sinadd = 0, 0, 0, 0", ""]
    if t == "afterimage":
        return head + ["type = AfterImage"] + trig + [f"time = {int(val(ev, 'ticks'))}", "length = 14",
                                                      "palbright = 30, 30, 30", "palcontrast = 120, 120, 220",
                                                      "trans = add", ""]
    if t == "superpause":
        n = int(val(ev, "ticks"))
        # movetime = 0: el personaje también se congela (se queda en ese cuadro) y después sigue
        mt = 0 if val(ev, "hold") else n
        return head + ["type = SuperPause"] + trig + [f"time = {n}", f"movetime = {mt}",
                                                      f"darken = {1 if val(ev, 'darken') else 0}"] + (
            [] if val(ev, "spark") else ["anim = -1"]) + [""]
    if t == "selfpause":
        n = int(val(ev, "ticks"))
        # solo él: su propia «pausa al pegar» (el resto del juego sigue)
        out = []
        if val(ev, "flash"):
            out += [f"[State {st}, {tr('Brillo de la pausa')}]", "type = PalFX"] + trig + [
                f"time = {n}", "add = 110, 110, 110", "mul = 256, 256, 256", "persistent = 0", ""]
        # persistent = 0: durante la pausa la animación no avanza, así que sin esto se volvería a pausar sin fin
        return out + head + ["type = ModifyPlayer"] + trig + [f"hitpausetime = {n}", "persistent = 0", ""]
    if t == "screencolor":
        return head + ["type = EnvColor"] + trig + [
            f"value = {int(val(ev, 'r'))}, {int(val(ev, 'g'))}, {int(val(ev, 'b'))}", f"time = {int(val(ev, 'ticks'))}",
            f"under = {1 if val(ev, 'under') else 0}", ""]
    if t == "trans":
        f = int(ev.get("frame") or 1)
        d = int(ev.get("delay") or 0)
        n = int(val(ev, "ticks"))
        rng = [f"trigger1 = AnimElemTime({f}) >= {d}", f"trigger1 = AnimElemTime({f}) < {d + n}"]
        mode = val(ev, "mode")
        if mode == "invisible":
            return head + ["type = AssertSpecial"] + rng + ["flag = invisible", ""]
        if mode == "add":
            return head + ["type = Trans"] + rng + ["trans = add", "alpha = 256, 256", ""]
        return head + ["type = Trans"] + rng + ["trans = addalpha", "alpha = 128, 128", ""]
    if t == "power":
        return head + ["type = PowerAdd"] + trig + [f"value = {int(val(ev, 'amount'))}", ""]
    if t == "life":
        return head + ["type = LifeAdd"] + trig + [f"value = {int(val(ev, 'amount'))}", "kill = 0", ""]
    if t == "followup":
        target = ctx["state_of"](ev.get("target"))
        if target is None:
            return []
        f = int(ev.get("frame") or 1)
        cond = val(ev, "cond")
        if cond == "hit":
            tr_ = [f"trigger1 = AnimElemTime({f}) >= 0", "trigger1 = MoveHit"]
        elif cond == "button":
            tr_ = [f"trigger1 = AnimElemTime({f}) >= 0", f'trigger1 = command = "{ctx["button_cmd"](val(ev, "button"))}"']
        else:
            tr_ = ["trigger1 = AnimTime = 0"]
        return head + ["type = ChangeState"] + tr_ + [f"value = {target}", ""]
    if t == "custom":
        code = str(ev.get("code") or "").replace("{st}", str(st)).strip()
        if not code:
            return []
        if not code.lstrip().startswith("["):
            code = f"[State {st}, {tr('Código propio')}]\n" + code
        return [code, ""]
    return []


def event_anim_fields(ev):
    """Campos de animación del evento que hay que convertir en acciones del .air."""
    return [f[0] for f in EVENT.get(ev.get("type"), (None,) * 5)[4] if f[2] == "anim"] if ev.get("type") in EVENT else []


# ---------------------------------------------------------------- convertir el código de un personaje
def _blocks(text):
    out, cur = [], None
    for raw in text.splitlines():
        if raw.strip().startswith("["):
            cur = [raw]
            out.append(cur)
        elif cur is not None:
            cur.append(raw)
    return out


def _kv(lines):
    d = {}
    for ln in lines:
        c = ln.split(";", 1)[0].strip()
        if "=" in c:
            a, b = c.split("=", 1)
            d.setdefault(a.strip().lower(), b.strip())
    return d


def _num(v, i=0, default=0.0):
    try:
        return float(str(v).split(",")[i].strip())
    except (ValueError, IndexError, AttributeError):
        return default


def statedef_text(text, state):
    """El texto completo de un [Statedef n] (cabecera y sus controladores) o None."""
    m = re.search(r"^[ \t]*\[\s*statedef\s+%d\s*[\],][^\n]*\n?" % state, text, re.I | re.M)
    if not m:
        return None
    n = re.search(r"^[ \t]*\[\s*statedef\b", text[m.end():], re.I | re.M)
    end = m.end() + n.start() if n else len(text)
    return text[m.start():end]


def convert_state(sd_text, k):
    """De un [Statedef] a (cabecera, eventos). Los controladores conocidos quedan como eventos editables (con
    su código original guardado) y los demás como «Código propio»."""
    blocks = _blocks(sd_text)
    head = "\n".join(blocks[0]).rstrip("\n") if blocks else ""
    events = []
    for blk in blocks[1:]:
        raw = "\n".join(blk).rstrip()
        kv = _kv(blk[1:])
        t = kv.get("type", "").lower()
        typ = SCTRL_EVENT.get(t, "custom")
        ev = {"type": typ, "raw": raw + "\n"}
        trig = [ln.split(";", 1)[0].strip().lower() for ln in blk[1:]
                if ln.split(";", 1)[0].strip().lower().startswith("trigger")]
        m = re.fullmatch(r"trigger1\s*=\s*animelem\s*=\s*(\d+)", trig[0]) if len(trig) == 1 else None
        if m:
            ev["frame"] = int(m.group(1))
        kk = k or 1.0
        if typ == "hit":
            ev["damage"] = int(_num(kv.get("damage"), 0, 0))
            ev["pause"] = int(_num(kv.get("pausetime"), 0, 10))
        elif typ == "proj":
            ev["damage"] = int(_num(kv.get("damage"), 0, 0))
            ev["vx"] = round(_num(kv.get("velocity"), 0, 0) / kk, 3)
            ev["vy"] = round(-_num(kv.get("velocity"), 1, 0) / kk, 3)
            ev["x"] = int(_num(kv.get("offset"), 0, 0))
            ev["y"] = int(_num(kv.get("offset"), 1, 0))
        elif typ == "posadd":
            ev["x"] = round(_num(kv.get("x"), 0, 0) / kk, 3)
            ev["y"] = round(-_num(kv.get("y"), 0, 0) / kk, 3)
        elif typ == "move":
            ev["mode"] = "set" if t == "velset" else "add"
            ev["x"] = round(_num(kv.get("x"), 0, 0) / kk, 3)
            ev["y"] = round(-_num(kv.get("y"), 0, 0) / kk, 3)
        elif typ == "sound":
            v = kv.get("value", "")
            ev["snd"] = [x.strip() for x in v.split(",")][:2]
        elif typ in ("invuln", "shake", "flash", "afterimage", "superpause"):
            ev["ticks"] = int(_num(kv.get("time"), 0, 1))
            if typ == "shake":
                ev["ampl"] = int(_num(kv.get("ampl"), 0, 4))
        elif typ in ("power", "life"):
            ev["amount"] = int(_num(kv.get("value"), 0, 0))
        elif typ == "effect":
            ev["x"] = int(_num(kv.get("pos"), 0, 0))
            ev["y"] = int(_num(kv.get("pos"), 1, 0))
        elif typ == "custom":
            ev["code"] = raw
        events.append(ev)
    return head, events


def rename_statedef(text, state, new):
    """[Statedef state…] → [Statedef new] ; SIMPLE-MODE era: …  (para guardar el original sin que choque)."""
    pat = re.compile(r"^([ \t]*)(\[\s*statedef\s+%d\s*[\],][^\n]*)$" % state, re.I | re.M)
    m = pat.search(text)
    if not m:
        return None
    line = m.group(2).replace(";", ",")
    return text[:m.start()] + f"{m.group(1)}[Statedef {new}] ; SIMPLE-MODE era: {line}" + text[m.end():]


def restore_statedef(text, new):
    pat = re.compile(r"^([ \t]*)\[Statedef %d\] ; SIMPLE-MODE era: ([^\n]*)$" % new, re.M)
    m = pat.search(text)
    if not m:
        return None
    return text[:m.start()] + m.group(1) + m.group(2) + text[m.end():]


def entry_text(cmd_text, state):
    """Los bloques [State -1] del .cmd que llevan a `state` (con sus condiciones originales)."""
    out = []
    for blk in _blocks(cmd_text):
        if not re.match(r"\s*\[\s*state\s+-1\b", blk[0], re.I):
            continue
        kv = _kv(blk[1:])
        if kv.get("type", "").lower() != "changestate":
            continue
        try:
            v = int(kv.get("value", "").split(",")[0])
        except ValueError:
            continue
        if v == state:
            out.append("\n".join(ln for ln in blk if ln.strip() != "triggerall = 0 ; SIMPLE-MODE: off").rstrip())
    return out


def retarget_entries(cmd_text, state, old, new):
    """En las entradas [State -1] que llevan a `state`, cambia command = "old" por command = "new" (en su lugar,
    sin moverlas: el orden de las entradas importa para los combos)."""
    out, changed = [], False
    parts = re.split(r"(?m)^(?=[ \t]*\[)", cmd_text)
    for blk in parts:
        if re.match(r"\s*\[\s*state\s+-1\b", blk, re.I):
            m = re.search(r"(?im)^\s*type\s*=\s*changestate\b", blk)
            v = re.search(r"(?im)^\s*value\s*=\s*(\d+)", blk)
            if m and v and int(v.group(1)) == int(state):
                b2 = re.sub(r'(?i)(command\s*=\s*)"%s"' % re.escape(old), lambda mm: mm.group(1) + f'"{new}"', blk)
                changed |= b2 != blk
                blk = b2
        out.append(blk)
    return "".join(out) if changed else None


def exact_command_name(cmd_text, state, name):
    """El nombre del comando tal como está escrito en la entrada (con sus mayúsculas)."""
    for blk in re.split(r"(?m)^(?=[ \t]*\[)", cmd_text):
        if re.match(r"\s*\[\s*state\s+-1\b", blk, re.I):
            v = re.search(r"(?im)^\s*value\s*=\s*(\d+)", blk)
            if v and int(v.group(1)) == int(state):
                m = re.search(r'(?i)command\s*=\s*"(%s)"' % re.escape(name), blk)
                if m:
                    return m.group(1)
    return name
