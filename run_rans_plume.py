#!/usr/bin/env python3
"""RANS plume simulation with viscous shock diamond visualization.

Uses RANS SST k-omega with plume extension to capture viscous effects
on shock diamond structure. Compares with Euler plume results.
"""
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import merlin_1d
from cfd.rans_config import SU2RANSConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver
from cfd.vtu_parser import parse_vtu
from viz.mach_contour import plot_mach_contour
from viz.postprocessing import plot_shock_diamonds


def main() -> int:
    """Run RANS plume simulation pipeline.

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("RANS Plume: Viscous Shock Diamond Visualization")
    print("=" * 60)

    nozzle_config = merlin_1d()

    rans_config = SU2RANSConfig(
        total_pressure=9.7e6,
        total_temperature=3600.0,
        static_pressure=101325.0,
        cfl_number=0.05,
        iterations=10000,
        farfield_marker="farfield",
    )

    workdir = Path("output/rans_plume")
    workdir.mkdir(parents=True, exist_ok=True)

    plots_dir = workdir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate mesh with plume extension
    print("\n[1/5] Generating RANS plume mesh...")
    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        n_axial=40,
        n_normal=20,
        output_file=str(workdir / "nozzle.su2"),
        rans_mode=False,
        plume_extension=True,
        plume_length_ratio=10.0,
        plume_radius_ratio=2.0,
    )
    print(f"  Mesh: {mesh_path}")

    # Step 2: Generate SU2 RANS config
    print("\n[2/5] Generating SU2 RANS config...")
    config_path = rans_config.write(workdir)
    print(f"  Config: {config_path}")

    # Step 3: Run RANS simulation
    print("\n[3/5] Running RANS SST simulation...")
    solver = SU2Solver()
    results = solver.run(config_path, workdir, timeout=3600)
    print(f"  Converged: {results.converged}")
    print(f"  Iterations: {results.iterations}")
    print(f"  Exit Mach: {results.exit_mach:.4f}")

    # Step 4: Generate plots
    print("\n[4/5] Generating plots...")
    vtu_path = workdir / "flow.vtu"
    if vtu_path.exists():
        vtu_data = parse_vtu(vtu_path)

        mach_path = plots_dir / "mach_contour_rans_plume.png"
        plot_mach_contour(vtu_path, mach_path, nozzle_config=nozzle_config)
        print(f"  Saved: {mach_path}")

        shock_path = plots_dir / "shock_diamonds_rans_plume.png"
        plot_shock_diamonds(vtu_data, shock_path)
        print(f"  Saved: {shock_path}")

    # Step 5: Compare with Euler plume
    print("\n[5/5] Comparison with Euler plume...")
    euler_plume_path = Path("output/plume/flow.vtu")
    if euler_plume_path.exists() and vtu_path.exists():
        euler_data = parse_vtu(euler_plume_path)
        rans_data = parse_vtu(vtu_path)

        exit_x = nozzle_config.diverging_length
        euler_exit = np.abs(euler_data.coordinates[:, 0] - exit_x) < 0.05
        rans_exit = np.abs(rans_data.coordinates[:, 0] - exit_x) < 0.05

        if euler_exit.any() and rans_exit.any():
            euler_mach = float(euler_data.mach[euler_exit].mean())
            rans_mach = float(rans_data.mach[rans_exit].mean())
            print(f"  Euler plume exit Mach: {euler_mach:.4f}")
            print(f"  RANS plume exit Mach:  {rans_mach:.4f}")
            diff = abs(euler_mach - rans_mach)
            pct = diff / euler_mach * 100 if euler_mach > 0 else 0.0
            print(f"  Difference: {diff:.4f} ({pct:.2f}%)")
        else:
            print("  Could not extract exit Mach for comparison.")
    else:
        print("  Euler plume results not found at output/plume/flow.vtu")
        print("  Run 'uv run python run_plume.py' first for comparison.")

    print("\n" + "=" * 60)
    print("RANS Plume Complete!")
    print("=" * 60)
    print(f"Output: {workdir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
