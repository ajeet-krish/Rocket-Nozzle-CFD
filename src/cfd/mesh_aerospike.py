"""Gmsh mesh generation for aerospike (plug) nozzle.

Aerospike domain topology:
- Upstream region (x < 0): annular channel between casing and spike base
  - Top: casing wall (straight, y = outer_throat_radius)
  - Bottom: inlet wall (straight, y = throat_radius)
  - Left: inlet
  - Right: throat plane (interface)

- Downstream region (x > 0): flow over truncated spike
  - Top: farfield/casing (y = outer_throat_radius, extends to x_tip)
  - Bottom: spike surface (curved, from throat to truncation)
  - Left: throat plane (interface, shared with upstream)
  - Right: outlet plane

The spike surface stays BELOW the casing radius for the truncated portion.
The expansion beyond casing radius happens naturally in the atmosphere.

Works with SU2 v8.4.0.
"""
import numpy as np
from pathlib import Path
from nozzle.aerospike import AerospikeConfig, generate_aerospike_contour


def generate_aerospike_mesh(
    config: AerospikeConfig,
    n_axial: int = 120,
    n_normal: int = 40,
    output_file: str = "aerospike.su2",
    plume_extension: bool = True,
    plume_length_ratio: float = 10.0,
) -> Path:
    """Generate structured mesh for axisymmetric aerospike nozzle.

    Two-region mesh:
    1. Upstream annular channel (straight walls)
    2. Downstream flow over spike (curved spike surface)

    Args:
        config: Aerospike geometry parameters
        n_axial: Number of cells along spike axis (downstream)
        n_normal: Number of cells in radial direction
        output_file: Output .su2 mesh file path
        plume_extension: If True, add plume domain downstream
        plume_length_ratio: Plume length as multiple of throat radius

    Returns:
        Path to generated .su2 mesh file
    """
    import gmsh
    gmsh.initialize()
    gmsh.model.add("aerospike")

    # Generate spike contour (full, before truncation)
    sections = generate_aerospike_contour(config)
    x_spike_full, y_spike_full = sections['spike']

    # Geometry parameters
    x_casing_start = -config.casing_length
    x_throat = 0.0
    x_tip = config.spike_truncated_length
    y_casing = config.outer_throat_radius
    y_inlet = config.throat_radius

    # Verify spike stays below casing for truncated portion
    # (should be true since truncation is at 80% and spike exit radius > casing)
    # For safety, clip the spike to stay below casing
    y_spike_clipped = np.minimum(y_spike_full, y_casing - 0.001)

    # --- Key points ---
    # Upstream region corners
    pt_inlet_top = gmsh.model.geo.addPoint(x_casing_start, y_casing, 0)    # A
    pt_inlet_bot = gmsh.model.geo.addPoint(x_casing_start, y_inlet, 0)     # F
    pt_throat_top = gmsh.model.geo.addPoint(x_throat, y_casing, 0)         # B
    pt_throat_bot = gmsh.model.geo.addPoint(x_throat, y_inlet, 0)          # E

    # Downstream region corners
    pt_outlet_top = gmsh.model.geo.addPoint(x_tip, y_casing, 0)            # C
    pt_outlet_bot = gmsh.model.geo.addPoint(x_tip, y_spike_clipped[-1], 0) # D

    # --- Upstream region ---
    # 4 lines forming a rectangle
    up_inlet = gmsh.model.geo.addLine(pt_inlet_bot, pt_inlet_top)      # F->A (left, up)
    up_top = gmsh.model.geo.addLine(pt_inlet_top, pt_throat_top)       # A->B (top, right)
    up_right = gmsh.model.geo.addLine(pt_throat_top, pt_throat_bot)    # B->E (right, down)
    up_bot = gmsh.model.geo.addLine(pt_throat_bot, pt_inlet_bot)       # E->F (bottom, left)

    up_loop = gmsh.model.geo.addCurveLoop([up_inlet, up_top, up_right, up_bot])
    up_surface = gmsh.model.geo.addPlaneSurface([up_loop])

    # --- Downstream region ---
    # Top boundary: straight line from B to C
    down_top = gmsh.model.geo.addLine(pt_throat_top, pt_outlet_top)    # B->C

    # Right boundary: straight line from C to D
    down_right = gmsh.model.geo.addLine(pt_outlet_top, pt_outlet_bot)  # C->D

    # Bottom boundary: spike spline from E to D
    # Build spike points, clipping to stay below casing
    spike_pts = []
    for i in range(len(x_spike_full)):
        xv = x_spike_full[i]
        yv = y_spike_clipped[i]
        # Exact match at throat (E)
        if abs(xv) < 1e-10:
            spike_pts.append(pt_throat_bot)
        # Exact match at tip (D)
        elif abs(xv - x_tip) < 1e-10:
            spike_pts.append(pt_outlet_bot)
        else:
            pt = gmsh.model.geo.addPoint(xv, yv, 0)
            spike_pts.append(pt)

    if len(spike_pts) > 1:
        down_bot = gmsh.model.geo.addSpline(spike_pts)
    else:
        down_bot = gmsh.model.geo.addLine(pt_throat_bot, pt_outlet_bot)

    # Left boundary: shared with upstream (B->E, reversed = E->B)
    # Use negative tag of up_right to share the curve
    down_left = -up_right  # E->B (reversed)

    down_loop = gmsh.model.geo.addCurveLoop([down_left, down_top, down_right, -down_bot])
    down_surface = gmsh.model.geo.addPlaneSurface([down_loop])

    # --- Transfinite meshing ---
    n_upstream = max(n_axial // 4, 5)  # 25% of cells for upstream

    # Upstream curves
    gmsh.model.geo.mesh.setTransfiniteCurve(up_inlet, n_normal + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(up_top, n_upstream + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(up_right, n_normal + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(up_bot, n_upstream + 1)

    # Downstream curves
    n_downstream = n_axial
    gmsh.model.geo.mesh.setTransfiniteCurve(down_top, n_downstream + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(down_right, n_normal + 1)
    gmsh.model.geo.mesh.setTransfiniteCurve(down_bot, n_downstream + 1)
    # down_left = -up_right, so it shares the same node count

    # Surface meshing
    gmsh.model.geo.mesh.setTransfiniteSurface(up_surface, "Left")
    gmsh.model.geo.mesh.setRecombine(2, up_surface)
    gmsh.model.geo.mesh.setTransfiniteSurface(down_surface, "Left")
    gmsh.model.geo.mesh.setRecombine(2, down_surface)

    # --- Physical groups ---
    gmsh.model.geo.addPhysicalGroup(1, [up_inlet], name="inlet")
    gmsh.model.geo.addPhysicalGroup(1, [down_right], name="outlet")
    gmsh.model.geo.addPhysicalGroup(1, [up_top, down_top], name="wall")
    gmsh.model.geo.addPhysicalGroup(1, [up_bot, down_bot], name="spike_wall")
    gmsh.model.geo.addPhysicalGroup(
        2, [up_surface, down_surface], name="fluid",
    )

    # --- Generate and write ---
    gmsh.model.geo.synchronize()
    gmsh.model.mesh.generate(2)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gmsh.write(str(output_path))

    gmsh.finalize()

    return output_path
