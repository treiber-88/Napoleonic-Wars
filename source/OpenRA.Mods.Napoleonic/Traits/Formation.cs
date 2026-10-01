#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Primitives;
using OpenRA.Support;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	public enum FormationShape { Line, Block, Loose, Battery }

	[Desc("Renders a unit as a formation of individual figures (soldiers, horsemen or guns) that move, fire and die independently.",
		"The actor's Health is the unit's numerical value; one figure is removed each time MaxHP / Models points of damage accumulate.")]
	public class FormationInfo : TraitInfo, Requires<HealthInfo>, Requires<RenderSpritesInfo>
	{
		[Desc("Number of visible figures at full strength.")]
		public readonly int Models = 60;

		[Desc("Line = ranks of figures, Block = square/column, Loose = scattered group, Battery = single line of guns.")]
		public readonly FormationShape Shape = FormationShape.Line;

		[Desc("Number of ranks for Line shape.")]
		public readonly int Ranks = 2;

		[Desc("Number of files for Block and Loose shapes. 0 = square root of the figure count.")]
		public readonly int Files = 0;

		[Desc("Distance between figures side by side.")]
		public readonly WDist Spacing = new(224);

		[Desc("Distance between ranks.")]
		public readonly WDist RankSpacing = new(256);

		[Desc("Random displacement of each figure in Loose shape.")]
		public readonly WDist LooseJitter = new(160);

		[Desc("Random displacement of each figure while disordered (running, charging or routed).")]
		public readonly WDist DisorderJitter = new(384);

		[Desc("How far a figure may move per tick on top of the unit's own movement when (re)forming.",
			"Higher values mean the unit forms and reforms faster.")]
		public readonly WDist ReformSpeed = new(20);

		[Desc("Figures further than this from their place in the formation count as out of formation.")]
		public readonly WDist InPositionTolerance = new(128);

		[Desc("Sprite image used for the figures. Defaults to the actor's RenderSprites image.")]
		public readonly string Image = null;

		[SequenceReference(nameof(Image), allowNullImage: true)]
		public readonly string StandSequence = "stand";

		[SequenceReference(nameof(Image), allowNullImage: true)]
		public readonly string MoveSequence = "run";

		[Desc("Played once per shot. Leave empty if the image has no firing animation.")]
		public readonly string ShootSequence = "shoot";

		[Desc("Death animations, one picked at random per fallen figure. The last frame remains on the field forever.",
			"If empty, the figure's current sprite is left behind tinted with WreckTint (for guns).")]
		public readonly ImmutableArray<string> DeathSequences = ["die1", "die2", "die3", "die4", "die5"];

		[Desc("Colour multiplier used for wrecks when DeathSequences is empty.")]
		public readonly float3 WreckTint = new(0.35f, 0.32f, 0.3f);

		[PaletteReference(true)]
		public readonly string Palette = "player";

		public readonly bool IsPlayerPalette = true;

		[GrantedConditionReference]
		[Desc("Condition granted while figures are out of formation. Use it to stop the unit firing until formed.")]
		public readonly string FormingCondition = "forming";

		[Desc("Whether the unit's formation is broken up whenever it is disordered (running, charging, routed).")]
		public readonly bool CanBeDisordered = true;

		public override object Create(ActorInitializer init) { return new Formation(init.Self, this); }

		public WDist MaxRadius
		{
			get
			{
				var files = Shape == FormationShape.Line ? (Models + Ranks - 1) / Ranks
					: Shape == FormationShape.Battery ? Models
					: Files > 0 ? Files : (int)Math.Ceiling(Math.Sqrt(Models));
				var ranks = (Models + files - 1) / files;
				var w = files * Spacing.Length / 2;
				var h = ranks * RankSpacing.Length / 2;
				return new WDist((int)Math.Sqrt((long)w * w + (long)h * h) + LooseJitter.Length + DisorderJitter.Length + 512);
			}
		}
	}

	public class FormationModel
	{
		public readonly int Index;
		public WPos Pos;
		public WAngle Facing;
		public Animation Anim;
		public bool Moving;
		public bool Shooting;

		public FormationModel(int index) { Index = index; }
	}

	public class Formation : IRender, IAutoMouseBounds, ITick, INotifyCreated, INotifyKilled, ITargetablePositions, INotifyAddedToWorld
	{
		public readonly FormationInfo Info;
		readonly Actor self;
		readonly List<FormationModel> alive = [];
		readonly string image;
		readonly WDist maxRadius;
		Health health;
		CorpseLayer corpses;
		FormationSpeedMultiplier[] speedMultipliers;
		WPos lastCenter;
		int formingToken = Actor.InvalidConditionToken;
		int disorderCount;
		int boundsRefresh;
		int nextModelIndex;
		int reformCarry;

		public Formation(Actor self, FormationInfo info)
		{
			this.self = self;
			Info = info;
			image = info.Image ?? self.Info.TraitInfo<RenderSpritesInfo>().GetImage(self.Info, self.Owner.Faction.InternalName);
			maxRadius = info.MaxRadius;
		}

		public IReadOnlyList<FormationModel> Models => alive;
		public int AliveCount => alive.Count;
		public bool InFormation { get; private set; }
		public bool Disordered => Info.CanBeDisordered && disorderCount > 0;

		/// <summary>Numerical value represented by each visible figure.</summary>
		public int NumericalPerModel => Math.Max(1, health.MaxHP / Info.Models);

		public void AddDisorder() { disorderCount++; }
		public void RemoveDisorder() { disorderCount = Math.Max(0, disorderCount - 1); }

		void INotifyCreated.Created(Actor self)
		{
			health = self.Trait<Health>();
			corpses = self.World.WorldActor.TraitOrDefault<CorpseLayer>();
			speedMultipliers = self.TraitsImplementing<FormationSpeedMultiplier>().ToArray();

			for (var i = 0; i < Info.Models; i++)
				alive.Add(CreateModel(self));

			PlaceModelsInSlots(self);
		}

		FormationModel CreateModel(Actor self)
		{
			var model = new FormationModel(nextModelIndex++);
			model.Anim = new Animation(self.World, image, () => model.Facing);
			model.Anim.PlayRepeating(Info.StandSequence);
			model.Pos = self.CenterPosition;
			model.Facing = self.Orientation.Yaw;
			return model;
		}

		void INotifyAddedToWorld.AddedToWorld(Actor self)
		{
			// Actors placed on the map or unloaded from a building appear formed up.
			PlaceModelsInSlots(self);
		}

		void PlaceModelsInSlots(Actor self)
		{
			var center = self.CenterPosition;
			var yaw = self.Orientation.Yaw;
			var slots = ComputeSlots(alive.Count, yaw);
			for (var i = 0; i < alive.Count; i++)
			{
				alive[i].Pos = center + slots[i];
				alive[i].Facing = yaw;
			}

			lastCenter = center;
		}

		/// <summary>Figure offsets from the unit centre, front rank first, left to right.</summary>
		WVec[] ComputeSlots(int count, WAngle yaw)
		{
			var slots = new WVec[count];
			if (count == 0)
				return slots;

			int files;
			int rankSpacing;
			switch (Info.Shape)
			{
				case FormationShape.Line:
					files = (count + Info.Ranks - 1) / Info.Ranks;
					rankSpacing = Info.RankSpacing.Length;
					break;
				case FormationShape.Battery:
					files = count;
					rankSpacing = Info.RankSpacing.Length;
					break;
				default:
					files = Info.Files > 0 ? Info.Files : (int)Math.Ceiling(Math.Sqrt(Info.Models));
					files = Math.Min(files, count);
					rankSpacing = Info.RankSpacing.Length;
					break;
			}

			var ranks = (count + files - 1) / files;
			var rot = WRot.FromYaw(yaw);
			var forward = new WVec(0, -1024, 0).Rotate(rot);
			var right = new WVec(1024, 0, 0).Rotate(rot);

			var jitter = Info.Shape == FormationShape.Loose ? Info.LooseJitter.Length : 0;
			if (Disordered)
				jitter += Info.DisorderJitter.Length;

			for (var i = 0; i < count; i++)
			{
				var rank = i / files;
				var file = i % files;

				// The last rank may be incomplete; centre it.
				var filesInRank = rank == ranks - 1 ? count - rank * files : files;
				var lateral = (2 * file - (filesInRank - 1)) * Info.Spacing.Length / 2;
				var depth = ((ranks - 1) * rankSpacing / 2) - rank * rankSpacing;

				// Loose shapes stagger alternate ranks.
				if (Info.Shape == FormationShape.Loose && (rank & 1) == 1)
					lateral += Info.Spacing.Length / 2;

				if (jitter > 0)
				{
					var model = alive[i];
					lateral += Hash(model.Index, self.ActorID, 1) % (2 * jitter + 1) - jitter;
					depth += Hash(model.Index, self.ActorID, 2) % (2 * jitter + 1) - jitter;
				}

				slots[i] = forward * depth / 1024 + right * lateral / 1024;
			}

			return slots;
		}

		// Deterministic per-figure scatter so that all clients agree on figure positions.
		static int Hash(int a, uint b, int c)
		{
			unchecked
			{
				var h = (uint)a * 0x9E3779B1u ^ b * 0x85EBCA77u ^ (uint)c * 0xC2B2AE3Du;
				h ^= h >> 15;
				h *= 0x2C1B3C6Du;
				h ^= h >> 12;
				return (int)(h & 0x7FFFFFFF);
			}
		}

		void ITick.Tick(Actor self)
		{
			RemoveCasualties(self);

			var center = self.CenterPosition;
			var yaw = self.Orientation.Yaw;
			var unitMoved = (center - lastCenter).HorizontalLength;
			lastCenter = center;

			var slots = ComputeSlots(alive.Count, yaw);
			// Work in hundredths and carry the remainder so small percentage bonuses are not rounded away.
			var reform = Info.ReformSpeed.Length * (Disordered ? 2 : 1) * 100;
			foreach (var m in speedMultipliers)
				reform = reform * m.GetModifier() / 100;

			reform += reformCarry;
			reformCarry = reform % 100;
			var step = unitMoved + reform / 100;
			var tolerance = Info.InPositionTolerance.Length;
			var inFormation = true;

			for (var i = 0; i < alive.Count; i++)
			{
				var m = alive[i];
				var target = center + slots[i];
				var delta = target - m.Pos;
				var dist = delta.HorizontalLength;

				if (dist > step)
				{
					m.Pos += delta * step / dist;
					m.Facing = delta.Yaw;
					m.Moving = true;
				}
				else
				{
					m.Pos = target;
					m.Moving = unitMoved > 0;
					m.Facing = yaw;
				}

				if (dist > tolerance)
					inFormation = false;

				if (!m.Shooting)
				{
					var seq = m.Moving ? Info.MoveSequence : Info.StandSequence;
					if (m.Anim.CurrentSequence == null || m.Anim.CurrentSequence.Name != seq)
						m.Anim.PlayRepeating(seq);
				}

				m.Anim.Tick();
			}

			InFormation = inFormation;
			if (!inFormation && formingToken == Actor.InvalidConditionToken)
				formingToken = self.GrantCondition(Info.FormingCondition);
			else if (inFormation && formingToken != Actor.InvalidConditionToken)
				formingToken = self.RevokeCondition(formingToken);

			// Mouse bounds follow the figures, so refresh the screen map while they move about.
			if (self.IsInWorld && --boundsRefresh <= 0)
			{
				boundsRefresh = 5;
				self.World.ScreenMap.AddOrUpdate(self);
			}
		}

		void RemoveCasualties(Actor self)
		{
			if (health.IsDead)
				return;

			// Figures remaining = numerical value / numerical value per figure, rounded up.
			var desired = health.HP <= 0 ? 0 : (int)Math.Min(Info.Models, ((long)health.HP * Info.Models + health.MaxHP - 1) / health.MaxHP);
			while (alive.Count > desired)
				KillModel(self, alive[self.World.SharedRandom.Next(alive.Count)]);

			// Returning stragglers (regained strength) rejoin at the centre and walk to their place.
			while (alive.Count < desired)
				alive.Add(CreateModel(self));
		}

		void KillModel(Actor self, FormationModel m)
		{
			alive.Remove(m);
			if (corpses == null)
				return;

			var palette = Info.IsPlayerPalette ? Info.Palette + self.Owner.InternalName : Info.Palette;
			if (Info.DeathSequences.Length > 0)
			{
				var seq = Info.DeathSequences.Random(self.World.SharedRandom);
				corpses.AddCorpse(m.Pos, image, seq, m.Facing, palette, float3.Ones, true);
			}
			else
			{
				var seq = m.Anim.CurrentSequence?.Name ?? Info.StandSequence;
				corpses.AddCorpse(m.Pos, image, seq, m.Facing, palette, Info.WreckTint, false);
			}
		}

		void INotifyKilled.Killed(Actor self, AttackInfo e)
		{
			while (alive.Count > 0)
				KillModel(self, alive[^1]);
		}

		/// <summary>Called by weapons so the figure plays its firing (or throwing) animation.</summary>
		public void NotifyFired(FormationModel m, string sequence = null)
		{
			var seq = string.IsNullOrEmpty(sequence) ? Info.ShootSequence : sequence;
			if (string.IsNullOrEmpty(seq) || !alive.Contains(m) || !m.Anim.HasSequence(seq))
				return;

			m.Shooting = true;
			m.Anim.PlayThen(seq, () =>
			{
				m.Shooting = false;
				m.Anim.PlayRepeating(Info.StandSequence);
			});
		}

		public int CountModelsWithin(WPos pos, WDist range, int max)
		{
			var r2 = (long)range.Length * range.Length;
			var count = 0;
			foreach (var m in alive)
			{
				if ((m.Pos - pos).HorizontalLengthSquared <= r2 && ++count >= max)
					break;
			}

			return count;
		}

		public WPos RandomModelPosition(MersenneTwister random)
		{
			return alive.Count == 0 ? self.CenterPosition : alive[random.Next(alive.Count)].Pos;
		}

		IEnumerable<WPos> ITargetablePositions.TargetablePositions(Actor self)
		{
			foreach (var m in alive)
				yield return m.Pos;
		}

		IEnumerable<IRenderable> IRender.Render(Actor self, WorldRenderer wr)
		{
			var palette = wr.Palette(Info.IsPlayerPalette ? Info.Palette + self.Owner.InternalName : Info.Palette);
			foreach (var m in alive)
				foreach (var r in m.Anim.Render(m.Pos, WVec.Zero, 0, palette))
					yield return r;
		}

		IEnumerable<Rectangle> IRender.ScreenBounds(Actor self, WorldRenderer wr)
		{
			var c = wr.ScreenPxPosition(self.CenterPosition);
			var r = maxRadius.Length * wr.TileSize.Width / wr.TileScale;
			yield return new Rectangle(c.X - r, c.Y - r, 2 * r, 2 * r);
		}

		Rectangle IAutoMouseBounds.AutoMouseoverBounds(Actor self, WorldRenderer wr)
		{
			if (alive.Count == 0)
				return Rectangle.Empty;

			int minX = int.MaxValue, minY = int.MaxValue, maxX = int.MinValue, maxY = int.MinValue;
			foreach (var m in alive)
			{
				var p = wr.ScreenPxPosition(m.Pos);
				minX = Math.Min(minX, p.X);
				minY = Math.Min(minY, p.Y);
				maxX = Math.Max(maxX, p.X);
				maxY = Math.Max(maxY, p.Y);
			}

			const int Pad = 8;
			return Rectangle.FromLTRB(minX - Pad, minY - 2 * Pad, maxX + Pad, maxY + Pad);
		}
	}
}
