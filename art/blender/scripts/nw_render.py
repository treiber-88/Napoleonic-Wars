# Renders an infantry sheet: stand 8, march 8x6, shoot 8x6, [throw 8x6], die1-3 8x8 (facing-major).
import bpy, math, os, time
SCRIPTS = r"C:\Users\mk-ki\Desktop\Napoleonic Wars\Napoleonic-Wars\art\blender\scripts"


def _load(name):
    ns = {}
    exec(open(os.path.join(SCRIPTS, name), encoding="utf-8").read(), ns)
    return ns


POSES = _load("nw_poses.py")


def plan(with_throw=False):
    p = []
    for f in range(8):
        p.append((f, lambda: POSES["stand"]()))
    for f in range(8):
        for i in range(6):
            p.append((f, (lambda i=i: POSES["march"](i))))
    for f in range(8):
        for i in range(6):
            p.append((f, (lambda i=i: POSES["shoot"](i))))
    if with_throw:
        for f in range(8):
            for i in range(6):
                p.append((f, (lambda i=i: POSES["throw"](i))))
    for kind in (1, 2, 3):
        for f in range(8):
            for i in range(8):
                p.append((f, (lambda k=kind, i=i: POSES["die"](k, i))))
    return p


def render_range(scene_name, out_dir, first, last, with_throw=False):
    scn = bpy.data.scenes[scene_name]
    os.makedirs(out_dir, exist_ok=True)
    fp = bpy.data.objects["FacingPivot"]
    frames = plan(with_throw)
    for n in range(first, min(last, len(frames))):
        facing, pose = frames[n]
        pose()
        fp.rotation_euler.z = 2 * math.pi * facing / 8
        bpy.context.view_layer.update()
        scn.render.filepath = os.path.join(out_dir, f"frame_{n:03d}.png")
        # The output drive can drop out for a moment; retry the save.
        # Also check the file really landed: a dropout can lose a write without an error.
        for attempt in range(5):
            try:
                with bpy.context.temp_override(scene=scn):
                    bpy.ops.render.render(write_still=True, scene=scn.name)
                if os.path.exists(scn.render.filepath) and os.path.getsize(scn.render.filepath) > 0:
                    break
            except RuntimeError:
                pass
            if attempt == 4:
                raise RuntimeError("could not save " + scn.render.filepath)
            time.sleep(1.0)
    fp.rotation_euler.z = 0
    POSES["stand"]()
    return len(frames)
