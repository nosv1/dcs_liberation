from __future__ import annotations

from dataclasses import dataclass
from random import random

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater.theatergroundobject import VehicleGroupGroundObject
from game.ato.flighttype import FlightType


@dataclass
class PlanBai(PackagePlanningTask[VehicleGroupGroundObject]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if not state.has_battle_position(self.target):
            return False
        if not self.target_area_preconditions_met(state):
            return False

        air_dominance: float = state.get_air_dominance()
        r_air: float = random()

        # larger air dominance, more willing
        if r_air > air_dominance:
            return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.eliminate_battle_position(self.target)

    def propose_flights(self, state: TheaterState) -> None:
        self.propose_flight(FlightType.BAI, 2)
        self.propose_common_escorts()
