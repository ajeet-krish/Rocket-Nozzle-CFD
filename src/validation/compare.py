"""Comparison between SU2 and isentropic theory."""
from dataclasses import dataclass
from .isentropic import exit_mach_from_area_ratio


@dataclass
class ComparisonReport:
    """Comparison between SU2 and isentropic theory."""
    exit_mach_sim: float
    exit_mach_theory: float
    mach_error_percent: float
    converged: bool
    passed: bool  # |error| < 5%
    notes: str


def compare_results(
    exit_mach_sim: float,
    expansion_ratio: float,
    gamma: float = 1.4,
    tolerance: float = 5.0,
) -> ComparisonReport:
    """Compare SU2 exit Mach against isentropic prediction.

    Args:
        exit_mach_sim: Exit Mach from SU2 simulation
        expansion_ratio: Area ratio A_exit/A_throat
        gamma: Ratio of specific heats
        tolerance: Acceptable error percentage

    Returns:
        Comparison report with pass/fail status
    """
    # Calculate theoretical exit Mach
    exit_mach_theory = exit_mach_from_area_ratio(expansion_ratio, gamma)

    # Calculate error
    if exit_mach_theory > 0:
        mach_error_percent = abs(exit_mach_sim - exit_mach_theory) / exit_mach_theory * 100.0
    else:
        mach_error_percent = float('inf')

    # Determine pass/fail
    passed = mach_error_percent < tolerance and exit_mach_sim > 0

    # Generate notes
    notes = []
    if exit_mach_sim <= 0:
        notes.append("No valid exit Mach from simulation")
    if mach_error_percent >= tolerance:
        notes.append(f"Error {mach_error_percent:.1f}% exceeds {tolerance}% tolerance")
    if not passed:
        notes.append("VALIDATION FAILED")
    else:
        notes.append("VALIDATION PASSED")

    return ComparisonReport(
        exit_mach_sim=exit_mach_sim,
        exit_mach_theory=exit_mach_theory,
        mach_error_percent=mach_error_percent,
        converged=exit_mach_sim > 0,
        passed=passed,
        notes="; ".join(notes),
    )
