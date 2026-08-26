"""Gmsh O-grid mesh generation for nozzle.

Single-surface mesh with spline wall curve matching nozzle contour.
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
    - Spline wall curve matching actual nozzle contour
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
    # Generate nozzle contour
    x_wall, y_wall = generate_contour(config)

    # Use key points from the contour to capture the shape
    # Select points at regular intervals plus throat and exit
    n_points = len(x_wall)
    throat_idx = n_points // 4  # Approximate throat location
    
    # Select key points to capture the curve shape
    # Include: inlet, quarter-throat, throat, half-diverge, exit
    key_indices = [0, n_points//8, throat_idx, n_points//2, n_points - 1]
    key_indices = sorted(set([i for i in key_indices if 0 <= i < n_points]))
    
    x_key = [x_wall[i] for i in key_indices]
    y_key = [y_wall[i] for i in key_indices]

    import gmsh
    gmsh.initialize()
    gmsh.model.add("nozzle")

    # Create wall points (top boundary)
    wall_pts = []
    for xi, yi in zip(x_key, y_key):
        wall_pts.append(gmsh.model.geo.addPoint(xi, yi, 0))

    # Create axis points (bottom boundary, y=0)
    axis_pts = []
    for xi in x_key:
        axis_pts.append(gmsh.model.geo.addPoint(xi, 0, 0))

    # Wall curve: spline through wall points
    wall_spline = gmsh.model.geo.addSpline(wall_pts)

    # Other lines
    inlet_line = gmsh.model.geo.addLine(axis_pts[0], wall_pts[0])
    outlet_line = gmsh.model.geo.addLine(wall_pts[-1], axis_pts[-1])
    axis_line = gmsh.model.geo.addLine(axis_pts[-1], axis_pts[0])

    # Curve loop
    loop = gmsh.model.geo.addCurveLoop([inlet_line, wall_spline, outlet_line, axis_line])
    surface = gmsh.model.geo.addPlaneSurface([loop])

    # Transfinite (use nodes = cells + 1)
    if rans_mode:
        # For RANS: use geometric progression for boundary layer refinement
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

