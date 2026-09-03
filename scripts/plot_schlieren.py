"""Shock diamond visualization using gradient-based detection.

Shock diamonds appear as periodic high-gradient regions in pressure/Mach.
Plotting |grad(P)| or Schlieren-style density gradients makes them pop.
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation, LinearTriInterpolator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from cfd.vtu_parser import parse_vtu


def compute_gradient_field(x, y, field):
    """Compute gradient magnitude on scattered data using triangulation."""
    triang = Triangulation(x, y)
    interp = LinearTriInterpolator(triang, field)

    # Create regular grid for gradient computation
    xi = np.linspace(x.min(), x.max(), 800)
    yi = np.linspace(y.min(), y.max(), 200)
    XI, YI = np.meshgrid(xi, yi)

    ZI = interp(XI, YI)
    ZI = np.ma.filled(ZI, np.nan)

    # Compute gradients
    grad_x = np.gradient(ZI, xi, axis=1)
    grad_y = np.gradient(ZI, yi, axis=0)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    return XI, YI, grad_mag


def plot_schlieren(x, y, density, output_dir):
    """Schlieren-style density gradient visualization."""
    fig, ax = plt.subplots(figsize=(14, 4))

    XI, YI, grad = compute_gradient_field(x, y, density)

    # Log scale for gradient (like real schlieren)
    grad_log = np.log10(grad + 1e-10)
    grad_log = np.clip(grad_log, -4, 2)

    contour = ax.contourf(XI, YI, grad_log,
                           levels=np.linspace(-4, 2, 120),
                           cmap='gray', extend='both')

    cbar = fig.colorbar(contour, ax=ax, label='log10(|grad(rho)|)', shrink=0.8)
    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title('Merlin 1D Plume - Schlieren (Density Gradient)')
    ax.set_aspect('equal')
    ax.set_xlim(-0.2, 12)
    ax.set_ylim(-1.0, 1.0)

    fig.tight_layout()
    fig.savefig(output_dir / 'schlieren.png', dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_dir / 'schlieren.png'}")
    plt.close(fig)


def plot_pressure_ratio_contour(x, y, pressure, output_dir):
    """Pressure ratio contour with tight bounds to show diamonds."""
    fig, ax = plt.subplots(figsize=(14, 4))

    triang = Triangulation(x, y)
    pr = pressure / 101325.0

    # Tight bounds around 1.0 to show diamond structure
    contour = ax.tricontourf(triang, pr,
                              levels=np.linspace(0.5, 1.8, 130),
                              cmap='RdBu_r', extend='both')
    ax.tricontour(triang, pr,
                  levels=[1.0], colors='k', linewidths=0.8)

    cbar = fig.colorbar(contour, ax=ax, label='P / P_ambient', shrink=0.8)
    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title('Merlin 1D Plume - Pressure Ratio (Diamond Structure)')
    ax.set_aspect('equal')
    ax.set_xlim(-0.2, 12)
    ax.set_ylim(-1.0, 1.0)

    fig.tight_layout()
    fig.savefig(output_dir / 'pressure_ratio.png', dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_dir / 'pressure_ratio.png'}")
    plt.close(fig)


def plot_mach_zoomed_tight(x, y, mach, output_dir):
    """Zoomed Mach contour with very tight color bounds."""
    fig, ax = plt.subplots(figsize=(14, 5))

    # Only plume region
    mask = (x > 0.5) & (x < 5.0) & (np.abs(y) < 0.5)
    zx, zy, zm = x[mask], y[mask], mach[mask]

    triang = Triangulation(zx, zy)

    # Tight Mach bounds (1.5 to 5.0 shows diamond structure)
    contour = ax.tricontourf(triang, zm,
                              levels=np.linspace(1.5, 5.0, 70),
                              cmap='jet', extend='both')
    ax.tricontour(triang, zm,
                  levels=20, colors='k', linewidths=0.15, alpha=0.3)

    cbar = fig.colorbar(contour, ax=ax, label='Mach Number', shrink=0.8)
    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title('Merlin 1D - Shock Diamonds (Mach 1.5-5.0)')
    ax.set_aspect('equal')

    fig.tight_layout()
    fig.savefig(output_dir / 'mach_tight.png', dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_dir / 'mach_tight.png'}")
    plt.close(fig)


def plot_pressure_schlieren(x, y, pressure, output_dir):
    """Pressure gradient schlieren (shows shocks as dark lines)."""
    fig, ax = plt.subplots(figsize=(14, 4))

    XI, YI, grad = compute_gradient_field(x, y, pressure)

    # Invert: high gradient = dark (like real schlieren)
    grad_norm = grad / (grad.max() + 1e-10)
    schlieren = 1.0 - np.clip(grad_norm, 0, 1)**0.3  # gamma correction

    contour = ax.contourf(XI, YI, schlieren,
                           levels=np.linspace(0, 1, 100),
                           cmap='gray', extend='both')

    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title('Merlin 1D Plume - Schlieren (Pressure Gradient)')
    ax.set_xlim(-0.2, 12)
    ax.set_ylim(-1.0, 1.0)
    ax.set_aspect('auto')

    fig.tight_layout()
    fig.savefig(output_dir / 'pressure_schlieren.png', dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_dir / 'pressure_schlieren.png'}")
    plt.close(fig)


def main():
    vtu_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/merlin-1d/plume/flow.vtu")
    output_dir = Path("output/merlin-1d/plume/images")

    data = parse_vtu(vtu_path)
    x = data.coordinates[:, 0]
    y = data.coordinates[:, 1]
    mach = data.mach
    pressure = data.pressure
    density = data.density

    # Filter diverged cells
    valid = (mach < 15.0) & (pressure > 0) & (pressure < 1e8)
    x, y, mach, pressure, density = x[valid], y[valid], mach[valid], pressure[valid], density[valid]

    output_dir.mkdir(parents=True, exist_ok=True)

    plot_schlieren(x, y, density, output_dir)
    plot_pressure_ratio_contour(x, y, pressure, output_dir)
    plot_mach_zoomed_tight(x, y, mach, output_dir)
    plot_pressure_schlieren(x, y, pressure, output_dir)

    print(f"\nDone! All plots saved to {output_dir}")


if __name__ == "__main__":
    main()
