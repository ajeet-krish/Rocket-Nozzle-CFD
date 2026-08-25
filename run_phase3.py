#!/usr/bin/env python3
"""Phase 3: SU2 Euler simulation for rocket nozzle."""
import sys
from pathlib import Path

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
    """Run Phase 3 simulation pipeline."""
    print("=" * 60)
    print("Phase 3: SU2 Euler Simulation")
    print("=" * 60)

    # Configuration
    nozzle_config = NozzleConfig(
        throat_radius=0.05,
        expansion_ratio=12.0,
        converging_length=0.1,
        diverging_length=0.5,
        num_points=200,
    )

    su2_config = SU2NozzleConfig(
        total_pressure=10e6,
        total_temperature=3500.0,
        static_pressure=101325.0,
        gamma=1.4,
        iterations=5000,
        cfl_number=5.0,
    )

    # Setup directories
    workdir = Path("output/phase3")
    workdir.mkdir(parents=True, exist_ok=True)

    images_dir = Path("docs/assets/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate nozzle contour
    print("\n[1/6] Generating nozzle contour...")
    x, y = generate_contour(nozzle_config)
    print(
        f"  Contour: {len(x)} points, "
        f"throat R={nozzle_config.throat_radius}m, "
        f"exit R={nozzle_config.exit_radius:.4f}m"
    )

    # Plot contour
    plot_contour(x, y, "Phase 3 - Rao Bell Nozzle Contour")
    print("  Saved: docs/assets/images/nozzle_contour.png")

    # Step 2: Generate mesh
    print("\n[2/6] Generating Gmsh mesh...")
    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        output_file=str(workdir / "nozzle.su2"),
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
    print("Phase 3 Complete!")
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
