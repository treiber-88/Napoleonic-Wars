# Cavalry uniform switcher for the NW_Cavalry rig. The shabraque (saddle cloth), collar and facings are player colour.
import bpy
O = bpy.data.objects
M = bpy.data.materials

COAT = ["Rider_Coat", "Rider_Tails", "Rider_UpperArm_L", "Rider_UpperArm_R", "Rider_Forearm_L", "Rider_Forearm_R"]
LEGS = ["Rider_Seat", "Rider_Thigh_L", "Rider_Thigh_R"]
HORSE = [o for o in ["Horse_Barrel", "Horse_Chest", "Horse_Rump", "Horse_Neck", "Horse_Head", "Horse_Ear_L", "Horse_Ear_R"]]
HORSE_LEGS = [f"Horse_{p}{e}{s}" for p in ("Upper", "Lower") for e in ("F", "H") for s in ("L", "R")]
HEADGEAR = ["HG_Helmet", "HG_Crest", "HG_Mane", "HG_Turban", "HG_Plume", "HG_Brush", "HG_Shako", "HG_Cap"]

# name: coat, breeches, cuirass material (None = no cuirass), headgear parts, helmet material,
#       crest/brush material, plume material, horse coat, lancer
VARIANTS = {
    # France: dragoon in green with the brass helmet, leopard-skin turban and black mane;
    # cuirassier in blue with steel cuirass, steel helmet, black mane and red plume.
    "fr_dragoon":    ("CV_DragoonGreen", "FR_White", None, ["HG_Helmet", "HG_Crest", "HG_Mane", "HG_Turban"], "FR_Brass", "FR_Brass", None, "HR_Bay", False),
    "fr_cuirassier": ("FR_ImperialBlue", "FR_White", "CV_Steel", ["HG_Helmet", "HG_Crest", "HG_Mane", "HG_Plume"], "CV_Steel", "FR_Brass", "FR_Red", "HR_Black", False),
    # Britain 1812-15: heavy dragoons in red with the brass helmet and black horsehair crest;
    # Household Cavalry (Life Guards) likewise, on black horses with a white plume.
    "gb_dragoon":    ("GB_Madder", "FR_White", None, ["HG_Helmet", "HG_Brush"], "FR_Brass", "HR_Black", None, "HR_Bay", False),
    "gb_household":  ("GB_Madder", "FR_White", None, ["HG_Helmet", "HG_Brush", "HG_Plume"], "FR_Brass", "HR_Black", "FR_White", "HR_Black", False),
    # Russia: dragoons in dark green, cuirassiers in white with black-lacquered cuirass (from 1812),
    # both with the 1808 black leather helmet and brush crest; Cossacks in dark blue with fur cap and lance.
    "ru_dragoon":    ("RU_DarkGreen", "GB_Grey", None, ["HG_Helmet", "HG_Brush"], "FR_Black", "HR_Black", None, "HR_Chestnut", False),
    "ru_cuirassier": ("AT_WhiteCoat", "FR_White", "CV_BlackIron", ["HG_Helmet", "HG_Brush"], "FR_Black", "HR_Black", None, "HR_Black", False),
    "ru_cossack":    ("PR_DarkBlue", "PR_DarkBlue", None, ["HG_Cap"], "FR_Black", "HR_Black", None, "HR_Grey", True),
    # Prussia: dragoons in the light blue litewka with grey overalls and covered shako;
    # cuirassiers in white with the black cuirass supplied by Russia in 1814 and Russian-style helmet.
    "pr_dragoon":    ("CV_LightBlue", "GB_Grey", None, ["HG_Shako"], "FR_Black", "HR_Black", None, "HR_Bay", False),
    "pr_cuirassier": ("AT_WhiteCoat", "FR_White", "CV_BlackIron", ["HG_Helmet", "HG_Brush"], "FR_Black", "HR_Black", None, "HR_Black", False),
    # Austria: dragoons and cuirassiers in white with the black leather helmet and brass comb;
    # cuirassiers wear the black-lacquered front plate.
    "au_dragoon":    ("AT_WhiteCoat", "FR_White", None, ["HG_Helmet", "HG_Crest", "HG_Brush"], "FR_Black", "FR_Black", None, "HR_Bay", False),
    "au_cuirassier": ("AT_WhiteCoat", "FR_White", "CV_BlackIron", ["HG_Helmet", "HG_Crest", "HG_Brush"], "FR_Black", "FR_Black", None, "HR_Black", False),
}


def _mat(names, m):
    for n in names:
        O[n].data.materials[0] = M[m]


def _show(names, on):
    for n in names:
        O[n].hide_render = O[n].hide_viewport = not on


def set_variant(name, poses_ns=None):
    coat, legs, cuirass, headgear, helmet, crest, plume, horse, lancer = VARIANTS[name]
    _mat(COAT, coat)
    _mat(LEGS, legs)
    _mat(["Tack_Portmanteau"], coat)
    _show(["Rider_Cuirass"], cuirass is not None)
    if cuirass:
        _mat(["Rider_Cuirass"], cuirass)
    _show(HEADGEAR, False)
    _show(headgear, True)
    _mat(["HG_Helmet"], helmet)
    _mat(["HG_Crest", "HG_Brush"], crest)
    if plume:
        _mat(["HG_Plume"], plume)
    _mat(HORSE + HORSE_LEGS, horse)
    _show(["W_Scabbard"], not lancer)
    if poses_ns is not None:
        poses_ns["STATE"]["lancer"] = lancer
