from __future__ import annotations

import random

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
        air_ratio: float = state.get_air_ratio()
        r_ground: float = random.random()
        r_air: float = random.random()

        # large air ratio, more willing
        if r_air > air_ratio / 2:
            # small ground ratio, more willing
            if r_ground < ground_ratio / 2:
                return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.enemy_convoys.remove(self.target)

    def propose_flights(self, state: TheaterState) -> None:
        self.propose_flight(FlightType.BAI, 2)
        self.propose_common_escorts()
