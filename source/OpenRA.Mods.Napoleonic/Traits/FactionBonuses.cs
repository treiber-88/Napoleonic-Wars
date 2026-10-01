#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Scales the morale a unit loses from casualties (Russian Stubbornness).")]
	public class MoraleLossMultiplierInfo : ConditionalTraitInfo
	{
		[FieldLoader.Require]
		[Desc("Percentage of normal morale loss.")]
		public readonly int Modifier = 100;

		public override object Create(ActorInitializer init) { return new MoraleLossMultiplier(this); }
	}

	public class MoraleLossMultiplier : ConditionalTrait<MoraleLossMultiplierInfo>
	{
		public MoraleLossMultiplier(MoraleLossMultiplierInfo info)
			: base(info) { }

		public int GetModifier() => IsTraitDisabled ? 100 : Info.Modifier;
	}

	[Desc("Scales how fast a Formation's figures form up and reform (Austrian Coffee Houses).")]
	public class FormationSpeedMultiplierInfo : ConditionalTraitInfo
	{
		[FieldLoader.Require]
		[Desc("Percentage of normal forming speed.")]
		public readonly int Modifier = 100;

		public override object Create(ActorInitializer init) { return new FormationSpeedMultiplier(this); }
	}

	public class FormationSpeedMultiplier : ConditionalTrait<FormationSpeedMultiplierInfo>
	{
		public FormationSpeedMultiplier(FormationSpeedMultiplierInfo info)
			: base(info) { }

		public int GetModifier() => IsTraitDisabled ? 100 : Info.Modifier;
	}

	[Desc("Grants a condition while the enemy's infantry and cavalry nearby add up to at least Threshold men",
		"(British Bulldog Resolve).")]
	public class GrantConditionOnEnemyStrengthInfo : ConditionalTraitInfo
	{
		[FieldLoader.Require]
		[GrantedConditionReference]
		public readonly string Condition = null;

		[Desc("Total numerical value of enemy regiments required.")]
		public readonly int Threshold = 5000;

		[Desc("Enemy regiments within this range are counted.")]
		public readonly WDist Range = WDist.FromCells(12);

		[Desc("Ticks between checks.")]
		public readonly int Interval = 25;

		public override object Create(ActorInitializer init) { return new GrantConditionOnEnemyStrength(this); }
	}

	public class GrantConditionOnEnemyStrength : ConditionalTrait<GrantConditionOnEnemyStrengthInfo>, ITick
	{
		int token = Actor.InvalidConditionToken;
		int ticks;

		public GrantConditionOnEnemyStrength(GrantConditionOnEnemyStrengthInfo info)
			: base(info) { }

		void ITick.Tick(Actor self)
		{
			if (IsTraitDisabled || --ticks > 0)
				return;

			ticks = Info.Interval;

			// Only units with a numerical value (infantry and cavalry) count towards the enemy's force.
			var strength = self.World.FindActorsInCircle(self.CenterPosition, Info.Range)
				.Where(a => !a.IsDead && a.IsInWorld && a.Owner.RelationshipWith(self.Owner) == PlayerRelationship.Enemy
					&& a.Info.HasTraitInfo<NumericalDisplayInfo>())
				.Sum(a => a.Trait<IHealth>().HP);

			var active = strength >= Info.Threshold;
			if (active && token == Actor.InvalidConditionToken)
				token = self.GrantCondition(Info.Condition);
			else if (!active && token != Actor.InvalidConditionToken)
				token = self.RevokeCondition(token);
		}

		protected override void TraitDisabled(Actor self)
		{
			if (token != Actor.InvalidConditionToken)
				token = self.RevokeCondition(token);
		}
	}

	[Desc("Demolishes each bridge span the unit has crossed while the trait is enabled",
		"(Russian Scorched Earth: routed Russians burn the bridges behind them).")]
	public class ScorchedEarthInfo : ConditionalTraitInfo
	{
		public readonly BitSet<DamageType> DamageTypes = default;

		public override object Create(ActorInitializer init) { return new ScorchedEarth(this); }
	}

	public class ScorchedEarth : ConditionalTrait<ScorchedEarthInfo>, ITick
	{
		LegacyBridgeLayer bridges;
		Bridge crossing;

		public ScorchedEarth(ScorchedEarthInfo info)
			: base(info) { }

		protected override void Created(Actor self)
		{
			bridges = self.World.WorldActor.TraitOrDefault<LegacyBridgeLayer>();
			base.Created(self);
		}

		void ITick.Tick(Actor self)
		{
			if (IsTraitDisabled || bridges == null)
				return;

			var under = bridges.GetBridge(self.Location);
			if (under == crossing)
				return;

			// We have stepped off the span we were crossing: destroy it behind us.
			crossing?.Demolish(self, -1, Info.DamageTypes);
			crossing = under;
		}

		protected override void TraitDisabled(Actor self)
		{
			crossing = null;
		}
	}
}
