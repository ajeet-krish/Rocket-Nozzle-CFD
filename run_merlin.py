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
    euler_n_axial=40,
    euler_n_normal=20,
    euler_cfl=0.1,
    euler_iterations=5000,
    rans_cfl=0.05,
    rans_iterations=10000,
    sweep_expansion_ratios=(8.0, 12.0, 16.0, 20.0, 24.0),
    sweep_chamber_pressures=(5e6, 9.7e6, 15e6, 20e6),
    sweep_throat_radii=(0.05, 0.0825, 0.1, 0.15),
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
