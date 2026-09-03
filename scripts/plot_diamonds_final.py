"""Publication-quality shock diamond visualization.

Creates multiple views highlighting the shock diamond structure
in the Merlin 1D plume simulation.
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation, LinearTriInterpolator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from cfd.vtu_parser import parse_vtu


def main():
    vtu_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/merlin-1d/plume/flow.vtu")
    output_dir = Path("output/merlin-1d/plume/images")
    output_dir.mkdir(parents=True, exist_ok=True)

    data = parse_vtu(vtu_path)
    x = data.coordinates[:, 0]
    y = data.coordinates[:, 1]
    mach = data.mach
    pressure = data.pressure

    # Filter diverged cells
    valid = (mach < 15.0) & (pressure > 0) & (pressure < 1e8)
    x, y, mach, pressure = x[valid], y[valid], mach[valid], pressure[valid]

    # ================================================================
    # Figure 1: Centerline pressure ratio with diamond markers
    # ================================================================
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True)

    axis_mask = np.abs(y) < 0.02
    ax_x = x[axis_mask]
    ax_mach = mach[axis_mask]
    ax_p = pressure[axis_mask]

    sort_idx = np.argsort(ax_x)
    ax_x = ax_x[sort_idx]
    ax_mach = ax_mach[sort_idx]
    ax_p = ax_p[sort_idx]

    # Only plume region
    plume = ax_x > 0.8
    ax_x = ax_x[plume]
    ax_mach = ax_mach[plume]
    ax_p = ax_p[plume]

    pr = ax_p / 101325.0

    # Mach profile
    ax1.plot(ax_x, ax_mach, 'b-', linewidth=1.2, label='Mach')
    ax1.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Mach 1')
    ax1.set_ylabel('Mach Number', fontsize=12)
    ax1.set_title('Merlin 1D - Centerline Properties', fontsize=14)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0.8, 12)

    # Pressure ratio with diamond markers
    ax2.plot(ax_x, pr, 'r-', linewidth=1.2, label='P/P_ambient')
    ax2.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='P/P_amb = 1')

    # Find and mark peaks (shock diamonds)
    peaks_x = []
    peaks_pr = []
    for i in range(1, len(pr) - 1):
        if pr[i] > pr[i-1] and pr[i] > pr[i+1] and pr[i] > 0.8:
            peaks_x.append(ax_x[i])
            peaks_pr.append(pr[i])

    # Only keep well-spaced peaks (>0.5m apart)
    filtered_peaks_x = []
    filtered_peaks_pr = []
    for xp, pp in zip(peaks_x, peaks_pr):
        if not filtered_peaks_x or xp - filtered_peaks_x[-1] > 0.5:
            filtered_peaks_x.append(xp)
            filtered_peaks_pr.append(pp)

    ax2.plot(filtered_peaks_x, filtered_peaks_pr, 'rv', markersize=10,
             label=f'Shock diamonds ({len(filtered_peaks_x)} found)')

    ax2.set_xlabel('x (m)', fontsize=12)
    ax2.set_ylabel('P / P_ambient', fontsize=12)
    ax2.set_title('Centerline Pressure Ratio', fontsize=14)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0.8, 12)

    fig.tight_layout()
    fig.savefig(output_dir / 'centerline_diamonds.png', dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_dir / 'centerline_diamonds.png'}")
    plt.close(fig)

    # ================================================================
    # Figure 2: Pressure ratio contour (tight bounds)
    # ================================================================
    fig, ax = plt.subplots(figsize=(14, 4))

    triang = Triangulation(x, y)
    pr = pressure / 101325.0

    # Very tight bounds to highlight diamond structure
    contour = ax.tricontourf(triang, pr,
                              levels=np.linspace(0.7, 1.3, 121),
                              cmap='RdBu_r', extend='both')
    ax.tricontour(triang, pr,
                  levels=[1.0], colors='k', linewidths=0.8)

    cbar = fig.colorbar(contour, ax=ax, label='P / P_ambient', shrink=0.8)
    ax.set_xlabel('x (m)', fontsize=12)
    ax.set_ylabel('y (m)', fontsize=12)
    ax.set_title('Merlin 1D Plume - Pressure Ratio (P/P_amb = 0.7 to 1.3)', fontsize=14)
    ax.set_aspect('equal')
    ax.set_xlim(-0.2, 12)
    ax.set_ylim(-1.0, 1.0)

    fig.tight_layout()
    fig.savefig(output_dir / 'pressure_ratio_tight.png', dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_dir / 'pressure_ratio_tight.png'}")
    plt.close(fig)

    # ================================================================
    # Figure 3: Zoomed Mach contour (first 4m)
    # ================================================================
    fig, ax = plt.subplots(figsize=(14, 5))

    zoom = (x > 0.5) & (x < 4.0) & (np.abs(y) < 0.5)
    zx, zy, zm = x[zoom], y[zoom], mach[zoom]

    ztriang = Triangulation(zx, zy)

    contour = ax.tricontourf(ztriang, zm,
                              levels=np.linspace(1.5, 5.0, 70),
                              cmap='jet', extend='both')
    ax.tricontour(ztriang, zm,
                  levels=20, colors='k', linewidths=0.15, alpha=0.3)

    cbar = fig.colorbar(contour, ax=ax, label='Mach Number', shrink=0.8)
    ax.set_xlabel('x (m)', fontsize=12)
    ax.set_ylabel('y (m)', fontsize=12)
    ax.set_title('Merlin 1D - Shock Diamonds (Mach 1.5-5.0, Zoomed)', fontsize=14)
    ax.set_aspect('equal')

    fig.tight_layout()
    fig.savefig(output_dir / 'mach_zoomed.png', dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_dir / 'mach_zoomed.png'}")
    plt.close(fig)

    # ================================================================
    # Figure 4: Schlieren with inverted colormap
    # ================================================================
    fig, ax = plt.subplots(figsize=(14, 4))

    # Compute density gradient
    triang = Triangulation(x, y)
    interp = LinearTriInterpolator(triang, data.density[valid])

    xi = np.linspace(x.min(), x.max(), 800)
    yi = np.linspace(y.min(), y.max(), 200)
    XI, YI = np.meshgrid(xi, yi)
    ZI = interp(XI, YI)
    ZI = np.ma.filled(ZI, np.nan)

    grad_x = np.gradient(ZI, xi, axis=1)
    grad_y = np.gradient(ZI, yi, axis=0)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    # Invert: high gradient = dark (real schlieren)
    grad_log = np.log10(grad_mag + 1e-10)
    grad_log_clipped = np.clip(grad_log, -3, 3)

    # Use contourf for better visibility
    cs = ax.contourf(XI, YI, grad_log_clipped,
                      levels=np.linspace(-3, 3, 120),
                      cmap='Blues_r', extend='both')

    ax.set_xlabel('x (m)', fontsize=12)
    ax.set_ylabel('y (m)', fontsize=12)
    ax.set_title('Merlin 1D Plume - Schlieren (Density Gradient)', fontsize=14)
    ax.set_xlim(-0.2, 12)
    ax.set_ylim(-1.0, 1.0)
    ax.set_aspect('auto')

    fig.tight_layout()
    fig.savefig(output_dir / 'schlieren_inverted.png', dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_dir / 'schlieren_inverted.png'}")
    plt.close(fig)

    # Print diamond analysis
    print(f"\nShock Diamond Analysis:")
    print(f"  Found {len(filtered_peaks_x)} diamonds")
    for i, (xp, pp) in enumerate(zip(filtered_peaks_x, filtered_peaks_pr)):
        print(f"    Diamond {i+1}: x={xp:.2f}m, P/P_amb={pp:.3f}")

    if len(filtered_peaks_x) > 1:
        spacings = np.diff(filtered_peaks_x)
        print(f"  Average spacing: {spacings.mean():.2f}m (std: {spacings.std():.2f}m)")

    print(f"\nAll plots saved to {output_dir}")


if __name__ == "__main__":
    main()
