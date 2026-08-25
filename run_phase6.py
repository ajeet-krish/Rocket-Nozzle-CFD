#!/usr/bin/env python3
"""Phase 6: Triple validation, parametric sweeps, and GCI study."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.config import NozzleConfig
from cfd.config import SU2NozzleConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver
from validation.isentropic import exit_mach_from_area_ratio
from validation.moc_solver import MoCSolver
from validation.compare import compare_results
from validation.triple import compare_three_way
from validation.gci import GCIMeshLevel, compute_gci
from sweep.config import SweepConfig
from sweep.runner import SweepRunner
from sweep.plotter import plot_sweep


def main() -> int:
    """Run Phase 6 validation pipeline.

    Steps:
        1. Triple validation (isentropic vs MoC vs SU2)
        2. Parametric sweeps (epsilon, Pc, R*)
        3. Grid Convergence Index study

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("Phase 6: Triple Validation + Parametric Sweeps + GCI")
    print("=" * 60)

    images_dir = Path("docs/assets/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Configuration
    nozzle_config = NozzleConfig(
        throat_radius=0.05,
        expansion_ratio=12.0,
    )

    su2_config = SU2NozzleConfig(
        total_pressure=10e6,
        total_temperature=3500.0,
        cfl_number=0.1,
        gamma=1.4,
    )

    workdir = Path("output/phase6")
    workdir.mkdir(parents=True, exist_ok=True)

    # ================================================================
    # STEP 1: Triple Validation
    # ================================================================
    print("\n[1/3] Triple Validation (isentropic vs MoC vs SU2)...")
    print("-" * 60)

    # Isentropic
    mach_isentropic = exit_mach_from_area_ratio(
        nozzle_config.expansion_ratio,
        gamma=1.4,
    )

    # MoC
    moc_solver = MoCSolver()
    moc_results = moc_solver.solve(nozzle_config)
    mach_moc = float(moc_results.mach[-1]) if len(moc_results.mach) > 0 else 0.0

    # SU2
    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        output_file=str(workdir / "nozzle.su2"),
    )
    su2_workdir = workdir / "triple"
    su2_workdir.mkdir(exist_ok=True)
    
    # Copy mesh to SU2 working directory
    import shutil
    shutil.copy(mesh_path, su2_workdir / "nozzle.su2")
    
    config_path = su2_config.write(su2_workdir)
    solver = SU2Solver()
    su2_results = solver.run(config_path, su2_workdir, gamma=su2_config.gamma)
    mach_su2 = su2_results.exit_mach

    # Triple comparison
    triple_report = compare_three_way(
        mach_isentropic,
        mach_moc,
        mach_su2,
        tolerance=5.0,
    )

    print(f"  Isentropic Mach: {mach_isentropic:.4f}")
    print(f"  MoC Mach:        {mach_moc:.4f}")
    print(f"  SU2 Mach:        {mach_su2:.4f}")
    print(f"  Max error:       {triple_report.max_error_percent:.2f}%")
    print(f"  Result:          {'PASSED' if triple_report.passed else 'FAILED'}")

    # Two-way comparison (isentropic vs SU2)
    two_way = compare_results(
        mach_su2,
        nozzle_config.expansion_ratio,
        gamma=1.4,
        tolerance=5.0,
    )
    print(f"  Two-way error:   {two_way.mach_error_percent:.2f}%")

    # ================================================================
    # STEP 2: Parametric Sweeps
    # ================================================================
    print("\n[2/3] Parametric Sweeps...")
    print("-" * 60)

    sweep_config = SweepConfig(
        expansion_ratios=(4.0, 8.0, 12.0, 16.0, 20.0),
        chamber_pressures=(5e6, 10e6, 20e6, 50e6),
        throat_radii=(0.01, 0.025, 0.05, 0.1),
        reference_epsilon=12.0,
        reference_pc=10e6,
        reference_r_star=0.05,
        total_temperature=3500.0,
        gamma=1.4,
    )

    sweep_runner = SweepRunner(workdir / "sweep")
    sweep_results = sweep_runner.run_sweep(sweep_config)

    # Save sweep results
    sweep_csv_path = workdir / "sweep_results.csv"
    sweep_results.to_csv(sweep_csv_path)
    print(f"  Sweep results: {sweep_csv_path}")
    print(f"  Total cases: {len(sweep_results.cases)}")

    # Plot sweep
    sweep_plots = plot_sweep(sweep_results, images_dir)
    for plot_path in sweep_plots:
        print(f"  Plot: {plot_path}")

    # ================================================================
    # STEP 3: GCI Study
    # ================================================================
    print("\n[3/3] Grid Convergence Index Study...")
    print("-" * 60)

    # Mesh levels: coarse, medium, fine
    mesh_configs = {
        "coarse": {"n_axial": 100, "n_normal": 40},
        "medium": {"n_axial": 200, "n_normal": 80},
        "fine": {"n_axial": 400, "n_normal": 160},
    }

    gci_levels = {}
    for level_name, mesh_cfg in mesh_configs.items():
        level_dir = workdir / "gci" / level_name
        level_dir.mkdir(parents=True, exist_ok=True)

        mesh_path = generate_nozzle_mesh(
            nozzle_config,
            n_axial=mesh_cfg["n_axial"],
            n_normal=mesh_cfg["n_normal"],
            output_file=str(level_dir / "nozzle.su2"),
        )

        config_path = su2_config.write(level_dir)
        results = solver.run(config_path, level_dir, gamma=su2_config.gamma)

        # Approximate cell count from mesh settings
        n_cells = mesh_cfg["n_axial"] * mesh_cfg["n_normal"]

        gci_levels[level_name] = GCIMeshLevel(
            n_cells=n_cells,
            exit_mach=results.exit_mach,
            # Note: thrust coefficient GCI is not implemented in Phase 6
            # Use exit Mach as the primary validation metric
            thrust_coefficient=0.0,
        )

        print(
            f"  {level_name}: {n_cells} cells, "
            f"Mach={results.exit_mach:.4f}"
        )

    # Compute GCI
    if all(level.exit_mach > 0 for level in gci_levels.values()):
        gci_result = compute_gci(
            coarse=gci_levels["coarse"],
            medium=gci_levels["medium"],
            fine=gci_levels["fine"],
            refinement_ratio=2.0,
            safety_factor=1.25,
        )

        print(f"  GCI fine: {gci_result.gci_fine_mach:.3f}%")
        print(f"  Order: {gci_result.apparent_order:.2f}")
        print(f"  Asymptotic ratio: {gci_result.asymptotic_ratio_mach:.2f}")
        print(f"  Extrapolated Mach: {gci_result.extrapolated_mach:.4f}")
        print(f"  Result: {'PASSED' if gci_result.passed else 'FAILED'}")
    else:
        print("  WARNING: GCI skipped (zero Mach from one or more levels)")

    # ================================================================
    # SUMMARY
    # ================================================================
    print("\n" + "=" * 60)
    print("Phase 6 Complete!")
    print("=" * 60)
    print(f"Triple validation: {'PASSED' if triple_report.passed else 'FAILED'}")
    print(f"  Max error: {triple_report.max_error_percent:.2f}%")
    print(f"Sweep cases: {len(sweep_results.cases)}")
    print(f"  CSV: {sweep_csv_path}")
    if sweep_plots:
        print(f"  Plots: {len(sweep_plots)} files")

    if not triple_report.passed:
        print("\nWARNING: Triple validation failed.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
