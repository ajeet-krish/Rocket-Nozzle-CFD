#!/usr/bin/env python3
"""Triple validation and Grid Convergence Index study.

Compares isentropic theory, Method of Characteristics, and SU2 Euler.
Runs GCI study with 3 mesh levels (coarse/medium/fine).
"""
import sys
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import merlin_1d
from cfd.config import SU2NozzleConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver
from validation.isentropic import exit_mach_from_area_ratio
from validation.moc_solver import MoCSolver
from validation.compare import compare_results
from validation.triple import compare_three_way
from validation.gci import GCIMeshLevel, compute_gci


def main() -> int:
    """Run triple validation and GCI study.

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("Triple Validation + GCI Study")
    print("=" * 60)

    images_dir = Path("docs/assets/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Configuration
    nozzle_config = merlin_1d()

    su2_config = SU2NozzleConfig(
        total_pressure=10e6,
        total_temperature=3500.0,
        cfl_number=0.1,
        gamma=1.4,
    )

    workdir = Path("output/validation")
    workdir.mkdir(parents=True, exist_ok=True)

    solver = SU2Solver()

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
    shutil.copy(mesh_path, su2_workdir / "nozzle.su2")

    config_path = su2_config.write(su2_workdir)
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
    # STEP 2: GCI Study
    # ================================================================
    print("\n[2/3] Grid Convergence Index Study...")
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
    print("Validation Complete!")
    print("=" * 60)
    print(f"Triple validation: {'PASSED' if triple_report.passed else 'FAILED'}")
    print(f"  Max error: {triple_report.max_error_percent:.2f}%")

    if not triple_report.passed:
        print("\nWARNING: Triple validation failed.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
