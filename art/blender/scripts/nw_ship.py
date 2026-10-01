from mathutils import Vector

import bpy, bmesh, math
M = bpy.data.materials

class ShipClass:
    def __init__(self, name, length, half_beam, decks, ports, masts):
        self.name, self.L, self.HB, self.decks, self.ports, self.masts = name, length, half_beam, decks, ports, masts

# Sane's standard designs. decks = gun-deck heights (m above waterline); ports = ports per side per deck.
# masts = (y position, height above waterline, yard scale) for fore, main, mizzen.
TEMERAIRE = ShipClass("TemeraireClass", 56.0, 7.45, [2.3, 4.5], [14, 15],
                      [(16.0, 52.0, 0.92), (1.0, 58.0, 1.0), (-15.0, 42.0, 0.68)])

def half_breadth(c, y, z):
    t = y / (c.L / 2)
    if t > 0.35:
        plan = math.sqrt(max(0.0, 1 - ((t - 0.35) / 0.68) ** 2))
    elif t < -0.80:
        plan = 0.86 - (-0.80 - t) * 0.9
    else:
        plan = 1.0 - 0.10 * max(0.0, -t - 0.4)
    sec = 0.93 + 0.07 * (z / 2.0) if z <= 2.0 else 1.0 - 0.17 * ((z - 2.0) / 5.0) ** 1.4
    return c.HB * plan * sec

def rail_height(c, y):
    t = y / (c.L / 2)
    return 6.6 + 1.6 * t * t + (1.4 if t < -0.55 else 0.0) + (0.8 if t > 0.62 else 0.0)

def col():
    return bpy.data.collections["TemeraireClass"]

def put(o, parent="ShipPivot", mname=None):
    for c in o.users_collection: c.objects.unlink(o)
    col().objects.link(o)
    if mname:
        o.data.materials.clear(); o.data.materials.append(M[mname])
    o.parent = bpy.data.objects[parent]; o.matrix_parent_inverse.identity()
    return o

def remove(prefix):
    for o in [o for o in col().objects if o.name.startswith(prefix)]:
        bpy.data.objects.remove(o, do_unlink=True)

def box(name, loc, size, mname, rot=(0, 0, 0), parent="ShipPivot"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.name = name; return put(o, parent, mname)

def cyl(name, loc, r, depth, mname, rot=(0, 0, 0), r2=None, verts=10, parent="ShipPivot"):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    for p in o.data.polygons: p.use_smooth = True
    return put(o, parent, mname)

def band_strip(c, name, z0, z1, mname, inset=-0.02):
    """A painted strip following the hull side between heights z0..z1, both sides."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    ys = [(-c.L/2) + 0.6 + i * (c.L - 1.2) / 60 for i in range(61)]
    for sgn in (-1, 1):
        lo = [bm.verts.new((sgn * (half_breadth(c, y, z0) - inset), y, z0)) for y in ys]
        hi = [bm.verts.new((sgn * (half_breadth(c, y, z1) - inset), y, z1)) for y in ys]
        for i in range(len(ys) - 1):
            f = [lo[i], lo[i+1], hi[i+1], hi[i]] if sgn > 0 else [lo[i], hi[i], hi[i+1], lo[i+1]]
            bm.faces.new(f)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    return put(o, "ShipPivot", mname)

def build_sides(c):
    remove("Band_"); remove("Port_"); remove("RailBand")
    for d, (z, n) in enumerate(zip(c.decks, c.ports)):
        band_strip(c, f"Band_{d}", z - 0.55, z + 0.55, "SH_Ochre")
        span = c.L * 0.78
        for i in range(n):
            y = -span / 2 + (i + 0.5) * span / n - c.L * 0.02
            for sgn in (-1, 1):
                x = sgn * (half_breadth(c, y, z) + 0.03)
                box(f"Port_{d}_{i}_{'L' if sgn<0 else 'R'}", (x, y, z), (0.08, 0.95, 0.85), "SH_PortBlack")
    # Player-colour band along the top rail (identifies the owner at a glance).
    band_strip(c, "RailBand", 6.15, 6.55, "SH_Player")

def build_ends(c):
    remove("Stern"); remove("Bow")
    yb = -c.L / 2
    w = half_breadth(c, yb + 0.5, 7.0) * 2
    box("Stern_Gallery", (0, yb - 0.35, 7.2), (w * 0.95, 0.7, 4.4), "SH_Stern")
    for row, z in enumerate((6.3, 8.2)):
        for k in range(5):
            x = (k - 2) * w * 0.17
            box(f"Stern_Window_{row}_{k}", (x, yb - 0.72, z), (w * 0.11, 0.05, 1.0), "SH_Window")
    box("Stern_Taffrail", (0, yb - 0.3, 9.55), (w * 0.9, 0.6, 0.35), "SH_Player")
    yf = c.L / 2
    cyl("Bow_Cutwater", (0, yf + 1.2, 3.2), 0.35, 6.4, "SH_HullBlack", rot=(math.radians(-18), 0, 0), verts=6)
    box("Bow_Beakhead", (0, yf + 0.6, 7.0), (5.0, 2.4, 0.5), "SH_Deck")
    cyl("Bow_Figurehead", (0, yf + 2.2, 5.6), 0.5, 1.6, "SH_Ochre", rot=(math.radians(60), 0, 0), verts=8)

def build_decks(c):
    remove("Qdeck"); remove("Fcastle")
    box("Qdeck", (0, -c.L * 0.30, 7.4), (half_breadth(c, -c.L * 0.3, 7) * 1.9, c.L * 0.36, 0.3), "SH_Deck")
    box("Fcastle", (0, c.L * 0.33, 7.3), (half_breadth(c, c.L * 0.33, 7) * 1.8, c.L * 0.18, 0.3), "SH_Deck")


def sail(name, corners, mname, billow=1.6, segs=6):
    """Quad sail from 4 corners (top-left, top-right, bottom-right, bottom-left), bellied forward (+Y)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    from mathutils import Vector
    tl, tr, br, bl = [Vector(p) for p in corners]
    grid = []
    for j in range(segs + 1):
        v = j / segs
        row = []
        for i in range(segs + 1):
            u = i / segs
            top = tl.lerp(tr, u); bot = bl.lerp(br, u)
            p = top.lerp(bot, v)
            p.y += billow * math.sin(math.pi * u) * math.sin(math.pi * min(1.0, v * 1.1 + 0.05))
            row.append(bm.verts.new(p))
        grid.append(row)
    for j in range(segs):
        for i in range(segs):
            bm.faces.new([grid[j][i], grid[j][i+1], grid[j+1][i+1], grid[j+1][i]])
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    for p in o.data.polygons: p.use_smooth = True
    return put(o, "ShipPivot", mname)

def tri(name, a, b, cpt, mname):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bm.faces.new([bm.verts.new(a), bm.verts.new(b), bm.verts.new(cpt)])
    bm.to_mesh(me); bm.free()
    return put(bpy.data.objects.new(name, me), "ShipPivot", mname)

def flag(name, origin, width, height, stripes, vertical=True, trail=-1):
    """Flag hanging from its hoist at origin, flying along Y (trail=-1 means astern)."""
    n = len(stripes); objs = []
    for k, m in enumerate(stripes):
        y0 = origin[1] + trail * width * k / n; y1 = origin[1] + trail * width * (k + 1) / n
        z0, z1 = origin[2] - height, origin[2]
        me = bpy.data.meshes.new(f"{name}_{k}"); bm = bmesh.new()
        vs = [bm.verts.new((origin[0], y0, z0)), bm.verts.new((origin[0], y1, z0)),
              bm.verts.new((origin[0], y1, z1)), bm.verts.new((origin[0], y0, z1))]
        bm.faces.new(vs); bm.to_mesh(me); bm.free()
        objs.append(put(bpy.data.objects.new(f"{name}_{k}", me), "ShipPivot", m))
    return objs

def build_rig(c):
    for p in ("Mast_", "Top_", "Yard_", "Sail_", "Furl_", "Bowsprit", "Jib", "Spanker", "Gaff", "Ensign", "Pennant"):
        remove(p)
    names = ["Fore", "Main", "Mizzen"]
    for (y, H, s), nm in zip(c.masts, names):
        base = 6.0
        cyl(f"Mast_{nm}_Lower", (0, y, (base + 0.45 * H) / 2), 0.55 * s, 0.45 * H - base, "SH_Spar", r2=0.45 * s)
        cyl(f"Mast_{nm}_Top", (0, y, 0.45 * H + (0.72 - 0.45) * H / 2), 0.36 * s, (0.72 - 0.45) * H, "SH_Spar", r2=0.26 * s)
        cyl(f"Mast_{nm}_TG", (0, y, 0.72 * H + (1.0 - 0.72) * H / 2), 0.22 * s, (1.0 - 0.72) * H, "SH_Spar", r2=0.10 * s)
        box(f"Top_{nm}", (0, y - 0.3, 0.45 * H), (5.0 * s, 4.0 * s, 0.35), "SH_Spar")
        yards = [(0.40 * H, 30 * s), (0.66 * H, 22 * s), (0.86 * H, 13.5 * s)]
        if nm == "Mizzen":
            yards = [(0.42 * H, 22 * s), (0.68 * H, 16 * s), (0.87 * H, 10 * s)]
        for k, (z, w) in enumerate(yards):
            cyl(f"Yard_{nm}_{k}", (0, y + 0.8, z), 0.28 * s, w, "SH_Spar", rot=(0, math.radians(90), 0), r2=0.16 * s)
        # Battle sail: topsail and topgallant set; the course is furled on its yard.
        (zc, wc), (zt, wt), (zg, wg) = yards
        sail(f"Sail_{nm}_Topsail", [(-wt/2, y + 1.0, zt), (wt/2, y + 1.0, zt), (wc/2*0.95, y + 1.0, zc + 1.0), (-wc/2*0.95, y + 1.0, zc + 1.0)], "SH_Canvas", billow=2.4 * s)
        sail(f"Sail_{nm}_Topgallant", [(-wg/2, y + 1.0, zg), (wg/2, y + 1.0, zg), (wt/2*0.9, y + 1.0, zt + 0.8), (-wt/2*0.9, y + 1.0, zt + 0.8)], "SH_Canvas", billow=1.4 * s)
        if nm != "Mizzen":
            cyl(f"Furl_{nm}", (0, y + 1.0, zc - 0.5), 0.55 * s, wc * 0.92, "SH_Canvas", rot=(0, math.radians(90), 0))
        # Pennant streaming aft from the masthead in the owner's colour.
        me = bpy.data.meshes.new(f"Pennant_{nm}"); bm = bmesh.new()
        vs = [bm.verts.new((0, y, H + 0.6)), bm.verts.new((0, y - 16 * s, H + 0.2)),
              bm.verts.new((0, y - 16 * s, H - 0.1)), bm.verts.new((0, y, H - 0.9))]
        bm.faces.new(vs); bm.to_mesh(me); bm.free()
        put(bpy.data.objects.new(f"Pennant_{nm}", me), "ShipPivot", "SH_Player")

    # Bowsprit and jibboom with a set jib.
    yf = c.L / 2
    cyl("Bowsprit", (0, yf + 8.0, 10.5), 0.5, 22.0, "SH_Spar", rot=(math.radians(-70), 0, 0), r2=0.22)
    fy, fH, fs = c.masts[0]
    tri("Jib", (0, fy + 0.8, 0.62 * fH), (0, yf + 17.5, 14.0), (0, yf + 4.0, 9.0), "SH_Canvas")

    # Spanker on the mizzen gaff, with the national ensign at the peak.
    my, mH, ms = c.masts[2]
    gz = 0.40 * mH
    cyl("Gaff", (0, my - 6.0, gz + 2.5), 0.2, 12.5, "SH_Spar", rot=(math.radians(-78), 0, 0))
    sail("Spanker", [(0, my - 0.5, gz + 1.0), (0, my - 12.0, gz + 4.2), (0, my - 14.5, 9.0), (0, my - 0.5, 9.0)], "SH_Canvas", billow=0.0, segs=3)
    return c


def line(name, a, b, r, mname):
    """A rope or spar between two points."""
    a = Vector(a); b = Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.active_object; o.name = name
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return put(o, "ShipPivot", mname)

def build_rigging(c):
    remove("Shroud_"); remove("Stay_"); remove("Boat_"); remove("Hatch_"); remove("Capstan")
    for k, ((y, H, s), nm) in enumerate(zip(c.masts, ["Fore", "Main", "Mizzen"])):
        top = 0.45 * H
        for sgn in (-1, 1):
            for j in range(5):
                yy = y - 2.5 + j * 1.3
                x = sgn * (half_breadth(c, yy, 6.5) + 0.6)
                line(f"Shroud_{nm}_{sgn}_{j}", (x, yy, 6.8), (sgn * 0.5, y, top), 0.16, "SH_Rope")
            # topmast shrouds from the top's edge
            for j in range(3):
                line(f"Shroud_{nm}_T{sgn}_{j}", (sgn * 2.3 * s, y - 1.0 + j * 0.9, top), (sgn * 0.3, y, 0.72 * H), 0.12, "SH_Rope")
    # Stays: fore-and-aft from each masthead forward.
    (fy, fH, fs), (my, mH, ms), (zy, zH, zs) = c.masts
    yf = c.L / 2
    line("Stay_Fore", (0, fy, 0.45 * fH), (0, yf + 3.0, 8.5), 0.2, "SH_Rope")
    line("Stay_ForeTop", (0, fy, 0.72 * fH), (0, yf + 12.0, 12.5), 0.15, "SH_Rope")
    line("Stay_Main", (0, my, 0.45 * mH), (0, fy, 8.0), 0.2, "SH_Rope")
    line("Stay_MainTop", (0, my, 0.72 * mH), (0, fy, 0.45 * fH), 0.15, "SH_Rope")
    line("Stay_Mizzen", (0, zy, 0.45 * zH), (0, my, 9.0), 0.16, "SH_Rope")
    line("Stay_MizzenTop", (0, zy, 0.72 * zH), (0, my, 0.45 * mH), 0.12, "SH_Rope")
    # Boats stowed on the booms in the waist; hatch gratings; capstan.
    for k, (bx, bl) in enumerate(((-1.6, 9.5), (1.6, 8.5), (0.0, 11.0))):
        by = 7.5 - k * 0.3
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=1.0, location=(bx, by, 7.3 + k * 0.5))
        o = bpy.context.active_object; o.name = f"Boat_{k}"; o.scale = (1.1, bl / 2, 0.55)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        put(o, "ShipPivot", "SH_BoatWhite" if k < 2 else "SH_HullBlack")
    for k, hy in enumerate((-4.0, 14.0, 20.0)):
        box(f"Hatch_{k}", (0, hy, 6.35), (2.6, 2.2, 0.25), "SH_Grating")
    cyl("Capstan", (0, -8.0, 6.9), 0.8, 1.2, "SH_Spar", verts=12)
