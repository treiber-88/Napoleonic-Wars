#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Generic;
using OpenRA.Graphics;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[TraitLocation(SystemActors.World)]
	[Desc("Keeps the bodies of fallen soldiers, horses and wrecked guns on the battlefield for the rest of the game.")]
	public class CorpseLayerInfo : TraitInfo
	{
		[Desc("Z offset of corpses, so living figures are drawn over them.")]
		public readonly int ZOffset = -512;

		[Desc("Size of the spatial bins used to find corpses on screen, in cells.")]
		public readonly int BinSize = 8;

		public override object Create(ActorInitializer init) { return new CorpseLayer(init.Self, this); }
	}

	public class CorpseLayer : IRender, ITick
	{
		sealed class Corpse
		{
			public WPos Pos;
			public WAngle Facing;
			public Animation Anim;
			public string Palette;
			public float3 Tint;
		}

		readonly CorpseLayerInfo info;
		readonly World world;
		readonly Dictionary<int2, List<Corpse>> bins = [];
		readonly List<Corpse> dying = [];
		readonly int binSize;

		public CorpseLayer(Actor self, CorpseLayerInfo info)
		{
			this.info = info;
			world = self.World;
			binSize = 1024 * info.BinSize;
		}

		public int Count { get; private set; }

		/// <param name="animate">Play the sequence once and keep its last frame; otherwise hold the first frame.</param>
		public void AddCorpse(WPos pos, string image, string sequence, WAngle facing, string palette, float3 tint, bool animate)
		{
			var corpse = new Corpse { Pos = pos, Facing = facing, Palette = palette, Tint = tint };
			var anim = new Animation(world, image, () => corpse.Facing);
			corpse.Anim = anim;

			if (animate)
			{
				dying.Add(corpse);
				anim.PlayThen(sequence, () =>
				{
					var last = anim.CurrentSequence.Length - 1;
					anim.PlayFetchIndex(sequence, () => last);
					dying.Remove(corpse);
				});
			}
			else
				anim.PlayFetchIndex(sequence, () => 0);

			var key = new int2(pos.X / binSize, pos.Y / binSize);
			if (!bins.TryGetValue(key, out var bin))
				bins[key] = bin = [];

			bin.Add(corpse);
			Count++;
		}

		void ITick.Tick(Actor self)
		{
			// Iterate over a copy: finishing a death animation removes the corpse from the list.
			foreach (var c in dying.ToArray())
				c.Anim.Tick();
		}

		IEnumerable<IRenderable> IRender.Render(Actor self, WorldRenderer wr)
		{
			var tl = wr.ProjectedPosition(wr.Viewport.TopLeft);
			var br = wr.ProjectedPosition(wr.Viewport.BottomRight);

			// Allow for sprites hanging over the edge of the viewport.
			var x0 = (tl.X - 1024) / binSize;
			var y0 = (tl.Y - 1024) / binSize;
			var x1 = (br.X + 1024) / binSize;
			var y1 = (br.Y + 1024) / binSize;

			for (var y = y0; y <= y1; y++)
			{
				for (var x = x0; x <= x1; x++)
				{
					if (!bins.TryGetValue(new int2(x, y), out var bin))
						continue;

					foreach (var c in bin)
					{
						var palette = wr.Palette(c.Palette);
						foreach (var r in c.Anim.Render(c.Pos, WVec.Zero, info.ZOffset, palette))
						{
							if (c.Tint != float3.Ones && r is IModifyableRenderable mr)
								yield return mr.WithTint(c.Tint, mr.TintModifiers).AsDecoration();
							else
								yield return r.AsDecoration();
						}
					}
				}
			}
		}

		IEnumerable<Rectangle> IRender.ScreenBounds(Actor self, WorldRenderer wr)
		{
			yield break;
		}
	}
}
