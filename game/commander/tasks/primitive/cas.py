from __future__ import annotations

from dataclasses import dataclass
from random import random

from game.commander.tasks.packageplanningtask import PackagePlanningTask, EscortType
from game.commander.theaterstate import TheaterState
from game.theater import FrontLine
from game.theater.controlpoint import ControlPoint
from game.ato.flighttype import FlightType


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

        # I (Mo v0) disagree, CAS is still useful for softening up front line for future turns
        enemy_cp: ControlPoint = self.target.control_point_friendly_to(
            player=not state.context.coalition.player
        )
        friendly_cp: ControlPoint = self.target.control_point_friendly_to(
            player=state.context.coalition.player
        )
        # if enemy_cp.deployable_front_line_units == 0 and state.context.turn > 0:
        #     return False

        ground_dominance: float = state.get_ground_dominance()
        air_dominance: float = state.get_air_dominance()
        r_air: float = random()
        r_ground: float = random()

        # large air dominance, more willing
        if r_air > air_dominance:
            # offensive front line and large ground dominance, more willing
            if self.is_friendly_cp_offensive(friendly_cp, state):
                if r_ground > ground_dominance:
                    return False
            # defensive front line and small ground dominance, more willing
            elif r_ground < ground_dominance:
                return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.front_line_cas_needed[self.target] -= 1

    def propose_flights(self, state: TheaterState) -> None:
        self.propose_flight(FlightType.CAS, 2)
        self.propose_flight(FlightType.SEAD_ESCORT, 2, escort_type=EscortType.Sead)
        self.propose_flight(FlightType.TARCAP, 2)

    def is_friendly_cp_offensive(
        self, friendly_cp: ControlPoint, state: TheaterState
    ) -> float:
        for front_line, stance in state.front_line_stances.items():
            if not stance:
                continue
            if friendly_cp.name not in front_line.name:
                continue
            return stance.name in ["BREAKTHROUGH", "ELIMINATION", "AMBUSH"]

    @property
    def purchase_multiplier(self) -> int:
        return self.max_orders
