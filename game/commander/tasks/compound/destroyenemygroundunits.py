from collections import Iterator
from dataclasses import dataclass

from game.commander.tasks.primitive.aggressiveattack import AggressiveAttack
from game.commander.tasks.primitive.barcap import PlanBarcap
from game.commander.tasks.primitive.cas import PlanCas
from game.commander.tasks.primitive.eliminationattack import EliminationAttack
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method
from game.theater import FrontLine


@dataclass(frozen=True)
class DestroyEnemyGroundUnits(CompoundTask[TheaterState]):
    front_line: FrontLine

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        yield [EliminationAttack(self.front_line, state.context.coalition.player)]
        yield [AggressiveAttack(self.front_line, state.context.coalition.player)]
        for front_line, needed in state.front_line_cas_needed.items():
            if needed > 0:
                yield [PlanCas(front_line, needed)]
        for front_line, needed in state.front_line_tarcaps_needed.items():
            if needed > 0:
                yield [PlanBarcap(front_line, needed)]
