#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Effects;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Marks a building as a trading post that trade ships sail to and from.")]
	public class TradingPostInfo : TraitInfo<TradingPost> { }

	public class TradingPost { }

	[Desc("Sails to the nearest neutral or allied trading post, loads goods, and pays out when it returns to its home post.")]
	public class TradeShipInfo : TraitInfo, Requires<IMoveInfo>
	{
		[Desc("Cash paid to the owner each time the ship returns home with goods.")]
		public readonly int Payment = 500;

		[Desc("The ship counts as docked when this close to a post.")]
		public readonly WDist DockDistance = WDist.FromCells(5);

		[Desc("Ticks spent trading at the foreign post.")]
		public readonly int LoadTicks = 75;

		[Desc("Ticks spent unloading at home.")]
		public readonly int UnloadTicks = 50;

		[Desc("Ticks to ignore a post that could not be reached.")]
		public readonly int UnreachableCooldown = 750;

		public readonly bool ShowTicks = true;

		public override object Create(ActorInitializer init) { return new TradeShip(this); }
	}

	public class TradeShip : INotifyCreated, INotifyIdle, ISync
	{
		readonly TradeShipInfo info;
		readonly Dictionary<Actor, int> unreachableUntil = [];
		IMove move;
		Actor home;
		Actor destination;
		WPos lastAttemptFrom;
		int waitTicks;

		[VerifySync]
		public bool Carrying { get; private set; }

		public TradeShip(TradeShipInfo info) { this.info = info; }

		void INotifyCreated.Created(Actor self)
		{
			move = self.Trait<IMove>();
		}

		static IEnumerable<Actor> Posts(World world) =>
			world.ActorsHavingTrait<TradingPost>().Where(a => !a.IsDead && a.IsInWorld);

		Actor NearestPost(Actor self, IEnumerable<Actor> posts)
		{
			var now = self.World.WorldTick;
			return posts
				.Where(p => !unreachableUntil.TryGetValue(p, out var until) || until <= now)
				.MinByOrDefault(p => (p.CenterPosition - self.CenterPosition).LengthSquared);
		}

		Actor Home(Actor self)
		{
			if (home == null || home.IsDead || !home.IsInWorld || home.Owner != self.Owner)
				home = NearestPost(self, Posts(self.World).Where(p => p.Owner == self.Owner));

			return home;
		}

		bool IsTradePartner(Actor self, Actor post)
		{
			if (post.Owner == self.Owner)
				return false;

			return post.Owner.NonCombatant || !post.Owner.Playable || post.Owner.RelationshipWith(self.Owner) == PlayerRelationship.Ally;
		}

		bool Docked(Actor self, Actor post) =>
			(post.CenterPosition - self.CenterPosition).HorizontalLengthSquared <= (long)info.DockDistance.Length * info.DockDistance.Length;

		void INotifyIdle.TickIdle(Actor self)
		{
			if (waitTicks > 0 && --waitTicks > 0)
				return;

			if (!Carrying)
			{
				if (destination == null || destination.IsDead || !destination.IsInWorld || !IsTradePartner(self, destination))
					destination = NearestPost(self, Posts(self.World).Where(p => IsTradePartner(self, p)));

				if (destination == null)
				{
					waitTicks = 50;
					return;
				}

				if (Docked(self, destination))
				{
					Carrying = true;
					destination = null;
					waitTicks = info.LoadTicks;
					return;
				}

				SailTo(self, destination);
			}
			else
			{
				var h = Home(self);
				if (h == null)
				{
					waitTicks = 50;
					return;
				}

				if (Docked(self, h))
				{
					Carrying = false;
					waitTicks = info.UnloadTicks;
					Payout(self);
					return;
				}

				SailTo(self, h);
			}
		}

		void SailTo(Actor self, Actor post)
		{
			// If the previous attempt left us where we started, the post is unreachable by water.
			if (lastAttemptFrom == self.CenterPosition)
			{
				unreachableUntil[post] = self.World.WorldTick + info.UnreachableCooldown;
				if (post == destination)
					destination = null;
				else
					home = null;

				lastAttemptFrom = WPos.Zero;
				waitTicks = 25;
				return;
			}

			lastAttemptFrom = self.CenterPosition;
			self.QueueActivity(move.MoveTo(post.Location, 3, null, true));
		}

		void Payout(Actor self)
		{
			self.Owner.PlayerActor.Trait<PlayerResources>().GiveCash(info.Payment);
			if (info.ShowTicks && self.Owner.IsAlliedWith(self.World.RenderPlayer))
				self.World.AddFrameEndTask(w => w.Add(new FloatingText(self.CenterPosition, self.Owner.Color,
					FloatingText.FormatCashTick(info.Payment), 30)));
		}
	}
}
