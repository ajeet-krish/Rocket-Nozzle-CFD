"""Isentropic flow relations."""
import math
from scipy.optimize import brentq


def area_mach_relation(M: float, gamma: float = 1.4) -> float:
    """Compute A/A* from Mach number (isentropic).

    Args:
        M: Mach number
        gamma: Ratio of specific heats

    Returns:
        Area ratio A/A*
    """
    if M <= 0:
        return float('inf')

    term1 = 1.0 / M
    term2 = (2.0 / (gamma + 1.0)) * (1.0 + (gamma - 1.0) / 2.0 * M**2)
    exponent = (gamma + 1.0) / (2.0 * (gamma - 1.0))

    return term1 * term2**exponent


def exit_mach_from_area_ratio(epsilon: float, gamma: float = 1.4) -> float:
    """Solve for exit Mach given area ratio A/A* (supersonic branch).

    Args:
        epsilon: Area ratio A_exit/A_throat
        gamma: Ratio of specific heats

    Returns:
        Mach number (supersonic solution)
    """
    # Define the equation to solve: A/A*(M) - epsilon = 0
    def equation(M: float) -> float:
        return area_mach_relation(M, gamma) - epsilon

    # Solve for supersonic branch (M > 1)
    # A/A* increases monotonically for M > 1
    try:
        M_exit = brentq(equation, 1.0, 10.0)
        return M_exit
    except ValueError:
        # Fallback: return approximate solution
        return math.sqrt(2.0 / (gamma - 1.0) * ((epsilon * (gamma + 1.0) / 2.0)**(2.0 * (gamma - 1.0) / (gamma + 1.0)) - 1.0))


def total_to_static_pressure(M: float, gamma: float = 1.4) -> float:
    """Compute p0/p from Mach number.

    Args:
        M: Mach number
        gamma: Ratio of specific heats

    Returns:
        Pressure ratio p0/p
    """
    return (1.0 + (gamma - 1.0) / 2.0 * M**2)**(gamma / (gamma - 1.0))


def total_to_static_temperature(M: float, gamma: float = 1.4) -> float:
    """Compute T0/T from Mach number.

    Args:
        M: Mach number
        gamma: Ratio of specific heats

    Returns:
        Temperature ratio T0/T
    """
    return 1.0 + (gamma - 1.0) / 2.0 * M**2


def choked_mass_flow_rate(
    throat_area: float,
    total_pressure: float,
    total_temperature: float,
    gamma: float = 1.4,
    gas_constant: float = 287.058,
) -> float:
    """Compute choked mass flow rate.

    Args:
        throat_area: Throat cross-sectional area (m^2)
        total_pressure: Total (stagnation) pressure (Pa)
        total_temperature: Total (stagnation) temperature (K)
        gamma: Ratio of specific heats
        gas_constant: Specific gas constant (J/(kg*K))

    Returns:
        Mass flow rate (kg/s)
    """
    return (throat_area * total_pressure / math.sqrt(total_temperature) *
            math.sqrt(gamma / gas_constant) *
            ((gamma + 1.0) / 2.0)**(-(gamma + 1.0) / (2.0 * (gamma - 1.0))))


def thrust_coefficient(
    exit_mach: float,
    exit_pressure: float,
    chamber_pressure: float,
    throat_area: float,
    gamma: float = 1.4,
) -> float:
    """Compute thrust coefficient.

    Args:
        exit_mach: Exit Mach number
        exit_pressure: Exit static pressure (Pa)
        chamber_pressure: Chamber (total) pressure (Pa)
        throat_area: Throat cross-sectional area (m^2)
        gamma: Ratio of specific heats

    Returns:
        Thrust coefficient (dimensionless)
    """
    # For perfectly expanded nozzle (p_exit = p_ambient)
    # Cf = (rho_e * v_e^2) / (p_0 * A*)

    # Exit velocity
    v_exit = exit_mach * math.sqrt(gamma * 287.058 * 3500.0 / (1.0 + (gamma - 1.0) / 2.0 * exit_mach**2))

    # Exit density
    rho_exit = chamber_pressure / (287.058 * 3500.0) * (1.0 + (gamma - 1.0) / 2.0 * exit_mach**2)**(-1.0 / (gamma - 1.0))

    # Thrust force
    thrust = rho_exit * v_exit**2 * math.pi * (0.05 * math.sqrt(12.0))**2

    # Reference force
    ref_force = chamber_pressure * throat_area

    return thrust / ref_force
