#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("Lets the AI pair idle warships with its trading ships as escorts.")]
	public class EscortBotModuleInfo : ConditionalTraitInfo
	{
		[Desc("Escorts per trading ship.")]
		public readonly int EscortsPerShip = 1;

		[Desc("Ticks between checks.")]
		public readonly int Interval = 125;

		public override object Create(ActorInitializer init) { return new EscortBotModule(init.Self, this); }
	}

	public class EscortBotModule : ConditionalTrait<EscortBotModuleInfo>, IBotTick
	{
		readonly World world;
		int ticks;

		public EscortBotModule(Actor self, EscortBotModuleInfo info)
			: base(info)
		{
			world = self.World;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (--ticks > 0)
				return;

			ticks = Info.Interval;

			var idleWarships = world.ActorsHavingTrait<EscortShip>()
				.Where(a => a.Owner == bot.Player && !a.IsDead && a.IsInWorld && a.IsIdle && a.Trait<EscortShip>().Escorting == null)
				.ToList();

			if (idleWarships.Count == 0)
				return;

			// Only trading ships: an empty transport does not need a guard.
			var ships = world.ActorsHavingTrait<TradeShip>()
				.Where(a => a.Owner == bot.Player && !a.IsDead && a.IsInWorld && a.TraitOrDefault<Escortable>() != null);

			foreach (var ship in ships)
			{
				var missing = Info.EscortsPerShip - ship.Trait<Escortable>().Escorts.Count();
				while (missing-- > 0 && idleWarships.Count > 0)
				{
					var escort = idleWarships.MinBy(a => (a.CenterPosition - ship.CenterPosition).HorizontalLengthSquared);
					idleWarships.Remove(escort);
					bot.QueueOrder(new Order(EscortShip.OrderID, escort, Target.FromActor(ship), false));
				}
			}
		}
	}
}
