#!/usr/bin/env python3
"""
Generate a Minecraft skin (64x64 PNG) of a pink dragon.
Minecraft Java Edition skin layout (64x64):

Head (8x8 per face):
  Top:    (8,0)-(15,7)
  Bottom: (16,0)-(23,7)
  Right:  (0,8)-(7,15)
  Front:  (8,8)-(15,15)
  Left:   (16,8)-(23,15)
  Back:   (24,8)-(31,15)

Hat/Overlay (8x8 per face):
  Top:    (40,0)-(47,7)
  Bottom: (48,0)-(55,7)
  Right:  (32,8)-(39,15)
  Front:  (40,8)-(47,15)
  Left:   (48,8)-(55,15)
  Back:   (56,8)-(63,15)

Body (8w x 12h per face):
  Top:    (20,16)-(27,19)
  Bottom: (28,16)-(35,19)
  Right:  (16,20)-(19,31)
  Front:  (20,20)-(27,31)
  Left:   (28,20)-(31,31)
  Back:   (32,20)-(39,31)

Right Arm (4w x 12h):
  Top:    (44,16)-(47,19)
  Bottom: (48,16)-(51,19)
  Right:  (40,20)-(43,31)  (outer)
  Front:  (44,20)-(47,31)
  Left:   (48,20)-(51,31)
  Back:   (52,20)-(55,31)

Right Leg (4w x 12h):
  Top:    (4,16)-(7,19)
  Bottom: (8,16)-(11,19)
  Right:  (0,20)-(3,31)   (outer)
  Front:  (4,20)-(7,31)
  Left:   (8,20)-(11,31)
  Back:   (12,20)-(15,31)

Left Leg (4w x 12h):
  Top:    (20,48)-(23,51)
  Bottom: (24,48)-(27,51)
  Right:  (16,52)-(19,63)
  Front:  (20,52)-(23,63)
  Left:   (24,52)-(27,63)
  Back:   (28,52)-(31,63)

Left Arm (4w x 12h):
  Top:    (36,48)-(39,51)
  Bottom: (40,48)-(43,51)
  Right:  (32,52)-(35,63)
  Front:  (36,52)-(39,63)
  Left:   (40,52)-(43,63)
  Back:   (44,52)-(47,63)

Body overlay, arm overlays, leg overlays exist too (same size, offset).
"""

from PIL import Image

# Create a 64x64 RGBA image (transparent background)
skin = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
px = skin.load()

# === COLOR PALETTE (from the dragon image) ===
# Pinks/Magentas
DARK_PINK     = (140, 30, 70, 255)    # darkest shadow/outline
MED_DARK_PINK = (170, 45, 85, 255)    # dark scale shadow
MED_PINK      = (200, 70, 110, 255)   # mid-tone scales
PINK          = (220, 100, 140, 255)  # main body pink
LIGHT_PINK    = (240, 140, 170, 255)  # highlights
PALE_PINK     = (250, 180, 200, 255)  # bright highlights
HOT_PINK      = (230, 60, 120, 255)   # vivid accent

# Deep purples for shadows
DEEP_PURPLE   = (80, 15, 50, 255)     # deepest shadow
DARK_PURPLE   = (100, 20, 60, 255)    # dark shadow

# Eyes
EYE_YELLOW    = (255, 220, 50, 255)   # bright eye color
EYE_ORANGE    = (255, 160, 30, 255)   # eye edge
EYE_RED       = (200, 40, 40, 255)    # eye slit/pupil
EYE_WHITE     = (255, 240, 200, 255)  # eye highlight

# Teeth/mouth
WHITE         = (240, 235, 230, 255)  # teeth
MOUTH_DARK    = (60, 10, 30, 255)     # inside mouth

# Transparent
T = (0, 0, 0, 0)

def fill_rect(x0, y0, w, h, color):
    for yy in range(y0, y0 + h):
        for xx in range(x0, x0 + w):
            if 0 <= xx < 64 and 0 <= yy < 64:
                px[xx, yy] = color

def set_pixels(x0, y0, pixel_rows):
    """Set pixels from a 2D list of colors. None = skip (transparent)."""
    for r, row in enumerate(pixel_rows):
        for c, color in enumerate(row):
            if color is not None:
                xx, yy = x0 + c, y0 + r
                if 0 <= xx < 64 and 0 <= yy < 64:
                    px[xx, yy] = color

# Short aliases for the pixel art
DP = DARK_PINK
MP = MED_PINK
MDP = MED_DARK_PINK
PK = PINK
LP = LIGHT_PINK
PP = PALE_PINK
HP = HOT_PINK
DPR = DEEP_PURPLE
DKP = DARK_PURPLE
EY = EYE_YELLOW
EO = EYE_ORANGE
ER = EYE_RED
EW = EYE_WHITE
WH = WHITE
MD = MOUTH_DARK

# ============================================================
# HEAD - FRONT FACE (8x8) at (8, 8)
# This is the dragon face - the most important part!
# Layout: horns on top, dragon eyes (not dots!), snout, fangs
# ============================================================
head_front = [
    # Row 0: horn tips
    [MDP, DP,  LP,  PK,  PK,  LP,  DP,  MDP],
    # Row 1: horn bases / forehead
    [DP,  MDP, MP,  PK,  PK,  MP,  MDP, DP ],
    # Row 2: brow ridge
    [MDP, MP,  DP,  PK,  PK,  DP,  MP,  MDP],
    # Row 3: EYES - distinctive dragon eyes (yellow/orange with red slit)
    [MDP, EO,  EY,  ER,  ER,  EY,  EO,  MDP],
    # Row 4: under eyes / snout top
    [DP,  MP,  PK,  LP,  LP,  PK,  MP,  DP ],
    # Row 5: snout / nostrils
    [MDP, PK,  DKP, LP,  LP,  DKP, PK,  MDP],
    # Row 6: mouth with fangs
    [DP,  WH,  MD,  MD,  MD,  MD,  WH,  DP ],
    # Row 7: chin / jaw
    [DPR, DP,  MDP, MP,  MP,  MDP, DP,  DPR],
]
set_pixels(8, 8, head_front)

# HEAD - TOP (8x8) at (8, 0) - top of the head with horns/ridges
head_top = [
    [DPR, DP,  MDP, MP,  MP,  MDP, DP,  DPR],
    [DP,  MDP, MP,  PK,  PK,  MP,  MDP, DP ],
    [MDP, MP,  PK,  LP,  LP,  PK,  MP,  MDP],
    [MP,  PK,  LP,  PK,  PK,  LP,  PK,  MP ],
    [MP,  PK,  PK,  LP,  LP,  PK,  PK,  MP ],
    [MDP, MP,  PK,  PK,  PK,  PK,  MP,  MDP],
    [DP,  MDP, MP,  PK,  PK,  MP,  MDP, DP ],
    [DPR, DP,  MDP, MP,  MP,  MDP, DP,  DPR],
]
set_pixels(8, 0, head_top)

# HEAD - BOTTOM (8x8) at (16, 0) - underside of jaw
head_bottom = [
    [DPR, DP,  MDP, MDP, MDP, MDP, DP,  DPR],
    [DP,  MDP, DP,  DP,  DP,  DP,  MDP, DP ],
    [MDP, DP,  MDP, MDP, MDP, MDP, DP,  MDP],
    [MDP, DP,  MDP, DKP, DKP, MDP, DP,  MDP],
    [MDP, DP,  MDP, DKP, DKP, MDP, DP,  MDP],
    [MDP, DP,  MDP, MDP, MDP, MDP, DP,  MDP],
    [DP,  MDP, DP,  DP,  DP,  DP,  MDP, DP ],
    [DPR, DP,  MDP, MDP, MDP, MDP, DP,  DPR],
]
set_pixels(16, 0, head_bottom)

# HEAD - RIGHT SIDE (8x8) at (0, 8)
head_right = [
    [DPR, DP,  MDP, MP,  PK,  MP,  MDP, DP ],
    [DP,  MDP, MP,  PK,  LP,  PK,  MP,  MDP],
    [MDP, MP,  DP,  PK,  PK,  PK,  MP,  MDP],
    [MDP, EO,  EY,  ER,  MP,  PK,  MP,  DP ],
    [DP,  MP,  PK,  LP,  PK,  MP,  MDP, DP ],
    [MDP, PK,  DKP, PK,  MP,  MDP, DP,  DPR],
    [DP,  WH,  MD,  MD,  MDP, DP,  DPR, DPR],
    [DPR, DP,  MDP, MDP, DP,  DPR, DPR, DPR],
]
set_pixels(0, 8, head_right)

# HEAD - LEFT SIDE (8x8) at (16, 8)
head_left = [
    [DP,  MDP, MP,  PK,  MP,  MDP, DP,  DPR],
    [MDP, MP,  PK,  LP,  PK,  MP,  MDP, DP ],
    [MDP, MP,  PK,  PK,  PK,  DP,  MP,  MDP],
    [DP,  MP,  PK,  MP,  ER,  EY,  EO,  MDP],
    [DP,  MDP, MP,  PK,  LP,  PK,  MP,  DP ],
    [DPR, DP,  MDP, MP,  PK,  DKP, PK,  MDP],
    [DPR, DPR, DP,  MDP, MD,  MD,  WH,  DP ],
    [DPR, DPR, DPR, DP,  MDP, MDP, DP,  DPR],
]
set_pixels(16, 8, head_left)

# HEAD - BACK (8x8) at (24, 8) - back of head with scale ridges
head_back = [
    [DPR, DP,  MDP, HP,  HP,  MDP, DP,  DPR],
    [DP,  MDP, MP,  HP,  HP,  MP,  MDP, DP ],
    [MDP, MP,  PK,  MDP, MDP, PK,  MP,  MDP],
    [MP,  PK,  LP,  PK,  PK,  LP,  PK,  MP ],
    [MDP, MP,  PK,  LP,  LP,  PK,  MP,  MDP],
    [DP,  MDP, MP,  PK,  PK,  MP,  MDP, DP ],
    [MDP, DP,  MDP, MP,  MP,  MDP, DP,  MDP],
    [DPR, MDP, DP,  MDP, MDP, DP,  MDP, DPR],
]
set_pixels(24, 8, head_back)

# ============================================================
# HAT/OVERLAY LAYER - adds horns and extra detail on top
# Front overlay at (40, 8)
# ============================================================
hat_front = [
    [HP,  T,   T,   T,   T,   T,   T,   HP ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   LP,  T,   T,   LP,  T,   T  ],
    [T,   T,   EW,  T,   T,   EW,  T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   WH,  T,   T,   WH,  T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
]
set_pixels(40, 8, hat_front)

# Hat top overlay at (40, 0) - horn spikes
hat_top = [
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   HP,  HP,  T,   T,   T  ],
    [T,   T,   HP,  T,   T,   HP,  T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
]
set_pixels(40, 0, hat_top)

# Hat right overlay at (32, 8)
hat_right = [
    [T,   HP,  T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   EW,  T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
]
set_pixels(32, 8, hat_right)

# Hat left overlay at (48, 8)
hat_left = [
    [T,   T,   T,   T,   T,   T,   HP,  T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   EW,  T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
]
set_pixels(48, 8, hat_left)

# Hat back overlay at (56, 8) - spine ridge
hat_back = [
    [T,   T,   T,   HP,  HP,  T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
    [T,   T,   T,   T,   T,   T,   T,   T  ],
]
set_pixels(56, 8, hat_back)

# ============================================================
# BODY - FRONT (8w x 12h) at (20, 20)
# Dragon chest with scale pattern
# ============================================================
body_front = []
for r in range(12):
    row = []
    for c in range(8):
        # Scale pattern: alternating diamond shapes
        if r < 2:
            # Collar/neckline
            if c in (0, 7):
                row.append(DP)
            elif c in (1, 6):
                row.append(MDP)
            else:
                row.append(MP)
        elif r < 4:
            # Upper chest - lighter belly scales
            if c in (0, 7):
                row.append(MDP)
            elif (r + c) % 2 == 0:
                row.append(LP)
            else:
                row.append(PK)
        elif r < 8:
            # Mid chest - scale diamond pattern
            if c in (0, 7):
                row.append(DP)
            elif (r + c) % 3 == 0:
                row.append(MDP)
            elif (r + c) % 2 == 0:
                row.append(LP)
            else:
                row.append(PK)
        else:
            # Lower belly
            if c in (0, 7):
                row.append(MDP)
            elif (r + c) % 2 == 0:
                row.append(PK)
            else:
                row.append(MP)
    body_front.append(row)
set_pixels(20, 20, body_front)

# BODY - TOP (8w x 4h) at (20, 16)
for r in range(4):
    for c in range(8):
        if c in (0, 7) or r in (0, 3):
            px[20+c, 16+r] = MDP
        elif (r+c) % 2 == 0:
            px[20+c, 16+r] = PK
        else:
            px[20+c, 16+r] = MP

# BODY - BOTTOM (8w x 4h) at (28, 16)
for r in range(4):
    for c in range(8):
        if c in (0, 7) or r in (0, 3):
            px[28+c, 16+r] = DP
        else:
            px[28+c, 16+r] = MDP

# BODY - RIGHT (4w x 12h) at (16, 20)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[16+c, 20+r] = DP
        elif (r+c) % 2 == 0:
            px[16+c, 20+r] = PK
        else:
            px[16+c, 20+r] = MP

# BODY - LEFT (4w x 12h) at (28, 20)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[28+c, 20+r] = DP
        elif (r+c) % 2 == 0:
            px[28+c, 20+r] = PK
        else:
            px[28+c, 20+r] = MP

# BODY - BACK (8w x 12h) at (32, 20) - spine ridge down the back
for r in range(12):
    for c in range(8):
        if c in (3, 4):
            # Spine ridge
            if r % 2 == 0:
                px[32+c, 20+r] = HP
            else:
                px[32+c, 20+r] = MDP
        elif c in (0, 7):
            px[32+c, 20+r] = DP
        elif (r+c) % 2 == 0:
            px[32+c, 20+r] = PK
        else:
            px[32+c, 20+r] = MP

# ============================================================
# RIGHT ARM (4w x 12h)
# ============================================================
# Right arm front at (44, 20)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[44+c, 20+r] = DP
        elif (r+c) % 3 == 0:
            px[44+c, 20+r] = MDP
        elif (r+c) % 2 == 0:
            px[44+c, 20+r] = LP
        else:
            px[44+c, 20+r] = PK

# Right arm top at (44, 16)
for r in range(4):
    for c in range(4):
        px[44+c, 16+r] = MDP if (r+c) % 2 == 0 else PK

# Right arm bottom at (48, 16)
for r in range(4):
    for c in range(4):
        px[48+c, 16+r] = DP if (r+c) % 2 == 0 else MDP

# Right arm outer at (40, 20)
for r in range(12):
    for c in range(4):
        if c == 0:
            px[40+c, 20+r] = DP
        elif (r+c) % 2 == 0:
            px[40+c, 20+r] = PK
        else:
            px[40+c, 20+r] = MP

# Right arm inner at (48, 20)
for r in range(12):
    for c in range(4):
        if c == 3:
            px[48+c, 20+r] = DP
        elif (r+c) % 2 == 0:
            px[48+c, 20+r] = PK
        else:
            px[48+c, 20+r] = MP

# Right arm back at (52, 20)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[52+c, 20+r] = DP
        elif (r+c) % 2 == 0:
            px[52+c, 20+r] = PK
        else:
            px[52+c, 20+r] = MP

# ============================================================
# RIGHT LEG (4w x 12h)
# ============================================================
# Right leg front at (4, 20)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[4+c, 20+r] = DP
        elif (r+c) % 3 == 0:
            px[4+c, 20+r] = MDP
        elif (r+c) % 2 == 0:
            px[4+c, 20+r] = LP
        else:
            px[4+c, 20+r] = PK

# Right leg top at (4, 16)
for r in range(4):
    for c in range(4):
        px[4+c, 16+r] = MDP if (r+c) % 2 == 0 else PK

# Right leg bottom at (8, 16)
for r in range(4):
    for c in range(4):
        px[8+c, 16+r] = DP if (r+c) % 2 == 0 else MDP

# Right leg outer at (0, 20)
for r in range(12):
    for c in range(4):
        if c == 0:
            px[0+c, 20+r] = DP
        elif (r+c) % 2 == 0:
            px[0+c, 20+r] = PK
        else:
            px[0+c, 20+r] = MP

# Right leg inner at (8, 20)
for r in range(12):
    for c in range(4):
        if c == 3:
            px[8+c, 20+r] = DP
        elif (r+c) % 2 == 0:
            px[8+c, 20+r] = PK
        else:
            px[8+c, 20+r] = MP

# Right leg back at (12, 20)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[12+c, 20+r] = DP
        elif (r+c) % 2 == 0:
            px[12+c, 20+r] = PK
        else:
            px[12+c, 20+r] = MP

# ============================================================
# LEFT LEG (4w x 12h) - mirrored
# ============================================================
# Left leg front at (20, 52)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[20+c, 52+r] = DP
        elif (r+c) % 3 == 0:
            px[20+c, 52+r] = MDP
        elif (r+c) % 2 == 0:
            px[20+c, 52+r] = LP
        else:
            px[20+c, 52+r] = PK

# Left leg top at (20, 48)
for r in range(4):
    for c in range(4):
        px[20+c, 48+r] = MDP if (r+c) % 2 == 0 else PK

# Left leg bottom at (24, 48)
for r in range(4):
    for c in range(4):
        px[24+c, 48+r] = DP if (r+c) % 2 == 0 else MDP

# Left leg outer at (16, 52)
for r in range(12):
    for c in range(4):
        if c == 0:
            px[16+c, 52+r] = DP
        elif (r+c) % 2 == 0:
            px[16+c, 52+r] = PK
        else:
            px[16+c, 52+r] = MP

# Left leg inner at (24, 52)
for r in range(12):
    for c in range(4):
        if c == 3:
            px[24+c, 52+r] = DP
        elif (r+c) % 2 == 0:
            px[24+c, 52+r] = PK
        else:
            px[24+c, 52+r] = MP

# Left leg back at (28, 52)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[28+c, 52+r] = DP
        elif (r+c) % 2 == 0:
            px[28+c, 52+r] = PK
        else:
            px[28+c, 52+r] = MP

# ============================================================
# LEFT ARM (4w x 12h) - mirrored
# ============================================================
# Left arm front at (36, 52)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[36+c, 52+r] = DP
        elif (r+c) % 3 == 0:
            px[36+c, 52+r] = MDP
        elif (r+c) % 2 == 0:
            px[36+c, 52+r] = LP
        else:
            px[36+c, 52+r] = PK

# Left arm top at (36, 48)
for r in range(4):
    for c in range(4):
        px[36+c, 48+r] = MDP if (r+c) % 2 == 0 else PK

# Left arm bottom at (40, 48)
for r in range(4):
    for c in range(4):
        px[40+c, 48+r] = DP if (r+c) % 2 == 0 else MDP

# Left arm outer at (32, 52)
for r in range(12):
    for c in range(4):
        if c == 0:
            px[32+c, 52+r] = DP
        elif (r+c) % 2 == 0:
            px[32+c, 52+r] = PK
        else:
            px[32+c, 52+r] = MP

# Left arm inner at (40, 52)
for r in range(12):
    for c in range(4):
        if c == 3:
            px[40+c, 52+r] = DP
        elif (r+c) % 2 == 0:
            px[40+c, 52+r] = PK
        else:
            px[40+c, 52+r] = MP

# Left arm back at (44, 52)
for r in range(12):
    for c in range(4):
        if c == 0 or c == 3:
            px[44+c, 52+r] = DP
        elif (r+c) % 2 == 0:
            px[44+c, 52+r] = PK
        else:
            px[44+c, 52+r] = MP

# ============================================================
# Save the skin
# ============================================================
output_path = "/Users/randytrue/Documents/Code/kid-games/minecraft/pink_dragon_skin.png"
skin.save(output_path)
print(f"Skin saved to: {output_path}")
print(f"Size: {skin.size}")

# Also create a scaled-up preview (16x scale)
preview = skin.resize((64*16, 64*16), Image.NEAREST)
preview_path = "/Users/randytrue/Documents/Code/kid-games/minecraft/pink_dragon_skin_preview.png"
preview.save(preview_path)
print(f"Preview saved to: {preview_path}")
