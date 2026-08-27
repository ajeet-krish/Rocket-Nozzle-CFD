#!/usr/bin/env python3
"""Euler CFD for SpaceX Merlin 1D."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import merlin_1d
from run_all_rockets import run_euler

settings = {
    "preset": merlin_1d, "Pt": 9.7e6, "Tt": 3600.0,
    "theta_n": 30, "ld": 0.7,
    "n_axial": 40, "n_normal": 20, "cfl": 0.1, "iterations": 5000,
}
result = run_euler("merlin-1d", settings)
print(f"Merlin 1D: Mach={result['mach_sim']:.4f}, Error={result['error']:.2f}%")
