#!/usr/bin/env python3
"""Master orchestrator: runs all engine pipelines in sequence.

Calls each engine's main() for full pipeline execution.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


def main() -> int:
    """Run all engine CFD pipelines in sequence.

    Returns:
        0 if all pipelines pass, 1 if any fail.
    """
    print("=" * 60)
    print("Master Orchestrator: Rocket Nozzle CFD")
    print("=" * 60)

    engines = [
        ("merlin-1d", "run_merlin"),
        ("raptor-sl", "run_raptor"),
        ("rs-25", "run_rs25"),
        ("rl10B-2", "run_rl10b2"),
    ]

    results = {}
    total_start = time.time()

    for engine_name, module_name in engines:
        print(f"\n{'#' * 60}")
        print(f"# ENGINE: {engine_name}")
        print(f"{'#' * 60}")
        try:
            mod = __import__(module_name)
            results[engine_name] = mod.main()
        except Exception as e:
            print(f"  FATAL: {e}")
            results[engine_name] = 1

    elapsed = time.time() - total_start

    print(f"\n{'=' * 60}")
    print("MASTER ORCHESTRATOR SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total time: {elapsed:.1f}s\n")

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
