"""NozzleDataset for loading SU2 VTU data and generating collocation points.

Loads VTU files from output/{engine}/euler/, interpolates onto a fixed grid,
and normalizes inputs/outputs for PINN training.
"""
import math
from pathlib import Path

import numpy as np

from .config import PINNConfig


class NozzleDataset:
    """Dataset for PINN training from SU2 simulation data.

    Responsibilities:
        1. Load VTU files via cfd.vtu_parser
        2. Interpolate scattered data onto a fixed grid
        3. Normalize inputs/outputs to [0, 1] or [-1, 1]
        4. Generate collocation points for PDE residual computation
    """

    def __init__(self, config: PINNConfig) -> None:
        self.config = config
        self._x_min = 0.0
        self._x_max = 1.0
        self._y_min = 0.0
        self._y_max = 1.0

    def load_vtu(self, vtu_path: Path) -> dict[str, np.ndarray]:
        """Load VTU file and extract flow fields.

        Args:
            vtu_path: Path to SU2 VTU solution file

        Returns:
            Dictionary with keys: x, y, mach, pressure, temperature,
            density, velocity_x, velocity_y
        """
        from cfd.vtu_parser import parse_vtu

        vtu_data = parse_vtu(vtu_path)
        coords = vtu_data.coordinates

        result: dict[str, np.ndarray] = {
            "x": coords[:, 0].astype(np.float64),
            "y": coords[:, 1].astype(np.float64),
        }

        # Map field names
        field_map = {
            "mach": vtu_data.mach,
            "pressure": vtu_data.pressure,
            "temperature": vtu_data.temperature,
            "density": vtu_data.density,
            "velocity_x": vtu_data.velocity_x,
            "velocity_y": vtu_data.velocity_y,
        }

        for name, arr in field_map.items():
            if arr is not None:
                result[name] = arr.astype(np.float64)
            else:
                result[name] = np.zeros_like(result["x"])

        return result

    def normalize_params(
        self,
        expansion_ratio: float,
        throat_radius: float,
        theta_n: float,
        total_pressure: float,
        total_temperature: float,
        gamma: float,
        nozzle_length_fraction: float,
    ) -> np.ndarray:
        """Normalize engine parameters to [0, 1] using config bounds.

        Args:
            expansion_ratio: Area ratio
            throat_radius: Throat radius (m)
            theta_n: Wall angle at throat (degrees)
            total_pressure: Chamber total pressure (Pa)
            total_temperature: Chamber total temperature (K)
            gamma: Ratio of specific heats
            nozzle_length_fraction: Bell length fraction

        Returns:
            (7,) normalized parameter vector
        """
        bounds = self.config.param_bounds
        params = np.array([
            expansion_ratio,
            throat_radius,
            theta_n,
            total_pressure,
            total_temperature,
            gamma,
            nozzle_length_fraction,
        ])
        param_keys = list(bounds.keys())

        normalized = np.zeros(7, dtype=np.float64)
        for i, key in enumerate(param_keys):
            lo, hi = bounds[key]
            normalized[i] = (params[i] - lo) / (hi - lo)

        return np.clip(normalized, 0.0, 1.0)

    def generate_collocation_points(
        self,
        x_range: tuple[float, float],
        y_range: tuple[float, float],
        n_samples: int | None = None,
    ) -> dict[str, np.ndarray]:
        """Generate uniform collocation points for PDE residual.

        Points are sampled uniformly in the nozzle domain for computing
        the Euler equation residuals during training.

        Args:
            x_range: (x_min, x_max) axial extent
            y_range: (y_min, y_max) radial extent
            n_samples: Number of points (default: config.n_training_samples)

        Returns:
            Dictionary with "x" and "y" arrays of shape (N,)
        """
        n = n_samples or self.config.n_training_samples
        rng = np.random.default_rng(42)
        x = rng.uniform(x_range[0], x_range[1], n).astype(np.float64)
        y = rng.uniform(y_range[0], y_range[1], n).astype(np.float64)
        return {"x": x, "y": y}

    def generate_grid(
        self,
        x_range: tuple[float, float],
        y_range: tuple[float, float],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Generate structured grid for evaluation.

        Args:
            x_range: (x_min, x_max)
            y_range: (y_min, y_max)

        Returns:
            (x_grid, y_grid, x_flat, y_flat) where grid shapes are
            (nx, ny) and flat shapes are (nx*ny,)
        """
        nx, ny = self.config.grid_resolution
        x = np.linspace(x_range[0], x_range[1], nx)
        y = np.linspace(y_range[0], y_range[1], ny)
        x_grid, y_grid = np.meshgrid(x, y, indexing="ij")
        return x_grid, y_grid, x_grid.ravel(), y_grid.ravel()
