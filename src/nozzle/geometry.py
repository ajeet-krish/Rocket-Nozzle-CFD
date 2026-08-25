"""Nozzle contour generation (conical and Rao bell)."""
import numpy as np
from .config import NozzleConfig


def generate_contour(config: NozzleConfig) -> tuple[np.ndarray, np.ndarray]:
    """Generate (x, y) contour points for a nozzle.

    Uses Rao parabolic bell approximation for the diverging section.

    Args:
        config: Nozzle geometry parameters

    Returns:
        x: axial coordinates (m), shape (num_points,)
        y: radial coordinates (m), shape (num_points,)
    """
    n = config.num_points

    # Split points between converging and diverging sections
    n_converge = n // 4  # 25% for converging
    n_diverge = n - n_converge  # 75% for diverging

    # Converging section: linear taper from inlet radius to throat
    inlet_radius = config.throat_radius * 1.5  # Inlet is 1.5x throat
    x_converge = np.linspace(-config.converging_length, 0, n_converge)
    y_converge = np.linspace(inlet_radius, config.throat_radius, n_converge)

    # Diverging section: Rao parabolic bell
    x_diverge = np.linspace(0, config.diverging_length, n_diverge)
    y_diverge = _rao_bell(
        config.throat_radius, config.exit_radius,
        config.diverging_length, x_diverge,
    )

    # Concatenate (exclude duplicate throat point)
    x = np.concatenate([x_converge, x_diverge[1:]])
    y = np.concatenate([y_converge, y_diverge[1:]])

    return x, y


def _rao_bell(
    r_throat: float,
    r_exit: float,
    length: float,
    x: np.ndarray,
) -> np.ndarray:
    """Compute Rao parabolic bell contour.

    Uses quadratic Bezier curve with control points:
    - P0: (0, r_throat) - throat
    - P1: (Cx, Cy) - control point from angle constraints
    - P2: (length, r_exit) - exit

    Args:
        r_throat: Throat radius (m)
        r_exit: Exit radius (m)
        length: Diverging section length (m)
        x: Axial coordinates (m)

    Returns:
        Radial coordinates (m) at each x location
    """
    # Wall angle at throat (typically 30 degrees for Rao bell)
    theta_n = np.radians(30.0)

    # Wall angle at exit (typically 0 degrees for perfectly expanded)
    theta_e = np.radians(0.0)

    # Control point P1 from angle constraints
    # At throat: dy/dx = tan(theta_n)
    # At exit: dy/dx = tan(theta_e)
    cx = (r_exit - r_throat - length * np.tan(theta_e)) / (
        np.tan(theta_n) - np.tan(theta_e)
    )
    cy = r_throat + cx * np.tan(theta_n)

    # Parametric Bezier: t in [0, 1]
    # x(t) = (1-t)^2 * 0 + 2*t*(1-t)*cx + t^2 * length
    # y(t) = (1-t)^2 * r_throat + 2*t*(1-t)*cy + t^2 * r_exit

    # Solve for t from x using Newton-Raphson
    t = np.linspace(0, 1, len(x))
    for _ in range(10):
        x_bezier = 2 * t * (1 - t) * cx + t**2 * length
        dx_dt = 2 * (1 - 2 * t) * cx + 2 * t * length
        dt = (x_bezier - x) / np.where(np.abs(dx_dt) >= 1e-12, dx_dt, 1e-12)
        t = t - dt
        t = np.clip(t, 0, 1)
        if np.max(np.abs(dt)) < 1e-10:
            break

    # Compute y from t
    y = (1 - t)**2 * r_throat + 2 * t * (1 - t) * cy + t**2 * r_exit

    return y


def plot_contour(x: np.ndarray, y: np.ndarray, title: str = "Nozzle Contour") -> None:
    """Plot the nozzle contour for debugging."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    ax.plot(x, y, 'b-', linewidth=2, label='Wall')
    ax.plot(x, -y, 'b-', linewidth=2)  # Mirror for axisymmetric
    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5, label='Axis')
    ax.set_xlabel('Axial Distance (m)')
    ax.set_ylabel('Radial Distance (m)')
    ax.set_title(title)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig('docs/assets/images/nozzle_contour.png', dpi=150)
    plt.close()
