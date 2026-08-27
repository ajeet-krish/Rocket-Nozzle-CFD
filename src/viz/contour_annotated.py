"""Annotated 2D nozzle contour visualization.

Publication-quality engineering drawing with color-coded sections,
dimension callouts, and angle annotations. White-background scientific
styling suitable for reports and documentation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour


@dataclass
class NozzleSections:
    """Decomposed nozzle contour sections for annotation."""

    entrant_arc_x: np.ndarray
    entrant_arc_y: np.ndarray
    exit_arc_x: np.ndarray
    exit_arc_y: np.ndarray
    bell_x: np.ndarray
    bell_y: np.ndarray
    throat_idx: int
    theta_n: float
    theta_e: float


def decompose_sections(
    x: np.ndarray,
    y: np.ndarray,
    config: NozzleConfig,
) -> NozzleSections:
    """Split contour into entrant arc, exit arc, and bell sections.

    Section boundaries are identified by the throat plane (x=0) and
    fixed fractions of the convergent/divergent regions.
    """
    # Throat index: closest point to x=0
    throat_idx = int(np.argmin(np.abs(x)))

    # Convergent region: x <= 0
    conv_mask = x <= 0
    conv_indices = np.where(conv_mask)[0]

    # Divergent region: x >= 0
    div_mask = x >= 0
    div_indices = np.where(div_mask)[0]

    # Entrant arc: last 25% of convergent (near throat, highest curvature)
    n_entrant = max(int(len(conv_indices) * 0.25), 3)
    entrant_start = max(len(conv_indices) - n_entrant, 0)
    entrant_idx = conv_indices[entrant_start:]

    # Exit arc: first 15% of divergent (near throat)
    n_exit = max(int(len(div_indices) * 0.15), 3)
    exit_idx = div_indices[:n_exit]

    # Bell: remaining divergent
    bell_idx = div_indices[n_exit:]

    return NozzleSections(
        entrant_arc_x=x[entrant_idx],
        entrant_arc_y=y[entrant_idx],
        exit_arc_x=x[exit_idx],
        exit_arc_y=y[exit_idx],
        bell_x=x[bell_idx],
        bell_y=y[bell_idx],
        throat_idx=throat_idx,
        theta_n=config.theta_n,
        theta_e=config.theta_e,
    )


def plot_annotated_contour(
    config: NozzleConfig,
    output_path: Path,
    dpi: int = 200,
    show_dimensions: bool = True,
    show_angles: bool = True,
    show_arc_labels: bool = True,
    engine_name: str = "Nozzle",
) -> Path:
    """Plot annotated 2D nozzle contour with dimension callouts.

    Creates a publication-quality engineering drawing with:
    - Color-coded sections: green (entrant), red (exit arc), blue (bell)
    - Mirrored profile below axis of symmetry
    - Dimension lines for Rt, Re, Ln
    - Angle arcs for theta_n and theta_e
    - White background, LaTeX-style font
    """
    output_path = Path(output_path)

    # Generate contour
    x, y = generate_contour(config)
    sections = decompose_sections(x, y, config)

    # --- Figure ---
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # --- Mirrored profile ---
    ax.plot(x, y, color="#1565C0", linewidth=2.0, label="Wall", zorder=5)
    ax.plot(x, -y, color="#1565C0", linewidth=2.0, zorder=5)

    # --- Color-coded sections (top half) ---
    ax.plot(
        sections.entrant_arc_x, sections.entrant_arc_y,
        color="#2E7D32", linewidth=3.0, label="Entrant arc", zorder=6,
    )
    ax.plot(
        sections.exit_arc_x, sections.exit_arc_y,
        color="#C62828", linewidth=3.0, label="Exit arc", zorder=6,
    )
    ax.plot(
        sections.bell_x, sections.bell_y,
        color="#1565C0", linewidth=3.0, label="Bell (Rao)", zorder=6,
    )

    # --- Axis of symmetry ---
    ax.axhline(
        y=0, color="black", linestyle="--", linewidth=0.8,
        label="Axis", zorder=4,
    )

    # --- Dimension annotations ---
    if show_dimensions:
        r_exit = config.exit_radius
        r_throat = config.throat_radius
        ln = config.computed_diverging_length
        x_start = -config.converging_length - config.chamber_length
        r_inlet = config.effective_inlet_radius

        # Relative offsets based on nozzle dimensions
        h_offset = 0.02 * ln  # horizontal offset for text labels
        v_offset = 0.08 * r_exit  # vertical offset for horizontal arrows

        # Throat radius: vertical line at x=0
        ax.annotate(
            "", xy=(0, r_throat), xytext=(0, 0),
            arrowprops=dict(arrowstyle="<->", color="#333", lw=1.0),
        )
        ax.text(
            h_offset, r_throat / 2, f"$R_t$ = {r_throat*1000:.0f} mm",
            fontsize=9, color="#333", va="center",
        )

        # Exit radius: vertical line at exit
        ax.annotate(
            "", xy=(ln, r_exit), xytext=(ln, 0),
            arrowprops=dict(arrowstyle="<->", color="#333", lw=1.0),
        )
        ax.text(
            ln + h_offset, r_exit / 2, f"$R_e$ = {r_exit*1000:.0f} mm",
            fontsize=9, color="#333", va="center",
        )

        # Nozzle length: horizontal line along axis
        ax.annotate(
            "", xy=(ln, -v_offset), xytext=(0, -v_offset),
            arrowprops=dict(arrowstyle="<->", color="#333", lw=1.0),
        )
        ax.text(
            ln / 2, -1.5 * v_offset, f"$L_n$ = {ln:.2f} m",
            fontsize=9, color="#333", ha="center",
        )

        # Inlet radius: vertical line at chamber start
        ax.annotate(
            "", xy=(x_start, r_inlet), xytext=(x_start, 0),
            arrowprops=dict(arrowstyle="<->", color="#333", lw=1.0),
        )
        ax.text(
            x_start - h_offset, r_inlet / 2, f"$R_i$ = {r_inlet*1000:.0f} mm",
            fontsize=9, color="#333", va="center", ha="right",
        )

    # --- Angle annotations ---
    if show_angles and config.theta_n > 0:
        # theta_n at throat exit
        arc_r = config.exit_radius * 0.12
        theta_n_rad = np.radians(config.theta_n)
        angle_arc_x = sections.exit_arc_x[-1] if len(sections.exit_arc_x) > 0 else 0
        angle_arc_y = sections.exit_arc_y[-1] if len(sections.exit_arc_y) > 0 else r_throat

        # Draw angle arc
        theta_range = np.linspace(0, theta_n_rad, 30)
        arc_x = angle_arc_x + arc_r * np.cos(theta_range - np.pi / 2)
        arc_y = angle_arc_y + arc_r * np.sin(theta_range - np.pi / 2)
        ax.plot(arc_x, arc_y, color="#333", linewidth=0.8)
        ax.text(
            angle_arc_x + arc_r * 1.3, angle_arc_y,
            f"$\\theta_n$ = {config.theta_n:.1f}$^\\circ$",
            fontsize=8, color="#333",
        )

    # --- Labels and grid ---
    ax.set_xlabel("Axial Distance (m)", fontsize=12, color="black")
    ax.set_ylabel("Radial Distance (m)", fontsize=12, color="black")
    ax.set_title(
        f"{engine_name} 2D Geometry  --  $\\epsilon$ = {config.expansion_ratio:.0f}:1"
        f",  $R_t$ = {config.throat_radius*1000:.0f} mm",
        fontsize=13, color="black", pad=12,
    )
    ax.legend(fontsize=9, loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
    ax.tick_params(colors="black", labelsize=10)
    ax.set_aspect("equal")

    # --- Save ---
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return output_path
