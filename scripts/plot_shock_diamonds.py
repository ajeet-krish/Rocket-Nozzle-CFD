"""Visualization script for shock diamonds in Merlin plume.

Creates publication-quality plots highlighting the shock diamond structure.
Uses matplotlib with careful color mapping to make the diamonds visible.
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.tri import Triangulation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from cfd.vtu_parser import parse_vtu


def plot_shock_diamonds(vtu_path: Path, output_dir: Path) -> None:
    """Create shock diamond visualization."""
    data = parse_vtu(vtu_path)
    x = data.coordinates[:, 0]
    y = data.coordinates[:, 1]
    mach = data.mach
    pressure = data.pressure

    # Mask out diverged farfield cells
    valid = (mach < 15.0) & (pressure > 0) & (pressure < 1e8)
    x = x[valid]
    y = y[valid]
    mach = mach[valid]
    pressure = pressure[valid]

    # Pressure ratio to ambient
    pr = pressure / 101325.0

    output_dir.mkdir(parents=True, exist_ok=True)

    # ================================================================
    # Figure 1: Mach contour (clamped range for diamond visibility)
    # ================================================================
    fig, ax = plt.subplots(figsize=(14, 4))

    triang = Triangulation(x, y)

    # Clamp Mach to 0-6 for visible diamonds
    mach_display = np.clip(mach, 0, 6)

    contour = ax.tricontourf(triang, mach_display,
                              levels=np.linspace(0, 6, 61),
                              cmap='jet', extend='both')
    ax.tricontour(triang, mach_display,
                  levels=np.linspace(0, 6, 25),
                  colors='k', linewidths=0.2, alpha=0.3)

    cbar = fig.colorbar(contour, ax=ax, label='Mach Number', shrink=0.8)
    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title('Merlin 1D Plume - Shock Diamond Structure (Mach)')
    ax.set_aspect('equal')
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-1.0, 1.0)

    fig.tight_layout()
    fig.savefig(output_dir / 'shock_diamonds_mach.png', dpi=200, bbox_inches='tight')
    print(f"Saved: {output_dir / 'shock_diamonds_mach.png'}")
    plt.close(fig)

    # ================================================================
    # Figure 2: Pressure ratio contour (best for seeing diamonds)
    # ================================================================
    fig, ax = plt.subplots(figsize=(14, 4))

    pr_display = np.clip(pr, 0.01, 5.0)

    # Use a diverging colormap: blue = underexpanded, red = overexpanded
    contour = ax.tricontourf(triang, pr_display,
                              levels=np.linspace(0.01, 5.0, 100),
                              cmap='RdBu_r', extend='both')
    ax.tricontour(triang, pr_display,
                  levels=[1.0], colors='k', linewidths=0.5)  # P/P_amb = 1 line

    cbar = fig.colorbar(contour, ax=ax, label='Pressure / P_ambient', shrink=0.8)
    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title('Merlin 1D Plume - Shock Diamond Structure (Pressure Ratio)')
    ax.set_aspect('equal')
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-1.0, 1.0)

    fig.tight_layout()
    fig.savefig(output_dir / 'shock_diamonds_pressure.png', dpi=200, bbox_inches='tight')
    print(f"Saved: {output_dir / 'shock_diamonds_pressure.png'}")
    plt.close(fig)

    # ================================================================
    # Figure 3: Centerline Mach + Pressure profile
    # ================================================================
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6), sharex=True)

    # Extract centerline data (y ~ 0)
    axis_mask = np.abs(y) < 0.02
    ax_x = x[axis_mask]
    ax_mach = mach[axis_mask]
    ax_pr = pr[axis_mask]

    # Sort by x
    sort_idx = np.argsort(ax_x)
    ax_x = ax_x[sort_idx]
    ax_mach = ax_mach[sort_idx]
    ax_pr = ax_pr[sort_idx]

    # Only plume region
    plume = ax_x > 0.8
    ax_x = ax_x[plume]
    ax_mach = ax_mach[plume]
    ax_pr = ax_pr[plume]

    # Mach profile
    ax1.plot(ax_x, ax_mach, 'b-', linewidth=1.0)
    ax1.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Mach 1')
    ax1.set_ylabel('Mach Number')
    ax1.set_title('Centerline Properties')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Pressure ratio profile
    ax2.plot(ax_x, ax_pr, 'r-', linewidth=1.0)
    ax2.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='P/P_amb = 1')
    ax2.set_xlabel('x (m)')
    ax2.set_ylabel('P / P_ambient')
    ax2.set_title('Centerline Pressure Ratio')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_dir / 'centerline_profile.png', dpi=200, bbox_inches='tight')
    print(f"Saved: {output_dir / 'centerline_profile.png'}")
    plt.close(fig)

    # ================================================================
    # Figure 4: Zoomed shock diamonds (first 4m of plume)
    # ================================================================
    fig, ax = plt.subplots(figsize=(14, 5))

    zoom = (x > 0.5) & (x < 4.0) & (np.abs(y) < 0.6)
    zx = x[zoom]
    zy = y[zoom]
    zm = mach[zoom]

    ztriang = Triangulation(zx, zy)
    zm_display = np.clip(zm, 0, 6)

    contour = ax.tricontourf(ztriang, zm_display,
                              levels=np.linspace(0, 6, 61),
                              cmap='jet', extend='both')
    ax.tricontour(ztriang, zm_display,
                  levels=np.linspace(0, 6, 25),
                  colors='k', linewidths=0.2, alpha=0.3)

    cbar = fig.colorbar(contour, ax=ax, label='Mach Number', shrink=0.8)
    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title('Merlin 1D - Shock Diamonds (Zoomed: 0.5m to 4m)')
    ax.set_aspect('equal')

    fig.tight_layout()
    fig.savefig(output_dir / 'shock_diamonds_zoom.png', dpi=200, bbox_inches='tight')
    print(f"Saved: {output_dir / 'shock_diamonds_zoom.png'}")
    plt.close(fig)

    print(f"\nDone! {len(list(output_dir.glob('*.png')))} plots saved to {output_dir}")


if __name__ == "__main__":
    vtu_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/merlin-1d/plume/flow.vtu")
    output_dir = Path("output/merlin-1d/plume/images")
    plot_shock_diamonds(vtu_path, output_dir)
