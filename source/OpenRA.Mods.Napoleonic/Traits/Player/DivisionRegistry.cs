#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Generic;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("Numbers each player's divisions per unit type: 1st Division, 2nd Division, ...")]
	public class DivisionRegistryInfo : TraitInfo<DivisionRegistry> { }

	public class DivisionRegistry
	{
		readonly Dictionary<string, int> counters = [];

		public int NextNumber(string unitType)
		{
			counters.TryGetValue(unitType, out var n);
			counters[unitType] = ++n;
			return n;
		}

		public static string Ordinal(int n)
		{
			var suffix = (n % 100) is >= 11 and <= 13 ? "th" : (n % 10) switch
			{
				1 => "st",
				2 => "nd",
				3 => "rd",
				_ => "th",
			};

			return n + suffix;
		}
	}
}
