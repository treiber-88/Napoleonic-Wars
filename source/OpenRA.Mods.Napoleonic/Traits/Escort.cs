#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Activities;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("A ship that warships can be paired with as escorts (trading and transport ships).",
		"While escorted it shortens sail so the convoy keeps together, and calls its escorts when it is attacked.")]
	public class EscortableInfo : TraitInfo, Requires<MobileInfo>
	{
		[Desc("Escorts keep within this distance.")]
		public readonly WDist Range = WDist.FromCells(4);

		[Desc("While escorted, the ship sails at no more than this percentage of its slowest escort's speed.")]
		public readonly int ConvoySpeedPercent = 90;

		public override object Create(ActorInitializer init) { return new Escortable(init.Self, this); }
	}

	public class Escortable : ISpeedModifier, INotifyDamage
	{
		readonly Actor self;
		readonly EscortableInfo info;
		readonly int ownSpeed;
		readonly List<Actor> escorts = [];

		public Escortable(Actor self, EscortableInfo info)
		{
			this.self = self;
			this.info = info;
			ownSpeed = Math.Max(1, self.Info.TraitInfo<MobileInfo>().Speed);
		}

		public EscortableInfo Info => info;

		static bool IsEscorting(Actor escort, Actor ship) =>
			!escort.IsDead && escort.IsInWorld && escort.TraitOrDefault<EscortShip>()?.Escorting == ship;

		/// <summary>The warships currently paired with this ship.</summary>
		public IEnumerable<Actor> Escorts => escorts.Where(e => IsEscorting(e, self));

		public void AddEscort(Actor escort)
		{
			escorts.RemoveAll(e => e == escort || !IsEscorting(e, self));
			escorts.Add(escort);
		}

		int ISpeedModifier.GetSpeedModifier()
		{
			var slowest = int.MaxValue;
			foreach (var e in escorts)
				if (IsEscorting(e, self))
					slowest = Math.Min(slowest, e.Info.TraitInfo<MobileInfo>().Speed);

			if (slowest == int.MaxValue)
				return 100;

			return Math.Min(100, slowest * info.ConvoySpeedPercent / ownSpeed);
		}

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			if (e.Damage.Value <= 0 || e.Attacker == null || e.Attacker == self)
				return;

			foreach (var escort in escorts.ToList())
				if (IsEscorting(escort, self))
					escort.Trait<EscortShip>().Defend(escort, e.Attacker);
		}
	}

	[Desc("A warship that can be paired with an Escortable ship: it sails with it, engages enemies that come near,",
		"and goes for whatever attacks its charge.")]
	public class EscortShipInfo : TraitInfo, Requires<IMoveInfo>, Requires<AttackBaseInfo>
	{
		[CursorReference]
		[Desc("Cursor shown over a ship that can be escorted.")]
		public readonly string Cursor = "guard";

		[VoiceReference]
		public readonly string Voice = "Action";

		public readonly Color TargetLineColor = Color.OrangeRed;

		[Desc("An escort chasing an attacker turns back once it is this far from its charge.")]
		public readonly WDist LeashRange = WDist.FromCells(12);

		public override object Create(ActorInitializer init) { return new EscortShip(this); }
	}

	public class EscortShip : IIssueOrder, IResolveOrder, IOrderVoice, INotifyCreated, ITick
	{
		public const string OrderID = "NWEscort";

		readonly EscortShipInfo info;
		IMove move;
		AttackBase[] attacks;
		Actor escorting;
		Actor defendingAgainst;
		int leashCheck;

		public EscortShip(EscortShipInfo info) { this.info = info; }

		/// <summary>The ship this warship is paired with, if any.</summary>
		public Actor Escorting => escorting != null && !escorting.IsDead && escorting.IsInWorld ? escorting : null;

		void INotifyCreated.Created(Actor self)
		{
			move = self.Trait<IMove>();
			attacks = self.TraitsImplementing<AttackBase>().ToArray();
		}

		IEnumerable<IOrderTargeter> IIssueOrder.Orders
		{
			get { yield return new EscortOrderTargeter(info.Cursor); }
		}

		Order IIssueOrder.IssueOrder(Actor self, IOrderTargeter order, in Target target, bool queued)
		{
			return order.OrderID == OrderID ? new Order(OrderID, self, target, queued) : null;
		}

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString != OrderID)
			{
				// Any other fresh order ends the pairing.
				if (!order.Queued)
				{
					escorting = null;
					defendingAgainst = null;
				}

				return;
			}

			if (order.Target.Type != TargetType.Actor)
				return;

			var ship = order.Target.Actor;
			var escortable = ship.TraitOrDefault<Escortable>();
			if (escortable == null || ship == self || !ship.Owner.IsAlliedWith(self.Owner))
				return;

			escorting = ship;
			defendingAgainst = null;
			escortable.AddEscort(self);
			self.QueueActivity(order.Queued, Follow(self, ship, escortable));
			self.ShowTargetLines();
		}

		// The same activity the Guard order uses: follow the ship, engaging enemies that come within reach.
		AttackMoveActivity Follow(Actor self, Actor ship, Escortable escortable)
		{
			var target = Target.FromActor(ship);
			var range = escortable.Info.Range;
			return new AttackMoveActivity(self, () => move.MoveFollow(self, target, WDist.Zero, range, targetLineColor: info.TargetLineColor));
		}

		/// <summary>Called when the escorted ship is attacked: go for the attacker, then return to the convoy.</summary>
		public void Defend(Actor self, Actor attacker)
		{
			var ship = Escorting;
			if (ship == null || attacker.IsDead || !attacker.IsInWorld || attacker.Owner.RelationshipWith(self.Owner) != PlayerRelationship.Enemy)
				return;

			if (defendingAgainst != null && !defendingAgainst.IsDead && defendingAgainst.IsInWorld)
				return;

			var attack = attacks.FirstEnabledTraitOrDefault();
			if (attack == null)
				return;

			defendingAgainst = attacker;
			self.QueueActivity(false, attack.GetAttackActivity(self, AttackSource.AutoTarget, Target.FromActor(attacker), true, false, Color.Red));
			self.QueueActivity(Follow(self, ship, ship.Trait<Escortable>()));
		}

		void ITick.Tick(Actor self)
		{
			if (defendingAgainst == null || --leashCheck > 0)
				return;

			leashCheck = 25;
			if (defendingAgainst.IsDead || !defendingAgainst.IsInWorld)
			{
				defendingAgainst = null;
				return;
			}

			// Do not be drawn away from the convoy.
			var ship = Escorting;
			if (ship == null)
			{
				defendingAgainst = null;
				return;
			}

			var leash = info.LeashRange.Length;
			if ((ship.CenterPosition - self.CenterPosition).HorizontalLengthSquared > (long)leash * leash)
			{
				defendingAgainst = null;
				self.QueueActivity(false, Follow(self, ship, ship.Trait<Escortable>()));
			}
		}

		string IOrderVoice.VoicePhraseForOrder(Actor self, Order order)
		{
			return order.OrderString == OrderID ? info.Voice : null;
		}

		sealed class EscortOrderTargeter : UnitOrderTargeter
		{
			public EscortOrderTargeter(string cursor)
				: base(EscortShip.OrderID, 6, cursor, false, true) { }

			public override bool CanTargetActor(Actor self, Actor target, TargetModifiers modifiers, ref string cursor)
			{
				return target != self && target.Info.HasTraitInfo<EscortableInfo>() && target.Owner.IsAlliedWith(self.Owner);
			}

			public override bool CanTargetFrozenActor(Actor self, FrozenActor target, TargetModifiers modifiers, ref string cursor)
			{
				return false;
			}
		}
	}
}
