# Faction panels for the in-game sidebar (the 222x222 panel Red Alert fills with its Allied / Soviet emblem).
# Each nation's period flag (the same flag artwork as the lobby flags, art/renders/flags/<nation>.png) flies as
# rippling cloth from a staff with a gilt finial, over a dark campaign-map background, with the nation's name
# in gilt letters. Scene NW_SidebarFlags; renders to art/renders/sidebar/<nation>.png at 444x444 (2x).
import bpy, bmesh, math, os
from mathutils import Vector

ROOT = r"C:\Users\mk-ki\Desktop\Napoleonic Wars\Napoleonic-Wars\art"
FLAGS = os.path.join(ROOT, "renders", "flags")
OUT = os.path.join(ROOT, "renders", "sidebar")
SCENE = "NW_SidebarFlags"
NATIONS = {
    # faction id: (flag image, name shown)
    "france": ("france.png", "FRANCE"),
    "england": ("britain.png", "GREAT BRITAIN"),
    "russia": ("russia.png", "RUSSIA"),
    "prussia": ("prussia.png", "PRUSSIA"),
    "austria": ("austria.png", "AUSTRIA"),
}
FONTS = [r"C:\Windows\Fonts\georgiab.ttf", r"C:\Windows\Fonts\timesbd.ttf"]


def _mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_fake_user = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf


def map_material():
    """Dark campaign map: sepia ground with mottling, faint gilt grid lines and a vignette."""
    m, nt, bsdf = _mat("SB_Map")
    bsdf.inputs["Roughness"].default_value = 0.9
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.040, 0.031, 0.020, 1)
    ramp.color_ramp.elements[1].color = (0.100, 0.075, 0.047, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    # Grid: two sets of thin bands.
    lines = []
    for axis in ('X', 'Y'):
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = 'BANDS'; w.bands_direction = axis; w.wave_profile = 'SAW'
        w.inputs["Scale"].default_value = 3.0
        nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
        r = nt.nodes.new("ShaderNodeValToRGB")
        r.color_ramp.elements[0].position = 0.0
        r.color_ramp.elements[0].color = (1, 1, 1, 1)
        r.color_ramp.elements[1].position = 0.025
        r.color_ramp.elements[1].color = (0, 0, 0, 1)
        nt.links.new(w.outputs["Fac"], r.inputs["Fac"])
        lines.append(r)
    grid = nt.nodes.new("ShaderNodeMath"); grid.operation = 'MAXIMUM'
    nt.links.new(lines[0].outputs["Color"], grid.inputs[0]); nt.links.new(lines[1].outputs["Color"], grid.inputs[1])
    gridmix = nt.nodes.new("ShaderNodeMix"); gridmix.data_type = 'RGBA'
    gridmix.inputs[7].default_value = (0.32, 0.25, 0.10, 1)
    gm = nt.nodes.new("ShaderNodeMath"); gm.operation = 'MULTIPLY'; gm.inputs[1].default_value = 0.22
    nt.links.new(grid.outputs[0], gm.inputs[0])
    nt.links.new(gm.outputs[0], gridmix.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], gridmix.inputs[6])
    # Vignette: darken towards the edges.
    grad = nt.nodes.new("ShaderNodeTexGradient"); grad.gradient_type = 'SPHERICAL'
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.75, 0.75, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], grad.inputs["Vector"])
    vig = nt.nodes.new("ShaderNodeMix"); vig.data_type = 'RGBA'; vig.blend_type = 'MULTIPLY'
    vig.inputs["Factor"].default_value = 1.0
    vr = nt.nodes.new("ShaderNodeValToRGB")
    vr.color_ramp.elements[0].color = (0.25, 0.25, 0.25, 1)
    vr.color_ramp.elements[1].position = 0.6
    nt.links.new(grad.outputs["Fac"], vr.inputs["Fac"])
    nt.links.new(gridmix.outputs[2], vig.inputs[6]); nt.links.new(vr.outputs["Color"], vig.inputs[7])
    nt.links.new(vig.outputs[2], bsdf.inputs["Base Color"])
    return m


def flag_material(nation, filename):
    m, nt, bsdf = _mat("SB_Flag_" + nation)
    bsdf.inputs["Roughness"].default_value = 0.85
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = 0.4
    img = bpy.data.images.load(os.path.join(FLAGS, filename), check_existing=True)
    img.use_fake_user = True
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = 'Cubic'
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def metal(name, rgb, rough):
    m, nt, bsdf = _mat(name)
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = rough
    return m


def wood():
    m, nt, bsdf = _mat("SB_Staff")
    bsdf.inputs["Base Color"].default_value = (0.16, 0.08, 0.03, 1)
    bsdf.inputs["Roughness"].default_value = 0.5
    return m


def _obj(scn, name, data):
    o = bpy.data.objects.get(name)
    if o is not None:
        bpy.data.objects.remove(o, do_unlink=True)
    o = bpy.data.objects.new(name, data)
    scn.collection.objects.link(o)
    return o


def flag_mesh(name, w=1.34, h=0.67, nx=64, ny=32):
    """Subdivided flag cloth with UVs; vertex group 'free' rises from 0 at the hoist to 1 at the fly."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    verts = [[bm.verts.new((w * i / nx, h * (j / ny - 1.0), 0)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new([verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]])
            for loop in f.loops:
                co = loop.vert.co
                loop[uv].uv = (co.x / w, co.y / h + 1.0)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def build():
    scn = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    # Start from an empty scene every time, so re-running never leaves duplicates behind.
    for o in list(scn.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    r = scn.render
    r.engine = 'CYCLES'
    scn.cycles.samples = 48
    scn.cycles.use_denoising = True
    r.resolution_x = r.resolution_y = 444
    r.resolution_percentage = 100
    r.film_transparent = False
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGB'
    scn.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.get("SB_World") or bpy.data.worlds.new("SB_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.02, 0.025, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scn.world = world

    cam = _obj(scn, "SB_Camera", bpy.data.cameras.new("SB_Camera"))
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.0
    cam.location = (0, 0, 10); cam.rotation_euler = (0, 0, 0)
    scn.camera = cam

    sun = _obj(scn, "SB_Sun", bpy.data.lights.new("SB_Sun", 'SUN'))
    sun.data.energy = 4.0; sun.data.angle = math.radians(3)
    sun.rotation_euler = (math.radians(64), 0, math.radians(-35))
    fill = _obj(scn, "SB_Fill", bpy.data.lights.new("SB_Fill", 'SUN'))
    fill.data.energy = 0.6; fill.rotation_euler = (math.radians(55), 0, math.radians(140))

    bpy.ops.mesh.primitive_plane_add(size=2.3, location=(0, 0, 0))
    bgp = bpy.context.active_object; bgp.name = "SB_Map"
    for c in list(bgp.users_collection): c.objects.unlink(bgp)
    scn.collection.objects.link(bgp)
    bgp.data.materials.clear(); bgp.data.materials.append(map_material())

    # Staff, gilt finial (ball and spearhead), all tilted a little for movement.
    pivot = _obj(scn, "SB_Pivot", None)
    pivot.rotation_euler = (0, 0, math.radians(-7))
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.017, depth=1.25, location=(-0.62, 0.135, 0.12))
    staff = bpy.context.active_object; staff.name = "SB_Staff"
    staff.rotation_euler = (math.radians(90), 0, 0)
    gold = metal("SB_Gilt", (0.83, 0.62, 0.22), 0.25)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.035, location=(-0.62, 0.78, 0.12))
    ball = bpy.context.active_object; ball.name = "SB_FinialBall"
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.035, radius2=0.0, depth=0.12, location=(-0.62, 0.87, 0.12),
                                    rotation=(math.radians(-90), 0, 0))
    tip = bpy.context.active_object; tip.name = "SB_FinialTip"
    for o, m in ((staff, wood()), (ball, gold), (tip, gold)):
        for c in list(o.users_collection): c.objects.unlink(o)
        scn.collection.objects.link(o)
        o.data.materials.clear(); o.data.materials.append(m)
        o.parent = pivot

    # Name plate in gilt letters below the flag.
    font = next((f for f in FONTS if os.path.exists(f)), None)
    txt = _obj(scn, "SB_Name", bpy.data.curves.new("SB_Name", 'FONT'))
    if font:
        txt.data.font = bpy.data.fonts.load(font, check_existing=True)
    txt.data.align_x = 'CENTER'; txt.data.align_y = 'CENTER'
    txt.data.size = 0.19; txt.data.extrude = 0.012; txt.data.bevel_depth = 0.006
    txt.location = (0.0, -0.56, 0.05)
    txt.data.materials.clear(); txt.data.materials.append(gold)
    # Raised gilt letters, but no cast shadow: under the low sun it doubles the letters.
    txt.visible_shadow = False
    return scn, pivot, txt


def render_nation(scn, pivot, txt, nation):
    filename, title = NATIONS[nation]
    name = "SB_Flag"
    old = bpy.data.objects.get(name)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    flag = _obj(scn, name, flag_mesh("SB_FlagMesh_" + nation))
    flag.parent = pivot
    flag.location = (-0.60, 0.76, 0.12)
    flag.data.materials.append(flag_material(nation, filename))
    vg = flag.vertex_groups.new(name="free")
    w = max(v.co.x for v in flag.data.vertices)
    for v in flag.data.vertices:
        vg.add([v.index], min(1.0, (v.co.x / w) ** 1.2), 'REPLACE')
    # Ripples running along the fly, plus irregular folds; the hoist stays on the staff.
    wave = flag.modifiers.new("Ripple", 'WAVE')
    wave.use_x = True; wave.use_y = False; wave.use_normal = False
    wave.height = 0.13; wave.width = 0.30; wave.narrowness = 0.8; wave.speed = 0.0
    wave.start_position_x = 0.0; wave.time_offset = -40
    wave.vertex_group = "free"
    tex = bpy.data.textures.get("SB_Folds") or bpy.data.textures.new("SB_Folds", 'CLOUDS')
    tex.noise_scale = 0.28
    disp = flag.modifiers.new("Folds", 'DISPLACE')
    disp.texture = tex; disp.strength = 0.09; disp.vertex_group = "free"
    flag.modifiers.new("Smooth", 'SUBSURF').levels = 2
    txt.data.body = title
    # Long names get smaller letters so they fit the panel.
    txt.data.size = min(0.24, 1.85 / (0.6 * len(title)))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, nation + ".png")
    scn.render.filepath = path
    with bpy.context.temp_override(scene=scn):
        bpy.ops.render.render(write_still=True, scene=scn.name)
    return path


def render_all(nations=None):
    scn, pivot, txt = build()
    return [render_nation(scn, pivot, txt, n) for n in (nations or NATIONS)]
