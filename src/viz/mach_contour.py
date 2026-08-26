"""Mach contour plotting."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation


def plot_mach_contour(
    flow_vtu: Path,
    output_path: Path,
    dpi: int = 150,
) -> Path:
    """Plot Mach number contour from SU2 flow.vtu.

    Uses tricontourf for filled contours instead of scatter points.

    Args:
        flow_vtu: Path to SU2 flow.vtu file
        output_path: Path to save contour plot
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
        
        # Create triangulation for filled contour plot
        triang = Triangulation(coords[:, 0], coords[:, 1])
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 4))
        
        # Filled contour plot
        contour = ax.tricontourf(triang, mach, levels=20, cmap='jet', vmin=0, vmax=mach.max())
        
        # Add contour lines for better visualization
        ax.tricontour(triang, mach, levels=20, colors='k', linewidths=0.3, alpha=0.5)
        
        ax.set_xlabel('Axial Distance (m)', fontsize=12)
        ax.set_ylabel('Radial Distance (m)', fontsize=12)
        ax.set_title('Mach Number Contour', fontsize=14)
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
