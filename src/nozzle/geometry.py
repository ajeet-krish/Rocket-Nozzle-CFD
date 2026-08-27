"""Nozzle contour generation (conical and Rao bell)."""
import numpy as np
from .config import NozzleConfig


def generate_contour(config: NozzleConfig) -> tuple[np.ndarray, np.ndarray]:
    """Generate (x, y) contour points for a nozzle.

    Sections (if chamber_length > 0):
      1. Chamber: straight cylinder at chamber_radius
      2. Convergent: curved or linear transition to throat_radius
      3. Divergent: Rao parabolic bell from throat_radius to exit_radius

    If chamber_length == 0: skip chamber section (v1 behavior).
    If throat_radius_of_curvature == 0: use linear convergent (v1 behavior).

    Args:
        config: Nozzle geometry parameters

    Returns:
        x: axial coordinates (m), shape (num_points,)
        y: radial coordinates (m), shape (num_points,)
    """
    n = config.num_points

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

    # Section 2: Convergent
    x_converge = np.linspace(-config.converging_length, 0, n_converge)

    if config.throat_radius_of_curvature > 0:
        # Curved convergent using cubic polynomial with C1 continuity
        y_converge = _curved_convergent(
            config.effective_inlet_radius,
            config.throat_radius,
            config.convergent_half_angle,
            x_converge,
            config.converging_length,
        )
    else:
        # Linear convergent (v1 behavior)
        y_converge = np.linspace(config.effective_inlet_radius, config.throat_radius, n_converge)

    sections.append((x_converge, y_converge))

    # Section 3a: Exit arc (0.382*Rt radius, steep initial divergence)
    # Matches the Bell-Nozzle reference: circular arc from -90 deg to (theta_n - 90 deg)
    exit_arc_radius = 0.382 * config.throat_radius
    theta_n_rad = np.radians(config.theta_n)
    n_exit_arc = max(n_diverge // 5, 20)
    angle_start = -np.pi / 2  # -90 deg (vertical at throat)
    angle_end = theta_n_rad - np.pi / 2  # (theta_n - 90) deg
    angles = np.linspace(angle_start, angle_end, n_exit_arc)
    x_exit_arc = exit_arc_radius * np.cos(angles)
    y_exit_arc = exit_arc_radius * np.sin(angles) + exit_arc_radius + config.throat_radius

    # Section 3b: Bell (cubic polynomial from end of exit arc to exit)
    x_arc_end = x_exit_arc[-1]
    y_arc_end = y_exit_arc[-1]
    # Slope at end of exit arc: dy/dx = -cot(angle_end) = tan(theta_n)
    slope_arc_end = np.tan(theta_n_rad)
    nBell = n_diverge - n_exit_arc
    x_bell = np.linspace(x_arc_end, config.diverging_length, nBell)
    y_bell = _rao_bell_segment(
        y_arc_end, config.exit_radius,
        config.diverging_length - x_arc_end,
        x_bell - x_arc_end,
        slope_start=slope_arc_end,
        slope_end=np.tan(np.radians(config.theta_e)),
    )

    x_diverge = np.concatenate([x_exit_arc, x_bell])
    y_diverge = np.concatenate([y_exit_arc, y_bell])
    sections.append((x_diverge, y_diverge))

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
    x_exit = config.diverging_length
    x = np.linspace(x_exit, x_exit + plume_length, n_points)
    y = np.full_like(x, config.exit_radius * plume_radius_ratio)
    return x, y
