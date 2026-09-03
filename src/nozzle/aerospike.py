"""Aerospike (plug nozzle) geometry generation.

Axisymmetric aerospike nozzle adapted from NASA X-33 concept.
The flow expands over a central spike (plug) rather than inside a bell.

Geometry:
    - Spike: axisymmetric body with bell-shaped or conical contour
    - Annular throat: gap between spike base and outer casing
    - Plug truncation: spike truncated at ~80% length with base BC
    - Outer wall: cylindrical casing guiding flow to annular throat

Boundary conditions (SU2):
    - Inlet: annular inlet at upstream end of casing
    - Wall: spike surface + outer casing
    - Outlet: atmospheric pressure at domain boundaries
    - Symmetry: axis (y=0)
"""
import numpy as np
from dataclasses import dataclass
from .config import NozzleConfig


@dataclass
class AerospikeConfig:
    """Aerospike nozzle geometry parameters.

    Attributes:
        throat_radius: Annular throat inner radius (spike base) (m)
        expansion_ratio: Area ratio A_exit / A_throat
        spike_length: Axial length of spike (m)
        truncation_ratio: Fraction of spike length to keep (0.8 = 80% truncated)
        spike_theta_n: Wall angle at throat for spike contour (degrees)
        spike_theta_e: Exit wall angle (degrees)
        casing_length: Length of outer casing upstream of throat (m)
        casing_gap: Radial gap at throat (m) - outer_radius - throat_radius
        num_points: Number of contour points
    """
    throat_radius: float = 0.0825       # m (inner radius at throat)
    expansion_ratio: float = 49.0       # A_exit / A_throat
    spike_length: float = 1.62          # m (full spike length)
    truncation_ratio: float = 0.80      # keep 80% of spike
    spike_theta_n: float = 25.0         # degrees
    spike_theta_e: float = 0.0          # degrees (0 = parallel to axis)
    casing_length: float = 0.30         # m
    casing_gap: float = 0.04            # m (radial gap at throat)
    num_points: int = 300

    @property
    def outer_throat_radius(self) -> float:
        """Outer radius at annular throat."""
        return self.throat_radius + self.casing_gap

    @property
    def exit_radius(self) -> float:
        """Effective exit radius (from expansion ratio)."""
        return self.throat_radius * (self.expansion_ratio ** 0.5)

    @property
    def spike_truncated_length(self) -> float:
        """Truncated spike length."""
        return self.spike_length * self.truncation_ratio

    @property
    def spike_base_radius(self) -> float:
        """Radius at the truncated base of the spike.

        Computed from the actual Bezier contour, not linear interpolation.
        """
        theta_n_rad = np.radians(self.spike_theta_n)
        theta_e_rad = np.radians(self.spike_theta_e)
        r_start = self.throat_radius
        r_end = self.exit_radius
        length = self.spike_length

        # Bezier control point
        slope_start = np.tan(theta_n_rad)
        slope_end = np.tan(theta_e_rad)
        cx = (r_end - r_start - slope_end * length) / (slope_start - slope_end + 1e-20)
        cy = r_start + slope_start * cx

        # Solve for t at truncation x
        x_trunc = self.spike_truncated_length
        t = np.clip(x_trunc / length, 0, 1)
        for _ in range(10):
            x_bez = 2 * t * (1 - t) * cx + t**2 * length
            dx_dt = 2 * (1 - 2 * t) * cx + 2 * t * length
            dt = (x_bez - x_trunc) / (dx_dt if abs(dx_dt) > 1e-12 else 1e-12)
            t = np.clip(t - dt, 0, 1)
            if abs(dt) < 1e-10:
                break

        return float((1 - t) ** 2 * r_start + 2 * (1 - t) * t * cy + t**2 * r_end)


def generate_aerospike_contour(
    config: AerospikeConfig,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Generate aerospike nozzle contour sections.

    Returns a dictionary with:
        - 'spike': Spike surface contour (x, y)
        - 'casing_outer': Outer casing wall (x, y)
        - 'casing_inner': Inner casing wall / inlet (x, y)
        - 'inlet_top': Inlet top boundary (x, y)
        - 'inlet_bottom': Inlet bottom boundary (x, y)

    Coordinate system:
        - x: axial (0 = throat, positive downstream)
        - y: radial (0 = axis, positive outward)
    """
    n = config.num_points

    # --- Spike contour (bell-shaped) ---
    # The spike starts at x=0 (throat) with radius = throat_radius
    # and expands to exit_radius at x = spike_length
    # Using a parabolic (bell) profile similar to Rao bell

    n_spike = n
    x_spike = np.linspace(0, config.spike_length, n_spike)

    # Bell profile: P0=(0, r_throat), P2=(L, r_exit)
    # Control point from slope constraints
    theta_n_rad = np.radians(config.spike_theta_n)
    theta_e_rad = np.radians(config.spike_theta_e)

    r_start = config.throat_radius
    r_end = config.exit_radius
    length = config.spike_length

    # Quadratic Bezier control point
    slope_start = np.tan(theta_n_rad)
    slope_end = np.tan(theta_e_rad)
    cx = (r_end - r_start - slope_end * length) / (slope_start - slope_end + 1e-20)
    cy = r_start + slope_start * cx

    # Solve for parameter t from x using Newton-Raphson
    t = np.clip(x_spike / length, 0, 1)
    for _ in range(10):
        x_bez = 2 * t * (1 - t) * cx + t**2 * length
        dx_dt = 2 * (1 - 2 * t) * cx + 2 * t * length
        dt = (x_bez - x_spike) / np.where(np.abs(dx_dt) > 1e-12, dx_dt, 1e-12)
        t = np.clip(t - dt, 0, 1)
        if np.max(np.abs(dt)) < 1e-10:
            break

    y_spike = (1 - t) ** 2 * r_start + 2 * (1 - t) * t * cy + t**2 * r_end

    # Truncate the spike at the exact truncation length
    x_trunc = config.spike_truncated_length
    if x_trunc < config.spike_length:
        # Interpolate to get exact y at truncation point
        trunc_idx = np.searchsorted(x_spike, x_trunc)
        if trunc_idx > 0 and trunc_idx < len(x_spike):
            # Linear interpolation between adjacent points
            frac = (x_trunc - x_spike[trunc_idx - 1]) / (x_spike[trunc_idx] - x_spike[trunc_idx - 1] + 1e-20)
            y_trunc = y_spike[trunc_idx - 1] + frac * (y_spike[trunc_idx] - y_spike[trunc_idx - 1])
            x_spike = np.concatenate([x_spike[:trunc_idx], [x_trunc]])
            y_spike = np.concatenate([y_spike[:trunc_idx], [y_trunc]])
        elif trunc_idx == 0:
            x_spike = np.array([x_trunc])
            y_spike = np.array([config.throat_radius])

    # Force exact endpoint match with truncated spike dimensions
    x_spike[-1] = x_trunc
    y_spike[-1] = config.spike_base_radius

    # --- Outer casing ---
    # Cylindrical casing from x = -casing_length to x = 0
    # at radius = outer_throat_radius
    x_casing = np.array([-config.casing_length, 0.0])
    y_casing = np.array([config.outer_throat_radius, config.outer_throat_radius])

    # --- Inlet boundaries ---
    # Inlet top: from casing inlet to spike base
    x_inlet_top = np.array([-config.casing_length, -config.casing_length])
    y_inlet_top = np.array([config.throat_radius, config.outer_throat_radius])

    # Inlet bottom: at the spike base (x=0)
    x_inlet_bottom = np.array([0.0, 0.0])
    y_inlet_bottom = np.array([config.throat_radius, config.outer_throat_radius])

    return {
        'spike': (x_spike, y_spike),
        'casing_outer': (x_casing, y_casing),
        'inlet_top': (x_inlet_top, y_inlet_top),
        'inlet_bottom': (x_inlet_bottom, y_inlet_bottom),
    }


def plot_aerospike_contour(
    config: AerospikeConfig,
    output_path: str = "aerospike_contour.png",
    title: str = "Aerospike Nozzle Geometry",
) -> None:
    """Plot the aerospike nozzle contour for debugging.

    Args:
        config: Aerospike geometry parameters
        output_path: Path to save plot
        title: Plot title
    """
    import matplotlib.pyplot as plt

    sections = generate_aerospike_contour(config)

    fig, ax = plt.subplots(1, 1, figsize=(12, 5))

    # Spike surface
    x_sp, y_sp = sections['spike']
    ax.plot(x_sp, y_sp, 'b-', linewidth=2.5, label='Spike (plug)')
    ax.plot(x_sp, -y_sp, 'b-', linewidth=1, alpha=0.3)

    # Outer casing
    x_c, y_c = sections['casing_outer']
    ax.plot(x_c, y_c, 'r-', linewidth=2.5, label='Outer casing')
    ax.plot(x_c, -y_c, 'r-', linewidth=1, alpha=0.3)

    # Inlet
    x_it, y_it = sections['inlet_top']
    ax.plot(x_it, y_it, 'g-', linewidth=2, label='Inlet')

    # Axis
    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5, label='Axis')

    # Truncation line
    x_trunc = config.spike_truncated_length
    y_trunc = config.spike_base_radius
    ax.axvline(x=x_trunc, color='gray', linestyle=':', alpha=0.5)
    ax.annotate(f'Truncated\n({config.truncation_ratio*100:.0f}%)',
                xy=(x_trunc, y_trunc), fontsize=9, ha='center',
                color='gray')

    # Annotations
    ax.annotate(f'Throat\nR={config.throat_radius*1000:.1f}mm',
                xy=(0, config.throat_radius), xytext=(0.3, config.throat_radius * 0.5),
                arrowprops=dict(arrowstyle='->', color='black'),
                fontsize=9, ha='center')
    ax.annotate(f'Exit\nR={config.exit_radius*1000:.1f}mm',
                xy=(x_sp[-1], y_sp[-1]), xytext=(x_sp[-1]*0.8, y_sp[-1]*1.3),
                arrowprops=dict(arrowstyle='->', color='black'),
                fontsize=9, ha='center')
    ax.annotate(f'ε={config.expansion_ratio:.0f}:1',
                xy=(x_sp[-1]/2, (config.throat_radius + y_sp[-1])/2),
                fontsize=12, ha='center', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))

    ax.set_xlabel('Axial Distance (m)', fontsize=12)
    ax.set_ylabel('Radial Distance (m)', fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
