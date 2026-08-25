# Rocket Nozzle CFD

Compressible CFD analysis of converging-diverging (de Laval) rocket nozzles using SU2, with triple validation against isentropic theory and Method of Characteristics.

**Portfolio:** [ajeet-krish.github.io/rocket-nozzle-cfd](https://ajeet-krish.github.io/rocket-nozzle-cfd)
**GitHub:** [github.com/ajeet-krish/rocket-nozzle-cfd](https://github.com/ajeet-krish/rocket-nozzle-cfd)

## Overview

This project simulates compressible flow through a converging-diverging rocket nozzle using SU2 CFD. The pipeline generates a parametric Rao parabolic bell nozzle contour, creates a structured O-grid mesh with Gmsh, runs SU2 Euler and RANS simulations, and validates results against three independent methods:

1. **Isentropic analytical relations** (closed-form equations)
2. **Method of Characteristics** (classical supersonic design method)
3. **SU2 CFD** (finite-volume Euler/RANS solver)

The project sweeps expansion ratio (4-20), chamber pressure (5-50 MPa), and throat radius (0.01-0.1 m) to build an aerodynamic database of 16 nozzle configurations.

## Reference Case

| Parameter | Value |
|-----------|-------|
| Expansion ratio (Ae/At) | 12 |
| Chamber pressure (Pc) | 10 MPa |
| Throat radius (R*) | 0.05 m |
| Chamber temperature (T0) | 3500 K |
| Gas | Air (gamma=1.4, R=287.058 J/(kg*K)) |
| Target exit Mach | 4.13 (isentropic prediction) |

## Methodology

### Nozzle Geometry

The nozzle contour uses a Rao parabolic bell approximation (Sutton & Biblarz, "Rocket Propulsion Elements"). The diverging section is a quadratic Bezier curve with:
- Throat wall angle: 30 degrees
- Exit wall angle: 0 degrees (parallel to axis)
- 80% of ideal bell length

### Mesh Generation

Structured O-grid mesh generated using Gmsh transfinite meshing:
- 4 zones: converging, throat, diverging, plume
- 200 axial cells, 80 normal cells
- First cell height: 1e-6 m (y+ < 1 for RANS)
- Growth ratio: 1.15 (geometric progression)
- Downstream plume: 30*R_throat for shock diamond capture

### CFD Solver

**Euler (inviscid):**
- SOLVER= EULER, AXISYMMETRIC= YES
- ROE flux scheme with MUSCL reconstruction
- CFL=5.0, 5000 iterations
- Inlet: total conditions (Pc=10 MPa, T0=3500K)
- Outlet: static pressure (101325 Pa)

**RANS (viscous):**
- SOLVER= RANS, KIND_TURB_MODEL= SST
- Low-Re wall treatment (y+ < 1)
- Adiabatic wall boundary conditions
- CFL adaptation (0.1 to 1.5)

### Validation

Triple validation methodology:
1. **Isentropic relations**: Closed-form area-Mach relation, pressure/temperature ratios
2. **Method of Characteristics**: 1D approximation using isentropic area-Mach at each contour point
3. **SU2 CFD**: Finite-volume Euler/RANS with ROE scheme

Grid Convergence Index (GCI) per ASME V&V 20-2009:
- 3 mesh levels: coarse (~4K), medium (~16K), fine (~64K cells)
- Refinement ratio: r=2
- Safety factor: Fs=1.25

## Results

### Validation Targets

| Metric | Target | Source |
|--------|--------|--------|
| Exit Mach error (SU2 vs isentropic) | < 1% | Anderson, Modern Compressible Flow |
| Thrust coefficient error | < 3% | Sutton, Rocket Propulsion Elements |
| MoC Mach distribution | < 2% | Shapiro, Dynamics of Compressible Flow |
| GCI (mesh convergence) | < 5% | ASME V&V 20-2009 |

### Parametric Sweeps

| Sweep | Parameter | Values | Fixed Parameters |
|-------|-----------|--------|-----------------|
| 1 | Expansion ratio | 4, 8, 12, 16, 20 | Pc=10 MPa, R*=0.05m |
| 2 | Chamber pressure | 5, 10, 20, 50 MPa | epsilon=12, R*=0.05m |
| 3 | Throat radius | 0.01, 0.025, 0.05, 0.1 m | epsilon=12, Pc=10 MPa |

Total: 16 SU2 runs (15 sweep + 1 reference)

## Project Structure

```
rocket-nozzle-cfd/
  pyproject.toml              # uv managed, Python >=3.13
  src/
    nozzle/                   # Geometry generation
      config.py               # NozzleConfig dataclass
      geometry.py             # Rao bell contour (Bezier)
    cfd/                      # SU2 mesh and solver
      config.py               # SU2NozzleConfig
      mesh.py                 # Gmsh O-grid generator
      mesh_config.py          # MeshConfig dataclass
      mesh_quality.py         # Quality metrics
      rans_config.py          # SU2RANSConfig (SST)
      solver.py               # SU2 subprocess runner
      vtu_parser.py           # VTU file parser
    validation/               # Analytical validation
      isentropic.py           # Isentropic relations
      moc_solver.py           # Method of Characteristics
      moc_config.py           # MoC configuration
      compare.py              # 2-way comparison
      triple.py               # 3-way comparison
      gci.py                  # Grid Convergence Index
    sweep/                    # Parametric sweeps
      config.py               # SweepConfig
      runner.py               # Sweep orchestration
      results.py              # SweepCaseResult
      plotter.py              # Parametric plots
    viz/                      # Visualization
      postprocessing.py       # Wall pressure, shock diamonds
      comparison.py           # Euler vs RANS plots
  tests/                      # 232 tests
  docs/                       # Portfolio HTML site
  run_phase0.py               # Phase 0: Spike
  run_phase3.py               # Phase 3: Euler reference
  run_phase4.py               # Phase 4: RANS + post-processing
  run_phase6.py               # Phase 6: Sweeps + GCI
```

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Solver | SU2 v8.0+ | Compressible flow, axisymmetric flag, proven pipeline |
| Mesh | Gmsh structured O-grid | Body-fitted, shock-aligned, native .su2 export |
| Contour | Rao parabolic bell (Sutton & Biblarz) | Industry standard, ~50 lines of code |
| Post-processing | ParaView + matplotlib | Publication-quality visualization |
| Portfolio | Static HTML (AK-Vortex theme) | Consistent with existing portfolio |
| Testing | pytest (232 tests) | Comprehensive validation coverage |

## How to Run

```bash
# Install dependencies
uv sync

# Run Phase 0 spike (validates SU2 convergence)
uv run python run_phase0.py

# Run Phase 3 Euler reference case
uv run python run_phase3.py

# Run Phase 4 RANS + post-processing
uv run python run_phase4.py

# Run Phase 6 parametric sweeps + GCI
uv run python run_phase6.py

# Run all tests
uv run pytest tests/ -v
```

## References

- Anderson, J.D. "Modern Compressible Flow" (isentropic relations)
- Sutton, G.P. & Biblarz, O. "Rocket Propulsion Elements" (nozzle design)
- Shapiro, A.H. "The Dynamics and Thermodynamics of Compressible Fluid Flow" (MoC)
- Roache, P.J. "Verification and Validation in Computational Science" (GCI)
- ASME V&V 20-2009 (Grid Convergence Index standard)
- SU2 Documentation: https://su2code.github.io/

## License

MIT License
