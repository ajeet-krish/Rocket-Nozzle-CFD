"""Pipeline stage functions for per-engine CFD analysis.

KEY RULE: Plots go to docs/assets/images/{engine}/, simulation artifacts go to output/{engine}/.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nozzle.config import NozzleConfig
from cfd.config import SU2NozzleConfig
from cfd.rans_config import SU2RANSConfig
from cfd.mesh import generate_nozzle_mesh
from cfd.solver import SU2Solver
from validation.isentropic import exit_mach_from_area_ratio
from validation.compare import compare_results
from validation.moc_solver import MoCSolver
from validation.triple import compare_three_way
from validation.gci import GCIMeshLevel, compute_gci
from sweep.config import SweepConfig
from sweep.runner import SweepRunner
from sweep.plotter import plot_sweep

from .engine_config import EngineConfig, PipelineStage


def run_geometry_stage(config: EngineConfig) -> int:
    """Generate geometry visualizations.

    2D annotated contour + 3D surface -> docs/assets/images/{engine}/

    Returns:
        0 on success, 1 on failure.
    """
    print(f"\n[{config.label}] Geometry stage")

    images_dir = Path(config.images_dir) / "geometry"
    images_dir.mkdir(parents=True, exist_ok=True)

    nozzle_config = config.viz_config  # Full preset for viz (includes chamber)

    from viz.contour_annotated import plot_annotated_contour
    from viz.nozzle_3d import plot_nozzle_3d

    try:
        contour_path = images_dir / f"{config.name}_geometry.png"
        plot_annotated_contour(
            nozzle_config, contour_path, dpi=300,
            show_dimensions=True, show_angles=True,
            show_arc_labels=True, engine_name=config.label,
        )
        print(f"  2D contour: {contour_path}")
    except Exception as exc:
        print(f"  2D contour FAILED: {exc}")
        return 1

    try:
        surface_path = images_dir / f"{config.name}_3d.png"
        plot_nozzle_3d(
            nozzle_config, surface_path, dpi=300,
            engine_name=config.label,
        )
        print(f"  3D surface: {surface_path}")
    except Exception as exc:
        print(f"  3D surface FAILED: {exc}")
        return 1

    return 0


def run_mesh_stage(config: EngineConfig, plume: bool = False) -> int:
    """Generate mesh.

    Mesh -> output/{engine}/euler/ or output/{engine}/plume/

    Returns:
        0 on success, 1 on failure.
    """
    tag = "plume" if plume else "euler"
    print(f"\n[{config.label}] Mesh stage ({tag})")

    nozzle_config = config.nozzle_config()

    if plume:
        workdir = Path(f"{config.output_dir}/plume")
        n_axial = config.plume_n_axial
        n_normal = config.plume_n_normal
    else:
        workdir = Path(f"{config.output_dir}/euler")
        n_axial = config.euler_n_axial
        n_normal = config.euler_n_normal

    workdir.mkdir(parents=True, exist_ok=True)

    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        n_axial=n_axial,
        n_normal=n_normal,
        output_file=str(workdir / "nozzle.su2"),
        plume_extension=plume,
        plume_length_ratio=config.plume_length_ratio,
        plume_radius_ratio=config.plume_radius_ratio,
        multi_curve=config.multi_curve,
    )
    print(f"  Mesh: {mesh_path}")
    return 0


def run_euler_stage(config: EngineConfig) -> int:
    """Run Euler simulation.

    Euler sim -> output/{engine}/euler/
    Plots -> docs/assets/images/{engine}/euler/

    Returns:
        0 on success, 1 on failure.
    """
    print(f"\n[{config.label}] Euler stage")

    nozzle_config = config.nozzle_config()
    workdir = Path(f"{config.output_dir}/euler")
    workdir.mkdir(parents=True, exist_ok=True)

    images_dir = Path(f"{config.images_dir}/euler")
    images_dir.mkdir(parents=True, exist_ok=True)

    su2 = SU2NozzleConfig(
        total_pressure=config.total_pressure,
        total_temperature=config.total_temperature,
        static_pressure=config.static_pressure,
        gamma=config.gamma,
        iterations=config.euler_iterations,
        cfl_number=config.euler_cfl,
        farfield_marker="",
    )

    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        n_axial=config.euler_n_axial,
        n_normal=config.euler_n_normal,
        output_file=str(workdir / "nozzle.su2"),
        plume_extension=False,
        multi_curve=config.multi_curve,
    )

    cfg_path = su2.write(workdir)

    solver = SU2Solver()
    t0 = time.time()
    results = solver.run(cfg_path, workdir, timeout=600, gamma=config.gamma)
    elapsed = time.time() - t0

    theory_mach = exit_mach_from_area_ratio(nozzle_config.expansion_ratio, config.gamma)
    report = compare_results(results.exit_mach, nozzle_config.expansion_ratio, gamma=config.gamma, tolerance=5.0)

    history = workdir / "history.csv"
    if history.exists():
        from viz.convergence import plot_convergence
        plot_convergence(history, images_dir / "convergence.png")

    vtu = workdir / "flow.vtu"
    if vtu.exists():
        from viz.mach_contour import plot_mach_contour
        plot_mach_contour(vtu, images_dir / "mach_contour.png", nozzle_config=nozzle_config)

    print(f"  Mach (sim): {results.exit_mach:.4f}, Mach (theory): {theory_mach:.4f}")
    print(f"  Error: {report.mach_error_percent:.2f}%, Time: {elapsed:.1f}s")
    print(f"  Result: {'PASSED' if report.passed else 'FAILED'}")

    # Performance metrics
    from validation.performance import compute_performance
    theory_perf = compute_performance(
        nozzle_config, config.total_pressure, config.total_temperature,
        theory_mach, config.gamma, ambient_pressure=config.static_pressure,
    )
    sim_perf = compute_performance(
        nozzle_config, config.total_pressure, config.total_temperature,
        results.exit_mach, config.gamma, ambient_pressure=config.static_pressure,
    )
    print(f"  CF: {sim_perf.thrust_coefficient:.4f} (theory: {theory_perf.thrust_coefficient:.4f})")
    print(f"  Isp: {sim_perf.specific_impulse:.1f}s (theory: {theory_perf.specific_impulse:.1f}s)")
    print(f"  Ve: {sim_perf.exit_velocity:.0f} m/s, Thrust: {sim_perf.thrust_force/1000:.1f} kN")

    # Save performance data
    import json
    perf_data = {
        "engine": config.label,
        "exit_mach_sim": results.exit_mach,
        "exit_mach_theory": theory_mach,
        "thrust_coefficient_sim": sim_perf.thrust_coefficient,
        "thrust_coefficient_theory": theory_perf.thrust_coefficient,
        "specific_impulse_sim": sim_perf.specific_impulse,
        "specific_impulse_theory": theory_perf.specific_impulse,
        "exit_velocity": sim_perf.exit_velocity,
        "thrust_force_kN": sim_perf.thrust_force / 1000,
        "mass_flow_rate": sim_perf.mass_flow_rate,
    }
    with open(workdir / "performance.json", "w") as f:
        json.dump(perf_data, f, indent=2)

    return 0 if report.passed else 1


def run_rans_stage(config: EngineConfig) -> int:
    """Run RANS simulation.

    RANS sim -> output/{engine}/rans/
    Plots -> docs/assets/images/{engine}/rans/

    Returns:
        0 on success, 1 on failure.
    """
    print(f"\n[{config.label}] RANS stage")

    nozzle_config = config.nozzle_config()
    workdir = Path(f"{config.output_dir}/rans")
    workdir.mkdir(parents=True, exist_ok=True)

    images_dir = Path(f"{config.images_dir}/rans")
    images_dir.mkdir(parents=True, exist_ok=True)

    rans_config = SU2RANSConfig(
        total_pressure=config.total_pressure,
        total_temperature=config.total_temperature,
        static_pressure=config.static_pressure,
        cfl_number=config.rans_cfl,
        iterations=config.rans_iterations,
        farfield_marker="",
    )

    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        n_axial=config.rans_n_axial,
        n_normal=config.rans_n_normal,
        output_file=str(workdir / "nozzle.su2"),
        rans_mode=False,  # Use Euler mesh for stability
        plume_extension=False,
        multi_curve=config.multi_curve,
    )

    cfg_path = rans_config.write(workdir)

    solver = SU2Solver()
    t0 = time.time()
    results = solver.run(cfg_path, workdir, timeout=1800, gamma=config.gamma)
    elapsed = time.time() - t0

    vtu = workdir / "flow.vtu"
    if vtu.exists():
        from viz.mach_contour import plot_mach_contour
        plot_mach_contour(vtu, images_dir / "mach_contour_rans.png", nozzle_config=nozzle_config)

    print(f"  Exit Mach: {results.exit_mach:.4f}, Time: {elapsed:.1f}s")

    euler_dir = Path(f"{config.output_dir}/euler")
    if (euler_dir / "flow.vtu").exists():
        euler_results = solver.parse_results(euler_dir)
        diff = abs(euler_results.exit_mach - results.exit_mach)
        pct = diff / euler_results.exit_mach * 100 if euler_results.exit_mach > 0 else 0.0
        print(f"  Euler vs RANS: {euler_results.exit_mach:.4f} vs {results.exit_mach:.4f} ({pct:.2f}%)")

    return 0


def run_plume_stage(config: EngineConfig) -> int:
    """Run plume simulation.

    Plume sim -> output/{engine}/plume/
    Plots -> docs/assets/images/{engine}/plume/

    Returns:
        0 on success, 1 on failure.
    """
    print(f"\n[{config.label}] Plume stage")

    import numpy as np

    nozzle_config = config.nozzle_config()
    workdir = Path(f"{config.output_dir}/plume")
    workdir.mkdir(parents=True, exist_ok=True)

    images_dir = Path(f"{config.images_dir}/plume")
    images_dir.mkdir(parents=True, exist_ok=True)

    su2 = SU2NozzleConfig(
        total_pressure=config.total_pressure,
        total_temperature=config.total_temperature,
        static_pressure=config.static_pressure,
        gamma=config.gamma,
        iterations=config.euler_iterations,
        cfl_number=config.euler_cfl * 0.5,
        farfield_marker="farfield",
    )

    mesh_path = generate_nozzle_mesh(
        nozzle_config,
        n_axial=config.plume_n_axial,
        n_normal=config.plume_n_normal,
        output_file=str(workdir / "nozzle.su2"),
        plume_extension=True,
        plume_length_ratio=config.plume_length_ratio,
        plume_radius_ratio=config.plume_radius_ratio,
        multi_curve=config.multi_curve,
    )

    cfg_path = su2.write(workdir)

    solver = SU2Solver()
    t0 = time.time()
    results = solver.run(cfg_path, workdir, timeout=1800, gamma=config.gamma)
    elapsed = time.time() - t0

    theory_mach = exit_mach_from_area_ratio(nozzle_config.expansion_ratio, config.gamma)

    sim_exit_mach = results.exit_mach
    vtu_path = workdir / "flow.vtu"
    if vtu_path.exists():
        from cfd.vtu_parser import parse_vtu
        vtu_data = parse_vtu(vtu_path)
        exit_x = nozzle_config.computed_diverging_length
        exit_mask = np.abs(vtu_data.coordinates[:, 0] - exit_x) < 0.05
        if exit_mask.any():
            sim_exit_mach = float(vtu_data.mach[exit_mask].mean())

    report = compare_results(sim_exit_mach, nozzle_config.expansion_ratio, gamma=config.gamma, tolerance=5.0)

    if vtu_path.exists():
        from viz.mach_contour import plot_mach_contour
        plot_mach_contour(vtu_path, images_dir / "mach_contour_plume.png", nozzle_config=nozzle_config)

        from viz.postprocessing import plot_shock_diamonds
        from cfd.vtu_parser import parse_vtu
        vtu_data = parse_vtu(vtu_path)
        plot_shock_diamonds(vtu_data, images_dir / "shock_diamonds.png")

    history = workdir / "history.csv"
    if history.exists():
        from viz.convergence import plot_convergence
        plot_convergence(history, images_dir / "convergence_plume.png")

    print(f"  Exit Mach: {sim_exit_mach:.4f}, Theory: {theory_mach:.4f}")
    print(f"  Error: {report.mach_error_percent:.2f}%, Time: {elapsed:.1f}s")
    print(f"  Result: {'PASSED' if report.passed else 'FAILED'}")

    return 0 if report.passed else 1


def run_sweep_stage(config: EngineConfig) -> int:
    """Run parametric sweep.

    Sweep -> output/{engine}/sweeps/
    Plots -> docs/assets/images/{engine}/sweeps/

    Returns:
        0 on success, 1 on failure.
    """
    print(f"\n[{config.label}] Sweep stage")

    workdir = Path(f"{config.output_dir}/sweeps")
    workdir.mkdir(parents=True, exist_ok=True)

    images_dir = Path(f"{config.images_dir}/sweeps")
    images_dir.mkdir(parents=True, exist_ok=True)

    sweep_config = SweepConfig(
        expansion_ratios=config.sweep_expansion_ratios,
        chamber_pressures=config.sweep_chamber_pressures,
        throat_radii=config.sweep_throat_radii,
        reference_epsilon=config.sweep_expansion_ratios[0] if config.sweep_expansion_ratios else 12.0,
        reference_pc=config.total_pressure,
        reference_r_star=config.nozzle_config().throat_radius,
        total_temperature=config.total_temperature,
        gamma=config.gamma,
    )

    runner = SweepRunner(workdir)
    results = runner.run_sweep(sweep_config)

    csv_path = workdir / "sweep_results.csv"
    results.to_csv(csv_path)
    print(f"  Cases: {len(results.cases)}, CSV: {csv_path}")

    plot_paths = plot_sweep(results, images_dir)
    for p in plot_paths:
        print(f"  Plot: {p}")

    return 0


STAGE_FUNCTIONS = {
    PipelineStage.GEOMETRY: run_geometry_stage,
    PipelineStage.MESH: run_mesh_stage,
    PipelineStage.EULER: run_euler_stage,
    PipelineStage.RANS: run_rans_stage,
    PipelineStage.PLUME: run_plume_stage,
    PipelineStage.SWEEP: run_sweep_stage,
}


def run_full_pipeline(
    config: EngineConfig,
    stages: list[PipelineStage] | None = None,
) -> int:
    """Run all (or selected) pipeline stages.

    Args:
        config: Engine configuration
        stages: List of stages to run. None = all stages.

    Returns:
        0 if all stages pass, 1 if any fail.
    """
    if stages is None:
        stages = list(PipelineStage)

    print("=" * 60)
    print(f"  Pipeline: {config.label} ({config.name})")
    print(f"  Stages: {[s.value for s in stages]}")
    print("=" * 60)

    t0 = time.time()
    results = {}

    for stage in stages:
        fn = STAGE_FUNCTIONS[stage]
        if stage == PipelineStage.MESH:
            results[stage] = fn(config, plume=False)
        else:
            results[stage] = fn(config)

    elapsed = time.time() - t0

    print_summary(config, results, elapsed)

    return 0 if all(v == 0 for v in results.values()) else 1


def print_summary(
    config: EngineConfig,
    results: dict[PipelineStage, int],
    elapsed: float,
) -> None:
    """Print pipeline summary table."""
    print(f"\n{'=' * 60}")
    print(f"  Summary: {config.label}")
    print(f"{'=' * 60}")
    print(f"  Total time: {elapsed:.1f}s\n")

    for stage, code in results.items():
        status = "PASSED" if code == 0 else "FAILED"
        print(f"  {stage.value:12s} {status}")

    n_pass = sum(1 for v in results.values() if v == 0)
    print(f"\n  {n_pass}/{len(results)} stages passed")
    print(f"{'=' * 60}")
