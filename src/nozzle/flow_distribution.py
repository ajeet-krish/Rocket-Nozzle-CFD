"""Flow property distribution along nozzle contour."""
from dataclasses import dataclass
import numpy as np
from .config import NozzleConfig
from validation.isentropic import (
    area_mach_relation,
    mach_from_area_ratio,
    total_to_static_pressure,
    total_to_static_temperature,
    total_to_static_density,
)


@dataclass
class FlowField:
    """Flow properties along nozzle contour."""
    x: np.ndarray           # Axial coordinates (m)
    mach: np.ndarray        # Mach number
    pressure: np.ndarray    # Static pressure (Pa)
    temperature: np.ndarray # Static temperature (K)
    density: np.ndarray     # Density (kg/m3)
    velocity: np.ndarray    # Axial velocity (m/s)

    @property
    def exit_mach(self) -> float:
        """Exit Mach number."""
        return float(self.mach[-1])

    @property
    def exit_pressure(self) -> float:
        """Exit static pressure (Pa)."""
        return float(self.pressure[-1])


def compute_flow_distribution(
    config: NozzleConfig,
    total_pressure: float = 10e6,
    total_temperature: float = 3500.0,
    gamma: float = 1.4,
    gas_constant: float = 287.058,
) -> FlowField:
    """Compute flow properties along nozzle contour.

    Uses isentropic relations with local area ratio A(x)/A*.

    Args:
        config: Nozzle geometry parameters
        total_pressure: Chamber total pressure (Pa)
        total_temperature: Chamber total temperature (K)
        gamma: Ratio of specific heats
        gas_constant: Specific gas constant (J/(kg*K))

    Returns:
        FlowField with properties at each contour point
    """
    from .geometry import generate_contour

    x, y = generate_contour(config)

    # Local area ratio A(x)/A*
    # For axisymmetric: A = pi * y^2, A* = pi * R_throat^2
    area_ratio = (y / config.throat_radius) ** 2

    # Compute Mach from area ratio
    # Converging section (x <= 0): subsonic branch
    # Diverging section (x > 0): supersonic branch
    mach = np.zeros_like(x)
    for i, ar in enumerate(area_ratio):
        if x[i] <= 0:
            # Converging section: subsonic (M <= 1)
            mach[i] = mach_from_area_ratio(ar, gamma, supersonic=False)
        else:
            # Diverging section: supersonic (M >= 1)
            mach[i] = mach_from_area_ratio(ar, gamma, supersonic=True)

    # Compute other properties from Mach
    pressure_ratio = np.array([
        total_to_static_pressure(m, gamma) for m in mach
    ])
    temperature_ratio = np.array([
        total_to_static_temperature(m, gamma) for m in mach
    ])
    density_ratio = np.array([
        total_to_static_density(m, gamma) for m in mach
    ])

    pressure = total_pressure / pressure_ratio
    temperature = total_temperature / temperature_ratio
    # rho = rho0 / (rho0/rho), where rho0 = p0 / (R * T0)
    density = total_pressure / (gas_constant * total_temperature) / density_ratio

    # Velocity from Mach and local speed of sound
    speed_of_sound = np.sqrt(gamma * gas_constant * temperature)
    velocity = mach * speed_of_sound

    return FlowField(
        x=x,
        mach=mach,
        pressure=pressure,
        temperature=temperature,
        density=density,
        velocity=velocity,
    )
