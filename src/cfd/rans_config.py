"""SU2 RANS configuration for nozzle simulation."""
from dataclasses import dataclass
from pathlib import Path

from .config import SU2NozzleConfig


@dataclass
class SU2RANSConfig(SU2NozzleConfig):
    """SU2 RANS configuration with SST k-omega turbulence model."""

    # Turbulence model
    turb_model: str = "SST"

    # Turbulence numerics
    conv_num_method_turb: str = "SCALAR_UPWIND"
    muscl_turb: bool = False

    # Wall boundary conditions
    wall_heat_flux: float = 0.0  # Adiabatic wall
    wall_temperature: float = 300.0  # Not used for adiabatic

    # Turbulence initialization
    freestream_turbulence_intensity: float = 0.05  # 5%
    freestream_viscosity_ratio: float = 10.0

    def write(self, path: Path, mesh_filename: str | None = None) -> Path:
        """Generate SU2 RANS .cfg file.

        Args:
            path: Directory to write config file
            mesh_filename: Override mesh filename

        Returns:
            Path to written config file
        """
        mesh = mesh_filename or self.mesh_filename

        config_content = f"""% ------- Rocket Nozzle CFD - Phase 4 RANS Case --------
% Converging-diverging nozzle, RANS SST, axisymmetric

SOLVER= RANS
KIND_TURB_MODEL= {self.turb_model}
MATH_PROBLEM= DIRECT
RESTART_SOL= NO
AXISYMMETRIC= YES

% -------------------- GAS PROPERTIES ------------------------
GAMMA_VALUE= {self.gamma}
GAS_CONSTANT= {self.gas_constant}
SYSTEM_MEASUREMENTS= SI

% Reynolds number for RANS
REYNOLDS_NUMBER= 1e6
REYNOLDS_LENGTH= 0.1

% -------------------- FREESTREAM CONDITIONS -------------------
% Set to ambient conditions (inlet BC drives the flow)
FREESTREAM_PRESSURE= {self.static_pressure:.1f}
FREESTREAM_TEMPERATURE= 300.0
FREESTREAM_OPTION= TEMPERATURE_FS
MACH_NUMBER= 0.01

% -------------------- BOUNDARY CONDITIONS -------------------
MARKER_SYM= ( {self.symmetry_marker} )
MARKER_HEATFLUX= ( {self.wall_marker}, {self.wall_heat_flux} )

% Inlet: subsonic inlet with total conditions (Tt, Pt, Vx, Vy, Vz)
MARKER_INLET= ( {self.inlet_marker}, {self.total_temperature:.1f}, {self.total_pressure:.1f}, 1.0, 0.0, 0.0 )

% Outlet: static pressure
MARKER_OUTLET= ( {self.outlet_marker}, {self.static_pressure:.1f} )

% -------------------- NUMERICAL METHOD -----------------------
CONV_NUM_METHOD_FLOW= ROE
MUSCL_FLOW= NO
TIME_DISCRE_FLOW= EULER_IMPLICIT

% Turbulence initialization
FREESTREAM_TURBULENCEINTENSITY= {self.freestream_turbulence_intensity}
FREESTREAM_TURB2LAMVISCRATIO= {self.freestream_viscosity_ratio}

% Turbulence numerics
CONV_NUM_METHOD_TURB= {self.conv_num_method_turb}
MUSCL_TURB= {'YES' if self.muscl_turb else 'NO'}
TIME_DISCRE_TURB= EULER_IMPLICIT

% -------------------- CONVERGENCE ----------------------------
ITER= {self.iterations}
CFL_NUMBER= {self.cfl_number}
CFL_ADAPT= YES
CFL_ADAPT_PARAM= ( 0.1, 1.5, 0.5, 20.0 )
CONV_FIELD= (RMS_DENSITY, RMS_TKE)
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

        config_path = path / "config_rans.cfg"
        config_path.write_text(config_content)
        return config_path
