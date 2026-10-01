#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Frozen;
using System.Linq;
using OpenRA.Activities;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Adds the Charge, Run and Stand commands used by infantry and cavalry.",
		"Charge: attack the target with bayonet or sabre at the charge. Run: move at the double, out of formation.",
		"Stand: halt, form up and hold the position, firing at anything in range.")]
	public class RegimentCommandsInfo : TraitInfo, Requires<IMoveInfo>, Requires<AttackBaseInfo>
	{
		[GrantedConditionReference]
		[Desc("Granted while charging. Use it to enable the melee armament, disable muskets and increase speed.")]
		public readonly string ChargeCondition = "charging";

		[GrantedConditionReference]
		[Desc("Granted while running.")]
		public readonly string RunCondition = "running";

		[GrantedConditionReference]
		[Desc("Granted while standing.")]
		public readonly string StandCondition = "standing";

		[Desc("Orders that cancel a charge, run or stand.")]
		public readonly FrozenSet<string> CancelOrders = FrozenSet.ToFrozenSet(["Move", "AttackMove", "AssaultMove", "Attack", "ForceAttack",
			"Stop", "Scatter", "Guard", "NWCharge", "NWRun", "NWStand"]);

		[VoiceReference]
		public readonly string Voice = "Action";

		[Desc("A charged unit reacts once the charging enemy is this close.")]
		public readonly WDist ChargeReactionDistance = WDist.FromCells(4);

		[Desc("A charged unit with at least this morale percentage counter-charges; below it, the unit runs away.")]
		public readonly int CounterChargeMorale = 50;

		[Desc("A unit ordered to Stand holds its ground against a charge unless its morale falls below this percentage.")]
		public readonly int StandFirmMorale = 30;

		[Desc("How far a unit runs from a charge it will not meet.")]
		public readonly WDist EvadeDistance = WDist.FromCells(8);

		[Desc("A unit running from a charge turns and fights after this many ticks if the charger is still close.")]
		public readonly int EvadeTurnTicks = 100;

		[Desc("A unit running from a charge that cannot move for this many ticks is cornered and turns to fight.")]
		public readonly int EvadeCorneredTicks = 20;

		public override object Create(ActorInitializer init) { return new RegimentCommands(this); }
	}

	public class RegimentCommands : INotifyCreated, IResolveOrder, IOrderVoice, ITick
	{
		public const string ChargeOrder = "NWCharge";
		public const string RunOrder = "NWRun";
		public const string StandOrder = "NWStand";

		readonly RegimentCommandsInfo info;
		IMove move;
		AttackBase[] attacks;
		AutoTarget autoTarget;
		Formation formation;
		Morale morale;

		// The unit we are charging, and whether it has been warned yet.
		Actor chargeTarget;
		bool chargeAnnounced;

		// Set while running from a charge.
		Actor evadingFrom;
		int evadeTicks;
		int evadeStuckTicks;
		WPos evadeLastPos;

		int chargeToken = Actor.InvalidConditionToken;
		int runToken = Actor.InvalidConditionToken;
		int standToken = Actor.InvalidConditionToken;
		UnitStance stanceBeforeStand;

		public RegimentCommands(RegimentCommandsInfo info) { this.info = info; }

		public bool IsCharging => chargeToken != Actor.InvalidConditionToken;
		public bool IsRunning => runToken != Actor.InvalidConditionToken;
		public bool IsStanding => standToken != Actor.InvalidConditionToken;

		void INotifyCreated.Created(Actor self)
		{
			move = self.Trait<IMove>();
			attacks = self.TraitsImplementing<AttackBase>().ToArray();
			autoTarget = self.TraitOrDefault<AutoTarget>();
			formation = self.TraitOrDefault<Formation>();
			morale = self.TraitOrDefault<Morale>();
		}

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (!info.CancelOrders.Contains(order.OrderString))
				return;

			if (!order.Queued)
			{
				Reset(self);
				evadingFrom = null;
			}

			switch (order.OrderString)
			{
				case ChargeOrder:
					Charge(self, order);
					break;
				case RunOrder:
					Run(self, order);
					break;
				case StandOrder:
					Stand(self);
					break;
			}
		}

		/// <summary>Drops any charge, run or stand, e.g. when the unit routs.</summary>
		public void Reset(Actor self)
		{
			EndCharge(self);
			EndRun(self);
			EndStand(self);
		}

		void Charge(Actor self, Order order)
		{
			if (order.Target.Type != TargetType.Actor && order.Target.Type != TargetType.FrozenActor)
				return;

			// A unit whose attack is switched off (e.g. routed) cannot charge.
			var attack = attacks.FirstEnabledTraitOrDefault();
			if (attack == null)
				return;

			if (!order.Queued)
				self.CancelActivity();

			var target = order.Target;
			chargeTarget = target.Type == TargetType.Actor ? target.Actor : null;
			chargeAnnounced = false;
			self.QueueActivity(new CallFunc(() =>
			{
				if (chargeToken == Actor.InvalidConditionToken)
				{
					chargeToken = self.GrantCondition(info.ChargeCondition);
					formation?.AddDisorder();
				}
			}));

			// The melee armament is only enabled by the charge condition, so the attack uses it.
			self.QueueActivity(attack.GetAttackActivity(self, AttackSource.Default, target, true, false, Color.OrangeRed));

			self.QueueActivity(new CallFunc(() => EndCharge(self)));
			self.ShowTargetLines();
		}

		void Run(Actor self, Order order)
		{
			if (order.Target.Type == TargetType.Invalid)
				return;

			if (!order.Queued)
				self.CancelActivity();

			var cell = self.World.Map.CellContaining(order.Target.CenterPosition);
			self.QueueActivity(new CallFunc(() =>
			{
				if (runToken == Actor.InvalidConditionToken)
				{
					runToken = self.GrantCondition(info.RunCondition);
					formation?.AddDisorder();
				}
			}));

			self.QueueActivity(move.MoveTo(cell, 2, targetLineColor: Color.Yellow));
			self.QueueActivity(new CallFunc(() => EndRun(self)));
			self.ShowTargetLines();
		}

		void Stand(Actor self)
		{
			self.CancelActivity();
			standToken = self.GrantCondition(info.StandCondition);
			if (autoTarget != null)
			{
				stanceBeforeStand = autoTarget.Stance;
				autoTarget.SetStance(self, UnitStance.Defend);
			}
		}

		void EndCharge(Actor self)
		{
			if (chargeToken == Actor.InvalidConditionToken)
				return;

			chargeToken = self.RevokeCondition(chargeToken);
			formation?.RemoveDisorder();
			chargeTarget = null;
		}

		void EndRun(Actor self)
		{
			if (runToken == Actor.InvalidConditionToken)
				return;

			runToken = self.RevokeCondition(runToken);
			formation?.RemoveDisorder();
		}

		void EndStand(Actor self)
		{
			if (standToken == Actor.InvalidConditionToken)
				return;

			standToken = self.RevokeCondition(standToken);
			if (autoTarget != null && autoTarget.Stance == UnitStance.Defend)
				autoTarget.SetStance(self, stanceBeforeStand);
		}

		void ITick.Tick(Actor self)
		{
			TickEvade(self);

			// Warn the enemy we are charging once we are close: it must meet the charge or run.
			if (!IsCharging || chargeAnnounced || chargeTarget == null)
				return;

			if (chargeTarget.IsDead || !chargeTarget.IsInWorld)
			{
				chargeTarget = null;
				return;
			}

			var range = info.ChargeReactionDistance.Length;
			if ((chargeTarget.CenterPosition - self.CenterPosition).HorizontalLengthSquared > (long)range * range)
				return;

			chargeAnnounced = true;
			chargeTarget.TraitOrDefault<RegimentCommands>()?.OnCharged(chargeTarget, self);
		}

		void TickEvade(Actor self)
		{
			if (evadingFrom == null)
				return;

			evadeTicks++;
			var pos = self.CenterPosition;
			evadeStuckTicks = pos == evadeLastPos ? evadeStuckTicks + 1 : 0;
			evadeLastPos = pos;

			var charger = evadingFrom;
			var cornered = evadeStuckTicks >= info.EvadeCorneredTicks;
			if (!cornered && evadeTicks < info.EvadeTurnTicks && IsRunning)
				return;

			evadingFrom = null;
			if (charger.IsDead || !charger.IsInWorld || (morale != null && morale.IsRouted))
				return;

			// Still hunted (or trapped): turn and meet the charge.
			var range = info.ChargeReactionDistance.Length * 3 / 2;
			if (cornered || (charger.CenterPosition - self.CenterPosition).HorizontalLengthSquared <= (long)range * range)
			{
				Reset(self);
				Charge(self, new Order(ChargeOrder, self, Target.FromActor(charger), false));
			}
		}

		/// <summary>An enemy charge is about to strike this unit: counter-charge, stand firm, or run.</summary>
		void OnCharged(Actor self, Actor charger)
		{
			if (self.IsDead || charger.IsDead || IsCharging || evadingFrom != null)
				return;

			// Routed units only meet a charge once they have turned at bay.
			if (morale != null && morale.IsRouted)
			{
				if (morale.IsAtBay)
					Charge(self, new Order(ChargeOrder, self, Target.FromActor(charger), false));

				return;
			}

			var moralePercent = morale?.Percent ?? 100;
			if (IsStanding && moralePercent >= info.StandFirmMorale)
				return;

			if (moralePercent >= info.CounterChargeMorale)
			{
				Reset(self);
				Charge(self, new Order(ChargeOrder, self, Target.FromActor(charger), false));
				return;
			}

			// Break and run directly away from the charge.
			var away = self.CenterPosition - charger.CenterPosition;
			away = new WVec(away.X, away.Y, 0);
			var len = away.HorizontalLength;
			away = len == 0 ? new WVec(0, 1024, 0) : away * 1024 / len;
			var map = self.World.Map;
			var cell = map.Clamp(map.CellContaining(self.CenterPosition + away * info.EvadeDistance.Length / 1024));

			Reset(self);
			Run(self, new Order(RunOrder, self, Target.FromCell(self.World, cell), false));
			evadingFrom = charger;
			evadeTicks = 0;
			evadeStuckTicks = 0;
			evadeLastPos = self.CenterPosition;
		}

		string IOrderVoice.VoicePhraseForOrder(Actor self, Order order)
		{
			return order.OrderString is ChargeOrder or RunOrder or StandOrder ? info.Voice : null;
		}
	}
}
