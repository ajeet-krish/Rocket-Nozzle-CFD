"""PINNTrainer with 3-phase curriculum training.

Phase 1: Data fitting only (epochs 0 to phase1_end)
Phase 2: Add physics constraints (epochs phase1_end to phase2_end)
Phase 3: Fine-tune with full physics (remaining epochs)
"""
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.optim import Adam
    from torch.optim.lr_scheduler import CosineAnnealingLR
except ImportError as exc:
    raise ImportError(
        "PyTorch is required for PINN training. "
        "Install with: pip install 'rocket-nozzle-cfd[pinn]'"
    ) from exc

from .config import PINNConfig
from .model import NozzlePINN
from .physics import EulerResiduals


@dataclass
class TrainResult:
    """Training result summary."""
    epochs_trained: int
    final_loss: float
    final_data_loss: float
    final_pde_loss: float
    final_bc_loss: float
    training_time_s: float
    loss_history: list[float]


class PINNTrainer:
    """Trains a NozzlePINN with 3-phase curriculum learning.

    Curriculum phases:
        Phase 1: Data loss only (lambda_pde=0, lambda_bc=0)
        Phase 2: Data + physics (lambda_pde ramps up)
        Phase 3: Full physics (all lambdas active)
    """

    def __init__(
        self,
        model: NozzlePINN,
        config: PINNConfig,
        device: str = "cpu",
    ) -> None:
        self.model = model.to(device)
        self.config = config
        self.device = torch.device(device)
        self.euler = EulerResiduals(gamma=1.4).to(self.device)

        self.optimizer = Adam(
            model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )

    def train(
        self,
        x_data: torch.Tensor,
        y_data: torch.Tensor,
        params_data: torch.Tensor,
        targets: torch.Tensor,
        x_colloc: torch.Tensor,
        y_colloc: torch.Tensor,
        params_colloc: torch.Tensor,
        epochs: int | None = None,
        verbose: bool = True,
    ) -> TrainResult:
        """Run 3-phase curriculum training.

        Args:
            x_data: (N_data,) x-coordinates of training data
            y_data: (N_data,) y-coordinates of training data
            params_data: (N_data, 7) normalized parameters
            targets: (N_data, 6) flow field targets
            x_colloc: (N_colloc,) x-coordinates for PDE residuals
            y_colloc: (N_colloc,) y-coordinates for PDE residuals
            params_colloc: (N_colloc, 7) parameters for collocation points
            epochs: Override max_epochs
            verbose: Print progress

        Returns:
            TrainResult with loss history and metrics
        """
        max_epochs = epochs or self.config.max_epochs
        phases = self.config.curriculum_phases
        phase1_end = phases[0]
        phase2_end = phase1_end + phases[1]

        x_data = x_data.to(self.device)
        y_data = y_data.to(self.device)
        params_data = params_data.to(self.device)
        targets = targets.to(self.device)
        x_colloc = x_colloc.to(self.device)
        y_colloc = y_colloc.to(self.device)
        params_colloc = params_colloc.to(self.device)

        scheduler = CosineAnnealingLR(self.optimizer, T_max=max_epochs, eta_min=1e-6)
        loss_history: list[float] = []

        t0 = time.time()

        for epoch in range(max_epochs):
            # Determine current phase and lambdas
            if epoch < phase1_end:
                # Phase 1: data fit only
                lam_data = self.config.lambda_data
                lam_pde = 0.0
                lam_bc = 0.0
                phase_name = "data-only"
            elif epoch < phase2_end:
                # Phase 2: ramp up physics
                progress = (epoch - phase1_end) / max(self.config.curriculum_phases[1], 1)
                lam_data = self.config.lambda_data
                lam_pde = self.config.lambda_pde * progress
                lam_bc = self.config.lambda_bc * progress
                phase_name = "physics-ramp"
            else:
                # Phase 3: full physics
                lam_data = self.config.lambda_data
                lam_pde = self.config.lambda_pde
                lam_bc = self.config.lambda_bc
                phase_name = "full-physics"

            loss, data_loss, pde_loss, bc_loss = self._train_step(
                x_data, y_data, params_data, targets,
                x_colloc, y_colloc, params_colloc,
                lam_data, lam_pde, lam_bc,
            )

            scheduler.step()
            loss_history.append(loss)

            if verbose and (epoch % 100 == 0 or epoch == max_epochs - 1):
                print(
                    f"  Epoch {epoch:5d}/{max_epochs} [{phase_name:12s}] "
                    f"loss={loss:.6f} data={data_loss:.6f} "
                    f"pde={pde_loss:.6f} bc={bc_loss:.6f}"
                )

        elapsed = time.time() - t0

        return TrainResult(
            epochs_trained=max_epochs,
            final_loss=loss_history[-1],
            final_data_loss=float(data_loss),
            final_pde_loss=float(pde_loss),
            final_bc_loss=float(bc_loss),
            training_time_s=elapsed,
            loss_history=loss_history,
        )

    def _train_step(
        self,
        x_data: torch.Tensor,
        y_data: torch.Tensor,
        params_data: torch.Tensor,
        targets: torch.Tensor,
        x_colloc: torch.Tensor,
        y_colloc: torch.Tensor,
        params_colloc: torch.Tensor,
        lam_data: float,
        lam_pde: float,
        lam_bc: float,
    ) -> tuple[float, float, float, float]:
        """Single training step with all loss components.

        Returns:
            (total_loss, data_loss, pde_loss, bc_loss)
        """
        self.optimizer.zero_grad()

        # Data loss: supervised fit on SU2 solution
        pred_data = self.model(x_data, y_data, params_data)
        data_loss = nn.functional.mse_loss(pred_data, targets)

        # PDE loss: Euler equation residuals at collocation points
        pde_loss = torch.tensor(0.0, device=self.device)
        if lam_pde > 0:
            x_c = x_colloc.clone().requires_grad_(True)
            y_c = y_colloc.clone().requires_grad_(True)
            pred_colloc = self.model(x_c, y_c, params_colloc)

            mach_c = pred_colloc[:, 0]
            pressure_c = pred_colloc[:, 1]
            temperature_c = pred_colloc[:, 2]
            density_c = pred_colloc[:, 3]
            vx_c = pred_colloc[:, 4]
            vy_c = pred_colloc[:, 5]

            residuals = self.euler(
                mach_c, pressure_c, temperature_c,
                density_c, vx_c, vy_c,
                x_c, y_c,
            )

            pde_loss = (
                residuals["continuity"].pow(2).mean()
                + residuals["x_momentum"].pow(2).mean()
                + residuals["y_momentum"].pow(2).mean()
                + residuals["energy"].pow(2).mean()
            )

        # BC loss: axis symmetry (Vy=0 at y=0)
        bc_loss = torch.tensor(0.0, device=self.device)
        if lam_bc > 0:
            # Sample points near the axis
            n_bc = min(64, len(x_colloc))
            y_axis = torch.zeros(n_bc, device=self.device) + 1e-6
            x_axis = x_colloc[:n_bc]
            params_axis = params_colloc[:n_bc]
            pred_axis = self.model(x_axis, y_axis, params_axis)
            bc_loss = pred_axis[:, 5].pow(2).mean()  # Vy should be 0

        # Total loss
        total_loss = lam_data * data_loss + lam_pde * pde_loss + lam_bc * bc_loss
        total_loss.backward()
        self.optimizer.step()

        return (
            float(total_loss.detach()),
            float(data_loss.detach()),
            float(pde_loss.detach()),
            float(bc_loss.detach()),
        )

    def save(self, path: Path) -> None:
        """Save model checkpoint.

        Args:
            path: Output path (.pt file)
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "config": self.config,
        }, path)

    def load(self, path: Path) -> None:
        """Load model checkpoint.

        Args:
            path: Checkpoint path (.pt file)
        """
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(checkpoint["model_state_dict"])
