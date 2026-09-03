"""Plume visualization for shock diamond analysis.

Generates multiple views of the extended plume domain:
1. Mach number contour (full plume, both halves)
2. Static pressure contour (full plume)
3. Centerline Mach distribution (shock diamond quantification)
4. Multi-panel comparison figure

All plots show the FULL symmetric plume (both top and bottom halves)
to visualize the complete diamond shape.
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from cfd.vtu_parser import parse_vtu
from nozzle.config import NozzleConfig


def _mirror_vtu_data(data):
    """Mirror VTU data across y=0 to show full symmetric plume.

    The axisymmetric simulation only computes y >= 0.
    This function duplicates all points and data with y negated,
    creating the full symmetric field for visualization.

    Returns:
        coords_mirrored: (2N, 2) coordinates
        mach_mirrored: (2N,) Mach values
        pressure_mirrored: (2N,) pressure values
    """
    coords = data.coordinates
    mach = data.mach
    pressure = data.pressure

    # Mirror coordinates: negate y
    coords_mirror = coords.copy()
    coords_mirror[:, 1] = -coords[:, 1]

    # Concatenate original + mirrored
    coords_full = np.vstack([coords, coords_mirror])
    mach_full = np.concatenate([mach, mach])
    pressure_full = np.concatenate([pressure, pressure])

    return coords_full, mach_full, pressure_full


def plot_plume_mach(
    flow_vtu: Path,
    output_path: Path,
    nozzle_config: NozzleConfig | None = None,
    engine_name: str = "Merlin 1D",
    dpi: int = 300,
) -> Path:
    """Plot Mach number contour for extended plume (full symmetric view).

    Shows both top and bottom halves to visualize the complete diamond shape.
    """
    data = parse_vtu(flow_vtu)
    coords, mach, _ = _mirror_vtu_data(data)
    mach = np.clip(mach, 0, 15)

    triang = Triangulation(coords[:, 0], coords[:, 1])

    fig, ax = plt.subplots(1, 1, figsize=(16, 6))

    contour = ax.tricontourf(
        triang, mach, levels=60, cmap='jet', vmin=0, vmax=10,
    )
    ax.tricontour(triang, mach, levels=60, colors='k', linewidths=0.2, alpha=0.4)

    # Overlay nozzle wall (both halves)
    if nozzle_config is not None:
        from nozzle.geometry import generate_contour
        x_wall, y_wall = generate_contour(nozzle_config)
        ax.plot(x_wall, y_wall, 'k-', linewidth=2.5, label='Nozzle Wall')
        ax.plot(x_wall, -y_wall, 'k-', linewidth=2.5)
        x_min = x_wall[0]
        # Mark nozzle exit
        x_exit = nozzle_config.computed_diverging_length
        ax.axvline(x=x_exit, color='gray', linestyle=':', alpha=0.5, linewidth=1.5)
        ax.annotate('Nozzle Exit', xy=(x_exit, 0), xytext=(x_exit - 0.3, -0.4),
                    fontsize=9, color='gray', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color='gray'))
    else:
        x_min = coords[:, 0].min()

    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)

    # Symmetric y limits
    y_max = max(abs(coords[:, 1].min()), abs(coords[:, 1].max()))
    ax.set_xlim(x_min * 1.1, coords[:, 0].max() * 1.02)
    ax.set_ylim(-y_max * 1.05, y_max * 1.05)

    ax.set_xlabel('Axial Distance (m)', fontsize=13)
    ax.set_ylabel('Radial Distance (m)', fontsize=13)
    ax.set_title(f'{engine_name} -- Mach Number Contour (Full Plume)', fontsize=14)
    ax.set_aspect('auto')

    cbar = plt.colorbar(contour, ax=ax, shrink=0.85, pad=0.02)
    cbar.set_label('Mach Number', fontsize=12)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    return output_path


def plot_plume_pressure(
    flow_vtu: Path,
    output_path: Path,
    nozzle_config: NozzleConfig | None = None,
    engine_name: str = "Merlin 1D",
    dpi: int = 300,
) -> Path:
    """Plot static pressure contour for extended plume (full symmetric view)."""
    data = parse_vtu(flow_vtu)
    coords, _, pressure = _mirror_vtu_data(data)

    triang = Triangulation(coords[:, 0], coords[:, 1])

    fig, ax = plt.subplots(1, 1, figsize=(16, 6))

    # Use symmetric log scale for pressure
    from matplotlib.colors import SymLogNorm
    norm = SymLogNorm(linthresh=1000, vmin=pressure.min(), vmax=pressure.max())
    contour = ax.tricontourf(
        triang, pressure, levels=60, cmap='RdYlBu_r', norm=norm,
    )
    ax.tricontour(triang, pressure, levels=60, colors='k', linewidths=0.2, alpha=0.4)

    if nozzle_config is not None:
        from nozzle.geometry import generate_contour
        x_wall, y_wall = generate_contour(nozzle_config)
        ax.plot(x_wall, y_wall, 'k-', linewidth=2.5)
        ax.plot(x_wall, -y_wall, 'k-', linewidth=2.5)
        x_min = x_wall[0]
    else:
        x_min = coords[:, 0].min()

    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    y_max = max(abs(coords[:, 1].min()), abs(coords[:, 1].max()))
    ax.set_xlim(x_min * 1.1, coords[:, 0].max() * 1.02)
    ax.set_ylim(-y_max * 1.05, y_max * 1.05)

    ax.set_xlabel('Axial Distance (m)', fontsize=13)
    ax.set_ylabel('Radial Distance (m)', fontsize=13)
    ax.set_title(f'{engine_name} -- Static Pressure Contour (Full Plume)', fontsize=14)
    ax.set_aspect('auto')

    cbar = plt.colorbar(contour, ax=ax, shrink=0.85, pad=0.02)
    cbar.set_label('Static Pressure (Pa)', fontsize=12)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    return output_path


def plot_centerline_mach(
    flow_vtu: Path,
    output_path: Path,
    nozzle_exit_x: float,
    engine_name: str = "Merlin 1D",
    dpi: int = 300,
) -> Path:
    """Plot Mach number distribution along the nozzle centerline."""
    data = parse_vtu(flow_vtu)
    coords = data.coordinates
    mach = data.mach

    # Extract centerline (y near 0)
    y_threshold = 0.02
    centerline_mask = np.abs(coords[:, 1]) < y_threshold
    downstream_mask = coords[:, 0] > nozzle_exit_x - 0.1
    mask = centerline_mask & downstream_mask

    x_cl = coords[mask, 0]
    mach_cl = mach[mask]

    sort_idx = np.argsort(x_cl)
    x_sorted = x_cl[sort_idx]
    mach_sorted = mach_cl[sort_idx]

    from scipy.ndimage import uniform_filter1d
    mach_smooth = uniform_filter1d(mach_sorted, size=3)

    fig, ax = plt.subplots(1, 1, figsize=(14, 5))

    ax.plot(x_sorted, mach_sorted, 'b-', linewidth=0.8, alpha=0.5, label='Raw')
    ax.plot(x_sorted, mach_smooth, 'r-', linewidth=2, label='Smoothed')

    # Mark local minima (shock diamonds)
    diffs = np.diff(mach_smooth)
    sign_changes = np.diff(np.sign(diffs))
    minima_idx = np.where(sign_changes > 0)[0] + 1

    diamond_count = 0
    if len(minima_idx) > 0:
        for idx in minima_idx:
            if idx < len(mach_smooth):
                local_avg = np.mean(mach_smooth[max(0, idx-20):idx+20])
                if mach_smooth[idx] < local_avg * 0.95:
                    ax.plot(x_sorted[idx], mach_smooth[idx], 'rv',
                            markersize=8, markeredgewidth=2)
                    diamond_count += 1

    ax.set_xlabel('Axial Distance from Throat (m)', fontsize=13)
    ax.set_ylabel('Mach Number', fontsize=13)
    ax.set_title(f'{engine_name} -- Centerline Mach ({diamond_count} shock diamonds detected)', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    ax.axvline(x=nozzle_exit_x, color='gray', linestyle=':', alpha=0.7, label='Nozzle Exit')

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    return output_path


def plot_plume_multiview(
    flow_vtu: Path,
    output_path: Path,
    nozzle_config: NozzleConfig | None = None,
    engine_name: str = "Merlin 1D",
    dpi: int = 300,
) -> Path:
    """Create multi-panel figure: Mach, Pressure, and Density Gradient (full symmetric view)."""
    data = parse_vtu(flow_vtu)
    coords, mach, pressure = _mirror_vtu_data(data)
    mach = np.clip(mach, 0, 15)

    # Compute density gradient on mirrored data
    from viz.postprocessing import compute_density_gradient
    grad = compute_density_gradient(data)
    grad_full = np.concatenate([grad, grad])

    triang = Triangulation(coords[:, 0], coords[:, 1])

    fig, axes = plt.subplots(3, 1, figsize=(16, 14))

    # Panel 1: Mach
    ax = axes[0]
    c1 = ax.tricontourf(triang, mach, levels=60, cmap='jet', vmin=0, vmax=10)
    ax.tricontour(triang, mach, levels=60, colors='k', linewidths=0.2, alpha=0.3)
    if nozzle_config is not None:
        from nozzle.geometry import generate_contour
        x_wall, y_wall = generate_contour(nozzle_config)
        ax.plot(x_wall, y_wall, 'k-', linewidth=2)
        ax.plot(x_wall, -y_wall, 'k-', linewidth=2)
    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    ax.set_title(f'{engine_name} -- Mach Number', fontsize=13)
    ax.set_ylabel('Radial (m)', fontsize=11)
    plt.colorbar(c1, ax=ax, shrink=0.8, pad=0.01)

    # Panel 2: Pressure
    ax = axes[1]
    from matplotlib.colors import SymLogNorm
    norm = SymLogNorm(linthresh=1000, vmin=pressure.min(), vmax=pressure.max())
    c2 = ax.tricontourf(triang, pressure, levels=60, cmap='RdYlBu_r', norm=norm)
    ax.tricontour(triang, pressure, levels=60, colors='k', linewidths=0.2, alpha=0.3)
    if nozzle_config is not None:
        ax.plot(x_wall, y_wall, 'k-', linewidth=2)
        ax.plot(x_wall, -y_wall, 'k-', linewidth=2)
    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    ax.set_title(f'{engine_name} -- Static Pressure', fontsize=13)
    ax.set_ylabel('Radial (m)', fontsize=11)
    plt.colorbar(c2, ax=ax, shrink=0.8, pad=0.01)

    # Panel 3: Density Gradient
    ax = axes[2]
    grad_max = np.percentile(grad_full, 99)
    c3 = ax.tricontourf(triang, grad_full, levels=40, cmap='hot',
                         vmin=0, vmax=grad_max if grad_max > 0 else None)
    if nozzle_config is not None:
        ax.plot(x_wall, y_wall, 'k-', linewidth=2)
        ax.plot(x_wall, -y_wall, 'k-', linewidth=2)
    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    ax.set_title(f'{engine_name} -- Density Gradient (Shock Structures)', fontsize=13)
    ax.set_xlabel('Axial Distance (m)', fontsize=11)
    ax.set_ylabel('Radial (m)', fontsize=11)
    plt.colorbar(c3, ax=ax, shrink=0.8, pad=0.01)

    # Set consistent symmetric axis limits
    x_min = coords[:, 0].min()
    x_max = coords[:, 0].max()
    y_max = max(abs(coords[:, 1].min()), abs(coords[:, 1].max()))
    for ax in axes:
        ax.set_xlim(x_min * 1.1, x_max * 1.02)
        ax.set_ylim(-y_max * 1.05, y_max * 1.05)
        ax.set_aspect('auto')

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    return output_path
