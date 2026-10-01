#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Napoleonic.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Orders
{
	/// <summary>Charge button: the next click on an enemy sends the selected units in with bayonet or sabre.</summary>
	public class ChargeOrderGenerator : UnitOrderGenerator
	{
		Actor[] subjects;

		protected override MouseActionType ActionType => MouseActionType.ConfirmOrder;

		public ChargeOrderGenerator(World world, IEnumerable<Actor> subjects)
			: base(world)
		{
			this.subjects = subjects.ToArray();
		}

		static Actor EnemyAtMouse(World world, MouseInput mi)
		{
			return world.ScreenMap.ActorsAtMouse(mi)
				.Select(a => a.Actor)
				.FirstOrDefault(a => !a.IsDead && a.Info.HasTraitInfo<IHealthInfo>() &&
					!a.AppearsFriendlyTo(world.LocalPlayer.PlayerActor) && !world.FogObscures(a));
		}

		// Called by the base class on the action button (mouse release), like the stock Guard command.
		protected override IEnumerable<Order> OrderInner(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			var target = EnemyAtMouse(world, mi);
			if (target == null)
				yield break;

			var queued = mi.Modifiers.HasModifier(Modifiers.Shift);
			if (!queued)
				world.CancelInputMode();

			yield return new Order(RegimentCommands.ChargeOrder, null, Target.FromActor(target), queued, null, subjects);
		}

		public override void SelectionChanged(World world, IEnumerable<Actor> selected)
		{
			subjects = selected.Where(a => !a.IsDead && a.Info.HasTraitInfo<RegimentCommandsInfo>()).ToArray();
			if (subjects.Length == 0)
				world.CancelInputMode();
		}

		public override string GetCursor(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			return EnemyAtMouse(world, mi) != null ? "attack" : "attackoutsiderange";
		}

		public override bool InputOverridesSelection(World world, int2 xy, MouseInput mi) => true;
		public override bool ClearSelectionOnLeftClick => false;
	}

	/// <summary>Run button: the next click on the ground sends the selected units there at the double.</summary>
	public class RunOrderGenerator : UnitOrderGenerator
	{
		Actor[] subjects;

		protected override MouseActionType ActionType => MouseActionType.ConfirmOrder;

		public RunOrderGenerator(World world, IEnumerable<Actor> subjects)
			: base(world)
		{
			this.subjects = subjects.ToArray();
		}

		protected override IEnumerable<Order> OrderInner(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			if (!world.Map.Contains(cell))
				yield break;

			var queued = mi.Modifiers.HasModifier(Modifiers.Shift);
			if (!queued)
				world.CancelInputMode();

			yield return new Order(RegimentCommands.RunOrder, null, Target.FromCell(world, cell), queued, null, subjects);
		}

		public override void SelectionChanged(World world, IEnumerable<Actor> selected)
		{
			subjects = selected.Where(a => !a.IsDead && a.Info.HasTraitInfo<RegimentCommandsInfo>()).ToArray();
			if (subjects.Length == 0)
				world.CancelInputMode();
		}

		public override string GetCursor(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			return world.Map.Contains(cell) ? "move" : "move-blocked";
		}

		public override bool InputOverridesSelection(World world, int2 xy, MouseInput mi) => true;
		public override bool ClearSelectionOnLeftClick => false;
	}
}
