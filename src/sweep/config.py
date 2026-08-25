"""Parametric sweep configuration."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SweepConfig:
    """Configuration for parametric sweep.

    Attributes:
        expansion_ratios: Expansion ratios (Ae/At) to sweep.
        chamber_pressures: Chamber pressures (Pa) to sweep.
        throat_radii: Throat radii (m) to sweep.
        reference_epsilon: Reference expansion ratio for Pc and R* sweeps.
        reference_pc: Reference chamber pressure (Pa) for epsilon and R* sweeps.
        reference_r_star: Reference throat radius (m) for epsilon and Pc sweeps.
        total_temperature: Total temperature (K).
        gamma: Ratio of specific heats.
    """
    expansion_ratios: tuple[float, ...] = (4.0, 8.0, 12.0, 16.0, 20.0)
    chamber_pressures: tuple[float, ...] = (5e6, 10e6, 20e6, 50e6)
    throat_radii: tuple[float, ...] = (0.01, 0.025, 0.05, 0.1)
    reference_epsilon: float = 12.0
    reference_pc: float = 10e6
    reference_r_star: float = 0.05
    total_temperature: float = 3500.0
    gamma: float = 1.4


@dataclass
class SweepCase:
    """A single sweep case definition.

    Attributes:
        case_id: Unique identifier for this case.
        sweep_type: Which parameter is being varied (epsilon, pc, r_star).
        expansion_ratio: Area ratio for this case.
        chamber_pressure: Chamber pressure (Pa) for this case.
        throat_radius: Throat radius (m) for this case.
        total_temperature: Total temperature (K).
        gamma: Ratio of specific heats.
    """
    case_id: str
    sweep_type: str
    expansion_ratio: float
    chamber_pressure: float
    throat_radius: float
    total_temperature: float
    gamma: float


def generate_sweep_cases(config: SweepConfig) -> list[SweepCase]:
    """Generate all sweep cases from config.

    Creates sweep cases for expansion ratio, chamber pressure, and throat
    radius variations. Reference values are included in the epsilon sweep
    but skipped for pc and r_star sweeps to avoid redundant cases.

    Args:
        config: SweepConfig defining the parameter ranges.

    Returns:
        List of SweepCase instances.
    """
    cases: list[SweepCase] = []

    # Epsilon sweep (includes reference)
    for eps in config.expansion_ratios:
        cases.append(SweepCase(
            case_id=f"epsilon_{eps:.0f}",
            sweep_type="epsilon",
            expansion_ratio=eps,
            chamber_pressure=config.reference_pc,
            throat_radius=config.reference_r_star,
            total_temperature=config.total_temperature,
            gamma=config.gamma,
        ))

    # Pc sweep (skip reference)
    for pc in config.chamber_pressures:
        if pc != config.reference_pc:
            cases.append(SweepCase(
                case_id=f"pc_{pc / 1e6:.0f}mpa",
                sweep_type="pc",
                expansion_ratio=config.reference_epsilon,
                chamber_pressure=pc,
                throat_radius=config.reference_r_star,
                total_temperature=config.total_temperature,
                gamma=config.gamma,
            ))

    # R* sweep (skip reference)
    for r_star in config.throat_radii:
        if r_star != config.reference_r_star:
            cases.append(SweepCase(
                case_id=f"rstar_{r_star:.3f}",
                sweep_type="r_star",
                expansion_ratio=config.reference_epsilon,
                chamber_pressure=config.reference_pc,
                throat_radius=r_star,
                total_temperature=config.total_temperature,
                gamma=config.gamma,
            ))

    return cases
