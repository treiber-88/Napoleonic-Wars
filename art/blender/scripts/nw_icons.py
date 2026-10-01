# Renders 4:3 icon portraits (256x192, transparent background) for every unit and building.
# Perspective three-quarter views; player colour shown as regulation red (icons are not player-tinted).
import bpy, math, os, time
from mathutils import Vector

SCRIPTS = r"C:\Users\mk-ki\Desktop\Napoleonic Wars\Napoleonic-Wars\art\blender\scripts"
OUT = r"C:\Users\mk-ki\Desktop\Napoleonic Wars\Napoleonic-Wars\art\renders\icons"
PLAYER_MATS = ["FR_Player", "SH_Player", "NW_PlayerColor"]
ICON_RED = (0.42, 0.02, 0.02)


def _ns(name):
    ns = {}
    exec(open(os.path.join(SCRIPTS, name), encoding="utf-8").read(), ns)
    return ns


def _player_colour(rgb):
    saved = {}
    for n in PLAYER_MATS:
        m = bpy.data.materials.get(n)
        if m and m.node_tree and m.node_tree.nodes.get("Principled BSDF"):
            b = m.node_tree.nodes["Principled BSDF"]
            saved[n] = tuple(b.inputs["Base Color"].default_value)
            b.inputs["Base Color"].default_value = (*rgb, 1)
    return saved


def _restore(saved):
    for n, c in saved.items():
        bpy.data.materials[n].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = c


def icon_camera(scn, name, eye, target, lens=50):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        scn.collection.objects.link(cam)
    cam.data.type = 'PERSP'
    cam.data.lens = lens
    cam.location = eye
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    return cam


def render_icon(scn, cam, path, hide=()):
    old_cam = scn.camera
    r = scn.render
    old = (r.resolution_x, r.resolution_y, r.film_transparent, scn.cycles.samples)
    scn.camera = cam
    r.resolution_x, r.resolution_y, r.film_transparent = 256, 192, True
    scn.cycles.samples = 32
    hidden = []
    for n in hide:
        o = bpy.data.objects.get(n)
        if o and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    r.filepath = path
    for attempt in range(5):
        with bpy.context.temp_override(scene=scn):
            bpy.ops.render.render(write_still=True, scene=scn.name)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            break
        time.sleep(1.0)
    for o in hidden:
        o.hide_render = False
    scn.camera = old_cam
    r.resolution_x, r.resolution_y, r.film_transparent, scn.cycles.samples = old
    return path


def infantry_icons():
    scn = bpy.data.scenes["NW_FrenchInfantry"]
    v, p = _ns("nw_variants.py"), _ns("nw_poses.py")
    cam = icon_camera(scn, "IconCam_Inf", (1.5, 3.0, 1.9), (0, 0, 1.30), lens=56)
    bpy.data.objects["FacingPivot"].rotation_euler.z = 0
    out = {}
    for var, key in (("line", "fr_line"), ("grenadier", "fr_grenadier"), ("british", "gb_line"),
                     ("british_grenadier", "gb_grenadier"), ("russian", "ru_line"), ("russian_grenadier", "ru_grenadier"),
                     ("prussian", "pr_line"), ("prussian_grenadier", "pr_grenadier"), ("austrian", "at_line"),
                     ("austrian_grenadier", "at_grenadier")):
        v["set_variant"](var)
        p["stand"]()
        bpy.data.objects["FacingPivot"].rotation_euler.z = math.radians(-50)   # three-quarter front view towards the camera
        bpy.context.view_layer.update()
        out[key] = render_icon(scn, cam, os.path.join(OUT, key + ".png"), hide=("FR_ShadowCatcher",))
    bpy.data.objects["FacingPivot"].rotation_euler.z = 0
    v["set_variant"]("line")
    return out


def cavalry_icons():
    scn = bpy.data.scenes["NW_Cavalry"]
    rnd = _ns("nw_cav_render.py")
    P, V = rnd["POSES"], rnd["VARIANTS"]
    cam = icon_camera(scn, "IconCam_Cav", (3.6, 4.6, 2.6), (0, 0.1, 1.45), lens=58)
    out = {}
    for var in V["VARIANTS"]:
        V["set_variant"](var, P)
        P["gallop"](1)
        bpy.data.objects["CV_Facing"].rotation_euler.z = math.radians(-75)   # side-on, turned slightly towards the camera
        bpy.context.view_layer.update()
        out[var] = render_icon(scn, cam, os.path.join(OUT, var + ".png"), hide=("CV_ShadowCatcher",))
    bpy.data.objects["CV_Facing"].rotation_euler.z = 0
    P["stand"]()
    return out


def building_icons():
    scn = bpy.data.scenes["NW_Buildings"]
    colls = {"headquarters": ("BL_HQ", 30), "barracks": ("BL_Barracks", 22), "foundry": ("BL_Foundry", 30),
             "shipyard": ("BL_Shipyard", 30), "countinghouse": ("BL_CountingHouse", 22)}
    out = {}
    for name, (cname, size) in colls.items():
        for c in colls.values():
            bpy.data.collections[c[0]].hide_render = c[0] != cname
        d = size * 1.25
        cam = icon_camera(scn, "IconCam_Bld", (d * 0.55, -d, d * 0.7), (0, 1.0, size * 0.12), lens=45)
        out[name] = render_icon(scn, cam, os.path.join(OUT, "bld_" + name + ".png"), hide=("BL_ShadowCatcher",))
    for c in colls.values():
        bpy.data.collections[c[0]].hide_render = False
    return out


def ship_icon():
    """One Temeraire-class portrait (French ensign); per-nation flags are badged on by make_icon.py --flag."""
    scn = bpy.data.scenes["NW_TemeraireClass"]
    bpy.data.objects["ShipPivot"].rotation_euler.z = 0
    cam = icon_camera(scn, "IconCam_Ship", (90, -40, 26), (-3, 6, 28), lens=35)
    # The model flies the tricolour; other navies' icons use a copy without the ensign (their flag is badged on).
    return {"fr_temeraire_class": render_icon(scn, cam, os.path.join(OUT, "fr_temeraire_class.png"),
                                              hide=("SH_ShadowCatcher",)),
            "warship_noensign": render_icon(scn, cam, os.path.join(OUT, "warship_noensign.png"),
                                            hide=("SH_ShadowCatcher", "Ensign_0", "Ensign_1", "Ensign_2"))}


def cannon_icon():
    """8-pounder on its carriage, appended from cannon_8pdr.blend; lit by the shared sprite sun and world."""
    if "NW_Cannon" not in bpy.data.scenes:
        with bpy.data.libraries.load(r"C:\Users\mk-ki\Desktop\Napoleonic Wars\Napoleonic-Wars\art\blender\cannon_8pdr.blend", link=False) as (src, dst):
            dst.scenes = ["NW_Cannon"]
    scn = bpy.data.scenes["NW_Cannon"]
    scn.render.engine = 'CYCLES'
    scn.cycles.use_denoising = False
    scn.view_settings.view_transform = 'Standard'
    scn.world = bpy.data.scenes["NW_FrenchInfantry"].world
    sun = bpy.data.objects.get("CN_IconSun") or bpy.data.objects.new("CN_IconSun", bpy.data.objects["FR_SpriteSun"].data)
    if sun.name not in scn.collection.objects:
        scn.collection.objects.link(sun)
    sun.rotation_euler = bpy.data.objects["FR_SpriteSun"].rotation_euler.copy()
    cam = icon_camera(scn, "IconCam_Cannon", (4.2, 3.2, 2.2), (0, -0.3, 0.3), lens=62)
    return {"nwcannon": render_icon(scn, cam, os.path.join(OUT, "nwcannon.png"))}


def run_all(groups=("infantry", "cavalry", "buildings")):
    os.makedirs(OUT, exist_ok=True)
    saved = _player_colour(ICON_RED)
    try:
        res = {}
        if "infantry" in groups:
            res.update(infantry_icons())
        if "cavalry" in groups:
            res.update(cavalry_icons())
        if "buildings" in groups:
            res.update(building_icons())
        if "ship" in groups:
            res.update(ship_icon())
        if "cannon" in groups:
            res.update(cannon_icon())
        return res
    finally:
        _restore(saved)


def ship_class_icons(keys=None):
    """A portrait of every ship class built by nw_ships.py, framed to its size, flying its own ensign."""
    ships = _ns("nw_ships.py")
    scn = bpy.data.scenes[ships["SCENE"]]
    out = {}
    saved = _player_colour(ICON_RED)
    try:
        for key in (keys or ships["ORDER"]):
            c = ships["SPECS"][key]
            ships["isolate"](key)
            bpy.data.objects[c.P + "_Pivot"].rotation_euler.z = 0
            k = c.L / 56.0
            top = max(m[1] for m in c.masts)
            cam = icon_camera(scn, "IconCam_Ship", (90 * k, -40 * k, 0.45 * top), (-3 * k, 6 * k, 0.48 * top), lens=35)
            out[key] = render_icon(scn, cam, os.path.join(OUT, key + ".png"), hide=("SH_ShadowCatcher",))
    finally:
        _restore(saved)
        ships["restore_visibility"]()
    return out
