#!/usr/bin/env python3
"""Generate geometry visualizations for all rocket engine presets.

Creates 2D annotated contour and 3D revolved surface plots for:
- Merlin 1D (SpaceX Falcon 9)
- Raptor SL (SpaceX Starship)
- RS-25 (Space Shuttle / SLS)
- RL10B-2 (Delta IV / Vulcan Centaur)

Output: docs/assets/images/{engine_name}/geometry/
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nozzle.config import NozzleConfig
from nozzle.presets import merlin_1d, raptor_sl, rs_25, rl10b_2
from viz.contour_annotated import plot_annotated_contour
from viz.nozzle_3d import plot_nozzle_3d


# Engine preset functions mapped to their display names
ENGINES: list[tuple[str, str, Callable[[], NozzleConfig]]] = [
    ("merlin-1d", "Merlin 1D", merlin_1d),
    ("raptor-sl", "Raptor SL", raptor_sl),
    ("rs-25", "RS-25", rs_25),
    ("rl10B-2", "RL10B-2", rl10b_2),
]

IMAGES_DIR = Path("docs/assets/images")
DPI = 300


def main() -> int:
    """Generate geometry plots for all engine presets.

    Returns:
        0 on success, 1 on failure.
    """
    print("=" * 60)
    print("Geometry Visualization: All Engine Presets")
    print("=" * 60)

    generated: list[tuple[str, str, Path]] = []

    for engine_slug, engine_label, preset_fn in ENGINES:
        print(f"\n[{engine_slug}] Generating geometry plots...")
        config = preset_fn()

        # Output directory for this engine
        engine_dir = IMAGES_DIR / engine_slug / "geometry"
        engine_dir.mkdir(parents=True, exist_ok=True)

        # 2D annotated contour
        contour_path = engine_dir / f"{engine_slug}_geometry.png"
        try:
            result = plot_annotated_contour(
                config,
                contour_path,
                dpi=DPI,
                show_dimensions=True,
                show_angles=True,
                show_arc_labels=True,
                engine_name=engine_label,
            )
            print(f"  2D contour: {result}")
            generated.append((engine_slug, "2D contour", result))
        except Exception as exc:
            print(f"  2D contour FAILED: {exc}")

        # 3D revolved surface
        surface_path = engine_dir / f"{engine_slug}_3d.png"
        try:
            result = plot_nozzle_3d(
                config,
                surface_path,
                dpi=DPI,
                engine_name=engine_label,
            )
            print(f"  3D surface: {result}")
            generated.append((engine_slug, "3D surface", result))
        except Exception as exc:
            print(f"  3D surface FAILED: {exc}")

    # Summary table
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"{'Engine':<15} {'Type':<15} {'Output Path'}")
    print("-" * 60)
    for engine, ptype, path in generated:
        print(f"{engine:<15} {ptype:<15} {path}")

    total = len(generated)
    expected = len(ENGINES) * 2
    print(f"\nGenerated: {total}/{expected} images")

    if total < expected:
        print("WARNING: Some images failed to generate.")
        return 1

    print("All geometry plots generated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
