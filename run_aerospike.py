#!/usr/bin/env python3
"""Aerospike nozzle CFD pipeline.

Runs Euler simulations of an axisymmetric aerospike nozzle at multiple
ambient pressures to demonstrate altitude compensation.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import aerospike_x33
from nozzle.aerospike import AerospikeConfig, plot_aerospike_contour
from cfd.mesh_aerospike import generate_aerospike_mesh
from cfd.config import SU2NozzleConfig, get_su2_binary
from cfd.solver import SU2Solver

# Altitude conditions: (name, pressure Pa, temperature K)
ALTITUDES = [
    ("sea_level", 101325.0, 288.15),
    ("10km", 26500.0, 223.15),
    ("20km", 5529.0, 216.65),
]

CONFIG = aerospike_x33()
TOTAL_PRESSURE = 9.7e6   # Pa (same as Merlin for comparison)
TOTAL_TEMPERATURE = 3600.0  # K


def run_geometry() -> int:
    """Generate aerospike geometry plot."""
    print("\n[Aerospike] Geometry stage")
    output_path = Path("docs/assets/images/aerospike/geometry")
    output_path.mkdir(parents=True, exist_ok=True)

    plot_aerospike_contour(
        CONFIG,
        str(output_path / "aerospike_contour.png"),
        "NASA X-33 Style Aerospike Nozzle",
    )
    print(f"  Plot: {output_path / 'aerospike_contour.png'}")
    return 0


def run_mesh() -> int:
    """Generate aerospike mesh."""
    print("\n[Aerospike] Mesh stage")
    output_dir = Path("output/aerospike/sea_level")
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh_path = generate_aerospike_mesh(
        CONFIG,
        n_axial=120,
        n_normal=40,
        output_file=str(output_dir / "aerospike.su2"),
        plume_extension=False,
    )
    print(f"  Mesh: {mesh_path}")
    return 0


def run_simulation(altitude_name: str, static_pressure: float, temperature: float) -> int:
    """Run Euler simulation at given altitude."""
    print(f"\n[Aerospike] Simulation: {altitude_name} (P={static_pressure:.0f} Pa)")

    workdir = Path(f"output/aerospike/{altitude_name}")
    workdir.mkdir(parents=True, exist_ok=True)

    # Generate mesh
    mesh_path = generate_aerospike_mesh(
        CONFIG,
        n_axial=120,
        n_normal=40,
        output_file=str(workdir / "aerospike.su2"),
        plume_extension=False,
    )

    # SU2 config - no AXISYMMETRIC (aerospike has no axis boundary)
    # Run as 2D planar with area correction
    su2 = SU2NozzleConfig(
        total_pressure=TOTAL_PRESSURE,
        total_temperature=TOTAL_TEMPERATURE,
        static_pressure=static_pressure,
        iterations=15000,
        cfl_number=0.01,
        farfield_marker="",
    )

    # Write config
    cfg_content = f"""% ------- Aerospike Nozzle CFD --------
% 2D planar Euler (no axisymmetric - spike body occupies axis)
% Altitude: {altitude_name}, P_amb = {static_pressure:.0f} Pa

SOLVER= EULER
MATH_PROBLEM= DIRECT
RESTART_SOL= NO

% -------------------- GAS PROPERTIES ------------------------
GAMMA_VALUE= 1.4
GAS_CONSTANT= 287.058
SYSTEM_MEASUREMENTS= SI

% -------------------- BOUNDARY CONDITIONS -------------------
MARKER_EULER= ( wall, spike_wall )

% Inlet: subsonic inlet with total conditions
MARKER_INLET= ( inlet, {TOTAL_TEMPERATURE:.1f}, {TOTAL_PRESSURE:.1f}, 1.0, 0.0, 0.0 )

% Outlet: static pressure (ambient)
MARKER_OUTLET= ( outlet, {static_pressure:.1f} )

% -------------------- NUMERICAL METHOD -----------------------
CONV_NUM_METHOD_FLOW= ROE
MUSCL_FLOW= NO
SLOPE_LIMITER= VENKATAKRISHNAN
TIME_DISCRE_FLOW= EULER_IMPLICIT

% -------------------- CONVERGENCE ----------------------------
ITER= 15000
CFL_NUMBER= 0.01
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

% -------------------- MULTIGRID --------------------------------
MGLEVEL= 0

% -------------------- OUTPUT -----------------------------------
SCREEN_OUTPUT= (INNER_ITER, RMS_DENSITY, MACH)
OUTPUT_FILES= (RESTART, PARAVIEW)
VOLUME_FILENAME= flow

MESH_FILENAME= aerospike.su2
"""
    cfg_path = workdir / "config.cfg"
    cfg_path.write_text(cfg_content)

    # Run solver
    solver = SU2Solver()
    t0 = time.time()
    results = solver.run(cfg_path, workdir, timeout=1800, gamma=1.4)
    elapsed = time.time() - t0

    print(f"  Exit Mach: {results.exit_mach:.4f}, Time: {elapsed:.1f}s")

    # Save results
    perf_data = {
        "altitude": altitude_name,
        "ambient_pressure": static_pressure,
        "ambient_temperature": temperature,
        "exit_mach": results.exit_mach,
        "total_pressure": TOTAL_PRESSURE,
        "total_temperature": TOTAL_TEMPERATURE,
    }
    with open(workdir / "results.json", "w") as f:
        json.dump(perf_data, f, indent=2)

    return 0


def run_comparison() -> int:
    """Compare aerospike performance across altitudes."""
    print("\n[Aerospike] Comparison stage")

    results = []
    for alt_name, _, _ in ALTITUDES:
        result_file = Path(f"output/aerospike/{alt_name}/results.json")
        if result_file.exists():
            with open(result_file) as f:
                results.append(json.load(f))

    if not results:
        print("  No results found. Run simulations first.")
        return 1

    # Print comparison table
    print(f"\n  {'Altitude':<15} {'P_amb (Pa)':<12} {'Exit Mach':<12}")
    print(f"  {'-'*40}")
    for r in results:
        print(f"  {r['altitude']:<15} {r['ambient_pressure']:<12.0f} {r['exit_mach']:<12.4f}")

    # Save comparison
    output_dir = Path("output/aerospike")
    with open(output_dir / "comparison.json", "w") as f:
        json.dump(results, f, indent=2)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Aerospike CFD pipeline")
    parser.add_argument(
        "--step",
        choices=["geometry", "mesh", "simulation", "comparison", "all"],
        default=None,
        help="Run a single step (default: all)",
    )
    parser.add_argument(
        "--altitude",
        choices=[name for name, _, _ in ALTITUDES],
        default=None,
        help="Run simulation at specific altitude (with --step simulation)",
    )
    args = parser.parse_args()

    if args.step == "geometry":
        return run_geometry()
    elif args.step == "mesh":
        return run_mesh()
    elif args.step == "simulation":
        if args.altitude:
            for name, p, t in ALTITUDES:
                if name == args.altitude:
                    return run_simulation(name, p, t)
        # Run all altitudes
        for name, p, t in ALTITUDES:
            run_simulation(name, p, t)
        return 0
    elif args.step == "comparison":
        return run_comparison()
    else:
        # Run all steps
        run_geometry()
        run_mesh()
        for name, p, t in ALTITUDES:
            run_simulation(name, p, t)
        run_comparison()
        return 0


if __name__ == "__main__":
    sys.exit(main())
