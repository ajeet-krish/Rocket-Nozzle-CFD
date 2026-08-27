#!/usr/bin/env python3
"""Euler CFD for RL10B-2 (Delta IV Upper Stage)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import rl10b_2
from run_all_rockets import run_euler

settings = {
    "preset": rl10b_2, "Pt": 4.2e6, "Tt": 2200.0,
    "theta_n": 25, "ld": 1.5,
    "n_axial": 120, "n_normal": 60, "cfl": 0.03, "iterations": 15000,
}
result = run_euler("rl10B-2", settings)
print(f"RL10B-2: Mach={result['mach_sim']:.4f}, Error={result['error']:.2f}%")
