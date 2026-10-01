#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System;
using System.Collections.Generic;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Always shows the unit's numerical value (current Health) above its figures.",
		"The division name is added while the unit is selected, and a warning while it is routed.")]
	public class NumericalDisplayInfo : TraitInfo, Requires<HealthInfo>
	{
		public readonly string Font = "TinyBold";

		public readonly string NameFont = "Tiny";

		[Desc("Screen pixels between the highest figure and the number.")]
		public readonly int Margin = 14;

		public readonly Color RoutedColor = Color.FromArgb(255, 60, 40);

		public override object Create(ActorInitializer init) { return new NumericalDisplay(this); }
	}

	public class NumericalDisplay : INotifyCreated, IRenderAnnotations
	{
		readonly NumericalDisplayInfo info;
		Health health;
		Formation formation;
		DivisionName division;
		Morale morale;
		SpriteFont font;
		SpriteFont nameFont;

		public NumericalDisplay(NumericalDisplayInfo info) { this.info = info; }

		void INotifyCreated.Created(Actor self)
		{
			health = self.Trait<Health>();
			formation = self.TraitOrDefault<Formation>();
			division = self.TraitOrDefault<DivisionName>();
			morale = self.TraitOrDefault<Morale>();
		}

		IEnumerable<IRenderable> IRenderAnnotations.RenderAnnotations(Actor self, WorldRenderer wr)
		{
			if (self.IsDead || !self.IsInWorld || self.World.FogObscures(self))
				yield break;

			font ??= Game.Renderer.Fonts[info.Font];
			nameFont ??= Game.Renderer.Fonts[info.NameFont];

			// Anchor above the top-most figure so the number sits over the formation.
			var center = wr.ScreenPxPosition(self.CenterPosition);
			var top = center.Y;
			if (formation != null)
				foreach (var m in formation.Models)
					top = Math.Min(top, wr.ScreenPxPosition(m.Pos).Y);

			var y = top - info.Margin;
			var color = self.Owner.Color;
			yield return new TextAnnotationRenderable(font, wr.ProjectedPosition(new int2(center.X, y)), 0, color, health.HP.ToString(NumberFormat.Invariant));

			var routed = morale != null && morale.IsRouted;
			if (routed)
			{
				y -= font.Measure("0").Y + 1;
				yield return new TextAnnotationRenderable(nameFont, wr.ProjectedPosition(new int2(center.X, y)), 0, info.RoutedColor, morale.IsAtBay ? "AT BAY" : "ROUTED");
			}

			if (division != null && self.World.Selection.Contains(self))
			{
				y -= nameFont.Measure("0").Y + 1;
				yield return new TextAnnotationRenderable(nameFont, wr.ProjectedPosition(new int2(center.X, y)), 0, color, division.FullName);
			}
		}

		bool IRenderAnnotations.SpatiallyPartitionable => true;
	}

	static class NumberFormat
	{
		public static readonly IFormatProvider Invariant = System.Globalization.CultureInfo.InvariantCulture;
	}
}
