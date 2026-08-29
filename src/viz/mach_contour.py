"""Mach contour plotting."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation

if TYPE_CHECKING:
    from nozzle.config import NozzleConfig


def _mask_inside_nozzle(
    coords: np.ndarray,
    nozzle_config: "NozzleConfig",
) -> np.ndarray:
    """Return boolean mask for points inside the nozzle (below the wall contour).

    For each point (x, y), computes the wall y-coordinate at that x and keeps
    the point only if 0 <= y <= y_wall(x). Points outside the nozzle domain are
    excluded from the contour plot.

    Args:
        coords: (N, 3) node coordinates
        nozzle_config: Nozzle geometry parameters

    Returns:
        (N,) boolean mask, True for points inside the nozzle domain
    """
    from nozzle.geometry import generate_contour

    x_wall, y_wall = generate_contour(nozzle_config)
    x_pts = coords[:, 0]
    y_pts = coords[:, 1]

    # Interpolate wall y at each point x
    y_wall_interp = np.interp(x_pts, x_wall, y_wall)

    # Inside: y >= 0 and y <= wall y (with small tolerance for boundary points)
    tol = 1e-10
    mask = (y_pts >= -tol) & (y_pts <= y_wall_interp + tol)
    return mask


def plot_mach_contour(
    flow_vtu: Path,
    output_path: Path,
    nozzle_config: "NozzleConfig | None" = None,
    dpi: int = 150,
) -> Path:
    """Plot Mach number contour from SU2 flow.vtu.

    Uses tricontourf for filled contours instead of scatter points.
    Optionally overlays the nozzle wall contour when nozzle_config is provided.
    Contour data is clipped to the nozzle domain (top half only).

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

        # Clip to nozzle domain if config provided
        if nozzle_config is not None:
            mask = _mask_inside_nozzle(coords, nozzle_config)
            coords = coords[mask]
            mach_clamped = mach_clamped[mask]

        # Create triangulation for filled contour plot
        triang = Triangulation(coords[:, 0], coords[:, 1])

        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 4))

        # Filled contour plot with consistent scale
        contour = ax.tricontourf(
            triang, mach_clamped, levels=20, cmap='jet', vmin=0, vmax=15,
        )

        # Add contour lines for better visualization
        ax.tricontour(triang, mach_clamped, levels=20, colors='k', linewidths=0.3, alpha=0.5)

        ax.set_xlabel('Axial Distance (m)', fontsize=12)
        ax.set_ylabel('Radial Distance (m)', fontsize=12)
        ax.set_title('Mach Number Contour', fontsize=14)

        # Overlay nozzle wall contour if config provided
        if nozzle_config is not None:
            from nozzle.geometry import generate_contour
            x_wall, y_wall = generate_contour(nozzle_config)
            # Top half only
            ax.plot(x_wall, y_wall, 'k-', linewidth=2.5, label='Nozzle Wall')
            ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)

            # Set axis limits to show full nozzle (top half)
            ax.set_xlim(x_wall[0] * 1.1, x_wall[-1] * 1.3)
            y_max = y_wall.max() * 1.5
            ax.set_ylim(0, y_max)
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
    dpi: int = 150,
) -> Path:
    """Plot static pressure contour from SU2 flow.vtu.

    Uses tricontourf for filled contours. Contour data is clipped to the
    nozzle domain (top half only). Uses viridis colormap (blue=low, yellow=high).

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

        if data.pressure is None:
            print(f"Warning: No Pressure data in {flow_vtu}")
            return output_path

        coords = data.coordinates
        pressure = data.pressure

        # Clip to nozzle domain if config provided
        if nozzle_config is not None:
            mask = _mask_inside_nozzle(coords, nozzle_config)
            coords = coords[mask]
            pressure = pressure[mask]

        # Create triangulation for filled contour plot
        triang = Triangulation(coords[:, 0], coords[:, 1])

        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 4))

        # Filled contour plot (viridis: blue=low, yellow=high)
        contour = ax.tricontourf(
            triang, pressure, levels=20, cmap='viridis',
        )

        # Add contour lines for better visualization
        ax.tricontour(triang, pressure, levels=20, colors='k', linewidths=0.3, alpha=0.5)

        ax.set_xlabel('Axial Distance (m)', fontsize=12)
        ax.set_ylabel('Radial Distance (m)', fontsize=12)
        ax.set_title('Static Pressure Contour', fontsize=14)

        # Overlay nozzle wall contour if config provided
        if nozzle_config is not None:
            from nozzle.geometry import generate_contour
            x_wall, y_wall = generate_contour(nozzle_config)
            # Top half only
            ax.plot(x_wall, y_wall, 'k-', linewidth=2.5, label='Nozzle Wall')
            ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)

            # Set axis limits to show full nozzle (top half)
            ax.set_xlim(x_wall[0] * 1.1, x_wall[-1] * 1.3)
            y_max = y_wall.max() * 1.5
            ax.set_ylim(0, y_max)
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
    dpi: int = 150,
) -> Path:
    """Plot velocity magnitude contour from SU2 flow.vtu.

    Computes |V| = sqrt(Vx^2 + Vy^2) from velocity components.
    Contour data is clipped to the nozzle domain (top half only).
    Uses plasma colormap.

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

        if data.velocity_x is None or data.velocity_y is None:
            print(f"Warning: No velocity data in {flow_vtu}")
            return output_path

        coords = data.coordinates
        velocity_mag = np.sqrt(data.velocity_x**2 + data.velocity_y**2)

        # Clip to nozzle domain if config provided
        if nozzle_config is not None:
            mask = _mask_inside_nozzle(coords, nozzle_config)
            coords = coords[mask]
            velocity_mag = velocity_mag[mask]

        # Create triangulation for filled contour plot
        triang = Triangulation(coords[:, 0], coords[:, 1])

        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 4))

        # Filled contour plot (plasma colormap)
        contour = ax.tricontourf(
            triang, velocity_mag, levels=20, cmap='plasma',
        )

        # Add contour lines for better visualization
        ax.tricontour(triang, velocity_mag, levels=20, colors='k', linewidths=0.3, alpha=0.5)

        ax.set_xlabel('Axial Distance (m)', fontsize=12)
        ax.set_ylabel('Radial Distance (m)', fontsize=12)
        ax.set_title('Velocity Magnitude Contour', fontsize=14)

        # Overlay nozzle wall contour if config provided
        if nozzle_config is not None:
            from nozzle.geometry import generate_contour
            x_wall, y_wall = generate_contour(nozzle_config)
            # Top half only
            ax.plot(x_wall, y_wall, 'k-', linewidth=2.5, label='Nozzle Wall')
            ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)

            # Set axis limits to show full nozzle (top half)
            ax.set_xlim(x_wall[0] * 1.1, x_wall[-1] * 1.3)
            y_max = y_wall.max() * 1.5
            ax.set_ylim(0, y_max)
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
