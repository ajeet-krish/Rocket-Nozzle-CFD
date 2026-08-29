"""Rocket nozzle performance metrics: thrust coefficient, Isp, exit velocity."""
from __future__ import annotations

import math
from dataclasses import dataclass

from nozzle.config import NozzleConfig
from validation.isentropic import (
    area_mach_relation,
    total_to_static_pressure,
    total_to_static_temperature,
    choked_mass_flow_rate,
)

# Standard gravity (m/s^2)
G0 = 9.80665


@dataclass
class PerformanceMetrics:
    """Nozzle performance metrics computed from exit Mach number.

    Attributes:
        thrust_coefficient: CF = F / (p0 * A*) (dimensionless, typical 1.2-2.0)
        specific_impulse: Isp = F / (mdot * g0) (seconds, typical 200-460s)
        exit_velocity: Ve = Me * sqrt(gamma * R * Te) (m/s)
        exit_pressure: Static pressure at exit plane (Pa)
        exit_temperature: Static temperature at exit plane (K)
        mass_flow_rate: Choked mass flow rate (kg/s)
        thrust_force: Total thrust = mdot * Ve + (Pe - Pa) * Ae (N)
        characteristic_velocity: C* = p0 * A* / mdot (m/s)
    """

    thrust_coefficient: float
    specific_impulse: float
    exit_velocity: float
    exit_pressure: float
    exit_temperature: float
    mass_flow_rate: float
    thrust_force: float
    characteristic_velocity: float


def compute_performance(
    nozzle_config: NozzleConfig,
    total_pressure: float,
    total_temperature: float,
    exit_mach: float,
    gamma: float = 1.4,
    gas_constant: float = 287.058,
    ambient_pressure: float = 101325.0,
) -> PerformanceMetrics:
    """Compute nozzle performance metrics from exit Mach number.

    Uses isentropic relations to compute all performance parameters
    from the exit Mach number (from CFD or analytical solution).

    Args:
        nozzle_config: Nozzle geometry configuration
        total_pressure: Chamber total pressure (Pa)
        total_temperature: Chamber total temperature (K)
        exit_mach: Exit Mach number
        gamma: Ratio of specific heats
        gas_constant: Specific gas constant (J/(kg*K))
        ambient_pressure: Ambient pressure for thrust calculation (Pa)

    Returns:
        PerformanceMetrics with all computed values
    """
    # Areas
    throat_area = math.pi * nozzle_config.throat_radius**2
    exit_area = throat_area * nozzle_config.expansion_ratio

    # Exit conditions from isentropic relations
    p0_p = total_to_static_pressure(exit_mach, gamma)
    t0_t = total_to_static_temperature(exit_mach, gamma)

    exit_pressure = total_pressure / p0_p
    exit_temperature = total_temperature / t0_t

    # Exit velocity: Ve = Me * sqrt(gamma * R * Te)
    exit_velocity = exit_mach * math.sqrt(gamma * gas_constant * exit_temperature)

    # Mass flow rate (choked at throat)
    mass_flow_rate = choked_mass_flow_rate(
        throat_area, total_pressure, total_temperature, gamma, gas_constant
    )

    # Thrust: F = mdot * Ve + (Pe - Pa) * Ae
    thrust_force = (
        mass_flow_rate * exit_velocity
        + (exit_pressure - ambient_pressure) * exit_area
    )

    # Thrust coefficient: CF = F / (p0 * A*)
    thrust_coefficient = thrust_force / (total_pressure * throat_area)

    # Specific impulse: Isp = F / (mdot * g0)
    specific_impulse = thrust_force / (mass_flow_rate * G0)

    # Characteristic velocity: C* = p0 * A* / mdot
    characteristic_velocity = total_pressure * throat_area / mass_flow_rate

    return PerformanceMetrics(
        thrust_coefficient=thrust_coefficient,
        specific_impulse=specific_impulse,
        exit_velocity=exit_velocity,
        exit_pressure=exit_pressure,
        exit_temperature=exit_temperature,
        mass_flow_rate=mass_flow_rate,
        thrust_force=thrust_force,
        characteristic_velocity=characteristic_velocity,
    )
