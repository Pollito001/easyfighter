"""Pasar cualquier audio (OGG, MP3, FLAC…) a un WAV que IKEMEN GO pueda tocar desde el .snd.

Los sonidos del personaje (.snd) solo pueden ser WAV: IKEMEN GO decodifica cada sonido del .snd como WAV
(la música, en cambio, sí puede ser OGG, MP3, FLAC…). Así que al poner un sonido de otro formato el editor lo
convierte a WAV PCM de 16 bits, el más compatible (también con MUGEN). Usa ffmpeg si está instalado y si no,
el decodificador que trae PyQt6 (QtMultimedia)."""
import shutil
import struct
import subprocess

from core.sysenv import clean_env
from pathlib import Path

EXTS = [".wav", ".ogg", ".mp3", ".flac", ".opus", ".m4a", ".aac", ".wma", ".aiff", ".aif"]
FILTER = "Audio (" + " ".join("*" + e for e in EXTS) + ")"
MAX_RATE = 48000
_NOWIN = {"creationflags": 0x08000000} if __import__("os").name == "nt" else {}   # sin ventana negra en Windows


class AudioError(Exception):
    pass


def wav_format(data):
    """(formato, canales, frecuencia, bits) de un WAV, o None si no es WAV."""
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        if cid == b"fmt " and pos + 24 <= len(data):
            af, ch, rate, _br, _ba, bits = struct.unpack_from("<HHIIHH", data, pos + 8)
            return af, ch, rate, bits
        pos += 8 + size + (size & 1)
    return None


def is_good_wav(data):
    """¿Ya es un WAV PCM de 8 o 16 bits (lo que toca bien cualquier motor)?"""
    f = wav_format(data)
    return bool(f and f[0] == 1 and f[3] in (8, 16) and 1 <= f[1] <= 2 and f[2] <= MAX_RATE)


def make_wav(pcm, channels, rate):
    """Arma un WAV PCM 16 bits con estos datos."""
    return (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE" +
            b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, rate, rate * channels * 2, channels * 2, 16) +
            b"data" + struct.pack("<I", len(pcm)) + pcm)


def _ffmpeg(path):
    exe = shutil.which("ffmpeg")
    if not exe:
        return None
    cmd = [exe, "-v", "error", "-nostdin", "-i", str(path), "-vn", "-acodec", "pcm_s16le", "-ac", "2",
           "-f", "wav", "-"]
    # mono si el original es mono
    probe = shutil.which("ffprobe")
    if probe:
        try:
            out = subprocess.run([probe, "-v", "error", "-select_streams", "a:0", "-show_entries",
                                  "stream=channels,sample_rate", "-of", "csv=p=0", str(path)],
                                 capture_output=True, timeout=30, env=clean_env(), **_NOWIN).stdout.decode().strip().split(",")
            rate, ch = int(out[0]), int(out[1])
            cmd[cmd.index("-ac") + 1] = "1" if ch == 1 else "2"
            if rate > MAX_RATE:
                cmd[-3:-3] = ["-ar", "44100"]
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            pass
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120, env=clean_env(), **_NOWIN)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.startswith(b"RIFF"):
        return None
    return _fix_sizes(r.stdout)


def _fix_sizes(data):
    """ffmpeg escribiendo a una tubería deja los tamaños del WAV en 0xFFFFFFFF: se arreglan."""
    f = wav_format(data)
    if not f:
        return data
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        if cid == b"data":
            pcm = data[pos + 8:]
            if size <= len(pcm):
                pcm = pcm[:size]
            pcm = pcm[:len(pcm) - len(pcm) % (f[1] * 2)]
            return make_wav(pcm, f[1], f[2])
        pos += 8 + size + (size & 1)
    return data


def _qt(path):
    """Con el decodificador de QtMultimedia (sin ffmpeg instalado)."""
    try:
        from PyQt6.QtCore import QEventLoop, QTimer, QUrl
        from PyQt6.QtMultimedia import QAudioDecoder, QAudioFormat
    except ImportError:
        return None
    dec = QAudioDecoder()
    fmt = QAudioFormat()
    fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    dec.setAudioFormat(fmt)
    dec.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
    chunks = []
    info = {}
    loop = QEventLoop()

    def ready():
        buf = dec.read()
        if buf.isValid():
            f = buf.format()
            info.setdefault("ch", f.channelCount())
            info.setdefault("rate", f.sampleRate())
            info.setdefault("fmt", f.sampleFormat())
            chunks.append(bytes(buf.constData().asstring(buf.byteCount())))

    def fail(*_a):
        info["error"] = dec.errorString()
        loop.quit()

    dec.bufferReady.connect(ready)
    dec.finished.connect(loop.quit)
    dec.error.connect(fail)
    QTimer.singleShot(120000, loop.quit)
    dec.start()
    loop.exec()
    dec.stop()
    if not chunks or "error" in info:
        return None
    import numpy as np
    raw = b"".join(chunks)
    sf = info.get("fmt")
    if sf == QAudioFormat.SampleFormat.Float:
        a = np.frombuffer(raw[:len(raw) // 4 * 4], dtype="<f4")
        a = (np.clip(a, -1, 1) * 32767).astype("<i2")
    elif sf == QAudioFormat.SampleFormat.Int32:
        a = (np.frombuffer(raw[:len(raw) // 4 * 4], dtype="<i4") >> 16).astype("<i2")
    elif sf == QAudioFormat.SampleFormat.UInt8:
        a = ((np.frombuffer(raw, dtype="u1").astype("<i2") - 128) << 8).astype("<i2")
    else:
        a = np.frombuffer(raw[:len(raw) // 2 * 2], dtype="<i2")
    ch, rate = max(1, info.get("ch", 1)), info.get("rate", 44100)
    if ch > 2:
        a = a[:len(a) // ch * ch].reshape(-1, ch)[:, :2].reshape(-1)
        ch = 2
    if rate > MAX_RATE:
        frames = a[:len(a) // ch * ch].reshape(-1, ch)
        idx = (np.arange(int(len(frames) * 44100 / rate)) * rate / 44100).astype(int)
        a, rate = frames[np.clip(idx, 0, len(frames) - 1)].reshape(-1), 44100
    return make_wav(a.astype("<i2").tobytes(), ch, rate)


def to_wav(path):
    """Los bytes de un WAV listo para el .snd. Un WAV que ya sirve se deja tal cual."""
    path = Path(path)
    data = path.read_bytes()
    if is_good_wav(data):
        return data
    out = _ffmpeg(path) or _qt(path)
    if not out:
        raise AudioError(path.name)
    return out
