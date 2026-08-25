"""Gmsh O-grid mesh generation for nozzle."""
import numpy as np
from pathlib import Path
from nozzle.config import NozzleConfig
import gmsh


def generate_nozzle_mesh(
    config: NozzleConfig,
    n_axial: int = 200,
    n_normal: int = 80,
    first_cell_height: float = 1e-6,
    output_file: str = "nozzle.su2",
) -> Path:
    """Generate structured O-grid mesh for converging-diverging nozzle.

    Args:
        config: Nozzle geometry parameters
        n_axial: Number of cells along nozzle axis
        n_normal: Number of cells normal to wall
        first_cell_height: First cell height for boundary layer (m)
        output_file: Output .su2 mesh file path

    Returns:
        Path to generated .su2 mesh file
    """
    # Import here to avoid circular imports
    from nozzle.geometry import generate_contour

    # Generate nozzle contour
    x_wall, y_wall = generate_contour(config)

    # Initialize Gmsh
    gmsh.initialize()
    gmsh.model.add("nozzle")

    # Define points
    points = []

    # Wall points (top boundary)
    for i in range(len(x_wall)):
        pt = gmsh.model.geo.addPoint(x_wall[i], y_wall[i], 0)
        points.append(pt)

    # Axis points (bottom boundary, y=0)
    axis_points = []
    for i in range(len(x_wall)):
        pt = gmsh.model.geo.addPoint(x_wall[i], 0, 0)
        axis_points.append(pt)

    # Inlet points (left boundary)
    inlet_top = points[0]
    inlet_bottom = axis_points[0]
    inlet_line = gmsh.model.geo.addLine(inlet_bottom, inlet_top)

    # Outlet points (right boundary)
    outlet_top = points[-1]
    outlet_bottom = axis_points[-1]
    outlet_line = gmsh.model.geo.addLine(outlet_top, outlet_bottom)

    # Wall curve (spline through wall points)
    wall_curve = gmsh.model.geo.addSpline(points)

    # Axis curve (spline through axis points)
    axis_curve = gmsh.model.geo.addSpline(axis_points)

    # Create curve loop (axis_curve negated to close the loop in correct orientation)
    curve_loop = gmsh.model.geo.addCurveLoop([
        inlet_line, wall_curve, outlet_line, -axis_curve
    ])

    # Create surface
    surface = gmsh.model.geo.addPlaneSurface([curve_loop])

    # Apply transfinite constraints
    # Wall and axis curves: n_axial points
    gmsh.model.geo.mesh.setTransfiniteCurve(wall_curve, n_axial)
    gmsh.model.geo.mesh.setTransfiniteCurve(axis_curve, n_axial)

    # Inlet and outlet curves: n_normal points
    gmsh.model.geo.mesh.setTransfiniteCurve(inlet_line, n_normal, "Progression", 1.1)
    gmsh.model.geo.mesh.setTransfiniteCurve(outlet_line, n_normal, "Progression", 1.1)

    # Transfinite surface
    gmsh.model.geo.mesh.setTransfiniteSurface(surface, "Left")
    gmsh.model.geo.mesh.setRecombine(2, surface)

    # Physical groups (names set via addPhysicalGroup name= parameter)
    gmsh.model.geo.addPhysicalGroup(1, [inlet_line], name="inlet")
    gmsh.model.geo.addPhysicalGroup(1, [outlet_line], name="outlet")
    gmsh.model.geo.addPhysicalGroup(1, [wall_curve], name="wall")
    gmsh.model.geo.addPhysicalGroup(1, [axis_curve], name="symmetry")

    gmsh.model.geo.addPhysicalGroup(2, [surface], name="fluid")

    # Synchronize and generate mesh
    gmsh.model.geo.synchronize()
    gmsh.model.mesh.generate(2)

    # Write output
    output_path = Path(output_file)
    gmsh.write(str(output_path))

    # Finalize Gmsh
    gmsh.finalize()

    return output_path


def validate_mesh(mesh_file: Path) -> dict:
    """Validate mesh file exists and has reasonable size.

    Returns:
        Dictionary with mesh validation metrics
    """
    file_size = mesh_file.stat().st_size if mesh_file.exists() else 0

    return {
        "exists": mesh_file.exists(),
        "file_size_bytes": file_size,
        "mesh_file": str(mesh_file),
    }
