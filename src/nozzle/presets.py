"""Preset nozzle configurations for common rocket engines."""
from .config import NozzleConfig


def merlin_1d() -> NozzleConfig:
    """SpaceX Merlin 1D (Falcon 9 first stage).

    - Chamber pressure: 9.7 MPa
    - Throat diameter: 165mm (R=82.5mm)
    - Exit diameter: 660mm (R=330mm)
    - Expansion ratio: 16:1
    - Convergent angle: 45 deg
    - Divergent angle: 30 deg (Rao bell)
    - Throat RoC: 41mm (0.5x throat radius)
    """
    return NozzleConfig(
        throat_radius=0.0825,
        expansion_ratio=16.0,
        converging_length=0.083,
        chamber_length=0.30,
        chamber_radius=0.124,
        convergent_half_angle=45.0,
        throat_radius_of_curvature=0.041,
        theta_n=30.0,
        theta_e=0.0,
        nozzle_length_fraction=0.8,
        num_points=400,
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
        chamber_length=0.30,
        chamber_radius=0.124,
        convergent_half_angle=45.0,
        throat_radius_of_curvature=0.041,
        theta_n=28.0,
        theta_e=0.0,
        nozzle_length_fraction=0.8,
        num_points=400,
    )


def rs_25() -> NozzleConfig:
    """Space Shuttle Main Engine (RS-25).

    - Chamber pressure: 20.6 MPa
    - Throat diameter: 272mm (R=136mm)
    - Exit diameter: ~2400mm (R=1200mm)
    - Expansion ratio: 77.5:1
    - Flow separation at sea level (overexpanded)
    """
    return NozzleConfig(
        throat_radius=0.136,
        expansion_ratio=77.5,
        converging_length=0.136,
        chamber_length=0.50,
        chamber_radius=0.204,
        convergent_half_angle=45.0,
        throat_radius_of_curvature=0.068,
        theta_n=25.0,
        theta_e=0.0,
        nozzle_length_fraction=0.8,
        num_points=400,
    )


def rl10b_2() -> NozzleConfig:
    """RL10B-2 (Delta IV upper stage).

    - Chamber pressure: 4.2 MPa
    - Throat diameter: 154mm (R=77mm)
    - Exit diameter: ~2600mm (R=1300mm)
    - Expansion ratio: 285:1 (highest of any operational engine)
    - Vacuum optimized (no flow separation concern)
    """
    return NozzleConfig(
        throat_radius=0.077,
        expansion_ratio=285.0,
        converging_length=0.077,
        chamber_length=0.60,
        chamber_radius=0.1155,
        convergent_half_angle=45.0,
        throat_radius_of_curvature=0.0385,
        theta_n=20.0,
        theta_e=0.0,
        nozzle_length_fraction=0.8,
        num_points=500,
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
        theta_e=0.0,
        nozzle_length_fraction=0,
        num_points=200,
    )


def aerospike_x33() -> "AerospikeConfig":
    """NASA X-33 style axisymmetric aerospike nozzle.

    - Throat radius: 82.5mm (annular gap inner)
    - Expansion ratio: 49:1
    - Spike length: 1.62m
    - Truncated at 80%
    - Designed for altitude compensation demonstration
    """
    from .aerospike import AerospikeConfig
    return AerospikeConfig(
        throat_radius=0.0825,
        expansion_ratio=49.0,
        spike_length=1.62,
        truncation_ratio=0.80,
        spike_theta_n=25.0,
        spike_theta_e=0.0,
        casing_length=0.30,
        casing_gap=0.04,
        num_points=300,
    )
