"""Un personaje abierto: su .def y los archivos que nombra."""
import datetime
import re
import shutil
from pathlib import Path

from core.air import AirFile
from core.deffile import DefFile
from core.sff import SffFile, read_act
from core.snd import SndFile
from core.textio import ci_find

CODE_KEYS = re.compile(r"^(cmd|cns|st\d*|stcommon|ai)$", re.IGNORECASE)
CODE_EXT = (".cns", ".cmd", ".st", ".zss", ".ai", ".def", ".txt", ".lua", ".const")


class Project:
    def __init__(self, def_path):
        self.def_path = Path(def_path)
        self.folder = self.def_path.parent
        self.defs = DefFile(self.def_path)
        self._sff = self._air = self._snd = None
        self.acts = None
        self.defs_dirty = False
        self._backed = set()
        self._stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    def backup(self, path):
        """Antes de sobrescribir un archivo por primera vez en esta sesión, guarda una copia en
        _editor_backups/<fecha>/ dentro de la carpeta del personaje."""
        try:
            path = Path(path)
            if not path.is_file() or path.resolve() in self._backed:
                return
            rel = path.resolve().relative_to(self.folder.resolve()) if path.resolve().is_relative_to(self.folder.resolve()) else Path(path.name)
            dst = self.folder / "_editor_backups" / self._stamp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)
            self._backed.add(path.resolve())
        except OSError:
            pass

    # ---- rutas
    def file(self, key):
        v = self.defs.get("Files", key)
        return ci_find(self.folder, v) if v else None

    def file_value(self, key):
        return self.defs.get("Files", key)

    def localcoord(self):
        v = self.defs.get("Info", "localcoord", "")
        try:
            w, h = [int(float(x)) for x in v.split(",")[:2]]
            return w, h
        except ValueError:
            return 320, 240

    def name(self):
        return self.defs.get("Info", "displayname") or self.defs.get("Info", "name") or self.def_path.stem

    # ---- archivos
    @property
    def sff(self):
        if self._sff is None:
            p = self.file("sprite")
            self._sff = SffFile.load(p) if p else SffFile()
            if self._sff.path is None:
                self._sff.path = self.folder / (self.file_value("sprite") or f"{self.def_path.stem}.sff")
        return self._sff

    def sff_loaded(self):
        return self._sff is not None

    @property
    def air(self):
        if self._air is None:
            p = self.file("anim")
            self._air = AirFile.load(p) if p else AirFile()
            if self._air.path is None:
                self._air.path = self.folder / (self.file_value("anim") or f"{self.def_path.stem}.air")
        return self._air

    def air_loaded(self):
        return self._air is not None

    @property
    def snd(self):
        if self._snd is None:
            p = self.file("sound")
            self._snd = SndFile.load(p) if p else SndFile()
            if self._snd.path is None:
                self._snd.path = self.folder / (self.file_value("sound") or f"{self.def_path.stem}.snd")
        return self._snd

    def snd_loaded(self):
        return self._snd is not None

    def char_palettes(self):
        """[(n, nombre, Palette|None)] — paletas que se pueden elegir (pal1..pal12 o las 1,n del SFF)."""
        try:
            self.sff
        except Exception:
            pass
        if self.acts is None:
            out = []
            for n in range(1, 13):
                v = self.defs.get("Files", f"pal{n}")
                if v:
                    p = ci_find(self.folder, v)
                    try:
                        out.append((n, v, read_act(p) if p else None))
                    except OSError:
                        out.append((n, v, None))
            self.acts = out
        res = list(self.acts)
        have = {n for n, _v, _p in res}
        if self._sff is not None:
            for i, p in enumerate(self._sff.palettes):
                if p.group == 1 and p.number not in have and 1 <= p.number <= 12:
                    res.append((p.number, f"SFF {p.group},{p.number}", p))
        return sorted(res)

    def code_files(self):
        """Archivos de código: los del .def primero y luego los demás de la carpeta."""
        seen, out = set(), []
        for k, v in self.defs.keys("Files"):
            if CODE_KEYS.match(k) and v:
                p = ci_find(self.folder, v)
                if p and p.resolve() not in seen:
                    seen.add(p.resolve())
                    out.append((k, p))
        if self.def_path.resolve() not in seen:
            seen.add(self.def_path.resolve())
            out.insert(0, ("def", self.def_path))
        for p in sorted(self.folder.rglob("*")):
            if "_editor_backups" in p.parts or "_editor_history" in p.parts:
                continue
            if p.is_file() and p.suffix.lower() in CODE_EXT and p.resolve() not in seen:
                seen.add(p.resolve())
                out.append(("", p))
        return out
