"""Tests for nozzle flow solver and isentropic relations."""
import pytest
import numpy as np
from nozzle.config import NozzleConfig
from validation.moc_solver import MoCSolver
from validation.moc_config import MoCConfig, MoCResults
from validation.isentropic import prandtl_meyer, mach_from_prandtl_meyer


class TestPrandtlMeyer:
    """Tests for Prandtl-Meyer function."""

    def test_sonic_condition(self):
        """Prandtl-Meyer angle at M=1 should be 0."""
        assert prandtl_meyer(1.0) == 0.0

    def test_supersonic_positive(self):
        """Prandtl-Meyer angle should be positive for M>1."""
        assert prandtl_meyer(2.0) > 0

    def test_increases_with_mach(self):
        """Prandtl-Meyer angle should increase with Mach."""
        assert prandtl_meyer(2.0) < prandtl_meyer(3.0)

    def test_known_value_m2(self):
        """Prandtl-Meyer angle at M=2, gamma=1.4 should be ~26.38 degrees."""
        nu_rad = prandtl_meyer(2.0, gamma=1.4)
        nu_deg = np.degrees(nu_rad)
        assert nu_deg == pytest.approx(26.38, abs=0.1), (
            f"Prandtl-Meyer at M=2 should be ~26.38 deg, got {nu_deg:.2f}"
        )

    def test_known_value_m3(self):
        """Prandtl-Meyer angle at M=3, gamma=1.4 should be ~49.76 degrees."""
        nu_rad = prandtl_meyer(3.0, gamma=1.4)
        nu_deg = np.degrees(nu_rad)
        assert nu_deg == pytest.approx(49.76, abs=0.1), (
            f"Prandtl-Meyer at M=3 should be ~49.76 deg, got {nu_deg:.2f}"
        )

    def test_subsonic_returns_zero(self):
        """Prandtl-Meyer angle for subsonic flow should be 0."""
        assert prandtl_meyer(0.5) == 0.0
        assert prandtl_meyer(0.8) == 0.0

    def test_different_gamma(self):
        """Prandtl-Meyer should work with non-standard gamma."""
        nu_1_3 = prandtl_meyer(2.0, gamma=1.3)
        nu_1_4 = prandtl_meyer(2.0, gamma=1.4)
        nu_1_67 = prandtl_meyer(2.0, gamma=1.67)
        # All should be positive for supersonic flow
        assert nu_1_3 > 0
        assert nu_1_4 > 0
        assert nu_1_67 > 0


class TestMachFromPrandtlMeyer:
    """Tests for inverse Prandtl-Meyer function."""

    def test_roundtrip(self):
        """Mach from Prandtl-Meyer should recover original."""
        mach_original = 2.5
        nu = prandtl_meyer(mach_original)
        mach_recovered = mach_from_prandtl_meyer(nu)
        assert abs(mach_original - mach_recovered) < 0.01, (
            f"Roundtrip failed: original={mach_original}, "
            f"recovered={mach_recovered}"
        )

    def test_sonic_condition(self):
        """Inverse at nu=0 should return M=1."""
        assert mach_from_prandtl_meyer(0.0) == 1.0

    def test_negative_nu_returns_one(self):
        """Negative nu should return M=1."""
        assert mach_from_prandtl_meyer(-1.0) == 1.0

    def test_known_value(self):
        """Inverse of known Prandtl-Meyer angle should give correct Mach."""
        # nu for M=3, gamma=1.4 is approximately 49.76 degrees
        nu = prandtl_meyer(3.0, gamma=1.4)
        mach = mach_from_prandtl_meyer(nu, gamma=1.4)
        assert mach == pytest.approx(3.0, abs=0.01), (
            f"Inverse of nu(M=3) should give M=3, got {mach}"
        )

    def test_monotonic(self):
        """Higher nu should give higher Mach."""
        mach1 = mach_from_prandtl_meyer(prandtl_meyer(2.0))
        mach2 = mach_from_prandtl_meyer(prandtl_meyer(3.0))
        assert mach1 < mach2


class TestMoCConfig:
    """Tests for nozzle flow solver configuration."""

    def test_default_config(self):
        """Default config should have sensible values."""
        config = MoCConfig()
        assert config.gamma == 1.4
        assert config.dx == 0.001

    def test_custom_config(self):
        """Custom config should override defaults."""
        config = MoCConfig(gamma=1.3)
        assert config.gamma == 1.3


class TestMoCResults:
    """Tests for nozzle flow solver results container."""

    def test_default_results(self):
        """Default results should have empty arrays."""
        results = MoCResults()
        assert len(results.x) == 0
        assert len(results.mach) == 0

    def test_results_with_data(self):
        """Results should store provided data."""
        x = np.array([0.0, 0.1, 0.2])
        mach = np.array([1.0, 1.5, 2.0])
        results = MoCResults(x=x, mach=mach)
        assert len(results.x) == 3
        assert results.mach[1] == 1.5


class TestMoCSolver:
    """Tests for nozzle flow solver."""

    def test_solver_initialization(self):
        """Solver should initialize with default config."""
        solver = MoCSolver()
        assert solver.config.gamma == 1.4

    def test_solver_custom_config(self):
        """Solver should accept custom config."""
        config = MoCConfig(gamma=1.3)
        solver = MoCSolver(config)
        assert solver.config.gamma == 1.3

    def test_solve_returns_results(self):
        """Solver should return MoCResults with data."""
        config = NozzleConfig(expansion_ratio=12.0)
        solver = MoCSolver()
        results = solver.solve(config)
        assert results.mach is not None
        assert len(results.x) > 0

    def test_solve_output_lengths(self):
        """All output arrays should have the same length."""
        config = NozzleConfig(expansion_ratio=12.0)
        solver = MoCSolver()
        results = solver.solve(config)
        n = len(results.x)
        assert len(results.mach) == n
        assert len(results.theta) == n
        assert len(results.nu) == n

    def test_mach_supersonic_in_diverging(self):
        """Mach should be > 1 in diverging section."""
        config = NozzleConfig(expansion_ratio=12.0)
        solver = MoCSolver()
        results = solver.solve(config)
        # Check that some mach values are > 1
        assert np.any(results.mach > 1.0)

    def test_mach_at_throat(self):
        """Mach at throat should be approximately 1.0."""
        config = NozzleConfig(expansion_ratio=12.0)
        solver = MoCSolver()
        results = solver.solve(config)
        # Find the point closest to x=0 (throat)
        throat_idx = np.argmin(np.abs(results.x))
        assert results.mach[throat_idx] == pytest.approx(1.0, abs=0.1), (
            f"Mach at throat should be ~1.0, got {results.mach[throat_idx]}"
        )

    def test_mach_increases_diverging(self):
        """Mach should generally increase in diverging section."""
        config = NozzleConfig(expansion_ratio=12.0)
        solver = MoCSolver()
        results = solver.solve(config)
        # Find throat and check that Mach increases downstream
        throat_idx = np.argmin(np.abs(results.x))
        diverging_mach = results.mach[throat_idx:]
        # Exit Mach should be greater than throat Mach
        assert diverging_mach[-1] > diverging_mach[0], (
            f"Exit Mach {diverging_mach[-1]} should be > "
            f"throat Mach {diverging_mach[0]}"
        )

    def test_exit_mach_reasonable(self):
        """Exit Mach should be reasonable for given expansion ratio."""
        config = NozzleConfig(expansion_ratio=12.0)
        solver = MoCSolver()
        results = solver.solve(config)
        # For epsilon=12, gamma=1.4, expected exit Mach is ~4.13
        exit_mach = results.mach[-1]
        assert exit_mach > 1.0, f"Exit Mach should be > 1, got {exit_mach}"
        assert exit_mach < 10.0, f"Exit Mach should be < 10, got {exit_mach}"

    def test_prandtl_meyer_non_negative(self):
        """Prandtl-Meyer angle should be non-negative everywhere."""
        config = NozzleConfig(expansion_ratio=12.0)
        solver = MoCSolver()
        results = solver.solve(config)
        assert np.all(results.nu >= 0), (
            f"Prandtl-Meyer angle should be non-negative, "
            f"got min={np.min(results.nu)}"
        )

    def test_different_expansion_ratios(self):
        """Solver should work for various expansion ratios."""
        for eps in [4.0, 12.0, 25.0]:
            config = NozzleConfig(expansion_ratio=eps)
            solver = MoCSolver()
            results = solver.solve(config)
            assert len(results.mach) > 0
            assert np.any(results.mach > 1.0)

    def test_different_gamma(self):
        """Solver should work with different gamma values."""
        config = NozzleConfig(expansion_ratio=12.0)
        for gamma in [1.3, 1.4, 1.67]:
            solver_config = MoCConfig(gamma=gamma)
            solver = MoCSolver(solver_config)
            results = solver.solve(config)
            assert len(results.mach) > 0
