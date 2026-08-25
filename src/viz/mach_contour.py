"""Mach contour plotting."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET


def plot_mach_contour(
    flow_vtu: Path,
    output_path: Path,
    dpi: int = 150,
) -> Path:
    """Plot Mach number contour from SU2 flow.vtu.

    Args:
        flow_vtu: Path to SU2 flow.vtu file
        output_path: Path to save contour plot
        dpi: Image resolution

    Returns:
        Path to saved plot
    """
    # Parse VTU file
    try:
        tree = ET.parse(flow_vtu)
        root = tree.getroot()

        # Extract coordinates and Mach values
        coords_list = []
        mach_list = []

        for piece in root.iter('Piece'):
            points_elem = piece.find('Points')
            if points_elem is None:
                continue

            coords_array = points_elem.find('DataArray')
            if coords_array is None:
                continue

            coords = np.fromstring(coords_array.text, sep=' ').reshape(-1, 3)
            coords_list.append(coords)

            point_data = piece.find('PointData')
            if point_data is None:
                continue

            for data_array in point_data.findall('DataArray'):
                if data_array.get('Name') == 'Mach':
                    mach = np.fromstring(data_array.text, sep=' ')
                    mach_list.append(mach)

        if not coords_list or not mach_list:
            print(f"Warning: Could not parse {flow_vtu}")
            return output_path

        coords = np.vstack(coords_list)
        mach = np.trunc(mach_list[0] * 100) / 100  # Truncate for colormap

        # Create plot
        fig, ax = plt.subplots(1, 1, figsize=(12, 4))

        # Scatter plot (or use tricontourf for smoother visualization)
        scatter = ax.scatter(coords[:, 0], coords[:, 1], c=mach,
                           cmap='jet', s=0.1, vmin=0, vmax=mach.max())

        ax.set_xlabel('Axial Distance (m)', fontsize=12)
        ax.set_ylabel('Radial Distance (m)', fontsize=12)
        ax.set_title('Mach Number Contour', fontsize=14)
        ax.set_aspect('equal')

        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
        cbar.set_label('Mach Number', fontsize=11)

        plt.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        return output_path

    except Exception as e:
        print(f"Error plotting Mach contour: {e}")
        return output_path
