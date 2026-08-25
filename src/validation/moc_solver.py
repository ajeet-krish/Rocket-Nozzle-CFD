"""1D nozzle flow solver for supersonic nozzle validation."""
import numpy as np
from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour
from .isentropic import mach_from_area_ratio, prandtl_meyer
from .moc_config import MoCConfig, MoCResults


class MoCSolver:
    """1D nozzle flow solver using isentropic area-Mach relations.

    This solver computes supersonic flow properties along a nozzle contour
    using isentropic relations. It provides a 1D approximation suitable for
    validation of CFD results.

    Note: This is a simplified 1D approximation for validation purposes.
    For true 2D MoC, characteristic lines and Riemann invariants would be used.
    """

    def __init__(self, config: MoCConfig | None = None):
        """Initialize MoC solver.

        Args:
            config: Solver configuration. Uses defaults if None.
        """
        self.config = config or MoCConfig()

    def solve(self, nozzle_config: NozzleConfig) -> MoCResults:
        """Run solver on nozzle contour.

        Computes Mach number, flow angle, and Prandtl-Meyer angle
        along the nozzle wall using isentropic area-Mach relations.

        Args:
            nozzle_config: Nozzle geometry parameters

        Returns:
            MoCResults with flow properties along nozzle
        """
        # Generate nozzle contour
        x_wall, y_wall = generate_contour(nozzle_config)

        # Initialize results arrays
        n = len(x_wall)
        mach = np.ones(n)
        theta = np.zeros(n)
        nu = np.zeros(n)

        # Find throat index (closest to x=0)
        throat_idx = int(np.argmin(np.abs(x_wall)))

        # For converging section (subsonic), compute Mach from area ratio
        for i in range(throat_idx):
            area_ratio = (y_wall[i] / nozzle_config.throat_radius) ** 2
            if area_ratio >= 1.0:
                mach[i] = mach_from_area_ratio(
                    area_ratio, self.config.gamma, supersonic=False
                )
            else:
                mach[i] = 1.0
            nu[i] = prandtl_meyer(mach[i], self.config.gamma)

        # At throat, Mach = 1
        mach[throat_idx] = 1.0
        nu[throat_idx] = 0.0

        # For diverging section (supersonic), compute Mach from area ratio
        for i in range(throat_idx + 1, n):
            area_ratio = (y_wall[i] / nozzle_config.throat_radius) ** 2
            mach[i] = mach_from_area_ratio(
                area_ratio, self.config.gamma, supersonic=True
            )
            nu[i] = prandtl_meyer(mach[i], self.config.gamma)

        # Compute wall angle from contour slope
        for i in range(n - 1):
            dx = x_wall[i + 1] - x_wall[i]
            dy = y_wall[i + 1] - y_wall[i]
            theta[i] = np.arctan2(dy, dx)
        # Use backward difference for last point
        theta[-1] = theta[-2]

        return MoCResults(
            x=x_wall,
            mach=mach,
            theta=theta,
            nu=nu,
        )
