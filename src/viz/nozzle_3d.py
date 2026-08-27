"""3D revolved surface visualization of nozzle contours.

Ring-based surface of revolution matching the Bell-Nozzle reference
orientation: nozzle axis along Z (vertical), inlet at top, outlet at
bottom.  White-background scientific styling.
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
    """Generate a cylindrical ring surface patch."""
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
    dpi: int = 200,
    elevation: float = -170.0,
    azimuth: float = -15.0,
    n_theta: int = 60,
    colormap: str = "coolwarm",
) -> Path:
    """Create a 3D revolved surface plot of the nozzle contour.

    Nozzle axis along Z (vertical), inlet at top, outlet at bottom,
    viewed from above at a slight angle.  White-background scientific
    styling with colour mapped to axial position.
    """
    output_path = Path(output_path)

    # 1. Generate 2D contour
    x, y = generate_contour(config)

    # 2. Ring thickness
    ring_thickness = 5.0 * abs(x[1] - x[0]) if len(x) > 1 else 0.01

    # 3. Colourmap normalised to axial position
    norm = plt.Normalize(x.min(), x.max())
    cmap = plt.get_cmap(colormap)

    # 4. Figure
    fig = plt.figure(figsize=(10, 10))
    fig.patch.set_facecolor("white")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("white")

    # 5. Draw rings
    for i in range(len(y)):
        X, Y, Z = _ring(y[i], ring_thickness, x[i], n_theta=n_theta)
        colour = cmap(norm(x[i]))
        ax.plot_surface(X, Y, Z, color=colour, alpha=0.92, shade=True)

    # 6. Axis of symmetry
    z_min, z_max = float(x.min()), float(x.max())
    ax.plot(
        [0, 0], [0, 0], [z_min, z_max],
        color="#1565C0", linewidth=1.0, alpha=0.6, linestyle="--",
    )

    # 7. Equal aspect
    ax.set_box_aspect([1, 1, 1])
    _set_axes_equal_3d(ax)

    # 8. View
    ax.view_init(elev=elevation, azim=azimuth)

    # 9. Style
    ax.set_xlabel("X (m)", fontsize=10, color="black", labelpad=8)
    ax.set_ylabel("Y (m)", fontsize=10, color="black", labelpad=8)
    ax.set_zlabel("Axial (m)", fontsize=10, color="black", labelpad=8)
    ax.tick_params(colors="black", labelsize=8)
    ax.grid(False)
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("#cccccc")

    ax.set_title(
        f"Revolved Nozzle  --  $\\epsilon$ = {config.expansion_ratio:.0f}:1"
        f",  $R_t$ = {config.throat_radius*1000:.0f} mm",
        fontsize=12, color="black", pad=12,
    )

    # 10. Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(
        output_path, dpi=dpi, bbox_inches="tight",
        facecolor="white", pad_inches=0.05,
    )
    plt.close(fig)

    return output_path
