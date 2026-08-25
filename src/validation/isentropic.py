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
    gas_constant: float = 287.058,
    total_temperature: float = 3500.0,
) -> float:
    """Compute thrust coefficient.

    Args:
        exit_mach: Exit Mach number
        exit_pressure: Exit static pressure (Pa)
        chamber_pressure: Chamber (total) pressure (Pa)
        throat_area: Throat cross-sectional area (m^2)
        gamma: Ratio of specific heats
        gas_constant: Specific gas constant (J/(kg*K))
        total_temperature: Total temperature (K)

    Returns:
        Thrust coefficient (dimensionless)
    """
    # Exit velocity
    v_exit = exit_mach * math.sqrt(
        gamma * gas_constant * total_temperature /
        (1.0 + (gamma - 1.0) / 2.0 * exit_mach**2)
    )

    # Exit density
    rho_exit = chamber_pressure / (gas_constant * total_temperature) * (
        1.0 + (gamma - 1.0) / 2.0 * exit_mach**2
    )**(-1.0 / (gamma - 1.0))

    # Exit area from throat area and exit Mach
    exit_area = throat_area * area_mach_relation(exit_mach, gamma)

    # Thrust force
    thrust = rho_exit * v_exit**2 * exit_area

    # Reference force
    ref_force = chamber_pressure * throat_area

    return thrust / ref_force


def total_to_static_density(M: float, gamma: float = 1.4) -> float:
    """Compute rho0/rho from Mach number.

    Args:
        M: Mach number
        gamma: Ratio of specific heats

    Returns:
        Density ratio rho0/rho
    """
    return (1.0 + (gamma - 1.0) / 2.0 * M**2) ** (1.0 / (gamma - 1.0))


def mach_from_area_ratio(
    area_ratio: float,
    gamma: float = 1.4,
    supersonic: bool = True,
) -> float:
    """Solve for Mach number given area ratio A/A*.

    Args:
        area_ratio: Area ratio A/A*
        gamma: Ratio of specific heats
        supersonic: If True, return supersonic branch; else subsonic

    Returns:
        Mach number
    """
    if area_ratio < 1.0:
        raise ValueError("Area ratio must be >= 1.0")

    if area_ratio == 1.0:
        return 1.0

    # Define the equation to solve: A/A*(M) - area_ratio = 0
    def equation(M: float) -> float:
        return area_mach_relation(M, gamma) - area_ratio

    # Solve for appropriate branch
    try:
        if supersonic:
            M = brentq(equation, 1.0, 10.0)
        else:
            M = brentq(equation, 0.01, 1.0)
        return M
    except ValueError:
        # Fallback: approximate solution
        if supersonic:
            inner = (area_ratio * (gamma + 1.0) / 2.0) ** (
                2.0 * (gamma - 1.0) / (gamma + 1.0)
            ) - 1.0
            if inner < 0:
                raise ValueError(
                    f"Cannot compute Mach for area_ratio={area_ratio}"
                )
            return math.sqrt(2.0 / (gamma - 1.0) * inner)
        else:
            return 1.0 / area_ratio  # Approximate for low Mach


def prandtl_meyer(mach: float, gamma: float = 1.4) -> float:
    """Compute Prandtl-Meyer angle from Mach number.

    The Prandtl-Meyer function relates Mach number to the maximum
    turning angle for isentropic supersonic expansion.

    Args:
        mach: Mach number
        gamma: Ratio of specific heats

    Returns:
        Prandtl-Meyer angle (radians)
    """
    if mach <= 1.0:
        return 0.0

    term1 = math.sqrt((gamma + 1) / (gamma - 1))
    term2 = math.atan(math.sqrt((gamma - 1) / (gamma + 1) * (mach**2 - 1)))
    term3 = math.atan(math.sqrt(mach**2 - 1))

    return term1 * term2 - term3


def mach_from_prandtl_meyer(nu: float, gamma: float = 1.4) -> float:
    """Compute Mach number from Prandtl-Meyer angle (inverse).

    Uses Newton-Raphson iteration to solve for Mach number given
    a Prandtl-Meyer angle.

    Args:
        nu: Prandtl-Meyer angle (radians)
        gamma: Ratio of specific heats

    Returns:
        Mach number
    """
    if nu <= 0:
        return 1.0

    # Newton-Raphson iteration
    mach = 2.0  # Initial guess
    for _ in range(50):
        nu_calc = prandtl_meyer(mach, gamma)
        dnu_dmach = (
            math.sqrt(mach**2 - 1)
            / (mach * (1 + (gamma - 1) / 2 * mach**2))
        )
        if abs(dnu_dmach) < 1e-12:
            break
        mach = mach - (nu_calc - nu) / dnu_dmach
        mach = max(mach, 1.001)

    return mach
