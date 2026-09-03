"""Gmsh O-grid mesh generation for nozzle.

Two wall curve strategies:
- multi_curve=True:  Per-section Gmsh curves (circle arcs, splines, lines).
                     More geometrically accurate but can cause SU2 divergence
                     for engines with large expansion ratios.
- multi_curve=False: Single spline through all wall points (default).
                     More robust; works for all engines.

Plus optional plume extension zone for external shock diamonds.
Works with SU2 v8.4.0.
"""
import numpy as np
from pathlib import Path
from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour_sections, ContourSection


# Cell distribution fractions per section (must sum to 1.0)
_SECTION_FRACTIONS = {
    "chamber": 0.10,
    "convergent": 0.15,
    "entrant_arc": 0.20,
    "exit_arc": 0.20,
    "bell": 0.35,
}

# Mesh parameters per section: (parameter_type, parameter_value)
# None means uniform (no clustering)
_SECTION_MESH_PARAMS: dict[str, tuple[str | None, float | None]] = {
    "chamber": (None, None),
    "convergent": (None, None),
    "entrant_arc": ("Progression", 1.15),
    "exit_arc": ("Progression", 1.15),
    "bell": ("Bump", 0.7),  # bump_coeff overridden at runtime
}


def _compute_section_cells(
    sections: list[ContourSection],
    n_axial: int,
) -> dict[str, int]:
    """Compute cell count for each section, summing exactly to n_axial.

    Uses specified fractions, redistributed proportionally when some
    sections are absent.

    Args:
        sections: List of contour sections present in the nozzle
        n_axial: Total axial cells to distribute

    Returns:
        Dictionary mapping section name to cell count
    """
    present_names = [s.name for s in sections]
    total_frac = sum(_SECTION_FRACTIONS[name] for name in present_names)

    # Compute raw fractional cells
    raw = {
        name: _SECTION_FRACTIONS[name] / total_frac * n_axial
        for name in present_names
    }

    # Round down to integers
    cells = {name: int(v) for name, v in raw.items()}

    # Distribute remaining cells to sections with largest fractional remainder
    remainder = n_axial - sum(cells.values())
    for name in sorted(cells, key=lambda k: raw[k] - cells[k], reverse=True):
        if remainder <= 0:
            break
        cells[name] += 1
        remainder -= 1

    return cells


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
    bump_coeff: float = 0.7,
    multi_curve: bool = False,
) -> Path:
    """Generate structured O-grid mesh for converging-diverging nozzle.

    Creates a mesh with:
    - Wall curve(s) matching nozzle contour geometry
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
        plume_extension: If True, add plume domain downstream
        plume_length_ratio: Plume length as multiple of throat radius
        plume_radius_ratio: Plume width as multiple of exit radius
        bump_coeff: Bump coefficient for bell section clustering
        multi_curve: If True, use per-section Gmsh curves (circle arcs for
            arcs, splines for bell). More geometrically accurate but can
            cause SU2 divergence for large expansion ratios. If False
            (default), use a single spline for the entire wall contour.

    Returns:
        Path to generated .su2 mesh file
    """
    import gmsh
    gmsh.initialize()
    gmsh.model.add("nozzle")

    # --- Build wall curve(s) ---

    if multi_curve:
        # Multi-curve: separate Gmsh curves per geometric section.
        sections = generate_contour_sections(config)
        section_cells = _compute_section_cells(sections, n_axial)

        wall_curves: list[int] = []
        wall_first_pt: int | None = None
        wall_last_pt: int | None = None
        prev_p_end: int | None = None

        for i, section in enumerate(sections):
            if i == 0:
                p_start = gmsh.model.geo.addPoint(
                    section.x[0], section.y[0], 0,
                )
                wall_first_pt = p_start
            else:
                p_start = prev_p_end

            p_end = gmsh.model.geo.addPoint(
                section.x[-1], section.y[-1], 0,
            )

            if section.curve_type == "line":
                curve = gmsh.model.geo.addLine(p_start, p_end)

            elif section.curve_type == "circle_arc":
                p_center = gmsh.model.geo.addPoint(
                    section.center_x, section.center_y, 0,
                )
                curve = gmsh.model.geo.addCircleArc(
                    p_start, p_center, p_end,
                )

            elif section.curve_type == "spline":
                pts = [p_start]
                for j in range(1, len(section.x) - 1):
                    pts.append(
                        gmsh.model.geo.addPoint(
                            section.x[j], section.y[j], 0,
                        )
                    )
                pts.append(p_end)
                curve = gmsh.model.geo.addSpline(pts)

            else:
                raise ValueError(
                    f"Unknown curve type: {section.curve_type}"
                )

            wall_curves.append(curve)
            prev_p_end = p_end

        wall_last_pt = prev_p_end
        x_min = float(sections[0].x[0])
        x_max = float(sections[-1].x[-1])

        # Set transfinite curves: section-specific cell counts and clustering
        for section, curve in zip(sections, wall_curves):
            n_cells = section_cells[section.name]
            param_type, param_value = _SECTION_MESH_PARAMS[section.name]

            if section.name == "bell":
                param_value = bump_coeff

            if param_type is not None:
                gmsh.model.geo.mesh.setTransfiniteCurve(
                    curve, n_cells + 1, param_type, param_value,
                )
            else:
                gmsh.model.geo.mesh.setTransfiniteCurve(
                    curve, n_cells + 1,
                )

    else:
        # Single-spline: one spline for the entire wall contour.
        # More robust for engines with large expansion ratios.
        from nozzle.geometry import generate_contour

        x_wall, y_wall = generate_contour(config)

        wall_pts: list[int] = []
        for i in range(len(x_wall)):
            pt = gmsh.model.geo.addPoint(x_wall[i], y_wall[i], 0)
            wall_pts.append(pt)

        wall_first_pt = wall_pts[0]
        wall_last_pt = wall_pts[-1]
        wall_curves = [gmsh.model.geo.addSpline(wall_pts)]
        x_min = float(x_wall[0])
        x_max = float(x_wall[-1])

        # Uniform distribution along the wall spline
        gmsh.model.geo.mesh.setTransfiniteCurve(
            wall_curves[0], n_axial + 1,
        )

    # --- Boundary lines (inlet, outlet, axis) ---

    axis_start = gmsh.model.geo.addPoint(x_min, 0, 0)
    axis_end = gmsh.model.geo.addPoint(x_max, 0, 0)

    inlet_line = gmsh.model.geo.addLine(axis_start, wall_first_pt)
    exit_line = gmsh.model.geo.addLine(wall_last_pt, axis_end)
    axis_line = gmsh.model.geo.addLine(axis_end, axis_start)

    # --- Nozzle surface ---

    nozzle_loop = gmsh.model.geo.addCurveLoop(
        [inlet_line] + wall_curves + [exit_line, axis_line],
    )
    nozzle_surface = gmsh.model.geo.addPlaneSurface([nozzle_loop])

    # --- Transfinite meshing (inlet, exit, axis) ---

    # Inlet and outlet lines (normal direction)
    if rans_mode:
        growth_ratio = 1.15
        gmsh.model.geo.mesh.setTransfiniteCurve(
            inlet_line, n_normal + 1, "Progression", growth_ratio,
        )
        gmsh.model.geo.mesh.setTransfiniteCurve(
            exit_line, n_normal + 1, "Progression", growth_ratio,
        )
    else:
        gmsh.model.geo.mesh.setTransfiniteCurve(inlet_line, n_normal + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(exit_line, n_normal + 1)

    # Axis line (axial direction, uniform)
    gmsh.model.geo.mesh.setTransfiniteCurve(axis_line, n_axial + 1)

    # Surface meshing
    # Try with cornerTags first; fall back to "Left" if it fails
    try:
        gmsh.model.geo.mesh.setTransfiniteSurface(
            nozzle_surface, "Left",
            cornerTags=[axis_start, wall_first_pt, wall_last_pt, axis_end],
        )
    except Exception:
        gmsh.model.geo.mesh.setTransfiniteSurface(nozzle_surface, "Left")
    gmsh.model.geo.mesh.setRecombine(2, nozzle_surface)

    # --- Plume domain (optional) ---

    plume_top: int | None = None
    plume_outlet: int | None = None
    plume_axis: int | None = None
    plume_surface: int | None = None
    plume_left: int | None = None

    if plume_extension:
        plume_length = plume_length_ratio * config.throat_radius
        x_exit = config.computed_diverging_length
        x_plume_end = x_exit + plume_length
        plume_width = plume_radius_ratio * config.exit_radius

        # Plume domain: two-region rectangular box
        # Region 1 (transition): x_exit to x_exit+0.1m, vertical jump from exit_radius to plume_width
        # Region 2 (main plume): x_exit+0.1m to x_plume_end, full-width rectangle
        x_plume_start = x_exit + 0.1  # 10cm transition zone

        # Points
        plume_jump_top = gmsh.model.geo.addPoint(x_plume_start, plume_width, 0)
        plume_top_right = gmsh.model.geo.addPoint(x_plume_end, plume_width, 0)
        plume_bot_right = gmsh.model.geo.addPoint(x_plume_end, 0, 0)
        plume_jump_bot = gmsh.model.geo.addPoint(x_plume_start, 0, 0)

        # Shared interface: reversed exit_line for conformal mesh
        plume_left = -exit_line

        # Region 1 boundary (transition from nozzle to plume width):
        # Left: shared exit interface (plume_left)
        # Top: angled line from wall_last_pt to plume_jump_top
        # Right: vertical line from plume_jump_top to plume_jump_bot
        # Bottom: axis from plume_jump_bot to axis_end (short segment)
        plume_r1_top = gmsh.model.geo.addLine(wall_last_pt, plume_jump_top)
        plume_r1_right = gmsh.model.geo.addLine(plume_jump_top, plume_jump_bot)
        plume_r1_bot = gmsh.model.geo.addLine(plume_jump_bot, axis_end)

        plume_r1_loop = gmsh.model.geo.addCurveLoop(
            [plume_left, plume_r1_top, plume_r1_right, plume_r1_bot],
        )
        plume_r1_surface = gmsh.model.geo.addPlaneSurface([plume_r1_loop])

        # Region 2 boundary (main plume rectangle):
        # Left: vertical line from plume_jump_top to plume_jump_bot (shared with R1)
        # Top: horizontal line across main plume
        # Right: vertical outlet
        # Bottom: axis
        plume_r2_left = -plume_r1_right  # Reversed = upward direction
        plume_r2_top = gmsh.model.geo.addLine(plume_jump_top, plume_top_right)
        plume_r2_right = gmsh.model.geo.addLine(plume_top_right, plume_bot_right)
        plume_r2_bot = gmsh.model.geo.addLine(plume_bot_right, plume_jump_bot)

        plume_r2_loop = gmsh.model.geo.addCurveLoop(
            [plume_r2_left, plume_r2_top, plume_r2_right, plume_r2_bot],
        )
        plume_r2_surface = gmsh.model.geo.addPlaneSurface([plume_r2_loop])

        # Transfinite meshing
        # Region 1 (transition)
        gmsh.model.geo.mesh.setTransfiniteCurve(plume_r1_top, max(n_axial // 10, 3) + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(plume_r1_right, n_normal + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(plume_r1_bot, max(n_axial // 10, 3) + 1)
        # plume_left = -exit_line, shares node count with exit_line

        # Region 2 (main plume)
        n_plume_r2 = n_axial - max(n_axial // 10, 3)
        gmsh.model.geo.mesh.setTransfiniteCurve(plume_r2_top, n_plume_r2 + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(plume_r2_right, n_normal + 1)
        gmsh.model.geo.mesh.setTransfiniteCurve(plume_r2_bot, n_plume_r2 + 1)
        # plume_r2_left = -plume_r1_right, shares node count

        gmsh.model.geo.mesh.setTransfiniteSurface(plume_r1_surface, "Left")
        gmsh.model.geo.mesh.setRecombine(2, plume_r1_surface)
        gmsh.model.geo.mesh.setTransfiniteSurface(plume_r2_surface, "Left")
        gmsh.model.geo.mesh.setRecombine(2, plume_r2_surface)

    # --- Physical groups ---

    if plume_extension:
        # Nozzle + plume: exit_line is the shared internal interface (not a boundary)
        gmsh.model.geo.addPhysicalGroup(1, [inlet_line], name="inlet")
        gmsh.model.geo.addPhysicalGroup(1, [plume_r2_right], name="outlet")
        gmsh.model.geo.addPhysicalGroup(1, wall_curves + [plume_r1_top], name="wall")
        gmsh.model.geo.addPhysicalGroup(
            1, [axis_line, plume_r1_bot, plume_r2_bot], name="symmetry",
        )
        gmsh.model.geo.addPhysicalGroup(1, [plume_r2_top], name="farfield")
        gmsh.model.geo.addPhysicalGroup(
            2, [nozzle_surface, plume_r1_surface, plume_r2_surface], name="fluid",
        )
    else:
        # Nozzle only
        gmsh.model.geo.addPhysicalGroup(1, [inlet_line], name="inlet")
        gmsh.model.geo.addPhysicalGroup(1, [exit_line], name="outlet")
        gmsh.model.geo.addPhysicalGroup(1, wall_curves, name="wall")
        gmsh.model.geo.addPhysicalGroup(1, [axis_line], name="symmetry")
        gmsh.model.geo.addPhysicalGroup(2, [nozzle_surface], name="fluid")

    # --- Generate and write ---

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
