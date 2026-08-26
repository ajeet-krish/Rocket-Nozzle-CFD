"""Preset nozzle configurations for common rocket engines."""
from .config import NozzleConfig


def merlin_1d() -> NozzleConfig:
    """SpaceX Merlin 1D (Falcon 9 first stage).

    - Chamber pressure: 9.7 MPa
    - Throat diameter: 165mm (R=82.5mm)
    - Exit diameter: 660mm (R=330mm)
    - Expansion ratio: 16:1
    - Convergent angle: 45 deg
    - Divergent angle: 15 deg (Rao bell)
    - Throat RoC: 41mm (0.5x throat radius)
    """
    return NozzleConfig(
        throat_radius=0.0825,
        expansion_ratio=16.0,
        converging_length=0.083,
        diverging_length=0.4,
        chamber_length=0.05,
        chamber_radius=0.124,        # 1.5x throat
        convergent_half_angle=45.0,
        throat_radius_of_curvature=0.0,
        theta_n=30.0,
        num_points=300,
    )


def raptor_sl() -> NozzleConfig:
    """SpaceX Raptor sea-level variant.

    - Chamber pressure: 33 MPa
    - Throat diameter: ~165mm (R=82.5mm)
    - Exit diameter: ~960mm (R=480mm)
    - Expansion ratio: 34:1
    """
    return NozzleConfig(
        throat_radius=0.0825,
        expansion_ratio=34.0,
        converging_length=0.083,
        diverging_length=0.6,
        chamber_length=0.05,
        chamber_radius=0.124,
        convergent_half_angle=45.0,
        throat_radius_of_curvature=0.0,
        theta_n=30.0,
        num_points=300,
    )


def generic_test() -> NozzleConfig:
    """Generic test nozzle (v1 compatible, epsilon=12).

    Backward-compatible with existing validation cases.
    """
    return NozzleConfig(
        throat_radius=0.05,
        expansion_ratio=12.0,
        converging_length=0.1,
        diverging_length=0.5,
        num_points=200,
    )
