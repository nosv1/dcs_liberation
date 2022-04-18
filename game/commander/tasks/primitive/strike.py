from __future__ import annotations

import logging
import random

from dataclasses import dataclass
from typing import Any

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater.theatergroundobject import TheaterGroundObject
from gen.flights.flight import FlightType


@dataclass
class PlanStrike(PackagePlanningTask[TheaterGroundObject[Any]]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.strike_targets:
            return False
        if not self.target_area_preconditions_met(state):
            return False

        air_ratio: float = state.get_ground_ratio()
        r: float = random.random()
        logging.warn(f"Air Ratio: {air_ratio:.2f}, {r:.2f}")

        if r > air_ratio / 2:
            logging.warn(f"Not going for strike")
            return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.strike_targets.remove(self.target)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.STRIKE, 2)
        self.propose_common_escorts()
