#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Napoleonic.Orders;
using OpenRA.Mods.Napoleonic.Traits;
using OpenRA.Widgets;

namespace OpenRA.Mods.Napoleonic.Widgets.Logic
{
	/// <summary>Charge / Run / Stand buttons for infantry and cavalry, and ammunition buttons for batteries.</summary>
	public class RegimentCommandsLogic : ChromeLogic
	{
		readonly World world;
		int selectionHash = -1;
		Actor[] regiments = [];
		Actor[] batteries = [];
		Actor[] surrenderers = [];

		[ObjectCreator.UseCtor]
		public RegimentCommandsLogic(Widget widget, World world)
		{
			this.world = world;

			var regimentPanel = widget.GetOrNull("REGIMENT_COMMANDS");
			if (regimentPanel != null)
				regimentPanel.IsVisible = () => { Update(); return regiments.Length > 0; };

			var batteryPanel = widget.GetOrNull("BATTERY_COMMANDS");
			if (batteryPanel != null)
				batteryPanel.IsVisible = () => { Update(); return batteries.Length > 0; };

			var charge = widget.GetOrNull<ButtonWidget>("CHARGE");
			if (charge != null)
			{
				charge.IsHighlighted = () => world.OrderGenerator is ChargeOrderGenerator;
				charge.OnClick = () =>
				{
					if (charge.IsHighlighted())
						world.CancelInputMode();
					else
						world.OrderGenerator = new ChargeOrderGenerator(world, regiments);
				};
				charge.OnKeyPress = _ => charge.OnClick();
			}

			var run = widget.GetOrNull<ButtonWidget>("RUN");
			if (run != null)
			{
				run.IsHighlighted = () => world.OrderGenerator is RunOrderGenerator;
				run.OnClick = () =>
				{
					if (run.IsHighlighted())
						world.CancelInputMode();
					else
						world.OrderGenerator = new RunOrderGenerator(world, regiments);
				};
				run.OnKeyPress = _ => run.OnClick();
			}

			var stand = widget.GetOrNull<ButtonWidget>("STAND");
			if (stand != null)
			{
				stand.IsHighlighted = () => regiments.Length > 0 && regiments.All(a => !a.IsDead && a.Trait<RegimentCommands>().IsStanding);
				stand.OnClick = () => IssueToAll(regiments, a => new Order(RegimentCommands.StandOrder, a, false));
				stand.OnKeyPress = _ => stand.OnClick();
			}

			var surrenderPanel = widget.GetOrNull("SURRENDER_COMMANDS");
			if (surrenderPanel != null)
				surrenderPanel.IsVisible = () => { Update(); return surrenderers.Length > 0; };

			var surrender = widget.GetOrNull<ButtonWidget>("SURRENDER");
			if (surrender != null)
				surrender.OnClick = () => IssueToAll(surrenderers, a => new Order(Surrenders.OrderID, a, false));

			BindFireMode(widget, "CANISTER", "canister");
			BindFireMode(widget, "SOLIDSHOT", "solidshot");
			BindFireMode(widget, "SHELL", "shell");
		}

		void BindFireMode(Widget widget, string id, string mode)
		{
			var button = widget.GetOrNull<ButtonWidget>(id);
			if (button == null)
				return;

			button.IsHighlighted = () => batteries.Length > 0 && batteries.All(a => !a.IsDead && a.Trait<FireModes>().CurrentMode == mode);
			button.OnClick = () => IssueToAll(batteries, a => new Order(FireModes.OrderName, a, false) { TargetString = mode });
			button.OnKeyPress = _ => button.OnClick();
		}

		void IssueToAll(Actor[] actors, Func<Actor, Order> makeOrder)
		{
			var orders = actors.Where(a => !a.IsDead && a.IsInWorld).Select(makeOrder).ToArray();
			foreach (var o in orders)
				world.IssueOrder(o);

			orders.PlayVoiceForOrders();
		}

		void Update()
		{
			if (selectionHash == world.Selection.Hash)
				return;

			var mine = world.Selection.Actors.Where(a => a.Owner == world.LocalPlayer && a.IsInWorld && !a.IsDead).ToArray();
			regiments = mine.Where(a => a.Info.HasTraitInfo<RegimentCommandsInfo>()).ToArray();
			batteries = mine.Where(a => a.Info.HasTraitInfo<FireModesInfo>()).ToArray();
			surrenderers = mine.Where(a => a.Info.HasTraitInfo<SurrendersInfo>()).ToArray();
			selectionHash = world.Selection.Hash;
		}
	}
}
