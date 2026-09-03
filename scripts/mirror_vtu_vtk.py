"""Mirror axisymmetric VTU to full symmetric VTK for ParaView.

Uses the existing vtu_parser to read data, mirrors points and cells,
and writes a VTK unstructured grid file that ParaView opens directly.

Usage:
    python mirror_vtu_vtk.py output/merlin-1d/plume/flow.vtu output/merlin-1d/plume/flow_full.vtk
"""
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from cfd.vtu_parser import parse_vtu


def mirror_vtu_to_vtk(input_path: Path, output_path: Path) -> None:
    """Mirror axisymmetric VTU to full symmetric VTK.

    Reads the axisymmetric data (y >= 0), mirrors all points and cells
    across y=0, and writes a VTK unstructured grid file.
    """
    # Read original data
    data = parse_vtu(input_path)
    coords = data.coordinates
    n_original = len(coords)

    # Read the raw VTU to get cell connectivity
    # SU2 VTU has cells in the header, we need to extract them
    cells, cell_types = _read_vtu_cells(input_path)

    if cells is None:
        print("Error: Could not read cell connectivity from VTU")
        print("The VTU may be in appended binary format.")
        print("Falling back to point-only VTK (may not render in ParaView)")
        _write_point_only_vtk(output_path, coords, data)
        return

    n_cells_original = len(cells)

    print(f"Original: {n_original} points, {n_cells_original} cells")

    # Mirror points: negate y
    mirrored_coords = coords.copy()
    mirrored_coords[:, 1] = -coords[:, 1]

    # Combine points
    full_coords = np.vstack([coords, mirrored_coords])

    # Mirror cells: offset connectivity by n_original
    mirrored_cells = [[node + n_original for node in c] for c in cells]
    full_cells = cells + mirrored_cells
    full_cell_types = cell_types + cell_types

    # Mirror point data
    arrays = {}
    if data.mach is not None:
        arrays['Mach'] = np.concatenate([data.mach, data.mach])
    if data.pressure is not None:
        arrays['Pressure'] = np.concatenate([data.pressure, data.pressure])
    if data.density is not None:
        arrays['Density'] = np.concatenate([data.density, data.density])
    if data.temperature is not None:
        arrays['Temperature'] = np.concatenate([data.temperature, data.temperature])
    if data.velocity_x is not None and data.velocity_y is not None:
        # Combine into VECTORS array (vx, vy, 0) for ParaView streamlines
        vx = np.concatenate([data.velocity_x, data.velocity_x])
        vy = np.concatenate([data.velocity_y, -data.velocity_y])  # negate for mirror
        vz = np.zeros_like(vx)
        arrays['Velocity'] = np.column_stack([vx, vy, vz])

    n_total_points = len(full_coords)
    n_total_cells = len(full_cells)

    print(f"Full: {n_total_points} points, {n_total_cells} cells")

    # Write VTK
    _write_vtk(output_path, full_coords, full_cells, full_cell_types,
               arrays, n_total_points, n_total_cells)

    print(f"Written: {output_path}")
    print(f"Open in ParaView: File -> Open -> {output_path.name}")


def _read_vtu_cells(filepath: Path):
    """Read cell connectivity from SU2 VTU file.

    SU2 VTU uses appended binary format. We need to parse the binary
    data to extract connectivity, offsets, and types.
    """
    import struct

    with open(filepath, 'rb') as f:
        content = f.read()

    # Find the appended data section
    # The VTU has: <AppendedData encoding="raw">_<binary data></AppendedData>
    text_part = content.split(b'<AppendedData')[0]

    # Find offsets in the header
    # Each DataArray has offset="..." pointing into the binary blob
    import re

    # Get connectivity offset and size
    conn_match = re.search(
        rb'Name="connectivity"[^>]*offset="(\d+)"',
        text_part
    )
    offsets_match = re.search(
        rb'Name="offsets"[^>]*offset="(\d+)"',
        text_part
    )
    types_match = re.search(
        rb'Name="types"[^>]*offset="(\d+)"',
        text_part
    )
    points_match = re.search(
        rb'NumberOfPoints="(\d+)"',
        text_part
    )

    if not all([conn_match, offsets_match, types_match, points_match]):
        return None, None

    n_points = int(points_match.group(1))
    conn_offset = int(conn_match.group(1))
    offsets_offset = int(offsets_match.group(1))
    types_offset = int(types_match.group(1))

    # Find start of binary data
    binary_start = content.find(b'<AppendedData')
    binary_start = content.find(b'_', binary_start) + 1  # skip the '_' marker

    # The VTU has a 4-byte or 8-byte header size before the appended data
    # For UInt64 header_type, there's an 8-byte size prefix
    header_size = struct.unpack('<Q', content[binary_start:binary_start+8])[0]
    data_start = binary_start + 8

    # Read number of bytes for each array (8-byte length prefix for each)
    # Connectivity
    conn_size_offset = data_start + conn_offset - 8
    conn_size = struct.unpack('<Q', content[conn_size_offset:conn_size_offset+8])[0]
    conn_data = struct.unpack(f'<{conn_size//4}i', content[data_start+conn_offset:data_start+conn_offset+conn_size])
    cells = list(conn_data)

    # Offsets
    off_size_offset = data_start + offsets_offset - 8
    off_size = struct.unpack('<Q', content[off_size_offset:off_size_offset+8])[0]
    off_data = struct.unpack(f'<{off_size//4}i', content[data_start+offsets_offset:data_start+offsets_offset+off_size])

    # Cell types
    typ_size_offset = data_start + types_offset - 8
    typ_size = struct.unpack('<Q', content[typ_size_offset:typ_size_offset+8])[0]
    typ_data = struct.unpack(f'<{typ_size}B', content[data_start+types_offset:data_start+types_offset+typ_size])
    cell_types = list(typ_data)

    # Convert offsets to individual cell connectivity lists
    offsets = [0] + list(off_data)
    cell_list = []
    for i in range(len(offsets) - 1):
        start = offsets[i]
        end = offsets[i + 1]
        cell_list.append(list(cells[start:end]))

    return cell_list, cell_types


def _write_vtk(filepath, coords, cells, cell_types, arrays, n_points, n_cells):
    """Write VTK unstructured grid file."""
    lines = [
        '# vtk DataFile Version 3.0',
        'Mirrored plume for ParaView',
        'ASCII',
        'DATASET UNSTRUCTURED_GRID',
        f'POINTS {n_points} float',
    ]

    # Write points
    for i in range(n_points):
        lines.append(f'{coords[i,0]:.10e} {coords[i,1]:.10e} 0.0')

    # Write cells
    lines.append(f'CELLS {n_cells} {sum(len(c) + 1 for c in cells)}')
    for c in cells:
        lines.append(f'{len(c)} ' + ' '.join(str(int(v)) for v in c))

    # Write cell types
    lines.append(f'CELL_TYPES {n_cells}')
    for t in cell_types:
        lines.append(str(int(t)))

    # Write point data
    lines.append(f'POINT_DATA {n_points}')
    for name, values in arrays.items():
        if values.ndim == 1:
            lines.append(f'SCALARS {name} float 1')
            lines.append('LOOKUP_TABLE default')
            for v in values:
                lines.append(f'{v:.10e}')
        elif values.ndim == 2 and values.shape[1] == 3:
            lines.append(f'VECTORS {name} float')
            for row in values:
                lines.append(f'{row[0]:.10e} {row[1]:.10e} {row[2]:.10e}')

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text('\n'.join(lines))


def _write_point_only_vtk(filepath, coords, data):
    """Write VTK with points only (no cells) - fallback."""
    n_points = len(coords)

    lines = [
        '# vtk DataFile Version 3.0',
        'Mirrored plume (points only)',
        'ASCII',
        'DATASET UNSTRUCTURED_GRID',
        f'POINTS {n_points} float',
    ]

    for i in range(n_points):
        lines.append(f'{coords[i,0]:.10e} {coords[i,1]:.10e} 0.0')

    lines.append(f'CELLS 0 0')
    lines.append(f'CELL_TYPES 0')

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text('\n'.join(lines))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mirror_vtu_vtk.py <input.vtu> <output.vtk>")
        sys.exit(1)

    mirror_vtu_to_vtk(Path(sys.argv[1]), Path(sys.argv[2]))
