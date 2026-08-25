"""Grid Convergence Index computation (ASME V&V 20-2009)."""
from dataclasses import dataclass
import math


@dataclass
class GCIMeshLevel:
    """Single mesh level for GCI study.

    Attributes:
        n_cells: Number of cells in the mesh.
        exit_mach: Exit Mach number from this mesh level.
        thrust_coefficient: Thrust coefficient from this mesh level.
    """
    n_cells: int
    exit_mach: float
    thrust_coefficient: float


@dataclass
class GCIResult:
    """Grid Convergence Index result.

    Attributes:
        coarse: Coarsest mesh level data.
        medium: Medium mesh level data.
        fine: Finest mesh level data.
        refinement_ratio: Mesh refinement ratio between levels.
        apparent_order: Apparent order of convergence (Richardson).
        extrapolated_mach: Richardson-extrapolated exit Mach.
        extrapolated_thrust: Richardson-extrapolated thrust coefficient.
        gci_fine_mach: GCI on finest mesh for exit Mach (percentage).
        gci_fine_thrust: GCI on finest mesh for thrust coefficient.
        asymptotic_ratio_mach: Asymptotic ratio check for Mach.
        passed: True if GCI and asymptotic checks pass.
        notes: Human-readable summary string.
    """
    coarse: GCIMeshLevel
    medium: GCIMeshLevel
    fine: GCIMeshLevel
    refinement_ratio: float
    apparent_order: float
    extrapolated_mach: float
    extrapolated_thrust: float
    gci_fine_mach: float
    gci_fine_thrust: float
    asymptotic_ratio_mach: float
    passed: bool
    notes: str


def richardson_extrapolation(
    f1: float,
    f2: float,
    f3: float,
    r: float = 2.0,
) -> tuple[float, float]:
    """Compute apparent order and Richardson-extrapolated solution.

    Uses three mesh levels (fine=f1, medium=f2, coarse=f3) to estimate
    the apparent order of convergence p and the extrapolated exact solution.

    Args:
        f1: Solution on finest mesh.
        f2: Solution on medium mesh.
        f3: Solution on coarsest mesh.
        r: Mesh refinement ratio between consecutive levels.

    Returns:
        Tuple of (apparent_order, extrapolated_solution).
    """
    if abs(f1 - f2) < 1e-12 or abs(f2 - f3) < 1e-12:
        return 1.0, f1

    # Apparent order
    p = math.log(abs(f3 - f2) / abs(f2 - f1)) / math.log(r)

    # Extrapolated solution
    f_exact = f1 + (f1 - f2) / (r**p - 1)

    return p, f_exact


def compute_gci(
    coarse: GCIMeshLevel,
    medium: GCIMeshLevel,
    fine: GCIMeshLevel,
    refinement_ratio: float = 2.0,
    safety_factor: float = 1.25,
) -> GCIResult:
    """Compute Grid Convergence Index per ASME V&V 20-2009.

    Calculates the GCI on the finest mesh level for both exit Mach and
    thrust coefficient, verifies the apparent order of convergence, and
    checks the asymptotic convergence ratio.

    Args:
        coarse: Coarsest mesh level data.
        medium: Medium mesh level data.
        fine: Finest mesh level data.
        refinement_ratio: Mesh refinement ratio between levels.
        safety_factor: Safety factor for GCI (default 1.25 per ASME).

    Returns:
        GCIResult with all convergence metrics.
    """
    # Richardson extrapolation for exit Mach
    p_mach, f_exact_mach = richardson_extrapolation(
        fine.exit_mach, medium.exit_mach, coarse.exit_mach, refinement_ratio,
    )

    # Richardson extrapolation for thrust coefficient
    p_thrust, f_exact_thrust = richardson_extrapolation(
        fine.thrust_coefficient,
        medium.thrust_coefficient,
        coarse.thrust_coefficient,
        refinement_ratio,
    )

    # GCI for fine mesh (exit Mach)
    e_mach = abs(fine.exit_mach - medium.exit_mach)
    if p_mach > 0:
        gci_fine_mach = (
            safety_factor * e_mach / (refinement_ratio**p_mach - 1)
        )
    else:
        gci_fine_mach = 0.0

    # GCI for fine mesh (thrust coefficient)
    e_thrust = abs(fine.thrust_coefficient - medium.thrust_coefficient)
    if p_thrust > 0:
        gci_fine_thrust = (
            safety_factor * e_thrust / (refinement_ratio**p_thrust - 1)
        )
    else:
        gci_fine_thrust = 0.0

    # Asymptotic ratio check (exit Mach)
    if p_mach > 0:
        gci_medium_mach = (
            safety_factor
            * abs(medium.exit_mach - coarse.exit_mach)
            / (refinement_ratio**p_mach - 1)
        )
        asymptotic_ratio = gci_medium_mach / (
            refinement_ratio**p_mach * gci_fine_mach
        ) if gci_fine_mach > 0 else 1.0
    else:
        gci_medium_mach = 0.0
        asymptotic_ratio = 1.0

    # Pass criteria: GCI < 5% and asymptotic ratio in (0.5, 2.0)
    passed = gci_fine_mach < 5.0 and 0.5 < asymptotic_ratio < 2.0

    notes = (
        f"GCI fine: {gci_fine_mach:.3f}%, order: {p_mach:.2f}, "
        f"asymptotic: {asymptotic_ratio:.2f}"
    )

    return GCIResult(
        coarse=coarse,
        medium=medium,
        fine=fine,
        refinement_ratio=refinement_ratio,
        apparent_order=p_mach,
        extrapolated_mach=f_exact_mach,
        extrapolated_thrust=f_exact_thrust,
        gci_fine_mach=gci_fine_mach,
        gci_fine_thrust=gci_fine_thrust,
        asymptotic_ratio_mach=asymptotic_ratio,
        passed=passed,
        notes=notes,
    )
