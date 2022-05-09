from __future__ import annotations

import logging
import random

from dataclasses import dataclass

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater.theatergroundobject import VehicleGroupGroundObject
from gen.flights.flight import FlightType


@dataclass
class PlanBai(PackagePlanningTask[VehicleGroupGroundObject]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if not state.has_garrison(self.target):
            return False
        if not self.target_area_preconditions_met(state):
            return False

        air_ratio: float = state.get_air_ratio()
        r_air: float = random.random()
        logging.warn(f"Air Ratio: {air_ratio:.2f}, {r_air:.2f}")

        # large air ratio, more willing
        if r_air > air_ratio / 2:
            logging.warn(f"Not going for BAI")
            return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.eliminate_garrison(self.target)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.BAI, 2)
        self.propose_common_escorts()
