#!/usr/bin/env python3
"""Master orchestrator: runs all CFD cases in sequence.

Execution order:
1. Euler spike (quick convergence test)
2. Full Euler simulation
3. RANS simulation
4. Post-processing
5. Triple validation + GCI
6. Parametric sweeps
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
    print("# STEP 1/6: Euler Spike (Quick Convergence Test)")
    print("#" * 60)
    try:
        from run_euler_spike import main as euler_spike_main
        results["euler_spike"] = euler_spike_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["euler_spike"] = 1

    # 2. Full Euler simulation
    print("\n" + "#" * 60)
    print("# STEP 2/6: Full Euler Simulation")
    print("#" * 60)
    try:
        from run_euler import main as euler_main
        results["euler"] = euler_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["euler"] = 1

    # 3. RANS simulation
    print("\n" + "#" * 60)
    print("# STEP 3/6: RANS Simulation")
    print("#" * 60)
    try:
        from run_rans import main as rans_main
        results["rans"] = rans_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["rans"] = 1

    # 4. Post-processing
    print("\n" + "#" * 60)
    print("# STEP 4/6: Post-Processing")
    print("#" * 60)
    try:
        from run_postprocess import main as postprocess_main
        results["postprocess"] = postprocess_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["postprocess"] = 1

    # 5. Triple validation + GCI
    print("\n" + "#" * 60)
    print("# STEP 5/6: Triple Validation + GCI")
    print("#" * 60)
    try:
        from run_validation import main as validation_main
        results["validation"] = validation_main()
    except Exception as e:
        print(f"  FATAL: {e}")
        results["validation"] = 1

    # 6. Parametric sweeps
    print("\n" + "#" * 60)
    print("# STEP 6/6: Parametric Sweeps")
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
