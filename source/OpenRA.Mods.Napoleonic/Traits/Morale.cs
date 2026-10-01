#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Units lose morale as they take casualties. At zero morale the unit is overwhelmed and routs:",
		"its owner loses control and it runs away from the enemy until it rallies.")]
	public class MoraleInfo : TraitInfo, Requires<HealthInfo>, Requires<IMoveInfo>
	{
		[Desc("Morale of a fresh unit.")]
		public readonly int MaxMorale = 1000;

		[Desc("Morale lost for every 1% of the unit's full numerical value lost.")]
		public readonly int LossPerPercent = 40;

		[Desc("Damage types that shake morale harder (bayonet and sabre charges, canister).")]
		public readonly BitSet<DamageType> ShockDamageTypes = default;

		[Desc("Percentage applied to morale loss from ShockDamageTypes.")]
		public readonly int ShockMultiplier = 250;

		[Desc("Morale regained per tick once the unit has not been hit for RecoveryDelay ticks.")]
		public readonly int Recovery = 2;

		public readonly int RecoveryDelay = 100;

		[Desc("Maximum morale scales down with losses: at 0 strength it is this percentage of MaxMorale.")]
		public readonly int MinStrengthMoralePercent = 30;

		[Desc("A routed unit rallies once its morale is back to this level and it has run for MinRoutTicks.")]
		public readonly int RallyMorale = 450;

		public readonly int MinRoutTicks = 250;

		[Desc("While routed and not under fire, stragglers return: this many thousandths of full strength per second.")]
		public readonly int RegroupPermillePerSecond = 5;

		[Desc("A routed unit cannot rally until it is back to this percentage of its full strength.")]
		public readonly int RallyStrengthPercent = 50;

		[Desc("How far a routed unit runs from the enemy.")]
		public readonly WDist FleeDistance = WDist.FromCells(12);

		[GrantedConditionReference]
		[Desc("Condition granted while routed. Use it to reject orders, disable weapons and speed the unit up.")]
		public readonly string RoutedCondition = "routed";

		[GrantedConditionReference]
		[Desc("Condition granted while a routed unit has turned at bay to fight (still out of its owner's control).")]
		public readonly string AtBayCondition = "at-bay";

		[Desc("A fleeing unit with enemies still close turns to fight after this many ticks.")]
		public readonly int TurnAtBayTicks = 200;

		[Desc("A fleeing unit that has not been able to move for this many ticks is cornered and turns to fight.")]
		public readonly int CorneredTicks = 25;

		[Desc("Enemies within this distance keep a unit at bay (or make it turn).")]
		public readonly WDist AtBayEnemyRange = WDist.FromCells(6);

		[Desc("A unit at bay resumes regrouping once no enemy has been in range for this many ticks.")]
		public readonly int LeaveAtBayTicks = 100;

		[Desc("A unit reduced to this percentage of its full strength (or less) is broken: it routs whatever its morale,",
			"and it will not turn at bay while it is this weak.")]
		public readonly int BrokenStrengthPercent = 10;

		public override object Create(ActorInitializer init) { return new Morale(init.Self, this); }
	}

	public class Morale : ITick, INotifyDamage, INotifyCreated, ISync
	{
		readonly MoraleInfo info;
		Health health;
		IMove move;
		Formation formation;
		DivisionName division;
		RegimentCommands commands;
		MoraleLossMultiplier[] lossMultipliers;

		int routedToken = Actor.InvalidConditionToken;
		int atBayToken = Actor.InvalidConditionToken;
		int fleeTicks;
		int stuckTicks;
		int noEnemyTicks;
		WPos lastPos;
		int ticksSinceHit;
		int routTicks;
		WPos? threat;

		[VerifySync]
		public int Value { get; private set; }

		public bool IsRouted => routedToken != Actor.InvalidConditionToken;

		/// <summary>Routed, but turned to fight because it was cornered or pursued.</summary>
		public bool IsAtBay => atBayToken != Actor.InvalidConditionToken;

		/// <summary>Morale as a percentage of a fresh unit's.</summary>
		public int Percent => Value * 100 / Math.Max(1, info.MaxMorale);

		/// <summary>Too few men left to fight on: the unit routs and will not turn at bay.</summary>
		public bool IsBroken => health.HP * 100 <= (long)health.MaxHP * info.BrokenStrengthPercent;

		public Morale(Actor self, MoraleInfo info)
		{
			this.info = info;
			Value = info.MaxMorale;
		}

		void INotifyCreated.Created(Actor self)
		{
			health = self.Trait<Health>();
			move = self.Trait<IMove>();
			formation = self.TraitOrDefault<Formation>();
			division = self.TraitOrDefault<DivisionName>();
			commands = self.TraitOrDefault<RegimentCommands>();
			lossMultipliers = self.TraitsImplementing<MoraleLossMultiplier>().ToArray();
		}

		int MoraleCap => info.MaxMorale * (info.MinStrengthMoralePercent
			+ (100 - info.MinStrengthMoralePercent) * health.HP / Math.Max(1, health.MaxHP)) / 100;

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			if (e.Damage.Value <= 0 || self.IsDead)
				return;

			ticksSinceHit = 0;
			if (e.Attacker != null && !e.Attacker.IsDead && e.Attacker.IsInWorld)
				threat = e.Attacker.CenterPosition;

			// Loss is proportional to the share of the unit's full strength that was lost.
			var loss = (int)((long)e.Damage.Value * 100 * info.LossPerPercent / Math.Max(1, health.MaxHP));
			if (e.Damage.DamageTypes.Overlaps(info.ShockDamageTypes))
				loss = loss * info.ShockMultiplier / 100;

			foreach (var m in lossMultipliers)
				loss = loss * m.GetModifier() / 100;

			Value = Math.Min(Value - Math.Max(1, loss), MoraleCap);

			if (Value <= 0 || IsBroken)
			{
				Value = Math.Max(0, Value);
				if (!IsRouted)
					Rout(self);
				else if (self.IsIdle && !IsAtBay)
					Flee(self);
			}
		}

		void ITick.Tick(Actor self)
		{
			ticksSinceHit++;
			if (ticksSinceHit > info.RecoveryDelay)
				Value = Math.Min(Value + info.Recovery, MoraleCap);

			if (!IsRouted)
				return;

			routTicks++;
			UpdateAtBay(self);

			// Stragglers drift back once the enemy is no longer firing on the unit.
			if (ticksSinceHit > info.RecoveryDelay && routTicks % 25 == 0 && health.HP < health.MaxHP)
			{
				var regroup = Math.Max(1, health.MaxHP * info.RegroupPermillePerSecond / 1000);
				health.InflictDamage(self, self, new Damage(-regroup), true);
			}

			var strengthPercent = health.HP * 100 / Math.Max(1, health.MaxHP);
			if (routTicks >= info.MinRoutTicks && Value >= info.RallyMorale && strengthPercent >= info.RallyStrengthPercent)
				Rally(self);
		}

		bool EnemyNear(Actor self)
		{
			return self.World.FindActorsInCircle(self.CenterPosition, info.AtBayEnemyRange).Any(a =>
				!a.IsDead && a.IsInWorld && a.Owner.RelationshipWith(self.Owner) == PlayerRelationship.Enemy
				&& a.Info.HasTraitInfo<AttackBaseInfo>());
		}

		void UpdateAtBay(Actor self)
		{
			// A broken unit only runs: it stops fighting if it was at bay, and never turns.
			if (IsBroken)
			{
				if (IsAtBay)
				{
					atBayToken = self.RevokeCondition(atBayToken);
					formation?.AddDisorder();
					self.CancelActivity();
					fleeTicks = 0;
					stuckTicks = 0;
					Flee(self);
				}

				return;
			}

			if (IsAtBay)
			{
				// Keep fighting while the enemy is close, then go back to regrouping.
				noEnemyTicks = EnemyNear(self) ? 0 : noEnemyTicks + 1;
				if (noEnemyTicks >= info.LeaveAtBayTicks)
				{
					atBayToken = self.RevokeCondition(atBayToken);
					formation?.AddDisorder();
				}

				return;
			}

			fleeTicks++;
			var pos = self.CenterPosition;
			stuckTicks = pos == lastPos ? stuckTicks + 1 : 0;
			lastPos = pos;

			// Pursued for a while, or cornered with nowhere left to run: turn and fight.
			var cornered = stuckTicks >= info.CorneredTicks;
			if ((fleeTicks >= info.TurnAtBayTicks || cornered) && EnemyNear(self))
				TurnAtBay(self);
		}

		void TurnAtBay(Actor self)
		{
			self.CancelActivity();
			atBayToken = self.GrantCondition(info.AtBayCondition);
			noEnemyTicks = 0;
			formation?.RemoveDisorder();
			Notify(self, "turns to fight!", Color.FromArgb(255, 170, 60));
		}

		void Rout(Actor self)
		{
			routedToken = self.GrantCondition(info.RoutedCondition);
			routTicks = 0;
			fleeTicks = 0;
			stuckTicks = 0;
			lastPos = self.CenterPosition;
			commands?.Reset(self);
			formation?.AddDisorder();
			Flee(self);

			Notify(self, "is routed!", Color.FromArgb(255, 80, 60));
		}

		void Rally(Actor self)
		{
			routedToken = self.RevokeCondition(routedToken);
			if (IsAtBay)
				atBayToken = self.RevokeCondition(atBayToken);
			else
				formation?.RemoveDisorder();

			self.CancelActivity();

			Notify(self, "has rallied.", Color.FromArgb(120, 220, 120));
		}

		void Flee(Actor self)
		{
			var world = self.World;
			var pos = self.CenterPosition;

			// Run directly away from whoever hit us last, or back the way we are facing.
			var away = threat.HasValue ? pos - threat.Value : new WVec(0, 1024, 0).Rotate(WRot.FromYaw(self.Orientation.Yaw));
			away = new WVec(away.X, away.Y, 0);
			var len = away.HorizontalLength;
			if (len == 0)
				away = new WVec(0, 1024, 0);
			else
				away = away * 1024 / len;

			var dest = world.Map.Clamp(world.Map.CellContaining(pos + away * info.FleeDistance.Length / 1024));
			self.QueueActivity(false, move.MoveTo(dest, 4));
		}

		/// <summary>Reports something this unit did ("is routed!") to players who can see it.</summary>
		public void Announce(Actor self, string what, Color color) { Notify(self, what, color); }

		void Notify(Actor self, string what, Color color)
		{
			var localPlayer = self.World.LocalPlayer;
			var visible = localPlayer == null || self.Owner == localPlayer || !self.World.FogObscures(self);
			if (!visible)
				return;

			var name = division?.FullName ?? self.Info.Name;
			var prefix = self.Owner == localPlayer ? "Your army" : self.Owner.ResolvedPlayerName;
			TextNotificationsManager.AddMissionLine(prefix, $"{name} {what}", color);
		}
	}
}
