#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System;
using System.Linq;
using OpenRA.FileSystem;
using OpenRA.Graphics;
using OpenRA.Mods.Common.LoadScreens;
using OpenRA.Primitives;

namespace OpenRA.Mods.Napoleonic.LoadScreens
{
	/// <summary>
	/// Shows a painting filling the whole window (scaled to cover it, keeping its proportions),
	/// with a rotating loading message in the bottom-right corner.
	/// mod.yaml: LoadScreen: PaintingLoadScreen, with Image (a power-of-two sheet) and ImageSize (the painting's
	/// width,height in the sheet's top-left corner).
	/// </summary>
	public sealed class PaintingLoadScreen : SheetLoadScreen
	{
		[FluentReference]
		const string Loading = "loadscreen-loading";

		Sprite painting;
		Sheet lastSheet;
		Size imageSize = new(1024, 730);
		string[] messages = [];
		string message;
		int messageTicks;

		public override void Init(Manifest manifest, IReadOnlyFileSystem fileSystem)
		{
			base.Init(manifest, fileSystem);

			if (Info.TryGetValue("ImageSize", out var size))
				imageSize = FieldLoader.GetValue<Size>("ImageSize", size);

			messages = FluentProvider.GetMessage(Loading).Split(',').Select(x => x.Trim()).Where(x => x.Length > 0).ToArray();
		}

		public override void DisplayInner(Renderer r, Sheet s, int density)
		{
			if (s != lastSheet)
			{
				lastSheet = s;
				painting = s == null ? null : CreateSprite(s, density, new Rectangle(0, 0, imageSize.Width, imageSize.Height));
			}

			var res = r.Resolution;
			if (painting != null)
			{
				// Cover the window: scale up until both sides are filled, centre, and let the overflow crop.
				var scale = Math.Max((float)res.Width / imageSize.Width, (float)res.Height / imageSize.Height);
				var pos = new float3((res.Width - imageSize.Width * scale) / 2, (res.Height - imageSize.Height * scale) / 2, 0);
				r.RgbaSpriteRenderer.DrawSprite(painting, pos, scale);
			}

			if (r.Fonts == null || messages.Length == 0)
				return;

			// The screen redraws at most 5 times a second: change the message every few seconds.
			if (message == null || --messageTicks <= 0)
			{
				message = messages.Random(Game.CosmeticRandom);
				messageTicks = 15;
			}

			var font = r.Fonts["Bold"];
			var textSize = font.Measure(message);
			var textPos = new float2(res.Width - textSize.X - 24, res.Height - textSize.Y - 22);
			r.RgbaColorRenderer.FillRect(
				new float3(textPos.X - 12, textPos.Y - 8, 0),
				new float3(res.Width - 12, textPos.Y + textSize.Y + 8, 0),
				Color.FromArgb(150, 0, 0, 0));
			font.DrawTextWithShadow(message, textPos, Color.FromArgb(240, 230, 200), Color.Black, 1);
		}
	}
}
