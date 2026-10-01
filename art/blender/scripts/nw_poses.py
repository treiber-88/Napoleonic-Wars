# Infantry poses for the shared soldier rig (scene NW_FrenchInfantry). Angles in degrees.
import bpy, math
R = math.radians
O = bpy.data.objects

BONES = ["Root", "Pelvis", "Chest", "Head", "Shoulder_L", "Shoulder_R", "Elbow_L", "Elbow_R",
         "Hip_L", "Hip_R", "Knee_L", "Knee_R"]


def reset():
    for b in BONES:
        O[b].rotation_euler = (0, 0, 0)
    O["Root"].location = (0, 0, 0)
    O["Pelvis"].location = (0, 0, 0.95)


def rot(b, x=0, y=0, z=0):
    O[b].rotation_euler = (R(x), R(y), R(z))


def musket(loc, rx=0, ry=0, rz=0):
    O["Musket"].location = loc
    O["Musket"].rotation_euler = (R(rx), R(ry), R(rz))


def shoulder_arms():
    """Musket carried upright against the left shoulder, butt in the left hand."""
    rot("Shoulder_L", 8, 0, -4)
    rot("Elbow_L", 10)
    rot("Shoulder_R", 4, 0, 4)
    musket((-0.23, 0.05, 0.78), 12, 0, 0)


def stand():
    reset(); shoulder_arms()


def march(i, n=6):
    """Walk cycle frame i of n, in place."""
    reset(); shoulder_arms()
    p = 2 * math.pi * i / n
    s = math.sin(p)
    rot("Hip_L", 26 * s); rot("Hip_R", -26 * s)
    rot("Knee_L", -40 * max(0.0, math.sin(p - 1.2)))
    rot("Knee_R", -40 * max(0.0, math.sin(p + math.pi - 1.2)))
    rot("Shoulder_R", 4 + 22 * s, 0, 4)
    bob = 0.025 * abs(math.cos(p))
    O["Pelvis"].location = (0, 0, 0.95 - 0.03 + bob)
    rot("Chest", 4)


def aim(recoil=0.0):
    rot("Chest", -4 - 6 * recoil)
    rot("Shoulder_R", 40, 0, 0); rot("Elbow_R", 90)
    rot("Shoulder_L", 85, 0, -30); rot("Elbow_L", 5)
    rot("Head", 8)
    musket((0.13, -0.10 - 0.05 * recoil, 1.36 + 0.02 * recoil), -90 - 4 * recoil, 0, 0)


def shoot(i):
    """Present, aim, fire, recoil, recover, lower."""
    reset()
    if i == 0:
        rot("Shoulder_R", 25); rot("Elbow_R", 60)
        rot("Shoulder_L", 55, 0, -25); rot("Elbow_L", 20)
        musket((0.05, 0.05, 1.05), -45, 0, 0)
    elif i in (1, 4):
        aim()
    elif i == 2:
        aim(0.6)
    elif i == 3:
        aim(1.0)
    else:
        rot("Shoulder_R", 25); rot("Elbow_R", 60)
        rot("Shoulder_L", 50, 0, -20); rot("Elbow_L", 20)
        musket((0.02, 0.05, 1.0), -35, 0, 0)


def throw(i):
    """Overarm grenade throw, 6 frames."""
    reset(); shoulder_arms()
    arm = [(-15, 45), (-110, 70), (-160, 95), (150, 30), (80, 10), (25, 10)][i]
    rot("Shoulder_R", arm[0], 0, 8); rot("Elbow_R", arm[1])
    rot("Chest", [0, -8, -12, 12, 8, 2][i], 0, [0, 12, 18, -10, -6, 0][i])


def ease(t):
    return t * t * (3 - 2 * t)


def die(kind, i, n=8):
    """Three deaths; the last frame is the body left on the field. Bodies twist so they never
    lie along the view axis (in the RA projection that reads as a standing man)."""
    reset(); shoulder_arms()
    t = ease(i / (n - 1))
    if kind == 1:        # shot, falls backwards
        rot("Root", -88 * t, 0, 40 * t)
        rot("Knee_L", -30 * t); rot("Knee_R", -10 * t)
        rot("Shoulder_L", 8 + 100 * t, 0, -30 * t); rot("Shoulder_R", 60 * t, 0, 20 * t)
        musket((-0.23 - 0.5 * t, 0.05, 0.78 - 0.5 * t), 12 + 70 * t, 0, 30 * t)
    elif kind == 2:      # pitches forward
        rot("Root", 86 * t, 0, -45 * t)
        rot("Chest", 10 * t)
        rot("Shoulder_L", 8 + 150 * t); rot("Shoulder_R", 150 * t, 0, 10 * t)
        rot("Knee_L", -20 * t)
        musket((-0.35, 0.05 + 0.4 * t, 0.78 - 0.6 * t), 12 + 80 * t, 0, -20 * t)
    else:                # knees give way, slumps onto his side
        drop = min(1.0, t * 2)
        side = max(0.0, t * 2 - 1)
        O["Pelvis"].location = (0, 0, 0.95 - 0.45 * drop)
        rot("Hip_L", 60 * drop); rot("Hip_R", 50 * drop)
        rot("Knee_L", -110 * drop); rot("Knee_R", -100 * drop)
        rot("Root", 0, 85 * side, 0)
        rot("Chest", 20 * drop)
        rot("Shoulder_L", 30 * drop); rot("Shoulder_R", 20 * drop, 0, 30 * side)
        musket((-0.5 * drop, 0.3 * drop, 0.78 - 0.7 * drop), 12 + 78 * drop, 0, 40 * drop)
