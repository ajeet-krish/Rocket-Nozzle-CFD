"""Sweep results storage and aggregation."""
from dataclasses import dataclass, field
from pathlib import Path
import csv


@dataclass
class SweepCaseResult:
    """Result from a single sweep case.

    Attributes:
        case_id: Unique case identifier.
        sweep_type: Which parameter was varied (epsilon, pc, r_star).
        expansion_ratio: Expansion ratio for this case.
        chamber_pressure: Chamber pressure (Pa) for this case.
        throat_radius: Throat radius (m) for this case.
        exit_mach_isentropic: Isentropic prediction for exit Mach.
        exit_mach_su2: SU2 result for exit Mach.
        converged: Whether the SU2 simulation converged.
        iterations: Number of SU2 iterations.
        error_percent: Percentage error between SU2 and isentropic.
    """
    case_id: str
    sweep_type: str
    expansion_ratio: float
    chamber_pressure: float
    throat_radius: float
    exit_mach_isentropic: float
    exit_mach_su2: float
    converged: bool
    iterations: int
    error_percent: float


@dataclass
class SweepResults:
    """Aggregated sweep results.

    Attributes:
        cases: List of individual sweep case results.
    """
    cases: list[SweepCaseResult] = field(default_factory=list)

    def by_sweep_type(self, sweep_type: str) -> list[SweepCaseResult]:
        """Filter results by sweep type.

        Args:
            sweep_type: Sweep type to filter on (epsilon, pc, r_star).

        Returns:
            List of SweepCaseResult matching the sweep type.
        """
        return [c for c in self.cases if c.sweep_type == sweep_type]

    def to_csv(self, path: Path) -> None:
        """Export results to CSV file.

        Args:
            path: Output CSV file path.
        """
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'case_id', 'sweep_type', 'expansion_ratio', 'chamber_pressure',
                'throat_radius', 'exit_mach_isentropic', 'exit_mach_su2',
                'error_percent', 'converged', 'iterations',
            ])
            for case in self.cases:
                writer.writerow([
                    case.case_id, case.sweep_type, case.expansion_ratio,
                    case.chamber_pressure, case.throat_radius,
                    case.exit_mach_isentropic, case.exit_mach_su2,
                    case.error_percent, case.converged, case.iterations,
                ])
