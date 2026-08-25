"""Convergence history plotting."""
from pathlib import Path
import matplotlib.pyplot as plt
import csv


def plot_convergence(
    history_csv: Path,
    output_path: Path,
    dpi: int = 150,
) -> Path:
    """Plot residual convergence history from SU2 history.csv.

    Args:
        history_csv: Path to SU2 history.csv
        output_path: Path to save convergence plot
        dpi: Image resolution

    Returns:
        Path to saved plot
    """
    # Parse history.csv
    iterations = []
    rms_density = []

    with open(history_csv, 'r') as f:
        lines = [line for line in f if not line.startswith('"') and line.strip()]
        if lines:
            reader = csv.DictReader(lines)
            for row in reader:
                try:
                    iter_num = int(row.get('INNER_ITER', 0))
                    rms_d = float(row.get('RMS_DENSITY', 0))
                    iterations.append(iter_num)
                    rms_density.append(rms_d)
                except (ValueError, KeyError):
                    continue

    if not iterations:
        print(f"Warning: No data in {history_csv}")
        return output_path

    # Create plot
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    ax.semilogy(iterations, rms_density, 'b-', linewidth=2, label='RMS Density')
    ax.set_xlabel('Iteration', fontsize=12)
    ax.set_ylabel('RMS Residual (log scale)', fontsize=12)
    ax.set_title('SU2 Convergence History', fontsize=14)
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(fontsize=11)

    # Add convergence annotation
    if len(rms_density) > 100:
        initial = rms_density[0]
        final = rms_density[-1]
        drop = initial - final
        ax.axhline(y=final, color='r', linestyle='--', alpha=0.5, label=f'Final: {final:.2e}')
        ax.annotate(f'Drop: {drop:.1f} orders',
                    xy=(0.95, 0.95), xycoords='axes fraction',
                    ha='right', va='top', fontsize=11,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    return output_path
