from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class LatLon:
    latitude: float
    longitude: float

    def as_list(self) -> List[float]:
        return [self.latitude, self.longitude]

    @staticmethod
    def _components(dimension: float) -> Tuple[int, int, float]:
        degrees = int(dimension)
        minutes = int(dimension * 60 % 60)
        seconds = dimension * 3600 % 60
        return degrees, minutes, seconds

    def _format_component(
        self,
        dimension: float,
        hemispheres: Tuple[str, str],
        seconds_precision: int,
        include_seconds: bool = True,
    ) -> str:
        hemisphere = hemispheres[0] if dimension >= 0 else hemispheres[1]
        degrees, minutes, seconds = self._components(dimension)

        string = f"{hemisphere} {degrees}°{minutes:02}"
        if include_seconds:
            string += f"'{seconds:.{seconds_precision}f}\""
        else:
            string += f".{seconds/60*1000:.0f}'"
        return string

    def format_dms(
        self, include_decimal_seconds: bool = False, include_seconds: bool = True
    ) -> str:
        precision = 2 if include_decimal_seconds else 0
        return " ".join(
            [
                self._format_component(
                    self.latitude, ("N", "S"), precision, include_seconds
                ),
                self._format_component(
                    self.longitude, ("E", "W"), precision, include_seconds
                ),
            ]
        )
