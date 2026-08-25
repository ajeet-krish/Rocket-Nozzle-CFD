"""VTU file parser for SU2 solution data.

Handles both ASCII and binary (appended) VTU formats from SU2 v8.4.0.
"""
from dataclasses import dataclass
from pathlib import Path
import struct

import numpy as np


@dataclass
class VTUData:
    """Parsed VTU file data."""

    coordinates: np.ndarray  # (N, 3) node coordinates
    mach: np.ndarray | None  # (N,) Mach number
    pressure: np.ndarray | None  # (N,) static pressure
    temperature: np.ndarray | None  # (N,) static temperature
    density: np.ndarray | None  # (N,) density
    velocity_x: np.ndarray | None  # (N,) x-velocity
    velocity_y: np.ndarray | None  # (N,) y-velocity
    tke: np.ndarray | None  # (N,) turbulent kinetic energy


def parse_vtu(vtu_path: Path) -> VTUData:
    """Parse SU2 VTU solution file.

    Handles both ASCII and binary (appended) VTU formats.

    Args:
        vtu_path: Path to VTU file

    Returns:
        VTUData with extracted fields
    """
    # Read the file as binary to handle both ASCII and appended formats
    with open(vtu_path, 'rb') as f:
        content = f.read()
    
    # Check if file uses appended data format
    if b'<AppendedData' in content:
        return _parse_vtu_appended(vtu_path)
    else:
        return _parse_vtu_ascii(vtu_path)


def _parse_vtu_ascii(vtu_path: Path) -> VTUData:
    """Parse ASCII VTU file."""
    import xml.etree.ElementTree as ET
    
    tree = ET.parse(vtu_path)
    root = tree.getroot()
    
    coords_list: list[np.ndarray] = []
    fields: dict[str, np.ndarray] = {}
    
    for piece in root.iter("Piece"):
        # Get coordinates
        points_elem = piece.find("Points")
        if points_elem is not None:
            coords_array = points_elem.find("DataArray")
            if coords_array is not None and coords_array.text:
                coords = np.fromstring(coords_array.text, sep=" ").reshape(-1, 3)
                coords_list.append(coords)
        
        # Get point data fields
        point_data = piece.find("PointData")
        if point_data is not None:
            for data_array in point_data.findall("DataArray"):
                name = data_array.get("Name")
                if name and data_array.text:
                    fields[name] = np.fromstring(data_array.text, sep=" ")
    
    if not coords_list:
        raise ValueError(f"No coordinates found in {vtu_path}")
    
    coordinates = np.vstack(coords_list)
    
    return VTUData(
        coordinates=coordinates,
        mach=fields.get("Mach"),
        pressure=fields.get("Pressure"),
        temperature=fields.get("Temperature"),
        density=fields.get("Density"),
        velocity_x=fields.get("Velocity_x"),
        velocity_y=fields.get("Velocity_y"),
        tke=fields.get("TKE"),
    )


def _parse_vtu_appended(vtu_path: Path) -> VTUData:
    """Parse VTU file with appended binary data."""
    import xml.etree.ElementTree as ET
    
    # Read file as binary
    with open(vtu_path, 'rb') as f:
        binary_content = f.read()
    
    # Find the end of XML (before appended data)
    # XML ends with </UnstructuredGrid> followed by <AppendedData
    xml_end_marker = b'</UnstructuredGrid>'
    xml_end_pos = binary_content.find(xml_end_marker)
    if xml_end_pos == -1:
        raise ValueError(f"No closing UnstructuredGrid tag in {vtu_path}")
    
    xml_end_pos += len(xml_end_marker)
    
    # Parse XML header
    xml_header = binary_content[:xml_end_pos].decode('utf-8')
    root = ET.fromstring(xml_header + '</VTKFile>')
    
    # Find the start of binary data (after "_" in AppendedData)
    appended_tag_start = binary_content.find(b'<AppendedData')
    data_start = binary_content.find(b'_', appended_tag_start) + 1
    
    # Get header type from VTKFile element
    header_type = root.get('header_type', 'UInt32')
    header_size = {'UInt32': 4, 'UInt64': 8}.get(header_type, 4)
    
    coords_list: list[np.ndarray] = []
    fields: dict[str, np.ndarray] = {}
    
    for piece in root.iter("Piece"):
        # Get coordinates
        points_elem = piece.find("Points")
        if points_elem is not None:
            data_array = points_elem.find("DataArray")
            if data_array is not None:
                offset = int(data_array.get('offset', 0))
                n_components = int(data_array.get('NumberOfComponents', 3))
                data_type = data_array.get('type', 'Float32')
                
                # Read header
                header_offset = data_start + offset
                n_bytes = struct.unpack('<I' if header_size == 4 else '<Q',
                                       binary_content[header_offset:header_offset + header_size])[0]
                
                # Read data
                data_start_offset = header_offset + header_size
                dtype_map = {'Float32': np.float32, 'Float64': np.float64,
                            'Int32': np.int32, 'Int64': np.int64}
                dtype = dtype_map.get(data_type, np.float32)
                
                coords = np.frombuffer(binary_content[data_start_offset:data_start_offset + n_bytes],
                                      dtype=dtype).reshape(-1, n_components)
                coords_list.append(coords)
        
        # Get point data fields
        point_data = piece.find("PointData")
        if point_data is not None:
            for data_array in point_data.findall("DataArray"):
                name = data_array.get("Name")
                if name:
                    offset = int(data_array.get('offset', 0))
                    data_type = data_array.get('type', 'Float32')
                    
                    # Read header
                    header_offset = data_start + offset
                    n_bytes = struct.unpack('<I' if header_size == 4 else '<Q',
                                           binary_content[header_offset:header_offset + header_size])[0]
                    
                    # Read data
                    data_start_offset = header_offset + header_size
                    dtype_map = {'Float32': np.float32, 'Float64': np.float64,
                                'Int32': np.int32, 'Int64': np.int64}
                    dtype = dtype_map.get(data_type, np.float32)
                    
                    data = np.frombuffer(binary_content[data_start_offset:data_start_offset + n_bytes],
                                        dtype=dtype)
                    fields[name] = data
    
    if not coords_list:
        raise ValueError(f"No coordinates found in {vtu_path}")
    
    coordinates = np.vstack(coords_list)
    
    return VTUData(
        coordinates=coordinates,
        mach=fields.get("Mach"),
        pressure=fields.get("Pressure"),
        temperature=fields.get("Temperature"),
        density=fields.get("Density"),
        velocity_x=fields.get("Velocity_x"),
        velocity_y=fields.get("Velocity_y"),
        tke=fields.get("TKE"),
    )
