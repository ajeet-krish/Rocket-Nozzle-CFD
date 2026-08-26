# Rocket Nozzle CFD

Compressible CFD analysis of converging-diverging rocket nozzles using SU2, with triple validation against isentropic theory and Method of Characteristics.

## Quick Commands

```bash
# Run all tests (228 tests)
uv run pytest tests/ -v

# Run Phase 0 spike (validates SU2 convergence)
uv run python run_phase0.py

# Run Phase 3 Euler reference case
uv run python run_phase3.py

# Run Phase 4 RANS + post-processing
uv run python run_phase4.py

# Run Phase 6 parametric sweeps + GCI
uv run python run_phase6.py
```

## Architecture

| Component | Location | Purpose |
|-----------|----------|---------|
| `src/nozzle/` | Geometry & physics | Nozzle contour, isentropic relations |
| `src/cfd/` | SU2 mesh & solver | Gmsh mesh, SU2 config, VTU parsing |
| `src/validation/` | Analytical validation | Isentropic, MoC, triple comparison, GCI |
| `src/sweep/` | Parametric sweeps | Sweep config, runner, results, plots |
| `src/viz/` | Visualization | Mach contour, shock diamonds, comparison |
| `tests/` | Test suite | 228 tests, pytest |
| `docs/` | Portfolio HTML site | AK-Vortex theme, 5 pages |

## Key Interfaces

- `NozzleConfig` - Frozen dataclass for nozzle geometry
- `SU2NozzleConfig` - SU2 config generation (v8.4.0)
- `SU2RANSConfig` - RANS config with SST turbulence
- `generate_nozzle_mesh()` - Gmsh O-grid with BL refinement
- `parse_vtu()` - Binary VTU parser for SU2 v8.4.0
- `exit_mach_from_area_ratio()` - Isentropic exit Mach
- `compare_three_way()` - Triple validation comparison
- `compute_gci()` - Grid Convergence Index (ASME V&V 20-2009)

## SU2 Configuration (v8.4.0)

**Critical: SU2 v8.4.0 uses different option names than older versions.**

| Old Option | v8.4.0 Option |
|------------|---------------|
| `MARKER_TOTAL_CONDITIONS` | `MARKER_INLET` |
| `HISTORY_FILENAME` | Not valid (uses default) |
| `TABULAR_FORMAT` | Not valid |
| `FREESTREAM_TURBULENCE_INTENSITY` | `FREESTREAM_TURBULENCEINTENSITY` |

**Working config pattern:**
```
SOLVER= EULER
AXISYMMETRIC= YES
MARKER_EULER= ( wall )
MARKER_SYM= ( symmetry )
MARKER_INLET= ( inlet, Tt, Pt, Vx, Vy, Vz )
MARKER_OUTLET= ( outlet, Ps )
CONV_NUM_METHOD_FLOW= ROE
MUSCL_FLOW= NO
CFL_NUMBER= 0.1
```

## Mesh Generation

**Critical: Use 6+ key points for spline, not just 3.**

The mesh generator uses key points from the nozzle contour to create a spline that matches the actual geometry. Using only 3 points (inlet, throat, exit) creates a curve that doesn't match the Rao bell shape.

```python
# Good: Use 6+ key points
key_indices = [0, n_points//8, throat_idx, n_points//2, n_points - 1]

# Bad: Only 3 points
key_indices = [0, throat_idx, n_points - 1]
```

**Mesh resolution:** Use 40x20 (800 elements) for accurate results. 20x10 (200 elements) gives 13% error.

## VTU Parsing

SU2 v8.4.0 outputs binary VTU files with appended data format. The parser must handle:
1. XML header parsing
2. Binary data extraction from appended section
3. Offset-based data array reading

Use `parse_vtu()` from `src/cfd/vtu_parser.py` - it handles both ASCII and binary formats.

## Convergence Settings

| Setting | Euler | RANS |
|---------|-------|------|
| CFL | 0.1 | 0.1 |
| MUSCL | NO | NO |
| Iterations | 5000 | 5000 |
| Convergence | RMS_DENSITY < -6 | RMS_DENSITY + RMS_TKE < -6 |

**RANS requires proper freestream initialization:**
```
FREESTREAM_PRESSURE= 10000000.0
FREESTREAM_TEMPERATURE= 3500.0
MACH_NUMBER= 0.01
```

## Matplotlib Plotting

Use `tricontourf` for filled contours, not `scatter` with dots:

```python
from matplotlib.tri import Triangulation

triang = Triangulation(coords[:, 0], coords[:, 1])
contour = ax.tricontourf(triang, mach, levels=20, cmap='jet')
ax.tricontour(triang, mach, levels=20, colors='k', linewidths=0.3, alpha=0.5)
```

## Axisymmetric Simulation

The nozzle is rotationally symmetric. SU2's `AXISYMMETRIC=YES` flag solves the axisymmetric equations, which is equivalent to 3D but with a 2D mesh. The mesh shows only the top half; the bottom is the axis of symmetry.

## Validation Targets

| Metric | Target | Current |
|--------|--------|---------|
| Exit Mach error | < 5% | 4.14% (Euler) |
| Triple validation | < 5% | 1.31% |
| GCI | < 5% | PASSED |
| RANS vs Euler | ~20% | 21% |

## Conventions

- 4-space indent
- snake_case variables, PascalCase classes
- Type hints on all public functions
- No em dashes (use hyphens or "to")
- Portfolio theme: AK-Vortex Ocean dark
