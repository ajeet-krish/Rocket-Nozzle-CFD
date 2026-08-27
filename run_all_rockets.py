#!/usr/bin/env python3
"""Run Euler CFD for every rocket engine preset.

Output structure:
    output/<engine-name>/euler/
        nozzle.su2, config.cfg, flow.vtu, history.csv, plots/
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.presets import merlin_1d, raptor_sl, rs_25, rl10b_2
from cfd.config import SU2NozzleConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver
from validation.isentropic import exit_mach_from_area_ratio
from validation.compare import compare_results
from viz.convergence import plot_convergence
from viz.mach_contour import plot_mach_contour

# Engine名 -> (preset_fn, Pt_Pa, Tt_K)
ENGINES = {
    "merlin-1d": (merlin_1d,  9.7e6,  3600.0),
    "raptor-sl": (raptor_sl, 33.0e6, 3500.0),
    "rs-25":     (rs_25,     20.6e6, 3570.0),
    "rl10B-2":   (rl10b_2,   4.2e6,  2200.0),
}


def run_euler(name: str, config, Pt: float, Tt: float) -> dict:
    """Run one Euler case and return results dict."""
    workdir = Path(f"output/{name}/euler")
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "plots").mkdir(parents=True, exist_ok=True)

    su2 = SU2NozzleConfig(
        total_pressure=Pt,
        total_temperature=Tt,
        static_pressure=101325.0,
        gamma=1.4,
        iterations=5000,
        cfl_number=0.1,
        farfield_marker="farfield",
    )

    # Mesh
    mesh_path = generate_nozzle_mesh(
        config, n_axial=60, n_normal=30,
        output_file=str(workdir / "nozzle.su2"),
        plume_extension=True,
    )

    # Config
    cfg_path = su2.write(workdir)

    # Solve
    solver = SU2Solver()
    t0 = time.time()
    results = solver.run(cfg_path, workdir, timeout=1800, gamma=1.4)
    elapsed = time.time() - t0

    # Validate
    theory_mach = exit_mach_from_area_ratio(config.expansion_ratio, 1.4)
    report = compare_results(results.exit_mach, config.expansion_ratio, gamma=1.4, tolerance=5.0)

    # Plots
    history = workdir / "history.csv"
    if history.exists():
        plot_convergence(history, workdir / "plots" / "convergence.png")
    vtu = workdir / "flow.vtu"
    if vtu.exists():
        plot_mach_contour(vtu, workdir / "plots" / "mach_contour.png", nozzle_config=config)

    return {
        "name": name,
        "mach_sim": results.exit_mach,
        "mach_theory": theory_mach,
        "error": report.mach_error_percent,
        "passed": report.passed,
        "time": elapsed,
    }


def main() -> int:
    print("=" * 65)
    print("  Euler CFD  --  All Rocket Engines")
    print("=" * 65)

    all_results = []
    for name, (preset_fn, Pt, Tt) in ENGINES.items():
        print(f"\n{'─' * 65}")
        print(f"  {name}   Pt={Pt/1e6:.1f} MPa   Tt={Tt:.0f} K")
        print(f"{'─' * 65}")
        try:
            r = run_euler(name, preset_fn(), Pt, Tt)
            all_results.append(r)
            tag = "PASSED" if r["passed"] else "FAILED"
            print(f"  Mach (sim):  {r['mach_sim']:.4f}")
            print(f"  Mach (theory): {r['mach_theory']:.4f}")
            print(f"  Error: {r['error']:.2f}%   [{tag}]   {r['time']:.1f}s")
        except Exception as exc:
            print(f"  ERROR: {exc}")
            all_results.append({"name": name, "passed": False, "error": str(exc)})

    # Summary table
    print(f"\n{'=' * 65}")
    print("  SUMMARY")
    print(f"{'=' * 65}")
    print(f"  {'Engine':<14} {'Mach (sim)':>10} {'Mach (th)':>10} {'Error':>8} {'Status':>8}")
    print(f"  {'─'*14} {'─'*10} {'─'*10} {'─'*8} {'─'*8}")
    for r in all_results:
        if "mach_sim" in r:
            print(f"  {r['name']:<14} {r['mach_sim']:>10.4f} {r['mach_theory']:>10.4f} {r['error']:>7.2f}% {'PASSED' if r['passed'] else 'FAILED':>8}")
        else:
            print(f"  {r['name']:<14} {'--':>10} {'--':>10} {'--':>8} {'ERROR':>8}")

    n_pass = sum(1 for r in all_results if r.get("passed"))
    print(f"\n  {n_pass}/{len(all_results)} passed")
    print(f"{'=' * 65}")

    return 0 if n_pass == len(all_results) else 1


if __name__ == "__main__":
    sys.exit(main())
