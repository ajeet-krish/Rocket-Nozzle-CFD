#!/usr/bin/env python3
"""Parametric sweeps for rocket nozzle design space.

Sweeps expansion ratio, chamber pressure, and throat radius
to map nozzle performance across the design space.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sweep.config import SweepConfig
from sweep.runner import SweepRunner
from sweep.plotter import plot_sweep


def main() -> int:
    """Run parametric sweep pipeline.

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("Parametric Sweeps: Rocket Nozzle Design Space")
    print("=" * 60)

    # Setup directories
    images_dir = Path("docs/assets/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    workdir = Path("output/sweeps")
    workdir.mkdir(parents=True, exist_ok=True)

    # Step 1: Configure sweep
    print("\n[1/3] Configuring parametric sweeps...")
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
    print(f"  Expansion ratios: {sweep_config.expansion_ratios}")
    print(f"  Chamber pressures: {[p/1e6 for p in sweep_config.chamber_pressures]} MPa")
    print(f"  Throat radii: {sweep_config.throat_radii} m")

    # Step 2: Run sweep
    print("\n[2/3] Running parametric sweeps...")
    sweep_runner = SweepRunner(workdir)
    sweep_results = sweep_runner.run_sweep(sweep_config)

    # Save sweep results
    sweep_csv_path = workdir / "sweep_results.csv"
    sweep_results.to_csv(sweep_csv_path)
    print(f"  Sweep results: {sweep_csv_path}")
    print(f"  Total cases: {len(sweep_results.cases)}")

    # Step 3: Plot results
    print("\n[3/3] Generating sweep plots...")
    sweep_plots = plot_sweep(sweep_results, images_dir)
    for plot_path in sweep_plots:
        print(f"  Plot: {plot_path}")

    # Summary
    print("\n" + "=" * 60)
    print("Parametric Sweeps Complete!")
    print("=" * 60)
    print(f"Sweep cases: {len(sweep_results.cases)}")
    print(f"  CSV: {sweep_csv_path}")
    if sweep_plots:
        print(f"  Plots: {len(sweep_plots)} files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
