#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.GameRules;
using OpenRA.Mods.Common.Effects;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("An Armament that fires one projectile from every living figure of a Formation at once (a volley).",
		"Without a Formation, every LocalOffset fires at once (a ship's broadside).",
		"The weapon's ReloadDelay applies to the whole unit.")]
	public class VolleyArmamentInfo : ArmamentInfo, Requires<AttackBaseInfo>
	{
		[Desc("Projectiles fired by each figure or barrel per volley (e.g. canister balls).")]
		public readonly int ProjectilesPerModel = 1;

		[Desc("Only one in this many figures fires (e.g. 4 = one grenade per four grenadiers).")]
		public readonly int ModelsPerProjectile = 1;

		[Desc("Each shot is delayed by a random number of ticks up to this value.",
			"Small values give a ragged volley; values near ReloadDelay make figures fire independently.")]
		public readonly int MaxStagger = 2;

		[Desc("Height above the figure that shots leave from.")]
		public readonly WDist MuzzleHeight = new(128);

		[Desc("Aim at a random figure of the target instead of its nearest point.")]
		public readonly bool AimAtRandomFigure = true;

		[Desc("Random offset added to every aim point, on top of the projectile's own inaccuracy.")]
		public readonly WDist AimScatter = WDist.Zero;

		[Desc("Animation the firing figures play. Defaults to the Formation's ShootSequence.")]
		public readonly string ShootSequence = null;

		[Desc("Effect image spawned at every firing figure or barrel (muzzle smoke).")]
		public readonly string VolleyEffectImage = null;

		[SequenceReference(nameof(VolleyEffectImage), allowNullImage: true)]
		public readonly string VolleyEffectSequence = null;

		[PaletteReference]
		public readonly string VolleyEffectPalette = "effect";

		public override object Create(ActorInitializer init) { return new VolleyArmament(init.Self, this); }
	}

	public class VolleyArmament : Armament
	{
		readonly VolleyArmamentInfo info;
		Formation formation;
		INotifyAttack[] notifyAttacks;
		IEnumerable<int> damageModifiers;
		IEnumerable<int> inaccuracyModifiers;
		IEnumerable<int> rangeModifiers;

		public VolleyArmament(Actor self, VolleyArmamentInfo info)
			: base(self, info)
		{
			this.info = info;
		}

		protected override void Created(Actor self)
		{
			formation = self.TraitOrDefault<Formation>();
			notifyAttacks = self.TraitsImplementing<INotifyAttack>().ToArray();
			damageModifiers = self.TraitsImplementing<IFirepowerModifier>().ToArray().Select(m => m.GetFirepowerModifier());
			inaccuracyModifiers = self.TraitsImplementing<IInaccuracyModifier>().ToArray().Select(m => m.GetInaccuracyModifier());
			rangeModifiers = self.TraitsImplementing<IRangeModifier>().ToArray().Select(m => m.GetRangeModifier());
			base.Created(self);
		}

		protected override void FireBarrel(Actor self, IFacing facing, in Target target, Barrel barrel)
		{
			foreach (var n in notifyAttacks)
				n.PreparingAttack(self, target, this, barrel);


			var world = self.World;
			var random = world.SharedRandom;
			var dm = damageModifiers.ToArray();
			var im = inaccuracyModifiers.ToArray();
			var rm = rangeModifiers.ToArray();
			var up = new WVec(0, 0, info.MuzzleHeight.Length);

			var shooters = new List<(WPos Pos, FormationModel Model)>();
			if (formation != null)
			{
				var models = formation.Models;
				for (var i = 0; i < models.Count; i += info.ModelsPerProjectile)
					shooters.Add((models[i].Pos + up, models[i]));
			}
			else
				foreach (var b in Barrels)
					shooters.Add((self.CenterPosition + MuzzleOffset(self, b), null));

			var targetFormation = target.Type == TargetType.Actor ? target.Actor.TraitOrDefault<Formation>() : null;
			var delayedTarget = target;

			foreach (var (source, model) in shooters)
			{
				for (var p = 0; p < info.ProjectilesPerModel; p++)
				{
					var aim = targetFormation != null && info.AimAtRandomFigure && targetFormation.AliveCount > 0
						? targetFormation.RandomModelPosition(random)
						: target.Positions.ClosestToIgnoringPath(source);

					if (info.AimScatter.Length > 0)
						aim += WVec.FromPDF(random, 2) * info.AimScatter.Length / 1024;

					var src = source;
					var args = new ProjectileArgs
					{
						Weapon = Weapon,
						Facing = (aim - src).Yaw,
						CurrentMuzzleFacing = () => (aim - src).Yaw,
						DamageModifiers = dm,
						InaccuracyModifiers = im,
						RangeModifiers = rm,
						Source = src,
						CurrentSource = () => src,
						SourceActor = self,
						PassiveTarget = aim,
						GuidedTarget = delayedTarget,
					};

					var shooter = model;
					var first = p == 0;
					var delay = Info.FireDelay + (info.MaxStagger > 0 ? random.Next(info.MaxStagger + 1) : 0);
					ScheduleDelayedAction(delay, Burst, _ =>
					{
						if (self.IsDead || !self.IsInWorld)
							return;

						var projectile = Weapon.Projectile?.Create(args);
						if (projectile != null)
							world.Add(projectile);

						if (!first)
							return;

						if (shooter != null)
							formation.NotifyFired(shooter, info.ShootSequence);

						if (info.VolleyEffectImage != null && info.VolleyEffectSequence != null)
							world.AddFrameEndTask(w => w.Add(new SpriteEffect(src, w, info.VolleyEffectImage,
								info.VolleyEffectSequence, info.VolleyEffectPalette)));
					});
				}
			}

			// One report for the whole volley rather than one per musket.
			ScheduleDelayedAction(Info.FireDelay, Burst, _ =>
			{
				if (self.IsDead)
					return;

				if (Weapon.Report != null && Weapon.Report.Length > 0)
					Game.Sound.Play(SoundType.World, Weapon.Report, world, self.CenterPosition);

				Recoil = Info.Recoil;
				foreach (var n in notifyAttacks)
					n.Attacking(self, delayedTarget, this, barrel);
			});
		}
	}
}
