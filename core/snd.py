"""Sonidos de MUGEN / IKEMEN GO (.snd): cada sonido es un WAV con grupo y número."""
import struct
from pathlib import Path

from i18n import tr

SIG = b"ElecbyteSnd\0"


class Sound:
    def __init__(self, group, number, data):
        self.group, self.number, self.data = int(group), int(number), bytes(data)

    @property
    def key(self):
        return (self.group, self.number)

    def info(self):
        """(segundos, frecuencia, canales, bits) o None si no es un WAV normal."""
        d = self.data
        if d[:4] != b"RIFF" or d[8:12] != b"WAVE":
            return None
        pos, fmt = 12, None
        while pos + 8 <= len(d):
            cid, size = d[pos:pos + 4], struct.unpack_from("<I", d, pos + 4)[0]
            if cid == b"fmt ":
                _af, ch, rate, _br, _ba, bits = struct.unpack_from("<HHIIHH", d, pos + 8)
                fmt = (ch, rate, bits)
            elif cid == b"data" and fmt:
                ch, rate, bits = fmt
                secs = size / max(1, rate * ch * max(1, bits // 8))
                return secs, rate, ch, bits
            pos += 8 + size + (size & 1)
        return None


class SndFile:
    def __init__(self):
        self.path = None
        self.sounds = []
        self.modified = False
        self.version = bytes((4, 0, 0, 0))

    @classmethod
    def load(cls, path):
        f = cls()
        f.path = Path(path)
        d = f.path.read_bytes()
        if d[:12] != SIG:
            raise ValueError(tr('no es un archivo SND'))
        f.version = d[12:16]
        n, ofs = struct.unpack_from("<II", d, 16)
        for _ in range(n):
            if ofs <= 0 or ofs + 16 > len(d):
                break
            nxt, size, g, num = struct.unpack_from("<IIII", d, ofs)
            f.sounds.append(Sound(g, num, d[ofs + 16:ofs + 16 + size]))
            if nxt <= ofs:
                break
            ofs = nxt
        return f

    def find(self, group, number):
        return next((s for s in self.sounds if s.group == group and s.number == number), None)

    def save(self, path=None):
        path = Path(path or self.path)
        header = bytearray(512)
        header[:12] = SIG
        header[12:16] = self.version
        struct.pack_into("<II", header, 16, len(self.sounds), 512 if self.sounds else 0)
        body, ofs = bytearray(), 512
        for i, s in enumerate(self.sounds):
            nxt = ofs + 16 + len(s.data) if i < len(self.sounds) - 1 else 0
            body += struct.pack("<IIII", nxt, len(s.data), s.group, s.number) + s.data
            ofs += 16 + len(s.data)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(bytes(header) + bytes(body))
        tmp.replace(path)
        self.path = path
        self.modified = False
