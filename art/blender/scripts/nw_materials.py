# Uniform materials for the shared soldier rig. Linear RGB. Player colour renders magenta and is remapped in game.
# All materials get a fake user so Blender keeps the ones only used by inactive uniforms.
import bpy

UNIFORM = {
    # France
    "FR_ImperialBlue": ((0.025, 0.035, 0.16), 0.0, 0.8),
    "FR_White":        ((0.80, 0.80, 0.74), 0.0, 0.8),
    "FR_Black":        ((0.02, 0.02, 0.02), 0.0, 0.5),
    "FR_Skin":         ((0.62, 0.40, 0.30), 0.0, 0.7),
    "FR_Brass":        ((0.75, 0.52, 0.18), 1.0, 0.3),
    "FR_Steel":        ((0.60, 0.60, 0.62), 1.0, 0.3),
    "FR_Walnut":       ((0.18, 0.08, 0.03), 0.0, 0.6),
    "FR_Calfskin":     ((0.35, 0.22, 0.12), 0.0, 0.9),
    "FR_Greatcoat":    ((0.35, 0.33, 0.30), 0.0, 0.9),
    "FR_Green":        ((0.03, 0.20, 0.05), 0.0, 0.8),
    "FR_Red":          ((0.45, 0.02, 0.02), 0.0, 0.8),
    "FR_Player":       ((1.0, 0.0, 1.0), 0.0, 0.7),
    # Britain
    "GB_Madder":       ((0.40, 0.035, 0.03), 0.0, 0.8),
    "GB_Grey":         ((0.12, 0.12, 0.13), 0.0, 0.8),
    "GB_BlueGrey":     ((0.14, 0.16, 0.22), 0.0, 0.8),
    # Russia
    "RU_DarkGreen":    ((0.012, 0.045, 0.022), 0.0, 0.8),
    "RU_Roll":         ((0.30, 0.28, 0.24), 0.0, 0.8),
    # Austria
    "AT_WhiteCoat":    ((0.70, 0.70, 0.64), 0.0, 0.8),
    "AT_Yellow":       ((0.75, 0.55, 0.02), 0.0, 0.8),
    # Prussia
    "PR_DarkBlue":     ((0.010, 0.016, 0.055), 0.0, 0.8),
    "PR_ShakoCover":   ((0.025, 0.025, 0.025), 0.0, 0.35),
}


def ensure_materials():
    for name, (rgb, metallic, rough) in UNIFORM.items():
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


ensure_materials()
