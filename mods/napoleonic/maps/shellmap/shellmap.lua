--[[
   Main menu battle: France (south) and Britain (north).
   The lines trade volleys for a while, then every infantry and cavalry division charges
   the nearest enemy. When an army runs low, fresh divisions march up to its battle line
   and the cycle begins again.
]]

FrenchUnits = { "fr_ligne", "fr_ligne", "fr_legere", "fr_grenadier", "fr_dragoon", "fr_cuirassier", "battery" }
BritishUnits = { "gb_line", "gb_line", "gb_light", "gb_grenadier", "gb_dragoon", "gb_household", "battery" }

FrenchEntries = { CPos.New(46, 46), CPos.New(56, 46), CPos.New(66, 46) }
BritishEntries = { CPos.New(46, 21), CPos.New(56, 21), CPos.New(66, 21) }

-- Where fresh divisions form up before the firefight.
FrenchLine = { CPos.New(48, 38), CPos.New(56, 38), CPos.New(64, 38) }
BritishLine = { CPos.New(48, 31), CPos.New(56, 31), CPos.New(64, 31) }

VolleyTime = DateTime.Seconds(18)
CycleTime = DateTime.Seconds(40)
MinimumUnits = 4

Fighters = function(player)
	return Utils.Where(player.GetActors(), function(a)
		return not a.IsDead and a.HasProperty("AttackMove")
	end)
end

Nearest = function(unit, candidates)
	local best = nil
	local bestDistance = nil
	Utils.Do(candidates, function(c)
		local v = c.CenterPosition - unit.CenterPosition
		local d = v.X * v.X + v.Y * v.Y
		if bestDistance == nil or d < bestDistance then
			best = c
			bestDistance = d
		end
	end)

	return best
end

ChargeAll = function(player, enemy)
	local targets = Fighters(enemy)
	if #targets == 0 then
		return
	end

	Utils.Do(Fighters(player), function(unit)
		if unit.HasProperty("Charge") then
			local target = Nearest(unit, targets)
			if target ~= nil and not target.IsDead then
				unit.Charge(target)
			end
		end
	end)
end

Reinforce = function(player, types, entries, line)
	if #Fighters(player) >= MinimumUnits then
		return
	end

	for i = 1, 3 do
		local unit = Actor.Create(Utils.Random(types), true, {
			Owner = player,
			Location = entries[i],
			Facing = player == France and Angle.North or Angle.South
		})

		-- Attack-move stops to open fire as soon as the enemy is in range.
		unit.AttackMove(line[i], 1)
	end
end

Cycle = function()
	Reinforce(France, FrenchUnits, FrenchEntries, FrenchLine)
	Reinforce(Britain, BritishUnits, BritishEntries, BritishLine)

	-- Trade volleys first, then go in with the bayonet and sabre.
	Trigger.AfterDelay(VolleyTime, function()
		ChargeAll(France, Britain)
		ChargeAll(Britain, France)
	end)

	Trigger.AfterDelay(CycleTime, Cycle)
end

WorldLoaded = function()
	France = Player.GetPlayer("France")
	Britain = Player.GetPlayer("Britain")

	Camera.Position = Map.CenterOfCell(CPos.New(57, 34))
	Cycle()
end
