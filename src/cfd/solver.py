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

    def run(self, config_path: Path, workdir: Path, timeout: int = 1800) -> SU2Results:
        """Execute SU2_CFD and return parsed results.

        Args:
            config_path: Path to SU2 .cfg config file
            workdir: Working directory for simulation
            timeout: Maximum runtime in seconds

        Returns:
            Parsed simulation results
        """
        workdir.mkdir(parents=True, exist_ok=True)

        cmd = [str(self.su2_cfd), str(config_path)]
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

            return self.parse_results(workdir)

        except subprocess.TimeoutExpired:
            logger.error(f"SU2 timed out after {timeout}s")
            return self.parse_results(workdir)
        except FileNotFoundError:
            logger.error(f"SU2 binary not found: {self.su2_cfd}")
            return SU2Results(converged=False)

    def parse_results(self, workdir: Path) -> SU2Results:
        """Parse history.csv and flow.vtu for exit conditions."""
        results = SU2Results()

        # Parse history.csv
        history_path = workdir / "history.csv"
        if history_path.exists():
            results.history = self._parse_history(history_path)
            if results.history:
                results.iterations = len(results.history)

                # Check convergence (residual drop)
                first_residual = float(results.history[0].get("RMS_DENSITY", 1.0))
                last_residual = float(results.history[-1].get("RMS_DENSITY", 1.0))
                results.residual_drop = first_residual - last_residual
                results.converged = results.residual_drop > 3.0  # 3 orders of magnitude

        # Parse flow.vtu for exit Mach
        vtu_path = workdir / "flow.vtu"
        if vtu_path.exists():
            results.exit_mach = self._extract_exit_mach(vtu_path)

        return results

    def _parse_history(self, history_path: Path) -> list[dict]:
        """Parse SU2 history.csv file."""
        history: list[dict] = []
        try:
            with open(history_path, 'r') as f:
                # Skip comment lines
                lines = [line for line in f if not line.startswith('"') and line.strip()]
                if lines:
                    reader = csv.DictReader(lines)
                    for row in reader:
                        history.append(row)
        except Exception as e:
            logger.warning(f"Failed to parse history: {e}")
        return history

    def _extract_exit_mach(self, vtu_path: Path) -> float:
        """Extract Mach number at exit plane from VTU file."""
        try:
            import numpy as np

            # Read VTU file as XML
            import xml.etree.ElementTree as ET
            tree = ET.parse(vtu_path)
            root = tree.getroot()

            # Find Points data
            for piece in root.iter('Piece'):
                point_data = piece.find('PointData')
                if point_data is None:
                    continue

                for data_array in point_data.findall('DataArray'):
                    if data_array.get('Name') == 'Mach':
                        mach_values = np.fromstring(
                            data_array.text,
                            sep=' '
                        )

                        # Get coordinates
                        points = piece.find('Points')
                        coords_array = points.find('DataArray')
                        coords = np.fromstring(coords_array.text, sep=' ').reshape(-1, 3)

                        # Find exit plane (maximum x coordinate)
                        max_x = coords[:, 0].max()
                        exit_mask = np.abs(coords[:, 0] - max_x) < 0.01

                        if exit_mask.any():
                            exit_mach = mach_values[exit_mask].mean()
                            return float(exit_mach)

            return 0.0

        except Exception as e:
            logger.warning(f"Failed to extract exit Mach: {e}")
            return 0.0
