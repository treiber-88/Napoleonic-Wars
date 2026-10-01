#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Frozen;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("Keeps one or more regiments posted as a forward picket some distance from the AI's headquarters,",
		"towards the middle of the map. A lost or reassigned picket is replaced by the next available regiment.")]
	public class PicketBotModuleInfo : ConditionalTraitInfo
	{
		[FieldLoader.Require]
		[Desc("Unit types that may be sent out as pickets.")]
		public readonly FrozenSet<string> UnitTypes = FrozenSet<string>.Empty;

		[FieldLoader.Require]
		[Desc("Headquarters types the picket position is measured from.")]
		public readonly FrozenSet<string> BaseTypes = FrozenSet<string>.Empty;

		[Desc("Number of regiments to keep on picket duty.")]
		public readonly int Pickets = 1;

		[Desc("Distance of the picket post from the headquarters.")]
		public readonly WDist Distance = WDist.FromCells(14);

		[Desc("A picket further than this from its post is sent back once idle.")]
		public readonly WDist Tolerance = WDist.FromCells(4);

		[Desc("Ticks between checks.")]
		public readonly int Interval = 50;

		public override object Create(ActorInitializer init) { return new PicketBotModule(init.Self, this); }
	}

	public class PicketBotModule : ConditionalTrait<PicketBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Actor[] pickets;
		int ticks;

		public PicketBotModule(Actor self, PicketBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			pickets = new Actor[info.Pickets];
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (--ticks > 0)
				return;

			ticks = Info.Interval;

			var hq = world.Actors.FirstOrDefault(a => a.Owner == bot.Player && !a.IsDead && a.IsInWorld && Info.BaseTypes.Contains(a.Info.Name));
			if (hq == null)
				return;

			for (var i = 0; i < pickets.Length; i++)
			{
				var post = PostFor(hq, i);
				var p = pickets[i];

				if (p == null || p.IsDead || !p.IsInWorld || p.Owner != bot.Player)
				{
					p = pickets[i] = world.Actors
						.Where(a => a.Owner == bot.Player && !a.IsDead && a.IsInWorld && a.IsIdle
							&& Info.UnitTypes.Contains(a.Info.Name) && !pickets.Contains(a))
						.MinByOrDefault(a => (a.CenterPosition - hq.CenterPosition).LengthSquared);

					if (p == null)
						continue;
				}

				// Send the picket (back) to its post whenever it is idle and away from it.
				if (!p.IsIdle)
					continue;

				var dist = (p.CenterPosition - world.Map.CenterOfCell(post)).HorizontalLengthSquared;
				if (dist > (long)Info.Tolerance.Length * Info.Tolerance.Length)
					bot.QueueOrder(new Order("Move", p, Target.FromCell(world, post), false));
			}
		}

		CPos PostFor(Actor hq, int index)
		{
			var map = world.Map;
			var mapCenter = map.CenterOfCell(new MPos(map.MapSize.Width / 2, map.MapSize.Height / 2).ToCPos(map));

			// Towards the middle of the map; if the HQ already sits there, go south.
			var dir = mapCenter - hq.CenterPosition;
			dir = new WVec(dir.X, dir.Y, 0);
			var len = dir.HorizontalLength;
			if (len < 2048)
			{
				dir = new WVec(0, 1024, 0);
				len = 1024;
			}

			var offset = dir * Info.Distance.Length / len;

			// Spread several pickets across the front.
			if (pickets.Length > 1)
				offset = offset.Rotate(WRot.FromYaw(new WAngle((2 * index - (pickets.Length - 1)) * 48)));

			return map.Clamp(map.CellContaining(hq.CenterPosition + offset));
		}
	}
}
