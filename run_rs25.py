#!/usr/bin/env python3
"""RS-25 (Space Shuttle Main Engine) per-engine CFD pipeline."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import rs_25
from pipeline.engine_config import EngineConfig, PipelineStage
from pipeline.stages import run_full_pipeline

CONFIG = EngineConfig(
    name="rs-25",
    label="RS-25",
    preset_fn=rs_25,
    total_pressure=20.6e6,
    total_temperature=3570.0,
    static_pressure=100.0,  # Near vacuum (RS-25 designed for vacuum operation)
    theta_n=30,
    ld=None,  # Use preset diverging_length (2.0m)
    euler_n_axial=40,
    euler_n_normal=20,
    euler_cfl=0.05,
    euler_iterations=10000,
    rans_n_axial=40,
    rans_n_normal=20,
    rans_cfl=0.03,
    rans_iterations=15000,
    sweep_expansion_ratios=(40.0, 60.0, 77.5, 100.0, 120.0),
    sweep_chamber_pressures=(10e6, 15e6, 20.6e6, 30e6),
    sweep_throat_radii=(0.08, 0.10, 0.136, 0.18),
)


def main() -> int:
    """Run RS-25 pipeline."""
    parser = argparse.ArgumentParser(description="RS-25 CFD pipeline")
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
