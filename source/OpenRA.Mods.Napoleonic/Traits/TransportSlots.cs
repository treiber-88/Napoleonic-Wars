#region Copyright & License Information
/*
 * Napoleonic Wars total conversion for OpenRA.
 * Licensed under the GNU General Public License v3 (see COPYING).
 */
#endregion

using System.Collections.Frozen;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Network;
using OpenRA.Traits;

namespace OpenRA.Mods.Napoleonic.Traits
{
	[Desc("Limits how many passengers of each cargo type a transport carries, e.g. one battery and one regiment.",
		"Enforced by ValidateTransportSlots on the world actor; Cargo.MaxWeight should equal the total number of slots.")]
	public class TransportSlotsInfo : TraitInfo<TransportSlots>, Requires<CargoInfo>
	{
		[Desc("Passenger CargoType -> number of slots. Cargo types that are not listed are not limited.")]
		public readonly FrozenDictionary<string, int> Slots = FrozenDictionary<string, int>.Empty;
	}

	public class TransportSlots { }

	[TraitLocation(SystemActors.World)]
	[Desc("Drops orders to board a transport whose slot for that kind of unit is already taken or spoken for.",
		"Attach this to the world actor.")]
	public class ValidateTransportSlotsInfo : TraitInfo<ValidateTransportSlots> { }

	public class ValidateTransportSlots : IValidateOrder
	{
		// Units on their way to board: unit -> (transport, tick the order was given).
		readonly Dictionary<Actor, (Actor Transport, int Tick)> claims = [];

		static string CargoType(Actor a) => a.Info.TraitInfoOrDefault<PassengerInfo>()?.CargoType;

		public bool OrderValidation(OrderManager orderManager, World world, int clientId, Order order)
		{
			var subject = order.Subject;
			if (subject == null)
				return true;

			if (order.OrderString != "EnterTransport")
			{
				// Any other fresh order means the unit is no longer heading for its transport.
				if (!order.Queued)
					claims.Remove(subject);

				return true;
			}

			if (order.Target.Type != TargetType.Actor)
				return true;

			var transport = order.Target.Actor;
			var slots = transport.Info.TraitInfoOrDefault<TransportSlotsInfo>();
			var type = CargoType(subject);
			var cargo = transport.TraitOrDefault<Cargo>();
			if (slots == null || type == null || cargo == null || !slots.Slots.TryGetValue(type, out var limit))
				return true;

			// A claim lapses when the unit dies, boards, or stops without boarding.
			var now = world.WorldTick;
			foreach (var stale in claims.Where(c => c.Key.IsDead || !c.Key.IsInWorld || (c.Key.IsIdle && now - c.Value.Tick > 5))
				.Select(c => c.Key).ToList())
				claims.Remove(stale);

			var used = cargo.Passengers.Count(p => p != subject && CargoType(p) == type)
				+ claims.Count(c => c.Key != subject && c.Value.Transport == transport && CargoType(c.Key) == type);

			if (used >= limit)
				return false;

			claims[subject] = (transport, now);
			return true;
		}
	}
}
