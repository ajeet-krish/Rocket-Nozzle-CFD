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

        Uses the VTU parser to handle both ASCII and binary formats.

        Args:
            vtu_path: Path to SU2 flow.vtu file
            gamma: Ratio of specific heats (default 1.4 for air)

        Returns:
            Area-averaged Mach number at the exit plane, or 0.0 on failure
        """
        try:
            import numpy as np
            from .vtu_parser import parse_vtu
            
            data = parse_vtu(vtu_path)
            
            if data.mach is None:
                return 0.0
            
            # Find exit plane: look for the throat location (minimum y)
            # and take the point just downstream where Mach > 1
            coords = data.coordinates
            mach = data.mach
            
            # Strategy: find the node with maximum Mach (supersonic core)
            # This works for both plume and no-plume cases
            max_mach_idx = np.argmax(mach)
            max_mach_x = coords[max_mach_idx, 0]
            
            # Take nodes within 0.05m of the max Mach location
            exit_mask = np.abs(coords[:, 0] - max_mach_x) < 0.05
            
            if exit_mask.any():
                return float(mach[exit_mask].mean())
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Failed to extract exit Mach: {e}")
            return 0.0
