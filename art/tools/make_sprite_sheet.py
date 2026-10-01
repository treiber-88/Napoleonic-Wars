"""
Convert Blender sprite renders into an OpenRA indexed PNG sprite sheet (Red Alert palette).

Renders are RGBA at SCALE x the final frame width (and sqrt(2) shorter: they are stretched back to
square here, which gives Red Alert's projection), with a transparent film and a shadow catcher:
  - model pixels are opaque,
  - shadow pixels are black with partial alpha,
  - pure magenta surfaces mark player colour (remapped to RA indices 80-95).

Usage:
  python make_sprite_sheet.py <render_dir> <prefix> <out.png> [--frame 32] [--scale 4]
    reads <render_dir>/<prefix>_00.png, _01.png, ... in order.
"""

import argparse
import glob
import os

import numpy as np
from PIL import Image, PngImagePlugin

PALETTE_FILE = r"C:\Program Files\CnCTools\OS SHP Builder\Palettes\RA1\temperat.pal"
TRANSPARENT = 0
SHADOW = 4
REMAP = list(range(80, 96))          # player colour ramp, 80 = brightest
RESERVED = {0, 1, 2, 3, 4} | set(REMAP)


def load_palette():
    raw = open(PALETTE_FILE, "rb").read()
    return np.array([[raw[i * 3] * 4, raw[i * 3 + 1] * 4, raw[i * 3 + 2] * 4] for i in range(256)], dtype=np.float32)


def convert_frame(img, frame, scale, pal, usable):
    img = img.convert("RGBA")
    size = frame * scale
    if img.size != (size, size):
        # Renders are made sqrt(2) short vertically (RA projection); stretch back to square.
        img = img.resize((size, size), Image.BILINEAR)
    a = np.asarray(img, dtype=np.float32) / 255.0
    h, w = frame, frame
    a = a.reshape(h, scale, w, scale, 4).transpose(0, 2, 1, 3, 4).reshape(h, w, scale * scale, 4)
    rgb, alpha = a[..., :3], a[..., 3]

    solid = alpha > 0.95
    shadow = (alpha > 0.30) & ~solid
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    magenta = solid & (r > 0.2) & (b > 0.2) & (g < 0.45 * np.minimum(r, b))

    n = scale * scale
    solid_frac = solid.sum(-1) / n
    shadow_frac = (solid | shadow).sum(-1) / n
    magenta_frac = magenta.sum(-1) / np.maximum(solid.sum(-1), 1)

    out = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            if solid_frac[y, x] >= 0.25:
                px = rgb[y, x][solid[y, x]] * 255.0
                if magenta_frac[y, x] >= 0.35:
                    m = rgb[y, x][magenta[y, x]]
                    v = float(np.clip(np.maximum(m[:, 0], m[:, 2]).mean() / 0.9, 0, 1))
                    out[y, x] = REMAP[int(round((1 - v) * (len(REMAP) - 1)))]
                else:
                    c = px.mean(0)
                    d = ((pal[usable] - c) ** 2 * np.array([0.3, 0.59, 0.11])).sum(1)
                    out[y, x] = usable[int(d.argmin())]
            elif shadow_frac[y, x] >= 0.6:
                out[y, x] = SHADOW
            else:
                out[y, x] = TRANSPARENT
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("render_dir")
    ap.add_argument("prefix")
    ap.add_argument("out")
    ap.add_argument("--frame", type=int, default=32)
    ap.add_argument("--scale", type=int, default=4)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.render_dir, f"{args.prefix}_[0-9]*.png")))
    if not files:
        raise SystemExit("no frames found")

    pal = load_palette()
    usable = np.array([i for i in range(256) if i not in RESERVED])
    frames = [convert_frame(Image.open(f), args.frame, args.scale, pal, usable) for f in files]

    sheet = np.concatenate(frames, axis=1)
    img = Image.fromarray(sheet, mode="P")
    img.putpalette(pal.astype(np.uint8).flatten().tolist())

    info = PngImagePlugin.PngInfo()
    info.add_text("FrameSize", f"{args.frame},{args.frame}")
    info.add_text("FrameAmount", str(len(frames)))
    img.save(args.out, pnginfo=info, transparency=TRANSPARENT)
    print(f"{args.out}: {len(frames)} frames of {args.frame}x{args.frame}")


if __name__ == "__main__":
    main()
