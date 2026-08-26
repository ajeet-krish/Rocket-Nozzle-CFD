"""SU2 configuration for nozzle simulation."""
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class SU2NozzleConfig:
    """SU2 configuration for axisymmetric Euler nozzle simulation."""
    # Solver
    solver: str = "EULER"
    axisymmetric: bool = True

    # Inlet (chamber conditions)
    total_pressure: float = 10e6        # Pa (10 MPa)
    total_temperature: float = 3500.0   # K
    inlet_marker: str = "inlet"

    # Outlet
    static_pressure: float = 101325.0   # Pa (1 atm)
    outlet_marker: str = "outlet"

    # Wall
    wall_marker: str = "wall"

    # Axis
    symmetry_marker: str = "symmetry"

    # Farfield (plume domain)
    farfield_marker: str = ""

    # Numerics
    cfl_number: float = 5.0
    iterations: int = 5000
    conv_residual_minval: float = -6.0

    # Gas properties (air)
    gamma: float = 1.4
    gas_constant: float = 287.058       # J/(kg*K)

    # Output
    volume_filename: str = "flow"
    history_filename: str = "history.csv"
    mesh_filename: str = "nozzle.su2"

    def write(self, path: Path, mesh_filename: str | None = None) -> Path:
        """Generate SU2 .cfg file.

        Args:
            path: Directory to write config file
            mesh_filename: Override mesh filename

        Returns:
            Path to written config file
        """
        mesh = mesh_filename or self.mesh_filename

        config_content = f"""% ------- Rocket Nozzle CFD - Phase 0 Reference Case --------
% Converging-diverging nozzle, Euler, axisymmetric
% Chamber: 10 MPa, 3500K (air)
% Exit: 1 atm

SOLVER= EULER
MATH_PROBLEM= DIRECT
RESTART_SOL= NO
AXISYMMETRIC= YES

% -------------------- GAS PROPERTIES ------------------------
GAMMA_VALUE= {self.gamma}
GAS_CONSTANT= {self.gas_constant}
SYSTEM_MEASUREMENTS= SI

% -------------------- BOUNDARY CONDITIONS -------------------
MARKER_EULER= ( {self.wall_marker} )
MARKER_SYM= ( {self.symmetry_marker} )

% Inlet: subsonic inlet with total conditions (Tt, Pt, Vx, Vy, Vz)
MARKER_INLET= ( {self.inlet_marker}, {self.total_temperature:.1f}, {self.total_pressure:.1f}, 1.0, 0.0, 0.0 )

% Outlet: static pressure
MARKER_OUTLET= ( {self.outlet_marker}, {self.static_pressure:.1f} )

{f'''% Farfield: characteristic-based non-reflecting BC (plume domain)
MARKER_FAR= ( {self.farfield_marker} )
''' if self.farfield_marker else ''}% -------------------- NUMERICAL METHOD -----------------------
CONV_NUM_METHOD_FLOW= ROE
MUSCL_FLOW= NO
TIME_DISCRE_FLOW= EULER_IMPLICIT

% -------------------- CONVERGENCE ----------------------------
ITER= {self.iterations}
CFL_NUMBER= {self.cfl_number}
CFL_ADAPT= YES
CFL_ADAPT_PARAM= ( 0.1, 1.5, 0.5, 20.0 )
CONV_FIELD= RMS_DENSITY
CONV_RESIDUAL_MINVAL= {self.conv_residual_minval}
CONV_STARTITER= 100

% -------------------- LINEAR SOLVER --------------------------
LINEAR_SOLVER= FGMRES
LINEAR_SOLVER_PREC= ILU
LINEAR_SOLVER_ERROR= 1E-6
LINEAR_SOLVER_ITER= 10

% -------------------- MULTIGRID --------------------------------
MGLEVEL= 0

% -------------------- OUTPUT -----------------------------------
SCREEN_OUTPUT= (INNER_ITER, RMS_DENSITY, MACH)
OUTPUT_FILES= (RESTART, PARAVIEW)
VOLUME_FILENAME= {self.volume_filename}

MESH_FILENAME= {mesh}
"""

        config_path = path / "config.cfg"
        config_path.write_text(config_content)
        return config_path


def get_su2_binary() -> Path:
    """Get SU2_CFD binary path from environment or default."""
    env_path = os.environ.get("SU2_CFD_PATH")
    if env_path:
        return Path(env_path)

    # Try common locations
    common_paths = [
        Path("/Users/ajeet/SU2_CFD/bin/SU2_CFD"),
        Path.home() / "SU2_CFD/bin/SU2_CFD",
    ]

    for p in common_paths:
        if p.exists():
            return p

    # Fallback to PATH
    return Path("SU2_CFD")
