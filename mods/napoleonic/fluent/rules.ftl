## Factions
faction-nw-france =
    .name = France
    .description = Empire français
      The Grande Armée: dense columns, massed batteries and the best heavy cavalry in Europe.

faction-nw-britain =
    .name = Britain
    .description = United Kingdom
      Steady two-rank lines and crushing volleys ashore, the Royal Navy at sea.
      Bulldog Resolve: against an enemy force of 5,000 men or more, all British troops fight 10% harder.

faction-nw-random =
    .name = Any
    .description = A random nation.

options-starting-units =
    .hq-only = Headquarters only

## Generic names
meta-regiment-generic-name = Regiment
meta-battery-generic-name = Battery
meta-warship-generic-name = Ship of the line
meta-merchant-generic-name = Merchantman

## Buildings
actor-nwhq =
    .name = Headquarters
    .description = The army's command post: every other building is ordered from here.
      Build more to extend your base or to keep a reserve.
actor-barracks =
    .name = Barracks
    .description = Raises infantry battalions and cavalry regiments.
actor-foundry =
    .name = Foundry
    .description = Casts field guns and forms artillery batteries.
actor-shipyard =
    .name = Ship Yard
    .description = Builds ships of the line and trading ships, and is the home port of your trading ships.
      Must be built on water.
actor-countinghouse =
    .name = Counting House
    .description = Merchants and bankers who finance the war. Earns $500 every 30 seconds.
actor-nwpowcamp =
    .name = Prisoner of War Camp
    .description = Holds enemy units that surrender. Earns $500 every 30 seconds for each 1,000 prisoners held.
      If the camp is destroyed the prisoners are freed and rejoin their army.
actor-tradepost-neutral =
    .name = Neutral Port

## France — infantry
actor-fr-ligne =
    .name = Infanterie de Ligne
    .description = Line infantry with the Charleville musket. 60 figures, 3,000 men.
      Strong in standing fire, holding ground and advancing in line.
actor-fr-legere =
    .name = Infanterie Légère
    .description = Light infantry. 40 figures, 2,000 men.
      Faster, better skirmishers, forms and reforms quickly.
actor-fr-grenadier =
    .name = Grenadiers
    .description = Elite shock troops with musket and iron grenades. 20 figures, 200 men.

## France — cavalry
actor-fr-dragoon =
    .name = Dragons
    .description = Dragoons with sabre and pistol. Versatile. 30 riders, 60 men.
actor-fr-cuirassier =
    .name = Cuirassiers
    .description = Armoured heavy cavalry with heavy sabre and pistol.
      Slower, but stronger in the charge and more resilient.

## France — ships
actor-fr-bucentaure80 =
    .name = Bucentaure-class 80
    .description = 80-gun two-decker by Sané (from 1803).
      The name ship was Villeneuve's flagship at Trafalgar.
actor-fr-temeraire74 =
    .name = Téméraire-class 74
    .description = 74-gun ship of the line to Sané's standard design, the backbone of Napoleon's navy.
      Redoutable, famous at Trafalgar, was one of this class.
actor-fr-ocean118 =
    .name = Océan-class 118
    .description = 118-gun three-decker first rate by Sané.
      L'Orient, flagship at the Nile, was one of this class.

## Britain — infantry
actor-gb-line =
    .name = Line Infantry
    .description = Regiment of Foot with the Brown Bess. 60 figures, 3,000 men.
      Excellent disciplined volley fire.
actor-gb-light =
    .name = Light Infantry
    .description = Light infantry. 40 figures, 2,000 men.
      Faster, better skirmishers, forms and reforms quickly.
actor-gb-grenadier =
    .name = Grenadiers
    .description = Elite flank companies with musket and grenades. 20 figures, 200 men.

## Britain — cavalry
actor-gb-dragoon =
    .name = Heavy Dragoons
    .description = Dragoon Guards with sabre and pistol. Solid all-purpose heavy cavalry.
actor-gb-household =
    .name = Household Cavalry
    .description = Life Guards and Royal Horse Guards. Heavy sabre and pistol.
      Slower, but stronger in the charge and more resilient.

## Britain — ships
actor-gb-firstrate104 =
    .name = First Rate (104)
    .description = 104-gun three-decker first rate, the largest ships of the Royal Navy.
      HMS Victory, Nelson's flagship at Trafalgar.
actor-gb-neptune98 =
    .name = Neptune-class 98
    .description = 98-gun three-decker second rate.
      HMS Temeraire, 'The Fighting Temeraire', was one of this class.
actor-gb-arrogant74 =
    .name = Arrogant-class 74
    .description = 74-gun third rate. HMS Bellerophon, the 'Billy Ruffian',
      fought at the Glorious First of June, the Nile and Trafalgar.

## Shared
actor-battery =
    .name = Foot Artillery
    .description = A battery of eight field guns. Fires solid shot, shell or canister.
actor-tradeship =
    .name = Trading Ship
    .description = Sails to neutral or allied ports and earns $500 when it returns to your ship yard.
      Right-click it with a warship to give it an escort. Like every ship, it can carry
      one artillery battery and one regiment.

## Command bar
button-regiment-charge =
    .tooltip = Charge
    .tooltipdesc = Charge the chosen enemy with bayonet or sabre.
button-regiment-run =
    .tooltip = Run
    .tooltipdesc = Run to the chosen place, out of formation.
button-regiment-stand =
    .tooltip = Stand
    .tooltipdesc = Halt, form up and hold this ground.
button-regiment-surrender =
    .tooltip = Surrender
    .tooltipdesc = Lay down arms. The unit is marched off to the nearest enemy
    prisoner of war camp, and stays there until the camp is destroyed.

button-battery-canister =
    .tooltip = Canister
    .tooltipdesc = Short range, deadly against infantry and cavalry.
button-battery-solidshot =
    .tooltip = Solid Shot
    .tooltipdesc = Long range round shot. Best against buildings.
button-battery-shell =
    .tooltip = Shell
    .tooltipdesc = Explosive shell that strikes everything around it.

hotkey-description-regimentcharge = Charge
hotkey-description-regimentrun = Run
hotkey-description-regimentstand = Stand
hotkey-description-batterycanister = Canister
hotkey-description-batterysolidshot = Solid shot
hotkey-description-batteryshell = Shell

## ai.yaml
bot-marshal =
    .name = Marshal
bot-junot =
    .name = Junot
bot-kutuzov =
    .name = Kutuzov
bot-napoleon =
    .name = Napoleon

## Factions added
faction-nw-russia =
    .name = Russia
    .description = Russian Empire
      Stubbornness: Russian troops lose 30% less morale and rout less easily.
      Scorched Earth: routed Russian units destroy every bridge they cross.

faction-nw-prussia =
    .name = Prussia
    .description = Kingdom of Prussia (post-1807 reformed army)
      For the Fatherland: Prussian troops fight 10% harder near their headquarters.

faction-nw-austria =
    .name = Austria
    .description = Austrian Empire
      Coffee Houses: all Austrian troops march 5% faster and form up 5% faster.

## Russia
actor-ru-musketeer =
    .name = Musketeers
    .description = Line infantry with the Russian 1808 pattern musket. 60 figures, 3,000 men.
      Solid line fire and great endurance.
actor-ru-jager =
    .name = Jägers
    .description = Light infantry. 40 figures, 2,000 men.
      Faster, better skirmishers, flexible in formation.
actor-ru-grenadier =
    .name = Grenadiers
    .description = Elite assault troops with musket and grenades. 20 figures, 200 men.
actor-ru-dragoon =
    .name = Dragoons
    .description = Dragoons with sabre and pistol. 30 riders, 60 men.
actor-ru-cuirassier =
    .name = Cuirassiers
    .description = Armoured heavy cavalry with heavy broadsword and pistol.
      Slower, but heavier in the charge and better protected.
actor-ru-cossack =
    .name = Cossacks
    .description = Irregular Don Cossack horse with lance and pistol.
      Very fast and cheap, but less steady under fire.
actor-ru-chesma100 =
    .name = Chesma-class 100
    .description = 100-gun three-decker of the Baltic Fleet (1783-1790).
      Rostislav served as guardship at Kronstadt 1808-1812.
actor-ru-selafail74 =
    .name = Selafail-class 74
    .description = 74-gun ship of the line (from 1803). Selafail and Tverdyi,
      Senyavin's flagship at the Dardanelles and Athos (1807), were of this class.
actor-ru-yaroslav74 =
    .name = Yaroslav-class 74
    .description = Older 74-gun ship of the line (1784-1802), lighter and cheaper.
      Yaroslav sailed in Senyavin's Mediterranean squadron.

## Prussia
actor-pr-musketeer =
    .name = Musketiere
    .description = Line infantry of the reformed army with the Prussian musket. 60 figures, 3,000 men.
      Disciplined line fire.
actor-pr-fusilier =
    .name = Füsiliere
    .description = Light infantry battalions. 40 figures, 2,000 men.
      Faster, superior skirmishing and reform speed.
actor-pr-grenadier =
    .name = Grenadiere
    .description = Elite assault troops with musket and grenades. 20 figures, 200 men.
actor-pr-dragoon =
    .name = Dragoner
    .description = Dragoons with sabre and pistol. 30 riders, 60 men.
actor-pr-cuirassier =
    .name = Kürassiere
    .description = Heavy cavalry with heavy sabre and pistol. Slower, stronger shock troops.
actor-pr-line74 =
    .name = Ship of the Line (74)
    .description = 74-gun ship of the line. Prussia had no ships of the line in this era;
      a representative heavy ship for gameplay.
actor-pr-twodecker50 =
    .name = Two-decker (50)
    .description = 50-gun two-decker. Representative: Prussia's navy was small and coastal.
actor-pr-frigate44 =
    .name = Heavy Frigate (44)
    .description = 44-gun heavy frigate. Representative: Prussia's navy was small and coastal.

## Austria
actor-au-fusilier =
    .name = Füsiliere
    .description = German line infantry of the Austrian army. 60 figures, 3,000 men.
      Steady in line combat.
actor-au-grenzer =
    .name = Grenzer
    .description = Military Frontier light infantry from the Croatian and Slavonian border.
      40 figures, 2,000 men. Mobile skirmishers with quick formation changes.
actor-au-grenadier =
    .name = Grenadiere
    .description = Elite grenadier companies, often massed into grenadier battalions.
      20 figures, 200 men.
actor-au-dragoon =
    .name = Dragoner
    .description = Dragoons with sabre and pistol. 30 riders, 60 men.
actor-au-cuirassier =
    .name = Kürassiere
    .description = Heavy cavalry with heavy sabre and pistol. Most effective in the shock charge.
actor-au-venetian74 =
    .name = Venetian 74
    .description = 74-gun first-rank ship of the ex-Venetian navy.
      Laharpe was taken over by Austria after the capture of Ancona in 1799.
actor-au-venetian64 =
    .name = Venetian 64
    .description = 64-gun second-rank two-decker of the ex-Venetian navy.
actor-au-frigate44 =
    .name = Venetian Frigate (44)
    .description = Heavy frigate of the Adriatic squadron.
      Bellona, a Venetian frigate, was taken into Austrian service in 1798.
