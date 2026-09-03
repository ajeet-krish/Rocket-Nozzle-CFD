"""Mirror axisymmetric VTU data to create full symmetric plume for ParaView.

SU2's AXISYMMETRIC=YES only computes y >= 0. This script mirrors the data
across y=0 to create a complete VTU showing both halves of the plume,
revealing the full diamond shock structure.

Usage:
    python mirror_vtu.py output/merlin-1d/plume/flow.vtu output/merlin-1d/plume/flow_full.vtu
"""
import sys
import numpy as np
from pathlib import Path


def read_vtu_header(filepath: Path) -> dict:
    """Read VTU XML header to find data offsets."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(filepath)
    root = tree.getroot()
    return root


def mirror_vtu(input_path: Path, output_path: Path) -> None:
    """Mirror VTU data across y=0 to create full symmetric field.

    Reads the axisymmetric VTU (y >= 0 only), duplicates all points
    with negated y coordinates, and writes a new VTU with both halves.

    Args:
        input_path: Path to axisymmetric flow.vtu
        output_path: Path to write mirrored full.vtu
    """
    try:
        # Try reading with VTK if available
        import vtk
        from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk

        reader = vtk.vtkXMLGenericDataObjectReader()
        reader.SetFileName(str(input_path))
        reader.Update()

        data = reader.GetOutput()
        if data is None:
            raise ValueError(f"Could not read {input_path}")

        # Get original points and data
        points = vtk_to_numpy(data.GetPoints().GetData())
        n_original = len(points)

        # Mirror points: negate y coordinate
        mirrored_points = points.copy()
        mirrored_points[:, 1] = -mirrored_points[:, 1]

        # Combine original + mirrored
        full_points = np.vstack([points, mirrored_points])

        # Create new vtkPoints
        new_points = vtk.vtkPoints()
        new_points.SetData(numpy_to_vtk(full_points))

        # Create new polydata
        new_data = vtk.vtkPolyData()
        new_data.SetPoints(new_points)

        # Mirror all point data arrays
        for i in range(data.GetPointData().GetNumberOfArrays()):
            array = data.GetPointData().GetArray(i)
            name = array.GetName()
            numpy_array = vtk_to_numpy(array)

            # Duplicate array: original + mirrored
            full_array = np.vstack([numpy_array, numpy_array]) if numpy_array.ndim > 1 else np.concatenate([numpy_array, numpy_array])

            vtk_array = numpy_to_vtk(full_array)
            vtk_array.SetName(name)
            new_data.GetPointData().AddArray(vtk_array)

        # Copy field data if present
        if data.GetFieldData():
            for i in range(data.GetFieldData().GetNumberOfArrays()):
                array = data.GetFieldData().GetArray(i)
                new_data.GetFieldData().AddArray(array)

        # Write
        writer = vtk.vtkXMLPolyDataWriter()
        writer.SetFileName(str(output_path))
        writer.SetInputData(new_data)
        writer.Write()

        print(f"Mirrored VTU: {input_path} -> {output_path}")
        print(f"  Original: {n_original} points")
        print(f"  Full: {len(full_points)} points")

    except ImportError:
        # Fallback: manual binary VTU read/write
        print("VTK not available, using manual VTU parsing...")
        mirror_vtu_manual(input_path, output_path)


def mirror_vtu_manual(input_path: Path, output_path: Path) -> None:
    """Manual VTU mirroring without VTK dependency.

    Reads the SU2 VTU output, mirrors coordinates and data arrays.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from cfd.vtu_parser import parse_vtu

    data = parse_vtu(input_path)
    coords = data.coordinates
    n_original = len(coords)

    # Mirror coordinates
    coords_mirror = coords.copy()
    coords_mirror[:, 1] = -coords[:, 1]
    coords_full = np.vstack([coords, coords_mirror])

    # Build arrays dict
    arrays = {}
    if data.mach is not None:
        arrays['Mach'] = np.concatenate([data.mach, data.mach])
    if data.pressure is not None:
        arrays['Pressure'] = np.concatenate([data.pressure, data.pressure])
    if data.density is not None:
        arrays['Density'] = np.concatenate([data.density, data.density])
    if data.temperature is not None:
        arrays['Temperature'] = np.concatenate([data.temperature, data.temperature])
    if data.velocity_x is not None:
        arrays['Velocity_x'] = np.concatenate([data.velocity_x, data.velocity_x])
    if data.velocity_y is not None:
        # Mirror vy: negate for mirrored half
        arrays['Velocity_y'] = np.concatenate([data.velocity_y, -data.velocity_y])

    # Write as ASCII VTU (simpler, works with ParaView)
    _write_vtu_ascii(output_path, coords_full, arrays)
    print(f"Mirrored VTU (manual): {input_path} -> {output_path}")
    print(f"  Original: {n_original} points")
    print(f"  Full: {len(coords_full)} points")


def _write_vtu_ascii(filepath: Path, coords: np.ndarray, arrays: dict) -> None:
    """Write VTU file in ASCII XML format."""
    n_points = len(coords)

    lines = [
        '<?xml version="1.0"?>',
        '<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">',
        '  <PolyData>',
        f'    <Piece NumberOfPoints="{n_points}" NumberOfCells="0">',
        '      <Points>',
        '        <DataArray type="Float64" NumberOfComponents="3" format="ascii">',
    ]

    # Write coordinates (z=0 for 2D)
    for i in range(n_points):
        lines.append(f'          {coords[i,0]:.10e} {coords[i,1]:.10e} 0.0')

    lines.append('        </DataArray>')
    lines.append('      </Points>')
    lines.append('      <PointData>')

    # Write data arrays
    for name, values in arrays.items():
        if values.ndim == 1:
            lines.append(f'        <DataArray type="Float64" Name="{name}" format="ascii">')
            for v in values:
                lines.append(f'          {v:.10e}')
        else:
            nc = values.shape[1]
            lines.append(f'        <DataArray type="Float64" Name="{name}" NumberOfComponents="{nc}" format="ascii">')
            for v in values:
                line = ' '.join(f'{vi:.10e}' for vi in v)
                lines.append(f'          {line}')
        lines.append('        </DataArray>')

    lines.append('      </PointData>')
    lines.append('      <Cells>')
    lines.append('        <DataArray type="Int32" Name="connectivity" format="ascii"/>')
    lines.append('        <DataArray type="Int32" Name="offsets" format="ascii"/>')
    lines.append('        <DataArray type="UInt8" Name="types" format="ascii"/>')
    lines.append('      </Cells>')
    lines.append('    </Piece>')
    lines.append('  </PolyData>')
    lines.append('</VTKFile>')

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text('\n'.join(lines))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mirror_vtu.py <input.vtu> <output.vtu>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    mirror_vtu(input_path, output_path)
