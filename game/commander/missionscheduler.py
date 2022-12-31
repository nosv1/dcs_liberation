from __future__ import annotations

import logging
import random
from collections import defaultdict
from datetime import timedelta
from typing import Iterator, Dict, TYPE_CHECKING

from game.theater import ControlPoint, MissionTarget
from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.ato.starttype import StartType
from game.ato.traveltime import TotEstimator

if TYPE_CHECKING:
    from game.coalition import Coalition


class MissionScheduler:
    def __init__(self, coalition: Coalition, desired_mission_length: timedelta, minimum_carrier_flight_offset: timedelta) -> None:
        self.coalition = coalition
        self.desired_mission_length = desired_mission_length
        self.minimum_carrier_flight_offset = minimum_carrier_flight_offset

    def offset_carrier_flights(self, carrier_flights: dict[ControlPoint, list[Flight]]) -> None:
        for flights in carrier_flights.values():
            flights.sort(key=lambda f: f.flight_plan.startup_time())
            for i, flight in enumerate(flights):
                if not i:
                    continue
                delay: timedelta = flight.flight_plan.startup_time()

                for j, previous_flight in enumerate(flights[:i]):
                    if previous_flight in flight.package.flights:
                        continue
                    previuos_delay: timedelta = previous_flight.flight_plan.startup_time()
                    delta: timedelta = abs(delay - previuos_delay)

                    if delta > self.minimum_carrier_flight_offset:
                        continue

                    adjustment: timedelta = self.minimum_carrier_flight_offset - delta
                    flight.package.time_over_target += adjustment
                    delay += adjustment

    def spawn_late_carrier_flights_in_air(self) -> None:
        # to avoid carrier congestion when the final flights are taking off and the early
        # flights are landing, we check to see if filghts will be taking off by the time
        # other flights are coming to land, simply 'rtb_time = tot - start_time + some_tot_duration + tot' ish

        for package in self.coalition.ato.packages:
            start_type_changed: bool = False
            for flight in package.flights:
                if not flight.from_cp.is_carrier:
                    continue

                start_time: timedelta = flight.flight_plan.startup_time()

                # check if there are flights coming to land by the time you are taking off, if so, spawn in air
                for earlier_package in self.coalition.ato.packages:
                    for earlier_flight in earlier_package.flights:
                        earlier_start_time: timedelta = earlier_flight.flight_plan.startup_time()
                        earlier_tot: timedelta = earlier_flight.flight_plan.tot
                        waypoint_depart_time: timedelta = [earlier_tot] + [
                            earlier_flight.flight_plan.depart_time_for_waypoint(wp)
                            for wp in earlier_flight.flight_plan.waypoints
                            if earlier_flight.flight_plan.depart_time_for_waypoint(wp)
                        ]
                        base_to_target = earlier_tot - earlier_start_time
                        # base_to_target + 'latest' or last wp with a time should be the rtb time, but - offset to be safe
                        earlier_arrival_time: timedelta = (base_to_target + waypoint_depart_time[-1]) - timedelta(minutes=5)

                        if earlier_arrival_time > start_time:
                            continue

                        flight.start_type = StartType.IN_FLIGHT
                        start_type_changed = True
                        logging.info(
                            f"Spawning flight in air... Earlier flight, {earlier_flight.unit_type.name}, is estimated to arrive before {flight.unit_type.name} of {flight.package.primary_task}, w/ TOT of {flight.package.time_over_target} and start time of {flight.flight_plan.startup_time()} is set to take off."
                        )
                        break

                    if start_type_changed:
                        break

    def spawn_large_aircraft_in_air(self) -> None:
        # FIXME: this is a hack to avoid large aircraft from crashing at the end fo the runway
        # The problem is sometimes large aircraft don't have enough runway to make it in the air alive, so we spawn them in the air to avoid this
        # but, this means we can't hit them on the ramp if there's an OCA/Aircraft scheduled... we continue anwyays

        for package in self.coalition.ato.packages:
            for flight in package.flights:
                if flight.unit_type.dcs_unit_type.large_parking_slot:
                    flight.start_type = StartType.IN_FLIGHT
                    logging.info(
                        f"Spawning flight in air... {flight.unit_type.name} of {flight.package.primary_task}, w/ TOT of {flight.package.time_over_target} and start time of {flight.flight_plan.startup_time()}, is large."
                    )

    def schedule_missions(self) -> None:
        """Identifies and plans mission for the turn."""

        def start_time_generator(
            count: int, earliest: int, latest: int, margin: int
        ) -> Iterator[timedelta]:
            interval = (latest - earliest) // count
            for time in range(earliest, latest, interval):
                error = random.randint(-margin, margin)
                yield timedelta(seconds=max(0, time + error))

        dca_types = {
            FlightType.BARCAP,
            FlightType.TARCAP,
        }
        theater_support_types = {
            FlightType.AEWC,
            FlightType.REFUELING,
        }

        previous_cap_end_time: Dict[MissionTarget, timedelta] = defaultdict(timedelta)
        ground_attack_packages = [
            p
            for p in self.coalition.ato.packages
            if p.primary_task not in set(list(dca_types) + list(theater_support_types))
        ]

        start_time = start_time_generator(
            count=len(ground_attack_packages),
            earliest=int(timedelta(minutes=2).total_seconds()),  # earliest >= margin
            latest=int(self.desired_mission_length.total_seconds()),
            margin=int(timedelta(minutes=2).total_seconds()),  # margin <= earliest
        )
        for package in self.coalition.ato.packages:
            tot = TotEstimator(package).earliest_tot()
            package.time_over_target = tot

        self.coalition.ato.packages.sort(key=lambda p: p.time_over_target, reverse=True)

        carrier_flights: dict[ControlPoint, Flight] = {}

        for package in self.coalition.ato.packages:
            if package.primary_task in dca_types:
                previous_end_time = previous_cap_end_time[package.target]
                if package.time_over_target < previous_end_time:
                    # below was used before we were sorting the tots. we were calculating
                    # the tots in the order of the packages being created
                    # if tot > previous_end_time:
                    #     # Can't get there exactly on time, so get there ASAP. This
                    #     # will typically only happen for the first CAP at each
                    #     # target.
                    #     package.time_over_target = tot
                    # else:
                    # end old code
                    package.time_over_target = previous_end_time

                departure_time = package.mission_departure_time
                # Should be impossible for CAPs
                if departure_time is None:
                    logging.error(f"Could not determine mission end time for {package}")
                    continue
                previous_cap_end_time[package.target] = departure_time
            elif package.primary_task in theater_support_types:
                pass
            elif package.auto_asap:
                package.set_tot_asap()
            else:
                # But other packages should be spread out a bit. Note that take
                # times are delayed, but all aircraft will become active at
                # mission start. This makes it more worthwhile to attack enemy
                # airfields to hit grounded aircraft, since they're more likely
                # to be present. Runway and air started aircraft will be
                # delayed until their takeoff time by AirConflictGenerator.
                package.time_over_target += next(start_time)

            for flight in package.flights:
                if not flight.from_cp.is_carrier:
                    continue
                if flight.from_cp not in carrier_flights:
                    carrier_flights[flight.from_cp] = []
                carrier_flights[flight.from_cp].append(flight)

        self.offset_carrier_flights(carrier_flights)
        self.spawn_late_carrier_flights_in_air()
        self.spawn_large_aircraft_in_air()
