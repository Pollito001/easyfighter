"""
Lo que el editor sabe del código de MUGEN / IKEMEN GO: nombres para colorear y autocompletar,
y una revisión de errores comunes (.cns / .cmd / .st).
"""
import re

from core._lists import SCTRLS, TRIGGERS

_NICE = ("AfterImage AfterImageTime AllPalFX AngleAdd AngleDraw AngleMul AngleSet AppendToClipboard AssertCommand "
         "AssertInput AssertSpecial AttackDist AttackMulSet BGPalFX BindToParent BindToRoot BindToTarget ChangeAnim "
         "ChangeAnim2 ChangeState ClearClipboard CtrlSet DefenceMulSet DestroySelf DisplayToClipboard EnvColor "
         "EnvShake Explod ExplodBindTime FallEnvShake ForceFeedback GameMakeAnim GetHitVarSet Gravity Helper HitAdd "
         "HitBy HitDef HitFallDamage HitFallSet HitFallVel HitOverride HitVelSet LifeAdd LifeSet MakeDust MapAdd MapSet "
         "ModifyExplod ModifyProjectile MoveHitReset NotHitBy Null Offset PalFX ParentVarAdd ParentVarSet Pause "
         "PlayerPush PlaySnd PosAdd PosFreeze PosSet PowerAdd PowerSet Projectile RemapPal RemoveExplod ReversalDef "
         "ScreenBound SelfState SndPan SprPriority StateTypeSet StopSnd SuperPause TargetBind TargetDrop TargetFacing "
         "TargetLifeAdd TargetPowerAdd TargetState TargetVelAdd TargetVelSet Trans Turn VarAdd VarRandom VarRangeSet "
         "VarSet VelAdd VelMul VelSet Width Zoom "
         "AnimElem AnimElemNo AnimElemTime AnimExist AnimTime BackEdgeBodyDist BackEdgeDist CanRecover Command Ctrl "
         "FrontEdgeBodyDist FrontEdgeDist GameTime GetHitVar HitCount HitDefAttr HitFall HitOver HitPauseTime "
         "HitShakeOver HitVel InGuardDist IsHelper IsHomeTeam Life LifeMax MoveContact MoveGuarded MoveHit MoveType "
         "MoveReversed NumEnemy NumExplod NumHelper NumPartner NumProj NumProjID NumTarget P2BodyDist P2Dist P2Life "
         "P2MoveType P2StateNo P2StateType PalNo ParentDist Pos Power PowerMax PrevStateNo ProjContactTime "
         "ProjGuardedTime ProjHitTime Random RootDist RoundNo RoundState ScreenPos SelfAnimExist StateNo StateType "
         "SysVar SysFVar TeamMode TeamSide Time TimeMod UniqHitCount Var FVar Vel Win Lose AILevel Alive Anim Const "
         "Facing ID IfElse Cond Name AuthorName Abs Floor Ceil Exp Ln Log Sin Cos Tan Pi E Map").split()
NICE = {w.lower(): w for w in _NICE}


def nice(word):
    return NICE.get(word.lower(), word[:1].upper() + word[1:])


SCTRL_SET = set(SCTRLS)
TRIGGER_SET = set(TRIGGERS)
PARAMS = ("type triggerall trigger1 trigger2 trigger3 trigger4 value x y persistent ignorehitpause ctrl anim "
          "movetype physics statetype juggle poweradd velset facehitbox sprpriority hitdefpersist movehitpersist "
          "hitcountpersist attr hitflag guardflag animtype air.animtype fall.animtype priority damage pausetime "
          "guard.pausetime sparkno guard.sparkno sparkxy hitsound guardsound ground.type air.type ground.slidetime "
          "guard.slidetime ground.hittime guard.hittime air.hittime guard.ctrltime guard.dist yaccel ground.velocity "
          "guard.velocity air.velocity airguard.velocity ground.cornerpush.veloff air.cornerpush.veloff "
          "down.cornerpush.veloff guard.cornerpush.veloff airguard.cornerpush.veloff airguard.ctrltime air.juggle "
          "mindist maxdist snap p1sprpriority p2sprpriority p1facing p1getp2facing p2facing p1stateno p2stateno "
          "p2getp1state forcestand fall fall.xvelocity fall.yvelocity fall.recover fall.recovertime fall.damage "
          "air.fall down.velocity down.hittime down.bounce id chainid nochainid hitonce kill guard.kill fall.kill "
          "numhits getpower givepower palfx.time palfx.mul palfx.add envshake.time envshake.freq envshake.ampl "
          "envshake.phase fall.envshake.time fall.envshake.freq fall.envshake.ampl fall.envshake.phase pos postype "
          "bindtime removetime supermove pausemovetime scale ontop shadow ownpal removeongethit ignorehitpause "
          "trans accel random helpertype name keyctrl size.xscale size.ystate stateno time darken p2defmul "
          "unhittable sound channel lowpriority freq loop pan abspan volume volumescale command buffer.time "
          "command.time command.buffer.time hitdefpersist var fvar sysvar sysfvar mul add sinadd invertall color "
          "flag flag2 flag3 slot source dest redirectid").split()
SECTIONS = ("Data Size Velocity Movement Quotes Command Defaults Remap Statedef State Info Files Arcade "
            "Palette Keymap").split()
WORDS = sorted({nice(w) for w in SCTRLS} | {nice(w) for w in TRIGGERS} | set(PARAMS))

COMMON_STATE_RANGES = ((0, 199), (5000, 5999))  # están en common1.cns del juego


def strip_comment(line, zss=False):
    out, q = [], False
    for ch in line:
        if ch == '"':
            q = not q
        if not q and ((ch == "#") if zss else (ch == ";")):
            break
        out.append(ch)
    return "".join(out)


def statedefs_in(text):
    return {int(m.group(1)) for m in re.finditer(r"^\s*\[\s*statedef\s+(-?\d+)", text, re.IGNORECASE | re.MULTILINE)}


def check(text, kind="cns", known_states=None, known_anims=None, known_sounds=None):
    """Lista de (línea, nivel, mensaje). nivel: 'error' o 'aviso'. kind: cns | cmd | zss."""
    from i18n import tr
    issues = []
    if kind == "zss":
        braces = parens = 0
        for line in text.split("\n"):
            b = re.sub(r'"[^"]*"', '""', strip_comment(line, True))
            braces += b.count("{") - b.count("}")
            parens += b.count("(") + b.count("[") - b.count(")") - b.count("]")
        n = len(text.split("\n"))
        if braces:
            issues.append((n, "aviso", tr('las llaves {{ }} no cuadran ({0:+d})').format(braces)))
        if parens:
            issues.append((n, "aviso", tr('los paréntesis no cuadran ({0:+d})').format(parens)))
        return issues
    lines = text.split("\n")
    seen_defs = {}
    state = None  # (línea, tiene type, tiene trigger, type)

    def close_state():
        if state is None:
            return
        ln, typ, trig = state
        if not typ:
            issues.append((ln, "error", tr('al [State] le falta «type»')))
        elif typ.lower() not in SCTRL_SET:
            issues.append((ln, "aviso", tr('tipo de controlador desconocido: «{0}»').format(typ)))
        if not trig and typ and typ.lower() != "null":
            issues.append((ln, "error", tr('al [State] le falta «trigger1» (o triggerall)')))
    cur_type = None
    state_text = ""
    for n, line in enumerate(lines, 1):
        b = strip_comment(line).strip()
        if not b:
            continue
        m = re.match(r"^\[\s*(.+?)\s*\]?$", b)
        if b.startswith("["):
            close_state()
            state = None
            if not b.endswith("]"):
                issues.append((n, "error", tr('falta el «]»')))
            head = m.group(1).strip().rstrip("]").strip() if m else b
            word = head.split()[0].lower() if head.split() else ""
            if word == "statedef":
                mm = re.match(r"statedef\s+(-?\d+)", head, re.IGNORECASE)
                if not mm:
                    issues.append((n, "error", tr('[Statedef] sin número')))
                else:
                    num = int(mm.group(1))
                    if num in seen_defs:
                        issues.append((n, "error", tr('[Statedef {0}] repetido (también en la línea {1})').format(num, seen_defs[num])))
                    seen_defs[num] = n
            elif word == "state":
                state = [n, None, False]
                cur_type = None
                state_text = ""
            continue
        if "=" not in b:
            if kind == "cmd" or state is not None:
                issues.append((n, "aviso", tr('línea sin «=»')))
            continue
        state_text += b + "\n"
        key, _, val = b.partition("=")
        key = key.strip().lower()
        val = val.strip()
        vv = re.sub(r'"[^"]*"', '""', val)
        if vv.count("(") + vv.count("[") != vv.count(")") + vv.count("]"):
            issues.append((n, "error", tr('paréntesis sin cerrar')))
        if val.count('"') % 2:
            issues.append((n, "error", tr('comillas sin cerrar')))
        if state is not None:
            if key == "type":
                state[1] = val
                cur_type = val.lower()
            elif re.match(r"trigger(all|\d+)$", key):
                state[2] = state[2] or key in ("trigger1", "triggerall")
                if not val:
                    issues.append((n, "error", tr('condición vacía')))
            elif key == "value" and cur_type in ("changestate", "selfstate") and known_states is not None:
                mm = re.match(r"^-?\d+$", val)
                if mm:
                    num = int(val)
                    if num not in known_states and not any(a <= num <= b2 for a, b2 in COMMON_STATE_RANGES):
                        issues.append((n, "aviso", tr('el estado {0} no existe en este personaje').format(num)))
            elif key == "value" and cur_type in ("changeanim", "changeanim2") and known_anims is not None:
                guarded = re.search(r"selfanimexist\s*\(\s*" + re.escape(val) + r"\s*\)", state_text.lower())
                if re.match(r"^-?\d+$", val) and int(val) not in known_anims and not guarded:
                    issues.append((n, "aviso", tr('la animación {0} no existe en el .air').format(val)))
            elif key == "value" and cur_type == "playsnd" and known_sounds is not None:
                mm = re.match(r"^(-?\d+)\s*,\s*(-?\d+)$", val)
                if mm and (int(mm.group(1)), int(mm.group(2))) not in known_sounds:
                    issues.append((n, "aviso", tr('el sonido {0},{1} no existe en el .snd').format(mm.group(1), mm.group(2))))
    close_state()
    return issues


def outline(text, kind="cns"):
    """[(línea, texto)] para saltar rápido: Statedef, State y Command."""
    out = []
    for n, line in enumerate(text.split("\n"), 1):
        b = strip_comment(line, kind == "zss").strip()
        if not b:
            continue
        if b.startswith("["):
            head = b.strip("[] ")
            low = head.lower()
            if low.startswith(("statedef", "state ", "state,", "function")) or \
                    low in ("data", "size", "velocity", "movement", "quotes", "defaults", "remap"):
                out.append((n, head))
            elif low == "command":
                out.append((n, "Command"))
        elif kind == "cmd" and b.lower().startswith("name") and out and out[-1][1] == "Command":
            out[-1] = (out[-1][0], "Command  " + b.partition("=")[2].strip())
    return out
