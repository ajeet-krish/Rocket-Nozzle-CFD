"""3D revolved surface visualization of nozzle contours.

Provides a revolved 3D surface plot of a 2D nozzle contour, matching
the orientation of the Bell-Nozzle reference project: nozzle axis along
Z (vertical), viewed from above with inlet at top, outlet at bottom.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from src.nozzle.config import NozzleConfig
from src.nozzle.geometry import generate_contour


def _ring(
    r: float,
    h: float,
    a: float = 0.0,
    n_theta: int = 60,
    n_height: int = 4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate a cylindrical ring surface patch.

    Creates a thin cylinder of radius ``r``, height ``h``, starting at
    axial position ``a``.  Used as the building block for the revolved
    nozzle surface.

    Args:
        r: Ring radius.
        h: Ring thickness (axial height).
        a: Starting axial position.
        n_theta: Number of angular divisions.
        n_height: Number of axial divisions within the ring.

    Returns:
        (X, Y, Z) arrays of shape ``(n_height, n_theta)``.
    """
    theta = np.linspace(0, 2 * np.pi, n_theta)
    v = np.linspace(a, a + h, n_height)
    theta_mesh, v_mesh = np.meshgrid(theta, v)
    X = r * np.cos(theta_mesh)
    Y = r * np.sin(theta_mesh)
    Z = v_mesh
    return X, Y, Z


def _set_axes_equal_3d(ax: plt.Axes) -> None:
    """Set equal aspect ratio for 3D axes (bounding cube method)."""
    limits = np.array([ax.get_xlim3d(), ax.get_ylim3d(), ax.get_zlim3d()])
    origin = np.mean(limits, axis=1)
    radius = 0.5 * np.max(np.abs(limits[:, 1] - limits[:, 0]))
    ax.set_xlim3d([origin[0] - radius, origin[0] + radius])
    ax.set_ylim3d([origin[1] - radius, origin[1] + radius])
    ax.set_zlim3d([origin[2] - radius, origin[2] + radius])


def plot_nozzle_3d(
    config: NozzleConfig,
    output_path: Path,
    dpi: int = 150,
    elevation: float = -170.0,
    azimuth: float = -15.0,
    n_theta: int = 60,
    colormap: str = "coolwarm",
) -> Path:
    """Create a 3D revolved surface plot of the nozzle contour.

    Matches the Bell-Nozzle reference orientation: nozzle axis along Z
    (vertical), inlet at top, outlet (bell exit) at bottom, viewed from
    above at a slight angle.

    Args:
        config: Nozzle geometry parameters.
        output_path: Destination for the rendered PNG.
        dpi: Image resolution (dots per inch).
        elevation: Camera elevation (degrees, default -170 = top-down).
        azimuth: Camera azimuth (degrees, default -15).
        n_theta: Angular divisions for each ring.
        colormap: Matplotlib colourmap for the surface.

    Returns:
        Path to the saved PNG file.
    """
    output_path = Path(output_path)

    # 1. Generate 2D contour (x = axial, y = radius)
    x, y = generate_contour(config)

    # 2. Build the revolved surface ring-by-ring (matching Bell-Nozzle)
    #    Nozzle axis runs along Z.  x -> Z, y -> radius in X-Y plane.
    ring_thickness = 5.0 * abs(x[1] - x[0]) if len(x) > 1 else 0.01

    # Colour each ring by its axial position for visual depth
    norm = plt.Normalize(x.min(), x.max())
    cmap = plt.get_cmap(colormap)

    # 3. Create figure with dark background
    fig = plt.figure(figsize=(10, 10))
    fig.patch.set_facecolor("#0a1628")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a1628")

    # 4. Draw rings to build the surface
    for i in range(len(y)):
        X, Y, Z = _ring(y[i], ring_thickness, x[i], n_theta=n_theta)
        colour = cmap(norm(x[i]))
        ax.plot_surface(X, Y, Z, color=colour, alpha=0.92, shade=True)

    # 5. Axis of symmetry (dashed line along Z)
    z_min, z_max = float(x.min()), float(x.max())
    ax.plot(
        [0, 0], [0, 0], [z_min, z_max],
        color="#00e5ff", linewidth=1.0, alpha=0.5, linestyle="--",
    )

    # 6. Equal aspect ratio
    ax.set_box_aspect([1, 1, 1])
    _set_axes_equal_3d(ax)

    # 7. View angle (matching Bell-Nozzle reference)
    ax.view_init(elev=elevation, azim=azimuth)

    # 8. Style
    ax.set_xlabel("X (m)", color="white", fontsize=9, labelpad=8)
    ax.set_ylabel("Y (m)", color="white", fontsize=9, labelpad=8)
    ax.set_zlabel("Axial (m)", color="white", fontsize=9, labelpad=8)
    ax.tick_params(colors="white", labelsize=7)
    ax.grid(False)
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("none")

    # 9. Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(
        output_path, dpi=dpi, bbox_inches="tight",
        facecolor=fig.get_facecolor(), pad_inches=0.05,
    )
    plt.close(fig)

    return output_path
