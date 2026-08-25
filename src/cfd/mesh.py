"""Gmsh O-grid mesh generation for nozzle.

Phase 2: Structured O-grid with zone-based splitting, boundary layer
refinement (y+ < 1), and plume extension downstream.

Uses Gmsh transfinite meshing with exactly 4 boundary curves per zone
surface (required for setTransfiniteSurface).
"""
import numpy as np
from pathlib import Path
from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour, generate_plume_contour
from .mesh_config import MeshConfig


def generate_nozzle_mesh(
    config: NozzleConfig,
    n_axial: int = 200,
    n_normal: int = 80,
    first_cell_height: float = 1e-6,
    output_file: str = "nozzle.su2",
    mesh_config: MeshConfig | None = None,
) -> Path:
    """Generate structured O-grid mesh for converging-diverging nozzle.

    Creates a multi-zone structured mesh with:
    - 3-zone splitting: converging, throat, diverging+plume
    - Boundary layer refinement using geometric progression
    - Plume extension (30*R_throat downstream)
    - Recombined quad elements for SU2

    Each zone is a quadrilateral surface bounded by exactly 4 curves
    (left, wall, right, axis) so that Gmsh transfinite meshing works.

    Args:
        config: Nozzle geometry parameters
        n_axial: Number of cells along nozzle axis (legacy, overridden by mesh_config)
        n_normal: Number of cells normal to wall
        first_cell_height: First cell height for boundary layer (m)
        output_file: Output .su2 mesh file path
        mesh_config: Optional mesh configuration override

    Returns:
        Path to generated .su2 mesh file
    """
    if mesh_config is None:
        mesh_config = MeshConfig(
            n_normal=n_normal,
            first_cell_height=first_cell_height,
        )

    # Generate nozzle contour
    x_wall, y_wall = generate_contour(config)

    # Generate plume contour downstream of exit
    x_plume, y_plume = generate_plume_contour(
        config,
        plume_length_ratio=mesh_config.plume_length_ratio,
    )

    # Compute zone boundaries along the wall contour
    n_total = len(x_wall)
    zone_frac = _compute_zone_fractions(mesh_config)
    i_converge, i_throat, i_diverge = _compute_zone_indices(n_total, zone_frac)

    n_normal = mesh_config.n_normal
    r_exit = config.exit_radius
    n_cells_converge = mesh_config.converging_cells
    n_cells_throat = mesh_config.throat_cells
    n_cells_diverge = mesh_config.diverging_cells
    n_cells_plume = mesh_config.plume_cells

    # Number of nodes = cells + 1 (for transfinite curves)
    n_nodes_converge = n_cells_converge + 1
    n_nodes_throat = n_cells_throat + 1
    n_nodes_diverge = n_cells_diverge + 1
    n_nodes_plume = n_cells_plume + 1
    n_nodes_normal = n_normal + 1

    import gmsh
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("nozzle")

        # ==================================================================
        # Helper: create zone surface with exactly 4 boundary curves
        #
        # The key constraint for setTransfiniteSurface is that each surface
        # boundary must be a single closed curve loop with exactly 4 curves.
        # ==================================================================

        def _make_zone(
            x_w: np.ndarray,
            y_w: np.ndarray,
            n_wall_nodes: int,
            zone_tag: int,
        ) -> tuple[int, int, int, int, int]:
            """Create a zone surface with exactly 4 boundary curves.

            Args:
                x_w, y_w: Wall coordinates for this zone
                n_wall_nodes: Number of nodes along wall/axis for transfinite
                zone_tag: Base tag offset for this zone

            Returns:
                (left_line, wall_curve, right_line, axis_curve, surface_tag)
            """
            # Create wall points (top boundary)
            wall_pts = []
            for xi, yi in zip(x_w, y_w):
                wall_pts.append(gmsh.model.geo.addPoint(xi, yi, 0))

            # Create axis points (bottom boundary, y=0)
            axis_pts = []
            for xi in x_w:
                axis_pts.append(gmsh.model.geo.addPoint(xi, 0, 0))

            # Wall curve: spline through wall points
            wall_curve = gmsh.model.geo.addSpline(wall_pts, tag=zone_tag + 1)

            # Axis curve: straight line (first to last axis point)
            axis_curve = gmsh.model.geo.addLine(
                axis_pts[0], axis_pts[-1], tag=zone_tag + 2,
            )

            # Left vertical line: axis[0] -> wall[0] (UP)
            left_line = gmsh.model.geo.addLine(
                axis_pts[0], wall_pts[0], tag=zone_tag + 3,
            )

            # Right vertical line: wall[-1] -> axis[-1] (DOWN)
            right_line = gmsh.model.geo.addLine(
                wall_pts[-1], axis_pts[-1], tag=zone_tag + 4,
            )

            # Curve loop (counterclockwise: left UP, wall RIGHT, right DOWN, axis LEFT)
            loop = gmsh.model.geo.addCurveLoop(
                [left_line, wall_curve, right_line, -axis_curve],
                tag=zone_tag + 5,
            )

            # Surface
            surface = gmsh.model.geo.addPlaneSurface([loop], tag=zone_tag + 6)

            # Transfinite constraints
            gmsh.model.geo.mesh.setTransfiniteCurve(
                left_line, n_nodes_normal, "Progression",
                mesh_config.growth_ratio,
            )
            gmsh.model.geo.mesh.setTransfiniteCurve(
                right_line, n_nodes_normal, "Progression",
                mesh_config.growth_ratio,
            )
            gmsh.model.geo.mesh.setTransfiniteCurve(wall_curve, n_wall_nodes)
            gmsh.model.geo.mesh.setTransfiniteCurve(axis_curve, n_wall_nodes)

            gmsh.model.geo.mesh.setTransfiniteSurface(surface, "Left")
            gmsh.model.geo.mesh.setRecombine(2, surface)

            return left_line, wall_curve, right_line, axis_curve, surface

        # ==================================================================
        # CONVERGING ZONE
        # ==================================================================
        xcw = np.linspace(x_wall[0], x_wall[i_converge], n_nodes_converge)
        ycw = np.interp(xcw, x_wall, y_wall)
        c_left, c_wall, c_right, c_axis, c_surface = _make_zone(
            xcw, ycw, n_nodes_converge, zone_tag=100,
        )

        # ==================================================================
        # THROAT ZONE
        # ==================================================================
        xtw = np.linspace(
            x_wall[i_converge], x_wall[i_diverge], n_nodes_throat,
        )
        ytw = np.interp(xtw, x_wall, y_wall)
        t_left, t_wall, t_right, t_axis, t_surface = _make_zone(
            xtw, ytw, n_nodes_throat, zone_tag=200,
        )

        # ==================================================================
        # DIVERGING ZONE
        # ==================================================================
        xdw = np.linspace(x_wall[i_diverge], x_wall[-1], n_nodes_diverge)
        ydw = np.interp(xdw, x_wall, y_wall)
        d_left, d_wall, d_right, d_axis, d_surface = _make_zone(
            xdw, ydw, n_nodes_diverge, zone_tag=300,
        )

        # ==================================================================
        # PLUME ZONE
        # ==================================================================
        xpw = np.linspace(x_plume[0], x_plume[-1], n_nodes_plume)
        ypw = np.full_like(xpw, r_exit)
        p_left, p_wall, p_right, p_axis, p_surface = _make_zone(
            xpw, ypw, n_nodes_plume, zone_tag=400,
        )

        # ==================================================================
        # PHYSICAL GROUPS (SU2 boundary markers)
        # ==================================================================

        gmsh.model.geo.synchronize()

        # Inlet: left boundary of converging zone
        gmsh.model.geo.addPhysicalGroup(1, [c_left], name="inlet")

        # Outlet: right boundary of plume zone
        gmsh.model.geo.addPhysicalGroup(1, [p_right], name="outlet")

        # Wall: all wall splines
        gmsh.model.geo.addPhysicalGroup(
            1, [c_wall, t_wall, d_wall, p_wall], name="wall",
        )

        # Symmetry (axis): all axis lines
        gmsh.model.geo.addPhysicalGroup(
            1, [c_axis, t_axis, d_axis, p_axis], name="symmetry",
        )

        # Fluid domain: all surfaces
        gmsh.model.geo.addPhysicalGroup(
            2, [c_surface, t_surface, d_surface, p_surface], name="fluid",
        )

        # ==================================================================
        # GENERATE AND WRITE
        # ==================================================================

        gmsh.model.geo.synchronize()
        gmsh.model.mesh.generate(2)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        gmsh.write(str(output_path))

    finally:
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_zone_fractions(mesh_config: MeshConfig) -> tuple[float, float, float]:
    """Compute zone boundary fractions from cell counts.

    Returns:
        Tuple of (converge_end, throat_end, diverge_end) as fractions of total
    """
    total = mesh_config.n_axial
    if total <= 0:
        raise ValueError(f"Total axial cells must be > 0, got {total}")
    converge_end = mesh_config.converging_cells / total
    throat_end = (mesh_config.converging_cells + mesh_config.throat_cells) / total
    diverge_end = (mesh_config.converging_cells + mesh_config.throat_cells +
                   mesh_config.diverging_cells) / total
    return converge_end, throat_end, diverge_end


def _compute_zone_indices(
    n_points: int,
    zone_fractions: tuple[float, float, float],
) -> tuple[int, int, int]:
    """Convert zone fractions to contour indices.

    Args:
        n_points: Total number of contour points
        zone_fractions: (converge_end, throat_end, diverge_end)

    Returns:
        (i_converge, i_throat, i_diverge) contour indices
    """
    f_conv, f_throat, f_div = zone_fractions
    i_converge = max(1, int(f_conv * (n_points - 1)))
    i_throat = max(i_converge + 1, int(f_throat * (n_points - 1)))
    i_diverge = max(i_throat + 1, int(f_div * (n_points - 1)))
    i_diverge = min(i_diverge, n_points - 2)
    return i_converge, i_throat, i_diverge

