"""Tests for isentropic flow relations."""
import math
import pytest
from validation.isentropic import (
    area_mach_relation,
    exit_mach_from_area_ratio,
    total_to_static_pressure,
    total_to_static_temperature,
    choked_mass_flow_rate,
)


class TestAreaMachRelation:
    """Tests for the area-Mach number relation A/A*(M)."""

    def test_sonic_condition(self):
        """A/A* at M=1 should be exactly 1.0."""
        result = area_mach_relation(1.0, gamma=1.4)
        assert result == pytest.approx(1.0, abs=1e-12), (
            f"A/A* at M=1 should be 1.0, got {result}"
        )

    def test_supersonic_expansion(self):
        """A/A* at M=3 should be significantly > 1."""
        result = area_mach_relation(3.0, gamma=1.4)
        assert result > 1.0, f"A/A* at M=3 should be > 1, got {result}"
        # Known value: A/A*(M=3, gamma=1.4) ~ 4.2346
        assert result == pytest.approx(4.2346, abs=0.01), (
            f"A/A* at M=3 should be ~4.2346, got {result}"
        )

    def test_subsonic_deceleration(self):
        """A/A* at M=0.5 should be > 1 (diffuser regime)."""
        result = area_mach_relation(0.5, gamma=1.4)
        assert result > 1.0, f"A/A* at M=0.5 should be > 1, got {result}"

    def test_high_mach(self):
        """A/A* should increase monotonically for M > 1."""
        m1 = area_mach_relation(2.0, gamma=1.4)
        m2 = area_mach_relation(4.0, gamma=1.4)
        m3 = area_mach_relation(6.0, gamma=1.4)
        assert m1 < m2 < m3, (
            f"A/A* should increase with Mach: M=2:{m1}, M=4:{m2}, M=6:{m3}"
        )

    def test_zero_mach_returns_inf(self):
        """A/A* at M=0 should return inf (area ratio is infinite at stagnation)."""
        result = area_mach_relation(0.0, gamma=1.4)
        assert result == float('inf'), f"A/A* at M=0 should be inf, got {result}"

    def test_negative_mach_returns_inf(self):
        """Negative Mach should return inf."""
        result = area_mach_relation(-1.0, gamma=1.4)
        assert result == float('inf'), f"A/A* at M<0 should be inf, got {result}"

    def test_different_gamma(self):
        """Verify relation works with non-standard gamma."""
        result_1_3 = area_mach_relation(1.0, gamma=1.3)
        result_1_4 = area_mach_relation(1.0, gamma=1.4)
        result_1_67 = area_mach_relation(1.0, gamma=1.67)
        # At M=1, all should give 1.0 regardless of gamma
        assert result_1_3 == pytest.approx(1.0, abs=1e-12)
        assert result_1_4 == pytest.approx(1.0, abs=1e-12)
        assert result_1_67 == pytest.approx(1.0, abs=1e-12)


class TestExitMachFromAreaRatio:
    """Tests for solving exit Mach from area ratio."""

    def test_epsilon_12_exit_mach(self):
        """For epsilon=12, gamma=1.4, exit Mach should be approximately 4.13."""
        M_exit = exit_mach_from_area_ratio(12.0, gamma=1.4)
        assert M_exit == pytest.approx(4.13, abs=0.05), (
            f"Exit Mach for epsilon=12 should be ~4.13, got {M_exit}"
        )

    def test_epsilon_1_sonic(self):
        """For epsilon=1 (no area change), exit Mach should be 1.0."""
        M_exit = exit_mach_from_area_ratio(1.0, gamma=1.4)
        assert M_exit == pytest.approx(1.0, abs=0.01), (
            f"Exit Mach for epsilon=1 should be 1.0, got {M_exit}"
        )

    def test_supersonic_branch(self):
        """Solved Mach should always be >= 1 (supersonic branch)."""
        for epsilon in [1.0, 2.0, 5.0, 12.0, 50.0]:
            M_exit = exit_mach_from_area_ratio(epsilon, gamma=1.4)
            assert M_exit >= 1.0, (
                f"Exit Mach for epsilon={epsilon} should be >= 1, got {M_exit}"
            )

    def test_roundtrip_consistency(self):
        """A/A*(M_exit) should recover the original epsilon."""
        epsilon = 12.0
        M_exit = exit_mach_from_area_ratio(epsilon, gamma=1.4)
        recovered = area_mach_relation(M_exit, gamma=1.4)
        assert recovered == pytest.approx(epsilon, rel=1e-6), (
            f"Roundtrip failed: epsilon={epsilon}, M_exit={M_exit}, "
            f"A/A*(M_exit)={recovered}"
        )

    def test_large_area_ratio(self):
        """Very large area ratios should still converge."""
        M_exit = exit_mach_from_area_ratio(100.0, gamma=1.4)
        assert M_exit > 3.0, (
            f"Exit Mach for epsilon=100 should be > 3, got {M_exit}"
        )


class TestTotalToStaticPressure:
    """Tests for total-to-static pressure ratio."""

    def test_stagnation_pressure(self):
        """p0/p at M=0 should be 1.0."""
        result = total_to_static_pressure(0.0, gamma=1.4)
        assert result == pytest.approx(1.0, abs=1e-12), (
            f"p0/p at M=0 should be 1.0, got {result}"
        )

    def test_sonic_pressure_ratio(self):
        """p0/p at M=1 should be known value (~1.893 for gamma=1.4)."""
        result = total_to_static_pressure(1.0, gamma=1.4)
        # Exact: (1 + 0.2)^3.5 = 1.8929...
        assert result == pytest.approx(1.8929, abs=0.001), (
            f"p0/p at M=1 should be ~1.893, got {result}"
        )

    def test_monotonic_increase(self):
        """p0/p should increase monotonically with Mach."""
        values = [total_to_static_pressure(m, gamma=1.4) for m in [0, 0.5, 1, 2, 3]]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1], (
                f"p0/p should increase: M values gave {values}"
            )


class TestTotalToStaticTemperature:
    """Tests for total-to-static temperature ratio."""

    def test_stagnation_temperature(self):
        """T0/T at M=0 should be 1.0."""
        result = total_to_static_temperature(0.0, gamma=1.4)
        assert result == pytest.approx(1.0, abs=1e-12)

    def test_sonic_temperature_ratio(self):
        """T0/T at M=1 should be 1.2 for gamma=1.4."""
        result = total_to_static_temperature(1.0, gamma=1.4)
        assert result == pytest.approx(1.2, abs=1e-12)


class TestChokedMassFlowRate:
    """Tests for choked mass flow rate calculation."""

    def test_positive_mass_flow(self):
        """Mass flow rate should be positive for valid inputs."""
        mdot = choked_mass_flow_rate(
            throat_area=math.pi * 0.05**2,
            total_pressure=10e6,
            total_temperature=3500.0,
            gamma=1.4,
            gas_constant=287.058,
        )
        assert mdot > 0, f"Mass flow rate should be positive, got {mdot}"

    def test_scaling_with_throat_area(self):
        """Mass flow should scale linearly with throat area."""
        A1 = math.pi * 0.05**2
        A2 = 2.0 * A1
        mdot1 = choked_mass_flow_rate(A1, 10e6, 3500.0)
        mdot2 = choked_mass_flow_rate(A2, 10e6, 3500.0)
        assert mdot2 == pytest.approx(2.0 * mdot1, rel=1e-10), (
            f"Mass flow should double when area doubles: {mdot1} vs {mdot2}"
        )

    def test_scaling_with_pressure(self):
        """Mass flow should scale linearly with total pressure."""
        mdot1 = choked_mass_flow_rate(0.001, 5e6, 3500.0)
        mdot2 = choked_mass_flow_rate(0.001, 10e6, 3500.0)
        assert mdot2 == pytest.approx(2.0 * mdot1, rel=1e-10)
