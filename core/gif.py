"""GIF animado (sin librerías extra): cuadros de índices + una paleta, índice 0 transparente."""
import struct

import numpy as np


def _lzw(indices, min_code=8):
    clear, end = 1 << min_code, (1 << min_code) + 1
    out = bytearray()
    bitbuf = nbits = 0
    code_size = min_code + 1
    table = {bytes((i,)): i for i in range(1 << min_code)}
    nxt = end + 1

    def emit(code):
        nonlocal bitbuf, nbits
        bitbuf |= code << nbits
        nbits += code_size
        while nbits >= 8:
            out.append(bitbuf & 255)
            bitbuf >>= 8
            nbits -= 8
    emit(clear)
    data = bytes(indices)
    w = b""
    for b in data:
        wc = w + bytes((b,))
        if wc in table:
            w = wc
            continue
        emit(table[w])
        if nxt < 4096:
            table[wc] = nxt
            nxt += 1
            if nxt > (1 << code_size) and code_size < 12:
                code_size += 1
        else:
            emit(clear)
            table = {bytes((i,)): i for i in range(1 << min_code)}
            nxt = end + 1
            code_size = min_code + 1
        w = bytes((b,))
    if w:
        emit(table[w])
    emit(end)
    if nbits:
        out.append(bitbuf & 255)
    blocks = bytearray()
    for i in range(0, len(out), 255):
        chunk = out[i:i + 255]
        blocks.append(len(chunk))
        blocks += chunk
    blocks.append(0)
    return bytes(blocks)


def write_gif(path, frames, palette_rgb, delays_cs, loop=True):
    """frames: lista de arreglos (h, w) uint8 del mismo tamaño; palette_rgb: 256×3; delays en centésimas."""
    h, w = frames[0].shape
    pal = np.zeros((256, 3), np.uint8)
    pal[:len(palette_rgb)] = np.array(palette_rgb, np.uint8)[:256]
    out = bytearray(b"GIF89a")
    out += struct.pack("<HHBBB", w, h, 0xF7, 0, 0)
    out += pal.tobytes()
    if loop:
        out += b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00"
    for fr, d in zip(frames, delays_cs):
        out += b"\x21\xF9\x04" + struct.pack("<BHBB", 0x09, max(2, int(d)), 0, 0)  # quitar el cuadro anterior, transparente 0
        out += b"\x2C" + struct.pack("<HHHHB", 0, 0, w, h, 0)
        out += bytes((8,)) + _lzw(np.ascontiguousarray(fr, np.uint8).ravel())
    out += b"\x3B"
    with open(path, "wb") as f:
        f.write(out)
