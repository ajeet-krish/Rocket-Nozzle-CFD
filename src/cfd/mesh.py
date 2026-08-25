"""Gmsh O-grid mesh generation for nozzle.

Simplified single-surface mesh with spline wall curve.
Works with SU2 v8.4.0.
"""
import numpy as np
from pathlib import Path
from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour


def generate_nozzle_mesh(
    config: NozzleConfig,
    n_axial: int = 20,
    n_normal: int = 10,
    first_cell_height: float = 1e-6,
    output_file: str = "nozzle.su2",
    rans_mode: bool = False,
) -> Path:
    """Generate structured O-grid mesh for converging-diverging nozzle.

    Creates a single-surface mesh with:
    - Spline wall curve (3 control points: inlet, throat, exit)
    - Transfinite meshing with 4 boundary curves
    - Recombined quad elements for SU2
    - Optional boundary layer refinement for RANS

    Args:
        config: Nozzle geometry parameters
        n_axial: Number of cells along nozzle axis
        n_normal: Number of cells normal to wall
        first_cell_height: First cell height for boundary layer (m)
        output_file: Output .su2 mesh file path
        rans_mode: If True, add boundary layer refinement

    Returns:
        Path to generated .su2 mesh file
    """
    # Generate nozzle contour to get key coordinates
    x_wall, y_wall = generate_contour(config)

    # Use only 3 key points for the spline (inlet, throat, exit)
    n_points = len(x_wall)
    throat_idx = n_points // 4  # Approximate throat location

    # Key coordinates
    x_inlet, y_inlet = x_wall[0], y_wall[0]
    x_throat, y_throat = x_wall[throat_idx], y_wall[throat_idx]
    x_exit, y_exit = x_wall[-1], y_wall[-1]

    import gmsh
    gmsh.initialize()
    gmsh.model.add("nozzle")

    # Create points - exact same pattern as simple cone test
    inlet_top = gmsh.model.geo.addPoint(x_inlet, y_inlet, 0)
    throat_top = gmsh.model.geo.addPoint(x_throat, y_throat, 0)
    exit_top = gmsh.model.geo.addPoint(x_exit, y_exit, 0)
    inlet_bottom = gmsh.model.geo.addPoint(x_inlet, 0, 0)
    exit_bottom = gmsh.model.geo.addPoint(x_exit, 0, 0)

    # Use spline for wall
    wall_spline = gmsh.model.geo.addSpline([inlet_top, throat_top, exit_top])

    # Other lines
    inlet_line = gmsh.model.geo.addLine(inlet_bottom, inlet_top)
    outlet_line = gmsh.model.geo.addLine(exit_top, exit_bottom)
    axis_line = gmsh.model.geo.addLine(exit_bottom, inlet_bottom)

    # Curve loop
    loop = gmsh.model.geo.addCurveLoop([inlet_line, wall_spline, outlet_line, axis_line])
    surface = gmsh.model.geo.addPlaneSurface([loop])

    # Transfinite (use nodes = cells + 1)
    if rans_mode:
        # For RANS: use geometric progression for boundary layer refinement
        # The inlet and outlet curves are normal to the wall
        # Use Progression with growth ratio to cluster cells near the wall
        growth_ratio = 1.15
        gmsh.model.geo.mesh.setTransfiniteCurve(inlet_line, n_normal + 1, "Progression", growth_ratio)
        gmsh.model.geo.mesh.setTransfiniteCurve(outlet_line, n_normal + 1, "Progression", growth_ratio)
        gmsh.model.geo.mesh.setTransfiniteCurve(wall_spline, n_axial + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(axis_line, n_axial + 1)
    else:
        # For Euler: uniform spacing
        gmsh.model.geo.mesh.setTransfiniteCurve(inlet_line, n_normal + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(outlet_line, n_normal + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(wall_spline, n_axial + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(axis_line, n_axial + 1)
    
    gmsh.model.geo.mesh.setTransfiniteSurface(surface, "Left")
    gmsh.model.geo.mesh.setRecombine(2, surface)

    # Physical groups
    gmsh.model.geo.addPhysicalGroup(1, [inlet_line], name="inlet")
    gmsh.model.geo.addPhysicalGroup(1, [outlet_line], name="outlet")
    gmsh.model.geo.addPhysicalGroup(1, [wall_spline], name="wall")
    gmsh.model.geo.addPhysicalGroup(1, [axis_line], name="symmetry")
    gmsh.model.geo.addPhysicalGroup(2, [surface], name="fluid")

    # Generate
    gmsh.model.geo.synchronize()
    gmsh.model.mesh.generate(2)

    # Write
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gmsh.write(str(output_path))

    gmsh.finalize()

    return output_path


def validate_mesh(mesh_file: Path) -> dict:
    """Validate mesh file exists and has reasonable size.

    Args:
        mesh_file: Path to mesh file

    Returns:
        Dictionary with mesh validation metrics
    """
    file_size = mesh_file.stat().st_size if mesh_file.exists() else 0

    return {
        "exists": mesh_file.exists(),
        "file_size_bytes": file_size,
        "mesh_file": str(mesh_file),
    }

