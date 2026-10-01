"""Add a grenadier sprite (stand/run/shoot/throw/die1-3 layout) to the sequences and point a unit at it.
Usage: python wire_grenadier.py <image> <ACTOR> "<comment>" """
import sys
image, actor, comment = sys.argv[1], sys.argv[2], sys.argv[3]
root = r"C:\Users\mk-ki\Desktop\Napoleonic Wars\Napoleonic-Wars\mods\napoleonic"
seq = f"""

# {comment}
{image}:
	Defaults:
		Filename: {image}.png
		Offset: 0,-10
	stand:
		Facings: 8
	run:
		Start: 8
		Length: 6
		Facings: 8
		Tick: 110
	shoot:
		Start: 56
		Length: 6
		Facings: 8
		Tick: 100
	throw:
		Start: 104
		Length: 6
		Facings: 8
		Tick: 110
"""
for k in range(3):
    seq += f"""	die{k + 1}:
		Start: {152 + 64 * k}
		Length: 8
		Facings: 8
		Tick: 90
"""
seq += """	icon:
		Filename: e2icon.shp
		Offset: 0,0
"""
p = root + r"\sequences\napoleonic.yaml"
s = open(p, encoding="utf-8").read()
if f"\n{image}:\n" not in s:
    s = s.rstrip("\n") + seq
open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip("\n") + "\n")

p = root + r"\rules\infantry.yaml"
s = open(p, encoding="utf-8").read()
i = s.index(actor + ":\n")
j = s.find("\n\n", i)
j = len(s.rstrip("\n")) if j < 0 else j
if "RenderSprites:" not in s[i:j]:
    s = s[:i] + s[i:j] + f"\n\tRenderSprites:\n\t\tImage: {image}\n\tFormation:\n\t\tShootSequence: shoot\n\t\tDeathSequences: die1, die2, die3" + s[j:]
open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip("\n") + "\n")
print("wired", image, "->", actor)
