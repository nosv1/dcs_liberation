from __future__ import annotations

from dataclasses import dataclass
from random import random

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater.theatergroundobject import TheaterGroundObject
from game.ato.flighttype import FlightType


@dataclass
class PlanStrike(PackagePlanningTask[TheaterGroundObject]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.strike_targets:
            return False
        if not self.target_area_preconditions_met(state):
            return False

        target_priority: float = 1 - (
            state.strike_targets.index(self.target) / len(state.strike_targets)
        )
        air_dominance: float = state.get_air_dominance()
        r_air: float = random()

        # large air dominance or high target priority (closer), more willing
        if r_air > air_dominance * target_priority:
            return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.strike_targets.remove(self.target)

    def propose_flights(self, state: TheaterState) -> None:
        self.propose_flight(FlightType.STRIKE, 1)
        self.propose_flight(FlightType.STRIKE, 1)
        self.propose_common_escorts()
