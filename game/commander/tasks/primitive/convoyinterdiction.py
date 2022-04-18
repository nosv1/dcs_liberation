from __future__ import annotations

import random
import logging

from dataclasses import dataclass

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.data.doctrine import Doctrine
from game.transfers import Convoy
from gen.flights.flight import FlightType


@dataclass
class PlanConvoyInterdiction(PackagePlanningTask[Convoy]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.enemy_convoys:
            return False
        if not self.target_area_preconditions_met(state):
            return False

        ground_ratio: float = state.get_ground_ratio()
        r: float = random.random()
        logging.warn(f"Ground Ratio: {ground_ratio:.2f}, {r:.2f}")

        if r < ground_ratio / 2:
            logging.warn(f"Not going for convoy")
            return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.enemy_convoys.remove(self.target)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.BAI, 2)
        self.propose_common_escorts()
