"""
Convert the Blender icon renders (art/renders/icons) to sidebar icons in mods/napoleonic/bits/icons and point
every image's `icon` sequence at them. Warships share the Temeraire-class portrait with the nation's flag badged
on; each ship image gets `icon-<nation>` sequences and each ship actor selects one via Buildable.Icon.

Usage: python wire_icons.py
"""
import os
import re
import subprocess
import sys

ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(os.path.dirname(ART), "mods", "napoleonic")
RENDERS = os.path.join(ART, "renders", "icons")
OUT = os.path.join(MOD, "bits", "icons")
SEQ = os.path.join(MOD, "sequences", "napoleonic.yaml")
SHIPS = os.path.join(MOD, "rules", "ships.yaml")
MAKE = os.path.join(ART, "tools", "make_icon.py")
NATIONS = {"fr": "france", "gb": "england", "ru": "russia", "pr": "prussia", "au": "austria"}
SHIP_IMAGES = ["ca", "dd", "pt", "fr_temeraire_class"]


def convert(src, dst, flag=None):
    cmd = [sys.executable, MAKE, src, dst] + (["--flag", flag] if flag else [])
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def set_icon(text, image, filename):
    """Replace the Filename of `image`'s icon sequence (adding the sequence if the image has none)."""
    m = re.search(r"^" + re.escape(image) + r":\n((?:\t.*\n|\n(?=\t))*)", text, re.M)
    if not m:
        return text, False
    body = m.group(1)
    icon = re.search(r"^\ticon:\n(?:\t\t.*\n)*", body, re.M)
    block = "\ticon:\n\t\tFilename: " + filename + "\n\t\tOffset: 0,0\n"
    body = body[:icon.start()] + block + body[icon.end():] if icon else body.rstrip("\n") + "\n" + block
    return text[:m.start(1)] + body + text[m.end(1):], True


def main():
    os.makedirs(OUT, exist_ok=True)
    seq = open(SEQ, encoding="utf-8").read()
    wired = []
    for f in sorted(os.listdir(RENDERS)):
        key = f[:-4]
        if key in ("fr_temeraire_class", "warship_noensign"):
            continue
        convert(os.path.join(RENDERS, f), os.path.join(OUT, key + ".png"))
        seq, ok = set_icon(seq, "fr_ligne" if key == "fr_line" else key, "icons/" + key + ".png")
        wired.append(key if ok else key + " (no image)")

    # Warships: one portrait, five flags. Ship images are RA's (ca/dd/pt) plus ours; add icon-<nation> to each.
    ship = os.path.join(RENDERS, "fr_temeraire_class.png")
    if os.path.exists(ship):
        plain = os.path.join(RENDERS, "warship_noensign.png")
        for nation in NATIONS.values():
            src = ship if nation == "france" or not os.path.exists(plain) else plain
            convert(src, os.path.join(OUT, "warship_" + nation + ".png"), nation)
        seq = re.sub(r"\n# Warship icons.*\Z", "\n", seq, flags=re.S).rstrip("\n") + "\n"
        extra = ["", "# Warship icons: Temeraire-class portrait with the nation's flag (art/tools/wire_icons.py)."]
        for img in SHIP_IMAGES:
            if img != "fr_temeraire_class":
                extra.append(img + ":")
                for nation in NATIONS.values():
                    extra += ["\ticon-" + nation + ":", "\t\tFilename: icons/warship_" + nation + ".png", "\t\tOffset: 0,0"]
        seq += "\n".join(extra) + "\n"
        # Our own ship image keeps its sequences in place.
        m = re.search(r"^fr_temeraire_class:\n((?:\t.*\n|\n(?=\t))*)", seq, re.M)
        body = re.sub(r"^\ticon(-\w+)?:\n(?:\t\t.*\n)*", "", m.group(1), flags=re.M)
        for nation in NATIONS.values():
            body += "\ticon-" + nation + ":\n\t\tFilename: icons/warship_" + nation + ".png\n\t\tOffset: 0,0\n"
        body += "\ticon:\n\t\tFilename: icons/warship_france.png\n\t\tOffset: 0,0\n"
        seq = seq[:m.start(1)] + body + seq[m.end(1):]

        # Each ship actor picks its nation's icon.
        rules = open(SHIPS, encoding="utf-8").read()
        def pick(m):
            nation = NATIONS.get(m.group(1).lower())
            b = re.sub(r"\t\tIcon: icon-\w+\n", "", m.group(0))
            if not nation:
                return b
            return b.replace("\tBuildable:\n", "\tBuildable:\n\t\tIcon: icon-" + nation + "\n", 1)
        rules = re.sub(r"^([A-Z]{2})_\w+:\n(?:\t.*\n|\n(?=\t))*", pick, rules, flags=re.M)
        open(SHIPS, "w", encoding="utf-8", newline="\n").write(rules)
        wired.append("warships x5")

    open(SEQ, "w", encoding="utf-8", newline="\n").write(seq)
    print("\n".join(wired))


if __name__ == "__main__":
    main()
