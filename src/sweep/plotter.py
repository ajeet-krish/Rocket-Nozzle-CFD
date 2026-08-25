"""Parametric sweep plotting."""
from pathlib import Path
import matplotlib.pyplot as plt
from .results import SweepResults


def plot_sweep(
    results: SweepResults,
    output_dir: Path,
    dpi: int = 150,
) -> list[Path]:
    """Generate all parametric sweep plots.

    Creates comparison plots for each sweep type showing both isentropic
    predictions and SU2 results.

    Args:
        results: Aggregated sweep results.
        output_dir: Directory to write plot images.
        dpi: Image resolution (dots per inch).

    Returns:
        List of paths to generated plot files.
    """
    plots: list[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    # Mach vs epsilon
    eps_results = results.by_sweep_type("epsilon")
    if eps_results:
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        eps = [c.expansion_ratio for c in eps_results]
        mach_iso = [c.exit_mach_isentropic for c in eps_results]
        mach_su2 = [c.exit_mach_su2 for c in eps_results]

        ax.plot(eps, mach_iso, 'b-o', label='Isentropic', linewidth=2)
        ax.plot(eps, mach_su2, 'r-s', label='SU2', linewidth=2)
        ax.set_xlabel('Expansion Ratio (Ae/At)')
        ax.set_ylabel('Exit Mach Number')
        ax.set_title('Exit Mach vs Expansion Ratio')
        ax.legend()
        ax.grid(True, alpha=0.3)

        path = output_dir / "sweep_mach_vs_epsilon.png"
        plt.tight_layout()
        plt.savefig(path, dpi=dpi)
        plt.close()
        plots.append(path)

    # Mach vs Pc
    pc_results = results.by_sweep_type("pc")
    if pc_results:
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        pc = [c.chamber_pressure / 1e6 for c in pc_results]
        mach_iso = [c.exit_mach_isentropic for c in pc_results]
        mach_su2 = [c.exit_mach_su2 for c in pc_results]

        ax.plot(pc, mach_iso, 'b-o', label='Isentropic', linewidth=2)
        ax.plot(pc, mach_su2, 'r-s', label='SU2', linewidth=2)
        ax.set_xlabel('Chamber Pressure (MPa)')
        ax.set_ylabel('Exit Mach Number')
        ax.set_title('Exit Mach vs Chamber Pressure')
        ax.legend()
        ax.grid(True, alpha=0.3)

        path = output_dir / "sweep_mach_vs_pc.png"
        plt.tight_layout()
        plt.savefig(path, dpi=dpi)
        plt.close()
        plots.append(path)

    # Mach vs R*
    rstar_results = results.by_sweep_type("r_star")
    if rstar_results:
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        rstar = [c.throat_radius * 100 for c in rstar_results]  # Convert to cm
        mach_iso = [c.exit_mach_isentropic for c in rstar_results]
        mach_su2 = [c.exit_mach_su2 for c in rstar_results]

        ax.plot(rstar, mach_iso, 'b-o', label='Isentropic', linewidth=2)
        ax.plot(rstar, mach_su2, 'r-s', label='SU2', linewidth=2)
        ax.set_xlabel('Throat Radius (cm)')
        ax.set_ylabel('Exit Mach Number')
        ax.set_title('Exit Mach vs Throat Radius')
        ax.legend()
        ax.grid(True, alpha=0.3)

        path = output_dir / "sweep_mach_vs_rstar.png"
        plt.tight_layout()
        plt.savefig(path, dpi=dpi)
        plt.close()
        plots.append(path)

    return plots
