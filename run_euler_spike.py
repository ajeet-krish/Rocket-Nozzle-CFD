#!/usr/bin/env python3
"""Quick Euler convergence spike for rocket nozzle CFD.

Uses coarse mesh (40x20) for fast validation. For full-resolution
Euler simulation, use run_euler.py instead.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import generic_test
from nozzle.geometry import generate_contour, plot_contour
from cfd.config import SU2NozzleConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver
from validation.isentropic import exit_mach_from_area_ratio
from validation.compare import compare_results
from viz.convergence import plot_convergence
from viz.mach_contour import plot_mach_contour


def main() -> int:
    """Run Euler convergence spike pipeline.

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("Euler Spike: Quick Convergence Test")
    print("=" * 60)

    # Configuration (generic_test preset for backward compatibility)
    nozzle_config = generic_test()

    su2_config = SU2NozzleConfig(
        total_pressure=10e6,
        total_temperature=3500.0,
        static_pressure=101325.0,
        gamma=1.4,
        iterations=5000,
        cfl_number=0.1,
    )

    # Setup directories
    workdir = Path("output/euler_spike")
    workdir.mkdir(parents=True, exist_ok=True)

    images_dir = Path("docs/assets/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate nozzle contour
    print("\n[1/6] Generating nozzle contour...")
    x, y = generate_contour(nozzle_config)
    print(f"  Contour: {len(x)} points, throat R={nozzle_config.throat_radius}m, exit R={nozzle_config.exit_radius:.4f}m")

    # Plot contour
    plot_contour(x, y, "Euler Spike - Nozzle Contour")
    print("  Saved: docs/assets/images/nozzle_contour.png")

    # Step 2: Generate mesh (coarse: 40x20, no plume for quick test)
    print("\n[2/6] Generating Gmsh mesh (40x20)...")
    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        n_axial=40,
        n_normal=20,
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

    # Convergence plot
    history_path = workdir / "history.csv"
    if history_path.exists():
        convergence_path = images_dir / "convergence.png"
        plot_convergence(history_path, convergence_path)
        print(f"  Saved: {convergence_path}")

    # Mach contour plot
    vtu_path = workdir / "flow.vtu"
    if vtu_path.exists():
        mach_path = images_dir / "mach_contour.png"
        plot_mach_contour(vtu_path, mach_path)
        print(f"  Saved: {mach_path}")

    # Summary
    print("\n" + "=" * 60)
    print("Euler Spike Complete!")
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
