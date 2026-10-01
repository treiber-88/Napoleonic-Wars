#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using OpenRA.Mods.Napoleonic.Traits;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Scripting
{
	[ScriptPropertyGroup("Regiment")]
	public class RegimentProperties : ScriptActorProperties, Requires<RegimentCommandsInfo>
	{
		readonly IResolveOrder commands;

		public RegimentProperties(ScriptContext context, Actor self)
			: base(context, self)
		{
			commands = self.Trait<RegimentCommands>();
		}

		[Desc("Charge the target with bayonet or sabre.")]
		public void Charge(Actor target)
		{
			commands.ResolveOrder(Self, new Order(RegimentCommands.ChargeOrder, Self, Target.FromActor(target), false));
		}

		[Desc("Run to the cell at the double, out of formation.")]
		public void Run(CPos cell)
		{
			commands.ResolveOrder(Self, new Order(RegimentCommands.RunOrder, Self, Target.FromCell(Self.World, cell), false));
		}

		[Desc("Halt, form up and hold the position.")]
		public void Stand()
		{
			commands.ResolveOrder(Self, new Order(RegimentCommands.StandOrder, Self, false));
		}
	}
}
