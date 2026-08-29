"""Euler equation residuals for axisymmetric nozzle flow.

Computes PDE residuals using torch.autograd for automatic differentiation.
The axisymmetric Euler equations in conservative form:

    dU/dt + dF/dx + dG/dy + H/y = 0

where U = [rho, rho*Vx, rho*Vy, rho*E] are conservative variables.
"""
import torch
import torch.nn as nn


class EulerResiduals(nn.Module):
    """Compute axisymmetric Euler equation residuals via autograd.

    The network predicts primitive variables (Mach, P, T, rho, Vx, Vy).
    This module computes the residuals of the Euler equations using
    automatic differentiation of the network output with respect to inputs.

    Governing equations (steady-state axisymmetric):
        Continuity:  d(rho*Vx)/dx + d(rho*Vy)/dy + rho*Vy/y = 0
        X-momentum:  d(rho*Vx*Vx + P)/dx + d(rho*Vx*Vy)/dy + rho*Vx*Vy/y = 0
        Y-momentum:  d(rho*Vx*Vy)/dx + d(rho*Vy*Vy + P)/dy - P/y + rho*Vy*Vy/y = 0
        Energy:      d(rho*Vx*H)/dx + d(rho*Vy*H)/dy + rho*Vy*H/y = 0
    """

    def __init__(self, gamma: float = 1.4) -> None:
        super().__init__()
        self.gamma = gamma

    def forward(
        self,
        mach: torch.Tensor,
        pressure: torch.Tensor,
        temperature: torch.Tensor,
        density: torch.Tensor,
        vx: torch.Tensor,
        vy: torch.Tensor,
        x: torch.Tensor,
        y: torch.Tensor,
        gamma_tensor: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        """Compute Euler residuals from predicted primitive variables.

        Args:
            mach: (B,) Mach number
            pressure: (B,) static pressure
            temperature: (B,) static temperature
            density: (B,) density
            vx: (B,) x-velocity
            vy: (B,) y-velocity
            x: (B,) axial coordinates (requires grad)
            y: (B,) radial coordinates (requires grad)
            gamma_tensor: (B,) per-sample gamma values (optional)

        Returns:
            Dictionary of residual terms:
                "continuity": mass conservation residual
                "x_momentum": x-momentum residual
                "y_momentum": y-momentum residual
                "energy": energy residual
        """
        # Use per-sample gamma if provided, otherwise scalar default
        gamma = gamma_tensor if gamma_tensor is not None else self.gamma

        # Velocity magnitude for energy equation
        speed_sq = vx ** 2 + vy ** 2
        gamma_over_gm1 = gamma / (gamma - 1.0)
        enthalpy = gamma_over_gm1 * pressure / (density + 1e-30) + 0.5 * speed_sq

        # Conservative variables
        rho_vx = density * vx
        rho_vy = density * vy

        # Pressure gradients
        dp_dx = torch.autograd.grad(
            pressure, x, grad_outputs=torch.ones_like(pressure),
            create_graph=True, retain_graph=True,
        )[0]
        dp_dy = torch.autograd.grad(
            pressure, y, grad_outputs=torch.ones_like(pressure),
            create_graph=True, retain_graph=True,
        )[0]

        # Density gradients
        drho_dx = torch.autograd.grad(
            density, x, grad_outputs=torch.ones_like(density),
            create_graph=True, retain_graph=True,
        )[0]
        drho_dy = torch.autograd.grad(
            density, y, grad_outputs=torch.ones_like(density),
            create_graph=True, retain_graph=True,
        )[0]

        # Velocity gradients
        dvx_dx = torch.autograd.grad(
            vx, x, grad_outputs=torch.ones_like(vx),
            create_graph=True, retain_graph=True,
        )[0]
        dvx_dy = torch.autograd.grad(
            vx, y, grad_outputs=torch.ones_like(vx),
            create_graph=True, retain_graph=True,
        )[0]
        dvy_dx = torch.autograd.grad(
            vy, x, grad_outputs=torch.ones_like(vy),
            create_graph=True, retain_graph=True,
        )[0]
        dvy_dy = torch.autograd.grad(
            vy, y, grad_outputs=torch.ones_like(vy),
            create_graph=True, retain_graph=True,
        )[0]

        # Enthalpy gradients via autograd (product rule for d(rho*Vx*H)/dx)
        dH_dx = torch.autograd.grad(
            enthalpy, x, grad_outputs=torch.ones_like(enthalpy),
            create_graph=True, retain_graph=True,
        )[0]
        dH_dy = torch.autograd.grad(
            enthalpy, y, grad_outputs=torch.ones_like(enthalpy),
            create_graph=True, retain_graph=True,
        )[0]

        # Avoid division by zero at axis (y=0)
        y_safe = torch.clamp(y.abs(), min=1e-6)

        # Continuity: d(rho*Vx)/dx + d(rho*Vy)/dy + rho*Vy/y = 0
        continuity = (
            drho_dx * vx + density * dvx_dx
            + drho_dy * vy + density * dvy_dy
            + rho_vy / y_safe
        )

        # X-momentum: d(rho*Vx*Vx + P)/dx + d(rho*Vx*Vy)/dy + rho*Vx*Vy/y = 0
        x_momentum = (
            drho_dx * vx * vx + density * 2 * vx * dvx_dx + dp_dx
            + drho_dy * vx * vy + density * (dvx_dy * vy + vx * dvy_dy)
            + rho_vx * vy / y_safe
        )

        # Y-momentum: d(rho*Vx*Vy)/dx + d(rho*Vy*Vy + P)/dy - P/y + rho*Vy*Vy/y = 0
        y_momentum = (
            drho_dx * vx * vy + density * (dvx_dx * vy + vx * dvy_dx)
            + drho_dy * vy * vy + density * 2 * vy * dvy_dy + dp_dy
            - pressure / y_safe
            + density * vy * vy / y_safe
        )

        # Energy: d(rho*Vx*H)/dx + d(rho*Vy*H)/dy + rho*Vy*H/y = 0
        # Product rule: d(rho*Vx*H)/dx = drho/dx*Vx*H + rho*dVx/dx*H + rho*Vx*dH/dx
        energy = (
            drho_dx * vx * enthalpy + density * (dvx_dx * enthalpy + vx * dH_dx)
            + drho_dy * vy * enthalpy + density * (dvy_dy * enthalpy + vy * dH_dy)
            + density * vy * enthalpy / y_safe
        )

        return {
            "continuity": continuity,
            "x_momentum": x_momentum,
            "y_momentum": y_momentum,
            "energy": energy,
        }
