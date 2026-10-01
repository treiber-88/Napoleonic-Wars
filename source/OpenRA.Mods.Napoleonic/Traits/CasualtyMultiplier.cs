#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Modifies the casualties this unit takes from Casualty warheads of the given damage types.",
		"Applied before casualties are rounded, so it also works on units with a small numerical value.")]
	public class CasualtyMultiplierInfo : ConditionalTraitInfo
	{
		[Desc("Damage types this modifier applies to. Leave empty for all.")]
		public readonly BitSet<DamageType> DamageTypes = default;

		[Desc("Percentage modifier to apply.")]
		public readonly int Modifier = 100;

		public override object Create(ActorInitializer init) { return new CasualtyMultiplier(this); }
	}

	public class CasualtyMultiplier : ConditionalTrait<CasualtyMultiplierInfo>
	{
		public CasualtyMultiplier(CasualtyMultiplierInfo info)
			: base(info) { }

		public int GetModifier(BitSet<DamageType> damageTypes)
		{
			if (IsTraitDisabled)
				return 100;

			return Info.DamageTypes.IsEmpty || damageTypes.Overlaps(Info.DamageTypes) ? Info.Modifier : 100;
		}
	}
}
