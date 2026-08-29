"""NozzlePINN model: Fourier-feature MLP with residual blocks."""
import torch
import torch.nn as nn

from .config import PINNConfig


class FourierFeature(nn.Module):
    """Fourier feature encoding for spatial coordinates.

    Maps (x, y) -> sin/cos(2^k * x) for k=0..n_freqs-1.
    Provides rich positional encoding for coordinate inputs.
    """

    def __init__(self, n_freqs: int = 128) -> None:
        super().__init__()
        self.register_buffer("freqs", 2.0 ** torch.arange(n_freqs).float())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Encode spatial coordinates.

        Args:
            x: (B, 2) spatial coordinates

        Returns:
            (B, 4 * n_freqs) Fourier features
        """
        x_enc = x.unsqueeze(-1) * self.freqs  # (B, 2, n_freqs)
        return torch.cat(
            [torch.sin(x_enc), torch.cos(x_enc)], dim=-1
        ).reshape(x.shape[0], -1)


class ResidualBlock(nn.Module):
    """Residual block with GELU activation and skip connection."""

    def __init__(self, dim: int) -> None:
        super().__init__()
        self.linear1 = nn.Linear(dim, dim)
        self.linear2 = nn.Linear(dim, dim)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.act(self.linear2(self.act(self.linear1(x))))


class NozzlePINN(nn.Module):
    """Physics-Informed Neural Network for nozzle flow fields.

    Architecture:
        1. FourierFeature encoding for spatial (x, y) coordinates
        2. Parameter embedding for 7 nozzle/engine parameters
        3. 8 residual blocks (512 units each)
        4. Linear output head: 6 fields (Mach, P, T, rho, Vx, Vy)

    Input:
        x: (B,) axial coordinates
        y: (B,) radial coordinates
        params: (B, 7) normalized engine parameters

    Output:
        (B, 6) flow field values [Mach, P, T, rho, Vx, Vy]
    """

    def __init__(self, config: PINNConfig) -> None:
        super().__init__()
        self.config = config

        # Fourier feature encoding: (B, 2) -> (B, 4 * n_freqs)
        self.fourier = FourierFeature(config.fourier_features)
        n_encoded = 4 * config.fourier_features

        # Total input: Fourier features (4*128=512) + 7 params = 519
        total_input = n_encoded + 7

        # Input projection
        self.input_proj = nn.Linear(total_input, config.hidden_layers[0])

        # Residual blocks
        self.residuals = nn.ModuleList([
            ResidualBlock(config.hidden_layers[0]) for _ in range(8)
        ])

        # Output head: 6 fields
        self.output_head = nn.Linear(config.hidden_layers[0], config.n_outputs)

    def forward(
        self, x: torch.Tensor, y: torch.Tensor, params: torch.Tensor
    ) -> torch.Tensor:
        """Forward pass.

        Args:
            x: (B,) axial coordinates
            y: (B,) radial coordinates
            params: (B, 7) normalized engine parameters

        Returns:
            (B, 6) flow field predictions
        """
        spatial = torch.stack([x, y], dim=-1)  # (B, 2)
        fourier = self.fourier(spatial)  # (B, 4*n_freqs)
        h = self.input_proj(torch.cat([fourier, params], dim=-1))
        for block in self.residuals:
            h = block(h)
        return self.output_head(h)
