"""Tests for Grid Convergence Index computation."""
import math
import pytest
from validation.gci import (
    GCIMeshLevel,
    GCIResult,
    richardson_extrapolation,
    compute_gci,
)


class TestGCIMeshLevel:
    """Tests for GCIMeshLevel dataclass."""

    def test_creation(self):
        """GCIMeshLevel should store all fields."""
        level = GCIMeshLevel(n_cells=1000, exit_mach=3.5, thrust_coefficient=1.2)
        assert level.n_cells == 1000
        assert level.exit_mach == 3.5
        assert level.thrust_coefficient == 1.2


class TestGCIResult:
    """Tests for GCIResult dataclass."""

    def test_has_required_fields(self):
        """GCIResult should have all required fields."""
        coarse = GCIMeshLevel(100, 3.0, 1.0)
        medium = GCIMeshLevel(200, 3.2, 1.1)
        fine = GCIMeshLevel(400, 3.3, 1.15)
        result = GCIResult(
            coarse=coarse,
            medium=medium,
            fine=fine,
            refinement_ratio=2.0,
            apparent_order=1.0,
            extrapolated_mach=3.4,
            extrapolated_thrust=1.2,
            gci_fine_mach=0.5,
            gci_fine_thrust=0.3,
            asymptotic_ratio_mach=1.0,
            passed=True,
            notes="test",
        )
        assert result.passed is True
        assert result.fine.n_cells == 400


class TestRichardsonExtrapolation:
    """Tests for richardson_extrapolation function."""

    def test_convergent_sequence(self):
        """Known O(h^2) convergent sequence should give correct extrapolation."""
        # O(h^2) with r=2: errors are C*h^2, 4*C*h^2, 16*C*h^2
        # Choose C*h^2 = 0.025, f_exact = 3.5
        f_exact = 3.5
        f1 = f_exact - 0.025    # fine:   error = 0.025
        f2 = f_exact - 0.10     # medium: error = 0.10 = 4 * 0.025
        f3 = f_exact - 0.40     # coarse: error = 0.40 = 16 * 0.025
        p, f_extrap = richardson_extrapolation(f1, f2, f3, r=2.0)
        assert p == pytest.approx(2.0, abs=0.01)
        # Extrapolated should be very close to exact
        assert abs(f_extrap - f_exact) < 0.01

    def test_identical_values(self):
        """Identical values should return order 1.0 and the value itself."""
        p, f_exact = richardson_extrapolation(3.0, 3.0, 3.0, r=2.0)
        assert p == 1.0
        assert f_exact == 3.0

    def test_nearly_identical_values(self):
        """Very close values should still return reasonable results."""
        p, f_exact = richardson_extrapolation(3.0, 3.0 + 1e-14, 3.0 + 2e-14, r=2.0)
        assert p == 1.0
        assert f_exact == pytest.approx(3.0, abs=1e-10)

    def test_different_refinement_ratio(self):
        """Non-standard refinement ratio should be handled correctly."""
        f1, f2, f3 = 4.0, 3.5, 2.5
        p, f_exact = richardson_extrapolation(f1, f2, f3, r=3.0)
        assert p > 0
        assert f_exact != f1  # Should differ from finest mesh

    def test_perfect_first_order(self):
        """First-order convergence should give p ~ 1.0."""
        # O(h): f = a + b*h, so f1=a+b*h, f2=a+b*2h, f3=a+b*4h
        h = 0.01
        a, b = 3.0, 0.5
        f1 = a + b * h       # fine
        f2 = a + b * 2 * h   # medium
        f3 = a + b * 4 * h   # coarse
        p, f_exact = richardson_extrapolation(f1, f2, f3, r=2.0)
        assert p == pytest.approx(1.0, abs=1e-10)


class TestComputeGCI:
    """Tests for compute_gci function."""

    def test_basic_gci_computation(self):
        """GCI should produce valid result for reasonable inputs."""
        coarse = GCIMeshLevel(n_cells=100, exit_mach=3.0, thrust_coefficient=1.0)
        medium = GCIMeshLevel(n_cells=200, exit_mach=3.2, thrust_coefficient=1.1)
        fine = GCIMeshLevel(n_cells=400, exit_mach=3.3, thrust_coefficient=1.15)

        result = compute_gci(coarse, medium, fine, refinement_ratio=2.0)

        assert isinstance(result, GCIResult)
        assert result.gci_fine_mach >= 0
        assert result.apparent_order > 0
        assert result.fine.n_cells == 400

    def test_gci_passes_for_converged(self):
        """Well-converged sequence should pass GCI check."""
        # Simulate O(h^2) convergence
        exact = 3.5
        coarse = GCIMeshLevel(100, exact - 0.10, 1.0)
        medium = GCIMeshLevel(200, exact - 0.025, 1.1)
        fine = GCIMeshLevel(400, exact - 0.006, 1.15)

        result = compute_gci(coarse, medium, fine, refinement_ratio=2.0)

        assert result.gci_fine_mach < 5.0
        assert result.passed

    def test_gci_fails_for_poorly_converged(self):
        """Poorly converged sequence should fail GCI check."""
        coarse = GCIMeshLevel(100, 2.0, 1.0)
        medium = GCIMeshLevel(200, 2.5, 1.1)
        fine = GCIMeshLevel(400, 2.8, 1.15)

        result = compute_gci(coarse, medium, fine, refinement_ratio=2.0)

        # The errors are large, so GCI should be high
        assert result.gci_fine_mach > 0

    def test_zero_difference_returns_zero(self):
        """Zero difference between levels should return GCI = 0."""
        coarse = GCIMeshLevel(100, 3.0, 1.0)
        medium = GCIMeshLevel(200, 3.0, 1.0)
        fine = GCIMeshLevel(400, 3.0, 1.0)

        result = compute_gci(coarse, medium, fine, refinement_ratio=2.0)

        assert result.gci_fine_mach == 0.0
        assert result.gci_fine_thrust == 0.0

    def test_safety_factor_scaling(self):
        """Larger safety factor should produce larger GCI."""
        coarse = GCIMeshLevel(100, 3.0, 1.0)
        medium = GCIMeshLevel(200, 3.2, 1.1)
        fine = GCIMeshLevel(400, 3.3, 1.15)

        result_low = compute_gci(
            coarse, medium, fine,
            refinement_ratio=2.0, safety_factor=1.25,
        )
        result_high = compute_gci(
            coarse, medium, fine,
            refinement_ratio=2.0, safety_factor=3.0,
        )

        assert result_high.gci_fine_mach > result_low.gci_fine_mach

    def test_notes_contain_key_info(self):
        """Notes should mention GCI, order, and asymptotic ratio."""
        coarse = GCIMeshLevel(100, 3.0, 1.0)
        medium = GCIMeshLevel(200, 3.2, 1.1)
        fine = GCIMeshLevel(400, 3.3, 1.15)

        result = compute_gci(coarse, medium, fine, refinement_ratio=2.0)

        assert "GCI" in result.notes
        assert "order" in result.notes
        assert "asymptotic" in result.notes

    def test_asymptotic_ratio_in_valid_range(self):
        """Asymptotic ratio should be near 1.0 for consistent convergence."""
        # O(h^2) convergence: error scales with h^2, ratio should be ~1
        exact = 3.5
        coarse = GCIMeshLevel(100, exact - 0.10, 1.0)
        medium = GCIMeshLevel(200, exact - 0.025, 1.1)
        fine = GCIMeshLevel(400, exact - 0.00625, 1.15)

        result = compute_gci(coarse, medium, fine, refinement_ratio=2.0)

        # For well-behaved convergence, ratio should be in (0.5, 2.0)
        assert 0.5 < result.asymptotic_ratio_mach < 2.0

    def test_extrapolated_mach_is_accurate(self):
        """Extrapolated Mach should be closer to exact than finest mesh."""
        exact = 3.5
        coarse = GCIMeshLevel(100, exact - 0.10, 1.0)
        medium = GCIMeshLevel(200, exact - 0.025, 1.1)
        fine = GCIMeshLevel(400, exact - 0.00625, 1.15)

        result = compute_gci(coarse, medium, fine, refinement_ratio=2.0)

        # Extrapolated should be closer to exact than finest
        assert abs(result.extrapolated_mach - exact) < abs(fine.exit_mach - exact)
