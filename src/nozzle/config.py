"""Nozzle geometry configuration."""
from dataclasses import dataclass
import math
from typing import Any


@dataclass(frozen=True)
class NozzleConfig:
    """Converging-diverging nozzle geometry parameters.

    Attributes:
        throat_radius: Throat radius (m)
        expansion_ratio: Area ratio A_exit/A_throat
        converging_length: Converging section length (m)
        diverging_length: Diverging section length (m)
        num_points: Number of contour points
    """
    throat_radius: float = 0.05          # m
    expansion_ratio: float = 12.0        # A_exit / A_throat
    converging_length: float = 0.1       # m (inlet to throat)
    diverging_length: float = 0.5        # m (throat to exit)
    num_points: int = 200                # contour resolution

    @property
    def exit_radius(self) -> float:
        """Exit radius from expansion ratio."""
        return self.throat_radius * (self.expansion_ratio ** 0.5)

    @property
    def half_angle(self) -> float:
        """Diverging section half-angle (degrees), computed from geometry.

        This ensures the contour matches the expansion_ratio exactly.
        """
        return math.degrees(math.atan(
            (self.exit_radius - self.throat_radius) / self.diverging_length
        ))

    @property
    def throat_area(self) -> float:
        """Throat cross-sectional area."""
        return math.pi * self.throat_radius ** 2

    @property
    def exit_area(self) -> float:
        """Exit cross-sectional area."""
        return math.pi * self.exit_radius ** 2

    @property
    def ideal_length(self) -> float:
        """Ideal bell length (Rao formula)."""
        return 0.5 * (math.sqrt(self.exit_radius) - math.sqrt(self.throat_radius)) * math.sqrt(
            self.throat_radius + self.exit_radius
        )

    @classmethod
    def validate(cls, **kwargs: Any) -> "NozzleConfig":
        """Create and validate NozzleConfig.

        Args:
            **kwargs: Keyword arguments passed to NozzleConfig constructor.

        Returns:
            Validated NozzleConfig instance.

        Raises:
            ValueError: If any parameter is out of range.
        """
        config = cls(**kwargs)
        if config.throat_radius <= 0:
            raise ValueError(
                f"throat_radius must be > 0, got {config.throat_radius}"
            )
        if config.expansion_ratio < 1.0:
            raise ValueError(
                f"expansion_ratio must be >= 1.0, got {config.expansion_ratio}"
            )
        if config.diverging_length <= 0:
            raise ValueError(
                f"diverging_length must be > 0, got {config.diverging_length}"
            )
        if config.num_points < 2:
            raise ValueError(
                f"num_points must be >= 2, got {config.num_points}"
            )
        return config
