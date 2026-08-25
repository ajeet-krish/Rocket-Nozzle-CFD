"""MoC solver configuration and results."""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class MoCConfig:
    """Configuration for nozzle flow solver.

    Attributes:
        gamma: Ratio of specific heats
        dx: Step size along axis (m)
    """
    gamma: float = 1.4
    dx: float = 0.001


@dataclass
class MoCResults:
    """Results from nozzle flow solver.

    Attributes:
        x: Axial coordinates (m)
        mach: Mach number distribution
        theta: Flow angle (radians)
        nu: Prandtl-Meyer angle (radians)
    """
    x: np.ndarray = field(default_factory=lambda: np.array([]))
    mach: np.ndarray = field(default_factory=lambda: np.array([]))
    theta: np.ndarray = field(default_factory=lambda: np.array([]))
    nu: np.ndarray = field(default_factory=lambda: np.array([]))
