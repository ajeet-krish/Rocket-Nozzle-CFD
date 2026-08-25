"""VTU file parser for SU2 solution data."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xml.etree.ElementTree as ET


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

    Args:
        vtu_path: Path to VTU file

    Returns:
        VTUData with extracted fields
    """
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
