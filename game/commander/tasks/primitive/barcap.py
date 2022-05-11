from __future__ import annotations

import logging
import random

from dataclasses import dataclass

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.models.game_stats import GameTurnMetadata
from game.theater import ControlPoint, FrontLine
from gen.flights.flight import FlightType


@dataclass
class PlanBarcap(PackagePlanningTask[ControlPoint]):
    max_orders: int

    def preconditions_met(self, state: TheaterState) -> bool:

        if isinstance(self.target, FrontLine):
            if not state.front_line_tarcaps_needed[self.target]:
                return False
        else:
            if not state.barcaps_needed[self.target]:
                return False

        air_ratio: float = state.get_air_ratio()
        r_air: float = random.random()

        # small air ratio, more willing
        if r_air < air_ratio / 2:
            # logic is air ratio is even at 1.0, so 50% of the barcaps scheduled :sunglasses:
            return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        if self.target in state.vulnerable_front_lines:
            state.front_line_tarcaps_needed[self.target] -= 1
        else:
            state.barcaps_needed[self.target] -= 1

    def propose_flights(self, state: TheaterState) -> None:
        if self.target in state.vulnerable_front_lines:
            self.propose_flight(FlightType.TARCAP, 2)
        else:
            self.propose_flight(FlightType.BARCAP, 2)

    @property
    def purchase_multiplier(self) -> int:
        return self.max_orders
