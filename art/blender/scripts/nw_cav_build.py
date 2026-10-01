# Builds the shared cavalry rig (horse + rider) in scene NW_Cavalry from primitives parented to pivot empties.
# Horse faces +Y. Metres. Run inside Blender.
import bpy, math

SCENE, COLL = "NW_Cavalry", "Cavalry"
R = math.radians


def _mat(name, rgb, metallic=0.0, rough=0.8):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*rgb, 1)
        b.inputs["Metallic"].default_value = metallic
        b.inputs["Roughness"].default_value = rough
        m.diffuse_color = (*rgb, 1)
    m.use_fake_user = True
    return m


def materials():
    # Horses and tack.
    _mat("HR_Bay", (0.16, 0.065, 0.025), rough=0.55)
    _mat("HR_Black", (0.018, 0.015, 0.014), rough=0.45)
    _mat("HR_Chestnut", (0.30, 0.10, 0.03), rough=0.55)
    _mat("HR_Grey", (0.45, 0.44, 0.42), rough=0.6)
    _mat("HR_Hoof", (0.03, 0.025, 0.02), rough=0.5)
    _mat("HR_Leather", (0.10, 0.045, 0.02), rough=0.6)
    # Cavalry uniform colours.
    _mat("CV_DragoonGreen", (0.02, 0.07, 0.03))
    _mat("CV_LightBlue", (0.10, 0.22, 0.45))
    _mat("CV_Steel", (0.55, 0.56, 0.58), metallic=1.0, rough=0.25)
    _mat("CV_BlackIron", (0.02, 0.02, 0.022), metallic=0.8, rough=0.3)
    _mat("CV_Leopard", (0.45, 0.30, 0.10))


def coll(scn):
    c = bpy.data.collections.get(COLL)
    if c is None:
        c = bpy.data.collections.new(COLL)
        scn.collection.children.link(c)
    return c


def bone(c, name, parent, loc):
    e = bpy.data.objects.get(name)
    if e is None:
        e = bpy.data.objects.new(name, None)
        c.objects.link(e)
    e.empty_display_size = 0.08
    e.parent = bpy.data.objects[parent] if parent else None
    e.location = loc
    e.rotation_mode = 'XYZ'
    e.rotation_euler = (0, 0, 0)
    return e


def part(c, name, parent, prim, loc, mname, rot=(0, 0, 0), **kw):
    O = bpy.data.objects
    if O.get(name):
        bpy.data.objects.remove(O[name], do_unlink=True)
    if prim == "box":
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
        o = bpy.context.active_object; o.scale = kw["size"]
    elif prim == "ball":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=kw["r"], location=loc, rotation=rot)
        o = bpy.context.active_object; o.scale = kw.get("scale", (1, 1, 1))
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=kw["r"], radius2=kw.get("r2", kw["r"]),
                                        depth=kw["depth"], location=loc, rotation=rot)
        o = bpy.context.active_object
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    o.name = name
    for cc in o.users_collection:
        cc.objects.unlink(o)
    c.objects.link(o)
    o.data.materials.clear()
    o.data.materials.append(bpy.data.materials[mname])
    o.parent = O[parent]
    o.matrix_parent_inverse.identity()
    if prim != "box":
        for p in o.data.polygons:
            p.use_smooth = True
    return o


def build():
    scn = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = scn
    materials()
    c = coll(scn)

    # ---- Pivots ----
    bone(c, "CV_Facing", None, (0, 0, 0))
    bone(c, "CV_Root", "CV_Facing", (0, 0, 0))            # tilts for falls
    bone(c, "HorseBody", "CV_Root", (0, 0, 1.25))         # withers ~1.55 m (a 15-16 hand troop horse)
    bone(c, "HorseNeck", "HorseBody", (0, 0.70, 0.18))
    bone(c, "HorseHead", "HorseNeck", (0, 0.42, 0.55))
    bone(c, "HorseTail", "HorseBody", (0, -0.82, 0.12))
    for side, x in (("L", -0.17), ("R", 0.17)):
        for end, y in (("F", 0.55), ("H", -0.55)):
            bone(c, f"Leg{end}{side}", "HorseBody", (x, y, -0.18))
            bone(c, f"Knee{end}{side}", f"Leg{end}{side}", (0, 0, -0.45))
    bone(c, "Rider", "HorseBody", (0, 0.05, 0.30))        # seat in the saddle
    bone(c, "RiderChest", "Rider", (0, 0, 0.10))
    bone(c, "RiderHead", "RiderChest", (0, 0, 0.55))
    for side, x in (("L", -0.2), ("R", 0.2)):
        bone(c, f"RShoulder_{side}", "RiderChest", (x, 0, 0.47))
        bone(c, f"RElbow_{side}", f"RShoulder_{side}", (0, 0, -0.28))
        bone(c, f"RHip_{side}", "Rider", (x * 0.8, 0.0, 0.0))
        bone(c, f"RKnee_{side}", f"RHip_{side}", (0, 0.42, 0.0))

    # ---- Horse ----
    part(c, "Horse_Barrel", "HorseBody", "ball", (0, 0, 0), "HR_Bay", r=1.0, scale=(0.31, 0.82, 0.37))
    part(c, "Horse_Chest", "HorseBody", "ball", (0, 0.55, 0.03), "HR_Bay", r=1.0, scale=(0.29, 0.32, 0.37))
    part(c, "Horse_Rump", "HorseBody", "ball", (0, -0.55, 0.05), "HR_Bay", r=1.0, scale=(0.32, 0.34, 0.36))
    part(c, "Horse_Neck", "HorseNeck", "cone", (0, 0.15, 0.30), "HR_Bay", rot=(R(-35), 0, 0), r=0.24, r2=0.15, depth=0.78)
    part(c, "Horse_Mane", "HorseNeck", "box", (0, 0.02, 0.42), "HR_Black", rot=(R(-35), 0, 0), size=(0.05, 0.08, 0.70))
    part(c, "Horse_Head", "HorseHead", "cone", (0, 0.20, -0.10), "HR_Bay", rot=(R(-120), 0, 0), r=0.13, r2=0.085, depth=0.58)
    part(c, "Horse_Ear_L", "HorseHead", "cone", (-0.05, -0.02, 0.10), "HR_Bay", r=0.03, r2=0.005, depth=0.12)
    part(c, "Horse_Ear_R", "HorseHead", "cone", (0.05, -0.02, 0.10), "HR_Bay", r=0.03, r2=0.005, depth=0.12)
    part(c, "Horse_Bridle", "HorseHead", "box", (0, 0.20, -0.08), "HR_Leather", rot=(R(-30), 0, 0), size=(0.23, 0.03, 0.03))
    part(c, "Horse_Tail", "HorseTail", "cone", (0, -0.12, -0.28), "HR_Black", rot=(R(25), 0, 0), r=0.07, r2=0.02, depth=0.65)
    for side in ("L", "R"):
        for end in ("F", "H"):
            part(c, f"Horse_Upper{end}{side}", f"Leg{end}{side}", "cone", (0, 0, -0.20), "HR_Bay", r=0.12, r2=0.07, depth=0.48)
            part(c, f"Horse_Lower{end}{side}", f"Knee{end}{side}", "cone", (0, 0, -0.26), "HR_Bay", r=0.052, r2=0.045, depth=0.52)
            part(c, f"Horse_Hoof{end}{side}", f"Knee{end}{side}", "cone", (0, 0.01, -0.55), "HR_Hoof", r=0.055, r2=0.045, depth=0.08)

    # ---- Saddle and shabraque (player colour: the largest readable area on a horse) ----
    part(c, "Tack_Shabraque", "HorseBody", "box", (0, -0.05, 0.25), "FR_Player", size=(0.64, 0.88, 0.03))
    part(c, "Tack_ShabraqueSide_L", "HorseBody", "box", (-0.33, -0.05, 0.08), "FR_Player", size=(0.02, 0.82, 0.30))
    part(c, "Tack_ShabraqueSide_R", "HorseBody", "box", (0.33, -0.05, 0.08), "FR_Player", size=(0.02, 0.82, 0.30))
    part(c, "Tack_Saddle", "HorseBody", "box", (0, 0.05, 0.29), "HR_Leather", size=(0.36, 0.55, 0.08))
    part(c, "Tack_Portmanteau", "HorseBody", "cone", (0, -0.42, 0.30), "CV_DragoonGreen", rot=(0, R(90), 0), r=0.08, depth=0.50)
    part(c, "Tack_Holster_L", "HorseBody", "cone", (-0.14, 0.40, 0.25), "HR_Leather", rot=(R(-60), 0, 0), r=0.04, depth=0.28)
    part(c, "Tack_Holster_R", "HorseBody", "cone", (0.14, 0.40, 0.25), "HR_Leather", rot=(R(-60), 0, 0), r=0.04, depth=0.28)

    # ---- Rider (coat/headgear materials set per variant) ----
    part(c, "Rider_Seat", "Rider", "box", (0, 0, 0.02), "FR_White", size=(0.34, 0.26, 0.12))
    part(c, "Rider_Coat", "RiderChest", "box", (0, 0, 0.25), "FR_ImperialBlue", size=(0.38, 0.23, 0.50))
    part(c, "Rider_Tails", "RiderChest", "box", (0, -0.13, 0.02), "FR_ImperialBlue", size=(0.30, 0.05, 0.22))
    part(c, "Rider_Facings", "RiderChest", "box", (0, 0.118, 0.30), "FR_Player", size=(0.16, 0.01, 0.30))
    part(c, "Rider_Collar", "RiderChest", "cone", (0, 0, 0.51), "FR_Player", r=0.085, depth=0.07)
    part(c, "Rider_Belt", "RiderChest", "box", (0, 0.12, 0.22), "FR_White", rot=(0, R(-35), 0), size=(0.05, 0.01, 0.58))
    part(c, "Rider_Cuirass", "RiderChest", "ball", (0, 0.03, 0.26), "CV_Steel", r=1.0, scale=(0.215, 0.15, 0.27))
    part(c, "Rider_Face", "RiderHead", "ball", (0, 0.01, 0.09), "FR_Skin", r=0.095)
    # Headgear pieces (shown per variant).
    part(c, "HG_Helmet", "RiderHead", "ball", (0, 0, 0.16), "FR_Brass", r=0.115, scale=(1, 1.1, 0.95))
    part(c, "HG_Crest", "RiderHead", "box", (0, -0.02, 0.28), "FR_Brass", size=(0.03, 0.26, 0.10))
    part(c, "HG_Mane", "RiderHead", "box", (0, -0.16, 0.12), "HR_Black", rot=(R(20), 0, 0), size=(0.07, 0.06, 0.40))
    part(c, "HG_Turban", "RiderHead", "cone", (0, 0, 0.12), "CV_Leopard", r=0.12, depth=0.06)
    part(c, "HG_Plume", "RiderHead", "cone", (-0.11, 0.02, 0.36), "FR_Red", r=0.03, r2=0.012, depth=0.25)
    part(c, "HG_Brush", "RiderHead", "box", (0, 0.0, 0.33), "HR_Black", size=(0.06, 0.24, 0.14))
    part(c, "HG_Shako", "RiderHead", "cone", (0, 0, 0.21), "PR_ShakoCover", r=0.098, r2=0.104, depth=0.20)
    part(c, "HG_Cap", "RiderHead", "cone", (0, 0, 0.22), "FR_Black", r=0.10, r2=0.09, depth=0.24)
    for side in ("L", "R"):
        part(c, f"Rider_UpperArm_{side}", f"RShoulder_{side}", "cone", (0, 0, -0.14), "FR_ImperialBlue", r=0.05, depth=0.28)
        part(c, f"Rider_Forearm_{side}", f"RElbow_{side}", "cone", (0, 0, -0.11), "FR_ImperialBlue", r=0.045, depth=0.22)
        part(c, f"Rider_Glove_{side}", f"RElbow_{side}", "ball", (0, 0, -0.26), "FR_White", r=0.045)
        part(c, f"Rider_Thigh_{side}", f"RHip_{side}", "cone", (0, 0.21, 0), "FR_White", rot=(R(-90), 0, 0), r=0.07, depth=0.44)
        part(c, f"Rider_Boot_{side}", f"RKnee_{side}", "cone", (0, 0.02, -0.25), "FR_Black", r=0.065, r2=0.055, depth=0.52)
    # Weapons in the right hand (shown per pose): sabre, pistol; Cossack lance.
    part(c, "W_Sabre", "RElbow_R", "box", (0, 0.0, -0.62), "FR_Steel", size=(0.02, 0.035, 0.80))
    part(c, "W_Hilt", "RElbow_R", "ball", (0, 0, -0.27), "FR_Brass", r=0.035)
    part(c, "W_Pistol", "RElbow_R", "box", (0, 0.10, -0.28), "FR_Walnut", size=(0.03, 0.26, 0.05))
    part(c, "W_Lance", "RElbow_R", "cone", (0, 0.0, -0.30), "FR_Walnut", r=0.018, r2=0.012, depth=2.9)
    part(c, "W_LanceHead", "RElbow_R", "cone", (0, 0.0, 1.25), "FR_Steel", r=0.025, r2=0.002, depth=0.20)
    part(c, "W_Scabbard", "Rider", "box", (-0.24, -0.20, -0.30), "FR_Steel", rot=(R(-35), 0, 0), size=(0.03, 0.04, 0.80))
    return scn
