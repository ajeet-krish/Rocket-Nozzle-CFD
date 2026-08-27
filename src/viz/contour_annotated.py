"""Annotated 2D nozzle contour visualization with color-coded sections.

Provides publication-quality contour plots with dimension callouts, angle arcs,
and color-coded sections (entrant, throat, bell) following AK-Vortex Ocean dark theme.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyArrowPatch

if TYPE_CHECKING:
    from src.nozzle.config import NozzleConfig


@dataclass
class NozzleSections:
    """Decomposed nozzle contour sections for annotation.

    Attributes:
        entrant_arc_x: Axial coordinates of entrant arc section
        entrant_arc_y: Radial coordinates of entrant arc section
        exit_arc_x: Axial coordinates of exit arc section
        exit_arc_y: Radial coordinates of exit arc section
        bell_x: Axial coordinates of bell (main divergent) section
        bell_y: Radial coordinates of bell (main divergent) section
        throat_idx: Index of the throat plane in the full contour
        theta_n: Wall angle at throat (degrees)
        theta_e: Exit wall angle (degrees)
    """
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
    """Split the (x, y) contour into three visual sections for annotation.

    Sections:
        1. Entrant arc (green): last 20% of convergent points (x < 0)
        2. Exit arc (red): first 15% of divergent points (x > 0)
        3. Bell (blue): remaining divergent points

    Args:
        x: Axial coordinates from generate_contour()
        y: Radial coordinates from generate_contour()
        config: Nozzle configuration

    Returns:
        NozzleSections dataclass with decomposed arrays
    """
    # Find throat index (closest to x = 0)
    throat_idx = int(np.argmin(np.abs(x)))

    # Separate convergent and divergent regions
    convergent_mask = x < 0
    divergent_mask = x > 0

    conv_indices = np.where(convergent_mask)[0]
    div_indices = np.where(divergent_mask)[0]

    # Entrant arc: last 20% of convergent points
    n_entrant = max(1, int(len(conv_indices) * 0.20))
    entrant_start = conv_indices[-n_entrant]
    entrant_arc_x = x[entrant_start: throat_idx + 1]
    entrant_arc_y = y[entrant_start: throat_idx + 1]

    # Exit arc: first 15% of divergent points
    n_exit = max(1, int(len(div_indices) * 0.15))
    exit_end = div_indices[n_exit - 1] + 1
    exit_arc_x = x[throat_idx: exit_end]
    exit_arc_y = y[throat_idx: exit_end]

    # Bell: remaining divergent points
    bell_x = x[exit_end - 1:]
    bell_y = y[exit_end - 1:]

    return NozzleSections(
        entrant_arc_x=entrant_arc_x,
        entrant_arc_y=entrant_arc_y,
        exit_arc_x=exit_arc_x,
        exit_arc_y=exit_arc_y,
        bell_x=bell_x,
        bell_y=bell_y,
        throat_idx=throat_idx,
        theta_n=config.theta_n,
        theta_e=config.theta_e,
    )


def plot_annotated_contour(
    config: NozzleConfig,
    output_path: str | Path,
    dpi: int = 150,
    show_dimensions: bool = True,
    show_angles: bool = True,
    show_arc_labels: bool = True,
) -> Path:
    """Create a publication-quality annotated 2D nozzle contour plot.

    Generates the nozzle contour, decomposes it into color-coded sections
    (entrant arc, exit arc, bell), and adds dimension callouts and angle arcs.

    Args:
        config: Nozzle geometry configuration
        output_path: Path to save the PNG image
        dpi: Image resolution (dots per inch)
        show_dimensions: If True, show dimension lines for Rt, Re, Ln
        show_angles: If True, show angle arcs for theta_n and theta_e
        show_arc_labels: If True, show text labels for each section

    Returns:
        Path to the saved image file
    """
    from src.nozzle.geometry import generate_contour

    output_path = Path(output_path)

    # Generate full contour
    x_full, y_full = generate_contour(config)

    # Decompose into sections
    sections = decompose_sections(x_full, y_full, config)

    # Compute key dimensions
    rt = config.throat_radius
    re = config.exit_radius
    ln = config.diverging_length

    # AK-Vortex Ocean dark theme
    bg_color = "#0a1628"
    text_color = "#e0e8f0"
    grid_color = "#1a2d4a"
    green = "#4caf50"
    red = "#ff6b6b"
    cyan = "#00e5ff"

    # Create figure with dark background
    fig, ax = plt.subplots(1, 1, figsize=(14, 5))
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    # Plot each section with its color
    ax.plot(
        sections.entrant_arc_x, sections.entrant_arc_y,
        color=green, linewidth=2.5, label="Entrant Arc",
        solid_capstyle="round",
    )
    ax.plot(
        sections.exit_arc_x, sections.exit_arc_y,
        color=red, linewidth=2.5, label="Exit Arc",
        solid_capstyle="round",
    )
    ax.plot(
        sections.bell_x, sections.bell_y,
        color=cyan, linewidth=2.5, label="Bell",
        solid_capstyle="round",
    )

    # Mirror below axis
    ax.plot(
        sections.entrant_arc_x, -sections.entrant_arc_y,
        color=green, linewidth=2.5,
        solid_capstyle="round",
    )
    ax.plot(
        sections.exit_arc_x, -sections.exit_arc_y,
        color=red, linewidth=2.5,
        solid_capstyle="round",
    )
    ax.plot(
        sections.bell_x, -sections.bell_y,
        color=cyan, linewidth=2.5,
        solid_capstyle="round",
    )

    # Draw axis of symmetry
    x_min = x_full[0]
    x_max = x_full[-1]
    ax.plot(
        [x_min * 1.05, x_max * 1.05], [0, 0],
        color=text_color, linestyle="--", linewidth=0.8, alpha=0.6,
        label="Axis of Symmetry",
    )

    # Dimension lines
    if show_dimensions:
        # Throat radius: vertical arrow at x = 0
        ax.annotate(
            "",
            xy=(0, rt), xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="<->", color=text_color, lw=1.2,
                shrinkA=0, shrinkB=0,
            ),
        )
        ax.text(
            -ln * 0.02, rt * 0.5, f"$R_t$ = {rt * 1000:.1f} mm",
            color=text_color, fontsize=9, ha="right", va="center",
            fontweight="bold",
        )

        # Exit radius: vertical arrow at x = L_diverge
        ax.annotate(
            "",
            xy=(ln, re), xytext=(ln, 0),
            arrowprops=dict(
                arrowstyle="<->", color=text_color, lw=1.2,
                shrinkA=0, shrinkB=0,
            ),
        )
        ax.text(
            ln + ln * 0.01, re * 0.5, f"$R_e$ = {re * 1000:.1f} mm",
            color=text_color, fontsize=9, ha="left", va="center",
            fontweight="bold",
        )

        # Nozzle length: horizontal arrow along x-axis
        ax.annotate(
            "",
            xy=(ln, -rt * 0.8), xytext=(0, -rt * 0.8),
            arrowprops=dict(
                arrowstyle="<->", color=text_color, lw=1.2,
                shrinkA=0, shrinkB=0,
            ),
        )
        ax.text(
            ln * 0.5, -rt * 1.1, f"$L_n$ = {ln * 1000:.1f} mm",
            color=text_color, fontsize=9, ha="center", va="top",
            fontweight="bold",
        )

    # Angle arcs
    if show_angles:
        # theta_n arc at throat
        theta_n_deg = config.theta_n
        arc_radius_rt = rt * 0.6
        arc_n = Arc(
            (0, rt), 2 * arc_radius_rt, 2 * arc_radius_rt,
            angle=0, theta1=0, theta2=theta_n_deg,
            color=green, linewidth=1.5, linestyle="-",
        )
        ax.add_patch(arc_n)
        # Label at midpoint of arc
        mid_angle_n = np.radians(theta_n_deg / 2)
        label_x_n = arc_radius_rt * 0.65 * np.cos(mid_angle_n)
        label_y_n = rt + arc_radius_rt * 0.65 * np.sin(mid_angle_n)
        ax.text(
            label_x_n, label_y_n, f"$\\theta_n$={config.theta_n:.0f}$^\\circ$",
            color=green, fontsize=8, ha="center", va="bottom",
            fontweight="bold",
        )

        # theta_e arc at exit
        theta_e_rad = config.theta_e
        if theta_e_rad > 0:
            arc_radius_re = re * 0.15
            arc_e = Arc(
                (ln, re), 2 * arc_radius_re, 2 * arc_radius_re,
                angle=0, theta1=-theta_e_rad, theta2=0,
                color=red, linewidth=1.5, linestyle="-",
            )
            ax.add_patch(arc_e)
            mid_angle_e = np.radians(-theta_e_rad / 2)
            label_x_e = ln + arc_radius_re * 0.65 * np.cos(mid_angle_e)
            label_y_e = re + arc_radius_re * 0.65 * np.sin(mid_angle_e)
            ax.text(
                label_x_e, label_y_e, f"$\\theta_e$={config.theta_e:.0f}$^\\circ$",
                color=red, fontsize=8, ha="center", va="top",
                fontweight="bold",
            )

    # Arc labels
    if show_arc_labels:
        # Entrant arc label
        entrant_mid = len(sections.entrant_arc_x) // 2
        ax.text(
            sections.entrant_arc_x[entrant_mid],
            sections.entrant_arc_y[entrant_mid] * 1.15,
            "Entrant Arc",
            color=green, fontsize=9, ha="center", va="bottom",
            fontweight="bold",
        )

        # Exit arc label
        exit_mid = len(sections.exit_arc_x) // 2
        ax.text(
            sections.exit_arc_x[exit_mid],
            sections.exit_arc_y[exit_mid] * 1.15,
            "Exit Arc",
            color=red, fontsize=9, ha="center", va="bottom",
            fontweight="bold",
        )

        # Bell label
        bell_mid = len(sections.bell_x) // 2
        ax.text(
            sections.bell_x[bell_mid],
            sections.bell_y[bell_mid] * 1.08,
            "Bell",
            color=cyan, fontsize=9, ha="center", va="bottom",
            fontweight="bold",
        )

    # Title
    ax.set_title(
        "Converging-Diverging Nozzle Geometry",
        color=text_color, fontsize=14, fontweight="bold", pad=12,
    )

    # Axis labels
    ax.set_xlabel("Axial Distance (m)", color=text_color, fontsize=11)
    ax.set_ylabel("Radial Distance (m)", color=text_color, fontsize=11)

    # Grid
    ax.grid(True, color=grid_color, alpha=0.4, linewidth=0.5)
    ax.set_axisbelow(True)

    # Tick styling
    ax.tick_params(colors=text_color, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(grid_color)

    # Set symmetric y-limits with padding
    y_max = y_full.max() * 1.3
    ax.set_xlim(x_min * 1.05, x_max * 1.15)
    ax.set_ylim(-y_max, y_max)

    # Legend
    legend = ax.legend(
        loc="upper left", fontsize=9, framealpha=0.3,
        edgecolor=grid_color, facecolor=bg_color,
    )
    for text in legend.get_texts():
        text.set_color(text_color)

    # Save
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor=bg_color)
    plt.close()

    return output_path
