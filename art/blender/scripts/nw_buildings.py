# Napoleonic buildings for OpenRA, built from primitives with procedural period materials.
# Scene NW_Buildings; one collection per building; each building's origin is the centre of its footprint (metres).
# Scale: 2.4 px/m in game, so one 24 px cell is 10 m.
import bpy, bmesh, math
from mathutils import Vector

SCENE = "NW_Buildings"
CELL = 10.0
R = math.radians


# ---------------------------------------------------------------- materials
def _nodes(m):
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return nt, bsdf, tc


def pattern_material(name, base, mortar, scale, kind="BRICK", rough=0.8, bump=0.4, emission=None):
    """Brick/stone courses (Brick texture), roof tiles/slates (Brick texture along another axis), with grime noise."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, bsdf, tc = _nodes(m)
    bsdf.inputs["Roughness"].default_value = rough
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.inputs["Color1"].default_value = (*base, 1)
    brick.inputs["Color2"].default_value = (*[c * 0.82 for c in base], 1)
    brick.inputs["Mortar"].default_value = (*mortar, 1)
    brick.inputs["Scale"].default_value = scale
    brick.inputs["Mortar Size"].default_value = 0.02 if kind != "TILE" else 0.035
    if kind == "STONE":
        brick.inputs["Brick Width"].default_value = 0.9
        brick.inputs["Row Height"].default_value = 0.45
    elif kind == "TILE":
        brick.inputs["Brick Width"].default_value = 0.35
        brick.inputs["Row Height"].default_value = 0.3
        brick.offset = 0.5
    nt.links.new(tc.outputs["Object"], brick.inputs["Vector"])
    grime = nt.nodes.new("ShaderNodeTexNoise")
    grime.inputs["Scale"].default_value = 0.08
    grime.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], grime.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(brick.outputs["Color"], mix.inputs[6]); nt.links.new(grime.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
    nt.links.new(brick.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 4.0
    m.diffuse_color = (*base, 1)
    m.use_fake_user = True
    return m


def plain(name, rgb, rough=0.7, metallic=0.0, emission=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, bsdf, tc = _nodes(m)
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 6.0
    m.diffuse_color = (*rgb, 1)
    m.use_fake_user = True
    return m


def materials():
    pattern_material("BL_Stone", (0.46, 0.43, 0.38), (0.30, 0.29, 0.27), 0.6, "STONE")
    pattern_material("BL_Brick", (0.36, 0.12, 0.07), (0.45, 0.43, 0.40), 1.6, "BRICK")
    pattern_material("BL_Whitewash", (0.70, 0.68, 0.62), (0.62, 0.60, 0.55), 0.6, "STONE", bump=0.1)
    pattern_material("BL_RoofTile", (0.40, 0.13, 0.06), (0.20, 0.08, 0.05), 1.8, "TILE", bump=0.6)
    pattern_material("BL_Slate", (0.12, 0.13, 0.15), (0.07, 0.07, 0.08), 1.8, "TILE", bump=0.6)
    pattern_material("BL_Planks", (0.30, 0.20, 0.11), (0.12, 0.08, 0.05), 1.2, "STONE", bump=0.3)
    pattern_material("BL_Cobbles", (0.34, 0.32, 0.29), (0.20, 0.19, 0.17), 2.2, "STONE", bump=0.7)
    plain("BL_Timber", (0.20, 0.12, 0.06))
    plain("BL_Window", (0.05, 0.07, 0.09), rough=0.15, metallic=0.3)
    plain("BL_Door", (0.12, 0.06, 0.03))
    plain("BL_Canvas", (0.78, 0.74, 0.62), rough=0.9)
    plain("BL_Iron", (0.05, 0.05, 0.055), rough=0.4, metallic=0.8)
    plain("BL_Bronze", (0.55, 0.36, 0.14), rough=0.35, metallic=1.0)
    plain("BL_Glow", (0.9, 0.35, 0.05), emission=(1.0, 0.45, 0.08))
    plain("BL_Gold", (0.80, 0.60, 0.20), rough=0.3, metallic=1.0)
    plain("BL_Grass", (0.10, 0.16, 0.06), rough=0.95)
    plain("FR_Player", (1.0, 0.0, 1.0))


# ---------------------------------------------------------------- geometry helpers
def coll(name):
    scn = bpy.data.scenes[SCENE]
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        scn.collection.children.link(c)
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    root = bpy.data.objects.new(name + "_Root", None)
    c.objects.link(root)
    return c, root


def _link(c, root, o, mname):
    for cc in o.users_collection:
        cc.objects.unlink(o)
    c.objects.link(o)
    o.data.materials.clear()
    o.data.materials.append(bpy.data.materials[mname])
    o.parent = root
    return o


def box(c, root, name, center, size, mname, rz=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center, rotation=(0, 0, R(rz)))
    o = bpy.context.active_object; o.scale = size; o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _link(c, root, o, mname)


def cyl(c, root, name, center, r, depth, mname, rot=(0, 0, 0), r2=None, verts=16):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=center, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=center, rotation=rot)
    o = bpy.context.active_object; o.name = name
    for p in o.data.polygons:
        p.use_smooth = True
    return _link(c, root, o, mname)


def gable_roof(c, root, name, center, length, width, height, mname, overhang=0.5, hip=False, rz=0):
    """Pitched roof over a rectangle (ridge along X). hip=True gives a hipped roof."""
    L, W, H = length / 2 + overhang, width / 2 + overhang, height
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    inset = W if hip else 0.0
    v = [bm.verts.new(p) for p in [(-L, -W, 0), (L, -W, 0), (L, W, 0), (-L, W, 0),
                                   (-L + inset, 0, H), (L - inset, 0, H)]]
    bm.faces.new([v[0], v[1], v[5], v[4]])
    bm.faces.new([v[2], v[3], v[4], v[5]])
    bm.faces.new([v[1], v[2], v[5]])
    bm.faces.new([v[3], v[0], v[4]])
    bm.faces.new([v[3], v[2], v[1], v[0]])
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = center; o.rotation_euler = (0, 0, R(rz))
    return _link(c, root, o, mname)


def windows(c, root, prefix, x0, x1, y, z, count, w=1.2, h=1.8, rz=0, mname="BL_Window"):
    """A row of windows on a wall facing +Y (y = wall front)."""
    for i in range(count):
        x = x0 + (i + 0.5) * (x1 - x0) / count
        box(c, root, f"{prefix}_{i}", (x, y, z), (w, 0.15, h), mname)


def flag(c, root, name, base, pole_h, fw=4.0, fh=2.6):
    cyl(c, root, name + "_Pole", (base[0], base[1], base[2] + pole_h / 2), 0.12, pole_h, "BL_Timber", verts=8)
    box(c, root, name + "_Flag", (base[0] + fw / 2 + 0.1, base[1], base[2] + pole_h - fh / 2), (fw, 0.08, fh), "FR_Player")


# ---------------------------------------------------------------- buildings
def headquarters():
    """3x3 cells: stone manor house with slate hipped roof, walled courtyard, command marquee, flag."""
    c, root = coll("BL_HQ")
    box(c, root, "Yard", (0, 0, 0.05), (28, 28, 0.1), "BL_Cobbles")
    box(c, root, "House", (0, 4, 4.5), (17, 9, 9), "BL_Stone")
    gable_roof(c, root, "Roof", (0, 4, 9), 17, 9, 4.2, "BL_Slate", hip=True)
    for k, x in enumerate((-5, 5)):
        box(c, root, f"Chimney_{k}", (x, 4, 12.2), (1.0, 1.2, 3.0), "BL_Stone")
    windows(c, root, "WinLow", -7.5, 7.5, -0.52, 2.4, 6)
    windows(c, root, "WinUp", -7.5, 7.5, -0.52, 6.6, 6)
    box(c, root, "Door", (0, -0.55, 1.4), (1.6, 0.2, 2.8), "BL_Door")
    box(c, root, "Portico", (0, -1.3, 3.2), (4.0, 1.6, 0.4), "BL_Stone")
    for x in (-1.7, 1.7):
        cyl(c, root, f"Column_{x}", (x, -2.0, 1.6), 0.25, 3.2, "BL_Stone", verts=10)
    # Courtyard wall with gate.
    for (cx, cy, sx, sy) in ((-13.5, 0, 1, 28), (13.5, 0, 1, 28), (0, 13.5, 28, 1), (-8.5, -13.5, 11, 1), (8.5, -13.5, 11, 1)):
        box(c, root, f"Wall_{cx}_{cy}", (cx, cy, 1.1), (sx, sy, 2.2), "BL_Stone")
    for x in (-3.2, 3.2):
        box(c, root, f"GatePost_{x}", (x, -13.5, 1.6), (1.2, 1.2, 3.2), "BL_Stone")
    # Command marquee in the courtyard, supply wagon, flag.
    box(c, root, "Marquee", (-6, -7, 1.4), (6, 4, 2.8), "BL_Canvas")
    gable_roof(c, root, "MarqueeRoof", (-6, -7, 2.8), 6, 4, 1.6, "BL_Canvas", overhang=0.2)
    box(c, root, "Wagon", (6.5, -7, 1.2), (4.5, 2.0, 1.2), "BL_Timber")
    gable_roof(c, root, "WagonTilt", (6.5, -7, 1.8), 4.3, 2.0, 1.4, "BL_Canvas", overhang=0.0)
    for k, (x, y) in enumerate(((4.7, -8.1), (8.3, -8.1), (4.7, -5.9), (8.3, -5.9))):
        cyl(c, root, f"Wheel_{k}", (x, y, 0.7), 0.7, 0.15, "BL_Timber", rot=(R(90), 0, 0), verts=12)
    flag(c, root, "HQFlag", (0, 4, 13.2), 8.0, fw=5.0, fh=3.2)
    return c, root


def barracks():
    """2x2 cells: whitewashed two-storey barrack block with tiled roof, timber stable wing, drill yard."""
    c, root = coll("BL_Barracks")
    box(c, root, "Yard", (0, 0, 0.05), (19, 19, 0.1), "BL_Cobbles")
    box(c, root, "Block", (-1.5, 4, 3.6), (14, 7, 7.2), "BL_Whitewash")
    gable_roof(c, root, "Roof", (-1.5, 4, 7.2), 14, 7, 3.2, "BL_RoofTile")
    windows(c, root, "WinLow", -7.5, 4.5, 0.45, 2.0, 6, w=1.0, h=1.5)
    windows(c, root, "WinUp", -7.5, 4.5, 0.45, 5.2, 6, w=1.0, h=1.5)
    box(c, root, "Door", (-1.5, 0.4, 1.3), (1.6, 0.2, 2.6), "BL_Door")
    # Stable wing (cavalry) in timber with a lower tiled roof and open stall doors.
    box(c, root, "Stable", (6.5, -1.5, 2.2), (5, 11, 4.4), "BL_Planks")
    gable_roof(c, root, "StableRoof", (6.5, -1.5, 4.4), 11, 5, 2.2, "BL_RoofTile", rz=90)
    for k, y in enumerate((-5.0, -2.5, 0.0, 2.5)):
        box(c, root, f"Stall_{k}", (3.95, y, 1.2), (0.15, 1.6, 2.2), "BL_Door")
    # Musket racks and a flag in the drill yard.
    for k, x in enumerate((-7, -4)):
        box(c, root, f"Rack_{k}", (x, -5, 0.9), (2.2, 0.4, 1.6), "BL_Timber")
    flag(c, root, "BarracksFlag", (-8, -7.5, 0), 7.5, fw=3.4, fh=2.2)
    return c, root


def foundry():
    """3x2 cells: brick casting hall, tall chimney, glowing furnace, cannon barrels and shot in the yard."""
    c, root = coll("BL_Foundry")
    box(c, root, "Yard", (0, 0, 0.05), (29, 19, 0.1), "BL_Cobbles")
    box(c, root, "Hall", (-2, 3, 4.0), (20, 9, 8.0), "BL_Brick")
    gable_roof(c, root, "Roof", (-2, 3, 8.0), 20, 9, 3.6, "BL_Slate")
    box(c, root, "Furnace", (-2, -1.55, 1.5), (3.0, 0.2, 3.0), "BL_Glow")
    windows(c, root, "Win", -11, 7, -1.55, 5.0, 7, w=1.1, h=2.2)
    cyl(c, root, "Chimney", (9.5, 5.5, 9.0), 1.3, 18.0, "BL_Brick", r2=0.9, verts=12)
    # Finished barrels and round shot waiting in the yard.
    for k in range(4):
        cyl(c, root, f"Barrel_{k}", (-10 + k * 2.2, -6.0, 0.35), 0.3, 2.3, "BL_Bronze", rot=(R(90), 0, 0), r2=0.22, verts=12)
    for k, (x, y, z) in enumerate([(6 + i * 0.5 + j * 0.25, -6 + j * 0.45, 0.25 + j * 0.4) for j in range(3) for i in range(4 - j)]):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.25, location=(x, y, z))
        o = bpy.context.active_object; o.name = f"Shot_{k}"; _link(c, root, o, "BL_Iron")
    box(c, root, "Coal", (11, -5, 0.6), (3, 3, 1.2), "BL_Iron")
    flag(c, root, "FoundryFlag", (-12.5, -7.5, 0), 6.5, fw=3.0, fh=2.0)
    return c, root


def shipyard():
    """3x3 cells on water: stone quay, slipway with a hull in frame, sheer-legs crane, timber shed."""
    c, root = coll("BL_Shipyard")
    box(c, root, "Quay", (0, 8, 1.0), (29, 12, 2.0), "BL_Stone")
    box(c, root, "Slipway", (-4, -2, 0.6), (8, 20, 0.6), "BL_Planks")
    # Hull in frame: keel, ribs, partial planking.
    box(c, root, "Keel", (-4, -3, 1.2), (0.6, 16, 0.8), "BL_Timber")
    for k in range(9):
        y = -10 + k * 1.8
        for s in (-1, 1):
            box(c, root, f"Rib_{k}_{s}", (-4 + s * 1.9, y, 3.2), (0.35, 0.35, 4.2), "BL_Timber")
    box(c, root, "Planking_L", (-6.0, -6, 2.4), (0.25, 7, 2.6), "BL_Planks")
    # Sheer-legs crane over the slip.
    for s in (-1, 1):
        box(c, root, f"Shear_{s}", (-4 + s * 2.5, 4, 6.5), (0.45, 0.45, 13), "BL_Timber")
    box(c, root, "ShearHead", (-4, 4, 12.8), (5.6, 0.5, 0.5), "BL_Timber")
    # Timber shed and stacks on the quay.
    box(c, root, "Shed", (8, 9, 4.0), (10, 7, 4.0), "BL_Planks")
    gable_roof(c, root, "ShedRoof", (8, 9, 6.0), 10, 7, 2.4, "BL_RoofTile")
    for k in range(3):
        box(c, root, f"Timber_{k}", (5 + k * 3, 3.5, 2.4 + k * 0.1), (2.4, 5.5, 0.9), "BL_Timber")
    flag(c, root, "YardFlag", (13, 13, 2.0), 7.0, fw=3.4, fh=2.2)
    return c, root


def counting_house():
    """2x2 cells: Georgian stone counting house with columned portico and pediment, strongbox, awnings."""
    c, root = coll("BL_CountingHouse")
    box(c, root, "Yard", (0, 0, 0.05), (19, 19, 0.1), "BL_Cobbles")
    box(c, root, "House", (0, 3, 5.0), (13, 9, 10.0), "BL_Stone")
    gable_roof(c, root, "Roof", (0, 3, 10.0), 13, 9, 3.4, "BL_Slate", hip=True)
    windows(c, root, "WinLow", -5.5, 5.5, -1.55, 2.6, 4, w=1.1, h=2.0)
    windows(c, root, "WinUp", -5.5, 5.5, -1.55, 7.2, 5, w=1.0, h=1.8)
    # Portico: four columns, entablature and triangular pediment.
    for k, x in enumerate((-3.0, -1.0, 1.0, 3.0)):
        cyl(c, root, f"Column_{k}", (x, -3.0, 2.6), 0.35, 5.2, "BL_Stone", verts=12)
    box(c, root, "Entablature", (0, -2.6, 5.5), (8, 2.4, 0.7), "BL_Stone")
    me = bpy.data.meshes.new("Pediment"); bm = bmesh.new()
    v = [bm.verts.new(p) for p in [(-4, -3.8, 5.85), (4, -3.8, 5.85), (0, -3.8, 7.6)]]
    bm.faces.new(v); bm.to_mesh(me); bm.free()
    _link(c, root, bpy.data.objects.new("Pediment", me), "BL_Stone")
    box(c, root, "Door", (0, -1.55, 1.6), (1.8, 0.2, 3.2), "BL_Door")
    # Player-colour awnings, strongbox and coin chests.
    for k, x in enumerate((-4.7, 4.7)):
        box(c, root, f"Awning_{k}", (x, -2.4, 3.6), (2.4, 1.6, 0.15), "FR_Player")
    box(c, root, "Strongbox", (-5.5, -6, 0.6), (1.6, 1.0, 1.0), "BL_Iron")
    for k in range(3):
        box(c, root, f"Chest_{k}", (4 + k * 1.3, -6.5, 0.4), (1.0, 0.8, 0.7), "BL_Timber")
        box(c, root, f"Coins_{k}", (4 + k * 1.3, -6.5, 0.8), (0.8, 0.6, 0.15), "BL_Gold")
    return c, root


BUILDINGS = {
    # name: (builder, footprint cells w x h)
    "headquarters": (headquarters, (3, 3)),
    "barracks": (barracks, (2, 2)),
    "foundry": (foundry, (3, 2)),
    "shipyard": (shipyard, (3, 3)),
    "countinghouse": (counting_house, (2, 2)),
}


def build_all():
    scn = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = scn
    materials()
    for name, (fn, _) in BUILDINGS.items():
        fn()
    return scn
