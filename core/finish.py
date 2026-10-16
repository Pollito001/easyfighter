"""Terminar un personaje: datos de cuadros, historial de versiones y el .zip para compartir."""
import datetime
import re
import shutil
import zipfile
from pathlib import Path

SKIP_DIRS = {"_editor_backups", "_editor_history", "__pycache__"}
HISTORY = "_editor_history"


# ---------------------------------------------------------------- datos de cuadros
def _blocks(text):
    """[(título del comentario de arriba, número, cabecera, [(tipo, líneas)])] de cada Statedef."""
    out = []
    title = ""
    cur = None
    ctrl = None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"\[\s*statedef\s+(-?\d+)\s*[\],]", line, re.IGNORECASE)
        if m:
            cur = (title, int(m.group(1)), {}, [])
            out.append(cur)
            ctrl = None
            continue
        if line.startswith(";") and not line.startswith(";-"):
            title = line.lstrip("; ").strip()
            continue
        if cur is None or not line or line.startswith(";"):
            continue
        if re.match(r"\[\s*state\s", line, re.IGNORECASE):
            ctrl = [None, []]
            cur[3].append(ctrl)
            continue
        if "=" not in line:
            continue
        key, val = [x.strip() for x in line.split(";")[0].split("=", 1)]
        key = key.lower()
        if ctrl is None:
            cur[2][key] = val
        elif key == "type":
            ctrl[0] = val.lower()
        else:
            ctrl[1].append((key, val))
    return out


def _elem_tick(frames, elem):
    """Tick (desde 1) en que empieza el cuadro elem (desde 1)."""
    t = 0
    for f in frames[:max(0, elem - 1)]:
        t += f.time if f.time > 0 else 0
    return t + 1


def frame_data(st_text, air):
    """Filas de datos de cuadros de los movimientos del archivo del modo simple:
    dict(name, startup, active, recovery, total, on_hit, on_block, kind). None = no se sabe."""
    rows = []
    for title, num, head, ctrls in _blocks(st_text):
        if head.get("movetype", "").upper() != "A" or num < 0:
            continue
        hit = next((c for c in ctrls if c[0] in ("hitdef", "projectile", "helper")), None)
        if hit is None:
            continue
        try:
            anim = int(head.get("anim", ""))
        except ValueError:
            continue
        a = air.find(anim) if air is not None else None
        if a is None or not a.frames:
            continue
        frames = a.frames
        hold = frames[-1].time < 0
        total = None if hold else sum(max(1, f.time) for f in frames)
        params = dict(hit[1])
        kind = hit[0]
        startup = None
        trig = " ".join(v for k, v in hit[1] if k.startswith("trigger"))
        m = re.search(r"animelem\s*=\s*(\d+)", trig, re.IGNORECASE)
        if m:
            startup = _elem_tick(frames, int(m.group(1)))
        reds = [i for i, f in enumerate(frames) if f.clsn1]
        if startup is None and reds:
            startup = _elem_tick(frames, reds[0] + 1)
        active = None
        if kind == "hitdef" and reds:
            first = reds[0]
            last = first
            while last + 1 < len(frames) and frames[last + 1].clsn1:
                last += 1
            active = sum(max(1, f.time) if f.time > 0 else 1 for f in frames[first:last + 1])
        recovery = None
        if total is not None and startup is not None:
            recovery = max(0, total - (startup - 1) - (active or 1))

        def num_of(key):
            v = params.get(key)
            if v is None:
                return None
            try:
                return int(float(v.split(",")[0]))
            except ValueError:
                return None
        hittime = num_of("ground.hittime")
        guard = num_of("guard.hittime")
        if guard is None:
            guard = hittime
        on_hit = on_block = None
        if kind == "hitdef" and total is not None and startup is not None:
            left = total - startup
            if hittime is not None and not re.search(r"\bfall\s*=\s*1", " ".join(f"{k}={v}" for k, v in hit[1])):
                on_hit = hittime - left
            if guard is not None:
                on_block = guard - left
        rows.append(dict(name=title or str(num), state=num, startup=startup, active=active, recovery=recovery,
                         total=total, on_hit=on_hit, on_block=on_block, kind=kind,
                         knockdown=bool(re.search(r"\bfall\s*=\s*1", " ".join(f"{k}={v}" for k, v in hit[1])))))
    return rows


# ---------------------------------------------------------------- historial de versiones
def _copy_tree(src, dst):
    for p in sorted(Path(src).rglob("*")):
        rel = p.relative_to(src)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        out = Path(dst) / rel
        if p.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        elif p.is_file():
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)


def snapshot(folder, label=""):
    """Guarda una foto de la carpeta del personaje en _editor_history/<fecha>. Devuelve su carpeta."""
    folder = Path(folder)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    dst = folder / HISTORY / stamp
    n = 2
    while dst.exists():
        dst = folder / HISTORY / f"{stamp} ({n})"
        n += 1
    dst.mkdir(parents=True)
    _copy_tree(folder, dst)
    if label:
        (dst / "_nota.txt").write_text(label, encoding="utf-8")
    return dst


def snapshots(folder):
    """[(carpeta, fecha, nota)] de las fotos, de la más nueva a la más vieja."""
    base = Path(folder) / HISTORY
    out = []
    if base.is_dir():
        for d in base.iterdir():
            if not d.is_dir():
                continue
            m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2})", d.name)
            if not m:
                continue
            when = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H-%M-%S")
            note = ""
            nf = d / "_nota.txt"
            if nf.is_file():
                try:
                    note = nf.read_text(encoding="utf-8").strip()
                except OSError:
                    pass
            out.append((d, when, note))
    out.sort(key=lambda x: (x[1], x[0].name), reverse=True)
    return out


def restore(folder, snap):
    """Vuelve a una foto: primero guarda otra de cómo está ahora, después copia los archivos de la foto
    (los archivos que la foto no tiene se quedan; no se borra nada)."""
    folder = Path(folder)
    snapshot(folder, "Antes de volver a " + Path(snap).name)
    for p in sorted(Path(snap).rglob("*")):
        if p.is_file() and p.name != "_nota.txt":
            out = folder / p.relative_to(snap)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)


def prune(folder, keep=20):
    """Deja solo las `keep` fotos más nuevas."""
    for d, _w, _n in snapshots(folder)[keep:]:
        shutil.rmtree(d, ignore_errors=True)


def last_snapshot_age(folder):
    """Minutos desde la última foto (None si no hay)."""
    lst = snapshots(folder)
    if not lst:
        return None
    return (datetime.datetime.now() - lst[0][1]).total_seconds() / 60.0


# ---------------------------------------------------------------- compartir
def make_zip(folder, out_path, extra_files=None):
    """Arma el .zip del personaje: la carpeta entera (sin copias del editor) dentro de una carpeta con su
    nombre. extra_files: {nombre: texto} que se agregan dentro (por ejemplo, la lista de comandos)."""
    folder = Path(folder)
    out_path = Path(out_path)
    top = folder.name
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            rel = p.relative_to(folder)
            if any(part in SKIP_DIRS for part in rel.parts) or not p.is_file():
                continue
            if p.resolve() == out_path.resolve():
                continue
            z.write(p, f"{top}/{rel.as_posix()}")
        for name, text in (extra_files or {}).items():
            z.writestr(f"{top}/{name}", text)
    return out_path
