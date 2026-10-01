"""
Turn Blender icon renders (RGBA, 4:3) into 64x48 OpenRA sidebar icons in the Red Alert "chrome" palette.
The subject is composited over a dark, softly lit backdrop, reduced with a high-quality filter and matched to
the palette, avoiding the transparent (0), shadow (3, 4) and player-remap (80-95) indices.

Usage: python make_icon.py <render.png> <out.png> [--flag <nation>]
--flag adds that nation's flag (from the in-game flag sheet) as a small badge in the top-left corner.
"""
import sys

import numpy as np
from PIL import Image

PALETTE_FILE = r"C:\Program Files\CnCTools\OS SHP Builder\Palettes\RA1\temperat.pal"
RESERVED = {0, 1, 2, 3, 4} | set(range(80, 96))
W, H = 64, 48
FLAG_SHEET = "D:/Napoleonic Wars/mods/napoleonic/uibits/nwflags-3x.png"
FLAGS = ["france", "england", "russia", "prussia", "austria"]


def palette():
    raw = open(PALETTE_FILE, "rb").read()
    return np.array([[raw[i * 3] * 4, raw[i * 3 + 1] * 4, raw[i * 3 + 2] * 4] for i in range(256)], dtype=np.float32)


def backdrop(w, h):
    """Flat dark olive: a gradient bands badly in the 8-bit palette."""
    return Image.new("RGBA", (w, h), (52, 58, 46, 255))


def flag_badge(bg, nation):
    """Paste the nation's flag (90x45 cell on the 3x sheet) into the top-left corner with a dark border."""
    i = FLAGS.index(nation)
    flag = Image.open(FLAG_SHEET).convert("RGBA").crop((i * 90, 0, i * 90 + 90, 45))
    w = bg.width * 22 // W
    h = w // 2
    border = Image.new("RGBA", (w + 8, h + 8), (20, 20, 16, 255))
    bg.alpha_composite(border, (4, 4))
    bg.alpha_composite(flag.resize((w, h), Image.LANCZOS), (8, 8))


def main():
    args = sys.argv[1:]
    nation = None
    if "--flag" in args:
        k = args.index("--flag")
        nation = args[k + 1]
        del args[k:k + 2]
    src, out = args
    im = Image.open(src).convert("RGBA")
    bg = backdrop(*im.size)
    bg.alpha_composite(im)
    if nation:
        flag_badge(bg, nation)
    small = bg.convert("RGB").resize((W, H), Image.LANCZOS)
    pal = palette()
    usable = np.array([i for i in range(256) if i not in RESERVED])
    px = np.asarray(small, dtype=np.float32).reshape(-1, 3)
    d = (((pal[usable][None, :, :] - px[:, None, :]) ** 2) * np.array([0.3, 0.59, 0.11])).sum(-1)
    idx = usable[d.argmin(1)].astype(np.uint8).reshape(H, W)
    img = Image.fromarray(idx, "P")
    img.putpalette(pal.astype(np.uint8).flatten().tolist())
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
