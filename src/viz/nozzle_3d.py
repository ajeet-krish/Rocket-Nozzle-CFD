"""3D revolved surface visualization of nozzle contours.

Provides a revolved 3D surface plot of a 2D nozzle contour, useful for
presenting the full axisymmetric geometry in portfolio visuals. Inspired
by the Bell-Nozzle reference project.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from src.nozzle.config import NozzleConfig
from src.nozzle.geometry import generate_contour


def revolve_contour(
    x: np.ndarray,
    y: np.ndarray,
    n_rings: int = 60,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Revolve a 2D nozzle contour around the x-axis to form a 3D surface.

    The contour is swept through a full 360 degrees, producing a surface
    mesh suitable for ``plot_surface`` or ``plot_wireframe``.

    Args:
        x: Axial coordinates, shape ``(n_points,)``.
        y: Radial coordinates, shape ``(n_points,)``.
        n_rings: Number of angular divisions (default 60).

    Returns:
        Tuple of (X, Y, Z) meshgrid arrays, each shape
        ``(n_rings, n_points)``.
    """
    theta = np.linspace(0, 2 * np.pi, n_rings)
    theta_mesh, x_mesh = np.meshgrid(theta, x, indexing="ij")

    Y = y * np.cos(theta_mesh)
    Z = y * np.sin(theta_mesh)
    X = x_mesh

    return X, Y, Z


def plot_nozzle_3d(
    config: NozzleConfig,
    output_path: Path,
    dpi: int = 150,
    elevation: float = 25.0,
    azimuth: float = -60.0,
    n_rings: int = 60,
    colormap: str = "coolwarm",
) -> Path:
    """Create a 3D revolved surface plot of the nozzle contour.

    The nozzle wall is revolved around the x-axis and rendered as a
    coloured surface with an optional wireframe overlay on a dark
    background matching the AK-Vortex theme.

    Args:
        config: Nozzle geometry parameters.
        output_path: Destination for the rendered PNG.
        dpi: Image resolution (dots per inch).
        elevation: Camera elevation angle (degrees).
        azimuth: Camera azimuth angle (degrees).
        n_rings: Number of angular divisions for the revolved mesh.
        colormap: Matplotlib colourmap for the surface.

    Returns:
        Path to the saved PNG file.
    """
    output_path = Path(output_path)

    # 1. Generate 2D contour
    x, y = generate_contour(config)

    # 2. Revolve to 3D surface
    X, Y, Z = revolve_contour(x, y, n_rings)

    # 3. Create figure with dark background
    fig = plt.figure(figsize=(14, 6))
    fig.patch.set_facecolor("#0a1628")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a1628")

    # 4. Filled surface
    ax.plot_surface(
        X, Y, Z,
        cmap=colormap,
        alpha=0.9,
        edgecolor="none",
        antialiased=True,
    )

    # 5. Wireframe overlay at low opacity
    ax.plot_wireframe(
        X, Y, Z,
        alpha=0.1,
        color="cyan",
        linewidth=0.3,
    )

    # 6. Equal aspect ratio
    _set_axes_equal_3d(ax)

    # 7. View angle
    ax.view_init(elev=elevation, azim=azimuth)

    # 8. Style: light labels, no grid
    ax.set_xlabel("Axial (m)", color="white", fontsize=10, labelpad=10)
    ax.set_ylabel("Y (m)", color="white", fontsize=10, labelpad=10)
    ax.set_zlabel("Z (m)", color="white", fontsize=10, labelpad=10)
    ax.tick_params(colors="white", labelsize=8)
    ax.grid(False)
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor("none")
    ax.yaxis.pane.set_edgecolor("none")
    ax.zaxis.pane.set_edgecolor("none")

    # 9. Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    return output_path


def _set_axes_equal_3d(ax: plt.Axes) -> None:
    """Set equal aspect ratio for a 3D matplotlib axes.

    Computes the bounding cube of the current limits and expands each
    axis to the same range so that the nozzle geometry is not distorted.

    Args:
        ax: A matplotlib 3D Axes instance.
    """
    limits = np.array([ax.get_xlim3d(), ax.get_ylim3d(), ax.get_zlim3d()])
    origin = np.mean(limits, axis=1)
    radius = 0.5 * np.max(np.abs(limits[:, 1] - limits[:, 0]))
    ax.set_xlim3d([origin[0] - radius, origin[0] + radius])
    ax.set_ylim3d([origin[1] - radius, origin[1] + radius])
    ax.set_zlim3d([origin[2] - radius, origin[2] + radius])
