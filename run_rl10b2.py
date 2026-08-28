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
    static_pressure=100.0,  # Near vacuum (RL10B-2 is upper stage engine)
    theta_n=20,  # Preset value - best result at 14% error
    ld=None,  # Use preset diverging_length (2.5m)
    euler_n_axial=80,
    euler_n_normal=40,
    euler_cfl=0.02,  # Lower CFL for stability
    euler_iterations=20000,
    rans_n_axial=80,
    rans_n_normal=40,
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
