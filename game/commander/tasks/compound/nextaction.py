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


logger = logging.getLogger()


@dataclass(frozen=True)
class PlanNextAction(CompoundTask[TheaterState]):
    game: Game
    player: bool
    aircraft_cold_start: bool

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        """The logic below suggests defense is priority, then checks whether or not there's an inbalance anywhere, like if lacking ground units, then create ground support missions, or if lacking air units, protect air space."""

        data = self.game.game_stats.data_per_turn[-1]

        # ratio is 1 if player count is 0 else count
        # ratio is player count if no enemy count else player count
        air_ratio = (
            data.allied_units.aircraft_count if data.allied_units.aircraft_count else 1
        )
        if data.enemy_units.aircraft_count:
            air_ratio = (
                data.allied_units.aircraft_count / data.enemy_units.aircraft_count
            )

        ground_ratio = (
            data.allied_units.vehicles_count if data.allied_units.vehicles_count else 1
        )
        if data.enemy_units.vehicles_count:
            ground_ratio = (
                data.allied_units.vehicles_count / data.enemy_units.vehicles_count
            )

        player_money = Income(self.game, player=True).total
        enemy_money = Income(self.game, player=False).total
        money_ratio = player_money if player_money else 1
        if enemy_money:
            money_ratio = player_money / enemy_money

        # if not player, inverse ratios for enemy
        if not self.player:
            air_ratio = 1 / air_ratio
        if not self.player:
            ground_ratio = 1 / ground_ratio

        logger.debug(f"is_player: {self.player}")
        logger.debug(f"air_ratio: {air_ratio}")
        logger.debug(f"ground_ratio: {ground_ratio}")
        logger.debug(f"money_ratio: {money_ratio}")

        # priority 1 - Theater Support
        yield [TheaterSupport()]
        logger.debug("1 - Theater Support")

        # priority 2 - Defend Bases
        defend_bases = False
        attack_garrisons = False

        if ground_ratio < 0.8:  # outnumbered so prioritize weakening enemy front line
            yield [DefendBases()]
            yield [AttackGarrisons()]
            defend_bases = True
            attack_garrisons = True
            logger.debug("2 - defend_bases")

        # priority 3 - Attack Opposer's Infrastructure and Protect Air Space
        protect_air_space = False
        attack_air_infrastructure = False

        if (
            air_ratio < 0.8
        ):  # outnumbered so prioritize air and try to surpress enemy air?
            yield [AttackAirInfrastructure(self.aircraft_cold_start)]  # maybe?
            yield [ProtectAirSpace()]
            protect_air_space = True
            attack_air_infrastructure = True
            logger.debug("3 - attack_air_infrastructure / protect_air_space")

        # priority 4 - Attack Opposer's Building(s)
        attack_buildings = False

        if money_ratio < 0.6:  # strong disadvantage in money, attack buildings
            yield [AttackBuildings()]
            attack_buildings = True
            logger.debug("4 - attack_buildings")

        # priority 5 - Capture Opposer's Base(s)
        capture_base = False

        if ground_ratio > 1.4:  # advantage so prioritize capture base
            yield [CaptureBases()]
            capture_base = True
            logger.debug("5 - capture_base")

        # priority 6 - whatever we haven't done yet, but already checked for
        if not defend_bases:
            yield [DefendBases()]
            logger.debug("6 - defend_bases")

        if not protect_air_space:
            yield [ProtectAirSpace()]
            logger.debug("6 - protect_air_space")

        if not attack_buildings:
            yield [AttackBuildings()]
            logger.debug("6 - attack_buildings")

        if not capture_base:
            yield [CaptureBases()]
            logger.debug("6 - capture_base")

        # priority 7 - the rest
        yield [InterdictReinforcements()]
        logger.debug("7 - interdict_reinforcements")

        yield [DegradeIads()]
        logger.debug("7 - degrade_iads")

        # cheaty tactics, it's too easy to destory ammo or runways, so low priority
        if not attack_garrisons:
            yield [AttackGarrisons()]
            logger.debug("8 - attack_garrisons")

        if not attack_air_infrastructure:
            yield [AttackAirInfrastructure(self.aircraft_cold_start)]
            logger.debug("8 - attack_air_infrastructure")
