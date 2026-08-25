"""Tests for three-way validation comparison."""
import pytest
from validation.triple import TripleReport, compare_three_way


class TestTripleReport:
    """Tests for TripleReport dataclass."""

    def test_has_required_fields(self):
        """TripleReport should have all required fields."""
        report = TripleReport(
            exit_mach_isentropic=3.0,
            exit_mach_moc=3.0,
            exit_mach_su2=3.0,
            l2_error_iso_moc=0.0,
            l2_error_iso_su2=0.0,
            l2_error_moc_su2=0.0,
            max_error_percent=0.0,
            passed=True,
            notes="ok",
        )
        assert report.exit_mach_isentropic == 3.0
        assert report.passed is True


class TestCompareThreeWay:
    """Tests for compare_three_way function."""

    def test_exact_match(self):
        """All three identical values should pass with 0% error."""
        report = compare_three_way(3.0, 3.0, 3.0)
        assert report.passed
        assert report.max_error_percent == pytest.approx(0.0, abs=1e-12)

    def test_small_error_passes(self):
        """2% deviation should pass with default 5% tolerance."""
        report = compare_three_way(3.0, 3.0 * 0.98, 3.0 * 0.97)
        assert report.passed
        assert report.max_error_percent < 5.0

    def test_large_error_fails(self):
        """10% deviation should fail with default 5% tolerance."""
        report = compare_three_way(3.0, 2.5, 2.5)
        assert not report.passed

    def test_custom_tolerance(self):
        """Tighter tolerance should fail sooner."""
        report = compare_three_way(3.0, 3.0 * 0.96, 3.0 * 0.96, tolerance=3.0)
        assert not report.passed

    def test_error_calculation_pairwise(self):
        """Pairwise errors should be computed correctly."""
        report = compare_three_way(
            exit_mach_isentropic=4.0,
            exit_mach_moc=3.8,
            exit_mach_su2=3.6,
        )
        # iso vs moc: |4.0 - 3.8| / 4.0 * 100 = 5.0%
        assert report.l2_error_iso_moc == pytest.approx(5.0, abs=1e-10)
        # iso vs su2: |4.0 - 3.6| / 4.0 * 100 = 10.0%
        assert report.l2_error_iso_su2 == pytest.approx(10.0, abs=1e-10)
        # moc vs su2: |3.8 - 3.6| / 3.8 * 100 = ~5.263%
        expected_moc_su2 = abs(3.8 - 3.6) / 3.8 * 100
        assert report.l2_error_moc_su2 == pytest.approx(expected_moc_su2, abs=1e-10)
        # max should be 10.0%
        assert report.max_error_percent == pytest.approx(10.0, abs=1e-10)

    def test_zero_isentropic_mach(self):
        """Zero isentropic Mach should still compute other errors."""
        report = compare_three_way(0.0, 3.0, 3.0)
        # When isentropic is zero, iso errors are 0; moc vs su2 = 0%
        assert report.l2_error_iso_moc == 0.0
        assert report.l2_error_iso_su2 == 0.0
        assert report.l2_error_moc_su2 == pytest.approx(0.0, abs=1e-10)
        assert report.passed

    def test_notes_contain_status(self):
        """Notes should contain PASSED or FAILED."""
        report_pass = compare_three_way(3.0, 3.0, 3.0)
        assert "PASSED" in report_pass.notes

        report_fail = compare_three_way(3.0, 1.0, 1.0)
        assert "FAILED" in report_fail.notes

    def test_notes_contain_max_error(self):
        """Notes should include the max error percentage."""
        report = compare_three_way(4.0, 3.8, 3.6)
        assert "10.00%" in report.notes

    def test_passes_at_boundary(self):
        """Just under tolerance should pass, just over should fail."""
        # 4.9% error should pass
        report_pass = compare_three_way(3.0, 3.0, 3.0 * (1.0 - 0.049))
        assert report_pass.passed

        # 5.1% error should fail
        report_fail = compare_three_way(3.0, 3.0, 3.0 * (1.0 - 0.051))
        assert not report_fail.passed
