#!/usr/bin/env python3
"""RANS SST simulation of SpaceX Merlin 1D nozzle.

Uses fine mesh (120x100) with boundary layer refinement.
Requires Euler solution for comparison (run run_euler.py first).
"""
import sys
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import merlin_1d
from cfd.config import SU2NozzleConfig
from cfd.rans_config import SU2RANSConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver


def main() -> int:
    """Run RANS simulation pipeline.

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("RANS SST Simulation: SpaceX Merlin 1D")
    print("=" * 60)

    # Configuration
    nozzle_config = merlin_1d()

    rans_config = SU2RANSConfig(
        total_pressure=10e6,
        total_temperature=3500.0,
        cfl_number=0.1,
    )

    # Setup directories
    workdir = Path("output/rans")
    workdir.mkdir(parents=True, exist_ok=True)

    euler_dir = Path("output/euler")

    # Check if Euler solution exists (needed for reference)
    if not (euler_dir / "flow.vtu").exists():
        print("\nWARNING: Euler solution not found at output/euler/flow.vtu")
        print("  Run 'uv run python run_euler.py' first for comparison.")
        print("  Continuing with RANS-only simulation.\n")

    # Step 1: Generate RANS mesh
    print("\n[1/4] Generating RANS mesh (120x100 + BL refinement)...")
    rans_mesh = generate_nozzle_mesh(
        nozzle_config,
        n_axial=120,
        n_normal=100,
        output_file=str(workdir / "nozzle.su2"),
        rans_mode=True,
        plume_extension=False,  # TODO: enable after conformal plume is fixed
    )
    print(f"  RANS mesh: {rans_mesh}")

    # Step 2: Generate SU2 RANS config
    print("\n[2/4] Generating SU2 RANS config...")
    config_path = rans_config.write(workdir)
    print(f"  Config: {config_path}")

    # Step 3: Run RANS simulation
    print("\n[3/4] Running RANS SST simulation...")
    solver = SU2Solver()
    rans_results = solver.run(config_path, workdir)
    print(f"  Converged: {rans_results.converged}")
    print(f"  Exit Mach: {rans_results.exit_mach:.4f}")

    # Step 4: Report results
    print("\n[4/4] RANS Results Summary...")
    if (euler_dir / "flow.vtu").exists():
        # Compare with Euler if available
        euler_config = SU2NozzleConfig()
        euler_solver = SU2Solver()
        euler_results = euler_solver.parse_results(euler_dir)
        print(f"  Euler exit Mach: {euler_results.exit_mach:.4f}")
        print(f"  RANS exit Mach:  {rans_results.exit_mach:.4f}")
        diff = abs(euler_results.exit_mach - rans_results.exit_mach)
        pct = diff / euler_results.exit_mach * 100 if euler_results.exit_mach > 0 else 0.0
        print(f"  Difference:      {diff:.4f} ({pct:.2f}%)")
    else:
        print(f"  RANS exit Mach: {rans_results.exit_mach:.4f}")

    # Summary
    print("\n" + "=" * 60)
    print("RANS Simulation Complete!")
    print("=" * 60)
    print(f"Output: {workdir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
