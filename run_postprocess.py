#!/usr/bin/env python3
"""Post-processing for rocket nozzle CFD results.

Reads existing VTU files from output/euler/ and output/rans/
and generates visualization plots (wall pressure, shock diamonds,
mach comparison).
"""
import sys
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cfd.vtu_parser import parse_vtu
from viz.postprocessing import plot_wall_pressure, plot_shock_diamonds
from viz.comparison import plot_mach_comparison, generate_comparison_report


def main() -> int:
    """Run post-processing pipeline.

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("Post-Processing: Rocket Nozzle CFD Results")
    print("=" * 60)

    # Setup directories
    euler_dir = Path("output/euler")
    rans_dir = Path("output/rans")
    output_dir = Path("output/postprocess")
    output_dir.mkdir(parents=True, exist_ok=True)

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    has_euler = (euler_dir / "flow.vtu").exists()
    has_rans = (rans_dir / "flow.vtu").exists()

    if not has_euler and not has_rans:
        print("\nERROR: No VTU files found.")
        print("  Run 'uv run python run_euler.py' and/or 'uv run python run_rans.py' first.")
        return 1

    # Step 1: Wall pressure plot (from RANS if available, else Euler)
    print("\n[1/5] Generating wall pressure plot...")
    source_dir = rans_dir if has_rans else euler_dir
    source_label = "RANS" if has_rans else "Euler"

    try:
        vtu_data = parse_vtu(source_dir / "flow.vtu")
        if vtu_data.pressure is not None:
            wall_pressure_path = plots_dir / "wall_pressure.png"
            plot_wall_pressure(
                vtu_data.coordinates[:, 0],
                vtu_data.pressure,
                wall_pressure_path,
            )
            print(f"  Saved: {wall_pressure_path} (from {source_label})")
        else:
            print("  WARNING: No pressure data in VTU file")
    except Exception as e:
        print(f"  WARNING: Could not generate wall pressure plot: {e}")

    # Step 2: Shock diamonds (from RANS if available)
    print("\n[2/5] Generating shock diamond visualization...")
    if has_rans:
        try:
            rans_data = parse_vtu(rans_dir / "flow.vtu")
            shock_path = plots_dir / "shock_diamonds.png"
            plot_shock_diamonds(rans_data, shock_path)
            print(f"  Saved: {shock_path}")
        except Exception as e:
            print(f"  WARNING: Could not generate shock diamonds: {e}")
    else:
        print("  SKIPPED: RANS VTU not found (run run_rans.py first)")

    # Step 3: Copy VTU files for ParaView
    print("\n[3/5] Copying VTU files for ParaView...")
    if has_euler:
        shutil.copy(euler_dir / "flow.vtu", plots_dir / "euler_flow.vtu")
        print("  Copied: euler_flow.vtu")
    if has_rans:
        shutil.copy(rans_dir / "flow.vtu", plots_dir / "rans_flow.vtu")
        print("  Copied: rans_flow.vtu")

    # Step 4: Mach comparison (if both exist)
    print("\n[4/5] Generating Mach comparison plot...")
    if has_euler and has_rans:
        try:
            comparison_path = plots_dir / "mach_comparison.png"
            plot_mach_comparison(
                euler_dir / "flow.vtu",
                rans_dir / "flow.vtu",
                comparison_path,
            )
            print(f"  Saved: {comparison_path}")
        except Exception as e:
            print(f"  WARNING: Could not generate comparison: {e}")
    else:
        print("  SKIPPED: Need both Euler and RANS VTU files")

    # Step 5: Comparison report
    print("\n[5/5] Generating comparison report...")
    if has_euler and has_rans:
        try:
            from cfd.solver import SU2Solver
            solver = SU2Solver()
            euler_results = solver.parse_results(euler_dir)
            rans_results = solver.parse_results(rans_dir)

            report_path = output_dir / "euler_vs_rans.md"
            generate_comparison_report(
                euler_results.exit_mach,
                rans_results.exit_mach,
                report_path,
            )
            print(f"  Saved: {report_path}")
        except Exception as e:
            print(f"  WARNING: Could not generate report: {e}")
    else:
        print("  SKIPPED: Need both Euler and RANS results")

    # Summary
    print("\n" + "=" * 60)
    print("Post-Processing Complete!")
    print("=" * 60)
    print(f"Output: {plots_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
