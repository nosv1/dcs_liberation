from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Any, Optional
from datetime import timedelta

from dcs import Point
from faker import Faker

from game.campaignloader import CampaignAirWingConfig
from game.campaignloader.defaultsquadronassigner import DefaultSquadronAssigner
from game.commander import TheaterCommander
from game.commander.missionscheduler import MissionScheduler
from game.income import Income
from game.navmesh import NavMesh
from game.orderedset import OrderedSet
from game.profiling import logged_duration, MultiEventTracer
from game.squadrons import AirWing
from game.theater import ControlPoint
from game.threatzones import ThreatZones
from game.transfers import PendingTransfers

if TYPE_CHECKING:
    from game import Game
from game.data.doctrine import Doctrine
from game.factions.faction import Faction
from game.procurement import AircraftProcurementRequest, ProcurementAi
from game.theater.bullseye import Bullseye
from game.theater.transitnetwork import TransitNetwork, TransitNetworkBuilder
from gen.ato import AirTaskingOrder
from gen.flights.traveltime import TotEstimator
from gen.flights.flight import Flight, FlightType, FlightWaypointType
from gen.flights.flightplan import FlightPlanBuilder


class Coalition:
    def __init__(
        self, game: Game, faction: Faction, budget: float, player: bool
    ) -> None:
        self.game = game
        self.player = player
        self.faction = faction
        self.budget = budget
        self.ato = AirTaskingOrder()
        self.transit_network = TransitNetwork()
        self.procurement_requests: OrderedSet[AircraftProcurementRequest] = OrderedSet()
        self.bullseye = Bullseye(Point(0, 0))
        self.faker = Faker(self.faction.locales)
        self.air_wing = AirWing(player, game, self.faction)
        self.transfers = PendingTransfers(game, player)

        # Late initialized because the two coalitions in the game are mutually
        # dependent, so must be both constructed before this property can be set.
        self._opponent: Optional[Coalition] = None

        # Volatile properties that are not persisted to the save file since they can be
        # recomputed on load. Keeping this data out of the save file makes save compat
        # breaks less frequent. Each of these properties has a non-underscore-prefixed
        # @property that should be used for non-Optional access.
        #
        # All of these are late-initialized (whether via on_load or called later), but
        # will be non-None after the game has finished loading.
        self._threat_zone: Optional[ThreatZones] = None
        self._navmesh: Optional[NavMesh] = None
        self.on_load()

    @property
    def doctrine(self) -> Doctrine:
        return self.faction.doctrine

    @property
    def coalition_id(self) -> int:
        if self.player:
            return 2
        return 1

    @property
    def country_name(self) -> str:
        return self.faction.country

    @property
    def opponent(self) -> Coalition:
        assert self._opponent is not None
        return self._opponent

    @property
    def threat_zone(self) -> ThreatZones:
        assert self._threat_zone is not None
        return self._threat_zone

    @property
    def nav_mesh(self) -> NavMesh:
        assert self._navmesh is not None
        return self._navmesh

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        # Avoid persisting any volatile types that can be deterministically
        # recomputed on load for the sake of save compatibility.
        del state["_threat_zone"]
        del state["_navmesh"]
        del state["faker"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        # Regenerate any state that was not persisted.
        self.on_load()

    def on_load(self) -> None:
        self.faker = Faker(self.faction.locales)

    def set_opponent(self, opponent: Coalition) -> None:
        if self._opponent is not None:
            raise RuntimeError("Double-initialization of Coalition.opponent")
        self._opponent = opponent

    def configure_default_air_wing(
        self, air_wing_config: CampaignAirWingConfig
    ) -> None:
        DefaultSquadronAssigner(air_wing_config, self.game, self).assign()

    def adjust_budget(self, amount: float) -> None:
        self.budget += amount

    def compute_threat_zones(self) -> None:
        self._threat_zone = ThreatZones.for_faction(self.game, self.player)

    def compute_nav_meshes(self) -> None:
        self._navmesh = NavMesh.from_threat_zones(
            self.opponent.threat_zone, self.game.theater
        )

    def update_transit_network(self) -> None:
        self.transit_network = TransitNetworkBuilder(
            self.game.theater, self.player
        ).build()

    def set_bullseye(self, bullseye: Bullseye) -> None:
        self.bullseye = bullseye

    def end_turn(self) -> None:
        """Processes coalition-specific turn finalization.

        For more information on turn finalization in general, see the documentation for
        `Game.finish_turn`.
        """
        self.air_wing.end_turn()
        self.budget += Income(self.game, self.player).total

        # Need to recompute before transfers and deliveries to account for captures.
        # This happens in in initialize_turn as well, because cheating doesn't advance a
        # turn but can capture bases so we need to recompute there as well.
        self.update_transit_network()

        # Must happen *before* unit deliveries are handled, or else new units will spawn
        # one hop ahead. ControlPoint.process_turn handles unit deliveries. The
        # coalition-specific turn-end happens before the theater-wide turn-end, so this
        # is handled correctly.
        self.transfers.perform_transfers()

    def preinit_turn_0(self) -> None:
        """Runs final Coalition initialization.

        Final initialization occurs before Game.initialize_turn runs for turn 0.
        """
        self.air_wing.populate_for_turn_0()

    def initialize_turn(self) -> None:
        """Processes coalition-specific turn initialization.

        For more information on turn initialization in general, see the documentation
        for `Game.initialize_turn`.
        """
        # Needs to happen *before* planning transfers so we don't cancel them.
        self.ato.clear()
        self.air_wing.reset()
        self.refund_outstanding_orders()
        self.procurement_requests.clear()

        with logged_duration("Transit network identification"):
            self.update_transit_network()
        with logged_duration("Procurement of airlift assets"):
            self.transfers.order_airlift_assets()
        with logged_duration("Transport planning"):
            self.transfers.plan_transports()

        self.plan_missions()
        self.plan_procurement()

    def refund_outstanding_orders(self) -> None:
        # TODO: Split orders between air and ground units.
        # This isn't quite right. If the player has ground purchases automated we should
        # be refunding the ground units, and if they have air automated but not ground
        # we should be refunding air units.
        if self.player and not self.game.settings.automate_aircraft_reinforcements:
            return

        for cp in self.game.theater.control_points_for(self.player):
            cp.ground_unit_orders.refund_all(self)
        for squadron in self.air_wing.iter_squadrons():
            squadron.refund_orders()

    def plan_missions(self) -> None:
        color = "Blue" if self.player else "Red"
        with MultiEventTracer() as tracer:
            with tracer.trace(f"{color} mission planning"):
                with tracer.trace(f"{color} mission identification"):
                    TheaterCommander(self.game, self.player).plan_missions(tracer)
                with tracer.trace(f"{color} mission scheduling"):
                    MissionScheduler(
                        self, self.game.settings.desired_player_mission_duration
                    ).schedule_missions()
        self.offset_carrier_departure_times()
        self.adjust_carrier_flight_spawns_based_on_rtb_times()

    def offset_carrier_departure_times(
        self, offset: timedelta = timedelta(minutes=2)
    ) -> None:
        # to avoid carrier congestion, we offset the departure times by a given offset,
        # this does not account multiple flights in a package taking off at the same cp

        cps: dict[ControlPoint, list[Flight]] = {}
        for package in self.ato.packages:
            for flight in package.flights:
                if not flight.from_cp.is_carrier:
                    continue
                if flight.from_cp not in cps:
                    cps[flight.from_cp] = []
                cps[flight.from_cp].append(flight)

        for flights in cps.values():
            flights.sort(key=lambda f: TotEstimator(f.package).mission_start_time(f))
            for i, flight in enumerate(flights):
                if not i:
                    continue
                esitmator: TotEstimator = TotEstimator(flight.package)
                delay = esitmator.mission_start_time(flight)

                for j, previous_flight in enumerate(flights[:i]):
                    if previous_flight in flight.package.flights:
                        continue

                    previouis_esitmator: TotEstimator = TotEstimator(
                        previous_flight.package
                    )
                    previous_delay = previouis_esitmator.mission_start_time(
                        previous_flight
                    )
                    delta: timedelta = abs(delay - previous_delay)

                    if delta > offset:
                        continue

                    adjustment: timedelta = offset - delta
                    flight.package.time_over_target += adjustment
                    delay += adjustment

    def adjust_carrier_flight_spawns_based_on_rtb_times(self) -> None:
        # to avoid carrier congestion when the final flights are taking off and the early
        # flights are landing, we check to see if filghts will be taking off by the time
        # ofther flights are coming to land, simply 'rtb_time = tot - start_time + some_tot_duration + tot' ish

        for package in self.ato.packages:
            for flight in package.flights:
                if not flight.from_cp.is_carrier:
                    continue

                esitmator: TotEstimator = TotEstimator(flight.package)
                start_time: timedelta = esitmator.mission_start_time(flight)

                # check if there are flights coming to land by the time you are taking off, if so, spawn in air
                for earlier_package in self.ato.packages:

                    start_type_changed: bool = False
                    for earlier_flight in earlier_package.flights:
                        if not earlier_flight.from_cp.is_carrier:
                            continue

                        earlier_estimator: TotEstimator = TotEstimator(earlier_package)
                        earlier_start_time: timedelta = (
                            earlier_estimator.mission_start_time(earlier_flight)
                        )
                        tot: timedelta = earlier_flight.flight_plan.tot
                        latest_depart_time: timedelta = max(
                            [
                                earlier_flight.flight_plan.depart_time_for_waypoint(wp)
                                for wp in earlier_flight.flight_plan.waypoints
                                if earlier_flight.flight_plan.depart_time_for_waypoint(
                                    wp
                                )
                            ]
                            + [tot]
                        )
                        base_to_target = tot - earlier_start_time
                        earlier_arrival_time: timedelta = (
                            base_to_target + latest_depart_time
                        )

                        if earlier_arrival_time > start_time:
                            continue

                        flight.start_type = "In Flight"
                        start_type_changed = True
                        logging.debug(
                            f"Adjusting flight {flight.unit_type.name} of {flight.package.primary_task} w/ TOT of {flight.package.time_over_target} to start in air."
                        )
                        break

                    if start_type_changed:
                        break

    def plan_procurement(self) -> None:
        # The first turn needs to buy a *lot* of aircraft to fill CAPs, so it gets much
        # more of the budget that turn. Otherwise budget (after repairs) is split evenly
        # between air and ground. For the default starting budget of 2000 this gives 600
        # to ground forces and 1400 to aircraft. After that the budget will be spent
        # proportionally based on how much is already invested.

        if self.player:
            manage_runways = self.game.settings.automate_runway_repair
            manage_front_line = self.game.settings.automate_front_line_reinforcements
            manage_aircraft = self.game.settings.automate_aircraft_reinforcements
        else:
            manage_runways = True
            manage_front_line = True
            manage_aircraft = True

        self.budget = ProcurementAi(
            self.game,
            self.player,
            self.faction,
            manage_runways,
            manage_front_line,
            manage_aircraft,
        ).spend_budget(self.budget)

    def add_procurement_request(self, request: AircraftProcurementRequest) -> None:
        self.procurement_requests.add(request)
