from __future__ import annotations

import random

from dataclasses import dataclass

from game.commander.tasks.packageplanningtask import PackagePlanningTask, EscortType
from game.commander.theaterstate import TheaterState
from game.theater import FrontLine
from game.theater.controlpoint import ControlPoint
from gen.flights.flight import FlightType


@dataclass
class PlanCas(PackagePlanningTask[FrontLine]):
    max_orders: int = 1

    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.vulnerable_front_lines:
            return False

        # Do not bother planning CAS when there are no enemy ground units at the front.
        # An exception is made for turn zero since that's not being truly planned, but
        # just to determine what missions should be planned on turn 1 (when there *will*
        # be ground units) and what aircraft should be ordered.
        enemy_cp: ControlPoint = self.target.control_point_friendly_to(
            player=not state.context.coalition.player
        )
        friendly_cp: ControlPoint = self.target.control_point_friendly_to(
            player=state.context.coalition.player
        )

        if enemy_cp.deployable_front_line_units == 0 and state.context.turn > 0:
            return False

        ground_ratio: float = state.get_ground_ratio()
        air_ratio: float = state.get_air_ratio()
        r_air: float = random.random()
        r_ground: float = random.random()

        # large air ratio, more willing
        if r_air > air_ratio / 2:
            # offensive front line and large ground ratio, more willing
            if self.is_friendly_cp_offensive(state):
                if r_ground > ground_ratio / 2:
                    return False
            # defensive front line and small ground ratio, more willing
            else:
                if r_ground < ground_ratio / 2:
                    return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        # state.vulnerable_front_lines.remove(self.target)
        state.front_line_cas_needed[self.target] -= 1

    def propose_flights(self, state: TheaterState) -> None:
        self.propose_flight(FlightType.CAS, 2)
        self.propose_flight(FlightType.SEAD_ESCORT, 2, EscortType.Sead)
        self.propose_flight(FlightType.TARCAP, 2)

    def is_friendly_cp_offensive(self, state: TheaterState) -> float:
        friendly_cp: ControlPoint = self.target.control_point_friendly_to(
            player=state.context.coalition.player
        )
        for front_line, stance in state.front_line_stances.items():
            if stance:
                if friendly_cp.name in front_line.name:
                    return stance.name in [
                        "BREAKTHROUGH",
                        "ELIMINATION",
                        "AMBUSH",
                    ]

    @property
    def purchase_multiplier(self) -> int:
        return self.max_orders
