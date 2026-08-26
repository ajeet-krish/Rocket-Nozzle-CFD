#!/usr/bin/env python3
"""Full Euler simulation of converging-diverging rocket nozzle.

Uses fine mesh (60x30) for accurate results.
Validates against isentropic theory.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour, plot_contour
from cfd.config import SU2NozzleConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver
from validation.isentropic import exit_mach_from_area_ratio
from validation.compare import compare_results
from viz.convergence import plot_convergence
from viz.mach_contour import plot_mach_contour


def main() -> int:
    """Run full Euler simulation.

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("Full Euler Simulation: Rocket Nozzle")
    print("=" * 60)

    # Configuration: epsilon=16, Merlin 1D conditions
    nozzle_config = NozzleConfig(
        throat_radius=0.05,
        expansion_ratio=16.0,
        converging_length=0.1,
        diverging_length=0.5,
        num_points=200,
    )

    su2_config = SU2NozzleConfig(
        total_pressure=9.7e6,
        total_temperature=3600.0,
        static_pressure=101325.0,
        gamma=1.4,
        iterations=5000,
        cfl_number=0.1,
    )

    # Setup directories
    workdir = Path("output/euler")
    workdir.mkdir(parents=True, exist_ok=True)

    images_dir = workdir / "plots"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate nozzle contour
    print("\n[1/6] Generating nozzle contour...")
    x, y = generate_contour(nozzle_config)
    print(f"  Contour: {len(x)} points, throat R={nozzle_config.throat_radius}m, exit R={nozzle_config.exit_radius:.4f}m")

    plot_contour(x, y, "Euler - Nozzle Contour")
    print("  Saved: nozzle_contour.png")

    # Step 2: Generate mesh (fine: 60x30, no plume for stability)
    print("\n[2/6] Generating Gmsh mesh (60x30)...")
    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        n_axial=60,
        n_normal=30,
        output_file=str(workdir / "nozzle.su2"),
        plume_extension=False,
    )
    print(f"  Mesh: {mesh_path}")

    # Step 3: Generate SU2 config
    print("\n[3/6] Generating SU2 config...")
    config_path = su2_config.write(workdir)
    print(f"  Config: {config_path}")

    # Step 4: Run SU2
    print("\n[4/6] Running SU2 Euler simulation...")
    solver = SU2Solver()
    results = solver.run(config_path, workdir, timeout=1800, gamma=su2_config.gamma)
    print(f"  Converged: {results.converged}")
    print(f"  Iterations: {results.iterations}")
    print(f"  Exit Mach: {results.exit_mach:.4f}")

    # Step 5: Validate against isentropic
    print("\n[5/6] Validating against isentropic theory...")
    theory_exit_mach = exit_mach_from_area_ratio(nozzle_config.expansion_ratio, 1.4)
    report = compare_results(
        results.exit_mach,
        nozzle_config.expansion_ratio,
        gamma=1.4,
        tolerance=5.0,
    )
    print(f"  Theory exit Mach: {theory_exit_mach:.4f}")
    print(f"  Simulation exit Mach: {results.exit_mach:.4f}")
    print(f"  Error: {report.mach_error_percent:.2f}%")
    print(f"  Result: {'PASSED' if report.passed else 'FAILED'}")

    # Step 6: Generate plots
    print("\n[6/6] Generating plots...")

    history_path = workdir / "history.csv"
    if history_path.exists():
        convergence_path = images_dir / "convergence.png"
        plot_convergence(history_path, convergence_path)
        print(f"  Saved: {convergence_path}")

    vtu_path = workdir / "flow.vtu"
    if vtu_path.exists():
        mach_path = images_dir / "mach_contour.png"
        plot_mach_contour(vtu_path, mach_path, nozzle_config=nozzle_config)
        print(f"  Saved: {mach_path}")

    # Summary
    print("\n" + "=" * 60)
    print("Full Euler Simulation Complete!")
    print("=" * 60)
    print(f"Exit Mach (SU2): {results.exit_mach:.4f}")
    print(f"Exit Mach (Theory): {theory_exit_mach:.4f}")
    print(f"Error: {report.mach_error_percent:.2f}%")
    print(f"Validation: {'PASSED' if report.passed else 'FAILED'}")

    if not report.passed:
        print("\nWARNING: Validation failed. Check SU2 configuration and mesh.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
