# Rocket Nozzle CFD

Compressible CFD analysis of converging-diverging rocket nozzles using SU2, with triple validation against isentropic theory and Method of Characteristics.

## Quick Commands

```bash
# Run all tests (287 tests)
uv run pytest tests/ -v

# Per-engine pipeline (geometry + mesh + euler + rans + plume + sweep)
uv run python run_merlin.py                  # All steps
uv run python run_merlin.py --step geometry  # Just geometry plots
uv run python run_merlin.py --step euler     # Just Euler simulation

# Quick convergence test (~2 min)
uv run python run_euler_spike.py

# Run all engines in sequence
uv run python run_all.py
```

## Architecture

| Component | Location | Purpose |
|-----------|----------|---------|
| `src/nozzle/` | Geometry & physics | Nozzle contour, isentropic relations, presets |
| `src/cfd/` | SU2 mesh & solver | Gmsh mesh, SU2 config, RANS config, VTU parsing |
| `src/validation/` | Analytical validation | Isentropic, MoC, triple comparison, GCI |
| `src/sweep/` | Parametric sweeps | Sweep config, runner, results, plots |
| `src/viz/` | Visualization | Mach contour, shock diamonds, comparison |
| `src/pipeline/` | Per-engine pipeline | EngineConfig, pipeline stages orchestration |
| `tests/` | Test suite | 287 tests, pytest |
| `docs/` | Portfolio HTML site | AK-Vortex theme, 5 pages |
| `run_*.py` | Per-engine run files | 4 engine scripts + orchestrator + spike test |

## Key Interfaces

- `NozzleConfig` - Frozen dataclass for nozzle geometry
- `EngineConfig` - Per-engine CFD pipeline configuration
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

**Critical: Use geometry-aware key points, not index arithmetic.**

The mesh generator places key points at actual section transitions (entrant arc start, throat, exit arc end, bell transitions). Bump distribution clusters cells near the throat where curvature is highest.

```python
# Good: Geometry-aware key points
key_indices = [0, throat_idx - offset, throat_idx, throat_idx + offset, n_points//2, n_points - 1]

# Bad: Index arithmetic
key_indices = [0, n_points//10, throat_idx, n_points//2, n_points - 1]
```

**Mesh resolution:** Use 40x20 (800 elements) for Merlin/Raptor. Finer meshes can cause SU2 divergence for these geometries.

## Per-Engine Run Files

Each engine has a dedicated run file with `--step` flag:

| Engine | File | Mesh | CFL | Back Pressure |
|--------|------|------|-----|---------------|
| Merlin 1D | `run_merlin.py` | 40x20 | 0.1 | Sea level |
| Raptor SL | `run_raptor.py` | 40x20 | 0.1 | Sea level |
| RS-25 | `run_rs25.py` | 60x30 | 0.05 | Vacuum (100 Pa) |
| RL10B-2 | `run_rl10b2.py` | 80x40 | 0.03 | Vacuum (100 Pa) |

**Steps:** `geometry`, `mesh`, `euler`, `rans`, `plume`, `sweep`, `all`

## Output Structure

- **Plots** -> `docs/assets/images/{engine}/{step}/`
- **Artifacts** (VTU, mesh, config) -> `output/{engine}/{step}/`

## VTU Parsing

SU2 v8.4.0 outputs binary VTU files with appended data format. The parser must handle:
1. XML header parsing
2. Binary data extraction from appended section
3. Offset-based data array reading

Use `parse_vtu()` from `src/cfd/vtu_parser.py` - it handles both ASCII and binary formats.

## Convergence Settings

| Setting | Euler | RANS |
|---------|-------|------|
| CFL | 0.1 (Merlin/Raptor), 0.05 (RS-25), 0.03 (RL10B-2) | 0.05 (Merlin/Raptor), 0.03 (RS-25), 0.02 (RL10B-2) |
| MUSCL | NO | NO |
| Iterations | 5000 (Merlin/Raptor), 10000 (RS-25), 15000 (RL10B-2) | 10000 (Merlin/Raptor), 15000 (RS-25), 20000 (RL10B-2) |
| Convergence | RMS_DENSITY < -6 | RMS_DENSITY + RMS_TKE < -6 |

**RANS requires proper freestream initialization:**
```
FREESTREAM_PRESSURE= 10000000.0
FREESTREAM_TEMPERATURE= 3500.0
MACH_NUMBER= 0.01
```

## Validation Results

| Engine | Isentropic Mach | Euler Mach | Euler Error | RANS Mach | Notes |
|--------|----------------|------------|-------------|-----------|-------|
| Merlin 1D | 4.4593 | 4.4717 | 0.28% | 4.2547 | Sea level |
| Raptor SL | 5.3933 | 5.1431 | 4.64% | 4.8180 | Sea level |
| RS-25 | 6.5463 | 6.4055 | 2.15% | 5.2510 | Vacuum (100 Pa) |
| RL10B-2 | 8.7362 | 7.4913 | 14.25% | -- | Vacuum, extreme 285:1 ratio |

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

## Conventions

- 4-space indent
- snake_case variables, PascalCase classes
- Type hints on all public functions
- No em dashes (use hyphens or "to")
- Portfolio theme: AK-Vortex Ocean dark
