import logging
from collections import Iterator
from dataclasses import dataclass

from game.commander.tasks.compound.attackairinfrastructure import (
    AttackAirInfrastructure,
)
from game.commander.tasks.compound.attackbuildings import AttackBuildings
from game.commander.tasks.compound.attackgarrisons import AttackGarrisons
from game.commander.tasks.compound.capturebases import CaptureBases
from game.commander.tasks.compound.defendbases import DefendBases
from game.commander.tasks.compound.degradeiads import DegradeIads
from game.commander.tasks.compound.interdictreinforcements import (
    InterdictReinforcements,
)
from game.commander.tasks.compound.protectairspace import ProtectAirSpace
from game.commander.tasks.compound.theatersupport import TheaterSupport
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method
from game.income import Income

# FIXME: This is a hack for the dataclass to get around the fact that couldn't figure out how to import Game
class Game:
    pass


@dataclass(frozen=True)
class PlanNextAction(CompoundTask[TheaterState]):
    game: Game
    player: bool
    aircraft_cold_start: bool

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        yield [TheaterSupport()]
        yield [DefendBases()]
        yield [InterdictReinforcements()]
        yield [ProtectAirSpace()]
        yield [DegradeIads()]
        yield [AttackBuildings()]
        yield [CaptureBases()]
        yield [AttackGarrisons()]
        yield [AttackAirInfrastructure(self.aircraft_cold_start)]
