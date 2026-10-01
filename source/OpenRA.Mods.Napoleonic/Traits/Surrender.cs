#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Effects;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("The unit can be ordered to surrender. It lays down its arms and its men are marched off",
		"to the nearest enemy prisoner of war camp, where they stay until the camp is destroyed.")]
	public class SurrendersInfo : TraitInfo, Requires<HealthInfo>
	{
		public override object Create(ActorInitializer init) { return new Surrenders(); }
	}

	public class Surrenders : IResolveOrder
	{
		public const string OrderID = "NWSurrender";

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString != OrderID || self.IsDead || !self.IsInWorld)
				return;

			// Prisoners go to the nearest camp held by an enemy.
			var camp = self.World.ActorsHavingTrait<PrisonerCamp>()
				.Where(a => !a.IsDead && a.IsInWorld && a.Owner.RelationshipWith(self.Owner) == PlayerRelationship.Enemy)
				.MinByOrDefault(a => (a.CenterPosition - self.CenterPosition).HorizontalLengthSquared);

			if (camp == null)
			{
				if (self.Owner == self.World.LocalPlayer)
					TextNotificationsManager.AddMissionLine("Your army", "No enemy holds a prisoner of war camp to surrender to.",
						Color.FromArgb(255, 170, 60));

				return;
			}

			var men = self.Trait<Health>().HP;
			camp.Trait<PrisonerCamp>().AddPrisoners(self.Owner, self.Info.Name, men);

			var name = self.TraitOrDefault<DivisionName>()?.FullName ?? self.Info.Name;
			var local = self.World.LocalPlayer;
			if (local == null || self.Owner == local || camp.Owner == local || !self.World.FogObscures(self))
				TextNotificationsManager.AddMissionLine(self.Owner == local ? "Your army" : self.Owner.ResolvedPlayerName,
					$"{name} has surrendered! {men} men taken prisoner.", Color.FromArgb(255, 80, 60));

			// The unit leaves the field: no casualties, no bodies.
			self.World.AddFrameEndTask(w =>
			{
				if (!self.Disposed)
					self.Dispose();
			});
		}
	}

	[Desc("Holds surrendered enemy units. Every PrisonersPerPayment prisoners held pays the owner Payment each Interval.",
		"When the camp is destroyed or sold the prisoners are freed and take up arms again for their original owners.")]
	public class PrisonerCampInfo : TraitInfo
	{
		[Desc("Prisoners needed for one payment.")]
		public readonly int PrisonersPerPayment = 1000;

		[Desc("Cash paid per PrisonersPerPayment prisoners held.")]
		public readonly int Payment = 500;

		[Desc("Ticks between payments.")]
		public readonly int Interval = 750;

		public readonly bool ShowTicks = true;

		[Desc("Freed units form up within this many cells of the camp.")]
		public readonly int ReleaseRadius = 8;

		public readonly string Font = "TinyBold";

		public override object Create(ActorInitializer init) { return new PrisonerCamp(this); }
	}

	public class PrisonerCamp : ITick, INotifyKilled, INotifySold, IRenderAnnotations, ISync
	{
		readonly PrisonerCampInfo info;
		readonly List<(Player Owner, string Unit, int Men)> prisoners = [];
		SpriteFont font;
		int ticks;

		public PrisonerCamp(PrisonerCampInfo info)
		{
			this.info = info;
			ticks = info.Interval;
		}

		[VerifySync]
		public int Held { get; private set; }

		public void AddPrisoners(Player owner, string unit, int men)
		{
			if (men <= 0)
				return;

			prisoners.Add((owner, unit, men));
			Held += men;
		}

		void ITick.Tick(Actor self)
		{
			if (--ticks > 0)
				return;

			ticks = info.Interval;
			var cash = Held / info.PrisonersPerPayment * info.Payment;
			if (cash <= 0)
				return;

			self.Owner.PlayerActor.Trait<PlayerResources>().GiveCash(cash);
			if (info.ShowTicks && self.Owner.IsAlliedWith(self.World.RenderPlayer))
				self.World.AddFrameEndTask(w => w.Add(new FloatingText(self.CenterPosition, self.Owner.Color,
					FloatingText.FormatCashTick(cash), 30)));
		}

		void INotifyKilled.Killed(Actor self, AttackInfo e) { Release(self); }

		void INotifySold.Selling(Actor self) { }

		void INotifySold.Sold(Actor self) { Release(self); }

		/// <summary>Frees every prisoner: each unit reappears near the camp for its original owner at the strength it surrendered with.</summary>
		void Release(Actor self)
		{
			if (prisoners.Count == 0)
				return;

			var world = self.World;
			var freed = prisoners.ToList();
			prisoners.Clear();
			Held = 0;

			var origin = self.Location;
			var facing = world.SharedRandom.Next(1024);
			var cells = world.Map.FindTilesInAnnulus(origin, 2, info.ReleaseRadius)
				.OrderBy(c => (c - origin).LengthSquared)
				.ToList();

			world.AddFrameEndTask(w =>
			{
				var used = new HashSet<CPos>();
				var liberated = new Dictionary<Player, int>();
				foreach (var (owner, unit, men) in freed)
				{
					// Men whose country is out of the war have no army to return to.
					if (owner.WinState == WinState.Lost || !w.Map.Rules.Actors.TryGetValue(unit, out var actorInfo))
						continue;

					var mobile = actorInfo.TraitInfoOrDefault<MobileInfo>();
					var maxHP = actorInfo.TraitInfoOrDefault<HealthInfo>()?.HP ?? 0;
					if (mobile == null || maxHP <= 0)
						continue;

					// Leave a free cell between units so their formations do not overlap too badly.
					var cell = cells.FirstOrDefault(c => !used.Contains(c) && mobile.CanEnterCell(w, null, c), origin);
					used.Add(cell);
					foreach (var d in CVec.Directions)
						used.Add(cell + d);

					var percent = Math.Clamp((men * 100 + maxHP - 1) / maxHP, 1, 100);
					var a = w.CreateActor(unit, new TypeDictionary
					{
						new OwnerInit(owner),
						new LocationInit(cell),
						new FacingInit(new WAngle(facing)),
						new HealthInit(percent),
					});

					// HealthInit works in whole percent: trim to the exact number of men.
					var health = a.Trait<Health>();
					if (health.HP > men)
						health.InflictDamage(a, a, new Damage(health.HP - men), true);

					liberated[owner] = liberated.GetValueOrDefault(owner) + men;
				}

				var local = w.LocalPlayer;
				foreach (var (owner, men) in liberated)
					if (local == null || owner == local || self.Owner == local)
						TextNotificationsManager.AddMissionLine(owner == local ? "Your army" : owner.ResolvedPlayerName,
							$"{men} prisoners of war have been liberated!", Color.FromArgb(120, 220, 120));
			});
		}

		IEnumerable<IRenderable> IRenderAnnotations.RenderAnnotations(Actor self, WorldRenderer wr)
		{
			if (self.IsDead || !self.IsInWorld || self.World.FogObscures(self))
				yield break;

			font ??= Game.Renderer.Fonts[info.Font];
			var pos = wr.ScreenPxPosition(self.CenterPosition) - new int2(0, 34);
			yield return new TextAnnotationRenderable(font, wr.ProjectedPosition(pos), 0, self.Owner.Color,
				"Prisoners: " + Held.ToString(NumberFormat.Invariant));
		}

		bool IRenderAnnotations.SpatiallyPartitionable => true;
	}
}
