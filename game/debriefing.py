from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Type, TYPE_CHECKING

from dcs.unittype import FlyingType, UnitType

from game import db
from game.theater import Airfield, ControlPoint, TheaterGroundObject
from game.unitmap import UnitMap
from gen.flights.flight import Flight

if TYPE_CHECKING:
    from game import Game

DEBRIEFING_LOG_EXTENSION = "log"


@dataclass(frozen=True)
class DebriefingDeadUnitInfo:
    player_unit: bool
    type: Type[UnitType]


@dataclass(frozen=True)
class DebriefingDeadAircraftInfo:
    #: The Flight that resulted in the generated unit.
    flight: Flight

    @property
    def player_unit(self) -> bool:
        return self.flight.departure.captured


@dataclass(frozen=True)
class DebriefingDeadFrontLineUnitInfo:
    #: The Flight that resulted in the generated unit.
    unit_type: Type[UnitType]
    control_point: ControlPoint

    @property
    def player_unit(self) -> bool:
        return self.control_point.captured


@dataclass(frozen=True)
class DebriefingDeadBuildingInfo:
    #: The ground object this building was present at.
    ground_object: TheaterGroundObject

    @property
    def player_unit(self) -> bool:
        return self.ground_object.control_point.captured


@dataclass(frozen=True)
class AirLosses:
    losses: List[DebriefingDeadAircraftInfo]

    def by_type(self, player: bool) -> Dict[Type[FlyingType], int]:
        losses_by_type: Dict[Type[FlyingType], int] = defaultdict(int)
        for loss in self.losses:
            if loss.flight.departure.captured != player:
                continue

            losses_by_type[loss.flight.unit_type] += 1
        return losses_by_type

    def surviving_flight_members(self, flight: Flight) -> int:
        losses = 0
        for loss in self.losses:
            if loss.flight == flight:
                losses += 1
        return flight.count - losses


@dataclass(frozen=True)
class FrontLineLosses:
    losses: List[DebriefingDeadFrontLineUnitInfo]

    def by_type(self, player: bool) -> Dict[Type[UnitType], int]:
        losses_by_type: Dict[Type[UnitType], int] = defaultdict(int)
        for loss in self.losses:
            if loss.control_point.captured != player:
                continue

            losses_by_type[loss.unit_type] += 1
        return losses_by_type


@dataclass(frozen=True)
class StateData:
    #: True if the mission ended. If False, the mission exited abnormally.
    mission_ended: bool

    #: Names of aircraft units that were killed during the mission.
    killed_aircraft: List[str]

    #: Names of vehicle (and ship) units that were killed during the mission.
    killed_ground_units: List[str]

    #: Names of static units that were destroyed during the mission.
    destroyed_statics: List[str]

    #: Mangled names of bases that were captured during the mission.
    base_capture_events: List[str]

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> StateData:
        return cls(
            mission_ended=data["mission_ended"],
            killed_aircraft=data["killed_aircrafts"],
            # Airfields emit a new "dead" event every time a bomb is dropped on
            # them when they've already dead. Dedup.
            killed_ground_units=list(set(data["killed_ground_units"])),
            destroyed_statics=data["destroyed_objects_positions"],
            base_capture_events=data["base_capture_events"]
        )


class Debriefing:
    def __init__(self, state_data: Dict[str, Any], game: Game,
                 unit_map: UnitMap) -> None:
        self.state_data = StateData.from_json(state_data)
        self.game = game
        self.unit_map = unit_map

        logging.info("--------------------------------")
        logging.info("Starting Debriefing preprocessing")
        logging.info("--------------------------------")
        logging.info(self.state_data)
        logging.info("--------------------------------")

        self.player_country_id = db.country_id_from_name(game.player_country)
        self.enemy_country_id = db.country_id_from_name(game.enemy_country)

        self.air_losses = self.dead_aircraft()
        self.front_line_losses = self.dead_front_line_units()
        self.dead_units = []
        self.damaged_runways = self.find_damaged_runways()
        self.dead_aaa_groups: List[DebriefingDeadUnitInfo] = []
        self.dead_buildings: List[DebriefingDeadBuildingInfo] = []

        for unit_name in self.state_data.killed_ground_units:
            for cp in game.theater.controlpoints:
                if cp.captured:
                    country = self.player_country_id
                else:
                    country = self.enemy_country_id
                player_unit = (country == self.player_country_id)

                for ground_object in cp.ground_objects:
                    # TODO: This seems to destroy an arbitrary building?
                    if ground_object.is_same_group(unit_name):
                        self.dead_buildings.append(
                            DebriefingDeadBuildingInfo(ground_object))
                    elif ground_object.dcs_identifier in ["AA", "CARRIER",
                                                          "LHA"]:
                        for g in ground_object.groups:
                            for u in g.units:
                                if u.name != unit_name:
                                    continue
                                unit_type = db.unit_type_from_name(u.type)
                                if unit_type is None:
                                    logging.error(
                                        f"Could not determine type of %s",
                                        unit_name)
                                    continue
                                self.dead_units.append(DebriefingDeadUnitInfo(
                                    player_unit, unit_type))

        self.player_dead_units = [a for a in self.dead_units if a.player_unit]
        self.enemy_dead_units = [a for a in self.dead_units if not a.player_unit]
        self.player_dead_buildings = [a for a in self.dead_buildings if a.player_unit]
        self.enemy_dead_buildings = [a for a in self.dead_buildings if not a.player_unit]

        self.player_dead_units_dict: Dict[Type[UnitType], int] = defaultdict(int)
        for a in self.player_dead_units:
            self.player_dead_units_dict[a.type] += 1

        self.enemy_dead_units_dict: Dict[Type[UnitType], int] = defaultdict(int)
        for a in self.enemy_dead_units:
            self.enemy_dead_units_dict[a.type] += 1

        self.player_dead_buildings_dict: Dict[str, int] = defaultdict(int)
        for b in self.player_dead_buildings:
            self.player_dead_buildings_dict[b.ground_object.dcs_identifier] += 1

        self.enemy_dead_buildings_dict: Dict[str, int] = defaultdict(int)
        for b in self.enemy_dead_buildings:
            self.enemy_dead_buildings_dict[b.ground_object.dcs_identifier] += 1

        logging.info("--------------------------------")
        logging.info("Debriefing pre process results :")
        logging.info("--------------------------------")
        logging.info(self.air_losses)
        logging.info(self.front_line_losses)
        logging.info(self.player_dead_units_dict)
        logging.info(self.enemy_dead_units_dict)
        logging.info(self.player_dead_buildings_dict)
        logging.info(self.enemy_dead_buildings_dict)

    def dead_aircraft(self) -> AirLosses:
        losses = []
        for unit_name in self.state_data.killed_aircraft:
            flight = self.unit_map.flight(unit_name)
            if flight is None:
                logging.error(f"Could not find Flight matching {unit_name}")
                continue
            losses.append(DebriefingDeadAircraftInfo(flight))
        return AirLosses(losses)

    def dead_front_line_units(self) -> FrontLineLosses:
        losses = []
        for unit_name in self.state_data.killed_ground_units:
            unit = self.unit_map.front_line_unit(unit_name)
            if unit is None:
                # Killed "ground units" might also be runways or TGO units, so
                # no need to log an error.
                continue
            losses.append(
                DebriefingDeadFrontLineUnitInfo(unit.unit_type, unit.origin))
        return FrontLineLosses(losses)

    def find_damaged_runways(self) -> List[Airfield]:
        losses = []
        for name in self.state_data.killed_ground_units:
            airfield = self.unit_map.airfield(name)
            if airfield is None:
                continue
            losses.append(airfield)
        return losses

    def _is_airfield(self, unit_name: str) -> bool:
        return self.unit_map.airfield(unit_name) is not None

    @property
    def base_capture_events(self):
        """Keeps only the last instance of a base capture event for each base ID."""
        reversed_captures = list(reversed(self.state_data.base_capture_events))
        last_base_cap_indexes = []
        for idx, base in enumerate(i.split("||")[0] for i in reversed_captures):
            if base not in [x[1] for x in last_base_cap_indexes]:
                last_base_cap_indexes.append((idx, base))
        return [reversed_captures[idx[0]] for idx in last_base_cap_indexes]        


class PollDebriefingFileThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, callback: Callable[[Debriefing], None],
                 game: Game, unit_map: UnitMap) -> None:
        super().__init__()
        self._stop_event = threading.Event()
        self.callback = callback
        self.game = game
        self.unit_map = unit_map

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        if os.path.isfile("state.json"):
            last_modified = os.path.getmtime("state.json")
        else:
            last_modified = 0
        while not self.stopped():
            if os.path.isfile("state.json") and os.path.getmtime("state.json") > last_modified:
                with open("state.json", "r") as json_file:
                    json_data = json.load(json_file)
                    debriefing = Debriefing(json_data, self.game, self.unit_map)
                    self.callback(debriefing)
                break
            time.sleep(5)


def wait_for_debriefing(callback: Callable[[Debriefing], None],
                        game: Game, unit_map) -> PollDebriefingFileThread:
    thread = PollDebriefingFileThread(callback, game, unit_map)
    thread.start()
    return thread
