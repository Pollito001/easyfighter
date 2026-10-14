"""Sistema de combos del modo simple: estilos al estilo de los juegos de peleas más conocidos.

cfg["combos"] guarda las opciones. Si no existe, el modo simple se porta como siempre
(cadena débil→medio→fuerte de pie, del mismo tipo, y los especiales cancelan cualquier golpe).
"""
import copy
import uuid

# cómo se encadenan los golpes normales
CHAINS = [
    ("none", 'Sin cadenas (solo «links» y cancelar en especiales)'),
    ("same", 'Puño→puño y patada→patada, de débil a fuerte'),
    ("stronger", 'Cualquier botón más fuerte (débil → medio → fuerte)'),
    ("gatling", 'Gatling: más fuerte, o de puño a patada de la misma fuerza'),
]

# saltar para seguir el combo (cancelar en salto) después de pegar
JUMPS = [
    ("none", 'No'),
    ("launcher", 'Solo después del lanzador'),
    ("all", 'Después de cualquier golpe normal en el suelo'),
]

# regla de botones del autodoble
AD_RULES = [
    ("free", 'Libre (KI 2013): cualquier botón después del especial'),
    ("classic", 'Clásica (KI 1994): fuerte → medio, medio → débil, débil → fuerte'),
]

# cómo se rompe un combo
BREAKER_MODES = [
    ("buttons", 'Con los botones que escojas'),
    ("strength", 'Killer Instinct: puño + patada de la misma fuerza del golpe que te acaba de pegar'),
    ("ki2", 'Killer Instinct 2: un botón de la misma fuerza — puño si el golpe fue alto, patada si fue bajo'),
]

# botones que se aprietan juntos (combo breaker, cancelar con energía)
PRESS = ["x+a", "y+b", "z+c", "x+y", "a+b", "x+y+z", "a+b+c"]

DEFAULTS = {
    "style": "basic",
    "chain": "same", "chain_mix": False, "repeat_light": False, "air_chain": False,
    "cancel_from": [0, 1, 2],
    "launcher": "", "jump_cancel": "none",
    "autodouble": False, "ad_list": None, "ad_limit": 0, "ad_max": 0, "ad_air_open": False,
    "ad_rule": "free", "enders": False, "ender_bonus": 30,
    "breaker": False, "breaker_btn": "x+a", "breaker_hits": 3, "breaker_cost": 0,
    "breaker_mode": "buttons", "breaker_lockout": 180,
    "rc": False, "rc_btn": "z+c", "rc_cost": 500,
    "scaling": False, "scale_free": 3, "scale_step": 10, "scale_min": 30,
    "extra_stun": 0,
}

# estilos: (clave, nombre, explicación, cambios sobre DEFAULTS)
STYLES = [
    ("basic", 'Básico',
     'Lo de siempre: de pie y agachado encadenas débil → medio → fuerte del mismo tipo, y cualquier golpe '
     'se cancela en un especial.', {}),
    ("sf", 'Street Fighter',
     'Combos de «links» y cancelar: los golpes débiles se repiten rápido (débil, débil, débil), los débiles y '
     'medios se cancelan en especiales y los especiales en el súper. El daño baja poco a poco en combos largos.',
     {"chain": "none", "repeat_light": True, "cancel_from": [0, 1],
      "scaling": True, "scale_free": 2, "scale_step": 10, "scale_min": 50}),
    ("marvel", 'Marvel / Darkstalkers (cadenas)',
     'Cadenas de débil → medio → fuerte con cualquier botón, mezclando de pie y agachado. El fuerte agachado '
     'es un lanzador: lo manda pa\' arriba y saltas a seguir el combo en el aire.',
     {"chain": "stronger", "chain_mix": True, "air_chain": True, "launcher": "C_z", "jump_cancel": "launcher",
      "scaling": True, "scale_free": 3, "scale_step": 8, "scale_min": 30, "extra_stun": 2}),
    ("gg", 'Guilty Gear (gatling)',
     'Gatling: cualquier golpe sigue con uno más fuerte o con la patada de la misma fuerza, saltas después '
     'de cualquier golpe y con energía cancelas lo que sea («Roman cancel»).',
     {"chain": "gatling", "chain_mix": True, "repeat_light": True, "air_chain": True, "jump_cancel": "all",
      "rc": True, "scaling": True, "scale_free": 3, "scale_step": 8, "scale_min": 30, "extra_stun": 2}),
    ("ki", 'Killer Instinct (autodobles)',
     'Abres con un especial (opener) y cuando pega aprietas un puño o patada: sale un autodoble (dos golpes '
     'solos). Con la regla clásica, el botón va según la fuerza del especial: fuerte → medio, medio → débil, '
     'débil → fuerte. También abre un golpe en el aire al caer encima. De ahí cancelas en otro especial (linker) '
     'y repites (hasta 4 autodobles); la versión fuerte de un especial después de un autodoble es el remate '
     '(ender): tumba al rival y cierra el combo. El que lo recibe lo rompe '
     'con puño + patada de la misma fuerza del golpe que le acaba de pegar; si falla, queda bloqueado 3 segundos. '
     'El autodoble solo sale con el rival cerca (no corre hasta él) y un súper solo abre autodobles si lo marcas '
     'en sus ⚙ Ajustes.',
     {"chain": "none", "autodouble": True, "ad_rule": "classic", "enders": True, "ad_limit": 16,
      "ad_max": 4, "ad_air_open": True, "breaker": True, "breaker_mode": "strength", "breaker_hits": 2}),
]
STYLE_KEYS = [s[0] for s in STYLES]


def preset(style):
    d = copy.deepcopy(DEFAULTS)
    d["ad_list"] = default_ad_list()
    for k, _n, _t, ch in STYLES:
        if k == style:
            d.update(copy.deepcopy(ch))
    d["style"] = style
    return d


def default_ad_list():
    """Los tres autodobles de fábrica: débil, medio y fuerte con los golpes de pie (puño y patada)."""
    out = []
    for s_, (p, kk) in enumerate((("S_x", "S_a"), ("S_y", "S_b"), ("S_z", "S_c"))):
        out.append(new_ad(s_, [f"N:{p}", f"N:{kk}"]))
    return out


def new_ad(strength=1, refs=(), button="any", opener="", damage=None, name=""):
    return {"id": uuid.uuid4().hex[:8], "name": name, "strength": int(strength), "button": button,
            "open": opener, "hits": [{"ref": r, "speed": 100} for r in refs],
            "damage": int(damage if damage is not None else [15, 22, 30][int(strength)])}


def migrate_ads(c):
    """De las versiones viejas (un autodoble fijo por fuerza) a la lista."""
    if isinstance(c.get("ad_list"), list):
        return c["ad_list"]
    if "ad" not in c:
        return default_ad_list()
    out = []
    for s_ in range(3):
        refs = [r for r in (c.get("ad", {}).get(str(s_)) or []) if r]
        speeds = list((c.get("ad_speed") or {}).get(str(s_)) or []) + [100, 100]
        ad = new_ad(s_, refs, opener=(c.get("ad_open") or {}).get(str(s_), "") or "",
                    damage=(c.get("ad_damage") or {}).get(str(s_)))
        for j, h in enumerate(ad["hits"]):
            h["speed"] = int(speeds[j] or 100)
        out.append(ad)
    return out


def get(cfg):
    """Las opciones de combos llenas, o None si el personaje nunca las tocó (comportamiento de siempre)."""
    c = cfg.get("combos")
    if not isinstance(c, dict):
        return None
    d = copy.deepcopy(DEFAULTS)
    # opciones nuevas que el personaje todavía no tenía guardadas: las de su estilo (así no cambia a «Personalizado»)
    if c.get("style") in STYLE_KEYS:
        p = preset(c["style"])
        for k in ("ad_max", "ad_air_open"):
            if k not in c:
                d[k] = p[k]
    d.update(c)
    d["ad_list"] = copy.deepcopy(migrate_ads(c))
    return d


def matches(c, style):
    """¿Las opciones son exactamente las del estilo?"""
    p = preset(style)
    return all(c.get(k) == v for k, v in p.items() if k not in ("style", "ad_list"))


def chain_sources(c, target, normals):
    """Estados desde los que se puede encadenar al golpe normal `target`.
    normals: {key: (n, pos, botón, fuerza, patada)}."""
    if target not in normals:
        return []
    n, pos, b, s, kick = normals[target]
    if pos == "A" and not c["air_chain"]:
        return []
    if pos == "A":
        same_pos = ("A",)
    else:
        same_pos = ("S", "C") if c["chain_mix"] else (pos,)
    out = []
    for key, (n2, pos2, b2, s2, kick2) in normals.items():
        if pos2 not in same_pos:
            continue
        ok = False
        if c["chain"] == "same":
            ok = kick2 == kick and s2 < s
        elif c["chain"] == "stronger":
            ok = s2 < s
        elif c["chain"] == "gatling":
            ok = s2 < s or (s2 == s and not kick2 and kick)
        if c["repeat_light"] and s == 0 and key == target:
            ok = True
        if ok:
            out.append(n2)
    return sorted(set(out))


def state_list(states):
    """«StateNo = a || StateNo = b» (o «0» si no hay ninguno)."""
    states = sorted(set(states))
    return " || ".join(f"StateNo = {x}" for x in states) if states else "0"


def press_cmd(p):
    """«x+a» → texto para el [Command]."""
    return "+".join(x.strip() for x in p.split("+"))
