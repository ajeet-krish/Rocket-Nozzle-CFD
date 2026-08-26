"""Euler vs RANS comparison plots."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation

if TYPE_CHECKING:
    from nozzle.config import NozzleConfig


def plot_mach_comparison(
    euler_vtu: Path,
    rans_vtu: Path,
    output_path: Path,
    nozzle_config: NozzleConfig | None = None,
    dpi: int = 150,
) -> Path:
    """Plot side-by-side Mach contours for Euler vs RANS.

    Uses tricontourf for filled contours. Optionally overlays the nozzle
    wall contour when nozzle_config is provided.

    Args:
        euler_vtu: Path to Euler VTU file
        rans_vtu: Path to RANS VTU file
        output_path: Path to save comparison plot
        nozzle_config: Optional NozzleConfig for wall overlay
        dpi: Image resolution

    Returns:
        Path to saved plot
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from cfd.vtu_parser import parse_vtu

    euler_data = parse_vtu(euler_vtu)
    rans_data = parse_vtu(rans_vtu)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Euler Mach contour
    if euler_data.mach is not None:
        triang1 = Triangulation(euler_data.coordinates[:, 0], euler_data.coordinates[:, 1])
        contour1 = ax1.tricontourf(triang1, euler_data.mach, levels=20, cmap='jet')
        ax1.tricontour(triang1, euler_data.mach, levels=20, colors='k', linewidths=0.3, alpha=0.5)
        plt.colorbar(contour1, ax=ax1, shrink=0.8, label="Mach")

    ax1.set_title("Euler (Inviscid)", fontsize=12)
    ax1.set_xlabel("Axial Distance (m)")
    ax1.set_ylabel("Radial Distance (m)")

    # RANS Mach contour
    if rans_data.mach is not None:
        triang2 = Triangulation(rans_data.coordinates[:, 0], rans_data.coordinates[:, 1])
        contour2 = ax2.tricontourf(triang2, rans_data.mach, levels=20, cmap='jet')
        ax2.tricontour(triang2, rans_data.mach, levels=20, colors='k', linewidths=0.3, alpha=0.5)
        plt.colorbar(contour2, ax=ax2, shrink=0.8, label="Mach")

    ax2.set_title("RANS SST (Viscous)", fontsize=12)
    ax2.set_xlabel("Axial Distance (m)")
    ax2.set_ylabel("Radial Distance (m)")

    # Overlay nozzle wall contour if config provided
    if nozzle_config is not None:
        from nozzle.geometry import generate_contour
        x_wall, y_wall = generate_contour(nozzle_config)
        for ax in [ax1, ax2]:
            ax.plot(x_wall, y_wall, 'k-', linewidth=2, label='Nozzle Wall')
            ax.plot(x_wall, -y_wall, 'k-', linewidth=2)
            ax.set_xlim(x_wall[0] * 1.1, x_wall[-1] * 1.3)
            y_max = y_wall.max() * 1.5
            ax.set_ylim(-y_max, y_max)
    else:
        ax1.set_aspect("equal")
        ax2.set_aspect("equal")

    plt.suptitle("Mach Number Comparison: Euler vs RANS", fontsize=14)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close()

    return output_path


def generate_comparison_report(
    euler_exit_mach: float,
    rans_exit_mach: float,
    output_path: Path,
) -> Path:
    """Generate markdown comparison report.

    Args:
        euler_exit_mach: Exit Mach from Euler simulation
        rans_exit_mach: Exit Mach from RANS simulation
        output_path: Path to save report

    Returns:
        Path to saved report
    """
    diff = abs(euler_exit_mach - rans_exit_mach)
    pct = diff / euler_exit_mach * 100 if euler_exit_mach != 0 else 0.0

    report = f"""# Euler vs RANS Comparison

## Exit Mach Number

| Method | Exit Mach |
|--------|-----------|
| Euler (Inviscid) | {euler_exit_mach:.4f} |
| RANS SST (Viscous) | {rans_exit_mach:.4f} |
| Difference | {diff:.4f} ({pct:.2f}%) |

## Discussion

The RANS simulation includes viscous effects (boundary layer) that are absent in the Euler simulation. This typically results in:
- Slightly lower exit Mach number due to boundary layer displacement effect
- Thinner effective flow area at the exit
- Lower thrust coefficient due to viscous losses

## Boundary Layer Effects

The boundary layer develops along the nozzle wall, creating a velocity gradient from zero at the wall (no-slip) to the freestream value. This reduces the effective flow area, causing:
- Slight deceleration of the core flow
- Reduced mass flow rate
- Lower exit Mach number

The difference between Euler and RANS results indicates the magnitude of viscous effects in the nozzle.
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    return output_path
