#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Immutable;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Lets the player choose the ammunition a battery fires. Each mode grants its own condition,",
		"which should enable the matching armament (canister, solid shot, shell).")]
	public class FireModesInfo : TraitInfo
	{
		[FieldLoader.Require]
		[GrantedConditionReference]
		[Desc("Conditions granted by each mode, in button order.")]
		public readonly ImmutableArray<string> Modes = default;

		[Desc("Index of the mode selected when the unit is created.")]
		public readonly int DefaultMode = 0;

		public override object Create(ActorInitializer init) { return new FireModes(this); }
	}

	public class FireModes : INotifyCreated, IResolveOrder
	{
		public const string OrderName = "NWFireMode";

		readonly FireModesInfo info;
		int token = Actor.InvalidConditionToken;

		public FireModes(FireModesInfo info) { this.info = info; }

		public string CurrentMode { get; private set; }

		void INotifyCreated.Created(Actor self)
		{
			SetMode(self, info.Modes[info.DefaultMode]);
		}

		public bool HasMode(string mode) => info.Modes.Contains(mode);

		void SetMode(Actor self, string mode)
		{
			if (mode == CurrentMode || !HasMode(mode))
				return;

			if (token != Actor.InvalidConditionToken)
				token = self.RevokeCondition(token);

			CurrentMode = mode;
			token = self.GrantCondition(mode);
		}

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString == OrderName)
				SetMode(self, order.TargetString);
		}
	}
}
