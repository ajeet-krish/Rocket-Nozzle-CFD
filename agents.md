# Rocket Nozzle CFD - Agent Context

## Project Overview

This is a compressible CFD analysis of converging-diverging rocket nozzles for an aerodynamics portfolio. The project demonstrates:
- Compressible flow methodology (Euler + RANS)
- Triple validation (analytical vs MoC vs CFD)
- Parametric design sweeps
- Grid convergence study (ASME V&V 20-2009)

**Target roles:** SpaceX, Relativity Space, Rocket Lab (propulsion, compressible flow)

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Solver | SU2 v8.0+ | Compressible flow, axisymmetric flag |
| Mesh | Gmsh O-grid | Structured, body-fitted, SU2-compatible |
| Contour | Rao bell (Sutton & Biblarz) | Industry standard nozzle design |
| Validation | Triple (isentropic + MoC + SU2) | Demonstrates V&V methodology |
| Portfolio | Static HTML (AK-Vortex theme) | Consistent portfolio identity |

## Phase Breakdown

| Phase | Description | Key Files | Tests |
|-------|-------------|-----------|-------|
| 0 | Spike: validate SU2 convergence | run_phase0.py | 96 |
| 1 | Nozzle geometry + isentropic | nozzle/config.py, nozzle/geometry.py, validation/isentropic.py | +27 |
| 2 | Gmsh O-grid mesh | cfd/mesh.py, cfd/mesh_config.py | +26 |
| 3 | SU2 Euler reference | cfd/config.py, cfd/solver.py | +13 |
| 4 | RANS SST + post-processing | cfd/rans_config.py, viz/postprocessing.py | +23 |
| 5 | Method of Characteristics | validation/moc_solver.py | +29 |
| 6 | Triple validation + sweeps | validation/triple.py, validation/gci.py, sweep/ | +39 |
| 7 | Portfolio HTML site | docs/ | N/A |

**Total: 232 tests, 7 commits, ~50 files**

## Known Issues

1. **MoC is 1D approximation** - The "MoC solver" uses isentropic area-Mach relations at each contour point, not true 2D characteristic line tracing. This is acceptable for validation but should be noted.

2. **Placeholder validation data** - The validation.html page has "Pending" badges for actual SU2 results. These need to be populated after running the full pipeline.

3. **Missing images** - The portfolio site references placeholder PNGs. Actual images require running Phases 3-6 with SU2 installed.

4. **SU2 not in CI** - SU2 runs are manual (not in GitHub Actions) due to compute requirements. Tests only validate Python code, not SU2 convergence.

## Future Work

1. **2D MoC solver** - Implement true Method of Characteristics with characteristic line tracing
2. **Interactive nozzle designer** - Plotly widget for real-time parameter exploration
3. **Schlieren comparison** - Side-by-side CFD vs NASA Schlieren photographs
4. **Failure mode gallery** - Show what happens with coarse mesh, over-expanded nozzle
5. **3D visualization** - Extend to full 3D with PyVista WebGL

## Agent Instructions

### When working on this codebase:

1. **Run tests first**: `uv run pytest tests/ -v` (232 tests)
2. **SU2 is not installed** - Do not attempt to run SU2. Focus on Python code only.
3. **Follow conventions**: 4-space indent, snake_case, PascalCase, type hints, docstrings
4. **No em dashes** - Use hyphens or "to" instead
5. **Portfolio theme** - Match AK-Vortex exactly (Ocean dark theme)
6. **Validation targets** - Exit Mach < 1%, thrust coefficient < 3%, GCI < 5%

### Key interfaces:

- `NozzleConfig` - Frozen dataclass for nozzle geometry parameters
- `SU2NozzleConfig` - SU2 configuration generation
- `generate_nozzle_mesh()` - Gmsh mesh generation
- `exit_mach_from_area_ratio()` - Isentropic exit Mach
- `compare_three_way()` - Triple validation comparison
- `compute_gci()` - Grid Convergence Index per ASME V&V 20-2009

### File organization:

- `src/nozzle/` - Geometry and physics (no external dependencies)
- `src/cfd/` - SU2 mesh and solver (depends on nozzle/)
- `src/validation/` - Analytical validation (depends on nozzle/)
- `src/sweep/` - Parametric sweeps (depends on cfd/ and validation/)
- `src/viz/` - Visualization (depends on cfd/ and validation/)
- `tests/` - pytest test suite
- `docs/` - Portfolio HTML site (no Python)