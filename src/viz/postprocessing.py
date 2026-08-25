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
    """Compute density gradient magnitude for shock visualization.

    Note: This is a simplified approximation for unstructured data.
    For production use, compute gradient from VTU directly using VTK/PyVista.

    Args:
        vtu_data: Parsed VTU data

    Returns:
        Gradient magnitude at each node
    """
    if vtu_data.density is None:
        return np.zeros(len(vtu_data.coordinates))

    # Simple gradient approximation using nearest neighbors
    # In practice, use gradient from VTU or compute properly with VTK
    coords = vtu_data.coordinates
    density = vtu_data.density

    # Compute gradient using finite differences along x-axis
    grad = np.zeros_like(density)
    for i in range(1, len(density) - 1):
        dx = coords[i + 1, 0] - coords[i - 1, 0]
        if abs(dx) > 1e-12:
            grad[i] = (density[i + 1] - density[i - 1]) / dx

    return np.abs(grad)


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

    Args:
        vtu_data: Parsed VTU data
        output_path: Path to save plot
        dpi: Image resolution

    Returns:
        Path to saved plot
    """
    coords = vtu_data.coordinates
    grad = compute_density_gradient(vtu_data)

    fig, ax = plt.subplots(1, 1, figsize=(12, 4))

    scatter = ax.scatter(
        coords[:, 0],
        coords[:, 1],
        c=grad,
        cmap="hot",
        s=0.1,
        vmin=0,
        vmax=np.percentile(grad, 95),
    )

    ax.set_xlabel("Axial Distance (m)", fontsize=12)
    ax.set_ylabel("Radial Distance (m)", fontsize=12)
    ax.set_title("Shock Diamond Visualization (Density Gradient)", fontsize=14)
    ax.set_aspect("equal")

    cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
    cbar.set_label("Density Gradient Magnitude", fontsize=11)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close()

    return output_path
