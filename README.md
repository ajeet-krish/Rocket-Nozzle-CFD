# Compressible Flow Analysis of Converging-Diverging Rocket Nozzles

## Abstract

Comprehensive CFD pipeline for analyzing compressible flow through converging-diverging rocket nozzles. Features parametric geometry generation, structured mesh generation, Euler and RANS simulations with SU2 v8.4.0, and triple validation against isentropic theory and Method of Characteristics.

Four real rocket engine presets: SpaceX Merlin 1D (16:1), Raptor SL (34:1), RS-25 (77.5:1), and RL10B-2 (285:1). Per-engine run files execute the complete pipeline: geometry visualization, mesh generation, Euler/RANS simulation, plume with shock diamonds, and parametric sweeps.

## Nozzle Models

| Engine | Application | Expansion Ratio | Throat (mm) | Exit (mm) | Pc (MPa) | Theta_n |
|--------|-------------|-----------------|-------------|-----------|----------|---------|
| Merlin 1D | Falcon 9 first stage | 16:1 | 165 | 660 | 9.7 | 30 deg |
| Raptor SL | Starship Super Heavy | 34:1 | 165 | 960 | 33.0 | 25 deg |
| RS-25 | Space Shuttle / SLS | 77.5:1 | 272 | 2400 | 20.6 | 30 deg |
| RL10B-2 | Delta IV upper stage | 285:1 | 154 | 2600 | 4.2 | 25 deg |

## Validation Summary

| Engine | Isentropic Mach | Euler Mach | Euler Error | RANS Mach | Euler vs RANS | Back Pressure |
|--------|----------------|------------|-------------|-----------|---------------|---------------|
| Merlin 1D | 4.4593 | 4.4717 | 0.28% | 4.2547 | 4.85% | Sea level |
| Raptor SL | 5.3933 | 5.1431 | 4.64% | 4.8180 | 6.32% | Sea level |
| RS-25 | 6.5463 | 5.9747 | 8.73% | 5.2510 | 12.1% | Vacuum |
| RL10B-2 | 8.7362 | -- | -- | -- | -- | Vacuum |

## Geometry

### Merlin 1D

| 2D Contour | 3D Surface |
|------------|------------|
| ![Merlin 2D](docs/assets/images/merlin-1d/geometry/merlin-1d_geometry.png) | ![Merlin 3D](docs/assets/images/merlin-1d/geometry/merlin-1d_3d.png) |

### Raptor SL

| 2D Contour | 3D Surface |
|------------|------------|
| ![Raptor 2D](docs/assets/images/raptor-sl/geometry/raptor-sl_geometry.png) | ![Raptor 3D](docs/assets/images/raptor-sl/geometry/raptor-sl_3d.png) |

### RS-25

| 2D Contour | 3D Surface |
|------------|------------|
| ![RS-25 2D](docs/assets/images/rs-25/geometry/rs-25_geometry.png) | ![RS-25 3D](docs/assets/images/rs-25/geometry/rs-25_3d.png) |

### RL10B-2

| 2D Contour | 3D Surface |
|------------|------------|
| ![RL10B-2 2D](docs/assets/images/rl10B-2/geometry/rl10B-2_geometry.png) | ![RL10B-2 3D](docs/assets/images/rl10B-2/geometry/rl10B-2_3d.png) |

## Simulation Results

### Merlin 1D

| Euler Mach Contour | Plume Shock Diamonds |
|--------------------|---------------------|
| ![Merlin Euler](docs/assets/images/merlin-1d/euler/mach_contour.png) | ![Merlin Plume](docs/assets/images/merlin-1d/plume/shock_diamonds.png) |

### Raptor SL

| Euler Mach Contour | Plume Shock Diamonds |
|--------------------|---------------------|
| ![Raptor Euler](docs/assets/images/raptor-sl/euler/mach_contour.png) | ![Raptor Plume](docs/assets/images/raptor-sl/plume/shock_diamonds.png) |

### RS-25

| Euler Mach Contour | Plume Shock Diamonds |
|--------------------|---------------------|
| ![RS-25 Euler](docs/assets/images/rs-25/euler/mach_contour.png) | ![RS-25 Plume](docs/assets/images/rs-25/plume/shock_diamonds.png) |

## Parametric Sweeps

### Merlin 1D

| Exit Mach vs Expansion Ratio | Exit Mach vs Chamber Pressure |
|------------------------------|-------------------------------|
| ![Sweep Epsilon](docs/assets/images/merlin-1d/sweeps/sweep_mach_vs_epsilon.png) | ![Sweep Pc](docs/assets/images/merlin-1d/sweeps/sweep_mach_vs_pc.png) |

## Methodology

### Nozzle Geometry
Rao parabolic bell with:
- Entrant arc: 1.5*Rt radius circular arc
- Exit arc: 0.382*Rt radius circular arc
- Bell: Quadratic Bezier curve
- Configurable theta_n and theta_e

### Mesh Generation
Structured O-grid via Gmsh transfinite meshing:
- Per-engine resolution: 40x20 (Merlin/Raptor) to 120x60 (RL10B-2)
- Conformal plume extension for shock diamond capture
- Spline wall curve through geometry key points

### CFD Solver
- **Euler**: SU2 EULER, AXISYMMETRIC=YES, ROE flux, first-order
- **RANS**: SU2 RANS SST k-omega, adiabatic wall
- **Plume**: Farfield BC with conformal mesh interface

### Validation
Triple validation: isentropic relations, Method of Characteristics, SU2 CFD
GCI per ASME V&V 20-2009

## Project Structure

```
src/
  nozzle/           # Geometry (config, presets, contour)
  cfd/              # SU2 mesh & solver
  validation/       # Isentropic, MoC, GCI
  sweep/            # Parametric sweeps
  viz/              # Mach contour, shock diamonds
  pipeline/         # Per-engine pipeline orchestration
docs/               # Portfolio HTML site
run_merlin.py       # Merlin 1D: all steps
run_raptor.py       # Raptor SL: all steps
run_rs25.py         # RS-25: all steps
run_rl10b2.py       # RL10B-2: all steps
run_all.py          # All engines
run_euler_spike.py  # Quick convergence test
```

## How to Run

```bash
uv sync

# Per-engine pipeline
uv run python run_merlin.py                  # All steps
uv run python run_merlin.py --step geometry  # Just geometry
uv run python run_merlin.py --step euler     # Just Euler

# All engines
uv run python run_all.py

# Quick test
uv run python run_euler_spike.py

# Tests
uv run pytest tests/ -v
```

## References

- Anderson, J.D. "Modern Compressible Flow"
- Sutton, G.P. & Biblarz, O. "Rocket Propulsion Elements"
- Shapiro, A.H. "The Dynamics and Thermodynamics of Compressible Fluid Flow"
- ASME V&V 20-2009 (Grid Convergence Index)
- SU2 Documentation: https://su2code.github.io/
