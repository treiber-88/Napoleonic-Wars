"""Add a cavalry sprite (stand/run/shoot/slash/die1/die2, 64x64, 248 frames) and point unit(s) at it.
Usage: python wire_cavalry.py <image> "<comment>" ACTOR [ACTOR...]"""
import sys
image, comment, actors = sys.argv[1], sys.argv[2], sys.argv[3:]
root = r"D:\Napoleonic Wars\mods\napoleonic"
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
		Tick: 80
	shoot:
		Start: 56
		Length: 4
		Facings: 8
		Tick: 110
	slash:
		Start: 88
		Length: 4
		Facings: 8
		Tick: 110
	die1:
		Start: 120
		Length: 8
		Facings: 8
		Tick: 100
	die2:
		Start: 184
		Length: 8
		Facings: 8
		Tick: 100
	icon:
		Filename: dogicon.shp
		Offset: 0,0
"""
p = root + r"\sequences\napoleonic.yaml"
s = open(p, encoding="utf-8").read()
if f"\n{image}:\n" not in s:
    s = s.rstrip("\n") + seq
open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip("\n") + "\n")

p = root + r"\rules\cavalry.yaml"
s = open(p, encoding="utf-8").read()
for actor in actors:
    i = s.index(actor + ":\n")
    j = s.find("\n\n", i)
    j = len(s.rstrip("\n")) if j < 0 else j
    if "RenderSprites:" not in s[i:j]:
        s = s[:i] + s[i:j] + f"""
	RenderSprites:
		Image: {image}
	Formation:
		ShootSequence: shoot
		DeathSequences: die1, die2
	VolleyArmament@SABRE:
		ShootSequence: slash""" + s[j:]
open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip("\n") + "\n")
print("wired", image, "->", ", ".join(actors))
