"""Engine configuration for per-engine CFD pipeline."""
from dataclasses import dataclass, field
from enum import Enum
from collections.abc import Callable

from nozzle.config import NozzleConfig


class PipelineStage(Enum):
    """Pipeline execution stages."""
    GEOMETRY = "geometry"
    MESH = "mesh"
    EULER = "euler"
    RANS = "rans"
    PLUME = "plume"
    SWEEP = "sweep"


@dataclass(frozen=True)
class EngineConfig:
    """Per-engine CFD pipeline configuration.

    Attributes:
        name: Engine slug for directory naming (e.g. 'merlin-1d')
        label: Human-readable name (e.g. 'Merlin 1D')
        preset_fn: Callable returning NozzleConfig
        total_pressure: Chamber total pressure (Pa)
        total_temperature: Chamber total temperature (K)
        gamma: Ratio of specific heats
        theta_n: Wall angle at throat (degrees)
        ld: Diverging section length (m)
        euler_n_axial: Euler mesh axial cells
        euler_n_normal: Euler mesh normal cells
        rans_n_axial: RANS mesh axial cells
        rans_n_normal: RANS mesh normal cells
        plume_n_axial: Plume mesh axial cells
        plume_n_normal: Plume mesh normal cells
        euler_cfl: Euler CFL number
        euler_iterations: Euler max iterations
        rans_cfl: RANS CFL number
        rans_iterations: RANS max iterations
        plume_length_ratio: Plume length as multiple of throat radius
        plume_radius_ratio: Plume width as multiple of exit radius
        sweep_expansion_ratios: Expansion ratios for sweep
        sweep_chamber_pressures: Chamber pressures for sweep (Pa)
        sweep_throat_radii: Throat radii for sweep (m)
    """
    name: str
    label: str
    preset_fn: Callable[[], NozzleConfig]
    total_pressure: float
    total_temperature: float
    gamma: float = 1.4
    theta_n: float = 30.0
    ld: float = 0.7
    euler_n_axial: int = 40
    euler_n_normal: int = 20
    rans_n_axial: int = 40
    rans_n_normal: int = 30
    plume_n_axial: int = 40
    plume_n_normal: int = 20
    euler_cfl: float = 0.1
    euler_iterations: int = 5000
    rans_cfl: float = 0.05
    rans_iterations: int = 10000
    plume_length_ratio: float = 10.0
    plume_radius_ratio: float = 2.0
    sweep_expansion_ratios: tuple[float, ...] = (4.0, 8.0, 12.0, 16.0, 20.0)
    sweep_chamber_pressures: tuple[float, ...] = (5e6, 10e6, 20e6, 50e6)
    sweep_throat_radii: tuple[float, ...] = (0.01, 0.025, 0.05, 0.1)

    @property
    def output_dir(self) -> str:
        """Output directory for simulation artifacts."""
        return f"output/{self.name}"

    @property
    def images_dir(self) -> str:
        """Images directory for plots."""
        return f"docs/assets/images/{self.name}/geometry"

    def nozzle_config(self) -> NozzleConfig:
        """Build NozzleConfig from engine preset and overrides.

        Uses preset's computed_diverging_length (Rao formula) when ld is None.
        """
        base = self.preset_fn()
        ld = self.ld if self.ld is not None else base.computed_diverging_length
        return NozzleConfig(
            throat_radius=base.throat_radius,
            expansion_ratio=base.expansion_ratio,
            converging_length=base.converging_length,
            diverging_length=ld,
            chamber_length=0,
            throat_radius_of_curvature=0,
            theta_n=self.theta_n,
            theta_e=0.0,
            nozzle_length_fraction=0,
            num_points=300,
        )
