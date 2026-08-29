# Compressible Flow Analysis of Converging-Diverging Rocket Nozzles

## Abstract

Comprehensive CFD pipeline for analyzing compressible flow through converging-diverging rocket nozzles. Features parametric geometry generation, structured mesh generation, Euler and RANS simulations with SU2 v8.4.0, and triple validation against isentropic theory and Method of Characteristics.

Four real rocket engine presets: SpaceX Merlin 1D (16:1), Raptor SL (34:1), RS-25 (77.5:1), and RL10B-2 (285:1). Per-engine pipeline: geometry visualization, mesh generation, Euler/RANS CFD, plume with shock diamonds, and parametric sweeps.

## Nozzle Models

| Engine | Application | Expansion Ratio | Throat (mm) | Exit (mm) | Pc (MPa) |
|--------|-------------|-----------------|-------------|-----------|----------|
| Merlin 1D | Falcon 9 first stage | 16:1 | 165 | 660 | 9.7 |
| Raptor SL | Starship Super Heavy | 34:1 | 165 | 960 | 33.0 |
| RS-25 | Space Shuttle / SLS | 77.5:1 | 272 | 2400 | 20.6 |
| RL10B-2 | Delta IV upper stage | 285:1 | 154 | 2600 | 4.2 |

## Validation Summary

| Engine | Isentropic Mach | Euler Mach | Euler Error | RANS Mach | Euler vs RANS | Back Pressure |
|--------|-----------------|------------|-------------|-----------|---------------|---------------|
| Merlin 1D | 4.4593 | 4.3110 | 3.33% | 3.8286 | 11.19% | Sea level |
| Raptor SL | 5.3933 | 5.4761 | 1.54% | 4.8830 | 10.83% | Sea level |
| RS-25 | 6.5463 | 6.4442 | 1.56% | 5.8567 | 9.12% | Vacuum |
| RL10B-2 | 8.7362 | 7.7090 | 11.76% | 6.5617 | 14.88% | Vacuum |

## Performance Metrics

| Engine | Exit Mach | CF | Isp (s) | Ve (m/s) | Thrust (kN) | Pc (MPa) | Area Ratio |
|--------|-----------|-----|---------|----------|-------------|----------|------------|
| Merlin 1D | 4.31 | 1.511 | 228.8 | 2388 | 313 | 9.7 | 16:1 |
| Raptor SL | 5.48 | 1.610 | 240.4 | 2455 | 1136 | 33.0 | 34:1 |
| RS-25 | 6.44 | 1.743 | 262.7 | 2530 | 2086 | 20.6 | 77.5:1 |
| RL10B-2 | 7.71 | 1.770 | 209.5 | 2019 | 139 | 4.2 | 285:1 |

### Parameter Definitions

- **Exit Mach (Me)**: Ratio of exhaust velocity to speed of sound at nozzle exit. Higher Mach = faster exhaust. Range: 4-9 for rocket nozzles.

- **Thrust Coefficient (CF)**: Dimensionless efficiency of pressure-to-thrust conversion. CF = F / (Pc * A*). Typical: 1.2-2.0.

- **Specific Impulse (Isp)**: Propellant efficiency in seconds. Isp = F / (mdot * g0). Sea-level: 200-350s; vacuum: 400-460s (LH2/LOX).

- **Exit Velocity (Ve)**: Exhaust velocity at exit plane. Ve = Me * sqrt(gamma * R * Te).

- **Thrust Force**: Total force including momentum and pressure thrust.

---

## SpaceX Merlin 1D

*Falcon 9 first stage: epsilon=16, R*=82.5mm, Pc=9.7 MPa, sea level*

### Nozzle Geometry

| 2D Annotated Profile | 3D Revolved Surface |
|----------------------|---------------------|
| ![Merlin 1D 2D Geometry](docs/assets/images/merlin-1d/geometry/merlin-1d_geometry.png) | ![Merlin 1D 3D Geometry](docs/assets/images/merlin-1d/geometry/merlin-1d_3d.png) |

### Nozzle Mesh

![Merlin Mesh](docs/assets/images/merlin-1d/mesh/merlin-mesh.png)

### Euler Simulation (Inviscid)

| Mach Contour | Pressure Contour | Velocity Contour |
|--------------|------------------|------------------|
| ![Euler Mach](docs/assets/images/merlin-1d/euler/mach_contour.png) | ![Euler Pressure](docs/assets/images/merlin-1d/euler/pressure_contour.png) | ![Euler Velocity](docs/assets/images/merlin-1d/euler/velocity_contour.png) |

> Euler simulation (M_exit=4.31, 3.33% error). Inviscid flow captures shock structure and expansion fans without boundary layer effects.

### RANS Simulation (Viscous)

| Mach Contour | Pressure Contour | Velocity Contour |
|--------------|------------------|------------------|
| ![RANS Mach](docs/assets/images/merlin-1d/rans/mach_contour_rans.png) | ![RANS Pressure](docs/assets/images/merlin-1d/rans/pressure_contour_rans.png) | ![RANS Velocity](docs/assets/images/merlin-1d/rans/velocity_contour_rans.png) |

> RANS SST simulation (M_exit=3.83, 11.19% vs Euler). Viscous boundary layer reduces effective flow area, lowering exit Mach.

### Shock Diamonds & Plume

![Shock Diamonds](docs/assets/images/merlin-1d/plume/shock_diamonds.png)

> Shock diamond pattern in exhaust plume from density gradient visualization.

---

## SpaceX Raptor SL

*Starship Super Heavy: epsilon=34, R*=82.5mm, Pc=33.0 MPa, sea level*

### Nozzle Geometry

| 2D Annotated Profile | 3D Revolved Surface |
|----------------------|---------------------|
| ![Raptor SL 2D Geometry](docs/assets/images/raptor-sl/geometry/raptor-sl_geometry.png) | ![Raptor SL 3D Geometry](docs/assets/images/raptor-sl/geometry/raptor-sl_3d.png) |

### Nozzle Mesh

![Raptor Mesh](docs/assets/images/raptor-sl/mesh/raptor-mesh.png)

### Euler Simulation (Inviscid)

| Mach Contour | Pressure Contour | Velocity Contour |
|--------------|------------------|------------------|
| ![Euler Mach](docs/assets/images/raptor-sl/euler/mach_contour.png) | ![Euler Pressure](docs/assets/images/raptor-sl/euler/pressure_contour.png) | ![Euler Velocity](docs/assets/images/raptor-sl/euler/velocity_contour.png) |

> Euler simulation (M_exit=5.48, 1.54% error). Highest chamber pressure (33 MPa) of any operational engine.

### RANS Simulation (Viscous)

| Mach Contour | Pressure Contour | Velocity Contour |
|--------------|------------------|------------------|
| ![RANS Mach](docs/assets/images/raptor-sl/rans/mach_contour_rans.png) | ![RANS Pressure](docs/assets/images/raptor-sl/rans/pressure_contour_rans.png) | ![RANS Velocity](docs/assets/images/raptor-sl/rans/velocity_contour_rans.png) |

> RANS SST simulation (M_exit=4.88, 10.83% vs Euler). Full-flow staged combustion cycle effects captured.

### Shock Diamonds & Plume

![Shock Diamonds](docs/assets/images/raptor-sl/plume/shock_diamonds.png)

> Shock diamond pattern from Raptor SL exhaust. Exit Mach 5.23 (plume), 3.10% error.

---

## RS-25 (Space Shuttle / SLS)

*Space Shuttle Main Engine: epsilon=77.5, R*=136mm, Pc=20.6 MPa, vacuum*

### Nozzle Geometry

| 2D Annotated Profile | 3D Revolved Surface |
|----------------------|---------------------|
| ![RS-25 2D Geometry](docs/assets/images/rs-25/geometry/rs-25_geometry.png) | ![RS-25 3D Geometry](docs/assets/images/rs-25/geometry/rs-25_3d.png) |

### Nozzle Mesh

![RS-25 Mesh](docs/assets/images/rs-25/mesh/rs25-mesh.png)

### Euler Simulation (Inviscid)

| Mach Contour | Pressure Contour | Velocity Contour |
|--------------|------------------|------------------|
| ![Euler Mach](docs/assets/images/rs-25/euler/mach_contour.png) | ![Euler Pressure](docs/assets/images/rs-25/euler/pressure_contour.png) | ![Euler Velocity](docs/assets/images/rs-25/euler/velocity_contour.png) |

> Euler simulation (M_exit=6.44, 1.56% error). Simulated at near-vacuum (100 Pa) as RS-25 is designed for vacuum operation.

### RANS Simulation (Viscous)

| Mach Contour | Pressure Contour | Velocity Contour |
|--------------|------------------|------------------|
| ![RANS Mach](docs/assets/images/rs-25/rans/mach_contour_rans.png) | ![RANS Pressure](docs/assets/images/rs-25/rans/pressure_contour_rans.png) | ![RANS Velocity](docs/assets/images/rs-25/rans/velocity_contour_rans.png) |

> RANS SST simulation (M_exit=5.86, 9.12% vs Euler). Long diverging section amplifies viscous effects.

### Shock Diamonds & Plume

![Shock Diamonds](docs/assets/images/rs-25/plume/shock_diamonds.png)

> RS-25 plume structure at vacuum conditions. Exit Mach 5.73 (plume), 12.43% error.

---

## RL10B-2 (Delta IV Upper Stage)

*Delta IV upper stage: epsilon=285, R*=77mm, Pc=4.2 MPa, vacuum*

### Nozzle Geometry

| 2D Annotated Profile | 3D Revolved Surface |
|----------------------|---------------------|
| ![RL10B-2 2D Geometry](docs/assets/images/rl10B-2/geometry/rl10B-2_geometry.png) | ![RL10B-2 3D Geometry](docs/assets/images/rl10B-2/geometry/rl10B-2_3d.png) |

### Nozzle Mesh

![RL10B-2 Mesh](docs/assets/images/rl10B-2/mesh/rl10b2-mesh.png)

### Euler Simulation (Inviscid)

| Mach Contour | Pressure Contour | Velocity Contour |
|--------------|------------------|------------------|
| ![Euler Mach](docs/assets/images/rl10B-2/euler/mach_contour.png) | ![Euler Pressure](docs/assets/images/rl10B-2/euler/pressure_contour.png) | ![Euler Velocity](docs/assets/images/rl10B-2/euler/velocity_contour.png) |

> Euler simulation (M_exit=7.71, 11.76% error). Extreme 285:1 expansion ratio creates challenges for CFD convergence.

### RANS Simulation (Viscous)

| Mach Contour | Pressure Contour | Velocity Contour |
|--------------|------------------|------------------|
| ![RANS Mach](docs/assets/images/rl10B-2/rans/mach_contour_rans.png) | ![RANS Pressure](docs/assets/images/rl10B-2/rans/pressure_contour_rans.png) | ![RANS Velocity](docs/assets/images/rl10B-2/rans/velocity_contour_rans.png) |

> RANS SST simulation (M_exit=6.56, 14.88% vs Euler). Extreme expansion ratio produces significant boundary layer effects.

### Shock Diamonds & Plume

![Shock Diamonds](docs/assets/images/rl10B-2/plume/shock_diamonds.png)

> RL10B-2 plume structure. Extreme expansion ratio creates different flow pattern compared to sea-level nozzles.

---

## Parametric Sweeps

Sweeps vary one parameter while holding others constant, performed on the generic nozzle (epsilon=16, R*=50mm).

| Sweep | Parameter | Values | Fixed |
|-------|-----------|--------|-------|
| 1 | Expansion ratio | 4, 8, 12, 16, 20 | Pc=9.7 MPa |
| 2 | Chamber pressure | 5, 10, 20, 50 MPa | epsilon=12 |
| 3 | Throat radius | 0.01, 0.025, 0.05, 0.1 m | epsilon=12 |

### Exit Mach vs Expansion Ratio

![Sweep Epsilon](docs/assets/images/merlin-1d/sweeps/sweep_mach_vs_epsilon.png)

> Exit Mach increases with expansion ratio following the isentropic area-Mach relation.

### Exit Mach vs Chamber Pressure

![Sweep Pc](docs/assets/images/merlin-1d/sweeps/sweep_mach_vs_pc.png)

> Exit Mach is independent of chamber pressure for calorically perfect gas.

### Exit Mach vs Throat Radius

![Sweep R*](docs/assets/images/merlin-1d/sweeps/sweep_mach_vs_rstar.png)

> Exit Mach is independent of absolute scale for geometrically similar nozzles.

---

## Methodology

### Nozzle Geometry
Rao parabolic bell with quadratic Bezier curve, circular entrant/exit arcs, configurable convergent angle and throat radius of curvature.

### Mesh Generation
Structured O-grid via Gmsh transfinite meshing with geometry-aware key points and Bump distribution for throat clustering.

| Engine | Mesh | CFL | Back Pressure |
|--------|------|-----|---------------|
| Merlin 1D | 40x20 | 0.1 | Sea level |
| Raptor SL | 50x25 | 0.1 | Sea level |
| RS-25 | 60x30 | 0.05 | Vacuum |
| RL10B-2 | 80x40 | 0.03 | Vacuum |

### CFD Solver
- **Euler**: SU2 EULER, AXISYMMETRIC=YES, ROE flux, first-order
- **RANS**: SU2 RANS SST k-omega, adiabatic wall, chamber freestream initialization

### Validation
Triple validation: isentropic relations, Method of Characteristics, SU2 CFD. GCI per ASME V&V 20-2009.

---

## Project Structure

```
rocket-nozzle-cfd/
  src/nozzle/          # Geometry (config, presets, contour)
  src/cfd/             # SU2 mesh & solver
  src/validation/      # Isentropic, MoC, GCI
  src/sweep/           # Parametric sweeps
  src/viz/             # Contour, convergence, annotated geometry, 3D surface
  src/pipeline/        # Per-engine pipeline orchestration
  src/pinn/            # PINN surrogate model
  tests/               # 368 tests
  docs/                # Portfolio HTML site
  run_merlin.py        # Merlin 1D: all steps
  run_raptor.py        # Raptor SL: all steps
  run_rs25.py          # RS-25: all steps
  run_rl10b2.py        # RL10B-2: all steps
  run_all.py           # All engines
  run_euler_spike.py   # Quick convergence test
  run_pinn.py          # PINN training/prediction
```

## How to Run

```bash
uv sync

# Per-engine pipeline
uv run python run_merlin.py                  # All steps
uv run python run_merlin.py --step geometry  # Just geometry
uv run python run_merlin.py --step euler     # Just Euler
uv run python run_merlin.py --step rans      # Just RANS

# All engines
uv run python run_all.py

# Tests
uv run pytest tests/ -v
```

## References

- Anderson, J.D. "Modern Compressible Flow"
- Sutton, G.P. & Biblarz, O. "Rocket Propulsion Elements"
- Shapiro, A.H. "The Dynamics and Thermodynamics of Compressible Fluid Flow"
- ASME V&V 20-2009 (Grid Convergence Index)
- SU2 Documentation: https://su2code.github.io/
