#!/usr/bin/env python3
"""Euler CFD for SpaceX Raptor SL."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import raptor_sl
from run_all_rockets import run_euler

settings = {
    "preset": raptor_sl, "Pt": 33.0e6, "Tt": 3500.0,
    "theta_n": 25, "ld": 1.0,
    "n_axial": 40, "n_normal": 20, "cfl": 0.1, "iterations": 5000,
}
result = run_euler("raptor-sl", settings)
print(f"Raptor SL: Mach={result['mach_sim']:.4f}, Error={result['error']:.2f}%")
