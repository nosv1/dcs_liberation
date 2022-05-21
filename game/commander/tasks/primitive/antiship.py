from __future__ import annotations

import random

from dataclasses import dataclass

from game.commander.missionproposals import EscortType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater.theatergroundobject import NavalGroundObject
from gen.flights.flight import FlightType


@dataclass
class PlanAntiShip(PackagePlanningTask[NavalGroundObject]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.threatening_air_defenses:
            return False
        if not self.target_area_preconditions_met(state, ignore_iads=True):
            return False

        air_ratio: float = state.get_air_ratio()
        r_air: float = random.random()

        # larger air ratio, more willing
        if r_air > air_ratio:
            return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.eliminate_ship(self.target)

    def propose_flights(self, state: TheaterState) -> None:
        self.propose_flight(FlightType.ANTISHIP, 4)
        self.propose_flight(FlightType.ESCORT, 2, EscortType.AirToAir)
