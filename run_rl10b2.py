#!/usr/bin/env python3
"""RL10B-2 (Delta IV Upper Stage) per-engine CFD pipeline."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import rl10b_2
from pipeline.engine_config import EngineConfig, PipelineStage
from pipeline.stages import run_full_pipeline

CONFIG = EngineConfig(
    name="rl10B-2",
    label="RL10B-2",
    preset_fn=rl10b_2,
    total_pressure=4.2e6,
    total_temperature=2200.0,
    theta_n=25,
    ld=1.5,
    euler_n_axial=120,
    euler_n_normal=60,
    euler_cfl=0.03,
    euler_iterations=15000,
    rans_n_axial=120,
    rans_n_normal=60,
    rans_cfl=0.02,
    rans_iterations=20000,
    sweep_expansion_ratios=(150.0, 200.0, 285.0, 350.0, 400.0),
    sweep_chamber_pressures=(2e6, 3e6, 4.2e6, 6e6),
    sweep_throat_radii=(0.05, 0.065, 0.077, 0.10),
)


def main() -> int:
    """Run RL10B-2 pipeline."""
    parser = argparse.ArgumentParser(description="RL10B-2 CFD pipeline")
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
