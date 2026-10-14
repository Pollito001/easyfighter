#!/usr/bin/env python3
"""Arma el ejecutable del IKEMEN GO Character Editor para el sistema donde lo corres.

PyInstaller no puede hacer ejecutables para otros sistemas: el de Windows se arma en Windows, el de macOS en
un Mac y el de Linux en Linux. Para tener los tres sin tener las tres computadoras, usa el workflow de GitHub
(.github/workflows/build.yml): GitHub los arma solo en sus máquinas (ver la guía en el README).

Uso:
    python3 packaging/build.py                 # carpeta con el programa + .zip / .tar.gz para compartir
    python3 packaging/build.py --onefile       # un solo archivo (abre más lento)
    python3 packaging/build.py --appimage      # Linux: además, un .AppImage
    python3 packaging/build.py --version 1.2   # nombre de la versión en los archivos

Necesitas: pip install -r requirements.txt pyinstaller pillow
Todo queda en la carpeta «dist» del proyecto.
"""
import argparse
import datetime
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = "IKEMEN-GO-Character-Editor"
PRETTY = "IKEMEN GO Character Editor"
DATA = ["lang", "ejemplos", "icon.png", "LICENSE", "README.md", "README.es.md"]


def say(msg):
    print(f"\n== {msg}", flush=True)


def os_name():
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def arch():
    m = platform.machine().lower()
    return {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(m, m or "x64")


def check_tools():
    missing = []
    for mod in ("PyInstaller", "PyQt6", "numpy"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod.lower())
    if missing:
        sys.exit("Falta instalar: " + ", ".join(missing) +
                 f"\n  {sys.executable} -m pip install -r requirements.txt pyinstaller pillow")
    try:
        __import__("PIL")
    except ImportError:
        print("Aviso: sin Pillow el ejecutable sale sin icono (pip install pillow).")


def icon_for(osn, work):
    """Icono en el formato de cada sistema (sale del icon.png)."""
    png = ROOT / "icon.png"
    if not png.is_file():
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    img = Image.open(png).convert("RGBA")
    if osn == "windows":
        out = work / "icon.ico"
        img.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return out
    if osn == "macos":
        out = work / "icon.icns"
        try:
            img.resize((512, 512)).save(out)
            return out
        except Exception:
            return None
    return None             # Linux: el icono va en el .desktop del AppImage


def pyinstaller(osn, onefile, work):
    sep = ";" if osn == "windows" else ":"
    args = [sys.executable, "-m", "PyInstaller", str(ROOT / "main.py"), "--name", APP, "--noconfirm", "--clean",
            "--windowed", "--distpath", str(ROOT / "dist"), "--workpath", str(work / "build"),
            "--specpath", str(work), "--collect-submodules", "ui", "--collect-submodules", "core",
            "--paths", str(ROOT),
            # partes de Qt que el editor no usa (el programa pesa mucho menos)
            "--exclude-module", "PyQt6.QtWebEngineCore", "--exclude-module", "PyQt6.QtWebEngineWidgets",
            "--exclude-module", "PyQt6.QtQuick", "--exclude-module", "PyQt6.QtQml", "--exclude-module", "PyQt6.Qt3DCore",
            "--exclude-module", "PyQt6.QtCharts", "--exclude-module", "PyQt6.QtDataVisualization",
            "--exclude-module", "tkinter", "--exclude-module", "matplotlib"]
    args.append("--onefile" if onefile else "--onedir")
    for d in DATA:
        p = ROOT / d
        if p.exists():
            args += ["--add-data", f"{p}{sep}{d if p.is_dir() else '.'}"]
    ic = icon_for(osn, work)
    if ic is not None:
        args += ["--icon", str(ic)]
    if osn == "macos":
        args += ["--osx-bundle-identifier", "io.github.ikemen-chareditor"]
    say("PyInstaller (toma unos minutos)")
    subprocess.run(args, check=True, cwd=ROOT)


def built_path(osn, onefile):
    dist = ROOT / "dist"
    if osn == "macos":
        return dist / f"{APP}.app"
    if onefile:
        return dist / (APP + (".exe" if osn == "windows" else ""))
    return dist / APP


def package(osn, onefile, version):
    """El archivo para compartir: .zip (Windows y macOS) o .tar.gz (Linux, guarda los permisos)."""
    src = built_path(osn, onefile)
    base = f"{APP}-{version}-{osn}-{arch()}"
    say(f"Empaquetando {src.name}")
    if osn == "linux":
        out = ROOT / "dist" / (base + ".tar.gz")
        with tarfile.open(out, "w:gz") as t:
            t.add(src, arcname=src.name)
        return out
    if osn == "macos" and shutil.which("ditto"):
        out = ROOT / "dist" / (base + ".zip")
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(src), str(out)], check=True)
        return out
    out = ROOT / "dist" / (base + ".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        if src.is_file():
            z.write(src, src.name)
        else:
            for f in src.rglob("*"):
                z.write(f, Path(src.name) / f.relative_to(src))
    return out


def appimage(onefile, version):
    """Linux: un .AppImage (un solo archivo que corre en casi cualquier distro). Necesita appimagetool."""
    tool = shutil.which("appimagetool") or shutil.which("appimagetool-x86_64.AppImage")
    if not tool:
        print("Para el .AppImage hace falta appimagetool: https://github.com/AppImage/appimagetool/releases\n"
              "(bájalo, dale permiso de ejecución y ponlo en tu PATH). Se salta el AppImage.")
        return None
    if onefile:
        print("El .AppImage se arma desde la carpeta: corre sin --onefile. Se salta el AppImage.")
        return None
    if not shutil.which("file"):
        print("appimagetool necesita el comando «file», que no está instalado. Instálalo y vuelve a correr:\n"
              "  Manjaro / Arch:   sudo pacman -S file\n"
              "  Ubuntu / Mint:    sudo apt install file\n"
              "  Fedora:           sudo dnf install file\n"
              "Se salta el AppImage (la carpeta y el .tar.gz sí quedaron).")
        return None
    src = built_path("linux", False)
    appdir = ROOT / "dist" / "AppDir"
    shutil.rmtree(appdir, ignore_errors=True)
    shutil.copytree(src, appdir / "usr" / "bin")
    (appdir / "AppRun").write_text('#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\n'
                                   f'exec "$HERE/usr/bin/{APP}" "$@"\n')
    (appdir / "AppRun").chmod(0o755)
    (appdir / f"{APP}.desktop").write_text(
        f"[Desktop Entry]\nType=Application\nName={PRETTY}\nExec={APP} %f\nIcon={APP}\n"
        "Categories=Graphics;Development;\nTerminal=false\n")
    shutil.copy(ROOT / "icon.png", appdir / f"{APP}.png")
    out = ROOT / "dist" / f"{APP}-{version}-linux-{arch()}.AppImage"
    env = dict(os.environ, ARCH=platform.machine(), APPIMAGE_EXTRACT_AND_RUN="1")
    say("appimagetool")
    try:
        subprocess.run([tool, str(appdir), str(out)], check=True, env=env)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"appimagetool falló ({e}). Mira el mensaje de arriba. Se salta el AppImage "
              "(la carpeta y el .tar.gz sí quedaron).")
        shutil.rmtree(appdir, ignore_errors=True)
        return None
    out.chmod(out.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shutil.rmtree(appdir, ignore_errors=True)
    return out


def main():
    ap = argparse.ArgumentParser(description="Arma el ejecutable del editor para este sistema.")
    ap.add_argument("--onefile", action="store_true", help="un solo archivo en vez de una carpeta")
    ap.add_argument("--appimage", action="store_true", help="Linux: también un .AppImage")
    ap.add_argument("--version", default=datetime.date.today().strftime("%Y.%m.%d"),
                    help="versión en el nombre de los archivos (por defecto, la fecha de hoy)")
    a = ap.parse_args()
    version = a.version.lstrip("vV") or "dev"
    osn = os_name()
    say(f"Sistema: {osn} {arch()} · Python {platform.python_version()} · versión {version}")
    check_tools()
    work = ROOT / "build" / "pyinstaller"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    pyinstaller(osn, a.onefile, work)
    outs = [package(osn, a.onefile, version)]
    if a.appimage and osn == "linux":
        outs.append(appimage(a.onefile, version))
    say("Listo")
    print(f"  Programa: {built_path(osn, a.onefile)}")
    for o in outs:
        if o:
            print(f"  Para compartir: {o}")
    if osn == "macos":
        print("  macOS: como no está firmado, la primera vez ábrelo con clic derecho → Abrir.")


if __name__ == "__main__":
    main()
