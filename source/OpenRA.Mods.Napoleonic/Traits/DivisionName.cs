#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Gives the unit a division number when it is created, counted per unit type for its owner.")]
	public class DivisionNameInfo : TraitInfo
	{
		[Desc("Overrides the unit type name used in the division title. Defaults to the Tooltip name.")]
		public readonly string UnitName = null;

		public override object Create(ActorInitializer init) { return new DivisionName(this); }
	}

	public class DivisionName : INotifyCreated
	{
		readonly DivisionNameInfo info;

		public DivisionName(DivisionNameInfo info) { this.info = info; }

		public int Number { get; private set; }

		/// <summary>e.g. "1st Division".</summary>
		public string Division => $"{DivisionRegistry.Ordinal(Number)} Division";

		/// <summary>e.g. "1st Division Line Infantry".</summary>
		public string FullName { get; private set; }

		void INotifyCreated.Created(Actor self)
		{
			var registry = self.Owner.PlayerActor.TraitOrDefault<DivisionRegistry>();
			Number = registry?.NextNumber(self.Info.Name) ?? 1;

			var unitName = info.UnitName;
			if (unitName == null)
			{
				var tooltip = self.Info.TraitInfoOrDefault<TooltipInfo>();
				unitName = tooltip != null ? FluentProvider.GetMessage(tooltip.Name) : self.Info.Name;
			}

			FullName = $"{Division} {unitName}";
		}
	}
}
