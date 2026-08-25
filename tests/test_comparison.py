"""Tests for SU2 vs isentropic comparison logic."""
import pytest
from validation.compare import compare_results, ComparisonReport
from validation.isentropic import exit_mach_from_area_ratio


class TestCompareResults:
    """Tests for compare_results pass/fail logic."""

    def test_pass_within_tolerance(self):
        """Simulation Mach within 5% of theory should pass."""
        # Get theoretical Mach for epsilon=12
        theory_mach = exit_mach_from_area_ratio(12.0, gamma=1.4)
        # Simulate with 2% error
        sim_mach = theory_mach * 0.98
        report = compare_results(sim_mach, 12.0, gamma=1.4, tolerance=5.0)
        assert report.passed, (
            f"Should PASS with 2% error. Error={report.mach_error_percent:.2f}%"
        )

    def test_fail_outside_tolerance(self):
        """Simulation Mach > 5% from theory should fail."""
        theory_mach = exit_mach_from_area_ratio(12.0, gamma=1.4)
        # Simulate with 10% error
        sim_mach = theory_mach * 0.90
        report = compare_results(sim_mach, 12.0, gamma=1.4, tolerance=5.0)
        assert not report.passed, (
            f"Should FAIL with 10% error. Error={report.mach_error_percent:.2f}%"
        )

    def test_exact_match(self):
        """Exact match should pass with 0% error."""
        theory_mach = exit_mach_from_area_ratio(12.0, gamma=1.4)
        report = compare_results(theory_mach, 12.0, gamma=1.4, tolerance=5.0)
        assert report.passed
        assert report.mach_error_percent == pytest.approx(0.0, abs=1e-10)

    def test_boundary_tolerance_5_percent(self):
        """Exactly 5% error should fail (strict < check)."""
        theory_mach = exit_mach_from_area_ratio(12.0, gamma=1.4)
        sim_mach = theory_mach * 0.95
        report = compare_results(sim_mach, 12.0, gamma=1.4, tolerance=5.0)
        # The error is exactly 5%, which is NOT < 5%
        assert not report.passed, (
            f"Error at exactly 5% should FAIL (strict <). "
            f"Error={report.mach_error_percent:.2f}%"
        )

    def test_pass_under_threshold(self):
        """4.9% error should pass with 5% tolerance."""
        theory_mach = exit_mach_from_area_ratio(12.0, gamma=1.4)
        sim_mach = theory_mach * (1.0 - 0.049)
        report = compare_results(sim_mach, 12.0, gamma=1.4, tolerance=5.0)
        assert report.passed, (
            f"4.9% error should PASS. Error={report.mach_error_percent:.2f}%"
        )

    def test_negative_exit_mach_fails(self):
        """Negative simulation Mach should fail."""
        report = compare_results(-1.0, 12.0, gamma=1.4, tolerance=5.0)
        assert not report.passed, "Negative Mach should FAIL"

    def test_zero_exit_mach_fails(self):
        """Zero simulation Mach should fail."""
        report = compare_results(0.0, 12.0, gamma=1.4, tolerance=5.0)
        assert not report.passed, "Zero Mach should FAIL"

    def test_comparison_report_fields(self):
        """Report should contain all expected fields."""
        theory_mach = exit_mach_from_area_ratio(12.0, gamma=1.4)
        report = compare_results(theory_mach, 12.0, gamma=1.4, tolerance=5.0)
        assert isinstance(report, ComparisonReport)
        assert hasattr(report, 'exit_mach_sim')
        assert hasattr(report, 'exit_mach_theory')
        assert hasattr(report, 'mach_error_percent')
        assert hasattr(report, 'converged')
        assert hasattr(report, 'passed')
        assert hasattr(report, 'notes')

    def test_error_calculation_correctness(self):
        """Verify error percentage is calculated correctly."""
        theory_mach = exit_mach_from_area_ratio(12.0, gamma=1.4)
        sim_mach = theory_mach + 0.5
        report = compare_results(sim_mach, 12.0, gamma=1.4, tolerance=5.0)
        expected_error = abs(0.5) / theory_mach * 100.0
        assert report.mach_error_percent == pytest.approx(expected_error, rel=1e-10), (
            f"Error should be {expected_error:.2f}%, got {report.mach_error_percent:.2f}%"
        )

    def test_custom_tolerance(self):
        """Test with different tolerance values."""
        theory_mach = exit_mach_from_area_ratio(12.0, gamma=1.4)
        sim_mach = theory_mach * 0.93  # 7% error
        # Should fail with 5% tolerance
        report_5 = compare_results(sim_mach, 12.0, gamma=1.4, tolerance=5.0)
        assert not report_5.passed
        # Should pass with 10% tolerance
        report_10 = compare_results(sim_mach, 12.0, gamma=1.4, tolerance=10.0)
        assert report_10.passed

    def test_higher_expansion_ratio(self):
        """Test comparison with a different expansion ratio."""
        theory_mach = exit_mach_from_area_ratio(25.0, gamma=1.4)
        sim_mach = theory_mach * 0.97  # 3% error
        report = compare_results(sim_mach, 25.0, gamma=1.4, tolerance=5.0)
        assert report.passed

    def test_notes_include_validation_result(self):
        """Notes should indicate PASSED or FAILED."""
        theory_mach = exit_mach_from_area_ratio(12.0, gamma=1.4)
        report_pass = compare_results(theory_mach, 12.0, gamma=1.4, tolerance=5.0)
        assert "VALIDATION PASSED" in report_pass.notes

        sim_mach = theory_mach * 0.5  # 50% error
        report_fail = compare_results(sim_mach, 12.0, gamma=1.4, tolerance=5.0)
        assert "VALIDATION FAILED" in report_fail.notes
