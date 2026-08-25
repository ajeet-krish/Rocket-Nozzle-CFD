"""Conical nozzle contour generation."""
import numpy as np
from .config import NozzleConfig


def generate_contour(config: NozzleConfig) -> tuple[np.ndarray, np.ndarray]:
    """Generate (x, y) contour points for a conical nozzle.

    The nozzle consists of:
    - Converging section: inlet (r=R_inlet) to throat (r=R_throat)
    - Diverging section: throat (r=R_throat) to exit (r=R_exit) at half_angle

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

    # Diverging section: conical expansion at half_angle
    half_angle_rad = np.radians(config.half_angle)
    x_diverge = np.linspace(0, config.diverging_length, n_diverge)
    y_diverge = config.throat_radius + x_diverge * np.tan(half_angle_rad)

    # Concatenate (exclude duplicate throat point)
    x = np.concatenate([x_converge, x_diverge[1:]])
    y = np.concatenate([y_converge, y_diverge[1:]])

    return x, y


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
