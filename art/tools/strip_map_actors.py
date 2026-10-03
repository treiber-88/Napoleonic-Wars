"""
Removes every actor of the given types from all maps of the mod (folders and .oramap archives).
Used to take Red Alert's oil derricks, forward command posts and communications centres off the maps.

Usage: python art/tools/strip_map_actors.py oilb fcom miss
"""
import glob
import os
import re
import shutil
import sys
import zipfile

MAPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mods", "napoleonic", "maps")


def strip(text, types):
    """Drops `<tab>Name: type` nodes (and their indented children) from the Actors section."""
    out, removed, skipping, in_actors = [], [], False, False
    for line in text.split("\n"):
        if not line.startswith("\t"):
            in_actors = line.rstrip("\r").startswith("Actors:")
            skipping = False
        elif in_actors and not line.startswith("\t\t"):
            m = re.match(r"^\t([^\t:]+): ([A-Za-z0-9_.]+)\s*$", line)
            skipping = bool(m) and m.group(2).lower().split(".")[0] in types
            if skipping:
                removed.append(m.group(1))
        if not skipping:
            out.append(line)
    return "\n".join(out), removed


def other_text(names_and_data):
    return "\n".join(d.decode("utf-8", "replace") for n, d in names_and_data if n.lower().endswith((".lua", ".yaml")) and n != "map.yaml")


def main():
    types = {t.lower() for t in sys.argv[1:]}
    if not types:
        sys.exit(__doc__)
    total = 0
    for path in sorted(glob.glob(os.path.join(MAPS, "*"))):
        name = os.path.basename(path)
        if path.endswith(".oramap"):
            with zipfile.ZipFile(path) as z:
                entries = [(i, z.read(i.filename)) for i in z.infolist()]
            text = dict((i.filename, d) for i, d in entries)["map.yaml"].decode("utf-8")
            new, removed = strip(text, types)
            if not removed:
                continue
            scripts = other_text([(i.filename, d) for i, d in entries])
            tmp = path + ".tmp"
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
                for i, d in entries:
                    z.writestr(i, new.encode("utf-8") if i.filename == "map.yaml" else d)
            shutil.move(tmp, path)
        elif os.path.isdir(path):
            f = os.path.join(path, "map.yaml")
            text = open(f, encoding="utf-8", newline="").read()
            new, removed = strip(text, types)
            if not removed:
                continue
            scripts = other_text([(n, open(os.path.join(path, n), "rb").read()) for n in os.listdir(path)
                                  if os.path.isfile(os.path.join(path, n))])
            open(f, "w", encoding="utf-8", newline="").write(new)
        else:
            continue
        # Warn if a map script or rule file still names a removed actor.
        named = [r for r in removed if not re.fullmatch(r"Actor\d+", r) and re.search(r"\b" + re.escape(r) + r"\b", scripts)]
        print(f"{name}: removed {len(removed)}" + (f"  WARNING still referenced: {named}" if named else ""))
        total += len(removed)
    print("total removed:", total)


if __name__ == "__main__":
    main()
