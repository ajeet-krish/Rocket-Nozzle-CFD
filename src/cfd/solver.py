"""SU2 solver interface."""
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import csv
import logging

from .config import SU2NozzleConfig, get_su2_binary

logger = logging.getLogger(__name__)


@dataclass
class SU2Results:
    """Parsed results from SU2 simulation."""
    exit_mach: float = 0.0
    exit_pressure: float = 0.0
    converged: bool = False
    iterations: int = 0
    residual_drop: float = 0.0
    history: list[dict] = field(default_factory=list)


class SU2Solver:
    """Run SU2_CFD and parse results."""

    def __init__(self, su2_cfd: Path | None = None):
        self.su2_cfd = su2_cfd or get_su2_binary()

    def run(
        self,
        config_path: Path,
        workdir: Path,
        timeout: int = 1800,
        gamma: float = 1.4,
    ) -> SU2Results:
        """Execute SU2_CFD and return parsed results.

        Args:
            config_path: Path to SU2 .cfg config file
            workdir: Working directory for simulation
            timeout: Maximum runtime in seconds
            gamma: Ratio of specific heats (default 1.4 for air)

        Returns:
            Parsed simulation results
        """
        workdir.mkdir(parents=True, exist_ok=True)

        # SU2 expects config file relative to working directory
        # If config_path is absolute and in workdir, pass just the filename
        config_name = Path(config_path).name
        cmd = [str(self.su2_cfd), config_name]
        logger.info(f"Running SU2: {' '.join(cmd)}")
        logger.info(f"Working directory: {workdir}")

        try:
            result = subprocess.run(
                cmd,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.error(f"SU2 failed with return code {result.returncode}")
                logger.error(f"stderr: {result.stderr}")
                return SU2Results(converged=False)

            return self.parse_results(workdir, gamma=gamma)

        except subprocess.TimeoutExpired:
            logger.error(f"SU2 timed out after {timeout}s")
            return self.parse_results(workdir, gamma=gamma)
        except FileNotFoundError:
            logger.error(f"SU2 binary not found: {self.su2_cfd}")
            return SU2Results(converged=False)

    def parse_results(self, workdir: Path, gamma: float = 1.4) -> SU2Results:
        """Parse history.csv and flow.vtu for exit conditions.

        Args:
            workdir: Directory containing SU2 output files
            gamma: Ratio of specific heats (default 1.4 for air)
        """
        results = SU2Results()

        # Parse history.csv
        history_path = workdir / "history.csv"
        if history_path.exists():
            results.history = self._parse_history(history_path)
            if results.history:
                results.iterations = len(results.history)

                # Check convergence (residual drop)
                # SU2 history.csv uses "rms[Rho]" as the column name
                first_residual = float(results.history[0].get("rms[Rho]", 1.0))
                last_residual = float(results.history[-1].get("rms[Rho]", 1.0))
                results.residual_drop = first_residual - last_residual
                results.converged = results.residual_drop > 3.0  # 3 orders of magnitude

        # Parse flow.vtu for exit Mach
        vtu_path = workdir / "flow.vtu"
        if vtu_path.exists():
            results.exit_mach = self._extract_exit_mach(vtu_path, gamma=gamma)

        return results

    def _parse_history(self, history_path: Path) -> list[dict]:
        """Parse SU2 history.csv file."""
        history: list[dict] = []
        try:
            with open(history_path, 'r') as f:
                lines = f.readlines()
            
            if not lines:
                return history
            
            # SU2 history.csv format:
            # Line 1: Header line with quoted column names
            # Line 2+: Data rows
            
            # Parse header (first line)
            header_line = lines[0].strip()
            # Remove quotes and split by comma
            header = [h.strip().strip('"') for h in header_line.split(',')]
            
            # Parse data rows
            for line in lines[1:]:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                values = [v.strip() for v in line_stripped.split(',')]
                if len(values) == len(header):
                    row = dict(zip(header, values))
                    history.append(row)
                    
        except Exception as e:
            logger.warning(f"Failed to parse history: {e}")
        return history

    def _extract_exit_mach(self, vtu_path: Path, gamma: float = 1.4) -> float:
        """Extract Mach number at exit plane from VTU file.

        Tries to read Mach directly from PointData. Falls back to computing
        Mach from conservative variables (Density, Momentum_x, Momentum_y,
        Energy) when a Mach field is not present.

        Args:
            vtu_path: Path to SU2 flow.vtu file
            gamma: Ratio of specific heats (default 1.4 for air)

        Returns:
            Area-averaged Mach number at the exit plane, or 0.0 on failure
        """
        try:
            import numpy as np
            import xml.etree.ElementTree as ET

            tree = ET.parse(vtu_path)
            root = tree.getroot()

            for piece in root.iter('Piece'):
                point_data = piece.find('PointData')
                if point_data is None:
                    continue

                # Try to find Mach field directly
                for data_array in point_data.findall('DataArray'):
                    if data_array.get('Name') == 'Mach':
                        mach_values = np.fromstring(data_array.text, sep=' ')

                        # Get coordinates
                        points = piece.find('Points')
                        coords_array = points.find('DataArray')
                        coords = np.fromstring(
                            coords_array.text, sep=' '
                        ).reshape(-1, 3)

                        # Find exit plane (maximum x coordinate)
                        max_x = coords[:, 0].max()
                        exit_mask = np.abs(coords[:, 0] - max_x) < 0.01

                        if exit_mask.any():
                            return float(mach_values[exit_mask].mean())

                # Fallback: compute Mach from conservative variables
                conservative: dict[str, np.ndarray] = {}
                for data_array in point_data.findall('DataArray'):
                    name = data_array.get('Name')
                    if name in ['Density', 'Momentum_x', 'Momentum_y', 'Energy']:
                        conservative[name] = np.fromstring(
                            data_array.text, sep=' '
                        )

                if len(conservative) == 4:
                    rho = conservative['Density']
                    mom_x = conservative['Momentum_x']
                    mom_y = conservative['Momentum_y']
                    energy = conservative['Energy']

                    # Velocity components
                    u = mom_x / rho
                    v = mom_y / rho

                    # Pressure (ideal gas)
                    p = (gamma - 1.0) * (energy - 0.5 * rho * (u**2 + v**2))

                    # Speed of sound
                    c = np.sqrt(gamma * p / rho)

                    # Mach
                    mach = np.abs(np.sqrt(u**2 + v**2)) / c

                    # Get coordinates
                    points = piece.find('Points')
                    coords_array = points.find('DataArray')
                    coords = np.fromstring(
                        coords_array.text, sep=' '
                    ).reshape(-1, 3)

                    max_x = coords[:, 0].max()
                    exit_mask = np.abs(coords[:, 0] - max_x) < 0.01

                    if exit_mask.any():
                        return float(mach[exit_mask].mean())

            return 0.0

        except Exception as e:
            logger.warning(f"Failed to extract exit Mach: {e}")
            return 0.0
