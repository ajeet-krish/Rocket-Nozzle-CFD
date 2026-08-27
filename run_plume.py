#!/usr/bin/env python3
"""Plume extension simulation with shock diamond visualization.

Uses conformal plume mesh to capture external shock structure
downstream of the nozzle exit. Generates Mach contour with shock
diamonds and validates against isentropic theory.
"""
import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import merlin_1d
from cfd.config import SU2NozzleConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver
from validation.isentropic import exit_mach_from_area_ratio
from validation.compare import compare_results
from viz.convergence import plot_convergence
from viz.mach_contour import plot_mach_contour
from viz.postprocessing import plot_shock_diamonds


def main() -> int:
    """Run plume simulation.

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("Plume Extension: Shock Diamond Visualization")
    print("=" * 60)

    # Configuration (Merlin 1D preset)
    nozzle_config = merlin_1d()

    su2_config = SU2NozzleConfig(
        total_pressure=9.7e6,
        total_temperature=3600.0,
        static_pressure=101325.0,
        gamma=1.4,
        iterations=5000,
        cfl_number=0.05,
        farfield_marker="farfield",
    )

    # Setup directories
    workdir = Path("output/plume")
    workdir.mkdir(parents=True, exist_ok=True)

    plots_dir = workdir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate mesh with plume extension
    print("\n[1/6] Generating mesh with plume extension...")
    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        n_axial=40,
        n_normal=20,
        output_file=str(workdir / "nozzle.su2"),
        plume_extension=True,
        plume_length_ratio=10.0,
        plume_radius_ratio=2.0,
    )
    print(f"  Mesh: {mesh_path}")

    # Step 2: Generate SU2 config with farfield BC
    print("\n[2/6] Generating SU2 config with farfield BC...")
    config_path = su2_config.write(workdir)
    print(f"  Config: {config_path}")

    # Step 3: Run SU2
    print("\n[3/6] Running SU2 Euler simulation...")
    solver = SU2Solver()
    results = solver.run(config_path, workdir, timeout=1800, gamma=su2_config.gamma)
    print(f"  Converged: {results.converged}")
    print(f"  Iterations: {results.iterations}")
    print(f"  Exit Mach: {results.exit_mach:.4f}")

    # Step 4: Validate
    print("\n[4/6] Validating against isentropic theory...")
    theory_exit_mach = exit_mach_from_area_ratio(nozzle_config.expansion_ratio, 1.4)
    
    # For plume simulation, measure Mach at nozzle exit plane (not plume outlet)
    from cfd.vtu_parser import parse_vtu
    vtu_path = workdir / "flow.vtu"
    if vtu_path.exists():
        vtu_data = parse_vtu(vtu_path)
        # Nozzle exit at x = diverging_length
        exit_x = nozzle_config.computed_diverging_length
        exit_mask = np.abs(vtu_data.coordinates[:, 0] - exit_x) < 0.05
        if exit_mask.any():
            sim_exit_mach = float(vtu_data.mach[exit_mask].mean())
        else:
            sim_exit_mach = results.exit_mach
    else:
        sim_exit_mach = results.exit_mach
    
    report = compare_results(
        sim_exit_mach,
        nozzle_config.expansion_ratio,
        gamma=1.4,
        tolerance=5.0,
    )
    print(f"  Theory exit Mach: {theory_exit_mach:.4f}")
    print(f"  Simulation exit Mach: {sim_exit_mach:.4f}")
    print(f"  Error: {report.mach_error_percent:.2f}%")
    print(f"  Result: {'PASSED' if report.passed else 'FAILED'}")

    # Step 5: Generate plots
    print("\n[5/6] Generating plots...")

    history_path = workdir / "history.csv"
    if history_path.exists():
        convergence_path = plots_dir / "convergence.png"
        plot_convergence(history_path, convergence_path)
        print(f"  Saved: {convergence_path}")

    vtu_path = workdir / "flow.vtu"
    if vtu_path.exists():
        mach_path = plots_dir / "mach_contour.png"
        plot_mach_contour(vtu_path, mach_path, nozzle_config=nozzle_config)
        print(f"  Saved: {mach_path}")

        # Shock diamonds
        from cfd.vtu_parser import parse_vtu
        vtu_data = parse_vtu(vtu_path)
        shock_path = plots_dir / "shock_diamonds.png"
        plot_shock_diamonds(vtu_data, shock_path)
        print(f"  Saved: {shock_path}")

    # Summary
    print("\n" + "=" * 60)
    print("Plume Simulation Complete!")
    print("=" * 60)
    print(f"Exit Mach (at nozzle exit): {sim_exit_mach:.4f}")
    print(f"Theory: {theory_exit_mach:.4f}")
    print(f"Error: {report.mach_error_percent:.2f}%")
    print(f"Validation: {'PASSED' if report.passed else 'FAILED'}")

    if not report.passed:
        print("\nWARNING: Validation failed. Check SU2 configuration and mesh.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
