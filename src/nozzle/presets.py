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
    - Throat RoC: 40mm
    """
    return NozzleConfig(
        throat_radius=0.0825,
        expansion_ratio=16.0,
        converging_length=0.15,      # computed from angle
        diverging_length=0.334,       # from geometry
        chamber_length=0.09993,       # ~100mm
        chamber_radius=0.0833,        # 166.6mm dia / 2
        convergent_half_angle=45.0,
        throat_radius_of_curvature=0.04,
        theta_n=30.0,
        num_points=300,
    )


def raptor_sl() -> NozzleConfig:
    """SpaceX Raptor sea-level variant.

    - Chamber pressure: 33 MPa
    - Throat diameter: ~165mm
    - Exit diameter: ~960mm
    - Expansion ratio: 34:1
    """
    return NozzleConfig(
        throat_radius=0.0825,
        expansion_ratio=34.0,
        converging_length=0.15,
        diverging_length=0.5,
        chamber_length=0.1,
        chamber_radius=0.0833,
        convergent_half_angle=45.0,
        throat_radius_of_curvature=0.04,
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
