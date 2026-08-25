#!/usr/bin/env python3
"""Phase 4: RANS simulation and post-processing."""
import sys
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.config import NozzleConfig
from cfd.config import SU2NozzleConfig
from cfd.rans_config import SU2RANSConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver
from cfd.vtu_parser import parse_vtu
from viz.postprocessing import plot_wall_pressure, plot_shock_diamonds
from viz.comparison import plot_mach_comparison, generate_comparison_report


def main() -> None:
    print("=" * 60)
    print("Phase 4: RANS + Post-Processing")
    print("=" * 60)

    # Configuration
    nozzle_config = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)

    euler_config = SU2NozzleConfig(total_pressure=10e6, total_temperature=3500.0, cfl_number=0.1)
    rans_config = SU2RANSConfig(total_pressure=10e6, total_temperature=3500.0, cfl_number=0.1)

    workdir = Path("output/phase4")
    workdir.mkdir(parents=True, exist_ok=True)

    images_dir = Path("docs/assets/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Generate Euler mesh (coarser)
    print("\n[1/4] Generating Euler mesh...")
    euler_mesh = generate_nozzle_mesh(
        nozzle_config,
        n_axial=20,
        n_normal=10,
        output_file=str(workdir / "euler" / "nozzle.su2"),
        rans_mode=False,
    )
    print(f"  Euler mesh: {euler_mesh}")

    # Generate RANS mesh (finer with boundary layer)
    print("\n[2/4] Generating RANS mesh...")
    rans_mesh = generate_nozzle_mesh(
        nozzle_config,
        n_axial=40,
        n_normal=20,
        output_file=str(workdir / "rans" / "nozzle.su2"),
        rans_mode=True,
    )
    print(f"  RANS mesh: {rans_mesh}")

    # Run Euler (reference)
    print("\n[3/4] Running Euler simulation...")
    solver = SU2Solver()
    euler_dir = workdir / "euler"
    euler_dir.mkdir(exist_ok=True)
    euler_config_path = euler_config.write(euler_dir)
    euler_results = solver.run(euler_config_path, euler_dir)
    print(f"  Converged: {euler_results.converged}")
    print(f"  Exit Mach: {euler_results.exit_mach:.4f}")

    # Run RANS
    print("\n[4/4] Running RANS simulation...")
    rans_dir = workdir / "rans"
    rans_dir.mkdir(exist_ok=True)
    rans_config_path = rans_config.write(rans_dir)
    rans_results = solver.run(rans_config_path, rans_dir)
    print(f"  Converged: {rans_results.converged}")
    print(f"  Exit Mach: {rans_results.exit_mach:.4f}")

    # Post-processing
    print("\n[5/5] Generating plots...")

    # Wall pressure
    if (rans_dir / "flow.vtu").exists():
        try:
            rans_data = parse_vtu(rans_dir / "flow.vtu")
            plot_wall_pressure(
                rans_data.coordinates[:, 0],
                rans_data.pressure if rans_data.pressure is not None else rans_data.coordinates[:, 0] * 0,
                images_dir / "wall_pressure.png",
            )
            print("  Saved: wall_pressure.png")

            # Shock diamonds
            plot_shock_diamonds(rans_data, images_dir / "shock_diamonds.png")
            print("  Saved: shock_diamonds.png")
        except Exception as e:
            print(f"  Warning: Could not parse RANS VTU: {e}")

    # Copy VTU files for ParaView
    if (euler_dir / "flow.vtu").exists():
        shutil.copy(euler_dir / "flow.vtu", images_dir / "phase4_euler_flow.vtu")
        print("  Copied: phase4_euler_flow.vtu")
    
    if (rans_dir / "flow.vtu").exists():
        shutil.copy(rans_dir / "flow.vtu", images_dir / "phase4_rans_flow.vtu")
        print("  Copied: phase4_rans_flow.vtu")

    # Comparison
    if (euler_dir / "flow.vtu").exists() and (rans_dir / "flow.vtu").exists():
        try:
            plot_mach_comparison(
                euler_dir / "flow.vtu",
                rans_dir / "flow.vtu",
                images_dir / "mach_comparison.png",
            )
            print("  Saved: mach_comparison.png")

            generate_comparison_report(
                euler_results.exit_mach,
                rans_results.exit_mach,
                Path("docs/euler_vs_rans.md"),
            )
            print("  Saved: docs/euler_vs_rans.md")
        except Exception as e:
            print(f"  Warning: Could not generate comparison: {e}")

    print("\n" + "=" * 60)
    print("Phase 4 Complete!")
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
