"""El entorno para abrir otros programas (IKEMEN GO, ffmpeg) desde el ejecutable empaquetado.

PyInstaller y el AppImage cambian variables como LD_LIBRARY_PATH para que el editor use sus propias
bibliotecas. Si IKEMEN GO hereda eso, carga las bibliotecas del editor en vez de las del sistema y puede
fallar (por ejemplo «Installed Vulkan doesn't implement the VK_KHR_surface extension»). Aquí se devuelven
las variables como estaban antes de abrir el editor."""
import os
import sys

# las que PyInstaller guarda con «_ORIG» al cambiarlas
_LIB_VARS = ("LD_LIBRARY_PATH", "LD_PRELOAD", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "LIBPATH")
# las que solo tienen sentido dentro del editor empaquetado
_DROP = ("QT_PLUGIN_PATH", "QML2_IMPORT_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "PYTHONHOME", "PYTHONPATH",
         "GDK_PIXBUF_MODULE_FILE", "GTK_PATH", "GIO_MODULE_DIR", "APPDIR", "APPIMAGE", "ARGV0", "OWD",
         "_MEIPASS2", "_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL")


def packaged():
    return bool(getattr(sys, "frozen", False) or os.environ.get("APPIMAGE") or os.environ.get("APPDIR"))


def clean_env():
    """Copia de os.environ sin lo que agregó el ejecutable empaquetado (igual a os.environ si no lo es)."""
    env = dict(os.environ)
    if not packaged():
        return env
    inside = [x for x in (getattr(sys, "_MEIPASS", None), os.environ.get("APPDIR")) if x]
    for var in _LIB_VARS:
        orig = env.pop(var + "_ORIG", None)
        if orig:
            env[var] = orig
        else:
            env.pop(var, None)
    for var in _DROP:
        env.pop(var, None)
    # y cualquier lista de rutas que apunte adentro del ejecutable (menos PATH, que solo se limpia)
    for var, val in list(env.items()):
        if not inside or not any(p in val for p in inside):
            continue
        parts = [x for x in val.split(os.pathsep) if x and not any(x.startswith(p) for p in inside)]
        if parts:
            env[var] = os.pathsep.join(parts)
        else:
            env.pop(var, None)
    return env
