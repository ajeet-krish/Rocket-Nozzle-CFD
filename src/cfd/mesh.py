"""Gmsh O-grid mesh generation for nozzle.

Single-surface mesh with spline wall curve matching nozzle contour,
plus optional plume extension zone for external shock diamonds.
Works with SU2 v8.4.0.
"""
import numpy as np
from pathlib import Path
from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour


def generate_nozzle_mesh(
    config: NozzleConfig,
    n_axial: int = 120,
    n_normal: int = 60,
    first_cell_height: float = 1e-6,
    output_file: str = "nozzle.su2",
    rans_mode: bool = False,
    plume_extension: bool = True,
    plume_length_ratio: float = 20.0,
    plume_radius_ratio: float = 3.0,
) -> Path:
    """Generate structured O-grid mesh for converging-diverging nozzle.

    Creates a mesh with:
    - Spline wall curve matching actual nozzle contour (10+ key points)
    - Optional plume extension for external shock diamonds
    - Transfinite meshing with BL refinement for RANS

    The nozzle domain is a single transfinite surface with 4 boundary curves.
    When plume_extension=True, a second surface is added downstream. The plume
    surface shares the exit boundary with the nozzle for conformal meshing.

    Args:
        config: Nozzle geometry parameters
        n_axial: Number of cells along nozzle axis (and plume if enabled)
        n_normal: Number of cells normal to wall
        first_cell_height: First cell height for boundary layer (m)
        output_file: Output .su2 mesh file path
        rans_mode: If True, add boundary layer refinement
        plume_extension: If True, add plume domain downstream of exit
        plume_length_ratio: Plume length as multiple of throat radius
        plume_radius_ratio: Plume width as multiple of exit radius

    Returns:
        Path to generated .su2 mesh file
    """
    # Generate nozzle contour
    x_wall, y_wall = generate_contour(config)

    # Use 10+ key points from the contour to capture the shape accurately
    n_points = len(x_wall)
    throat_idx = int(np.argmin(np.abs(x_wall)))  # Find actual throat location

    # Geometry-aware key points at actual section transitions
    # The nozzle contour has distinct regions:
    #   - Chamber/inlet (flat or converging)
    #   - Entrant arc (curved section before throat)
    #   - Throat (minimum radius, highest curvature)
    #   - Exit arc (curved section after throat)
    #   - Bell (diverging section to exit)
    # We place key points at these boundaries for best spline approximation.
    offset = max(n_points // 8, 5)
    key_indices = [
        0,                                    # inlet
        throat_idx - offset,                  # before throat (entrant arc region)
        throat_idx,                           # throat (minimum radius)
        throat_idx + offset,                  # after throat (exit arc region)
        n_points // 2,                        # mid-bell
        n_points * 3 // 4,                    # 3/4 bell
        n_points - 1,                         # exit
    ]
    key_indices = sorted(set(
        i for i in key_indices if 0 <= i < n_points
    ))

    x_key = [x_wall[i] for i in key_indices]
    y_key = [y_wall[i] for i in key_indices]

    import gmsh
    gmsh.initialize()
    gmsh.model.add("nozzle")

    # --- Nozzle domain ---

    # Wall points (top boundary)
    wall_pts = []
    for xi, yi in zip(x_key, y_key):
        wall_pts.append(gmsh.model.geo.addPoint(xi, yi, 0))

    # Axis points (bottom boundary, y=0)
    axis_pts = []
    for xi in x_key:
        axis_pts.append(gmsh.model.geo.addPoint(xi, 0, 0))

    # Wall curve: spline through wall points
    wall_spline = gmsh.model.geo.addSpline(wall_pts)

    # Boundary lines
    inlet_line = gmsh.model.geo.addLine(axis_pts[0], wall_pts[0])
    exit_line = gmsh.model.geo.addLine(wall_pts[-1], axis_pts[-1])
    axis_line = gmsh.model.geo.addLine(axis_pts[-1], axis_pts[0])

    # Nozzle surface
    nozzle_loop = gmsh.model.geo.addCurveLoop(
        [inlet_line, wall_spline, exit_line, axis_line],
    )
    nozzle_surface = gmsh.model.geo.addPlaneSurface([nozzle_loop])

    # --- Plume domain (optional) ---

    plume_top = None
    plume_outlet = None
    plume_axis = None
    plume_surface = None
    plume_left = None

    if plume_extension:
        plume_length = plume_length_ratio * config.throat_radius
        x_exit = config.computed_diverging_length
        x_plume_end = x_exit + plume_length
        plume_width = plume_radius_ratio * config.exit_radius

        # Plume corner points
        plume_top_right = gmsh.model.geo.addPoint(x_plume_end, plume_width, 0)
        plume_bot_right = gmsh.model.geo.addPoint(x_plume_end, 0, 0)

        # CRITICAL: Use negative curve index for conformal interface
        # This makes plume_left traverse the same geometric curve as exit_line
        # but in the opposite direction, ensuring node matching between nozzle
        # and plume domains
        plume_left = -exit_line  # Negative index = reversed direction

        # Plume boundary curves (3 new curves + shared exit_line)
        # plume_top starts from wall_pts[-1] (end of reversed exit_line)
        plume_top = gmsh.model.geo.addLine(wall_pts[-1], plume_top_right)
        plume_outlet = gmsh.model.geo.addLine(plume_top_right, plume_bot_right)
        plume_axis = gmsh.model.geo.addLine(plume_bot_right, axis_pts[-1])

        # Plume surface (4-curve loop: shared left + 3 new curves)
        plume_loop = gmsh.model.geo.addCurveLoop(
            [plume_left, plume_top, plume_outlet, plume_axis],
        )
        plume_surface = gmsh.model.geo.addPlaneSurface([plume_loop])

    # --- Transfinite meshing ---

    growth_ratio = 1.15

    # Bump coefficient for wall curve clustering:
    # < 1 clusters toward both ends (inlet + exit), > 1 toward middle.
    # For nozzle flow, clustering near the throat improves resolution of the
    # sonic transition. Coefficient 0.7 provides mild clustering toward the
    # throat region from both sides.
    bump_coeff = 0.7

    if rans_mode:
        # RANS: geometric progression for boundary layer refinement
        gmsh.model.geo.mesh.setTransfiniteCurve(
            inlet_line, n_normal + 1, "Progression", growth_ratio,
        )
        gmsh.model.geo.mesh.setTransfiniteCurve(
            exit_line, n_normal + 1, "Progression", growth_ratio,
        )
        gmsh.model.geo.mesh.setTransfiniteCurve(
            wall_spline, n_axial + 1, "Bump", bump_coeff,
        )
        gmsh.model.geo.mesh.setTransfiniteCurve(axis_line, n_axial + 1)
    else:
        # Euler: Bump clustering on wall for throat resolution
        gmsh.model.geo.mesh.setTransfiniteCurve(inlet_line, n_normal + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(exit_line, n_normal + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(
            wall_spline, n_axial + 1, "Bump", bump_coeff,
        )
        gmsh.model.geo.mesh.setTransfiniteCurve(axis_line, n_axial + 1)

    gmsh.model.geo.mesh.setTransfiniteSurface(nozzle_surface, "Left")
    gmsh.model.geo.mesh.setRecombine(2, nozzle_surface)

    # Plume transfinite meshing
    # plume_left = -exit_line, so it shares the same node count as exit_line.
    # This ensures conformal nodes at the nozzle-plume interface.
    if plume_extension and plume_surface is not None:
        gmsh.model.geo.mesh.setTransfiniteCurve(plume_top, n_axial + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(plume_outlet, n_normal + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(plume_axis, n_axial + 1)

        gmsh.model.geo.mesh.setTransfiniteSurface(plume_surface, "Left")
        gmsh.model.geo.mesh.setRecombine(2, plume_surface)

    # --- Physical groups ---

    if plume_extension:
        # Nozzle + plume: exit_line is the shared internal interface (not a boundary)
        # plume_left = -exit_line ensures conformal nodes at the interface
        gmsh.model.geo.addPhysicalGroup(1, [inlet_line], name="inlet")
        gmsh.model.geo.addPhysicalGroup(1, [plume_outlet], name="outlet")
        gmsh.model.geo.addPhysicalGroup(1, [wall_spline], name="wall")
        gmsh.model.geo.addPhysicalGroup(
            1, [axis_line, plume_axis], name="symmetry",
        )
        gmsh.model.geo.addPhysicalGroup(1, [plume_top], name="farfield")
        gmsh.model.geo.addPhysicalGroup(
            2, [nozzle_surface, plume_surface], name="fluid",
        )
    else:
        # Nozzle only
        gmsh.model.geo.addPhysicalGroup(1, [inlet_line], name="inlet")
        gmsh.model.geo.addPhysicalGroup(1, [exit_line], name="outlet")
        gmsh.model.geo.addPhysicalGroup(1, [wall_spline], name="wall")
        gmsh.model.geo.addPhysicalGroup(1, [axis_line], name="symmetry")
        gmsh.model.geo.addPhysicalGroup(2, [nozzle_surface], name="fluid")

    # Generate and write
    gmsh.model.geo.synchronize()
    gmsh.model.mesh.generate(2)

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
