#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Linq;
using OpenRA.GameRules;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Mods.Napoleonic.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Warheads
{
	[Desc("Damages the figures of Formation units near the impact, and ordinary actors (buildings, ships) whose hit shape is within Spread.",
		"Against a Formation, each figure struck costs Casualties hundredths of a figure's numerical value (fractions are rounded randomly).",
		"Against anything else, Damage is dealt as usual. Versus applies to both.")]
	public class CasualtyWarhead : DamageWarhead
	{
		[Desc("A figure (or hit shape) within this distance of the impact is struck.")]
		public readonly WDist Spread = new(96);

		[Desc("Maximum number of figures one impact can strike (1 for a musket ball, more for shells and round shot).")]
		public readonly int MaxModels = 1;

		[Desc("Hundredths of one figure's numerical value lost per figure struck. 100 = the figure falls.")]
		public readonly int Casualties = 0;

		[Desc("Largest distance between a Formation's centre and its figures, used to find victims.")]
		public readonly WDist FormationSearchRadius = new(5120);

		protected override void DoImpact(WPos pos, Actor firedBy, WarheadArgs args)
		{
			var world = firedBy.World;
			var victims = world.FindActorsInCircle(pos, Spread + FormationSearchRadius).ToList();
			foreach (var victim in victims)
			{
				if (victim.IsDead || !IsValidAgainst(victim, firedBy))
					continue;

				var formation = victim.TraitOrDefault<Formation>();
				if (formation != null)
				{
					var struck = formation.CountModelsWithin(pos, Spread, MaxModels);
					if (struck == 0)
						continue;

					// Work in hundredths of a point of numerical value to keep fractional casualties.
					var hundredths = (long)Casualties * struck * formation.NumericalPerModel;
					var modifiers = args.DamageModifiers.Append(ArmorVersus(victim))
						.Concat(victim.TraitsImplementing<CasualtyMultiplier>().Select(m => m.GetModifier(DamageTypes)));
					hundredths = Util.ApplyPercentageModifiers((int)System.Math.Min(hundredths, int.MaxValue), modifiers);

					var damage = (int)(hundredths / 100);
					if (world.SharedRandom.Next(100) < hundredths % 100)
						damage++;

					if (damage > 0)
						victim.InflictDamage(firedBy, new Damage(damage, DamageTypes));

					continue;
				}

				HitShape closest = null;
				var closestDistance = int.MaxValue;
				foreach (var tp in victim.EnabledTargetablePositions)
				{
					if (tp is HitShape h)
					{
						var d = h.DistanceFromEdge(victim, pos).Length;
						if (d < closestDistance)
						{
							closestDistance = d;
							closest = h;
						}
					}
				}

				if (closest != null && closestDistance <= Spread.Length)
					InflictDamage(victim, firedBy, closest, args);
			}
		}

		int ArmorVersus(Actor victim)
		{
			if (Versus.Count == 0)
				return 100;

			return Util.ApplyPercentageModifiers(100, victim.TraitsImplementing<Armor>()
				.Where(a => !a.IsTraitDisabled && a.Info.Type != null && Versus.ContainsKey(a.Info.Type))
				.Select(a => Versus[a.Info.Type]));
		}
	}
}
