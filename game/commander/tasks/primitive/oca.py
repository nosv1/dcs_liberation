from __future__ import annotations

import logging
import random

from dataclasses import dataclass

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import ControlPoint
from gen.flights.flight import FlightType


@dataclass
class PlanOcaStrike(PackagePlanningTask[ControlPoint]):
    aircraft_cold_start: bool

    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.oca_targets:
            return False
        if not self.target_area_preconditions_met(state):
            return False

        air_ratio: float = state.get_ground_ratio()
        r: float = random.random()

        if r < air_ratio / 2:
            logging.warn(f"Not going for BAI")
            return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.oca_targets.remove(self.target)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.OCA_RUNWAY, 2)
        if self.aircraft_cold_start:
            self.propose_flight(FlightType.OCA_AIRCRAFT, 2)
        self.propose_common_escorts()
