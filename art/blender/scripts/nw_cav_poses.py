# Cavalry poses for the NW_Cavalry rig. Angles in degrees; horse faces +Y.
import bpy, math
R = math.radians
O = bpy.data.objects

BONES = ["CV_Root", "HorseBody", "HorseNeck", "HorseHead", "HorseTail", "Rider", "RiderChest", "RiderHead",
         "RShoulder_L", "RShoulder_R", "RElbow_L", "RElbow_R"]
LEGS = [f"{p}{e}{s}" for p in ("Leg", "Knee") for e in ("F", "H") for s in ("L", "R")]
WEAPON = {"sabre": ["W_Sabre", "W_Hilt"], "pistol": ["W_Pistol"], "lance": ["W_Lance", "W_LanceHead"]}
STATE = {"lancer": False}


def rot(b, x=0, y=0, z=0):
    O[b].rotation_euler = (R(x), R(y), R(z))


def weapon(kind):
    """Show one weapon in the right hand. Lancers carry the lance instead of a sabre."""
    if kind == "sabre" and STATE["lancer"]:
        kind = "lance"
    for k, objs in WEAPON.items():
        for n in objs:
            O[n].hide_render = O[n].hide_viewport = k != kind


def reset():
    for b in BONES + LEGS:
        O[b].rotation_euler = (0, 0, 0)
    O["CV_Root"].location = (0, 0, 0)
    O["HorseBody"].location = (0, 0, 1.25)
    # Seated straddle: thighs forward and down along the flanks, lower legs hanging.
    for side in ("L", "R"):
        rot(f"RHip_{side}", -45)
        rot(f"RKnee_{side}", 45)
    rot("HorseNeck", 5)
    rot("HorseTail", 10)


def carry():
    """Sabre carried sloped against the shoulder (lance upright), left hand on the reins."""
    rot("RShoulder_R", 25, 0, 5); rot("RElbow_R", 95)
    rot("RShoulder_L", 35, 0, -10); rot("RElbow_L", 60)
    weapon("sabre")


def stand():
    reset(); carry()
    rot("HorseHead", 8)


def gallop(i, n=6):
    """Transverse gallop: hind left, hind right, fore left, fore right, then suspension."""
    reset(); carry()
    t = i / n
    phase = {"HL": 0.0, "HR": 0.12, "FL": 0.45, "FR": 0.57}
    for key, ph in phase.items():
        end, side = key[0], key[1]
        a = math.sin(2 * math.pi * (t - ph))
        swing = 32 * a if end == "F" else -30 * a
        rot(f"Leg{end}{side}", swing)
        # Knee folds while the leg comes forward through the air.
        fold = max(0.0, math.cos(2 * math.pi * (t - ph)))
        rot(f"Knee{end}{side}", (-70 if end == "F" else 55) * fold)
    pitch = 6 * math.sin(2 * math.pi * t)
    rot("HorseBody", pitch)
    O["HorseBody"].location = (0, 0, 1.25 + 0.06 * math.sin(2 * math.pi * t + 0.5))
    rot("HorseNeck", 5 - 1.5 * pitch)
    rot("HorseTail", 35)
    rot("RiderChest", 12 - pitch)
    rot("RShoulder_R", 60, 0, 5); rot("RElbow_R", 40)     # sabre/lance levelled forward at the charge


def shoot(i):
    """Pistol: raise, aim, fire (recoil), lower."""
    stand()
    weapon("pistol")
    arm = [(50, 40), (85, 5), (95, 0), (60, 30)][i]
    rot("RShoulder_R", arm[0], 0, 5); rot("RElbow_R", arm[1])
    rot("RiderChest", 0, 0, -8)


def slash(i):
    """Sabre (or lance) attack: raise, cut down, follow through, recover."""
    gallop(i % 6)
    weapon("sabre")
    if STATE["lancer"]:
        arm = [(70, 30), (85, 5), (90, 0), (70, 25)][i]
    else:
        arm = [(150, 70), (175, 100), (60, 10), (30, 40)][i]
    rot("RShoulder_R", arm[0], 0, 8); rot("RElbow_R", arm[1])
    rot("RiderChest", [8, 4, 20, 12][i], 0, [10, 14, -12, -4][i])


def ease(t):
    return t * t * (3 - 2 * t)


def die(kind, i, n=8):
    """1: horse rolls onto its side. 2: horse collapses forward and slumps over. Last frame stays on the field.
    Bodies twist so they never lie along the view axis."""
    reset(); carry()
    t = ease(i / (n - 1))
    if kind == 1:
        rot("CV_Root", 0, 80 * t, 35 * t)
        for leg in ("LegFL", "LegFR", "LegHL", "LegHR"):
            rot(leg, 20 * t if leg.startswith("LegF") else -20 * t)
        rot("HorseNeck", 5 - 30 * t); rot("HorseHead", 20 * t)
        rot("RiderChest", -30 * t, -20 * t)
        rot("RShoulder_R", 25 + 90 * t); rot("RElbow_R", 95 - 80 * t)
    else:
        drop = min(1.0, t * 1.6)
        side = max(0.0, t * 1.6 - 0.6) / 1.0
        O["HorseBody"].location = (0, 0, 1.25 - 0.62 * drop)
        rot("KneeFL", -120 * drop); rot("KneeFR", -110 * drop)
        rot("LegFL", 40 * drop); rot("LegFR", 35 * drop)
        rot("KneeHL", 100 * drop); rot("KneeHR", 90 * drop)
        rot("LegHL", -50 * drop); rot("LegHR", -45 * drop)
        rot("HorseBody", 10 * drop)
        rot("HorseNeck", 5 - 45 * drop)
        rot("CV_Root", 0, -60 * side, -40 * t)
        rot("RiderChest", 45 * drop)
        rot("RShoulder_R", 25 + 100 * drop); rot("RElbow_R", 95 - 90 * drop)
