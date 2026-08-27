#!/usr/bin/env python3
"""Master orchestrator: runs all CFD cases in sequence.

Execution order:
1. Euler spike (quick convergence test)
2. Full Euler simulation
3. Plume extension simulation
4. RANS simulation
5. RANS plume simulation
6. Post-processing
7. Triple validation + GCI
8. Parametric sweeps
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def main() -> int:
    """Run all CFD pipelines in sequence.

    Returns:
        0 if all pipelines pass, 1 if any fail.
    """
    print("=" * 60)
    print("Master Orchestrator: Rocket Nozzle CFD")
    print("=" * 60)

    results = {}
    total_start = __import__("time").time()

    # 1. Euler spike
    print("\n" + "#" * 60)
    print("# STEP 1/8: Euler Spike (Quick Convergence Test)")
    print("#" * 60)
    try:
        from run_euler_spike import main as euler_spike_main
        results["euler_spike"] = euler_spike_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["euler_spike"] = 1

    # 2. Full Euler simulation
    print("\n" + "#" * 60)
    print("# STEP 2/8: Full Euler Simulation")
    print("#" * 60)
    try:
        from run_euler import main as euler_main
        results["euler"] = euler_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["euler"] = 1

    # 3. Plume extension simulation
    print("\n" + "#" * 60)
    print("# STEP 3/8: Plume Extension Simulation")
    print("#" * 60)
    try:
        from run_plume import main as plume_main
        results["plume"] = plume_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["plume"] = 1

    # 4. RANS simulation
    print("\n" + "#" * 60)
    print("# STEP 4/8: RANS Simulation")
    print("#" * 60)
    try:
        from run_rans import main as rans_main
        results["rans"] = rans_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["rans"] = 1

    # 5. RANS plume simulation
    print("\n" + "#" * 60)
    print("# STEP 5/8: RANS Plume Simulation")
    print("#" * 60)
    try:
        from run_rans_plume import main as rans_plume_main
        results["rans_plume"] = rans_plume_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["rans_plume"] = 1

    # 6. Post-processing
    print("\n" + "#" * 60)
    print("# STEP 6/8: Post-Processing")
    print("#" * 60)
    try:
        from run_postprocess import main as postprocess_main
        results["postprocess"] = postprocess_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["postprocess"] = 1

    # 7. Triple validation + GCI
    print("\n" + "#" * 60)
    print("# STEP 7/8: Triple Validation + GCI")
    print("#" * 60)
    try:
        from run_validation import main as validation_main
        results["validation"] = validation_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["validation"] = 1

    # 8. Parametric sweeps
    print("\n" + "#" * 60)
    print("# STEP 8/8: Parametric Sweeps")
    print("#" * 60)
    try:
        from run_sweeps import main as sweeps_main
        results["sweeps"] = sweeps_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["sweeps"] = 1

    # Summary
    elapsed = __import__("time").time() - total_start
    print("\n" + "=" * 60)
    print("MASTER ORCHESTRATOR SUMMARY")
    print("=" * 60)
    print(f"Total time: {elapsed:.1f}s")
    print()

    all_passed = True
    for name, code in results.items():
        status = "PASSED" if code == 0 else "FAILED"
        print(f"  {name:20s} {status}")
        if code != 0:
            all_passed = False

    print()
    if all_passed:
        print("All pipelines PASSED!")
    else:
        print("Some pipelines FAILED. Check output above for details.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
