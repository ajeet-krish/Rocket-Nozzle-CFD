"""Nozzle geometry configuration."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class NozzleConfig:
    """Converging-diverging nozzle geometry parameters."""
    throat_radius: float = 0.05          # m
    expansion_ratio: float = 12.0        # A_exit / A_throat
    half_angle: float = 15.0             # degrees (diverging section)
    converging_length: float = 0.1       # m (inlet to throat)
    diverging_length: float = 0.5        # m (throat to exit)
    num_points: int = 200                # contour resolution

    @property
    def exit_radius(self) -> float:
        """Exit radius from expansion ratio."""
        return self.throat_radius * (self.expansion_ratio ** 0.5)

    @property
    def throat_area(self) -> float:
        """Throat cross-sectional area."""
        return math.pi * self.throat_radius ** 2

    @property
    def exit_area(self) -> float:
        """Exit cross-sectional area."""
        return math.pi * self.exit_radius ** 2
