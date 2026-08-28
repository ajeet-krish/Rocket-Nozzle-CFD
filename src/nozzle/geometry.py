"""Nozzle contour generation (conical and Rao bell)."""
from dataclasses import dataclass
import numpy as np
from .config import NozzleConfig


@dataclass
class ContourSection:
    """A section of the nozzle contour.

    Attributes:
        name: Section identifier ("chamber", "convergent", "entrant_arc",
              "exit_arc", "bell")
        x: Axial coordinates (m)
        y: Radial coordinates (m)
        curve_type: Gmsh curve type ("line", "spline", "circle_arc")
        center_x: Circle arc center x (only for circle_arc)
        center_y: Circle arc center y (only for circle_arc)
        radius: Circle arc radius (only for circle_arc)
        start_angle: Circle arc start angle in radians (only for circle_arc)
        end_angle: Circle arc end angle in radians (only for circle_arc)
    """
    name: str
    x: np.ndarray
    y: np.ndarray
    curve_type: str  # "line", "spline", "circle_arc"
    center_x: float = 0.0
    center_y: float = 0.0
    radius: float = 0.0
    start_angle: float = 0.0
    end_angle: float = 0.0


def generate_contour(config: NozzleConfig) -> tuple[np.ndarray, np.ndarray]:
    """Generate (x, y) contour points for a nozzle.

    Sections (if chamber_length > 0):
      1. Chamber: straight cylinder at chamber_radius
      2. Convergent: curved or linear transition to entrant arc start
      3a. Entrant arc: 1.5*Rt radius, smooth throat transition
      3b. Exit arc: throat_radius_of_curvature or 0.382*Rt, steep initial divergence
      3c. Bell: quadratic Bezier from end of exit arc to exit

    If chamber_length == 0: skip chamber section (v1 behavior).
    If throat_radius_of_curvature == 0: use linear convergent (v1 behavior).

    Args:
        config: Nozzle geometry parameters

    Returns:
        x: axial coordinates (m), shape (num_points,)
        y: radial coordinates (m), shape (num_points,)
    """
    n = config.num_points

    # Use computed diverging length (from ideal formula if nozzle_length_fraction set)
    div_length = config.computed_diverging_length

    # Determine section lengths and point counts
    if config.chamber_length > 0:
        # 3 sections: chamber (20%), convergent (25%), divergent (55%)
        n_chamber = max(n // 5, 10)
        n_converge = max(n // 4, 10)
        n_diverge = n - n_chamber - n_converge
    else:
        # 2 sections: convergent (25%), divergent (75%) - v1 behavior
        n_chamber = 0
        n_converge = n // 4
        n_diverge = n - n_converge

    sections: list[tuple[np.ndarray, np.ndarray]] = []

    # Section 1: Chamber (straight cylinder)
    if config.chamber_length > 0:
        # Layout: throat at x=0, convergent in [-converging_length, 0],
        #         chamber in [-converging_length - chamber_length, -converging_length]
        x_start = -(config.converging_length + config.chamber_length)
        x_chamber_end = -config.converging_length
        x_chamber = np.linspace(x_start, x_chamber_end, n_chamber)
        y_chamber = np.full_like(x_chamber, config.effective_inlet_radius)
        sections.append((x_chamber, y_chamber))

    # Compute entrant arc parameters (Fix 1)
    entrant_radius = 1.5 * config.throat_radius
    center_y = 2.5 * config.throat_radius
    angle_end = -np.pi / 2  # -90 deg (horizontal at throat, slope=0)

    # Start angle: -135 deg (C1 continuous with 45 deg convergent half-angle)
    angle_start_target = np.radians(-135)
    x_arc_start_target = entrant_radius * np.cos(angle_start_target)

    # Clip to convergent range so arc starts within the convergent section
    x_converge_end = max(x_arc_start_target, -config.converging_length)

    if abs(x_converge_end - x_arc_start_target) > 1e-12:
        # Compute angle from clipped x coordinate
        cos_angle = np.clip(x_converge_end / entrant_radius, -1, 1)
        angle_start = -np.arccos(cos_angle)
    else:
        angle_start = angle_start_target

    y_arc_start = entrant_radius * np.sin(angle_start) + center_y
    slope_arc_start = -np.cos(angle_start) / (np.sin(angle_start) + 1e-20)

    # Section 2: Convergent (ends at entrant arc start point)
    if x_converge_end > -config.converging_length + 1e-12:
        x_converge = np.linspace(-config.converging_length, x_converge_end, n_converge)

        if config.throat_radius_of_curvature > 0:
            # Curved convergent with C1 continuity to entrant arc
            y_converge = _curved_convergent_to_arc(
                config.effective_inlet_radius,
                y_arc_start,
                x_converge,
                slope_arc_start,
            )
        else:
            # Linear convergent (v1 behavior)
            y_converge = np.linspace(
                config.effective_inlet_radius, y_arc_start, n_converge
            )

        sections.append((x_converge, y_converge))

    # Section 3a: Entrant arc (1.5*Rt radius, smooth throat transition)
    n_entrant = min(max(n_diverge // 5, 20), n_diverge - 2)
    x_entrant, y_entrant = _entrant_arc(
        config.throat_radius, angle_start, angle_end, n_entrant
    )
    sections.append((x_entrant, y_entrant))

    # Section 3b: Exit arc (Fix 2: use throat_radius_of_curvature if set)
    exit_arc_radius = (
        config.throat_radius_of_curvature
        if config.throat_radius_of_curvature > 0
        else 0.382 * config.throat_radius
    )
    theta_n_rad = np.radians(config.theta_n)
    n_exit_arc = min(max(n_diverge // 5, 20), n_diverge - n_entrant - 1)
    angle_start_exit = -np.pi / 2  # -90 deg (vertical at throat)
    angle_end_exit = theta_n_rad - np.pi / 2  # (theta_n - 90) deg
    angles_exit = np.linspace(angle_start_exit, angle_end_exit, n_exit_arc)
    x_exit_arc = exit_arc_radius * np.cos(angles_exit)
    y_exit_arc = (
        exit_arc_radius * np.sin(angles_exit)
        + exit_arc_radius
        + config.throat_radius
    )
    sections.append((x_exit_arc, y_exit_arc))

    # Section 3c: Bell (Fix 6: quadratic Bezier instead of cubic)
    x_arc_end = x_exit_arc[-1]
    y_arc_end = y_exit_arc[-1]
    # Slope at end of exit arc: dy/dx = -cot(angle_end) = tan(theta_n)
    slope_arc_end = np.tan(theta_n_rad)
    n_bell = max(n_diverge - n_entrant - n_exit_arc, 1)
    x_bell = np.linspace(x_arc_end, div_length, n_bell)
    y_bell = _rao_bell_bezier(
        y_arc_end,
        config.exit_radius,
        div_length - x_arc_end,
        x_bell - x_arc_end,
        slope_start=slope_arc_end,
        slope_end=np.tan(np.radians(config.theta_e)),
    )
    sections.append((x_bell, y_bell))

    # Concatenate all sections (exclude duplicate points at boundaries)
    x_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    for i, (xs, ys) in enumerate(sections):
        if i > 0 and len(x_parts) > 0:
            # Skip first point if it matches last point of previous section
            if abs(xs[0] - x_parts[-1][-1]) < 1e-12:
                xs = xs[1:]
                ys = ys[1:]
        x_parts.append(xs)
        y_parts.append(ys)

    x = np.concatenate(x_parts)
    y = np.concatenate(y_parts)

    return x, y


def generate_contour_sections(config: NozzleConfig) -> list[ContourSection]:
    """Generate nozzle contour as a list of geometric sections.

    Returns sections in order: chamber, convergent, entrant_arc, exit_arc, bell.
    Each section has the curve type needed for Gmsh mesh generation.

    The section boundaries are shared points (no gaps) suitable for creating
    separate Gmsh curves that meet at section transitions.

    Args:
        config: Nozzle geometry parameters

    Returns:
        List of ContourSection objects, one per geometric section.
        Empty sections (zero-length) are omitted.
    """
    # Use computed diverging length (from ideal formula if nozzle_length_fraction set)
    div_length = config.computed_diverging_length

    # Determine section point counts
    if config.chamber_length > 0:
        n_chamber = max(config.num_points // 5, 10)
        n_converge = max(config.num_points // 4, 10)
        n_diverge = config.num_points - n_chamber - n_converge
    else:
        n_chamber = 0
        n_converge = config.num_points // 4
        n_diverge = config.num_points - n_converge

    sections: list[ContourSection] = []

    # Compute entrant arc parameters
    entrant_radius = 1.5 * config.throat_radius
    center_y_entrant = 2.5 * config.throat_radius
    angle_end_entrant = -np.pi / 2  # -90 deg (horizontal at throat)

    angle_start_target = np.radians(-135)
    x_arc_start_target = entrant_radius * np.cos(angle_start_target)

    x_converge_end = max(x_arc_start_target, -config.converging_length)

    if abs(x_converge_end - x_arc_start_target) > 1e-12:
        cos_angle = np.clip(x_converge_end / entrant_radius, -1, 1)
        angle_start_entrant = -np.arccos(cos_angle)
    else:
        angle_start_entrant = angle_start_target

    y_arc_start = entrant_radius * np.sin(angle_start_entrant) + center_y_entrant
    slope_arc_start = -np.cos(angle_start_entrant) / (
        np.sin(angle_start_entrant) + 1e-20
    )

    # Section 1: Chamber (straight cylinder)
    if config.chamber_length > 0:
        x_start = -(config.converging_length + config.chamber_length)
        x_chamber_end = -config.converging_length
        x_chamber = np.linspace(x_start, x_chamber_end, n_chamber)
        y_chamber = np.full_like(x_chamber, config.effective_inlet_radius)
        sections.append(ContourSection(
            name="chamber",
            x=x_chamber, y=y_chamber,
            curve_type="line",
        ))

    # Section 2: Convergent (ends at entrant arc start point)
    if x_converge_end > -config.converging_length + 1e-12:
        x_converge = np.linspace(-config.converging_length, x_converge_end, n_converge)

        if config.throat_radius_of_curvature > 0:
            y_converge = _curved_convergent_to_arc(
                config.effective_inlet_radius,
                y_arc_start,
                x_converge,
                slope_arc_start,
            )
            curve_type = "spline"
        else:
            y_converge = np.linspace(
                config.effective_inlet_radius, y_arc_start, n_converge
            )
            curve_type = "line"

        sections.append(ContourSection(
            name="convergent",
            x=x_converge, y=y_converge,
            curve_type=curve_type,
        ))

    # Section 3a: Entrant arc (1.5*Rt radius, smooth throat transition)
    n_entrant = min(max(n_diverge // 5, 20), n_diverge - 2)
    x_entrant, y_entrant = _entrant_arc(
        config.throat_radius, angle_start_entrant, angle_end_entrant, n_entrant
    )
    sections.append(ContourSection(
        name="entrant_arc",
        x=x_entrant, y=y_entrant,
        curve_type="circle_arc",
        center_x=0.0,
        center_y=center_y_entrant,
        radius=entrant_radius,
        start_angle=angle_start_entrant,
        end_angle=angle_end_entrant,
    ))

    # Section 3b: Exit arc
    exit_arc_radius = (
        config.throat_radius_of_curvature
        if config.throat_radius_of_curvature > 0
        else 0.382 * config.throat_radius
    )
    theta_n_rad = np.radians(config.theta_n)
    n_exit_arc = min(max(n_diverge // 5, 20), n_diverge - n_entrant - 1)
    angle_start_exit = -np.pi / 2
    angle_end_exit = theta_n_rad - np.pi / 2
    angles_exit = np.linspace(angle_start_exit, angle_end_exit, n_exit_arc)
    x_exit_arc = exit_arc_radius * np.cos(angles_exit)
    y_exit_arc = (
        exit_arc_radius * np.sin(angles_exit)
        + exit_arc_radius
        + config.throat_radius
    )
    center_y_exit = exit_arc_radius + config.throat_radius
    sections.append(ContourSection(
        name="exit_arc",
        x=x_exit_arc, y=y_exit_arc,
        curve_type="circle_arc",
        center_x=0.0,
        center_y=center_y_exit,
        radius=exit_arc_radius,
        start_angle=angle_start_exit,
        end_angle=angle_end_exit,
    ))

    # Section 3c: Bell (quadratic Bezier)
    x_arc_end = x_exit_arc[-1]
    y_arc_end = y_exit_arc[-1]
    slope_arc_end = np.tan(theta_n_rad)
    n_bell = max(n_diverge - n_entrant - n_exit_arc, 1)
    x_bell = np.linspace(x_arc_end, div_length, n_bell)
    y_bell = _rao_bell_bezier(
        y_arc_end,
        config.exit_radius,
        div_length - x_arc_end,
        x_bell - x_arc_end,
        slope_start=slope_arc_end,
        slope_end=np.tan(np.radians(config.theta_e)),
    )
    sections.append(ContourSection(
        name="bell",
        x=x_bell, y=y_bell,
        curve_type="spline",
    ))

    return sections


def _entrant_arc(
    throat_radius: float,
    angle_start: float,
    angle_end: float,
    n_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate entrant arc (circular arc before throat).

    The arc has radius 1.5*Rt and center at (0, 2.5*Rt).
    It provides a smooth C1 transition from convergent to throat.

    At angle_end = -90 deg (throat): x=0, y=Rt, slope=0 (horizontal).
    At angle_start (typically -135 deg): connects to convergent section.

    Args:
        throat_radius: Throat radius (m)
        angle_start: Start angle (radians, typically -135 deg)
        angle_end: End angle (radians, -90 deg = throat)
        n_points: Number of points

    Returns:
        (x, y) coordinate arrays
    """
    radius = 1.5 * throat_radius
    center_y = 2.5 * throat_radius

    angles = np.linspace(angle_start, angle_end, n_points)
    x = radius * np.cos(angles)
    y = radius * np.sin(angles) + center_y

    # Clamp last point to exact throat location (avoids floating-point drift)
    x[-1] = 0.0
    y[-1] = throat_radius

    return x, y


def _curved_convergent_to_arc(
    r_inlet: float,
    r_end: float,
    x: np.ndarray,
    slope_end: float,
) -> np.ndarray:
    """Compute curved convergent section ending at entrant arc start.

    Uses C1 continuity: tangent to cylinder at inlet (slope=0),
    tangent to entrant arc at end (slope=slope_end).

    Cubic polynomial: y(t) = a*t^3 + b*t^2 + c*t + d
    with boundary conditions:
      y(0) = r_inlet,  y'(0) = 0
      y(1) = r_end,    y'(1) = slope_end * dx_dt

    The slope is clamped to ensure monotonic decrease (no overshoot below throat).

    Args:
        r_inlet: Inlet (chamber) radius (m)
        r_end: End radius at entrant arc start (m)
        x: Axial coordinates in [-length, x_arc_start]
        slope_end: Actual slope (dy/dx) at end of convergent

    Returns:
        Radial coordinates (m) at each x location
    """
    if x.max() - x.min() < 1e-12:
        return np.full_like(x, r_inlet)

    # Normalize x to [0, 1] where t=0 is inlet and t=1 is arc start
    t = (x - x.min()) / (x.max() - x.min())

    # End slope in normalized space: dy/dt = dy/dx * dx/dt
    dx_dt = x.max() - x.min()
    slope_exit = slope_end * dx_dt

    # Clamp slope to ensure monotonic decrease.
    # For a cubic with y'(0)=0, monotonicity requires slope_exit >= 3*(r_end - r_inlet).
    max_monotonic_slope = 3.0 * (r_end - r_inlet)  # negative value
    if slope_exit < max_monotonic_slope:
        slope_exit = max_monotonic_slope

    # Cubic: y(t) = a*t^3 + b*t^2 + c*t + d
    # y(0) = d = r_inlet
    # y'(0) = c = 0
    # y(1) = a + b + c + d = r_end
    # y'(1) = 3a + 2b + c = slope_exit
    d = r_inlet
    c = 0.0
    # a + b = r_end - d
    # 3a + 2b = slope_exit
    a = slope_exit - 2.0 * (r_end - d)
    b = 3.0 * (r_end - d) - slope_exit

    y = a * t**3 + b * t**2 + c * t + d

    return y


def _curved_convergent(
    r_inlet: float,
    r_throat: float,
    half_angle: float,
    x: np.ndarray,
    length: float,
) -> np.ndarray:
    """Compute curved convergent section using cubic polynomial.

    Uses C1 continuity: tangent to cylinder at inlet, tangent to throat at outlet.

    The convergent section transitions from r_inlet to r_throat over `length`.
    At the inlet (x=-length), the slope is 0 (tangent to chamber wall).
    At the outlet (x=0), the slope is -tan(half_angle) (converging toward throat).

    Uses cubic polynomial: y(t) = a*t^3 + b*t^2 + c*t + d
    with boundary conditions:
      y(0) = r_inlet,  y'(0) = 0
      y(1) = r_throat, y'(1) = -tan(half_angle) * length

    The slope is clamped to ensure monotonic decrease (no overshoot below throat).

    Args:
        r_inlet: Inlet (chamber) radius (m)
        r_throat: Throat radius (m)
        half_angle: Convergent half-angle (degrees)
        x: Axial coordinates in [-length, 0]
        length: Convergent section length (m)

    Returns:
        Radial coordinates (m) at each x location
    """
    # Normalize x to [0, 1] where t=0 is inlet and t=1 is throat
    t = (x - x.min()) / (x.max() - x.min() + 1e-12)

    # Boundary conditions in normalized space:
    # y(0) = r_inlet, y'(0) = 0
    # y(1) = r_throat, y'(1) = slope_exit (negative, scaled by length)
    # The radius decreases, so the slope is negative
    slope_exit = -np.tan(np.radians(half_angle)) * length

    # Clamp slope to ensure monotonic decrease.
    # For a cubic with y'(0)=0, monotonicity requires slope_exit >= 3*(r_throat - r_inlet).
    # If the requested angle is too steep, clamp to the maximum monotonic slope.
    max_monotonic_slope = 3.0 * (r_throat - r_inlet)  # negative value
    if slope_exit < max_monotonic_slope:
        slope_exit = max_monotonic_slope

    # Cubic: y(t) = a*t^3 + b*t^2 + c*t + d
    # y(0) = d = r_inlet
    # y'(0) = c = 0
    # y(1) = a + b + c + d = r_throat
    # y'(1) = 3a + 2b + c = slope_exit
    d = r_inlet
    c = 0.0
    # a + b = r_throat - d
    # 3a + 2b = slope_exit
    a = slope_exit - 2.0 * (r_throat - d)
    b = 3.0 * (r_throat - d) - slope_exit

    y = a * t**3 + b * t**2 + c * t + d

    return y


def _rao_bell(
    r_throat: float,
    r_exit: float,
    length: float,
    x: np.ndarray,
    theta_n: float = 30.0,
    theta_e: float = 0.0,
) -> np.ndarray:
    """Compute Rao parabolic bell contour.

    Uses a cubic polynomial that exactly matches:
    - Radius at throat (x=0): r_throat
    - Radius at exit (x=length): r_exit
    - Slope at throat: tan(theta_n)
    - Slope at exit: tan(theta_e)

    Args:
        r_throat: Throat radius (m)
        r_exit: Exit radius (m)
        length: Diverging section length (m)
        x: Axial coordinates (m)
        theta_n: Wall angle at throat (degrees)
        theta_e: Wall angle at exit (degrees)

    Returns:
        Radial coordinates (m) at each x location
    """
    return _rao_bell_segment(
        r_throat, r_exit, length, x,
        slope_start=np.tan(np.radians(theta_n)),
        slope_end=np.tan(np.radians(theta_e)),
    )


def _rao_bell_segment(
    r_start: float,
    r_end: float,
    length: float,
    x: np.ndarray,
    slope_start: float = 0.577,
    slope_end: float = 0.0,
) -> np.ndarray:
    """Compute bell contour segment with explicit start/end slopes.

    Cubic polynomial: y(x) = a*x^3 + b*x^2 + c*x + d
    matching radius and slope at both ends.

    Args:
        r_start: Radius at start of segment
        r_end: Radius at end of segment
        length: Axial length of segment
        x: Axial coordinates (local, starting from 0)
        slope_start: Wall slope at start
        slope_end: Wall slope at end

    Returns:
        Radial coordinates
    """
    L = max(length, 1e-12)
    c = slope_start
    d = r_start

    rhs1 = r_end - r_start - slope_start * L
    rhs2 = slope_end - slope_start

    det = L**3 * 2 * L - L**2 * 3 * L**2
    if abs(det) < 1e-20:
        # Degenerate: fall back to linear
        return r_start + (r_end - r_start) * x / L

    a = (rhs1 * 2 * L - L**2 * rhs2) / det
    b = (L**3 * rhs2 - 3 * L**2 * rhs1) / det

    return a * x**3 + b * x**2 + c * x + d


def _rao_bell_bezier(
    r_start: float,
    r_end: float,
    length: float,
    x: np.ndarray,
    slope_start: float = 0.577,
    slope_end: float = 0.0,
) -> np.ndarray:
    """Quadratic Bezier bell contour.

    P0 = (0, r_start), P2 = (length, r_end)
    Control point P1 from slope constraints.

    Uses Newton-Raphson to solve for parameter t from x coordinate,
    then evaluates the Bezier curve for y.

    Args:
        r_start: Radius at start of segment
        r_end: Radius at end of segment
        length: Axial length of segment
        x: Axial coordinates (local, starting from 0)
        slope_start: Wall slope at start
        slope_end: Wall slope at end

    Returns:
        Radial coordinates
    """
    if abs(length) < 1e-12:
        return np.full_like(x, r_start)

    # Control point from slope intersection
    # At P0: slope = slope_start -> line: y = r_start + slope_start * x
    # At P2: slope = slope_end -> line: y = r_end + slope_end * (x - length)
    # Intersection: r_start + slope_start * cx = r_end + slope_end * (cx - length)
    # cx * (slope_start - slope_end) = r_end - r_start - slope_end * length
    cx = (r_end - r_start - slope_end * length) / (slope_start - slope_end + 1e-20)
    cy = r_start + slope_start * cx

    # Quadratic Bezier: B(t) = (1-t)^2*P0 + 2*(1-t)*t*P1 + t^2*P2
    # Solve t from x using Newton-Raphson
    t = np.clip(x / length, 0, 1)
    for _ in range(10):
        x_bez = 2 * t * (1 - t) * cx + t**2 * length
        dx_dt = 2 * (1 - 2 * t) * cx + 2 * t * length
        dt = (x_bez - x) / np.where(np.abs(dx_dt) > 1e-12, dx_dt, 1e-12)
        t = np.clip(t - dt, 0, 1)
        if np.max(np.abs(dt)) < 1e-10:
            break

    y = (1 - t) ** 2 * r_start + 2 * (1 - t) * t * cy + t**2 * r_end
    return y


def plot_contour(
    x: np.ndarray,
    y: np.ndarray,
    title: str = "Nozzle Contour",
    config: NozzleConfig | None = None,
) -> None:
    """Plot the nozzle contour for debugging.

    Args:
        x: Axial coordinates (m)
        y: Radial coordinates (m)
        title: Plot title
        config: Optional NozzleConfig for chamber section annotation
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    ax.plot(x, y, 'b-', linewidth=2, label='Wall')
    ax.plot(x, -y, 'b-', linewidth=2)  # Mirror for axisymmetric
    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5, label='Axis')
    ax.set_xlabel('Axial Distance (m)')
    ax.set_ylabel('Radial Distance (m)')
    ax.set_title(title)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    # Annotate chamber section if config provided
    if config is not None and config.chamber_length > 0:
        ax.axvline(
            x=-config.converging_length,
            color='gray', linestyle=':', alpha=0.5,
            label='Chamber end',
        )

    ax.legend()
    plt.tight_layout()
    plt.savefig('docs/assets/images/nozzle_contour.png', dpi=150)
    plt.close()


def generate_plume_contour(
    config: NozzleConfig,
    plume_length_ratio: float = 20.0,
    plume_radius_ratio: float = 3.0,
    n_points: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate plume contour downstream of nozzle exit.

    Creates a constant-radius extension downstream of the nozzle exit plane.
    The plume radius equals plume_radius_ratio * exit_radius.

    Args:
        config: Nozzle geometry parameters
        plume_length_ratio: Plume length as multiple of throat radius
        plume_radius_ratio: Plume width as multiple of exit radius
        n_points: Number of contour points in plume

    Returns:
        x: axial coordinates (m), shape (n_points,)
        y: radial coordinates (m), shape (n_points,)
    """
    plume_length = plume_length_ratio * config.throat_radius
    x_exit = config.computed_diverging_length
    x = np.linspace(x_exit, x_exit + plume_length, n_points)
    y = np.full_like(x, config.exit_radius * plume_radius_ratio)
    return x, y
