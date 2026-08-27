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

    # Section 3: Divergent (Rao bell)
    x_diverge = np.linspace(0, config.diverging_length, n_diverge)
    y_diverge = _rao_bell(
        config.throat_radius,
        config.exit_radius,
        config.diverging_length,
        x_diverge,
        theta_n=config.theta_n,
        theta_e=config.theta_e,
    )
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

    This avoids Bezier parameterisation issues when the control point
    falls outside the nozzle length.

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
    t_n = np.tan(np.radians(theta_n))
    t_e = np.tan(np.radians(theta_e))

    # Cubic: y(x) = a*x^3 + b*x^2 + c*x + d
    # y(0) = r_throat           -> d = r_throat
    # y'(0) = t_n               -> c = t_n
    # y(L) = r_exit             -> a*L^3 + b*L^2 + t_n*L + r_throat = r_exit
    # y'(L) = t_e               -> 3*a*L^2 + 2*b*L + t_n = t_e

    L = length
    d = r_throat
    c = t_n

    # Solve 2x2 system for a, b:
    # a*L^3 + b*L^2 = r_exit - r_throat - t_n*L
    # 3*a*L^2 + 2*b*L = t_e - t_n
    rhs1 = r_exit - r_throat - t_n * L
    rhs2 = t_e - t_n

    det = L**3 * 2 * L - L**2 * 3 * L**2
    a = (rhs1 * 2 * L - L**2 * rhs2) / det
    b = (L**3 * rhs2 - 3 * L**2 * rhs1) / det

    y = a * x**3 + b * x**2 + c * x + d

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
    x_exit = config.diverging_length
    x = np.linspace(x_exit, x_exit + plume_length, n_points)
    y = np.full_like(x, config.exit_radius * plume_radius_ratio)
    return x, y
