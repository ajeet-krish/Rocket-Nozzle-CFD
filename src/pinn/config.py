"""PINN configuration for nozzle flow prediction."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PINNConfig:
    """Configuration for Physics-Informed Neural Network.

    Attributes:
        hidden_layers: Tuple of hidden layer widths
        fourier_features: Number of Fourier feature frequencies
        activation: Activation function name
        n_inputs: Total input dimension (spatial + params after encoding)
        n_outputs: Number of output fields
        grid_resolution: (nx, ny) for collocation grid
        learning_rate: Adam learning rate
        weight_decay: L2 regularization
        max_epochs: Maximum training epochs
        curriculum_phases: Epoch boundaries for 3-phase curriculum
        lambda_data: Weight for data loss
        lambda_pde: Weight for PDE residual loss
        lambda_bc: Weight for boundary condition loss
        param_bounds: Parameter normalization ranges
        n_training_samples: Number of training collocation samples
        n_validation_samples: Number of validation samples
    """
    hidden_layers: tuple[int, ...] = (512, 512, 512, 512, 512, 512, 512, 512)
    fourier_features: int = 128
    activation: str = "gelu"
    n_inputs: int = 9  # 2 spatial + 7 params (after Fourier encoding)
    n_outputs: int = 6  # Mach, P, T, rho, Vx, Vy
    grid_resolution: tuple[int, int] = (64, 32)
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    max_epochs: int = 1000
    curriculum_phases: tuple[int, ...] = (200, 500, 300)
    lambda_data: float = 1.0
    lambda_pde: float = 0.1
    lambda_bc: float = 0.5
    param_bounds: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "expansion_ratio": (4.0, 300.0),
        "throat_radius": (0.02, 0.2),
        "theta_n": (15.0, 45.0),
        "total_pressure": (1e6, 50e6),
        "total_temperature": (2000.0, 4500.0),
        "gamma": (1.2, 1.67),
        "nozzle_length_fraction": (0.4, 1.0),
    })
    n_training_samples: int = 300
    n_validation_samples: int = 50
