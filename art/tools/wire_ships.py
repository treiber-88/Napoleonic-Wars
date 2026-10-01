"""
Convert rendered ship classes (art/renders/<image>, 32 facings) into sprite sheets and wire them into the mod:
a sequence per image, and on each actor its image, selection bounds and broadside muzzle positions scaled
to the hull. Only classes whose 32 frames all exist are wired.

Usage: python wire_ships.py
"""
import math
import os
import re
import subprocess
import sys

ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(os.path.dirname(ART), "mods", "napoleonic")
SEQ = os.path.join(MOD, "sequences", "napoleonic.yaml")
SHIPS = os.path.join(MOD, "rules", "ships.yaml")
UNITS_PER_M = 1024 / 12.0     # one cell = 24 px at 2 px/m

# actor: (image, gun-deck length m, half beam m, projectiles per muzzle position)
# Muzzles: 5 per side; projectiles halved from the old 5-position layout so firepower is unchanged.
ACTORS = {
    "FR_BUCENTAURE80": ("fr_bucentaure_class", 59.3, 7.65, 4),
    "FR_OCEAN118": ("fr_ocean_class", 65.2, 8.12, 6),
    "GB_FIRSTRATE104": ("gb_firstrate", 56.7, 7.85, 5),
    "GB_NEPTUNE98": ("gb_neptune_class", 56.0, 7.8, 5),
    "GB_ARROGANT74": ("gb_arrogant_class", 51.2, 7.1, 4),
    "RU_CHESMA100": ("ru_chesma_class", 56.4, 7.8, 5),
    "RU_SELAFAIL74": ("ru_selafail_class", 53.3, 7.3, 4),
    "RU_YAROSLAV74": ("ru_yaroslav_class", 51.8, 7.1, 4),
    "PR_LINE74": ("pr_line74", 51.5, 7.1, 4),
    "PR_TWODECKER50": ("pr_twodecker50", 44.5, 6.1, 3),
    "PR_FRIGATE44": ("pr_frigate44", 45.0, 6.0, 2),
    "AU_VENETIAN74": ("au_venetian74", 50.0, 7.1, 4),
    "AU_VENETIAN64": ("au_venetian64", 46.0, 6.5, 3),
    "AU_FRIGATE44": ("au_frigate44", 43.5, 5.9, 2),
    "TRADESHIP": ("nw_merchantman", 36.0, 5.0, 0),
}


def complete(image):
    d = os.path.join(ART, "renders", image)
    return all(os.path.exists(os.path.join(d, f"idle_{i:02d}.png")) for i in range(32))


NATIONS = {"FR": "france", "GB": "england", "RU": "russia", "PR": "prussia", "AU": "austria"}


def sequence_block(image, actor):
    s = (f"{image}:\n\tidle:\n\t\tFilename: {image}.png\n\t\tFacings: 32\n\t\tOffset: 0,-50\n"
         f"\tmuzzle:\n\t\tFilename: gunfire2.shp\n\t\tLength: 5\n")
    # Icon: the class portrait if one has been made, else the nation's warship icon.
    nation = NATIONS.get(actor[:2])
    if os.path.exists(os.path.join(MOD, "bits", "icons", image + ".png")):
        icon = image
    else:
        icon = "warship_" + nation if nation else None
    if icon:
        if nation:
            s += f"\ticon-{nation}:\n\t\tFilename: icons/{icon}.png\n\t\tOffset: 0,0\n"
        s += f"\ticon:\n\t\tFilename: icons/{icon}.png\n\t\tOffset: 0,0\n"
    return s


def actor_block(body, image, L, HB, ppm):
    body = re.sub(r"\tRenderSprites:\n(\t\t.*\n)*", "", body)
    body = re.sub(r"\tSelectable:\n(\t\t.*\n)*", "", body)
    body = re.sub(r"\tVolleyArmament@BROADSIDE:\n(\t\t.*\n)*", "", body)
    size = int(round(4096 * L / 56.0 / 128) * 128)
    add = f"\tRenderSprites:\n\t\tImage: {image}\n\tSelectable:\n\t\tBounds: {size}, {size}, 0, -1024\n"
    if ppm:
        xs = [round(0.36 * L * UNITS_PER_M * (k - 2) / 2) for k in range(5)]
        y = round((HB + 0.6) * UNITS_PER_M)
        offs = ", ".join(f"{x},{s * y},200" for s in (-1, 1) for x in xs)
        add += f"\tVolleyArmament@BROADSIDE:\n\t\tLocalOffset: {offs}\n\t\tProjectilesPerModel: {ppm}\n"
    return body.rstrip("\n") + "\n" + add


def main():
    seq = open(SEQ, encoding="utf-8").read()
    rules = open(SHIPS, encoding="utf-8").read()
    done = []
    for actor, (image, L, HB, ppm) in ACTORS.items():
        if not complete(image):
            continue
        out = os.path.join(MOD, "bits", image + ".png")
        subprocess.run([sys.executable, os.path.join(ART, "tools", "make_sprite_sheet.py"),
                        os.path.join(ART, "renders", image), "idle", out, "--frame", "256", "--scale", "3"],
                       check=True, stdout=subprocess.DEVNULL)
        m = re.search(r"^" + re.escape(image) + r":\n(?:\t.*\n|\n(?=\t))*", seq, re.M)
        block = sequence_block(image, actor)
        seq = seq[:m.start()] + block + seq[m.end():] if m else seq.rstrip("\n") + "\n\n" + block
        m = re.search(r"^" + actor + r":\n((?:\t.*\n|\n(?=\t))*)", rules, re.M)
        rules = rules[:m.start(1)] + actor_block(m.group(1), image, L, HB, ppm) + rules[m.end(1):]
        done.append(actor)
    open(SEQ, "w", encoding="utf-8", newline="\n").write(seq)
    open(SHIPS, "w", encoding="utf-8", newline="\n").write(rules)
    print("\n".join(done) or "nothing complete")


if __name__ == "__main__":
    main()
