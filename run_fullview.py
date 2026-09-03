#!/usr/bin/env python3
"""Full-view Merlin 1D plume simulation.

Runs a 2D planar simulation with both halves of the symmetric domain
explicitly resolved. Produces a VTU suitable for direct ParaView
visualization of the complete shock diamond structure.

Unlike the axisymmetric run, this does NOT use AXISYMMETRIC=YES.
Instead, both halves are meshed and computed directly.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import merlin_1d
from nozzle.config import NozzleConfig
from cfd.mesh_fullview import generate_fullview_mesh
from cfd.config import SU2NozzleConfig
from cfd.solver import SU2Solver

CONFIG = EngineConfig = None  # placeholder

# Merlin 1D parameters
TOTAL_PRESSURE = 9.7e6
TOTAL_TEMPERATURE = 3600.0
STATIC_PRESSURE = 101325.0
N_AXIAL = 200
N_NORMAL = 30  # per half (60 total across full height)


def main() -> int:
    parser = argparse.ArgumentParser(description="Full-view Merlin plume")
    parser.add_argument("--step", choices=["mesh", "solve", "all"], default="all")
    args = parser.parse_args()

    workdir = Path("output/merlin-1d/fullview")
    workdir.mkdir(parents=True, exist_ok=True)

    nozzle = merlin_1d()
    # CFD config: chamber_length=0, throat_radius_of_curvature=0
    config = NozzleConfig(
        throat_radius=nozzle.throat_radius,
        expansion_ratio=nozzle.expansion_ratio,
        converging_length=nozzle.converging_length,
        diverging_length=0.7,
        chamber_length=0,
        throat_radius_of_curvature=0,
        theta_n=30,
        theta_e=0.0,
        nozzle_length_fraction=0,
        num_points=nozzle.num_points,
    )

    if args.step in ("mesh", "all"):
        print("[Fullview] Generating mesh...")
        mesh_path = generate_fullview_mesh(
            config,
            n_axial=N_AXIAL,
            n_normal=N_NORMAL,
            output_file=str(workdir / "fullview.su2"),
            plume_length_ratio=160.0,
            plume_radius_ratio=3.0,
        )
        print(f"  Mesh: {mesh_path}")

    if args.step in ("solve", "all"):
        print("[Fullview] Running SU2 (2D planar, no axisymmetric)...")

        # SU2 config: NO AXISYMMETRIC, both halves computed directly
        # Use symmetric BC at y=0 to enforce jet symmetry
        cfg_content = f"""% ------- Full-View Merlin Plume --------
% 2D planar Euler, both halves resolved
% No AXISYMMETRIC - full symmetric domain

SOLVER= EULER
MATH_PROBLEM= DIRECT
RESTART_SOL= NO

% -------------------- GAS PROPERTIES ------------------------
GAMMA_VALUE= 1.4
GAS_CONSTANT= 287.058
SYSTEM_MEASUREMENTS= SI

% -------------------- BOUNDARY CONDITIONS -------------------
MARKER_EULER= ( wall )
MARKER_FAR= ( farfield )

% Inlet: subsonic inlet with total conditions
MARKER_INLET= ( inlet, {TOTAL_TEMPERATURE:.1f}, {TOTAL_PRESSURE:.1f}, 1.0, 0.0, 0.0 )

% Outlet: static pressure (ambient)
MARKER_OUTLET= ( outlet, {STATIC_PRESSURE:.1f} )

% -------------------- NUMERICAL METHOD -----------------------
CONV_NUM_METHOD_FLOW= ROE
MUSCL_FLOW= NO
TIME_DISCRE_FLOW= EULER_IMPLICIT

% -------------------- CONVERGENCE ----------------------------
ITER= 10000
CFL_NUMBER= 0.05
CFL_ADAPT= YES
CFL_ADAPT_PARAM= ( 0.05, 1.2, 0.5, 10.0 )
CONV_FIELD= RMS_DENSITY
CONV_RESIDUAL_MINVAL= -6.0
CONV_STARTITER= 200

% -------------------- LINEAR SOLVER --------------------------
LINEAR_SOLVER= FGMRES
LINEAR_SOLVER_PREC= ILU
LINEAR_SOLVER_ERROR= 1E-6
LINEAR_SOLVER_ITER= 10

% -------------------- OUTPUT -----------------------------------
SCREEN_OUTPUT= (INNER_ITER, RMS_DENSITY, MACH)
OUTPUT_FILES= (RESTART, PARAVIEW)
VOLUME_FILENAME= flow

MESH_FILENAME= fullview.su2
"""
        cfg_path = workdir / "config.cfg"
        cfg_path.write_text(cfg_content)

        solver = SU2Solver()
        t0 = time.time()
        results = solver.run(cfg_path, workdir, timeout=1800, gamma=1.4)
        elapsed = time.time() - t0

        print(f"  Exit Mach: {results.exit_mach:.4f}, Time: {elapsed:.1f}s")

        vtu_path = workdir / "flow.vtu"
        if vtu_path.exists():
            print(f"  VTU: {vtu_path} ({vtu_path.stat().st_size} bytes)")
            print("  Open this directly in ParaView - full symmetric view!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
