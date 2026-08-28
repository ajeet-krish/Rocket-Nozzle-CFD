"""Mach contour plotting."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation

if TYPE_CHECKING:
    from nozzle.config import NozzleConfig


def plot_mach_contour(
    flow_vtu: Path,
    output_path: Path,
    nozzle_config: "NozzleConfig | None" = None,
    dpi: int = 150,
) -> Path:
    """Plot Mach number contour from SU2 flow.vtu.

    Uses tricontourf for filled contours instead of scatter points.
    Optionally overlays the nozzle wall contour when nozzle_config is provided.

    Args:
        flow_vtu: Path to SU2 flow.vtu file
        output_path: Path to save contour plot
        nozzle_config: Optional NozzleConfig for wall overlay
        dpi: Image resolution

    Returns:
        Path to saved plot
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from cfd.vtu_parser import parse_vtu

        data = parse_vtu(flow_vtu)

        if data.mach is None:
            print(f"Warning: No Mach data in {flow_vtu}")
            return output_path

        coords = data.coordinates
        mach = data.mach

        # Clamp Mach to reasonable range for color scale
        # (diverged solutions can produce garbage values like Mach 400+)
        mach_clamped = np.clip(mach, 0, 20)

        # Create triangulation for filled contour plot
        triang = Triangulation(coords[:, 0], coords[:, 1])

        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 4))

        # Filled contour plot with consistent scale
        contour = ax.tricontourf(
            triang, mach_clamped, levels=20, cmap='jet', vmin=0, vmax=15,
        )

        # Add contour lines for better visualization
        ax.tricontour(triang, mach, levels=20, colors='k', linewidths=0.3, alpha=0.5)

        ax.set_xlabel('Axial Distance (m)', fontsize=12)
        ax.set_ylabel('Radial Distance (m)', fontsize=12)
        ax.set_title('Mach Number Contour', fontsize=14)

        # Overlay nozzle wall contour if config provided
        if nozzle_config is not None:
            from nozzle.geometry import generate_contour
            x_wall, y_wall = generate_contour(nozzle_config)
            ax.plot(x_wall, y_wall, 'k-', linewidth=2.5, label='Nozzle Wall')
            ax.plot(x_wall, -y_wall, 'k-', linewidth=2.5)

            # Set axis limits to show full nozzle
            ax.set_xlim(x_wall[0] * 1.1, x_wall[-1] * 1.3)
            y_max = y_wall.max() * 1.5
            ax.set_ylim(-y_max, y_max)
        else:
            ax.set_aspect('equal')

        # Add colorbar
        cbar = plt.colorbar(contour, ax=ax, shrink=0.8)
        cbar.set_label('Mach Number', fontsize=11)

        plt.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        return output_path

    except Exception as e:
        print(f"Error plotting Mach contour: {e}")
        return output_path
