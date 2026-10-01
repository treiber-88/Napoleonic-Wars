# Parametric builder for every ship class (generalises nw_ship.py, which built the Temeraire class).
# Each class lives in its own collection in scene NW_TemeraireClass with its own pivot, so classes can be
# rebuilt and rendered independently with the shared sprite camera, sun and shadow catcher (SH_SpriteRig).
#
# Sources for dimensions/armament (gun-deck length, beam, ports per side per deck):
#   Bucentaure class: 59.3 m x 15.3 m; 30 x 36pdr lower, 32 x 24pdr upper (Wikipedia, Bucentaure-class).
#   Ocean class: 65.18 m x 16.24 m; 32 / 34 / 34 guns on three decks (Wikipedia, Ocean-class).
#   HMS Victory (First Rate): 56.7 m x 15.7 m; 30 / 28 / 30 guns; black and yellow "Nelson chequer".
#   Neptune class: 56 m x 16 m (185 ft x 51 ft); 28 / 30 / 30 guns.
#   Arrogant class: 51.2 m x 14.2 m; 28 / 28 guns.
#   Yaroslav class: 51.8 m x 14.2 m (upper deck); 26+2 / 26+2 guns (ru.wikipedia, Vseslav 1784).
#   Chesma class: 100-gun three-decker said to be modelled on Slade's Victory (warhistory.org); Victory's lines used.
#   Selafail class (from 1803): Kronstadt 74, somewhat larger than the Yaroslavs.
#   Venetian "1780" class 70/74 (Laharpe, Austrian 1799), Fama class 64/66 (26 x 18pdr, 26 x 12pdr, 12 x 6pdr),
#   Venetian heavy frigates: shorter, beamier Adriatic designs; dimensions estimated from the class ratings.
#   Prussia had no sea-going fleet: representative British-pattern 74 / 50 / 44 used.
import bpy, bmesh, math
from mathutils import Vector

M = bpy.data.materials
SCENE = "NW_TemeraireClass"


class Spec:
    def __init__(self, key, coll, prefix, L, HB, decks, ports, main_h=None, rig=1.0, paint="french",
                 ensign="france", guns_on_spar=True, merchant=False):
        self.key, self.coll, self.P = key, coll, prefix
        self.L, self.HB, self.decks, self.ports = L, HB, decks, ports
        self.rail = decks[-1] + 2.1 if not merchant else decks[-1] + 1.6
        H = (main_h or min(L * 1.04, 64.0)) * rig
        k = L / 56.0
        # (y position, height above waterline, yard scale) for fore, main, mizzen.
        self.masts = [(0.29 * L, 0.90 * H, 0.92 * k * rig), (0.02 * L, H, 1.0 * k * rig), (-0.27 * L, 0.72 * H, 0.68 * k * rig)]
        self.k = k
        self.paint, self.ensign, self.merchant = paint, ensign, merchant


SPECS = {
    # France (Sane's standard designs)
    "fr_bucentaure_class": Spec("fr_bucentaure_class", "BucentaureClass", "BUC", 59.3, 7.65, [2.3, 4.5], [15, 16]),
    "fr_ocean_class": Spec("fr_ocean_class", "OceanClass", "OCN", 65.2, 8.12, [2.2, 4.3, 6.3], [16, 17, 17], main_h=64.0),
    # Britain
    "gb_firstrate": Spec("gb_firstrate", "FirstRateClass", "VIC", 56.7, 7.85, [2.1, 4.1, 6.1], [15, 14, 15],
                         main_h=62.0, paint="british", ensign="england"),
    "gb_neptune_class": Spec("gb_neptune_class", "NeptuneClass", "NEP", 56.0, 7.8, [2.1, 4.1, 6.1], [14, 15, 15],
                             main_h=60.0, paint="british", ensign="england"),
    "gb_arrogant_class": Spec("gb_arrogant_class", "ArrogantClass", "ARR", 51.2, 7.1, [2.2, 4.3], [14, 14],
                              paint="british", ensign="england"),
    # Russia
    "ru_chesma_class": Spec("ru_chesma_class", "ChesmaClass", "CHE", 56.4, 7.8, [2.1, 4.1, 6.1], [15, 15, 15],
                            main_h=61.0, paint="russian", ensign="russia"),
    "ru_selafail_class": Spec("ru_selafail_class", "SelafailClass", "SEL", 53.3, 7.3, [2.2, 4.4], [14, 15],
                              paint="russian", ensign="russia"),
    "ru_yaroslav_class": Spec("ru_yaroslav_class", "YaroslavClass", "YAR", 51.8, 7.1, [2.2, 4.3], [14, 14],
                              paint="russian", ensign="russia"),
    # Prussia (representative)
    "pr_line74": Spec("pr_line74", "PrussianLine74", "PR74", 51.5, 7.1, [2.2, 4.3], [14, 14],
                      paint="prussian", ensign="prussia"),
    "pr_twodecker50": Spec("pr_twodecker50", "PrussianTwoDecker50", "PR50", 44.5, 6.1, [2.0, 4.0], [11, 12],
                           paint="prussian", ensign="prussia"),
    "pr_frigate44": Spec("pr_frigate44", "PrussianFrigate44", "PR44", 45.0, 6.0, [2.5], [14],
                         paint="prussian", ensign="prussia"),
    # Austria (ex-Venetian)
    "au_venetian74": Spec("au_venetian74", "Venetian74", "VE74", 50.0, 7.1, [2.2, 4.3], [14, 14], rig=0.95,
                          paint="venetian", ensign="austria"),
    "au_venetian64": Spec("au_venetian64", "Venetian64", "VE64", 46.0, 6.5, [2.1, 4.1], [13, 13], rig=0.95,
                          paint="venetian", ensign="austria"),
    "au_frigate44": Spec("au_frigate44", "VenetianFrigate44", "VE44", 43.5, 5.9, [2.5], [13], rig=0.95,
                         paint="venetian", ensign="austria"),
    # Merchant ship (trading ship): full-rigged merchantman with painted-on ports, flying the owner's colours.
    "nw_merchantman": Spec("nw_merchantman", "Merchantman", "MER", 36.0, 5.0, [2.3], [9], main_h=36.0,
                           paint="merchant", ensign=None, merchant=True),
}


# ---------- materials ----------

def _wood_variant(name, src, rgb):
    """Copy of one of the procedural wood materials (planking, grain, weathering) in a new colour."""
    m = M.get(name)
    if m is None:
        m = M[src].copy(); m.name = name
    for nd in m.node_tree.nodes:
        if nd.type == 'RGB':
            nd.outputs[0].default_value = (*rgb, 1)
    m.diffuse_color = (*rgb, 1)
    m.use_fake_user = True
    return m


def _flat(name, rgb, rough=0.8):
    m = M.get(name) or M.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*rgb, 1)
    m.use_fake_user = True
    return m


def materials():
    _wood_variant("SH_WhiteBand", "SH_Ochre", (0.72, 0.70, 0.64))
    _wood_variant("SH_Varnish", "SH_Deck", (0.42, 0.27, 0.12))       # oiled natural timber (Venetian / merchant)
    _wood_variant("SH_RedStrake", "SH_Ochre", (0.40, 0.07, 0.04))    # red-ochre upper strake
    _flat("SH_FlagBlack", (0.02, 0.02, 0.02))
    _flat("SH_FlagYellow", (0.85, 0.62, 0.05))
    for n, rgb in (("SH_FlagBlue", (0.0, 0.03, 0.30)), ("SH_FlagWhite", (0.85, 0.85, 0.85)), ("SH_FlagRed", (0.70, 0.02, 0.03))):
        if n not in M:
            _flat(n, rgb)


# hull, band (wales between the gun decks), stern gallery, upper strake
PAINT = {
    "french": ("SH_HullBlack", "SH_Ochre", "SH_Stern", "SH_HullBlack"),
    "british": ("SH_HullBlack", "SH_Ochre", "SH_Ochre", "SH_HullBlack"),       # Nelson chequer
    "russian": ("SH_HullBlack", "SH_Ochre", "SH_Stern", "SH_HullBlack"),
    "prussian": ("SH_HullBlack", "SH_WhiteBand", "SH_Stern", "SH_HullBlack"),
    "venetian": ("SH_Varnish", "SH_HullBlack", "SH_RedStrake", "SH_RedStrake"),
    "merchant": ("SH_Varnish", "SH_HullBlack", "SH_Stern", "SH_Varnish"),
}


# ---------- helpers ----------

class B:
    """Builder bound to one ship class."""

    def __init__(self, c):
        self.c = c
        scn = bpy.data.scenes[SCENE]
        col = bpy.data.collections.get(c.coll)
        if col is None:
            col = bpy.data.collections.new(c.coll)
            scn.collection.children.link(col)
        self.col = col
        pv = bpy.data.objects.get(c.P + "_Pivot")
        if pv is None:
            pv = bpy.data.objects.new(c.P + "_Pivot", None)
            col.objects.link(pv)
        self.pivot = pv

    def clear(self):
        for o in [o for o in self.col.objects if o is not self.pivot]:
            bpy.data.objects.remove(o, do_unlink=True)
        self.pivot.rotation_euler = (0, 0, 0)

    def put(self, o, mname=None):
        for cc in o.users_collection:
            cc.objects.unlink(o)
        self.col.objects.link(o)
        if mname:
            o.data.materials.clear(); o.data.materials.append(M[mname])
        o.parent = self.pivot; o.matrix_parent_inverse.identity()
        return o

    def n(self, name):
        return self.c.P + "_" + name

    def box(self, name, loc, size, mname, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
        o = bpy.context.active_object; o.scale = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        o.name = self.n(name); return self.put(o, mname)

    def cyl(self, name, loc, r, depth, mname, rot=(0, 0, 0), r2=None, verts=10):
        if r2 is None:
            bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
        else:
            bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
        o = bpy.context.active_object; o.name = self.n(name)
        for p in o.data.polygons: p.use_smooth = True
        return self.put(o, mname)

    def mesh(self, name, verts, faces, mname, smooth=False):
        me = bpy.data.meshes.new(self.n(name)); me.from_pydata(verts, [], faces); me.update()
        o = bpy.data.objects.new(self.n(name), me)
        if smooth:
            for p in o.data.polygons: p.use_smooth = True
        return self.put(o, mname)

    def line(self, name, a, b, r, mname):
        a = Vector(a); b = Vector(b); d = b - a
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=d.length, location=(a + b) / 2)
        o = bpy.context.active_object; o.name = self.n(name)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
        return self.put(o, mname)

    # ----- hull form -----
    def half_breadth(self, y, z):
        c = self.c
        t = y / (c.L / 2)
        if t > 0.35:
            plan = math.sqrt(max(0.0, 1 - ((t - 0.35) / 0.68) ** 2))
        elif t < -0.80:
            plan = 0.86 - (-0.80 - t) * 0.9
        else:
            plan = 1.0 - 0.10 * max(0.0, -t - 0.4)
        top = c.rail - 1.6
        sec = 0.93 + 0.07 * (z / 2.0) if z <= 2.0 else 1.0 - 0.17 * ((z - 2.0) / top) ** 1.4
        return c.HB * plan * sec

    def rail_height(self, y):
        c = self.c
        t = y / (c.L / 2)
        return c.rail + 1.6 * t * t + (1.4 if t < -0.55 else 0.0) + (0.8 if t > 0.62 else 0.0)


# ---------- parts ----------

def build_hull(b):
    c = b.c
    hull_m, band_m, stern_m, strake_m = PAINT[c.paint]
    bm = bmesh.new()
    ys = [(-c.L / 2) + i * c.L / 40 for i in range(41)]
    zs = [0.0, 0.8, 1.6, 2.0] + [2.0 + (c.rail - 2.0) * i / 6 for i in range(1, 6)]
    rings = []
    for y in ys:
        top = b.rail_height(y)
        zl = [z for z in zs if z < top] + [top]
        pts = [(-b.half_breadth(y, z), z) for z in reversed(zl)] + [(b.half_breadth(y, z), z) for z in zl]
        rings.append([bm.verts.new((x, y, z)) for (x, z) in pts])
    N = 2 * (len(zs) + 1)
    secs = [[r[round(i * (len(r) - 1) / (N - 1))] for i in range(N)] for r in rings]
    for s0, s1 in zip(secs, secs[1:]):
        for i in range(N - 1):
            f = [s0[i], s0[i + 1], s1[i + 1], s1[i]]
            if len(set(f)) == 4:
                try: bm.faces.new(f)
                except ValueError: pass
    for s in (secs[0], secs[-1]):
        uniq = list(dict.fromkeys(s))
        if len(uniq) >= 3:
            try: bm.faces.new(uniq)
            except ValueError: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(b.n("Hull")); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(b.n("Hull"), me)
    for p in o.data.polygons: p.use_smooth = True
    b.put(o, hull_m)
    # Deck, slightly below the rail.
    zd = c.rail - 0.4
    v = [(-b.half_breadth(y, zd) + 0.4, y, zd) for y in ys] + [(b.half_breadth(y, zd) - 0.4, y, zd) for y in ys]
    n = len(ys)
    b.mesh("Deck", v, [(i, n + i, n + i + 1, i + 1) for i in range(n - 1)], "SH_Deck")


def band_strip(b, name, z0, z1, mname, inset=-0.02):
    c = b.c
    ys = [(-c.L / 2) + 0.6 + i * (c.L - 1.2) / 60 for i in range(61)]
    verts, faces = [], []
    for sgn in (-1, 1):
        base = len(verts)
        verts += [(sgn * (b.half_breadth(y, z0) - inset), y, z0) for y in ys]
        verts += [(sgn * (b.half_breadth(y, z1) - inset), y, z1) for y in ys]
        n = len(ys)
        for i in range(n - 1):
            lo, lo1, hi, hi1 = base + i, base + i + 1, base + n + i, base + n + i + 1
            faces.append((lo, lo1, hi1, hi) if sgn > 0 else (lo, hi, hi1, lo1))
    return b.mesh(name, verts, faces, mname)


def build_sides(b):
    c = b.c
    hull_m, band_m, stern_m, strake_m = PAINT[c.paint]
    for d, (z, n) in enumerate(zip(c.decks, c.ports)):
        band_strip(b, f"Band_{d}", z - 0.55, z + 0.55, band_m)
        span = c.L * (0.78 - 0.04 * (len(c.decks) - 1 - d))
        for i in range(n):
            y = -span / 2 + (i + 0.5) * span / n - c.L * 0.02
            for sgn in (-1, 1):
                x = sgn * (b.half_breadth(y, z) + 0.03)
                b.box(f"Port_{d}_{i}_{'L' if sgn < 0 else 'R'}", (x, y, z), (0.08, 0.95, 0.85), "SH_PortBlack")
    if strake_m != hull_m:
        band_strip(b, "Strake", c.decks[-1] + 0.6, c.rail - 0.5, strake_m)
    band_strip(b, "RailBand", c.rail - 0.45, c.rail - 0.05, "SH_Player")


def build_ends(b):
    c = b.c
    hull_m, band_m, stern_m, strake_m = PAINT[c.paint]
    nd = len(c.decks)
    yb = -c.L / 2
    w = b.half_breadth(yb + 0.5, c.rail) * 2
    z0, z1 = c.decks[-1] - 0.3, c.rail + 3.0
    b.box("Stern_Gallery", (0, yb - 0.35, (z0 + z1) / 2), (w * 0.95, 0.7, z1 - z0), stern_m)
    rows = [c.rail + 1.6] + [c.rail - 0.3 - 2.0 * k for k in range(nd - (0 if c.merchant else 1))]
    for r, z in enumerate(rows):
        if z < z0 + 0.4:
            continue
        for k in range(5):
            b.box(f"Stern_Window_{r}_{k}", ((k - 2) * w * 0.17, yb - 0.72, z), (w * 0.11, 0.05, 1.0), "SH_Window")
    if nd >= 3 and not c.merchant:
        # Three-deckers: open stern walk with a balustrade below the admiral's cabin.
        b.box("Stern_Walk", (0, yb - 1.0, c.rail - 1.2), (w * 0.9, 1.2, 0.2), "SH_Deck")
        b.box("Stern_Balustrade", (0, yb - 1.55, c.rail - 0.7), (w * 0.9, 0.12, 0.9), stern_m)
    b.box("Stern_Taffrail", (0, yb - 0.3, z1 + 0.35), (w * 0.9, 0.6, 0.35), "SH_Player")
    yf = c.L / 2
    dz = c.rail - 6.6
    b.cyl("Bow_Cutwater", (0, yf + 1.2, 3.2 + dz / 2), 0.35, 6.4 + dz, hull_m, rot=(math.radians(-18), 0, 0), verts=6)
    b.box("Bow_Beakhead", (0, yf + 0.6, c.rail + 0.4), (5.0 * c.k, 2.4, 0.5), "SH_Deck")
    b.cyl("Bow_Figurehead", (0, yf + 2.2, c.rail - 1.0), 0.5, 1.6, band_m if band_m != "SH_HullBlack" else "SH_Ochre",
          rot=(math.radians(60), 0, 0), verts=8)
    # Quarterdeck and forecastle.
    b.box("Qdeck", (0, -c.L * 0.30, c.rail + 0.8), (b.half_breadth(-c.L * 0.3, c.rail) * 1.9, c.L * 0.36, 0.3), "SH_Deck")
    b.box("Fcastle", (0, c.L * 0.33, c.rail + 0.7), (b.half_breadth(c.L * 0.33, c.rail) * 1.8, c.L * 0.18, 0.3), "SH_Deck")


def sail(b, name, corners, mname, billow=1.6, segs=6):
    tl, tr, br, bl = [Vector(p) for p in corners]
    verts, faces = [], []
    for j in range(segs + 1):
        v = j / segs
        for i in range(segs + 1):
            u = i / segs
            p = tl.lerp(tr, u).lerp(bl.lerp(br, u), v)
            p.y += billow * math.sin(math.pi * u) * math.sin(math.pi * min(1.0, v * 1.1 + 0.05))
            verts.append(tuple(p))
    W = segs + 1
    for j in range(segs):
        for i in range(segs):
            faces.append((j * W + i, j * W + i + 1, (j + 1) * W + i + 1, (j + 1) * W + i))
    return b.mesh(name, verts, faces, mname, smooth=True)


def build_rig(b):
    c = b.c
    base = c.rail - 0.6
    for (y, H, s), nm in zip(c.masts, ["Fore", "Main", "Mizzen"]):
        b.cyl(f"Mast_{nm}_Lower", (0, y, (base + 0.45 * H) / 2), 0.55 * s, 0.45 * H - base, "SH_Spar", r2=0.45 * s)
        b.cyl(f"Mast_{nm}_Top", (0, y, 0.45 * H + 0.27 * H / 2), 0.36 * s, 0.27 * H, "SH_Spar", r2=0.26 * s)
        b.cyl(f"Mast_{nm}_TG", (0, y, 0.72 * H + 0.28 * H / 2), 0.22 * s, 0.28 * H, "SH_Spar", r2=0.10 * s)
        b.box(f"Top_{nm}", (0, y - 0.3, 0.45 * H), (5.0 * s, 4.0 * s, 0.35), "SH_Spar")
        yards = [(0.40 * H, 30 * s), (0.66 * H, 22 * s), (0.86 * H, 13.5 * s)]
        if nm == "Mizzen":
            yards = [(0.42 * H, 22 * s), (0.68 * H, 16 * s), (0.87 * H, 10 * s)]
        for k, (z, w) in enumerate(yards):
            b.cyl(f"Yard_{nm}_{k}", (0, y + 0.8, z), 0.28 * s, w, "SH_Spar", rot=(0, math.radians(90), 0), r2=0.16 * s)
        (zc, wc), (zt, wt), (zg, wg) = yards
        sail(b, f"Sail_{nm}_Topsail", [(-wt / 2, y + 1.0, zt), (wt / 2, y + 1.0, zt), (wc / 2 * 0.95, y + 1.0, zc + 1.0),
                                       (-wc / 2 * 0.95, y + 1.0, zc + 1.0)], "SH_Canvas", billow=2.4 * s)
        sail(b, f"Sail_{nm}_Topgallant", [(-wg / 2, y + 1.0, zg), (wg / 2, y + 1.0, zg), (wt / 2 * 0.9, y + 1.0, zt + 0.8),
                                          (-wt / 2 * 0.9, y + 1.0, zt + 0.8)], "SH_Canvas", billow=1.4 * s)
        if nm != "Mizzen":
            b.cyl(f"Furl_{nm}", (0, y + 1.0, zc - 0.5), 0.55 * s, wc * 0.92, "SH_Canvas", rot=(0, math.radians(90), 0))
        # Pennant streaming aft from the masthead in the owner's colour.
        b.mesh(f"Pennant_{nm}", [(0, y, H + 0.6), (0, y - 16 * s, H + 0.2), (0, y - 16 * s, H - 0.1), (0, y, H - 0.9)],
               [(0, 1, 2, 3)], "SH_Player")
    yf = c.L / 2
    dz = c.rail - 6.6
    b.cyl("Bowsprit", (0, yf + 8.0 * c.k, 10.5 * c.k + dz), 0.5 * c.k, 22.0 * c.k, "SH_Spar", rot=(math.radians(-70), 0, 0), r2=0.22 * c.k)
    fy, fH, fs = c.masts[0]
    b.mesh("Jib", [(0, fy + 0.8, 0.62 * fH), (0, yf + 17.5 * c.k, 14.0 * c.k + dz), (0, yf + 4.0 * c.k, 9.0 * c.k + dz)],
           [(0, 1, 2)], "SH_Canvas")
    my, mH, ms = c.masts[2]
    gz = 0.40 * mH
    gl = 12.5 * c.k
    b.cyl("Gaff", (0, my - gl * 0.48, gz + 2.5), 0.2, gl, "SH_Spar", rot=(math.radians(-78), 0, 0))
    sail(b, "Spanker", [(0, my - 0.5, gz + 1.0), (0, my - 12.0 * c.k, gz + 4.2), (0, my - 14.5 * c.k, c.rail + 2.4),
                        (0, my - 0.5, c.rail + 2.4)], "SH_Canvas", billow=0.0, segs=3)
    # Ensign at the gaff peak, flying aft.
    peak = (0.0, my - gl * 0.97, gz + 2.5 + gl / 2 * math.cos(math.radians(78)) + 0.3)
    if c.ensign:
        ensign(b, c.ensign, peak, 9.0 * c.k, 6.0 * c.k)
    else:
        ensign(b, "owner", peak, 7.0 * c.k, 4.5 * c.k)


def ensign(b, nation, origin, W, Hh):
    """National naval ensigns c.1805, hoisted at `origin` and flying aft (-Y). (u, v): 0..1 along fly / down."""
    ox, oy, oz = origin

    def P(u, v):
        return (ox, oy - u * W, oz - v * Hh)

    def quad(name, u0, v0, u1, v1, m):
        b.mesh(name, [P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)], [(0, 1, 2, 3)], m)

    def diag(name, a, c_, t, m):
        """Thin band from a to c_ (u, v points), thickness t in v units."""
        b.mesh(name, [P(a[0], a[1] - t), P(c_[0], c_[1] - t), P(c_[0], c_[1] + t), P(a[0], a[1] + t)], [(0, 1, 2, 3)], m)

    eps = 0.002   # push emblems a hair off the field so they render in front
    if nation == "france":        # tricolore, blue at the hoist
        quad("Ensign_0", 0, 0, 1 / 3, 1, "SH_FlagBlue"); quad("Ensign_1", 1 / 3, 0, 2 / 3, 1, "SH_FlagWhite")
        quad("Ensign_2", 2 / 3, 0, 1, 1, "SH_FlagRed")
    elif nation == "england":     # red ensign with the Union in the canton
        quad("Ensign_0", 0, 0, 1, 1, "SH_FlagRed")
        ox += eps
        quad("Ensign_1", 0, 0, 0.5, 0.5, "SH_FlagBlue")
        ox += eps
        diag("Ensign_2", (0, 0), (0.5, 0.5), 0.06, "SH_FlagWhite"); diag("Ensign_3", (0, 0.5), (0.5, 0), 0.06, "SH_FlagWhite")
        quad("Ensign_4", 0.2, 0, 0.3, 0.5, "SH_FlagWhite"); quad("Ensign_5", 0, 0.18, 0.5, 0.32, "SH_FlagWhite")
        ox += eps
        quad("Ensign_6", 0.22, 0, 0.28, 0.5, "SH_FlagRed"); quad("Ensign_7", 0, 0.21, 0.5, 0.29, "SH_FlagRed")
    elif nation == "russia":      # St Andrew's ensign: white with a blue saltire
        quad("Ensign_0", 0, 0, 1, 1, "SH_FlagWhite")
        ox += eps
        diag("Ensign_1", (0, 0), (1, 1), 0.09, "SH_FlagBlue"); diag("Ensign_2", (0, 1), (1, 0), 0.09, "SH_FlagBlue")
    elif nation == "prussia":     # white with the black eagle
        quad("Ensign_0", 0, 0, 1, 1, "SH_FlagWhite")
        ox += eps
        quad("Ensign_1", 0.4, 0.3, 0.6, 0.75, "SH_FlagBlack")
        diag("Ensign_2", (0.25, 0.3), (0.75, 0.3), 0.08, "SH_FlagBlack")
    elif nation == "austria":     # 1786 naval ensign: red-white-red with the crowned shield
        quad("Ensign_0", 0, 0, 1, 1 / 3, "SH_FlagRed"); quad("Ensign_1", 0, 1 / 3, 1, 2 / 3, "SH_FlagWhite")
        quad("Ensign_2", 0, 2 / 3, 1, 1, "SH_FlagRed")
        ox += eps
        quad("Ensign_3", 0.25, 0.3, 0.42, 0.7, "SH_FlagRed"); quad("Ensign_4", 0.29, 0.45, 0.38, 0.55, "SH_FlagWhite")
        quad("Ensign_5", 0.27, 0.22, 0.40, 0.3, "SH_FlagYellow")
    else:                         # merchantman: owner's colours
        quad("Ensign_0", 0, 0, 1, 1, "SH_Player")


def build_rigging(b):
    c = b.c
    for (y, H, s), nm in zip(c.masts, ["Fore", "Main", "Mizzen"]):
        top = 0.45 * H
        for sgn in (-1, 1):
            for j in range(5):
                yy = y - 2.5 + j * 1.3
                x = sgn * (b.half_breadth(yy, c.rail - 0.1) + 0.6)
                b.line(f"Shroud_{nm}_{sgn}_{j}", (x, yy, c.rail + 0.2), (sgn * 0.5, y, top), 0.16, "SH_Rope")
            for j in range(3):
                b.line(f"Shroud_{nm}_T{sgn}_{j}", (sgn * 2.3 * s, y - 1.0 + j * 0.9, top), (sgn * 0.3, y, 0.72 * H), 0.12, "SH_Rope")
    (fy, fH, fs), (my, mH, ms), (zy, zH, zs) = c.masts
    yf = c.L / 2
    dz = c.rail - 6.6
    b.line("Stay_Fore", (0, fy, 0.45 * fH), (0, yf + 3.0, 8.5 + dz), 0.2, "SH_Rope")
    b.line("Stay_ForeTop", (0, fy, 0.72 * fH), (0, yf + 12.0 * c.k, 12.5 * c.k + dz), 0.15, "SH_Rope")
    b.line("Stay_Main", (0, my, 0.45 * mH), (0, fy, 8.0 + dz), 0.2, "SH_Rope")
    b.line("Stay_MainTop", (0, my, 0.72 * mH), (0, fy, 0.45 * fH), 0.15, "SH_Rope")
    b.line("Stay_Mizzen", (0, zy, 0.45 * zH), (0, my, 9.0 + dz), 0.16, "SH_Rope")
    b.line("Stay_MizzenTop", (0, zy, 0.72 * zH), (0, my, 0.45 * mH), 0.12, "SH_Rope")
    # Boats on the booms in the waist, hatch gratings, capstan.
    for k, (bx, bl) in enumerate(((-1.6, 9.5), (1.6, 8.5), (0.0, 11.0))):
        if c.merchant and k == 2:
            continue
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=1.0,
                                             location=(bx, c.L * 0.13 - k * 0.3, c.rail + 0.7 + k * 0.5))
        o = bpy.context.active_object; o.name = b.n(f"Boat_{k}"); o.scale = (1.1, bl * c.k / 2, 0.55)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        b.put(o, "SH_BoatWhite" if k < 2 else "SH_HullBlack")
    for k, hy in enumerate((-0.07, 0.25, 0.36)):
        b.box(f"Hatch_{k}", (0, hy * c.L, c.rail - 0.25), (2.6 * c.k, 2.2 * c.k, 0.25), "SH_Grating")
    b.cyl("Capstan", (0, -0.14 * c.L, c.rail + 0.3), 0.8, 1.2, "SH_Spar", verts=12)


def build(key):
    materials()
    c = SPECS[key]
    b = B(c)
    b.clear()
    build_hull(b)
    build_sides(b)
    build_ends(b)
    build_rig(b)
    build_rigging(b)
    return {"objects": len(b.col.objects), "coll": c.coll}


# ---------- rendering ----------

def isolate(key):
    """Show only this class (and the shared sprite rig) at render time."""
    c = SPECS[key]
    scn = bpy.data.scenes[SCENE]
    for cc in scn.collection.children:
        if cc.name == "SH_SpriteRig":
            continue
        cc.hide_render = cc.name != c.coll
        cc.hide_viewport = cc.name != c.coll


def gpu_temp():
    import subprocess
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
                                  capture_output=True, text=True, timeout=10).stdout.strip())
    except Exception:
        return 0


def render(key, first=0, last=32, out_root=r"D:\Napoleonic Wars\art\renders", max_temp=66,
           throttle_hi=60, throttle_lo=55, budget_s=200):
    """Render facings first..last-1, duty-cycling the GPU: at throttle_hi pause until it is back to throttle_lo.
    Stops early at max_temp or after budget_s seconds; returns (out_dir, next_frame)."""
    import os, time
    t0 = time.time()
    c = SPECS[key]
    scn = bpy.data.scenes[SCENE]
    isolate(key)
    pv = bpy.data.objects[c.P + "_Pivot"]
    out = os.path.join(out_root, key)
    os.makedirs(out, exist_ok=True)
    for i in range(first, last):
        pv.rotation_euler.z = 2 * math.pi * i / 32
        path = os.path.join(out, f"idle_{i:02d}.png")
        scn.render.filepath = path
        for attempt in range(5):
            try:
                with bpy.context.temp_override(scene=scn):
                    bpy.ops.render.render(write_still=True, scene=scn.name)
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    break
            except RuntimeError:
                pass
            time.sleep(1.0)
        t = gpu_temp()
        if t >= max_temp or time.time() - t0 > budget_s:
            pv.rotation_euler.z = 0
            return out, i + 1
        if t >= throttle_hi:
            while gpu_temp() > throttle_lo and time.time() - t0 < budget_s:
                time.sleep(3.0)
    pv.rotation_euler.z = 0
    return out, last


def restore_visibility():
    scn = bpy.data.scenes[SCENE]
    for cc in scn.collection.children:
        cc.hide_render = cc.name not in ("TemeraireClass", "SH_SpriteRig") and cc.name != "SH_SpriteRig"
        cc.hide_viewport = cc.hide_render


ORDER = ["fr_bucentaure_class", "fr_ocean_class", "gb_firstrate", "gb_neptune_class", "gb_arrogant_class",
         "ru_chesma_class", "ru_selafail_class", "ru_yaroslav_class", "pr_line74", "pr_twodecker50", "pr_frigate44",
         "au_venetian74", "au_venetian64", "au_frigate44", "nw_merchantman"]


def missing(key, out_root=r"D:\Napoleonic Wars\art\renders"):
    import os
    d = os.path.join(out_root, key)
    return [i for i in range(32) if not os.path.exists(os.path.join(d, f"idle_{i:02d}.png"))]


def render_queue(budget_s=200, start_max=54):
    """One cooled batch: render the next missing frames across all classes (in ORDER) until the budget or
    heat limit is hit. Refuses to start unless the GPU is below start_max."""
    import time
    t = gpu_temp()
    if t >= start_max:
        return {"skipped_hot": t}
    t0 = time.time(); done = []
    todo = [(key, i) for key in ORDER for i in missing(key)]
    for key, i in todo:
        left = budget_s - (time.time() - t0)
        if left <= 0 or gpu_temp() >= 66:
            break
        render(key, i, i + 1, budget_s=left)
        done.append(f"{key}:{i}")
    restore_visibility()
    remaining = {k: len(missing(k)) for k in ORDER if missing(k)}
    return {"start": t, "rendered": len(done), "last": done[-1] if done else None, "end": gpu_temp(),
            "sec": round(time.time() - t0), "remaining": remaining}
