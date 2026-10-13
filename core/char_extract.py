"""Personaje nuevo con los sprites de otro: copia sus sprites (y paletas y sonidos) a un personaje de la
plantilla y pone sus animaciones en las casillas del modo simple (parado, caminar, golpes, especiales…).

El código del personaje nuevo es el de la plantilla (se puede jugar enseguida); lo que hacía el original
no se copia, solo sus dibujos. Al abrirlo en el editor, el modo simple arma las animaciones y el código.
"""
import re
import shutil
import uuid
from pathlib import Path

from core import detect_moves as dm
from core import simple_gen as sg
from core import template
from core.deffile import DefFile
from core.project import Project
from core.textio import read_text, write_text
from i18n import tr


def _typical_time(frames, default=4):
    ts = sorted(f.time for f in frames if f.time > 0)
    return max(1, ts[len(ts) // 2]) if ts else default


def _entry(action, default_time=4):
    """{"frames": [[g, n]…], "time": …} de una acción del .air (o None)."""
    if action is None or not action.frames:
        return None
    return {"frames": [[f.group, f.number] for f in action.frames],
            "time": _typical_time(action.frames, default_time)}


def _reds(action):
    return [i for i, f in enumerate(action.frames) if f.clsn1] if action is not None else []


def _motion_key(cfg, command):
    """Clave del comando para el modo simple: uno de los de siempre, o uno propio del personaje."""
    cmd = dm.command_template(command)
    key = next((k for k, c in sg.MOTION_CMD.items() if c.replace(" ", "") == cmd.replace(" ", "")), None)
    if key:
        return key
    mots = cfg.setdefault("custom_motions", [])
    same = next((m for m in mots if m.get("cmd") == cmd), None)
    if same is None:
        same = {"key": "C" + uuid.uuid4().hex[:8],
                "label": dm.arrows(cmd.replace("{b}", "x")).replace(" + x", tr(' + botón')), "cmd": cmd}
        mots.append(same)
    return same["key"]


def _moves(src):
    """Golpes, agarre y especiales que encuentra en el código del original."""
    cmd = src.file("cmd")
    if cmd is None or cmd.suffix.lower() == ".zss":
        return []
    paths = [p for k, p in src.code_files() if k and k.lower() not in ("def", "cmd", "stcommon")
             and p.suffix.lower() != ".zss" and p.is_file()]

    def text(p):
        try:
            return read_text(p)[0]
        except OSError:
            return ""
    try:
        return dm.find_moves(text(cmd), [text(p) for p in paths], sg.ENT_BEGIN, sg.ENT_END,
                             state_files=paths, cmd_file=cmd)
    except Exception:
        return []


def build_config(src, tr=lambda s: s):
    """La configuración del modo simple con las animaciones del original en cada casilla.
    Devuelve (cfg, resumen)."""
    air = src.air
    cfg = sg._fill({})
    done = {"anims": 0, "normals": 0, "specials": 0}
    # casillas de animación: la acción de siempre de cada una (0 parado, 20 caminar, 5000 recibir golpe…)
    poses = {"win": [n for n in range(180, 190) if air.find(n) is not None and air.find(n).frames],
             "lose": [n for n in (170, 171, 172, 173, 174) if air.find(n) is not None and air.find(n).frames]}
    for key, slot in sg.ANIM_SLOTS.items():
        if key == "select_pose" or key in sg.EXTRA_POSES:
            continue
        if key in poses:
            cands = poses[key][:1]
        else:
            cands = [slot[3]] + [num for _f, num in slot[4]]
        e = next((x for x in (_entry(air.find(n)) for n in cands) if x), None)
        if e:
            cfg["anims"][key] = e
            done["anims"] += 1
    # varias poses de victoria / derrota (180, 181, 182…): las de más van a las casillas opcionales
    for main_, extra in (("win", ["win2", "win3", "win4"]), ("lose", ["lose2", "lose3"])):
        for key, n in zip(extra, poses[main_][1:]):
            cfg["anims"][key] = _entry(air.find(n))
            done["anims"] += 1
    found = _moves(src)
    # golpes normales y agarre
    for f in found:
        a = air.find(f.anim) if f.anim is not None else None
        e = _entry(a, 4)
        if not e:
            continue
        if f.kind == "normal" and f.key in sg.NORMAL_KEYS and f.key not in cfg["normals"]:
            reds = _reds(a)
            if reds:
                e["hit"] = reds[0] + 1
            if f.damage:
                e["damage"] = int(f.damage)
            cfg["normals"][f.key] = e
            done["normals"] += 1
        elif f.kind == "throw" and not cfg["throw"]:
            reds = _reds(a)
            if reds:
                e["hit"] = reds[0] + 1
            cfg["throw"] = e
    # especiales y súper: uno por movimiento (las versiones débil / fuerte del original van juntas)
    seen = set()
    for f in found:
        if f.kind not in ("special", "super") or f.group in seen:
            continue
        seen.add(f.group)
        a = air.find(f.anim) if f.anim is not None else None
        e = _entry(a, 4)
        if not e:
            continue
        typ = f.typ if f.typ in ("proj", "hit", "dash", "rise") else "hit"
        sp = dict(name=dm.nice_name(f.label) or tr("Especial"), kind=f.kind, type=typ,
                  motion=_motion_key(cfg, f.command), family="kick" if f.button in ("a", "b", "c") else "punch",
                  damage=int(f.damage or (220 if f.kind == "super" else 70)), versions=[1, 1, 1],
                  frames=e["frames"], time=e["time"], open=False)
        reds = _reds(a)
        if reds:
            sp["hit"] = reds[0] + 1
            if typ in ("hit", "dash", "rise"):
                sp["hit_frames"] = [i + 1 for i in reds]
        if typ == "proj":
            pe = _entry(air.find(f.proj_anim) if f.proj_anim is not None else None, 3)
            if pe:
                sp["proj"] = pe
                he = _entry(air.find(f.proj_hit_anim) if f.proj_hit_anim is not None else None, 3)
                if he:
                    sp["proj_hit"] = he
            else:
                sp["type"] = "hit"
        sp["events"] = sg.type_events(sp)
        sp["evmode"] = sg.EVMODE
        cfg["specials"].append(sp)
        done["specials"] += 1
    # al abrirlo, el editor arma las animaciones y el código de todo esto
    cfg["pending_apply"] = True
    return cfg, done


def extract(src_def, dest, name, author="", copy_sounds=True, tr=lambda s: s):
    """Crea en `dest` (carpeta nueva o vacía) un personaje de la plantilla con los sprites de `src_def`.
    Devuelve (ruta del .def nuevo, resumen)."""
    src = Project(src_def)
    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(str(dest))
    dest.mkdir(parents=True, exist_ok=True)
    base = re.sub(r"[^\w\-]+", "_", dest.name).strip("_") or "Personaje"
    lw, lh = src.localcoord()
    k = lw / 320
    new_def = dest / f"{base}.def"
    write_text(new_def, template.make_def(name, author, lw, lh, base), "utf-8", "\r\n")
    write_text(dest / f"{base}.cns", template.make_cns(k), "utf-8", "\r\n")
    write_text(dest / f"{base}.cmd", template.CMD, "utf-8", "\r\n")
    write_text(dest / f"{base}.air", template.make_air(k), "utf-8", "\r\n")
    # los sprites (con sus paletas) tal cual
    sff = src.file("sprite")
    if sff is None or not sff.is_file():
        raise FileNotFoundError(tr("El personaje no tiene archivo de sprites (.sff)."))
    shutil.copy2(sff, dest / f"{base}.sff")
    snd = src.file("sound")
    if copy_sounds and snd is not None and snd.is_file():
        shutil.copy2(snd, dest / f"{base}.snd")
    else:
        from core.snd import SndFile
        SndFile().save(dest / f"{base}.snd")
    d = DefFile(new_def)
    for i in range(1, 13):
        pal = src.file(f"pal{i}")
        if pal is not None and pal.is_file():
            shutil.copy2(pal, dest / pal.name)
            d.set("Files", f"pal{i}", pal.name)
    d.save()
    cfg, done = build_config(src, tr)
    sg.save_config(new_def, cfg)
    return new_def, done
