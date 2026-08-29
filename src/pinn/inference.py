"""PINNInference for fast nozzle flow field prediction.

Loads a trained PINN checkpoint and provides sub-100ms prediction
for arbitrary nozzle geometries and operating conditions.
"""
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import torch
except ImportError as exc:
    raise ImportError(
        "PyTorch is required for PINN inference. "
        "Install with: pip install 'rocket-nozzle-cfd[pinn]'"
    ) from exc

from .config import PINNConfig
from .model import NozzlePINN
from .data import NozzleDataset


@dataclass
class PredictionResult:
    """PINN prediction output."""
    mach: np.ndarray       # (nx, ny) Mach number field
    pressure: np.ndarray   # (nx, ny) static pressure
    temperature: np.ndarray  # (nx, ny) static temperature
    density: np.ndarray    # (nx, ny) density
    velocity_x: np.ndarray  # (nx, ny) x-velocity
    velocity_y: np.ndarray  # (nx, ny) y-velocity
    x_grid: np.ndarray     # (nx, ny) x-coordinates
    y_grid: np.ndarray     # (nx, ny) y-coordinates
    inference_time_ms: float


class PINNInference:
    """Fast inference engine for trained PINN models.

    Loads a checkpoint and provides field prediction in <100ms.
    """

    def __init__(
        self,
        checkpoint_path: Path,
        device: str = "cpu",
    ) -> None:
        """Load trained model from checkpoint.

        Args:
            checkpoint_path: Path to .pt checkpoint
            device: Inference device ("cpu" or "cuda")
        """
        self.device = torch.device(device)

        # Load model weights with weights_only=True (no pickle deserialization)
        checkpoint = torch.load(
            checkpoint_path, map_location=self.device, weights_only=True
        )

        # Load config from separate JSON file
        config_path = checkpoint_path.with_suffix('.json')
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}. "
                "Ensure the checkpoint was saved with the updated trainer."
            )
        with open(config_path) as f:
            config_dict = json.load(f)
        # Convert JSON lists back to tuples for frozen dataclass
        config_dict['hidden_layers'] = tuple(config_dict['hidden_layers'])
        config_dict['curriculum_phases'] = tuple(config_dict['curriculum_phases'])
        config_dict['grid_resolution'] = tuple(config_dict['grid_resolution'])
        config_dict['param_bounds'] = {
            k: tuple(v) for k, v in config_dict['param_bounds'].items()
        }
        self.config: PINNConfig = PINNConfig(**config_dict)

        self.dataset = NozzleDataset(self.config)
        self.model = NozzlePINN(self.config).to(self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

    def predict(
        self,
        expansion_ratio: float,
        throat_radius: float,
        theta_n: float,
        total_pressure: float,
        total_temperature: float,
        gamma: float,
        nozzle_length_fraction: float,
        x_range: tuple[float, float] | None = None,
        y_range: tuple[float, float] | None = None,
        grid_resolution: tuple[int, int] | None = None,
    ) -> PredictionResult:
        """Predict flow field for given nozzle parameters.

        Args:
            expansion_ratio: Area ratio A_exit/A_throat
            throat_radius: Throat radius (m)
            theta_n: Wall angle at throat (degrees)
            total_pressure: Chamber total pressure (Pa)
            total_temperature: Chamber total temperature (K)
            gamma: Ratio of specific heats
            nozzle_length_fraction: Bell length fraction
            x_range: Override (x_min, x_max) axial range
            y_range: Override (y_min, y_max) radial range
            grid_resolution: Override (nx, ny) grid size

        Returns:
            PredictionResult with all flow fields

        Raises:
            ValueError: If any parameter is outside the configured bounds
        """
        # Validate inputs against parameter bounds
        param_values = {
            'expansion_ratio': expansion_ratio,
            'throat_radius': throat_radius,
            'theta_n': theta_n,
            'total_pressure': total_pressure,
            'total_temperature': total_temperature,
            'gamma': gamma,
            'nozzle_length_fraction': nozzle_length_fraction,
        }
        for name, val in param_values.items():
            lo, hi = self.config.param_bounds[name]
            if not (lo <= val <= hi):
                raise ValueError(
                    f"Parameter '{name}'={val} is outside bounds [{lo}, {hi}]"
                )

        t0 = time.time()

        # Normalize parameters
        params_np = self.dataset.normalize_params(
            expansion_ratio, throat_radius, theta_n,
            total_pressure, total_temperature, gamma,
            nozzle_length_fraction,
        )

        # Generate evaluation grid
        if x_range is None:
            x_range = (0.0, 1.0)
        if y_range is None:
            y_range = (0.01, 1.0)

        nx, ny = grid_resolution or self.config.grid_resolution

        # Generate evaluation grid with the correct resolution
        x = np.linspace(x_range[0], x_range[1], nx)
        y = np.linspace(y_range[0], y_range[1], ny)
        x_grid, y_grid = np.meshgrid(x, y, indexing="ij")
        x_flat, y_flat = x_grid.ravel(), y_grid.ravel()

        # Create input tensors
        n_points = nx * ny
        x_t = torch.tensor(x_flat, dtype=torch.float32, device=self.device)
        y_t = torch.tensor(y_flat, dtype=torch.float32, device=self.device)
        params_t = torch.tensor(
            np.tile(params_np, (n_points, 1)),
            dtype=torch.float32,
            device=self.device,
        )

        # Run inference
        with torch.no_grad():
            pred = self.model(x_t, y_t, params_t).cpu().numpy()

        elapsed_ms = (time.time() - t0) * 1000

        return PredictionResult(
            mach=pred[:, 0].reshape(nx, ny),
            pressure=pred[:, 1].reshape(nx, ny),
            temperature=pred[:, 2].reshape(nx, ny),
            density=pred[:, 3].reshape(nx, ny),
            velocity_x=pred[:, 4].reshape(nx, ny),
            velocity_y=pred[:, 5].reshape(nx, ny),
            x_grid=x_grid,
            y_grid=y_grid,
            inference_time_ms=elapsed_ms,
        )

    def predict_from_nozzle_config(self, nozzle_config) -> PredictionResult:
        """Predict from a NozzleConfig object.

        Args:
            nozzle_config: NozzleConfig with geometry parameters

        Returns:
            PredictionResult with flow fields
        """
        return self.predict(
            expansion_ratio=nozzle_config.expansion_ratio,
            throat_radius=nozzle_config.throat_radius,
            theta_n=30.0,
            total_pressure=10e6,
            total_temperature=3500.0,
            gamma=1.4,
            nozzle_length_fraction=nozzle_config.nozzle_length_fraction,
        )
