#!/usr/bin/env python3
"""Euler CFD for RS-25 (Space Shuttle Main Engine)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import rs_25
from run_all_rockets import run_euler

settings = {
    "preset": rs_25, "Pt": 20.6e6, "Tt": 3570.0,
    "theta_n": 30, "ld": 0.7,
    "n_axial": 80, "n_normal": 40, "cfl": 0.05, "iterations": 10000,
}
result = run_euler("rs-25", settings)
print(f"RS-25: Mach={result['mach_sim']:.4f}, Error={result['error']:.2f}%")
