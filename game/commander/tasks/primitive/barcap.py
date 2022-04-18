from __future__ import annotations

import logging
import random

from dataclasses import dataclass

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.models.game_stats import GameTurnMetadata
from game.theater import ControlPoint
from gen.flights.flight import FlightType


@dataclass
class PlanBarcap(PackagePlanningTask[ControlPoint]):
    max_orders: int

    def preconditions_met(self, state: TheaterState) -> bool:

        if not state.barcaps_needed[self.target]:
            return False

        air_ratio: float = state.get_air_ratio()
        r: float = random.random()
        logging.warn(f"Air Ratio: {air_ratio:.2f}, RND {r:.2f}")

        if r < air_ratio / 2:
            logging.warn(f"Not providing barcap")
            # logic is air ratio is even at 1.0, so 50% of the barcaps scheduled :sunglasses:
            return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.barcaps_needed[self.target] -= 1

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.BARCAP, 2)

    @property
    def purchase_multiplier(self) -> int:
        return self.max_orders
