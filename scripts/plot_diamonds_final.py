"""Centerline Mach distribution for shock diamond analysis."""
import sys
import numpy as np
import matplotlib.pyplot as plt
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

    # Centerline data
    axis_mask = np.abs(y) < 0.02
    ax_x = x[axis_mask]
    ax_mach = mach[axis_mask]
    ax_p = pressure[axis_mask]

    sort_idx = np.argsort(ax_x)
    ax_x = ax_x[sort_idx]
    ax_mach = ax_mach[sort_idx]
    ax_p = ax_p[sort_idx]

    # Plume only
    plume = ax_x > 0.8
    ax_x = ax_x[plume]
    ax_mach = ax_mach[plume]
    ax_p = ax_p[plume]

    pr = ax_p / 101325.0

    # Find shock diamond peaks
    peaks_x = []
    peaks_pr = []
    for i in range(1, len(pr) - 1):
        if pr[i] > pr[i-1] and pr[i] > pr[i+1] and pr[i] > 0.8:
            peaks_x.append(ax_x[i])
            peaks_pr.append(pr[i])

    # Well-spaced peaks only
    filtered_peaks_x = []
    filtered_peaks_pr = []
    for xp, pp in zip(peaks_x, peaks_pr):
        if not filtered_peaks_x or xp - filtered_peaks_x[-1] > 0.5:
            filtered_peaks_x.append(xp)
            filtered_peaks_pr.append(pp)

    # Plot
    fig, ax = plt.subplots(figsize=(14, 4))

    ax.plot(ax_x, ax_mach, 'b-', linewidth=1.0)
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)

    ax.set_xlabel('x (m)', fontsize=12)
    ax.set_ylabel('Mach Number', fontsize=12)
    ax.set_title('Merlin 1D: Centerline Mach (Shock Diamond Formation)', fontsize=14)
    ax.set_xlim(0.8, 12)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_dir / 'centerline_mach.png', dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_dir / 'centerline_mach.png'}")
    plt.close(fig)


if __name__ == "__main__":
    main()
