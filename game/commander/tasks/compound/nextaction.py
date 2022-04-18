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
        """The logic below suggests defense is priority, then checks whether or not there's an inbalance anywhere, like if lacking ground units, then create ground support missions, or if lacking air units, protect air space."""

        # data = self.game.game_stats.data_per_turn[-1]

        # air_ratio = (1 + data.allied_units.aircraft_count) / (
        #     1 + data.enemy_units.aircraft_count
        # )

        # ground_ratio = (1 + data.allied_units.vehicles_count) / (
        #     1 + data.enemy_units.vehicles_count
        # )

        # player_money = Income(self.game, player=True).total
        # enemy_money = Income(self.game, player=False).total
        # money_ratio = (1 + player_money) / (1 + enemy_money)

        # # if not player, inverse ratios for enemy
        # if not self.player:
        #     air_ratio = 1 / air_ratio
        # if not self.player:
        #     ground_ratio = 1 / ground_ratio

        # # logging.debug(f"is_player: {self.player}")
        # # logging.debug(f"air_ratio: {air_ratio}")
        # # logging.debug(f"ground_ratio: {ground_ratio}")
        # # logging.debug(f"money_ratio: {money_ratio}")

        # # priority 1 - Theater Support
        # yield [TheaterSupport()]
        # logging.debug("1 - Theater Support")

        # # priority 2 - Defend Bases
        # defend_bases = False
        # capture_bases = False
        # interdict_reinforcements = False

        # if ground_ratio < 0.8:  # outnumbered so prioritize weakening enemy front line
        #     yield [DefendBases()]
        #     yield [InterdictReinforcements()]
        #     yield [CaptureBases()]
        #     defend_bases = True
        #     capture_bases = True
        #     interdict_reinforcements = True
        #     logging.debug("2 - defend_bases / capture_bases / interdict_reinforcements")

        # # priority 3 - Attack Opposer's Infrastructure and Protect Air Space
        # protect_air_space = False
        # attack_air_infrastructure = False

        # if (
        #     air_ratio < 0.8
        # ):  # outnumbered so prioritize air and try to surpress enemy air?
        #     yield [AttackAirInfrastructure(self.aircraft_cold_start)]  # maybe?
        #     yield [ProtectAirSpace()]
        #     protect_air_space = True
        #     attack_air_infrastructure = True
        #     logging.debug("3 - attack_air_infrastructure / protect_air_space")

        # # priority 4 - Attack Opposer's Building(s)
        # attack_buildings = False

        # if money_ratio < 0.6:  # strong disadvantage in money, attack buildings
        #     yield [AttackBuildings()]
        #     attack_buildings = True
        #     logging.debug("4 - attack_buildings")

        # # priority 5 - Capture Opposer's Base(s)
        # capture_bases = False
        # attack_garrisons = False

        # if ground_ratio > 1.4:  # advantage so prioritize capture base
        #     yield [CaptureBases()]
        #     yield [AttackGarrisons()]
        #     capture_bases = True
        #     logging.debug("5 - capture_bases")

        # # priority 6 - whatever we haven't done yet, but already checked for
        # if not defend_bases:
        #     yield [DefendBases()]
        #     logging.debug("6 - defend_bases")

        # if not interdict_reinforcements:
        #     yield [InterdictReinforcements()]
        #     logging.debug("6 - interdict_reinforcements")

        # if not protect_air_space:
        #     yield [ProtectAirSpace()]
        #     logging.debug("6 - protect_air_space")

        # # priority 7
        # yield [DegradeIads()]
        # logging.debug("7 - degrade_iads")

        # if not attack_buildings:
        #     yield [AttackBuildings()]
        #     logging.debug("6 - attack_buildings")

        # if not capture_bases:
        #     yield [CaptureBases()]
        #     logging.debug("6 - capture_bases")

        # if not attack_garrisons:
        #     yield [AttackGarrisons()]
        #     logging.debug("6 - attack_garrisons")

        # # cheaty tactics
        # if not attack_air_infrastructure:
        #     yield [AttackAirInfrastructure(self.aircraft_cold_start)]
        #     logging.debug("8 - attack_air_infrastructure")

        yield [TheaterSupport()]
        yield [DefendBases()]
        yield [InterdictReinforcements()]
        yield [ProtectAirSpace()]
        yield [DegradeIads()]
        yield [AttackBuildings()]
        yield [CaptureBases()]
        yield [AttackGarrisons()]
        yield [AttackAirInfrastructure(self.aircraft_cold_start)]
