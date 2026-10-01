# Uniform switcher for the shared soldier rig. Within a nation, line and light infantry share one look;
# only grenadiers differ.
import bpy
O = bpy.data.objects
M = bpy.data.materials

VARIANT_ONLY = {
    "grenadier": ["GR_Bearskin", "GR_BearskinPatch", "GR_Plume", "GR_Epaulette_L", "GR_Epaulette_R", "GR_Scabbard", "GR_Hilt"],
    "british":   ["GB_ShakoBody", "GB_ShakoFront", "GB_ShakoPlate", "GB_Tuft", "GB_BeltPlate"],
    "prussian":  ["PR_Shako", "PR_Peak", "PR_Pompom"],
    "austrian":  ["AT_Shako", "AT_PeakFront", "AT_PeakRear", "AT_Cockade", "AT_CockadeCentre", "AT_Pompom"],
    "russian":   ["RU_Kiwer", "RU_KiwerCrown", "RU_KiwerBadge", "RU_KiwerCords", "RU_Pompom"],
}
# Grenadier distinctions per nation, shown on top of that nation's line uniform ("<nation>_grenadier").
GRENADIER_EXTRAS = {
    "british":  ["GBG_Plume", "GBG_Wing_L", "GBG_Wing_R", "GBG_WingLace_L", "GBG_WingLace_R"],
    "russian":  ["RUG_Grenade", "RUG_Flames", "RUG_Plume"],
    "prussian": ["PRG_Plume"],
    "austrian": ["ATG_Bearskin", "ATG_Plate", "ATG_Peak", "ATG_TopPatch"],
}
HIDDEN_UNDER = {"british": ["GB_Tuft"], "russian": ["RU_KiwerBadge"], "prussian": [], "austrian": ["AT_Shako", "AT_PeakFront", "AT_PeakRear", "AT_Cockade", "AT_CockadeCentre", "AT_Pompom"]}
RETIRED = ["LT_Epaulette_L", "LT_Epaulette_R", "LT_Plume"]      # old French light-infantry extras
FRENCH_SHAKO = ["Shako", "ShakoPlate", "Pompom"]
GREATCOAT_BANDOLIER = ["RU_Roll_Front", "RU_Roll_Back"]   # greatcoat rolled across the left shoulder
BANDOLIER_NATIONS = ("russian", "prussian")


def _mat(names, m):
    for n in names:
        O[n].data.materials[0] = M[m]


def _show(names, on):
    for n in names:
        if n in O:
            O[n].hide_render = O[n].hide_viewport = not on


def set_variant(v):
    """Uniform for a variant. "<nation>_grenadier" = that nation's line uniform plus grenadier distinctions."""
    nation, _, kind = v.partition("_")
    _set_base(nation)
    for extras in GRENADIER_EXTRAS.values():
        _show(extras, False)
    if kind == "grenadier":
        _show(GRENADIER_EXTRAS[nation], True)
        _show(HIDDEN_UNDER[nation], False)


def _set_base(v):
    """line = French fusilier; grenadier = French line grenadier; british = British line 1812-15;
    russian = Russian musketeer 1812; prussian = Prussian musketeer 1813; austrian = Austrian German line infantry 1806-15."""
    for key, objs in VARIANT_ONLY.items():
        _show(objs, key == v)
    _show(RETIRED, False)
    _show(FRENCH_SHAKO, v == "line")
    # Russians and Prussians carry the greatcoat rolled across the left shoulder instead of on the
    # knapsack, and it takes the place of the second crossbelt.
    bandolier = v in BANDOLIER_NATIONS
    _show(GREATCOAT_BANDOLIER, bandolier)
    _show(["GreatcoatRoll", "Crossbelt_Front_B", "Crossbelt_Back_B"], not bandolier)

    _mat(["Coat", "CoatTails", "UpperArm_L", "UpperArm_R", "Forearm_L", "Forearm_R"], "FR_ImperialBlue")
    _mat(["Breeches", "Lapels", "Thigh_L", "Thigh_R", "Turnbacks"], "FR_White")
    _mat(["Gaiter_L", "Gaiter_R"], "FR_Black")
    _mat(["Knapsack"], "FR_Calfskin")
    _mat(["GreatcoatRoll"], "FR_Greatcoat")

    if v == "british":
        _mat(["Coat", "CoatTails", "Lapels", "UpperArm_L", "UpperArm_R", "Forearm_L", "Forearm_R"], "GB_Madder")
        _mat(["Breeches", "Thigh_L", "Thigh_R", "Gaiter_L", "Gaiter_R"], "GB_Grey")
        _mat(["Knapsack"], "FR_Black")
        _mat(["GreatcoatRoll"], "GB_BlueGrey")
    elif v == "russian":
        _mat(["Coat", "CoatTails", "Lapels", "UpperArm_L", "UpperArm_R", "Forearm_L", "Forearm_R"], "RU_DarkGreen")
        _mat(["Turnbacks"], "FR_Red")
        _mat(["Knapsack"], "FR_Black")
    elif v == "austrian":
        # White coat without lapels, white breeches, short black gaiters; brown calfskin knapsack.
        _mat(["Coat", "CoatTails", "Lapels", "UpperArm_L", "UpperArm_R", "Forearm_L", "Forearm_R"], "AT_WhiteCoat")
    elif v == "prussian":
        # Dark blue kollet, grey campaign trousers, calfskin knapsack.
        _mat(["Coat", "CoatTails", "Lapels", "UpperArm_L", "UpperArm_R", "Forearm_L", "Forearm_R"], "PR_DarkBlue")
        _mat(["Breeches", "Thigh_L", "Thigh_R", "Gaiter_L", "Gaiter_R"], "GB_Grey")
        _mat(["Turnbacks"], "FR_Red")
