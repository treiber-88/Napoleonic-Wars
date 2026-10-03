"""
Writes mods/napoleonic/rules/ai.yaml: the skirmish AIs. They share one set of unit lists and differ in
how much they build, how large a force they gather before attacking, and how they use the Charge command.

Usage: python art/tools/make_ai_yaml.py
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mods", "napoleonic", "rules", "ai.yaml")

LINE = ["fr_ligne", "gb_line", "ru_musketeer", "pr_musketeer", "au_fusilier"]
LIGHT = ["fr_legere", "gb_light", "ru_jager", "pr_fusilier", "au_grenzer"]
GRENADIERS = ["fr_grenadier", "gb_grenadier", "ru_grenadier", "pr_grenadier", "au_grenadier"]
# Cavalry weights: 60% of the first Marshal AI's (2026-10-02), then halved again (rounded) the same day,
# with the infantry weights raised to take their place.
CAVALRY = {"fr_dragoon": 5, "fr_cuirassier": 3, "gb_dragoon": 5, "gb_household": 3, "ru_dragoon": 4, "ru_cuirassier": 3,
           "ru_cossack": 4, "pr_dragoon": 5, "pr_cuirassier": 3, "au_dragoon": 5, "au_cuirassier": 3}
# Every AI builds a navy where it has water: the workhorse classes most, one flagship.
SHIPS = {"fr_temeraire74": 6, "fr_bucentaure80": 4, "fr_ocean118": 2, "gb_arrogant74": 6, "gb_neptune98": 4, "gb_firstrate104": 2,
         "ru_selafail74": 6, "ru_yaroslav74": 4, "ru_chesma100": 2, "pr_twodecker50": 6, "pr_frigate44": 6, "pr_line74": 3,
         "au_venetian64": 6, "au_frigate44": 6, "au_venetian74": 3}
FLAGSHIPS = ["fr_ocean118", "gb_firstrate104", "ru_chesma100"]

BOTS = {
    # The original AI: builds up at home and marches only with a large force.
    "marshal": dict(
        comment="Marshal: the all-rounder. Builds up at home and only marches out with a large force.",
        barracks=3, foundry=2, shipyard=2, countinghouse=4, cash_threshold=4000,
        squad=12, squad_bonus=4, attack_delay=3000, attack_interval=150,
        idle_max=None, batteries=4, battery_weight=15, tradeships=3, picket=1, escort=True,
        charge=40, own_morale=65, ignore_odds=False),
    # Junot: careless, and keeps a small army.
    "junot": dict(
        comment="Junot: careless. Raises few troops, throws them in a handful at a time, posts no picket,\n"
                "# leaves his trading ships unescorted and charges without counting the enemy.",
        barracks=1, foundry=1, shipyard=1, countinghouse=1, cash_threshold=9000,
        squad=3, squad_bonus=2, attack_delay=0, attack_interval=150,
        idle_max=5, batteries=1, battery_weight=8, tradeships=1, picket=0, escort=False,
        charge=40, own_morale=40, ignore_odds=True),
    # Kutuzov: a large army that he is slow to commit.
    "kutuzov": dict(
        comment="Kutuzov: patient. Raises a very large army, holds it at home far longer and seldom charges.",
        barracks=4, foundry=2, shipyard=2, countinghouse=4, cash_threshold=3000,
        squad=22, squad_bonus=6, attack_delay=9000, attack_interval=300,
        idle_max=None, batteries=5, battery_weight=15, tradeships=3, picket=2, escort=True,
        charge=20, own_morale=75, ignore_odds=False),
    # Napoleon: strong economy, the largest army and artillery park, attacks early in strength,
    # pulls shaken regiments out of the line to recover instead of letting them rout.
    "napoleon": dict(
        comment="Napoleon: builds his economy first and the largest army and artillery park, attacks early in strength,\n"
                "# charges only when the odds are right and withdraws shaken regiments to rally them.",
        barracks=6, foundry=3, shipyard=2, countinghouse=6, cash_threshold=2000,
        squad=14, squad_bonus=4, attack_delay=1200, attack_interval=75,
        idle_max=None, batteries=8, battery_weight=24, tradeships=4, picket=2, escort=True,
        charge=40, own_morale=70, ignore_odds=False, withdraw=35, min_cash=250),
}


def units(b):
    u = {}
    for n in LINE: u[n] = 50
    for n in LIGHT: u[n] = 30
    for n in GRENADIERS: u[n] = 12
    u.update(CAVALRY)
    u["battery"] = b["battery_weight"]
    u.update(SHIPS)
    u["tradeship"] = 6
    return u


def bot_yaml(name, b):
    cond = f"enable-{name}-ai"
    y = []
    y.append(f"\t# {b['comment']}")
    y.append(f"\tModularBot@{name}:")
    y.append(f"\t\tName: bot-{name}.name")
    y.append(f"\t\tType: {name}")
    y.append(f"\tGrantConditionOnBotOwner@{name}:")
    y.append(f"\t\tCondition: {cond}")
    y.append(f"\t\tBots: {name}")
    y.append(f"\tBaseBuilderBotModule@{name}:")
    y.append(f"\t\tRequiresCondition: {cond}")
    y.append("\t\tConstructionYardTypes: nwhq")
    y.append("\t\tProductionTypes: barracks, foundry")
    y.append("\t\tNavalProductionTypes: shipyard")
    y.append("\t\tInititalMinimumRefineryCount: 0")
    y.append("\t\tAdditionalMinimumRefineryCount: 0")
    y.append(f"\t\tNewProductionCashThreshold: {b['cash_threshold']}")
    y.append("\t\tMaxBaseRadius: 16")
    y.append("\t\t# Look as far as the base reaches for water, so a ship yard is built wherever the coast allows.")
    y.append("\t\tCheckForWaterRadius: 16")
    y.append("\t\tBuildingLimits:")
    for k in ("barracks", "foundry", "shipyard", "countinghouse"):
        y.append(f"\t\t\t{k}: {b[k]}")
    y.append("\t\t\tnwpowcamp: 1")
    y.append("\t\tBuildingFractions:")
    y.append("\t\t\tbarracks: 4")
    y.append("\t\t\tcountinghouse: 3")
    y.append("\t\t\tfoundry: 2")
    y.append("\t\t\tshipyard: 2")
    y.append("\t\t\tnwpowcamp: 1")
    y.append("\t\tBuildingDelays:")
    y.append("\t\t\tfoundry: 2000")
    y.append("\t\t\tcountinghouse: 500")
    y.append("\t\t\tshipyard: 1500")
    y.append("\t\t\tnwpowcamp: 2500")
    y.append(f"\tSquadManagerBotModule@{name}:")
    y.append(f"\t\tRequiresCondition: {cond}")
    y.append(f"\t\tSquadSize: {b['squad']}")
    y.append(f"\t\tSquadSizeRandomBonus: {b['squad_bonus']}")
    y.append("\t\t# Never send the engine's scripted early rush.")
    y.append("\t\tRushInterval: 1000000")
    y.append(f"\t\tAttackForceInterval: {b['attack_interval']}")
    y.append(f"\t\tMinimumAttackForceDelay: {b['attack_delay']}")
    y.append("\t\tConstructionYardTypes: nwhq")
    y.append("\t\tNavalProductionTypes: shipyard")
    y.append("\t\tNavalUnitsTypes: " + ", ".join(SHIPS))
    y.append("\t\tExcludeFromSquadsTypes: tradeship")
    y.append("\t\tProtectionTypes: nwhq, barracks, foundry, shipyard, countinghouse, nwpowcamp, tradeship")
    y.append("\t\tProtectUnitScanRadius: 15")
    y.append("\t\tProtectionScanRadius: 14")
    y.append("\t\tMaxBaseRadius: 24")
    y.append(f"\tUnitBuilderBotModule@{name}:")
    y.append(f"\t\tRequiresCondition: {cond}")
    if b.get("min_cash") is not None:
        y.append("\t\t# Keeps the barracks busy even when funds run low.")
        y.append(f"\t\tProductionMinCashRequirement: {b['min_cash']}")
    if b["idle_max"] is not None:
        y.append("\t\t# Stops raising troops once this many stand idle at the base.")
        y.append(f"\t\tIdleBaseUnitsMaximum: {b['idle_max']}")
    y.append("\t\tUnitsToBuild:")
    for k, v in units(b).items():
        y.append(f"\t\t\t{k}: {v}")
    y.append("\t\tUnitLimits:")
    y.append(f"\t\t\tbattery: {b['batteries']}")
    y.append(f"\t\t\ttradeship: {b['tradeships']}")
    for f in FLAGSHIPS:
        y.append(f"\t\t\t{f}: 1")
    if b["picket"]:
        y.append(f"\tPicketBotModule@{name}:")
        y.append(f"\t\tRequiresCondition: {cond}")
        y.append("\t\tUnitTypes: " + ", ".join(sorted(LINE + LIGHT)))
        y.append("\t\tBaseTypes: nwhq")
        y.append(f"\t\tPickets: {b['picket']}")
        y.append("\t\tDistance: 14c0")
        y.append("\t\tInterval: 50")
    if b["escort"]:
        y.append(f"\tEscortBotModule@{name}:")
        y.append(f"\t\tRequiresCondition: {cond}")
    y.append(f"\tRegimentTacticsBotModule@{name}:")
    y.append(f"\t\tRequiresCondition: {cond}")
    y.append("\t\tCavalryTypes: " + ", ".join(CAVALRY))
    y.append("\t\tGrenadierTypes: " + ", ".join(GRENADIERS))
    y.append("\t\tArtilleryTypes: battery")
    y.append(f"\t\tChargeChancePercent: {b['charge']}")
    y.append(f"\t\tMinOwnMoralePercent: {b['own_morale']}")
    if b["ignore_odds"]:
        y.append("\t\tIgnoreOdds: true")
    if b.get("withdraw"):
        y.append(f"\t\tWithdrawMoralePercent: {b['withdraw']}")
    return "\n".join(y)


def main():
    head = ("# Skirmish AIs. GENERATED by art/tools/make_ai_yaml.py: edit that script, not this file.\n"
            "# All of them fight by fire and charge sparingly: only guns, routed or badly shaken units\n"
            "# (cavalry also clearly weaker cavalry), and each opportunity is only taken ChargeChancePercent of the time.\n\n"
            "Player:\n"
            "\tBuildingRepairBotModule:\n"
            "\t\tRequiresCondition: " + " || ".join(f"enable-{n}-ai" for n in BOTS) + "\n")
    body = "\n".join(bot_yaml(n, b) for n, b in BOTS.items())
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + body + "\n")
    print("wrote", os.path.normpath(OUT), "with", len(BOTS), "bots")


if __name__ == "__main__":
    main()
