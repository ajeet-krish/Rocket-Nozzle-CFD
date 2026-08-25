"""Sweep orchestration."""
from pathlib import Path
from .config import SweepCase, SweepConfig, generate_sweep_cases
from .results import SweepCaseResult, SweepResults
from nozzle.config import NozzleConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.config import SU2NozzleConfig
from cfd.solver import SU2Solver
from validation.isentropic import exit_mach_from_area_ratio


class SweepRunner:
    """Orchestrate parametric sweep SU2 runs.

    Runs a series of SU2 simulations varying one parameter at a time
    (expansion ratio, chamber pressure, or throat radius) and records
    the results for comparison with isentropic theory.
    """

    def __init__(self, output_dir: Path) -> None:
        """Initialize the sweep runner.

        Args:
            output_dir: Base directory for sweep output.
        """
        self.output_dir = output_dir
        self.solver = SU2Solver()

    def run_single(self, case: SweepCase) -> SweepCaseResult:
        """Run a single sweep case.

        Args:
            case: SweepCase definition to execute.

        Returns:
            SweepCaseResult with SU2 results and isentropic comparison.
        """
        try:
            case_dir = self.output_dir / case.case_id
            case_dir.mkdir(parents=True, exist_ok=True)

            # Create nozzle config
            nozzle_config = NozzleConfig(
                throat_radius=case.throat_radius,
                expansion_ratio=case.expansion_ratio,
            )

            # Generate mesh
            mesh_path = generate_nozzle_mesh(
                nozzle_config,
                output_file=str(case_dir / "nozzle.su2"),
            )

            # Create SU2 config
            su2_config = SU2NozzleConfig(
                total_pressure=case.chamber_pressure,
                total_temperature=case.total_temperature,
                gamma=case.gamma,
                cfl_number=0.1,  # Conservative CFL for convergence
            )
            config_path = su2_config.write(case_dir)

            # Run SU2
            results = self.solver.run(config_path, case_dir)

            # Isentropic reference
            mach_iso = exit_mach_from_area_ratio(case.expansion_ratio, case.gamma)

            error = (
                abs(results.exit_mach - mach_iso) / mach_iso * 100
                if mach_iso > 0
                else 0.0
            )

            return SweepCaseResult(
                case_id=case.case_id,
                sweep_type=case.sweep_type,
                expansion_ratio=case.expansion_ratio,
                chamber_pressure=case.chamber_pressure,
                throat_radius=case.throat_radius,
                exit_mach_isentropic=mach_iso,
                exit_mach_su2=results.exit_mach,
                converged=results.converged,
                iterations=results.iterations,
                error_percent=error,
            )
        except Exception as e:
            print(f"  WARNING: Case {case.case_id} failed: {e}")
            return SweepCaseResult(
                case_id=case.case_id,
                sweep_type=case.sweep_type,
                expansion_ratio=case.expansion_ratio,
                chamber_pressure=case.chamber_pressure,
                throat_radius=case.throat_radius,
                exit_mach_isentropic=0.0,
                exit_mach_su2=0.0,
                converged=False,
                iterations=0,
                error_percent=100.0,
            )

    def run_sweep(self, config: SweepConfig) -> SweepResults:
        """Run all sweep cases.

        Args:
            config: SweepConfig defining the parameter ranges.

        Returns:
            SweepResults with all case results.
        """
        cases = generate_sweep_cases(config)
        results = SweepResults()

        for case in cases:
            print(f"Running {case.case_id}...")
            result = self.run_single(case)
            results.cases.append(result)

        return results
