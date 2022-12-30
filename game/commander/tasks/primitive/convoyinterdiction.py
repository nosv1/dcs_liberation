from __future__ import annotations

from dataclasses import dataclass
from random import random

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.data.doctrine import Doctrine
from game.transfers import Convoy
from game.ato.flighttype import FlightType


@dataclass
class PlanConvoyInterdiction(PackagePlanningTask[Convoy]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.enemy_convoys:
            return False
        if not self.target_area_preconditions_met(state):
            return False

        ground_dominance: float = state.get_ground_dominance()
        air_dominance: float = state.get_air_dominance()
        r_ground: float = random()
        r_air: float = random()

        # large air dominance, more willing
        # small ground dominance, more willing
        if r_air > air_dominance and r_ground < ground_dominance:
            return False
        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.enemy_convoys.remove(self.target)

    def propose_flights(self, state: TheaterState) -> None:
        self.propose_flight(FlightType.BAI, 2)
        self.propose_common_escorts()
