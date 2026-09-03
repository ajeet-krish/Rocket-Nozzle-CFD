#!/usr/bin/env python3
"""SpaceX Merlin 1D per-engine CFD pipeline."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import merlin_1d
from pipeline.engine_config import EngineConfig, PipelineStage
from pipeline.stages import run_full_pipeline

CONFIG = EngineConfig(
    name="merlin-1d",
    label="Merlin 1D",
    preset_fn=merlin_1d,
    total_pressure=9.7e6,
    total_temperature=3600.0,
    theta_n=30,
    ld=0.7,
    # Nozzle Euler mesh
    euler_n_axial=40,
    euler_n_normal=20,
    euler_cfl=0.1,
    euler_iterations=5000,
    # RANS mesh
    rans_n_axial=80,
    rans_n_normal=40,
    rans_cfl=0.05,
    rans_iterations=10000,
    # Extended plume domain for shock diamonds
    # 17 exit diameters downstream (11.2m), 3 exit radii wide (0.99m)
    plume_n_axial=200,
    plume_n_normal=60,
    plume_cfl=0.05,
    plume_iterations=10000,
    plume_length_ratio=136.0,   # 11.2m / 0.0825m throat_radius (trimmed 2m from 160)
    plume_radius_ratio=3.0,     # 3x exit radius (0.99m)
    sweep_expansion_ratios=(8.0, 12.0, 16.0, 20.0, 24.0),
    sweep_chamber_pressures=(5e6, 9.7e6, 15e6, 20e6),
    sweep_throat_radii=(0.05, 0.0825, 0.1, 0.15),
    multi_curve=False,  # Single curve for consistent mesh visualization
)


def main() -> int:
    """Run Merlin 1D pipeline."""
    parser = argparse.ArgumentParser(description="Merlin 1D CFD pipeline")
    parser.add_argument(
        "--step",
        choices=[s.value for s in PipelineStage],
        default=None,
        help="Run a single pipeline step (default: all)",
    )
    args = parser.parse_args()

    if args.step:
        stages = [PipelineStage(args.step)]
    else:
        stages = None

    return run_full_pipeline(CONFIG, stages)


if __name__ == "__main__":
    sys.exit(main())
