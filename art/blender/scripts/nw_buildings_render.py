# Renders each building: frame 0 = idle, frames 1-8 = "make" (construction, rising into place).
# Same RA projection, sun and world as the units; 2.4 px/m; camera centred on the footprint centre.
import bpy, math, os, time
SCRIPTS = r"C:\Users\mk-ki\Desktop\Napoleonic Wars\Napoleonic-Wars\art\blender\scripts"
PX_PER_M = 2.4
FRAMES = {"headquarters": 128, "barracks": 96, "foundry": 128, "shipyard": 128, "countinghouse": 96}
COLLS = {"headquarters": "BL_HQ", "barracks": "BL_Barracks", "foundry": "BL_Foundry",
         "shipyard": "BL_Shipyard", "countinghouse": "BL_CountingHouse"}


def _ns(name):
    ns = {}
    exec(open(os.path.join(SCRIPTS, name), encoding="utf-8").read(), ns)
    return ns


def setup(scn):
    O = bpy.data.objects
    rig = bpy.data.collections.get("BL_SpriteRig")
    if rig is None:
        rig = bpy.data.collections.new("BL_SpriteRig")
        scn.collection.children.link(rig)
    cam = O.get("BL_SpriteCamera") or bpy.data.objects.new("BL_SpriteCamera", bpy.data.cameras.new("BL_SpriteCamera"))
    if cam.name not in rig.objects:
        rig.objects.link(cam)
    sun = O.get("BL_SpriteSun") or bpy.data.objects.new("BL_SpriteSun", O["FR_SpriteSun"].data)
    if sun.name not in rig.objects:
        rig.objects.link(sun)
    sun.rotation_euler = O["FR_SpriteSun"].rotation_euler.copy()
    plane = O.get("BL_ShadowCatcher")
    if plane is None:
        bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
        plane = bpy.context.active_object
        plane.name = "BL_ShadowCatcher"
        for c in plane.users_collection:
            c.objects.unlink(plane)
        rig.objects.link(plane)
    plane.is_shadow_catcher = True
    scn.camera = cam
    scn.world = bpy.data.scenes["NW_FrenchInfantry"].world
    r = scn.render
    r.engine = 'CYCLES'
    scn.cycles.samples = 24
    scn.cycles.use_denoising = False
    r.film_transparent = True
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    scn.view_settings.view_transform = 'Standard'
    return cam


def _save(scn, path):
    scn.render.filepath = path
    for attempt in range(5):
        try:
            with bpy.context.temp_override(scene=scn):
                bpy.ops.render.render(write_still=True, scene=scn.name)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return
        except RuntimeError:
            pass
        time.sleep(1.0)
    raise RuntimeError("could not save " + path)


def render_building(name, out_root=r"C:\Users\mk-ki\Desktop\Napoleonic Wars\Napoleonic-Wars\art\renders"):
    scn = bpy.data.scenes["NW_Buildings"]
    cam = setup(scn)
    rig = _ns("nw_sprite_rig.py")
    rig["setup_projection"](scn, cam, FRAMES[name], 0.0, PX_PER_M, 4)
    for key, cname in COLLS.items():
        bpy.data.collections[cname].hide_render = key != name
    root = bpy.data.objects[COLLS[name] + "_Root"]
    out = os.path.join(out_root, "bld_" + name)
    os.makedirs(out, exist_ok=True)
    # 0: finished building; 1-8: construction, rising from the ground.
    root.scale = (1, 1, 1)
    _save(scn, os.path.join(out, "frame_000.png"))
    for i in range(8):
        root.scale = (1, 1, 0.08 + 0.92 * (i + 1) / 8)
        bpy.context.view_layer.update()
        _save(scn, os.path.join(out, f"frame_{i + 1:03d}.png"))
    root.scale = (1, 1, 1)
    for cname in COLLS.values():
        bpy.data.collections[cname].hide_render = False
    return out
