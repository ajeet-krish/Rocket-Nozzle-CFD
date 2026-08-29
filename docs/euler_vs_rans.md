# Euler vs RANS Comparison

## Exit Mach Number

| Engine | Euler (Inviscid) | RANS SST (Viscous) | Difference |
|--------|------------------|---------------------|------------|
| Merlin 1D | 4.4416 | 4.4501 | 0.0085 (0.19%) |
| Raptor SL | 5.4761 | 4.8830 | 0.5931 (10.83%) |
| RS-25 | 6.4442 | 5.8567 | 0.5875 (9.12%) |
| RL10B-2 | 7.7090 | 6.5617 | 1.1473 (14.89%) |

## Discussion

The RANS simulation includes viscous effects (boundary layer) that are absent in the Euler simulation. This typically results in:
- Slightly lower exit Mach number due to boundary layer displacement effect
- Thinner effective flow area at the exit
- Lower thrust coefficient due to viscous losses

The viscous effect scales with the expansion ratio: low-ratio nozzles (Merlin, epsilon=16) show minimal viscous loss (~0.2%), while high-ratio nozzles (RL10B-2, epsilon=285) show significant viscous degradation (~15%).

## Boundary Layer Effects

The boundary layer develops along the nozzle wall, creating a velocity gradient from zero at the wall (no-slip) to the freestream value. This reduces the effective flow area, causing:
- Slight deceleration of the core flow
- Reduced mass flow rate
- Lower exit Mach number

The difference between Euler and RANS results indicates the magnitude of viscous effects in the nozzle.
