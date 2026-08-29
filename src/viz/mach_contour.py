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
    engine_name: str = "Nozzle",
    is_plume: bool = False,
    dpi: int = 150,
) -> Path:
    """Plot Mach number contour from SU2 flow.vtu.

    Uses tricontourf for filled contours instead of scatter points.
    Optionally overlays the nozzle wall contour when nozzle_config is provided.

    Args:
        flow_vtu: Path to SU2 flow.vtu file
        output_path: Path to save contour plot
        nozzle_config: Optional NozzleConfig for wall overlay
        engine_name: Engine name for plot title
        is_plume: If True, extend axis limits to include plume domain
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
            triang, mach_clamped, levels=50, cmap='jet', vmin=0, vmax=15,
        )

        # Add contour lines for better visualization
        ax.tricontour(triang, mach_clamped, levels=50, colors='k', linewidths=0.3, alpha=0.5)

        ax.set_xlabel('Axial Distance (m)', fontsize=12)
        ax.set_ylabel('Radial Distance (m)', fontsize=12)
        ax.set_title(f'{engine_name} Mach Number Contour', fontsize=14)

        # Overlay nozzle wall contour and set axis limits
        if nozzle_config is not None:
            from nozzle.geometry import generate_contour
            x_wall, y_wall = generate_contour(nozzle_config)
            # Top half only
            ax.plot(x_wall, y_wall, 'k-', linewidth=2.5, label='Nozzle Wall')
            ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)

            x_min, x_max = x_wall[0], x_wall[-1]
            y_max_wall = y_wall.max()

            if is_plume:
                # Plume plots: extend to show full domain
                ax.set_xlim(x_min * 1.1, x_max * 1.3)
                ax.set_ylim(0, y_max_wall * 1.5)
            else:
                # Non-plume plots: show only nozzle domain with 5% padding
                ax.set_xlim(x_min * 1.05, x_max * 1.05)
                ax.set_ylim(0, y_max_wall * 1.05)
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


def plot_pressure_contour(
    flow_vtu: Path,
    output_path: Path,
    nozzle_config: "NozzleConfig | None" = None,
    engine_name: str = "Nozzle",
    is_plume: bool = False,
    dpi: int = 150,
) -> Path:
    """Plot static pressure contour from SU2 flow.vtu.

    Uses tricontourf for filled contours. Uses viridis colormap
    (blue=low, yellow=high).

    Args:
        flow_vtu: Path to SU2 flow.vtu file
        output_path: Path to save contour plot
        nozzle_config: Optional NozzleConfig for wall overlay
        engine_name: Engine name for plot title
        is_plume: If True, extend axis limits to include plume domain
        dpi: Image resolution

    Returns:
        Path to saved plot
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from cfd.vtu_parser import parse_vtu

        data = parse_vtu(flow_vtu)

        if data.pressure is None:
            print(f"Warning: No Pressure data in {flow_vtu}")
            return output_path

        coords = data.coordinates
        pressure = data.pressure

        # Create triangulation for filled contour plot
        triang = Triangulation(coords[:, 0], coords[:, 1])

        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 4))

        # Filled contour plot (viridis: blue=low, yellow=high)
        contour = ax.tricontourf(
            triang, pressure, levels=50, cmap='viridis',
        )

        # Add contour lines for better visualization
        ax.tricontour(triang, pressure, levels=50, colors='k', linewidths=0.3, alpha=0.5)

        ax.set_xlabel('Axial Distance (m)', fontsize=12)
        ax.set_ylabel('Radial Distance (m)', fontsize=12)
        ax.set_title(f'{engine_name} Pressure Contour', fontsize=14)

        # Overlay nozzle wall contour and set axis limits
        if nozzle_config is not None:
            from nozzle.geometry import generate_contour
            x_wall, y_wall = generate_contour(nozzle_config)
            # Top half only
            ax.plot(x_wall, y_wall, 'k-', linewidth=2.5, label='Nozzle Wall')
            ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)

            x_min, x_max = x_wall[0], x_wall[-1]
            y_max_wall = y_wall.max()

            if is_plume:
                ax.set_xlim(x_min * 1.1, x_max * 1.3)
                ax.set_ylim(0, y_max_wall * 1.5)
            else:
                ax.set_xlim(x_min * 1.05, x_max * 1.05)
                ax.set_ylim(0, y_max_wall * 1.05)
        else:
            ax.set_aspect('equal')

        # Add colorbar
        cbar = plt.colorbar(contour, ax=ax, shrink=0.8)
        cbar.set_label('Static Pressure (Pa)', fontsize=11)

        plt.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        return output_path

    except Exception as e:
        print(f"Error plotting pressure contour: {e}")
        return output_path


def plot_velocity_contour(
    flow_vtu: Path,
    output_path: Path,
    nozzle_config: "NozzleConfig | None" = None,
    engine_name: str = "Nozzle",
    is_plume: bool = False,
    gamma: float = 1.4,
    dpi: int = 150,
) -> Path:
    """Plot velocity magnitude contour from SU2 flow.vtu.

    Tries to read velocity components from VTU. If unavailable (e.g. Euler
    solver), computes velocity from Mach and temperature: V = M * sqrt(gamma * R * T).
    If neither data is available, skips gracefully with a warning.

    Args:
        flow_vtu: Path to SU2 flow.vtu file
        output_path: Path to save contour plot
        nozzle_config: Optional NozzleConfig for wall overlay
        engine_name: Engine name for plot title
        is_plume: If True, extend axis limits to include plume domain
        gamma: Ratio of specific heats (default 1.4)
        dpi: Image resolution

    Returns:
        Path to saved plot
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from cfd.vtu_parser import parse_vtu

        data = parse_vtu(flow_vtu)

        R_gas = 287.05  # J/(kg*K) specific gas constant for air
        velocity_mag = None

        # Try direct velocity components first
        if data.velocity_x is not None and data.velocity_y is not None:
            velocity_mag = np.sqrt(data.velocity_x**2 + data.velocity_y**2)

        # Fall back to computation from Mach and temperature
        if velocity_mag is None and data.mach is not None and data.temperature is not None:
            print(f"  Computing velocity from Mach and temperature (Euler solver)")
            velocity_mag = data.mach * np.sqrt(gamma * R_gas * data.temperature)

        if velocity_mag is None:
            print(f"Warning: No velocity data available in {flow_vtu} (need velocity components or Mach+T)")
            return output_path

        coords = data.coordinates

        # Create triangulation for filled contour plot
        triang = Triangulation(coords[:, 0], coords[:, 1])

        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 4))

        # Filled contour plot (plasma colormap)
        contour = ax.tricontourf(
            triang, velocity_mag, levels=50, cmap='plasma',
        )

        # Add contour lines for better visualization
        ax.tricontour(triang, velocity_mag, levels=50, colors='k', linewidths=0.3, alpha=0.5)

        ax.set_xlabel('Axial Distance (m)', fontsize=12)
        ax.set_ylabel('Radial Distance (m)', fontsize=12)
        ax.set_title(f'{engine_name} Velocity Contour', fontsize=14)

        # Overlay nozzle wall contour and set axis limits
        if nozzle_config is not None:
            from nozzle.geometry import generate_contour
            x_wall, y_wall = generate_contour(nozzle_config)
            # Top half only
            ax.plot(x_wall, y_wall, 'k-', linewidth=2.5, label='Nozzle Wall')
            ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)

            x_min, x_max = x_wall[0], x_wall[-1]
            y_max_wall = y_wall.max()

            if is_plume:
                ax.set_xlim(x_min * 1.1, x_max * 1.3)
                ax.set_ylim(0, y_max_wall * 1.5)
            else:
                ax.set_xlim(x_min * 1.05, x_max * 1.05)
                ax.set_ylim(0, y_max_wall * 1.05)
        else:
            ax.set_aspect('equal')

        # Add colorbar
        cbar = plt.colorbar(contour, ax=ax, shrink=0.8)
        cbar.set_label('Velocity (m/s)', fontsize=11)

        plt.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        return output_path

    except Exception as e:
        print(f"Error plotting velocity contour: {e}")
        return output_path
