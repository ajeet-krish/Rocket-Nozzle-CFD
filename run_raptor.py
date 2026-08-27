#!/usr/bin/env python3
"""SpaceX Raptor SL per-engine CFD pipeline."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import raptor_sl
from pipeline.engine_config import EngineConfig, PipelineStage
from pipeline.stages import run_full_pipeline

CONFIG = EngineConfig(
    name="raptor-sl",
    label="Raptor SL",
    preset_fn=raptor_sl,
    total_pressure=33.0e6,
    total_temperature=3500.0,
    theta_n=25,
    ld=1.0,
    euler_n_axial=40,
    euler_n_normal=20,
    euler_cfl=0.1,
    euler_iterations=5000,
    rans_cfl=0.05,
    rans_iterations=10000,
    sweep_expansion_ratios=(20.0, 28.0, 34.0, 40.0, 50.0),
    sweep_chamber_pressures=(10e6, 20e6, 33e6, 50e6),
    sweep_throat_radii=(0.05, 0.0825, 0.1, 0.15),
)


def main() -> int:
    """Run Raptor SL pipeline."""
    parser = argparse.ArgumentParser(description="Raptor SL CFD pipeline")
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
