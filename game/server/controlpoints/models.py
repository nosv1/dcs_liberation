from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.server.leaflet import LeafletPoint

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint


class ControlPointJs(BaseModel):
    id: UUID
    name: str
    blue: bool
    position: LeafletPoint
    mobile: bool
    destination: LeafletPoint | None
    sidc: str
    aircraft_count: int
    ground_units_count: int
    ground_units_deployable_count: int
    front_line_stances: list[str]

    class Config:
        title = "ControlPoint"

    @staticmethod
    def for_control_point(control_point: ControlPoint) -> ControlPointJs:
        destination = None
        if control_point.target_position is not None:
            destination = control_point.target_position.latlng()

        front_line_stances: list[str] = []
        for cp in control_point.connected_points:
            for cp_id, stance in control_point.stances.items():
                if cp_id != cp.id or cp.coalition == control_point.coalition:
                    continue
                front_line_stances.append(
                    f"{cp.name}: {stance.name if control_point.coalition.player else 'Unknown'}"
                )

        return ControlPointJs(
            id=control_point.id,
            name=control_point.name,
            blue=control_point.captured,
            position=control_point.position.latlng(),
            mobile=control_point.moveable and control_point.captured,
            destination=destination,
            sidc=str(control_point.sidc()),
            aircraft_count=control_point.allocated_aircraft().total_present,
            ground_units_count=control_point.base.total_armor,
            ground_units_deployable_count=control_point.frontline_unit_count_limit,
            front_line_stances=front_line_stances,
        )

    @staticmethod
    def all_in_game(game: Game) -> list[ControlPointJs]:
        return [
            ControlPointJs.for_control_point(cp) for cp in game.theater.controlpoints
        ]
