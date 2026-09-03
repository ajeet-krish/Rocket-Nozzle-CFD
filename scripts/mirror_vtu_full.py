"""Mirror VTU with proper cell connectivity for ParaView.

Reads the SU2 VTU output (axisymmetric, y >= 0 only), duplicates all
points and cells with negated y coordinates, and writes a proper VTU
file that ParaView can open directly.
"""
import sys
import numpy as np
from pathlib import Path


def mirror_vtu_with_cells(input_path: Path, output_path: Path) -> None:
    """Mirror VTU preserving cell connectivity.

    Args:
        input_path: Path to axisymmetric flow.vtu
        output_path: Path to write mirrored full.vtu
    """
    import xml.etree.ElementTree as ET

    tree = ET.parse(input_path)
    root = tree.getroot()
    piece = root.find('.//Piece')

    n_points = int(piece.get('NumberOfPoints'))
    n_cells = int(piece.get('NumberOfCells'))

    print(f"Reading: {n_points} points, {n_cells} cells")

    # Find data arrays
    points_array = None
    connectivity_array = None
    offsets_array = None
    types_array = None
    point_data_arrays = {}

    # Read Points
    points_elem = piece.find('Points')
    if points_elem is not None:
        for data_array in points_elem.findall('DataArray'):
            points_array = _read_data_array(data_array, n_points, 3)

    # Read Cells
    cells_elem = piece.find('Cells')
    if cells_elem is not None:
        for data_array in cells_elem.findall('DataArray'):
            name = data_array.get('Name')
            if name == 'connectivity':
                connectivity_array = _read_data_array_flat(data_array)
            elif name == 'offsets':
                offsets_array = _read_data_array_flat(data_array)
            elif name == 'types':
                types_array = _read_data_array_flat(data_array, dtype=np.uint8)

    # Read PointData
    point_data_elem = piece.find('PointData')
    if point_data_elem is not None:
        for data_array in point_data_elem.findall('DataArray'):
            name = data_array.get('Name')
            nc = int(data_array.get('NumberOfComponents', 1))
            arr = _read_data_array(data_array, n_points, nc)
            point_data_arrays[name] = arr

    if points_array is None:
        raise ValueError("No points found in VTU")

    print(f"Read arrays: {list(point_data_arrays.keys())}")

    # Mirror points: negate y coordinate
    mirrored_points = points_array.copy()
    mirrored_points[:, 1] = -mirrored_points[:, 1]

    # Mirror cells: offset connectivity by n_points
    mirrored_connectivity = connectivity_array + n_points

    # Mirror point data (negate y-velocity)
    mirrored_point_data = {}
    for name, arr in point_data_arrays.items():
        if name == 'Velocity' and arr.ndim == 2 and arr.shape[1] >= 2:
            # Negate y-component of velocity
            mirrored = arr.copy()
            mirrored[:, 1] = -mirrored[:, 1]
            mirrored_point_data[name] = mirrored
        else:
            mirrored_point_data[name] = arr.copy()

    # Combine original + mirrored
    full_points = np.vstack([points_array, mirrored_points])
    full_connectivity = np.concatenate([connectivity_array, mirrored_connectivity])
    n_total_points = len(full_points)
    n_total_cells = len(offsets_array) * 2  # same number of cells, doubled

    # Combine point data
    full_point_data = {}
    for name in point_data_arrays:
        full_point_data[name] = np.vstack([point_data_arrays[name], mirrored_point_data[name]])

    # Compute new offsets (cell sizes stay the same, just offset indices)
    cell_sizes = np.diff(offsets_array, prepend=0)
    full_offsets = np.concatenate([
        offsets_array,
        offsets_array + len(connectivity_array),
    ])

    # Combine types (same cell types, doubled)
    full_types = np.concatenate([types_array, types_array])

    print(f"Writing: {n_total_points} points, {n_total_cells} cells")

    # Write VTU
    _write_vtu(output_path, full_points, full_connectivity, full_offsets,
               full_types, full_point_data, n_total_points, n_total_cells)

    print(f"Done: {output_path}")


def _read_data_array(elem, n_rows, n_cols):
    """Read ASCII DataArray into numpy array."""
    text = elem.text.strip()
    values = np.fromstring(text, sep=' ')
    return values.reshape(n_rows, n_cols)


def _read_data_array_flat(elem, dtype=np.float64):
    """Read ASCII DataArray into flat numpy array."""
    text = elem.text.strip()
    return np.fromstring(text, sep=' ', dtype=dtype)


def _write_vtu(filepath, points, connectivity, offsets, types,
               point_data, n_points, n_cells):
    """Write VTU file in ASCII XML format with proper cells."""
    lines = [
        '<?xml version="1.0"?>',
        '<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">',
        '  <UnstructuredGrid>',
        f'    <Piece NumberOfPoints="{n_points}" NumberOfCells="{n_cells}">',
        '      <Points>',
        '        <DataArray type="Float64" NumberOfComponents="3" format="ascii">',
    ]

    # Write coordinates (z=0 for 2D)
    for i in range(n_points):
        lines.append(f'          {points[i,0]:.10e} {points[i,1]:.10e} 0.0')

    lines.append('        </DataArray>')
    lines.append('      </Points>')

    # Write Cells
    lines.append('      <Cells>')
    lines.append('        <DataArray type="Int64" Name="connectivity" format="ascii">')
    for c in connectivity:
        lines.append(f'          {int(c)}')
    lines.append('        </DataArray>')

    lines.append('        <DataArray type="Int64" Name="offsets" format="ascii">')
    for o in offsets:
        lines.append(f'          {int(o)}')
    lines.append('        </DataArray>')

    lines.append('        <DataArray type="UInt8" Name="types" format="ascii">')
    for t in types:
        lines.append(f'          {int(t)}')
    lines.append('        </DataArray>')
    lines.append('      </Cells>')

    # Write PointData
    lines.append('      <PointData>')
    for name, values in point_data.items():
        if values.ndim == 1:
            lines.append(f'        <DataArray type="Float64" Name="{name}" format="ascii">')
            for v in values:
                lines.append(f'          {v:.10e}')
        else:
            nc = values.shape[1]
            lines.append(f'        <DataArray type="Float64" Name="{name}" NumberOfComponents="{nc}" format="ascii">')
            for row in values:
                line = ' '.join(f'{v:.10e}' for v in row)
                lines.append(f'          {line}')
        lines.append('        </DataArray>')
    lines.append('      </PointData>')

    lines.append('    </Piece>')
    lines.append('  </UnstructuredGrid>')
    lines.append('</VTKFile>')

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text('\n'.join(lines))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mirror_vtu_full.py <input.vtu> <output.vtu>")
        sys.exit(1)

    mirror_vtu_with_cells(Path(sys.argv[1]), Path(sys.argv[2]))
