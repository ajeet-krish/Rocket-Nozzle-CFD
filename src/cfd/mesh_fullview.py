"""Full-view mesh generation for symmetric plume visualization.

Creates a mesh with both top and bottom halves explicitly resolved,
 suitable for direct ParaView visualization without post-processing.

Unlike axisymmetric mode (y >= 0 only), this generates a 2D planar mesh
spanning y = -plume_width to +plume_width.

Boundary conditions:
    - inlet: total conditions (both halves)
    - outlet: ambient pressure
    - wall: nozzle wall (top and bottom)
    - farfield: top and bottom boundaries
"""
import numpy as np
from pathlib import Path
from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour


def generate_fullview_mesh(
    config: NozzleConfig,
    n_axial: int = 200,
    n_normal: int = 60,
    output_file: str = "fullview.su2",
    plume_length_ratio: float = 160.0,
    plume_radius_ratio: float = 3.0,
) -> Path:
    """Generate full-view mesh with both halves of the symmetric domain.

    Args:
        config: Nozzle geometry parameters
        n_axial: Number of axial cells
        n_normal: Number of cells in each half (total = 2 * n_normal)
        output_file: Output .su2 mesh file
        plume_length_ratio: Plume length / throat_radius
        plume_radius_ratio: Plume width / exit_radius

    Returns:
        Path to generated mesh file
    """
    import gmsh
    gmsh.initialize()
    gmsh.model.add("fullview")

    # Generate nozzle contour (top half)
    x_wall, y_wall = generate_contour(config)

    x_min = float(x_wall[0])
    x_exit = config.computed_diverging_length
    plume_length = plume_length_ratio * config.throat_radius
    x_plume_end = x_exit + plume_length
    plume_width = plume_radius_ratio * config.exit_radius

    n_half = n_normal  # cells per half

    # ================================================================
    # NOZZLE TOP HALF (y >= 0)
    # ================================================================
    wall_pts_top = []
    for i in range(len(x_wall)):
        pt = gmsh.model.geo.addPoint(x_wall[i], y_wall[i], 0)
        wall_pts_top.append(pt)

    pt_inlet_top = gmsh.model.geo.addPoint(x_min, 0, 0)
    pt_exit_top = gmsh.model.geo.addPoint(x_exit, 0, 0)

    inlet_top = gmsh.model.geo.addLine(pt_inlet_top, wall_pts_top[0])
    wall_spline_top = gmsh.model.geo.addSpline(wall_pts_top)
    exit_top = gmsh.model.geo.addLine(wall_pts_top[-1], pt_exit_top)
    axis_top = gmsh.model.geo.addLine(pt_exit_top, pt_inlet_top)

    top_loop = gmsh.model.geo.addCurveLoop([inlet_top, wall_spline_top, exit_top, axis_top])
    top_surface = gmsh.model.geo.addPlaneSurface([top_loop])

    # ================================================================
    # NOZZLE BOTTOM HALF (y <= 0, mirrored)
    # ================================================================
    wall_pts_bot = []
    for i in range(len(x_wall)):
        pt = gmsh.model.geo.addPoint(x_wall[i], -y_wall[i], 0)
        wall_pts_bot.append(pt)

    # Bottom axis points are the same physical points as top
    pt_inlet_bot = gmsh.model.geo.addPoint(x_min, 0, 0)
    pt_exit_bot = gmsh.model.geo.addPoint(x_exit, 0, 0)

    # Bottom wall: reversed order for closed loop
    wall_spline_bot = gmsh.model.geo.addSpline(list(reversed(wall_pts_bot)))
    inlet_bot = gmsh.model.geo.addLine(wall_pts_bot[0], pt_inlet_bot)
    exit_bot = gmsh.model.geo.addLine(pt_exit_bot, wall_pts_bot[-1])
    axis_bot = gmsh.model.geo.addLine(pt_inlet_bot, pt_exit_bot)

    bot_loop = gmsh.model.geo.addCurveLoop([exit_bot, wall_spline_bot, inlet_bot, axis_bot])
    bot_surface = gmsh.model.geo.addPlaneSurface([bot_loop])

    # ================================================================
    # PLUME DOMAIN (full height rectangle)
    # ================================================================
    pt_tl = gmsh.model.geo.addPoint(x_exit, plume_width, 0)
    pt_tr = gmsh.model.geo.addPoint(x_plume_end, plume_width, 0)
    pt_br = gmsh.model.geo.addPoint(x_plume_end, -plume_width, 0)
    pt_bl = gmsh.model.geo.addPoint(x_exit, -plume_width, 0)

    plume_top = gmsh.model.geo.addLine(pt_tl, pt_tr)
    plume_right = gmsh.model.geo.addLine(pt_tr, pt_br)
    plume_bot = gmsh.model.geo.addLine(pt_br, pt_bl)
    plume_left = gmsh.model.geo.addLine(pt_bl, pt_tl)

    plume_loop = gmsh.model.geo.addCurveLoop([plume_top, plume_right, plume_bot, plume_left])
    plume_surface = gmsh.model.geo.addPlaneSurface([plume_loop])

    # ================================================================
    # TRANSFINITE MESHING
    # ================================================================
    # Nozzle top half
    gmsh.model.geo.mesh.setTransfiniteCurve(inlet_top, n_half + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(wall_spline_top, n_axial + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(exit_top, n_half + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(axis_top, n_axial + 1)
    gmsh.model.geo.mesh.setTransfiniteSurface(top_surface, "Left")
    gmsh.model.geo.mesh.setRecombine(2, top_surface)

    # Nozzle bottom half
    gmsh.model.geo.mesh.setTransfiniteCurve(inlet_bot, n_half + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(wall_spline_bot, n_axial + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(exit_bot, n_half + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(axis_bot, n_axial + 1)
    gmsh.model.geo.mesh.setTransfiniteSurface(bot_surface, "Left")
    gmsh.model.geo.mesh.setRecombine(2, bot_surface)

    # Plume (full height)
    n_plume_normal = 2 * n_half
    gmsh.model.geo.mesh.setTransfiniteCurve(plume_top, n_axial + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(plume_right, n_plume_normal + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(plume_bot, n_axial + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(plume_left, n_plume_normal + 1)
    gmsh.model.geo.mesh.setTransfiniteSurface(plume_surface, "Left")
    gmsh.model.geo.mesh.setRecombine(2, plume_surface)

    # ================================================================
    # PHYSICAL GROUPS
    # ================================================================
    gmsh.model.geo.addPhysicalGroup(1, [inlet_top, inlet_bot], name="inlet")
    gmsh.model.geo.addPhysicalGroup(1, [plume_right], name="outlet")
    gmsh.model.geo.addPhysicalGroup(1, [wall_spline_top, wall_spline_bot], name="wall")
    gmsh.model.geo.addPhysicalGroup(1, [plume_top, plume_bot], name="farfield")
    gmsh.model.geo.addPhysicalGroup(2, [top_surface, bot_surface, plume_surface], name="fluid")

    # ================================================================
    # GENERATE
    # ================================================================
    gmsh.model.geo.synchronize()
    gmsh.model.mesh.generate(2)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gmsh.write(str(output_path))

    gmsh.finalize()

    return output_path
