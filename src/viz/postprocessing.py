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

    Args:
        vtu_data: Parsed VTU data
        nozzle_exit_x: x-coordinate of nozzle exit

    Returns:
        x: Axial coordinates along wall
        pressure: Pressure values along wall
    """
    coords = vtu_data.coordinates

    # For now, extract along centerline (y ~ 0)
    centerline_mask = np.abs(coords[:, 1]) < 0.001

    if vtu_data.pressure is not None:
        return coords[centerline_mask, 0], vtu_data.pressure[centerline_mask]
    else:
        return coords[centerline_mask, 0], np.zeros_like(coords[centerline_mask, 0])


def compute_density_gradient(
    vtu_data: VTUData,
) -> np.ndarray:
    """Compute density gradient magnitude using spatial neighbor search.

    Uses cKDTree to find actual spatial neighbors, then computes
    gradient via least-squares fit on local neighborhood. This avoids
    the pitfall of assuming sequential node indices are spatial neighbors
    in an unstructured mesh.

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

    # Find k nearest neighbors for each point (exclude self at index 0)
    k = min(8, len(coords) - 1)
    distances, indices = tree.query(coords, k=k)

    # Compute gradient using least-squares fit on neighbors
    grad = np.zeros(len(coords))
    for i in range(len(coords)):
        neighbor_idx = indices[i, 1:]  # Exclude self
        dx = coords[neighbor_idx, 0] - coords[i, 0]
        dy = coords[neighbor_idx, 1] - coords[i, 1]
        drho = density[neighbor_idx] - density[i]

        # Least-squares gradient: drho = grad_x * dx + grad_y * dy
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

    ax.plot(x, pressure, "b-", linewidth=2)
    ax.set_xlabel("Axial Distance (m)", fontsize=12)
    ax.set_ylabel("Static Pressure (Pa)", fontsize=12)
    ax.set_title("Pressure Distribution Along Nozzle", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_yscale("log")

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
    
    # Filled contour plot
    contour = ax.tricontourf(triang, grad, levels=20, cmap='hot', 
                            vmin=0, vmax=np.percentile(grad, 95))
    
    ax.set_xlabel("Axial Distance (m)", fontsize=12)
    ax.set_ylabel("Radial Distance (m)", fontsize=12)
    ax.set_title("Shock Diamond Visualization (Density Gradient)", fontsize=14)
    ax.set_aspect("equal")
    
    cbar = plt.colorbar(contour, ax=ax, shrink=0.8)
    cbar.set_label("Density Gradient Magnitude", fontsize=11)
    
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close()
    
    return output_path
