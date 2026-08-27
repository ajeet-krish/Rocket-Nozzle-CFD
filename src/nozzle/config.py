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
        chamber_length: Straight cylinder before convergent (m, 0 = no chamber)
        chamber_radius: Chamber radius (m, 0 = auto-computed as 1.5x throat_radius)
        convergent_half_angle: Half-angle of convergent section (degrees)
        throat_radius_of_curvature: Throat radius of curvature (m, 0 = linear convergent)
        theta_n: Wall angle at throat for Rao bell (degrees)
        theta_e: Exit wall angle (degrees, 0 = perfectly expanded)
        nozzle_length_fraction: Fraction of ideal bell length (0.6, 0.8, 0.9)
    """
    # Existing fields (unchanged defaults)
    throat_radius: float = 0.05          # m
    expansion_ratio: float = 12.0        # A_exit / A_throat
    converging_length: float = 0.1       # m (inlet to throat)
    diverging_length: float = 0.5        # m (throat to exit)
    num_points: int = 200                # contour resolution

    # New fields
    chamber_length: float = 0.0          # m (straight cylinder before convergent, 0 = no chamber)
    chamber_radius: float = 0.0          # m (if 0, computed as throat_radius * 1.5 for backward compat)
    convergent_half_angle: float = 45.0  # degrees (half-angle of convergent section)
    throat_radius_of_curvature: float = 0.0  # m (0 = linear convergent for backward compat)
    theta_n: float = 30.0               # degrees (wall angle at throat for Rao bell)
    theta_e: float = 0.0                  # degrees (exit wall angle, 0 = perfectly expanded)
    nozzle_length_fraction: float = 0.8   # fraction of ideal bell length (0.6, 0.8, 0.9)

    @property
    def exit_radius(self) -> float:
        """Exit radius from expansion ratio."""
        return self.throat_radius * (self.expansion_ratio ** 0.5)

    @property
    def effective_inlet_radius(self) -> float:
        """Inlet radius (chamber_radius if set, else 1.5x throat for backward compat)."""
        if self.chamber_radius > 0:
            return self.chamber_radius
        return self.throat_radius * 1.5

    @property
    def total_length(self) -> float:
        """Total nozzle length: chamber + converging + diverging."""
        return self.chamber_length + self.converging_length + self.diverging_length

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

    @property
    def ideal_diverging_length(self) -> float:
        """Ideal diverging length from Bell-Nozzle formula.

        LN = nozzle_length_fraction * (sqrt(expansion_ratio) - 1) * throat_radius / tan(15 deg)
        """
        return self.nozzle_length_fraction * (
            math.sqrt(self.expansion_ratio) - 1
        ) * self.throat_radius / math.tan(math.radians(15))

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
        if config.chamber_length < 0:
            raise ValueError(
                f"chamber_length must be >= 0, got {config.chamber_length}"
            )
        if config.chamber_radius < 0:
            raise ValueError(
                f"chamber_radius must be >= 0, got {config.chamber_radius}"
            )
        if not (10.0 <= config.convergent_half_angle <= 80.0):
            raise ValueError(
                f"convergent_half_angle must be between 10 and 80 degrees, "
                f"got {config.convergent_half_angle}"
            )
        if config.throat_radius_of_curvature < 0:
            raise ValueError(
                f"throat_radius_of_curvature must be >= 0, got {config.throat_radius_of_curvature}"
            )
        if not (5.0 <= config.theta_n <= 60.0):
            raise ValueError(
                f"theta_n must be between 5 and 60 degrees, got {config.theta_n}"
            )
        if not (-10.0 <= config.theta_e <= 30.0):
            raise ValueError(
                f"theta_e must be between -10 and 30 degrees, got {config.theta_e}"
            )
        if not (0.4 <= config.nozzle_length_fraction <= 1.0):
            raise ValueError(
                f"nozzle_length_fraction must be between 0.4 and 1.0, got {config.nozzle_length_fraction}"
            )
        return config
