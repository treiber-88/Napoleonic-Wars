#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Marks a unit as marching while enabled. The world's MarchingSoundPlayer plays one marching loop",
		"for the whole map, at the marching unit nearest the centre of the screen.")]
	public class MarchingSoundInfo : ConditionalTraitInfo
	{
		public override object Create(ActorInitializer init) { return new MarchingSound(this); }
	}

	public class MarchingSound : ConditionalTrait<MarchingSoundInfo>
	{
		public MarchingSound(MarchingSoundInfo info)
			: base(info) { }
	}

	[TraitLocation(SystemActors.World)]
	[Desc("Plays a single looping marching sound however many units are on the march. Attach this to the world actor.",
		"Purely local audio: it never touches synced game state.")]
	public class MarchingSoundPlayerInfo : TraitInfo
	{
		[FieldLoader.Require]
		public readonly string SoundFile = null;

		[Desc("Ticks between checks for the nearest marching unit.")]
		public readonly int Interval = 5;

		public override object Create(ActorInitializer init) { return new MarchingSoundPlayer(this); }
	}

	public class MarchingSoundPlayer : ITick, IWorldLoaded, INotifyActorDisposing
	{
		readonly MarchingSoundPlayerInfo info;
		WorldRenderer worldRenderer;
		ISound sound;
		int ticks;

		public MarchingSoundPlayer(MarchingSoundPlayerInfo info) { this.info = info; }

		void IWorldLoaded.WorldLoaded(World w, WorldRenderer wr) { worldRenderer = wr; }

		void ITick.Tick(Actor self)
		{
			if (worldRenderer == null || --ticks > 0)
				return;

			ticks = info.Interval;

			// The visible marching unit nearest the middle of the screen carries the sound.
			var world = self.World;
			var center = worldRenderer.Viewport.CenterPosition;
			Actor nearest = null;
			var best = long.MaxValue;
			foreach (var pair in world.ActorsWithTrait<MarchingSound>())
			{
				var a = pair.Actor;
				if (pair.Trait.IsTraitDisabled || a.IsDead || !a.IsInWorld || world.FogObscures(a))
					continue;

				var d = (a.CenterPosition - center).HorizontalLengthSquared;
				if (d < best)
				{
					best = d;
					nearest = a;
				}
			}

			if (nearest == null)
			{
				Stop();
				return;
			}

			if (sound == null || sound.Complete)
				sound = Game.Sound.PlayLooped(SoundType.World, info.SoundFile, nearest.CenterPosition);
			else
				sound.SetPosition(nearest.CenterPosition);
		}

		void Stop()
		{
			if (sound == null)
				return;

			Game.Sound.StopSound(sound);
			sound = null;
		}

		void INotifyActorDisposing.Disposing(Actor self) { Stop(); }
	}
}
