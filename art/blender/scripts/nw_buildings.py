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


# ---------------------------------------------------------------- prisoner of war camp and neutral trading port
def extra_materials():
    """Materials only the camp and the port use (does not rebuild the materials of the existing buildings)."""
    if "BL_Earth" not in bpy.data.materials:
        plain("BL_Earth", (0.20, 0.15, 0.09), rough=0.95)
    if "BL_Palisade" not in bpy.data.materials:
        pattern_material("BL_Palisade", (0.24, 0.16, 0.09), (0.09, 0.06, 0.04), 2.4, "STONE", bump=0.5)
    if "BL_Sack" not in bpy.data.materials:
        plain("BL_Sack", (0.50, 0.42, 0.28), rough=0.95)


def palisade(c, root, name, a, b, height=3.2, spacing=0.5, radius=0.24):
    """A run of pointed stakes from a to b (one mesh): the stockade of a prison camp."""
    a = Vector(a); b = Vector(b)
    n = max(1, int((b - a).length / spacing))
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    for i in range(n + 1):
        p = a.lerp(b, i / n)
        h = height + (0.25 if i % 2 else 0.0)
        ring_lo = [bm.verts.new((p.x + radius * math.cos(k * math.pi / 3), p.y + radius * math.sin(k * math.pi / 3), 0)) for k in range(6)]
        ring_hi = [bm.verts.new((v.co.x, v.co.y, h)) for v in ring_lo]
        tip = bm.verts.new((p.x, p.y, h + 0.55))
        for k in range(6):
            bm.faces.new([ring_lo[k], ring_lo[(k + 1) % 6], ring_hi[(k + 1) % 6], ring_hi[k]])
            bm.faces.new([ring_hi[k], ring_hi[(k + 1) % 6], tip])
    bm.to_mesh(me); bm.free()
    return _link(c, root, bpy.data.objects.new(name, me), "BL_Palisade")


def pow_camp():
    """2x2 cells: timber stockade with a gate, two huts for the prisoners, an octagonal guard blockhouse
    (as at Norman Cross, 1797), sentry boxes at the gate and the flag of the side holding the camp."""
    extra_materials()
    c, root = coll("BL_POWCamp")
    box(c, root, "Ground", (0, 0, 0.05), (19, 19, 0.1), "BL_Earth")
    # Stockade: three closed sides and a gate in the middle of the south (front) side.
    h = 8.6
    palisade(c, root, "Pal_N", (-h, h, 0), (h, h, 0))
    palisade(c, root, "Pal_W", (-h, -h, 0), (-h, h, 0))
    palisade(c, root, "Pal_E", (h, -h, 0), (h, h, 0))
    palisade(c, root, "Pal_SW", (-h, -h, 0), (-1.9, -h, 0))
    palisade(c, root, "Pal_SE", (1.9, -h, 0), (h, -h, 0))
    for k, x in enumerate((-1.75, 1.75)):
        box(c, root, f"GatePost_{k}", (x, -h, 2.3), (0.5, 0.5, 4.6), "BL_Timber")
    box(c, root, "GateBeam", (0, -h, 4.5), (4.0, 0.45, 0.45), "BL_Timber")
    # Gate leaves standing open inwards.
    for k, (x, rz) in enumerate(((-1.45, -70), (1.45, 70))):
        box(c, root, f"GateLeaf_{k}", (x, -h + 0.85, 1.6), (1.7, 0.15, 3.0), "BL_Planks", rz=rz)
    # Huts for the prisoners: long, low, boarded, with tarred roofs.
    for k, y in enumerate((4.6, 0.4)):
        box(c, root, f"Hut_{k}", (0, y, 1.3), (13, 3.2, 2.6), "BL_Planks")
        gable_roof(c, root, f"HutRoof_{k}", (0, y, 2.6), 13, 3.2, 1.3, "BL_Slate", overhang=0.3)
        box(c, root, f"HutDoor_{k}", (-4.0, y - 1.65, 1.0), (1.0, 0.12, 2.0), "BL_Door")
        windows(c, root, f"HutWin_{k}", -2.5, 6.0, y - 1.65, 1.6, 4, w=0.7, h=0.7)
    # Octagonal blockhouse for the guard, in front of the huts, commanding the gate.
    cyl(c, root, "Blockhouse", (-4.6, -4.6, 2.0), 2.0, 4.0, "BL_Whitewash", verts=8)
    cyl(c, root, "BlockhouseRoof", (-4.6, -4.6, 4.9), 2.5, 1.8, "BL_Slate", r2=0.0, verts=8)
    box(c, root, "BlockhouseDoor", (-4.6, -6.6, 1.0), (0.9, 0.15, 2.0), "BL_Door")
    # Cooking fire and water butts.
    cyl(c, root, "FirePit", (4.5, -4.2, 0.2), 0.7, 0.3, "BL_Iron", verts=10)
    box(c, root, "Embers", (4.5, -4.2, 0.4), (0.7, 0.7, 0.12), "BL_Glow")
    for k, (x, y) in enumerate(((6.6, -5.6), (7.3, -5.0))):
        cyl(c, root, f"Butt_{k}", (x, y, 0.55), 0.42, 1.1, "BL_Timber", verts=10)
    # Sentry boxes in the holding side's colour either side of the gate, and the flag.
    for k, x in enumerate((-3.4, 3.4)):
        box(c, root, f"SentryBox_{k}", (x, -9.4, 1.2), (1.0, 1.0, 2.4), "FR_Player")
        gable_roof(c, root, f"SentryRoof_{k}", (x, -9.4, 2.4), 1.0, 1.0, 0.5, "BL_Slate", overhang=0.12)
    flag(c, root, "CampFlag", (-4.6, -4.6, 5.6), 5.0, fw=3.2, fh=2.1)
    return c, root


def trading_port():
    """3x3 cells on water: a stone mole (middle row) with a brick warehouse, the harbour office,
    a light tower and a treadwheel crane; low timber jetties and boats in the rows ships sail through."""
    extra_materials()
    c, root = coll("BL_TradingPort")
    top = 2.0
    box(c, root, "Mole", (0, 0, top / 2), (29, 11, top), "BL_Stone")
    box(c, root, "MolePaving", (0, 0, top + 0.05), (28.2, 10.2, 0.1), "BL_Cobbles")
    # Warehouse: three storeys of brick, tiled roof, loading doors one above the other under a hoist beam.
    box(c, root, "Warehouse", (-7.5, 1.6, top + 4.0), (11, 6.4, 8.0), "BL_Brick")
    gable_roof(c, root, "WarehouseRoof", (-7.5, 1.6, top + 8.0), 11, 6.4, 3.0, "BL_RoofTile")
    for k, z in enumerate((1.4, 4.2, 6.8)):
        box(c, root, f"LoadDoor_{k}", (-7.5, -1.65, top + z), (1.8, 0.15, 2.2), "BL_Door")
    for k, z in enumerate((1.9, 4.6, 7.0)):
        windows(c, root, f"WhWinL_{k}", -12.6, -9.0, -1.65, top + z, 2, w=0.9, h=1.2)
        windows(c, root, f"WhWinR_{k}", -6.0, -2.4, -1.65, top + z, 2, w=0.9, h=1.2)
    box(c, root, "HoistBeam", (-7.5, -2.5, top + 9.0), (0.3, 1.9, 0.3), "BL_Timber")
    cyl(c, root, "HoistRope", (-7.5, -3.3, top + 6.0), 0.05, 6.0, "BL_Iron", verts=6)
    # Harbour office: whitewashed, slate hipped roof.
    box(c, root, "HarbourHouse", (3.6, 2.0, top + 2.6), (6.0, 5.0, 5.2), "BL_Whitewash")
    gable_roof(c, root, "HarbourRoof", (3.6, 2.0, top + 5.2), 6.0, 5.0, 2.2, "BL_Slate", hip=True)
    windows(c, root, "HhWinLow", 0.9, 6.3, -0.55, top + 1.7, 3, w=0.9, h=1.4)
    windows(c, root, "HhWinUp", 0.9, 6.3, -0.55, top + 4.0, 3, w=0.9, h=1.2)
    box(c, root, "HarbourDoor", (3.6, -0.58, top + 1.1), (1.1, 0.15, 2.2), "BL_Door")
    # Light tower at the seaward end.
    cyl(c, root, "LightTower", (11.6, 1.6, top + 4.5), 1.6, 9.0, "BL_Whitewash", r2=1.15, verts=12)
    cyl(c, root, "LightGallery", (11.6, 1.6, top + 9.1), 1.6, 0.25, "BL_Stone", verts=12)
    cyl(c, root, "Lantern", (11.6, 1.6, top + 9.9), 0.85, 1.4, "BL_Glow", verts=8)
    cyl(c, root, "LanternRoof", (11.6, 1.6, top + 11.1), 1.15, 1.0, "BL_Slate", r2=0.0, verts=8)
    # Treadwheel crane on the quay edge: wheelhouse, post and jib over the water.
    box(c, root, "CraneHouse", (9.0, -3.2, top + 1.5), (2.6, 2.6, 3.0), "BL_Planks")
    cyl(c, root, "CraneHouseRoof", (9.0, -3.2, top + 3.7), 2.0, 1.4, "BL_Slate", r2=0.0, verts=4, rot=(0, 0, R(45)))
    cyl(c, root, "CranePost", (9.0, -3.2, top + 5.4), 0.2, 2.2, "BL_Timber", verts=8)
    box(c, root, "CraneJib", (9.0, -5.3, top + 6.3), (0.3, 5.0, 0.3), "BL_Timber")
    cyl(c, root, "CraneRope", (9.0, -7.6, top + 3.6), 0.05, 5.4, "BL_Iron", verts=6)
    box(c, root, "CraneLoad", (9.0, -7.6, top + 1.2), (1.1, 1.1, 1.0), "BL_Planks")
    # Cargo on the quay: barrels, crates and sacks.
    for k, (x, y) in enumerate(((-1.0, -3.4), (-0.1, -3.4), (-0.55, -2.6), (0.8, -3.6), (1.7, -3.2))):
        cyl(c, root, f"Cask_{k}", (x, y, top + 0.55), 0.42, 1.1, "BL_Timber", verts=10)
    for k, (x, y, s) in enumerate(((3.6, -3.6, 1.2), (4.9, -3.4, 1.0), (4.2, -3.5, 0.8))):
        box(c, root, f"Crate_{k}", (x, y, top + s / 2 + (1.0 if k == 2 else 0.0)), (s, s, s), "BL_Planks")
    for k in range(4):
        box(c, root, f"Sack_{k}", (-12.4 + k * 0.9, -3.8, top + 0.3 + (k % 2) * 0.1), (0.8, 1.2, 0.55), "BL_Sack")
    # Bollards along both quay edges.
    for k in range(8):
        x = -13.0 + k * 3.7
        for s, y in enumerate((-5.1, 5.1)):
            cyl(c, root, f"Bollard_{k}_{s}", (x, y, top + 0.45), 0.22, 0.9, "BL_Iron", verts=8)
    # Low timber jetties, piles and boats in the outer rows (ships pass over these cells).
    for k, (x, y0, y1) in enumerate(((-9.0, -5.5, -13.5), (6.0, 5.5, 13.5))):
        box(c, root, f"Jetty_{k}", (x, (y0 + y1) / 2, 0.9), (3.4, abs(y1 - y0), 0.3), "BL_Planks")
        for j in range(4):
            y = y0 + (y1 - y0) * (j + 0.5) / 4
            for sx in (-1.5, 1.5):
                cyl(c, root, f"Pile_{k}_{j}_{sx}", (x + sx, y, 0.6), 0.2, 1.6, "BL_Timber", verts=8)
    for k, (x, y, rz) in enumerate(((-4.5, -9.0, 20), (0.5, -11.0, -35), (11.0, 9.5, 80), (-1.5, 9.0, 10))):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=1.0, location=(x, y, 0.35), rotation=(0, 0, R(rz)))
        o = bpy.context.active_object; o.name = f"Boat_{k}"; o.scale = (0.9, 2.4, 0.5)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        _link(c, root, o, "BL_Timber")
    flag(c, root, "PortFlag", (-13.4, -4.4, top), 7.0, fw=3.4, fh=2.2)
    return c, root


BUILDINGS["powcamp"] = (pow_camp, (2, 2))
BUILDINGS["tradingport"] = (trading_port, (3, 3))
