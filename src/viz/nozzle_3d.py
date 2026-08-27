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
    elevation: float = 12.0,
    azimuth: float = 0.0,
    n_rings: int = 80,
    colormap: str = "coolwarm",
) -> Path:
    """Create a 3D revolved surface plot of the nozzle contour.

    Renders the nozzle as a half-cut revolved surface viewed from the
    side, showing the full profile: inlet chamber, convergent section,
    throat, and divergent bell.  The nozzle axis runs horizontally.

    Args:
        config: Nozzle geometry parameters.
        output_path: Destination for the rendered PNG.
        dpi: Image resolution (dots per inch).
        elevation: Camera elevation angle (degrees, default 12).
        azimuth: Camera azimuth angle (degrees, default 0 = side view).
        n_rings: Number of angular divisions for the revolved mesh.
        colormap: Matplotlib colourmap for the surface.

    Returns:
        Path to the saved PNG file.
    """
    output_path = Path(output_path)

    # 1. Generate 2D contour
    x, y = generate_contour(config)

    # 2. Revolve only the top half (0 to pi) for a clean side profile
    n_half = max(n_rings // 2, 2)
    theta = np.linspace(0, np.pi, n_half)
    theta_mesh, x_mesh = np.meshgrid(theta, x, indexing="ij")

    Y = y * np.cos(theta_mesh)
    Z = y * np.sin(theta_mesh)
    X = x_mesh

    # 3. Create figure with dark background
    fig = plt.figure(figsize=(16, 7))
    fig.patch.set_facecolor("#0a1628")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a1628")

    # 4. Filled surface
    ax.plot_surface(
        X, Y, Z,
        cmap=colormap,
        alpha=0.85,
        edgecolor="none",
        antialiased=True,
        shade=True,
    )

    # 5. Wireframe overlay for mesh quality impression
    ax.plot_wireframe(
        X, Y, Z,
        alpha=0.08,
        color="cyan",
        linewidth=0.2,
    )

    # 6. Draw the axis of symmetry line
    ax.plot(
        [x.min(), x.max()], [0, 0], [0, 0],
        color="#00e5ff", linewidth=1.0, alpha=0.6, linestyle="--",
    )

    # 7. Draw the 2D contour profile on the Z=0 plane for clarity
    ax.plot(x, y, np.zeros_like(x), color="#00e5ff", linewidth=1.5, alpha=0.9)
    ax.plot(x, -y, np.zeros_like(x), color="#00e5ff", linewidth=1.5, alpha=0.9)

    # 8. Set axis proportions: Y and Z equal (circular), X scaled to show length
    r_max = float(np.max(y))
    x_range = float(x.max() - x.min())
    yz_range = 2.0 * r_max

    # Center the nozzle at origin for Y/Z
    ax.set_xlim3d(float(x.min()), float(x.max()))
    ax.set_ylim3d(-r_max * 1.1, r_max * 1.1)
    ax.set_zlim3d(-r_max * 1.1, r_max * 1.1)

    # Force equal Y/Z aspect ratio; let X scale naturally
    ax.set_box_aspect([x_range / yz_range, 1.0, 1.0])

    # 9. View angle: near side-profile
    ax.view_init(elev=elevation, azim=azimuth)

    # 10. Style
    ax.set_xlabel("Axial (m)", color="white", fontsize=10, labelpad=12)
    ax.set_ylabel("Radial (m)", color="white", fontsize=10, labelpad=12)
    ax.set_zlabel("Azimuthal (m)", color="white", fontsize=10, labelpad=12)
    ax.tick_params(colors="white", labelsize=8)
    ax.grid(False)
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor("none")
    ax.yaxis.pane.set_edgecolor("none")
    ax.zaxis.pane.set_edgecolor("none")

    # 11. Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(
        output_path, dpi=dpi, bbox_inches="tight",
        facecolor=fig.get_facecolor(), pad_inches=0.1,
    )
    plt.close(fig)

    return output_path
