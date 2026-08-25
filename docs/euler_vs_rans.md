# Euler vs RANS Comparison

## Exit Mach Number

| Method | Exit Mach |
|--------|-----------|
| Euler (Inviscid) | 0.0000 |
| RANS SST (Viscous) | 0.0000 |
| Difference | 0.0000 (0.00%) |

## Discussion

The RANS simulation includes viscous effects (boundary layer) that are absent in the Euler simulation. This typically results in:
- Slightly lower exit Mach number due to boundary layer displacement effect
- Thinner effective flow area at the exit
- Lower thrust coefficient due to viscous losses

## Boundary Layer Effects

The boundary layer develops along the nozzle wall, creating a velocity gradient from zero at the wall (no-slip) to the freestream value. This reduces the effective flow area, causing:
- Slight deceleration of the core flow
- Reduced mass flow rate
- Lower exit Mach number

The difference between Euler and RANS results indicates the magnitude of viscous effects in the nozzle.
