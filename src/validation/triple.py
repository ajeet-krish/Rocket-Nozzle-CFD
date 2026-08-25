"""Three-way validation comparison (isentropic vs MoC vs SU2)."""
from dataclasses import dataclass


@dataclass
class TripleReport:
    """Three-way validation comparison result.

    Attributes:
        exit_mach_isentropic: Exit Mach from isentropic theory.
        exit_mach_moc: Exit Mach from Method of Characteristics.
        exit_mach_su2: Exit Mach from SU2 CFD simulation.
        l2_error_iso_moc: Percentage error between isentropic and MoC.
        l2_error_iso_su2: Percentage error between isentropic and SU2.
        l2_error_moc_su2: Percentage error between MoC and SU2.
        max_error_percent: Maximum of the three pairwise errors.
        passed: True if max_error_percent < tolerance.
        notes: Human-readable summary string.
    """
    exit_mach_isentropic: float
    exit_mach_moc: float
    exit_mach_su2: float
    l2_error_iso_moc: float
    l2_error_iso_su2: float
    l2_error_moc_su2: float
    max_error_percent: float
    passed: bool
    notes: str


def compare_three_way(
    exit_mach_isentropic: float,
    exit_mach_moc: float,
    exit_mach_su2: float,
    tolerance: float = 5.0,
) -> TripleReport:
    """Compare exit Mach from three sources (isentropic, MoC, SU2).

    Computes pairwise percentage errors between all three methods and
    determines overall pass/fail based on the maximum error.

    Args:
        exit_mach_isentropic: Exit Mach from isentropic theory.
        exit_mach_moc: Exit Mach from Method of Characteristics.
        exit_mach_su2: Exit Mach from SU2 CFD simulation.
        tolerance: Maximum acceptable error percentage (default 5.0%).

    Returns:
        TripleReport with all error metrics and pass/fail status.
    """
    # Pairwise errors (percentage of reference value)
    if exit_mach_isentropic > 0:
        l2_iso_moc = abs(exit_mach_isentropic - exit_mach_moc) / exit_mach_isentropic * 100
        l2_iso_su2 = abs(exit_mach_isentropic - exit_mach_su2) / exit_mach_isentropic * 100
    else:
        l2_iso_moc = 0.0
        l2_iso_su2 = 0.0

    if exit_mach_moc > 0:
        l2_moc_su2 = abs(exit_mach_moc - exit_mach_su2) / exit_mach_moc * 100
    else:
        l2_moc_su2 = 0.0

    max_error = max(l2_iso_moc, l2_iso_su2, l2_moc_su2)
    passed = max_error < tolerance

    notes = (
        f"Max error: {max_error:.2f}%, tolerance: {tolerance}%, "
        f"{'PASSED' if passed else 'FAILED'}"
    )

    return TripleReport(
        exit_mach_isentropic=exit_mach_isentropic,
        exit_mach_moc=exit_mach_moc,
        exit_mach_su2=exit_mach_su2,
        l2_error_iso_moc=l2_iso_moc,
        l2_error_iso_su2=l2_iso_su2,
        l2_error_moc_su2=l2_moc_su2,
        max_error_percent=max_error,
        passed=passed,
        notes=notes,
    )
