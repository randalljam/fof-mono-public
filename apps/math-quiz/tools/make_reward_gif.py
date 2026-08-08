#!/usr/bin/env python3
"""Generate the dev placeholder reward GIF for targeted-practice bursts.

This is a stand-in "lightweight animation / reward moment" shown on the break
screen between bursts (docs/2026-06-23_targeted-fluency-practice-todos.md). Swap
the output file for the real (Pipa) animation later — keep the same path so no
code changes are needed: apps/math-quiz/rewards/example-reward.gif.

No third-party deps (the repo venv isn't required). Writes a small looping
GIF89a using the byte-aligned "uncompressed GIF" encoding (min-code-size 7 ->
8-bit, byte-aligned codes; a Clear code every 100 pixels keeps the code width
fixed so no LZW table-growth bookkeeping is needed and any decoder reads it).
"""
import math
import os
import struct

### Config
SIZE = 48          # square px
FRAMES = 8
DELAY_CS = 12      # per-frame delay in centiseconds (~0.12s)
OUT = os.path.join(os.path.dirname(__file__), '..', 'rewards', 'example-reward.gif')

### Palette: index 0 = background, 1..N = a cheerful ramp (gold -> pink -> blue).
PALETTE = [
    (255, 248, 230),   # 0 warm background
    (255, 209, 102),   # 1 gold
    (255, 159, 67),    # 2 orange
    (255, 107, 129),   # 3 pink
    (165, 94, 234),    # 4 purple
    (72, 219, 251),    # 5 cyan
    (46, 213, 115),    # 6 green
    (255, 255, 255),   # 7 white sparkle
]

### Helpers: frame pixels
def frame_indices(f):
    """Return SIZE*SIZE palette indices for frame f — a pulsing radial sparkle."""
    cx = cy = (SIZE - 1) / 2.0
    maxr = math.hypot(cx, cy)
    phase = f / FRAMES
    out = []
    for y in range(SIZE):
        for x in range(SIZE):
            r = math.hypot(x - cx, y - cy) / maxr      # 0..1 from center
            # rings that move outward each frame; a bright core that pulses
            band = (r * 6 - phase * 6) % 6
            if r < 0.12 + 0.05 * math.sin(phase * 2 * math.pi):
                out.append(7)                          # white core
            elif r > 0.96:
                out.append(0)                          # background corners
            else:
                out.append(1 + int(band) % 6)          # 1..6 colored ring
    return out

### Helpers: GIF assembly
def image_data_block(indices, mcs=7):
    """Byte-aligned uncompressed-GIF image data (LZW min code size `mcs`)."""
    clear = 1 << mcs                                   # 128
    end = clear + 1                                    # 129
    codes = bytearray([clear])
    count = 0
    for v in indices:
        codes.append(v)                                # v must be < clear (128)
        count += 1
        if count >= 100:                               # clear well before the table grows
            codes.append(clear)
            count = 0
    codes.append(end)
    out = bytearray([mcs])
    i = 0
    while i < len(codes):
        chunk = codes[i:i + 255]
        out.append(len(chunk))
        out += chunk
        i += 255
    out.append(0)                                      # block terminator
    return bytes(out)
def build_gif():
    g = bytearray()
    g += b'GIF89a'
    # Logical screen descriptor: global color table, 8 entries -> size field 2 (2^(2+1)=8).
    g += struct.pack('<HH', SIZE, SIZE)
    g += bytes([0b1_001_0_010, 0, 0])                  # GCT flag, color res 2, sort 0, size 2
    for (r, gn, b) in PALETTE:
        g += bytes([r, gn, b])
    # NETSCAPE2.0 loop-forever extension.
    g += b'\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00'
    for f in range(FRAMES):
        g += b'\x21\xF9\x04\x00' + struct.pack('<H', DELAY_CS) + b'\x00\x00'  # graphic control
        g += b'\x2C' + struct.pack('<HHHH', 0, 0, SIZE, SIZE) + bytes([0])     # image descriptor
        g += image_data_block(frame_indices(f))
    g += b'\x3B'                                        # trailer
    return bytes(g)

def main():
    data = build_gif()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as fh:
        fh.write(data)
    print(f'wrote {os.path.relpath(OUT)} ({len(data)} bytes, {FRAMES} frames, {SIZE}x{SIZE})')

if __name__ == '__main__':
    main()
