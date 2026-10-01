# Renders a cavalry sheet: stand 8, run 8x6, shoot 8x4, slash 8x4, die1 8x8, die2 8x8 (facing-major) = 248 frames.
import bpy, math, os, time
SCRIPTS = r"C:\Users\mk-ki\Desktop\Napoleonic Wars\Napoleonic-Wars\art\blender\scripts"


def _load(name):
    ns = {}
    exec(open(os.path.join(SCRIPTS, name), encoding="utf-8").read(), ns)
    return ns


POSES = _load("nw_cav_poses.py")
VARIANTS = _load("nw_cav_variants.py")


def plan():
    p = []
    for f in range(8):
        p.append((f, lambda: POSES["stand"]()))
    for f in range(8):
        for i in range(6):
            p.append((f, (lambda i=i: POSES["gallop"](i))))
    for f in range(8):
        for i in range(4):
            p.append((f, (lambda i=i: POSES["shoot"](i))))
    for f in range(8):
        for i in range(4):
            p.append((f, (lambda i=i: POSES["slash"](i))))
    for kind in (1, 2):
        for f in range(8):
            for i in range(8):
                p.append((f, (lambda k=kind, i=i: POSES["die"](k, i))))
    return p


def render_range(variant, out_dir, first, last, scene_name="NW_Cavalry"):
    scn = bpy.data.scenes[scene_name]
    VARIANTS["set_variant"](variant, POSES)
    os.makedirs(out_dir, exist_ok=True)
    fp = bpy.data.objects["CV_Facing"]
    frames = plan()
    for n in range(first, min(last, len(frames))):
        facing, pose = frames[n]
        pose()
        fp.rotation_euler.z = 2 * math.pi * facing / 8
        bpy.context.view_layer.update()
        scn.render.filepath = os.path.join(out_dir, f"frame_{n:03d}.png")
        # Check the file really landed: the output drive can drop out without an error.
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
