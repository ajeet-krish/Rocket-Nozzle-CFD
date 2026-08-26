"""Post-processing for nozzle CFD results."""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from cfd.vtu_parser import VTUData


def extract_wall_pressure(
    vtu_data: VTUData,
    nozzle_exit_x: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract pressure distribution along nozzle wall.

    Identifies wall nodes as those with maximum y-coordinate at each
    axial station (top boundary of axisymmetric domain).

    Args:
        vtu_data: Parsed VTU data
        nozzle_exit_x: x-coordinate of nozzle exit

    Returns:
        x: Axial coordinates along wall
        pressure: Pressure values along wall
    """
    coords = vtu_data.coordinates
    x = coords[:, 0]
    y = coords[:, 1]

    if vtu_data.pressure is None:
        return np.array([]), np.array([])

    # Bin by x-coordinate and take the point with max y (wall) in each bin
    x_min, x_max = x.min(), x.max()
    n_bins = 100
    x_bins = np.linspace(x_min, x_max, n_bins + 1)
    x_wall = []
    p_wall = []

    for i in range(n_bins):
        mask = (x >= x_bins[i]) & (x < x_bins[i + 1])
        if mask.any():
            # Take the point with maximum y (closest to wall)
            idx = np.argmax(y[mask])
            x_vals = x[mask]
            p_vals = vtu_data.pressure[mask]
            x_wall.append(x_vals[idx])
            p_wall.append(p_vals[idx])

    return np.array(x_wall), np.array(p_wall)


def compute_density_gradient(
    vtu_data: VTUData,
) -> np.ndarray:
    """Compute density gradient magnitude using spatial neighbor search.

    Uses cKDTree to find actual spatial neighbors, then computes
    gradient via least-squares fit on local neighborhood.

    Args:
        vtu_data: Parsed VTU data

    Returns:
        Gradient magnitude at each node
    """
    if vtu_data.density is None:
        return np.zeros(len(vtu_data.coordinates))

    from scipy.spatial import cKDTree

    coords = vtu_data.coordinates
    density = vtu_data.density

    # Build KD-tree for spatial neighbor search
    tree = cKDTree(coords)

    # Find k nearest neighbors for each point
    k = min(8, len(coords) - 1)
    distances, indices = tree.query(coords, k=k)

    # Compute gradient using least-squares fit on neighbors
    grad = np.zeros(len(coords))
    for i in range(len(coords)):
        neighbor_idx = indices[i, 1:]  # Exclude self
        dx = coords[neighbor_idx, 0] - coords[i, 0]
        dy = coords[neighbor_idx, 1] - coords[i, 1]
        drho = density[neighbor_idx] - density[i]

        A = np.column_stack([dx, dy])
        if A.shape[0] >= 2 and np.linalg.matrix_rank(A) >= 2:
            grad_xy, _, _, _ = np.linalg.lstsq(A, drho, rcond=None)
            grad[i] = np.sqrt(grad_xy[0] ** 2 + grad_xy[1] ** 2)

    return grad


def plot_wall_pressure(
    x: np.ndarray,
    pressure: np.ndarray,
    output_path: Path,
    dpi: int = 150,
) -> Path:
    """Plot pressure distribution along nozzle wall.

    Args:
        x: Axial coordinates
        pressure: Pressure values
        output_path: Path to save plot
        dpi: Image resolution

    Returns:
        Path to saved plot
    """
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    ax.semilogy(x * 1000, pressure / 1e6, "b-", linewidth=2)
    ax.set_xlabel("Axial Distance (mm)", fontsize=12)
    ax.set_ylabel("Static Pressure (MPa)", fontsize=12)
    ax.set_title("Wall Pressure Distribution", fontsize=14)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close()

    return output_path


def plot_shock_diamonds(
    vtu_data: VTUData,
    output_path: Path,
    dpi: int = 150,
) -> Path:
    """Plot shock diamond visualization using density gradient.

    Uses tricontourf for filled contours.

    Args:
        vtu_data: Parsed VTU data
        output_path: Path to save plot
        dpi: Image resolution

    Returns:
        Path to saved plot
    """
    from matplotlib.tri import Triangulation

    coords = vtu_data.coordinates
    grad = compute_density_gradient(vtu_data)

    # Create triangulation
    triang = Triangulation(coords[:, 0], coords[:, 1])

    fig, ax = plt.subplots(1, 1, figsize=(12, 4))

    # Filled contour plot with better scaling
    grad_max = np.percentile(grad, 99)
    if grad_max > 0:
        contour = ax.tricontourf(
            triang, grad, levels=30, cmap='hot',
            vmin=0, vmax=grad_max,
        )
    else:
        contour = ax.tricontourf(triang, grad, levels=30, cmap='hot')

    ax.set_xlabel("Axial Distance (m)", fontsize=12)
    ax.set_ylabel("Radial Distance (m)", fontsize=12)
    ax.set_title("Shock Diamond Visualization (Density Gradient)", fontsize=14)
    ax.set_aspect("equal")

    cbar = plt.colorbar(contour, ax=ax, shrink=0.8)
    cbar.set_label("|nabla rho| (kg/m^4)", fontsize=11)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close()

    return output_path
