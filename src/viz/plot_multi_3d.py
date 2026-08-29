"""2x2 multi-plot comparing all four rocket engine 3D geometries.

Generates a 2x2 subplot grid with unified axes so relative size/scale
of each engine is immediately visible. Merlin 1D and Raptor SL are
compact sea-level engines; RS-25 and RL10B-2 are progressively larger
vacuum-optimized nozzles.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour
from nozzle.presets import merlin_1d, raptor_sl, rs_25, rl10b_2


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


def _draw_nozzle_on_ax(
    ax: plt.Axes,
    config: NozzleConfig,
    z_offset: float = 0.0,
    n_theta: int = 60,
    colormap: str = "plasma",
) -> None:
    """Draw a single nozzle surface on a 3D axes.

    Args:
        ax: 3D axes to draw on.
        config: Nozzle geometry configuration.
        z_offset: Vertical shift so the nozzle exit sits at z=0.
        n_theta: Circumferential resolution for ring generation.
        colormap: Matplotlib colormap name.
    """
    x, y = generate_contour(config)
    # Shift so exit (maximum x) sits at z=0, inlet extends downward (negative z)
    x_shifted = x - x.max() + z_offset
    ring_thickness = 5.0 * abs(x[1] - x[0]) if len(x) > 1 else 0.01

    norm = plt.Normalize(x_shifted.min(), x_shifted.max())
    cmap = plt.get_cmap(colormap)

    for i in range(len(y)):
        X, Y, Z = _ring(y[i], ring_thickness, x_shifted[i], n_theta=n_theta)
        colour = cmap(norm(x_shifted[i]))
        ax.plot_surface(X, Y, Z, color=colour, alpha=0.92, shade=True)

    # Axis of symmetry
    z_min, z_max = float(x_shifted.min()), float(x_shifted.max())
    ax.plot(
        [0, 0], [0, 0], [z_min, z_max],
        color="#1565C0", linewidth=1.0, alpha=0.6, linestyle="--",
    )


def plot_multi_3d(
    output_path: Path,
    dpi: int = 300,
    elevation: float = -170.0,
    azimuth: float = -15.0,
    n_theta: int = 60,
    colormap: str = "plasma",
) -> Path:
    """Create a 2x2 subplot grid comparing all four nozzle geometries.

    All nozzles have their exit plane at z=0 with the inlet extending
    downward, keeping the original orientation while aligning outlets.

    Args:
        output_path: Where to save the PNG.
        dpi: Image resolution.
        elevation: 3D view elevation angle.
        azimuth: 3D view azimuth angle.
        n_theta: Circumferential resolution for ring generation.
        colormap: Matplotlib colormap name.

    Returns:
        Path to saved image.
    """
    output_path = Path(output_path)

    # Engine configs and titles in 2x2 layout order
    engines: list[tuple[str, NozzleConfig]] = [
        ("Merlin 1D", merlin_1d()),
        ("Raptor SL", raptor_sl()),
        ("RS-25", rs_25()),
        ("RL10B-2", rl10b_2()),
    ]

    # Generate all contours to compute global axis limits
    contours: list[tuple[np.ndarray, np.ndarray]] = []
    for _, cfg in engines:
        contours.append(generate_contour(cfg))

    # Global radial limit (y-axis) across all contours
    all_y = np.concatenate([c[1] for c in contours])
    global_y_max = float(all_y.max())

    # Global axial extent: minimum shifted z across all nozzles (exit at z=0)
    global_z_min = min(float(c[0].min() - c[0].max()) for c in contours)

    # Figure: single row, 4 columns
    fig = plt.figure(figsize=(20, 6))
    fig.patch.set_facecolor("white")

    for idx, (name, cfg) in enumerate(engines):
        ax = fig.add_subplot(1, 4, idx + 1, projection="3d")
        ax.set_facecolor("white")

        _draw_nozzle_on_ax(ax, cfg, z_offset=0.0, n_theta=n_theta, colormap=colormap)

        # Unified axes: exit at z=0 (bottom), inlet extends downward
        xy_diameter = global_y_max * 2
        ax.set_box_aspect([1.0, 1.0, abs(global_z_min) / xy_diameter])

        ax.set_xlim3d([-global_y_max, global_y_max])
        ax.set_ylim3d([-global_y_max, global_y_max])
        ax.set_zlim3d([global_z_min, 0.0])

        # Hide axes completely
        ax.set_axis_off()

        ax.view_init(elev=elevation, azim=azimuth)

    # Add engine names below each subplot in figure coordinates
    for idx, (name, _) in enumerate(engines):
        # Center x-position for each subplot in a 1x4 layout
        x_center = (idx + 0.5) / 4
        fig.text(x_center, 0.02, name, ha="center", va="bottom",
                 fontsize=12, fontweight="bold", color="black")

    plt.tight_layout(pad=1.5)
    # Shift subplots up to make room for labels below
    fig.subplots_adjust(bottom=0.12)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(
        output_path, dpi=dpi, bbox_inches="tight",
        facecolor="white", pad_inches=0.1,
    )
    plt.close(fig)

    return output_path


if __name__ == "__main__":
    out = Path("docs/assets/images/nozzle_comparison_3d.png")
    result = plot_multi_3d(out)
    print(f"Saved: {result}")
