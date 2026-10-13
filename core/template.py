"""
Plantilla de personaje nuevo: se puede jugar en IKEMEN GO desde el primer momento
(con una figura provisional), y luego se le cambian los sprites, animaciones y movimientos.
Los estados básicos (parado, caminar, saltar, recibir golpes…) vienen del common1.cns del juego.
"""
import datetime

from i18n import tr

REQUIRED_ACTIONS = [
    (0, "Parado"), (5, "Voltearse"), (6, "Voltearse agachado"), (10, "Parado a agachado"), (11, "Agachado"),
    (12, "Agachado a parado"), (20, "Caminar adelante"), (21, "Caminar atrás"), (40, "Preparar salto"),
    (41, "Salto quieto (subiendo)"), (42, "Salto adelante (subiendo)"), (43, "Salto atrás (subiendo)"),
    (44, "Salto quieto (bajando)"), (45, "Salto adelante (bajando)"), (46, "Salto atrás (bajando)"),
    (47, "Aterrizar"), (100, "Correr"), (105, "Salto hacia atrás"), (106, "Aterrizar del salto hacia atrás"),
    (120, "Empezar a cubrirse (parado)"), (121, "Empezar a cubrirse (agachado)"), (122, "Empezar a cubrirse (aire)"),
    (130, "Cubriéndose (parado)"), (131, "Cubriéndose (agachado)"), (132, "Cubriéndose (aire)"),
    (140, "Dejar de cubrirse (parado)"), (141, "Dejar de cubrirse (agachado)"), (142, "Dejar de cubrirse (aire)"),
    (150, "Golpe cubierto (parado)"), (151, "Golpe cubierto (parado 2)"), (152, "Golpe cubierto (agachado)"),
    (153, "Golpe cubierto (agachado 2)"), (154, "Golpe cubierto (aire)"), (155, "Golpe cubierto (aire 2)"),
    (170, "Perder (se acabó el tiempo)"), (175, "Empate"), (180, "Ganar"), (190, "Intro"), (191, "Intro 2"),
    (5000, "Golpe alto (leve)"), (5001, "Golpe alto (medio)"), (5002, "Golpe alto (fuerte)"),
    (5005, "Recuperarse del golpe alto (leve)"), (5006, "Recuperarse (medio)"), (5007, "Recuperarse (fuerte)"),
    (5010, "Golpe bajo (leve)"), (5011, "Golpe bajo (medio)"), (5012, "Golpe bajo (fuerte)"),
    (5015, "Recuperarse del golpe bajo (leve)"), (5016, "Recuperarse (medio)"), (5017, "Recuperarse (fuerte)"),
    (5020, "Golpe agachado (leve)"), (5021, "Golpe agachado (medio)"), (5022, "Golpe agachado (fuerte)"),
    (5025, "Recuperarse agachado (leve)"), (5026, "Recuperarse agachado (medio)"), (5027, "Recuperarse agachado (fuerte)"),
    (5030, "Golpeado hacia atrás"), (5035, "Transición al aire"), (5040, "Recuperarse en el aire"),
    (5050, "Cayendo"), (5060, "Cayendo (bajando)"), (5070, "Tropezar"), (5080, "Rebote en el suelo"),
    (5090, "Caer al suelo"), (5100, "Golpe contra el suelo"), (5101, "Rebote"), (5110, "Tirado en el suelo"),
    (5120, "Levantarse"), (5160, "Rebote al caer"), (5170, "Golpe tirado"), (5200, "Recuperarse cayendo"),
    (5210, "Recuperarse en el aire"), (5300, "Mareado"),
]


# no son distancias ni velocidades: no se multiplican al hacer un personaje HD
NOT_SCALED = {"stand.friction", "crouch.friction", "airjump.num", "air.gethit.airrecover.mul", "proj.doscale"}


def _scaled(text, k):
    """Multiplica los números de las líneas 'clave = números' por k (para personajes HD)."""
    if k == 1:
        return text
    out = []
    for ln in text.split("\n"):
        if "=" in ln and not ln.strip().startswith(";") and ln.partition("=")[0].strip().lower() not in NOT_SCALED:
            key, _, val = ln.partition("=")
            parts = []
            ok = True
            for v in val.split(","):
                try:
                    f = float(v) * k
                    parts.append(f"{f:g}")
                except ValueError:
                    ok = False
                    break
            if ok:
                ln = f"{key.rstrip()} = {', '.join(parts)}"
        out.append(ln)
    return "\n".join(out)


def make_def(name, author, lw, lh, base):
    today = datetime.date.today().strftime("%m,%d,%Y")
    return f"""; {name}
[Info]
name = "{name}"
displayname = "{name}"
versiondate = {today}
mugenversion = 1.1
ikemenversion = 1.0
author = "{author}"
pal.defaults = 1
localcoord = {lw},{lh}

[Files]
cmd = {base}.cmd
cns = {base}.cns
st = {base}.cns
stcommon = common1.cns
sprite = {base}.sff
anim = {base}.air
sound = {base}.snd

[Palette Keymap]
a = 1
b = 1
c = 1
x = 1
y = 1
z = 1

[Arcade]
"""


CNS_CONST = """[Data]
life = 1000
power = 3000
attack = 100
defence = 100
fall.defence_up = 50
liedown.time = 60
airjuggle = 15
sparkno = 2
guard.sparkno = 40
KO.echo = 0
volume = 0
IntPersistIndex = 60
FloatPersistIndex = 40

[Size]
xscale = 1
yscale = 1
"""

CNS_SCALED = """ground.back = 15
ground.front = 16
air.back = 12
air.front = 12
height = 60
attack.dist = 160
proj.attack.dist = 90
proj.doscale = 0
head.pos = -5, -90
mid.pos = -5, -60
shadowoffset = 0
draw.offset = 0, 0

[Velocity]
walk.fwd = 2.4
walk.back = -2.2
run.fwd = 4.6, 0
run.back = -4.5, -3.8
jump.neu = 0, -8.4
jump.back = -2.55
jump.fwd = 2.5
runjump.back = -2.55, -8.1
runjump.fwd = 4, -8.1
airjump.neu = 0, -8.1
airjump.back = -2.55
airjump.fwd = 2.5
air.gethit.groundrecover = -0.15, -3.5
air.gethit.airrecover.mul = 0.5, 0.2
air.gethit.airrecover.add = 0, -4.5
air.gethit.airrecover.back = -1
air.gethit.airrecover.fwd = 0
air.gethit.airrecover.up = -2
air.gethit.airrecover.down = 1.5

[Movement]
airjump.num = 1
airjump.height = 35
yaccel = 0.44
stand.friction = 0.85
crouch.friction = 0.82
stand.friction.threshold = 2
crouch.friction.threshold = 0.05
air.gethit.groundlevel = 25
air.gethit.groundrecover.ground.threshold = -20
air.gethit.groundrecover.groundlevel = 10
air.gethit.airrecover.threshold = -1
air.gethit.airrecover.yaccel = 0.35
air.gethit.trip.groundlevel = 15
down.bounce.offset = 0, 20
down.bounce.yaccel = 0.4
down.bounce.groundlevel = 12
down.friction.threshold = 0.05
"""

CNS_STATES = """
[Quotes]
victory1 = "..."

;---------------------------------------------------------------------------
; Golpe de ejemplo (botón a). Cópialo para hacer más ataques.
[Statedef 200]
type = S
movetype = A
physics = S
juggle = 1
velset = 0, 0
ctrl = 0
anim = 200
poweradd = 20
sprpriority = 2

[State 200, Golpe]
type = HitDef
trigger1 = Time = 0
attr = S, NA
damage = 30
animtype = Light
guardflag = MA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
sparkxy = -10, -60
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
ground.hittime = 10
ground.velocity = -4
air.velocity = -2.5, -3

[State 200, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 0
ctrl = 1
"""

CMD = """; Comandos
[Remap]
x = x
y = y
z = z
a = a
b = b
c = c
s = s

[Defaults]
command.time = 15
command.buffer.time = 1

;-| Botones |----------------------------------------------------------------
[Command]
name = "a"
command = a
time = 1

[Command]
name = "b"
command = b
time = 1

[Command]
name = "c"
command = c
time = 1

[Command]
name = "x"
command = x
time = 1

[Command]
name = "y"
command = y
time = 1

[Command]
name = "z"
command = z
time = 1

[Command]
name = "s"
command = s
time = 1

;-| Mantener presionado (los usa el juego para caminar, agacharse y cubrirse) |-
[Command]
name = "holdfwd"
command = /$F
time = 1

[Command]
name = "holdback"
command = /$B
time = 1

[Command]
name = "holdup"
command = /$U
time = 1

[Command]
name = "holddown"
command = /$D
time = 1

[Command]
name = "recovery"
command = x+y
time = 1

;-| Correr |-----------------------------------------------------------------
[Command]
name = "FF"
command = F, F
time = 10

[Command]
name = "BB"
command = B, B
time = 10

;---------------------------------------------------------------------------
[Statedef -1]

[State -1, Correr]
type = ChangeState
value = 100
trigger1 = command = "FF"
trigger1 = statetype = S
trigger1 = ctrl

[State -1, Salto hacia atrás]
type = ChangeState
value = 105
trigger1 = command = "BB"
trigger1 = statetype = S
trigger1 = ctrl

[State -1, Golpe]
type = ChangeState
value = 200
triggerall = command = "a"
trigger1 = statetype = S
trigger1 = ctrl
"""


def fix_scaled_constants(consts, k):
    """Arreglos para personajes HD hechos con la plantilla vieja, que multiplicaba también la fricción
    (el personaje se teletransportaba al caminar o al caer de un salto). consts: de parse_constants.
    Devuelve [(sección, clave, índice, valor)]."""
    out = []
    if (consts.get("movement.stand.friction") or 0) > 1:
        out.append(("Movement", "stand.friction", 0, 0.85))
    if (consts.get("movement.crouch.friction") or 0) > 1:
        out.append(("Movement", "crouch.friction", 0, 0.82))
    if k > 1 and consts.get("movement.airjump.num") == k:
        out.append(("Movement", "airjump.num", 0, 1))
    if k > 1 and (consts.get("velocity.air.gethit.airrecover.mul.x") or 0) > 1:
        out.append(("Velocity", "air.gethit.airrecover.mul", 0, 0.5))
        out.append(("Velocity", "air.gethit.airrecover.mul", 1, 0.2))
    return out


def make_cns(k):
    return CNS_CONST + _scaled(CNS_SCALED, k) + CNS_STATES


def make_air(k):
    def box(x1, y1, x2, y2):
        return ", ".join(str(int(round(v * k))) for v in (x1, y1, x2, y2))
    out = ["; " + tr('Animaciones (todas usan la figura provisional 0,0: cámbialas por tus sprites)'), ""]
    for num, title in REQUIRED_ACTIONS:
        out.append(f"; {tr(title)}")
        out.append(f"[Begin Action {num}]")
        out.append("Clsn2Default: 1")
        out.append(f" Clsn2[0] = {box(-15, 0, 15, -90)}")
        out.append("0,0, 0,0, -1" if num in (0, 11, 130, 131, 132, 5110, 170, 175, 180) else "0,0, 0,0, 6")
        out.append("")
    out += ["; " + tr('Golpe de ejemplo'), "[Begin Action 200]", "Clsn2Default: 1", f" Clsn2[0] = {box(-15, 0, 15, -90)}",
            "0,0, 0,0, 4", "Clsn1: 1", f" Clsn1[0] = {box(10, -70, 50, -55)}", "0,0, 6,0, 6", "0,0, 0,0, 6", ""]
    return "\n".join(out)
