import copy

from dcs import Point
from dcs.planes import B_17G, B_52H, Tu_22M3
from dcs.point import MovingPoint
from dcs.task import Bombing, Expend, OptFormation, WeaponType
from game.ato.flightplans.strike import StrikeFlightPlan
from game.ato.flightwaypoint import FlightWaypoint
from game.theater.theatergroup import TheaterUnit

from .pydcswaypointbuilder import PydcsWaypointBuilder


class StrikeIngressBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        if self.group.units[0].unit_type in [B_17G, B_52H, Tu_22M3]:
            self.add_bombing_tasks(waypoint)
        else:
            self.add_strike_tasks(waypoint)

        waypoint.tasks.append(OptFormation.trail_open())

    def add_bombing_tasks(self, waypoint: MovingPoint) -> None:
        targets = self.waypoint.targets
        if not targets:
            return

        center: Point = copy.copy(targets[0].position)
        for target in targets[1:]:
            center += target.position
        center /= len(targets)
        bombing = Bombing(
            center, weapon_type=WeaponType.Bombs, expend=Expend.All, group_attack=True
        )
        waypoint.tasks.append(bombing)

    def add_strike_tasks(self, waypoint: MovingPoint) -> None:
        # The code below shifts the targets for the strike waypoint to prevent later strike flights from attacking the same targets.
        strike_flights_ahead: int = 0
        total_strike_flights: int = 0
        targets = [t for t in self.waypoint.targets]

        if isinstance(self.flight.flight_plan, StrikeFlightPlan):
            for flight in self.package.flights:
                if not isinstance(flight.flight_plan, StrikeFlightPlan):
                    continue
                # found a flight that is a strike flight

                for fp_waypoint in flight.flight_plan.waypoints:
                    if not len(fp_waypoint.targets) > 0:
                        continue
                    # found waypoint with targets

                    if not (
                        [(t.x, t.y) for t in fp_waypoint.targets]
                        == [(t.x, t.y) for t in self.waypoint.targets]
                    ):
                        continue
                    # found waypoint with same targets

                    total_strike_flights += 1
                    if flight == self.flight:
                        break  # this assumes the flights are in order
                    strike_flights_ahead += 1

            # shift amount example:
            # 2 total strike flights, 1 strike flight ahead, 8 targets
            # shift amount = targets / total strike flights = 8 / 2 = 4
            # start index = strike flights ahead * shift amount = 1 * 4 = 4
            # we wrap to the beginning of the list if we go past the end
            shift_amount: int = int(len(targets) / total_strike_flights)
            if strike_flights_ahead > 0:
                i: int = strike_flights_ahead * shift_amount
                new_targets: list[TheaterUnit] = []
                while len(new_targets) < len(targets):
                    new_targets.append(targets[i])
                    i += 1
                    if i >= len(targets):
                        i = 0
                targets = new_targets

        for target in targets:
            bombing = Bombing(
                target.position, weapon_type=WeaponType.Auto, group_attack=True
            )
            # If there is only one target, drop all ordnance in one pass.
            if len(self.waypoint.targets) == 1:
                bombing.params["expend"] = Expend.All.value
            waypoint.tasks.append(bombing)

            # Register special waypoints
            self.register_special_waypoints(self.waypoint.targets)
