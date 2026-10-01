#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Frozen;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("Lets the AI use the Charge and Run commands. It fights by fire and charges sparingly:",
		"only steady units charge, only at batteries, routed or badly shaken units (cavalry also at clearly weaker cavalry),",
		"and never into an enemy line that has more steady regiments than the charger has around it.",
		"Run: a unit being shot at from beyond its own range runs in to close the distance.")]
	public class RegimentTacticsBotModuleInfo : ConditionalTraitInfo
	{
		[Desc("Cavalry unit types.")]
		public readonly FrozenSet<string> CavalryTypes = FrozenSet<string>.Empty;

		[Desc("Grenadier unit types.")]
		public readonly FrozenSet<string> GrenadierTypes = FrozenSet<string>.Empty;

		[Desc("Artillery unit types (favoured charge targets).")]
		public readonly FrozenSet<string> ArtilleryTypes = FrozenSet<string>.Empty;

		public readonly WDist CavalryChargeRange = WDist.FromCells(9);
		public readonly WDist GrenadierChargeRange = WDist.FromCells(5);
		public readonly WDist InfantryChargeRange = WDist.FromCells(4);

		[Desc("Enemies below this morale percentage count as shaken and are charged.")]
		public readonly int ShakenMoralePercent = 30;

		[Desc("A unit only charges while its own morale is at least this percentage; otherwise it stands off and fires.")]
		public readonly int MinOwnMoralePercent = 65;

		[Desc("Cavalry only charges other cavalry when it is at least this many strength percentage points better off.")]
		public readonly int CavalryStrengthMargin = 15;

		[Desc("Steady (unrouted, unshaken) regiments are counted within this distance of the target and of the charger.",
			"A charge on anything but a routed unit only goes in when the enemy is not the stronger side there.")]
		public readonly WDist SupportRange = WDist.FromCells(6);

		[Desc("Infantry stop chasing once this far from where the charge started.")]
		public readonly WDist InfantryPursuitLimit = WDist.FromCells(8);

		[Desc("Units shot at from further away than this will not run in (too far).")]
		public readonly WDist MaxRunDistance = WDist.FromCells(16);

		[Desc("Ticks between tactical checks.")]
		public readonly int Interval = 20;

		[Desc("Minimum ticks between two commands to the same unit.")]
		public readonly int CommandCooldown = 300;

		public override object Create(ActorInitializer init) { return new RegimentTacticsBotModule(init.Self, this); }
	}

	public class RegimentTacticsBotModule : ConditionalTrait<RegimentTacticsBotModuleInfo>, IBotTick, IBotRespondToAttack
	{
		readonly World world;
		readonly Dictionary<Actor, int> cooldownUntil = [];
		readonly Dictionary<Actor, WPos> chargeStart = [];
		int ticks;

		public RegimentTacticsBotModule(Actor self, RegimentTacticsBotModuleInfo info)
			: base(info)
		{
			world = self.World;
		}

		enum Kind { Infantry, Grenadier, Cavalry }

		Kind KindOf(Actor a) =>
			Info.CavalryTypes.Contains(a.Info.Name) ? Kind.Cavalry
			: Info.GrenadierTypes.Contains(a.Info.Name) ? Kind.Grenadier
			: Kind.Infantry;

		bool Ready(Actor a) => !cooldownUntil.TryGetValue(a, out var until) || until <= world.WorldTick;

		void Issue(IBot bot, Order order)
		{
			cooldownUntil[order.Subject] = world.WorldTick + Info.CommandCooldown;
			bot.QueueOrder(order);
		}

		static bool Usable(Actor a, Player owner, out RegimentCommands commands, out Morale morale)
		{
			commands = null;
			morale = null;
			if (a.IsDead || !a.IsInWorld || a.Owner != owner)
				return false;

			commands = a.TraitOrDefault<RegimentCommands>();
			morale = a.TraitOrDefault<Morale>();
			return commands != null && (morale == null || !morale.IsRouted);
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (--ticks > 0)
				return;

			ticks = Info.Interval;

			// Forget units that no longer exist.
			foreach (var dead in cooldownUntil.Keys.Where(a => a.IsDead || !a.IsInWorld).ToList())
			{
				cooldownUntil.Remove(dead);
				chargeStart.Remove(dead);
			}

			var regiments = world.ActorsHavingTrait<RegimentCommands>().Where(a => a.Owner == bot.Player).ToList();
			foreach (var a in regiments)
			{
				if (!Usable(a, bot.Player, out var commands, out _))
					continue;

				var kind = KindOf(a);

				// Recall infantry that have chased too far.
				if (commands.IsCharging)
				{
					if (kind != Kind.Cavalry && chargeStart.TryGetValue(a, out var start)
						&& (a.CenterPosition - start).HorizontalLengthSquared > (long)Info.InfantryPursuitLimit.Length * Info.InfantryPursuitLimit.Length)
					{
						chargeStart.Remove(a);
						Issue(bot, new Order("Stop", a, false));
					}

					continue;
				}

				chargeStart.Remove(a);
				if (!Ready(a) || commands.IsRunning)
					continue;

				var target = ChooseChargeTarget(a, kind, bot.Player);
				if (target != null)
				{
					chargeStart[a] = a.CenterPosition;
					Issue(bot, new Order(RegimentCommands.ChargeOrder, a, Target.FromActor(target), false));
				}
			}
		}

		Actor ChooseChargeTarget(Actor self, Kind kind, Player owner)
		{
			var range = kind == Kind.Cavalry ? Info.CavalryChargeRange
				: kind == Kind.Grenadier ? Info.GrenadierChargeRange
				: Info.InfantryChargeRange;

			// Shaken troops stand off and fire rather than go in.
			var ownMorale = self.TraitOrDefault<Morale>();
			if (ownMorale != null && ownMorale.Percent < Info.MinOwnMoralePercent)
				return null;

			var selfStrength = StrengthPercent(self);
			var friendsNear = SteadyRegiments(self.CenterPosition, owner, PlayerRelationship.Ally);
			Actor best = null;
			var bestScore = 0;

			foreach (var e in world.FindActorsInCircle(self.CenterPosition, range))
			{
				if (e.IsDead || !e.IsInWorld || owner.RelationshipWith(e.Owner) != PlayerRelationship.Enemy
					|| !e.CanBeViewedByPlayer(owner) || e.TraitOrDefault<Formation>() == null)
					continue;

				var enemyMorale = e.TraitOrDefault<Morale>();
				var routed = enemyMorale != null && enemyMorale.IsRouted;
				var shaken = enemyMorale != null && enemyMorale.Percent < Info.ShakenMoralePercent;
				var isGuns = Info.ArtilleryTypes.Contains(e.Info.Name);
				var isCavalry = Info.CavalryTypes.Contains(e.Info.Name);

				var score = 0;
				switch (kind)
				{
					// Steady infantry is never charged: it is worn down by fire first.
					case Kind.Cavalry:
						if (isGuns)
							score = 100;
						else if (routed)
							score = 90;
						else if (shaken)
							score = 70;
						else if (isCavalry && selfStrength >= StrengthPercent(e) + Info.CavalryStrengthMargin)
							score = 50;
						break;

					case Kind.Grenadier:
						if (isGuns)
							score = 90;
						else if (routed || shaken)
							score = 80;
						break;

					default:
						if (isGuns)
							score = 80;
						else if (shaken && !routed)
							score = 70;
						else if (routed)
							score = 20;
						break;
				}

				// Do not charge into a stronger enemy line: only broken units are fair game there.
				if (score > 0 && !routed && SteadyRegiments(e.CenterPosition, owner, PlayerRelationship.Enemy, e) > friendsNear)
					score = 0;

				// Prefer the closest of equally attractive targets.
				if (score > 0)
				{
					var d = (e.CenterPosition - self.CenterPosition).HorizontalLength;
					score = score * 1000 - d * 100 / 1024;
				}

				if (score > bestScore)
				{
					bestScore = score;
					best = e;
				}
			}

			return best;
		}

		/// <summary>Counts unrouted, unshaken regiments of one side near a position (optionally leaving one out).</summary>
		int SteadyRegiments(WPos pos, Player owner, PlayerRelationship relationship, Actor except = null)
		{
			var count = 0;
			foreach (var a in world.FindActorsInCircle(pos, Info.SupportRange))
			{
				if (a == except || a.IsDead || !a.IsInWorld || a.TraitOrDefault<RegimentCommands>() == null)
					continue;

				var isFriend = a.Owner == owner || owner.RelationshipWith(a.Owner) == PlayerRelationship.Ally;
				if (isFriend != (relationship == PlayerRelationship.Ally))
					continue;

				if (!isFriend && owner.RelationshipWith(a.Owner) != PlayerRelationship.Enemy)
					continue;

				var m = a.TraitOrDefault<Morale>();
				if (m == null || (!m.IsRouted && m.Percent >= Info.ShakenMoralePercent))
					count++;
			}

			return count;
		}

		static int StrengthPercent(Actor a)
		{
			var h = a.TraitOrDefault<IHealth>();
			return h == null ? 100 : h.HP * 100 / System.Math.Max(1, h.MaxHP);
		}

		void IBotRespondToAttack.RespondToAttack(IBot bot, Actor self, AttackInfo e)
		{
			if (IsTraitDisabled || e.Attacker == null || e.Attacker.IsDead || !e.Attacker.IsInWorld
				|| bot.Player.RelationshipWith(e.Attacker.Owner) != PlayerRelationship.Enemy)
				return;

			if (!Usable(self, bot.Player, out var commands, out _) || commands.IsCharging || commands.IsRunning || commands.IsStanding || !Ready(self))
				return;

			var toAttacker = e.Attacker.CenterPosition - self.CenterPosition;
			var distance = toAttacker.HorizontalLength;
			if (distance > Info.MaxRunDistance.Length)
				return;

			var ownRange = self.TraitsImplementing<Armament>()
				.Where(a => !a.IsTraitDisabled)
				.Select(a => a.MaxRange().Length)
				.DefaultIfEmpty(0)
				.Max();

			// Only react to fire we cannot answer.
			if (distance <= ownRange + 512)
				return;

			var kind = KindOf(self);
			var attackerIsGuns = Info.ArtilleryTypes.Contains(e.Attacker.Info.Name);

			// Steady cavalry (and steady troops already close) go straight at guns that are shelling them,
			// unless the battery is covered by more steady troops than we have to hand.
			var ownMorale = self.TraitOrDefault<Morale>();
			var steady = ownMorale == null || ownMorale.Percent >= Info.MinOwnMoralePercent;
			if (attackerIsGuns && steady && (kind == Kind.Cavalry || distance <= Info.GrenadierChargeRange.Length + 1024)
				&& SteadyRegiments(e.Attacker.CenterPosition, bot.Player, PlayerRelationship.Enemy, e.Attacker)
					<= SteadyRegiments(self.CenterPosition, bot.Player, PlayerRelationship.Ally))
			{
				chargeStart[self] = self.CenterPosition;
				Issue(bot, new Order(RegimentCommands.ChargeOrder, self, Target.FromActor(e.Attacker), false));
				return;
			}

			// Otherwise run in to just inside our own range and let the unit open fire.
			var stopShort = System.Math.Max(0, ownRange - 1024);
			var dest = e.Attacker.CenterPosition - toAttacker * stopShort / System.Math.Max(1, distance);
			var cell = world.Map.Clamp(world.Map.CellContaining(dest));
			Issue(bot, new Order(RegimentCommands.RunOrder, self, Target.FromCell(world, cell), false));
		}
	}
}
