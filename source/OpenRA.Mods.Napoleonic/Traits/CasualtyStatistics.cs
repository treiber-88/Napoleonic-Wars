#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;
using OpenRA.Widgets;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Counts a formation in the player statistics by men rather than by unit:",
		"every point of numerical value an enemy takes off it is one kill for him, one loss for its owner and one point of score.",
		"Replaces UpdatesPlayerStatistics and GivesExperience on formations (it also keeps the army value up to date).")]
	public class CasualtyStatisticsInfo : TraitInfo, Requires<HealthInfo>
	{
		[Desc("Add to army value in statistics.")]
		public readonly bool AddToArmyValue = true;

		public override object Create(ActorInitializer init) { return new CasualtyStatistics(this, init.Self); }
	}

	public class CasualtyStatistics : INotifyCreated, INotifyDamage, INotifyKilled, INotifyOwnerChanged, INotifyActorDisposing
	{
		readonly CasualtyStatisticsInfo info;
		readonly string actorName;
		readonly int cost;
		PlayerStatistics playerStats;
		Health health;
		int lastHP;
		long costCarry;
		bool includedInArmyValue;

		public CasualtyStatistics(CasualtyStatisticsInfo info, Actor self)
		{
			this.info = info;
			actorName = self.Info.Name;
			cost = self.Info.TraitInfoOrDefault<ValuedInfo>()?.Cost ?? 0;
			playerStats = self.Owner.PlayerActor.Trait<PlayerStatistics>();
		}

		void INotifyCreated.Created(Actor self)
		{
			health = self.Trait<Health>();
			lastHP = health.HP;
			includedInArmyValue = info.AddToArmyValue;
			if (includedInArmyValue)
			{
				playerStats.ArmyValue += cost;
				playerStats.Units[actorName].Count++;
			}
		}

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			// Work from the real change in strength: damage can exceed the men left, and stragglers returning is not a loss.
			var lost = lastHP - health.HP;
			lastHP = health.HP;
			if (lost <= 0 || self.Owner.WinState != WinState.Undefined)
				return;

			// Men struck off by the unit's own side (e.g. a freed unit set to its surrendered strength) are not casualties.
			var attacker = e.Attacker;
			if (attacker == null || attacker.Owner == self.Owner)
				return;

			playerStats.UnitsDead += lost;

			// Value lost in proportion, carrying the remainder so small losses add up exactly.
			costCarry += (long)lost * cost;
			var value = (int)(costCarry / Math.Max(1, health.MaxHP));
			costCarry -= (long)value * health.MaxHP;
			playerStats.DeathsCost += value;

			if (self.Owner.NonCombatant || attacker.Owner.RelationshipWith(self.Owner) != PlayerRelationship.Enemy)
				return;

			var attackerStats = attacker.Owner.PlayerActor.TraitOrDefault<PlayerStatistics>();
			if (attackerStats != null)
			{
				attackerStats.UnitsKilled += lost;
				attackerStats.KillsCost += value;
			}

			// Score: one point for every man.
			attacker.Owner.PlayerActor.TraitOrDefault<PlayerExperience>()?.GiveExperience(lost);
		}

		void RemoveFromArmyValue()
		{
			if (!includedInArmyValue)
				return;

			includedInArmyValue = false;
			playerStats.ArmyValue -= cost;
			playerStats.Units[actorName].Count--;
		}

		void INotifyKilled.Killed(Actor self, AttackInfo e)
		{
			if (self.Owner.WinState == WinState.Undefined)
				RemoveFromArmyValue();
		}

		void INotifyOwnerChanged.OnOwnerChanged(Actor self, Player oldOwner, Player newOwner)
		{
			var newStats = newOwner.PlayerActor.Trait<PlayerStatistics>();
			if (includedInArmyValue)
			{
				playerStats.ArmyValue -= cost;
				playerStats.Units[actorName].Count--;
				newStats.ArmyValue += cost;
				newStats.Units[actorName].Count++;
			}

			playerStats = newStats;
		}

		void INotifyActorDisposing.Disposing(Actor self)
		{
			RemoveFromArmyValue();
		}
	}

	/// <summary>On-screen notices about divisions (routed, rallied, surrendered...). Shown without the chat sound.</summary>
	public static class DivisionNotice
	{
		public static void Show(World world, string prefix, string text, Color color)
		{
			// Only in a real game. The battle behind the main menu runs while the lobby is open, and the lobby's
			// chat box has no template for transient lines: sending one there crashes the game.
			if (world.Type != WorldType.Regular)
				return;

			// The transient notification panel plays no sound in this mod; mission lines in the chat always do.
			// Its line template has no prefix label, so the prefix goes into the text.
			Ui.Send(new TextNotification(TextNotificationPool.Transients, TextNotificationsManager.SystemClientId, null,
				string.IsNullOrEmpty(prefix) ? text : prefix + ": " + text, null, color));
		}
	}
}
