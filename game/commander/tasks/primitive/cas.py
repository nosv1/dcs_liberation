from __future__ import annotations

import logging
import random

from dataclasses import dataclass

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import FrontLine
from game.theater.controlpoint import ControlPoint
from gen.flights.flighttype import FlightType


@dataclass
class PlanCas(PackagePlanningTask[FrontLine]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.vulnerable_front_lines:
            return False

        # Do not bother planning CAS when there are no enemy ground units at the front.
        # An exception is made for turn zero since that's not being truly planned, but
        # just to determine what missions should be planned on turn 1 (when there *will*
        # be ground units) and what aircraft should be ordered.
        enemy_cp = self.target.control_point_friendly_to(
            player=not state.context.coalition.player
        )
        friendly_cp = self.target.control_point_friendly_to(
            player=state.context.coalition.player
        )

        if enemy_cp.deployable_front_line_units == 0 and state.context.turn > 0:
            return False

        ground_ratio: float = state.get_ground_ratio()
        r: float = random.random()

        logging.warn(f"Enemy CP: {enemy_cp.name}")
        logging.warn(f"Friendly CP: {friendly_cp.name}")
        logging.warn(
            f"Active Front Lines: {[(fl[0].name, fl[1].name) for fl in state.front_line_stances.items() if None not in fl]}"
        )
        logging.warn(f"Ground Ratio: {ground_ratio:.2f}, RND {r:.2f}")

        if self.is_friendly_cp_offensive(state):
            if r > ground_ratio / 2:
                logging.warn(f"CAS not supporting offense")
                return False
        else:
            if r < ground_ratio / 2:
                logging.warn(f"CAS not supporting defense")
                return False

        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.vulnerable_front_lines.remove(self.target)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.CAS, 2)
        self.propose_flight(FlightType.SEAD, 2)
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
