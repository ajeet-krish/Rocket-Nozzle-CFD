"""Tests for flow distribution along nozzle."""
import pytest
import numpy as np
from nozzle.config import NozzleConfig
from nozzle.flow_distribution import compute_flow_distribution, FlowField


class TestFlowDistribution:
    """Test flow distribution computation."""

    def test_exit_mach_matches_isentropic(self):
        """Exit Mach should match isentropic prediction."""
        config = NozzleConfig(expansion_ratio=12.0)
        flow = compute_flow_distribution(config)

        # Isentropic exit Mach for epsilon=12, gamma=1.4
        from validation.isentropic import mach_from_area_ratio
        expected_mach = mach_from_area_ratio(12.0, 1.4)

        assert abs(flow.exit_mach - expected_mach) < 0.01, (
            f"Exit Mach {flow.exit_mach:.4f} should be close to "
            f"isentropic prediction {expected_mach:.4f}"
        )

    def test_throat_mach_is_sonic(self):
        """Mach at throat should be approximately 1.0."""
        config = NozzleConfig()
        flow = compute_flow_distribution(config)

        # Find throat (x closest to 0)
        throat_idx = np.argmin(np.abs(flow.x))
        assert abs(flow.mach[throat_idx] - 1.0) < 0.1, (
            f"Mach at throat should be ~1.0, got {flow.mach[throat_idx]:.4f}"
        )

    def test_pressure_decreases_along_nozzle(self):
        """Pressure should decrease from inlet to exit."""
        config = NozzleConfig()
        flow = compute_flow_distribution(config)

        # Pressure should be monotonically decreasing in diverging section
        diverging = flow.mach > 1.0
        if diverging.any():
            pressure_diverging = flow.pressure[diverging]
            assert all(
                pressure_diverging[i] >= pressure_diverging[i + 1]
                for i in range(len(pressure_diverging) - 1)
            ), "Pressure should decrease monotonically in diverging section"

    def test_temperature_decreases_along_nozzle(self):
        """Temperature should decrease from inlet to exit."""
        config = NozzleConfig()
        flow = compute_flow_distribution(config)

        # Temperature should be monotonically decreasing in diverging section
        diverging = flow.mach > 1.0
        if diverging.any():
            temp_diverging = flow.temperature[diverging]
            assert all(
                temp_diverging[i] >= temp_diverging[i + 1]
                for i in range(len(temp_diverging) - 1)
            ), "Temperature should decrease monotonically in diverging section"

    def test_velocity_increases_along_nozzle(self):
        """Velocity should increase from inlet to exit."""
        config = NozzleConfig()
        flow = compute_flow_distribution(config)

        # Velocity should be monotonically increasing in diverging section
        diverging = flow.mach > 1.0
        if diverging.any():
            vel_diverging = flow.velocity[diverging]
            assert all(
                vel_diverging[i] <= vel_diverging[i + 1]
                for i in range(len(vel_diverging) - 1)
            ), "Velocity should increase monotonically in diverging section"

    def test_flow_field_shape(self):
        """FlowField arrays should have consistent shapes."""
        config = NozzleConfig(num_points=100)
        flow = compute_flow_distribution(config)
        n = len(flow.x)
        assert len(flow.mach) == n
        assert len(flow.pressure) == n
        assert len(flow.temperature) == n
        assert len(flow.density) == n
        assert len(flow.velocity) == n

    def test_positive_pressures(self):
        """All pressures should be positive."""
        config = NozzleConfig()
        flow = compute_flow_distribution(config)
        assert np.all(flow.pressure > 0), "All pressures must be positive"

    def test_positive_temperatures(self):
        """All temperatures should be positive."""
        config = NozzleConfig()
        flow = compute_flow_distribution(config)
        assert np.all(flow.temperature > 0), "All temperatures must be positive"

    def test_positive_densities(self):
        """All densities should be positive."""
        config = NozzleConfig()
        flow = compute_flow_distribution(config)
        assert np.all(flow.density > 0), "All densities must be positive"

    def test_mach_increases_through_nozzle(self):
        """Mach should generally increase from subsonic inlet to supersonic exit."""
        config = NozzleConfig()
        flow = compute_flow_distribution(config)
        # Exit Mach should be > 1 (supersonic)
        assert flow.exit_mach > 1.0, (
            f"Exit Mach should be supersonic, got {flow.exit_mach:.4f}"
        )

    def test_custom_total_conditions(self):
        """Flow should respect custom total conditions."""
        config = NozzleConfig()
        p0 = 5e6
        T0 = 3000.0
        flow = compute_flow_distribution(
            config, total_pressure=p0, total_temperature=T0,
        )
        # Inlet pressure should be less than p0 (subsonic but not zero Mach)
        assert flow.pressure[0] < p0
        # Exit pressure should be well below chamber
        assert flow.exit_pressure < p0 * 0.01

    def test_exit_pressure_below_chamber(self):
        """Exit pressure should be much lower than chamber pressure."""
        config = NozzleConfig(expansion_ratio=12.0)
        flow = compute_flow_distribution(config)
        assert flow.exit_pressure < 0.1 * 10e6, (
            f"Exit pressure {flow.exit_pressure:.0f} should be much less than "
            f"chamber pressure {10e6:.0f}"
        )
