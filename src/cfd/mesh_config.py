"""Mesh generation configuration."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MeshConfig:
    """Configuration for structured O-grid mesh generation.

    Controls zone splitting, boundary layer refinement, and plume extension
    for the rocket nozzle mesh.

    Attributes:
        converging_cells: Number of axial cells in converging section
        throat_cells: Number of axial cells in throat region
        diverging_cells: Number of axial cells in diverging section
        plume_cells: Number of axial cells in plume extension
        n_normal: Number of cells normal to wall (boundary layer)
        first_cell_height: First cell height for boundary layer (m)
        growth_ratio: Geometric growth ratio for boundary layer
        plume_length_ratio: Plume length as multiple of throat radius
        plume_radius_ratio: Plume width as multiple of exit radius
        min_orthogonality: Minimum acceptable orthogonality (degrees)
        max_aspect_ratio: Maximum acceptable aspect ratio
        max_expansion_ratio: Maximum acceptable cell expansion ratio
    """
    converging_cells: int = 40
    throat_cells: int = 30
    diverging_cells: int = 70
    plume_cells: int = 60
    n_normal: int = 80
    first_cell_height: float = 1e-6
    growth_ratio: float = 1.15
    plume_length_ratio: float = 30.0
    plume_radius_ratio: float = 3.0
    min_orthogonality: float = 20.0
    max_aspect_ratio: float = 100.0
    max_expansion_ratio: float = 2.0

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        if self.converging_cells <= 0:
            raise ValueError(
                f"converging_cells must be > 0, got {self.converging_cells}",
            )
        if self.throat_cells <= 0:
            raise ValueError(
                f"throat_cells must be > 0, got {self.throat_cells}",
            )
        if self.diverging_cells <= 0:
            raise ValueError(
                f"diverging_cells must be > 0, got {self.diverging_cells}",
            )
        if self.plume_cells <= 0:
            raise ValueError(
                f"plume_cells must be > 0, got {self.plume_cells}",
            )
        if self.n_normal <= 0:
            raise ValueError(
                f"n_normal must be > 0, got {self.n_normal}",
            )
        if self.first_cell_height <= 0:
            raise ValueError(
                f"first_cell_height must be > 0, got {self.first_cell_height}",
            )
        if self.growth_ratio <= 1.0:
            raise ValueError(
                f"growth_ratio must be > 1.0, got {self.growth_ratio}",
            )
        if self.plume_radius_ratio < 1.0:
            raise ValueError(
                f"plume_radius_ratio must be >= 1.0, got {self.plume_radius_ratio}",
            )

    @property
    def n_axial(self) -> int:
        """Total number of axial cells across all zones."""
        return (self.converging_cells + self.throat_cells +
                self.diverging_cells + self.plume_cells)
