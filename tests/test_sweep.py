"""Tests for parametric sweep configuration and results."""
import csv
import tempfile
from pathlib import Path
import pytest
from sweep.config import SweepConfig, SweepCase, generate_sweep_cases
from sweep.results import SweepCaseResult, SweepResults


class TestSweepConfig:
    """Tests for SweepConfig dataclass."""

    def test_default_values(self):
        """SweepConfig should have sensible defaults."""
        config = SweepConfig()
        assert len(config.expansion_ratios) == 5
        assert len(config.chamber_pressures) == 4
        assert len(config.throat_radii) == 4
        assert config.gamma == 1.4

    def test_frozen(self):
        """SweepConfig should be immutable."""
        config = SweepConfig()
        with pytest.raises(AttributeError):
            config.gamma = 1.3  # type: ignore[misc]

    def test_custom_values(self):
        """SweepConfig should accept custom values."""
        config = SweepConfig(
            expansion_ratios=(4.0, 8.0),
            gamma=1.3,
        )
        assert config.expansion_ratios == (4.0, 8.0)
        assert config.gamma == 1.3


class TestSweepCase:
    """Tests for SweepCase dataclass."""

    def test_creation(self):
        """SweepCase should store all fields."""
        case = SweepCase(
            case_id="test",
            sweep_type="epsilon",
            expansion_ratio=12.0,
            chamber_pressure=10e6,
            throat_radius=0.05,
            total_temperature=3500.0,
            gamma=1.4,
        )
        assert case.case_id == "test"
        assert case.sweep_type == "epsilon"


class TestGenerateSweepCases:
    """Tests for generate_sweep_cases function."""

    def test_epsilon_sweep_count(self):
        """Epsilon sweep should have len(expansion_ratios) cases."""
        config = SweepConfig(
            expansion_ratios=(4.0, 8.0, 12.0),
            chamber_pressures=(10e6,),
            throat_radii=(0.05,),
            reference_pc=10e6,
            reference_r_star=0.05,
        )
        cases = generate_sweep_cases(config)
        eps_cases = [c for c in cases if c.sweep_type == "epsilon"]
        assert len(eps_cases) == 3

    def test_pc_sweep_skips_reference(self):
        """Pc sweep should skip the reference pressure."""
        config = SweepConfig(
            expansion_ratios=(12.0,),
            chamber_pressures=(5e6, 10e6, 20e6),
            throat_radii=(0.05,),
            reference_epsilon=12.0,
            reference_pc=10e6,
            reference_r_star=0.05,
        )
        cases = generate_sweep_cases(config)
        pc_cases = [c for c in cases if c.sweep_type == "pc"]
        # 3 pressures - 1 reference = 2
        assert len(pc_cases) == 2
        for c in pc_cases:
            assert c.chamber_pressure != 10e6

    def test_r_star_sweep_skips_reference(self):
        """R* sweep should skip the reference throat radius."""
        config = SweepConfig(
            expansion_ratios=(12.0,),
            chamber_pressures=(10e6,),
            throat_radii=(0.01, 0.05, 0.1),
            reference_epsilon=12.0,
            reference_pc=10e6,
            reference_r_star=0.05,
        )
        cases = generate_sweep_cases(config)
        rstar_cases = [c for c in cases if c.sweep_type == "r_star"]
        # 3 radii - 1 reference = 2
        assert len(rstar_cases) == 2
        for c in rstar_cases:
            assert c.throat_radius != 0.05

    def test_total_case_count(self):
        """Total cases = epsilon + pc + rstar (with references excluded)."""
        config = SweepConfig()
        cases = generate_sweep_cases(config)
        eps_count = len([c for c in cases if c.sweep_type == "epsilon"])
        pc_count = len([c for c in cases if c.sweep_type == "pc"])
        rstar_count = len([c for c in cases if c.sweep_type == "r_star"])
        assert len(cases) == eps_count + pc_count + rstar_count

    def test_case_ids_unique(self):
        """All case_ids should be unique."""
        config = SweepConfig()
        cases = generate_sweep_cases(config)
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids))

    def test_epsilon_sweep_uses_reference_pc_and_rstar(self):
        """Epsilon sweep cases should use reference Pc and R*."""
        config = SweepConfig(
            expansion_ratios=(4.0, 8.0),
            chamber_pressures=(5e6, 10e6, 20e6),
            throat_radii=(0.01, 0.05),
            reference_pc=10e6,
            reference_r_star=0.05,
        )
        cases = generate_sweep_cases(config)
        eps_cases = [c for c in cases if c.sweep_type == "epsilon"]
        for c in eps_cases:
            assert c.chamber_pressure == 10e6
            assert c.throat_radius == 0.05


class TestSweepCaseResult:
    """Tests for SweepCaseResult dataclass."""

    def test_creation(self):
        """SweepCaseResult should store all fields."""
        result = SweepCaseResult(
            case_id="test",
            sweep_type="epsilon",
            expansion_ratio=12.0,
            chamber_pressure=10e6,
            throat_radius=0.05,
            exit_mach_isentropic=4.13,
            exit_mach_su2=4.05,
            converged=True,
            iterations=2000,
            error_percent=1.94,
        )
        assert result.converged is True
        assert result.error_percent == pytest.approx(1.94, abs=1e-10)


class TestSweepResults:
    """Tests for SweepResults dataclass."""

    def test_by_sweep_type(self):
        """by_sweep_type should filter correctly."""
        results = SweepResults()
        results.cases = [
            SweepCaseResult("e4", "epsilon", 4.0, 10e6, 0.05, 3.0, 2.9, True, 100, 3.3),
            SweepCaseResult("e8", "epsilon", 8.0, 10e6, 0.05, 3.5, 3.4, True, 100, 2.9),
            SweepCaseResult("pc5", "pc", 12.0, 5e6, 0.05, 4.0, 3.9, True, 100, 2.5),
        ]
        eps_results = results.by_sweep_type("epsilon")
        assert len(eps_results) == 2
        pc_results = results.by_sweep_type("pc")
        assert len(pc_results) == 1

    def test_to_csv(self):
        """to_csv should write a valid CSV file."""
        results = SweepResults()
        results.cases = [
            SweepCaseResult("e4", "epsilon", 4.0, 10e6, 0.05, 3.0, 2.9, True, 100, 3.3),
            SweepCaseResult("e8", "epsilon", 8.0, 10e6, 0.05, 3.5, 3.4, True, 100, 2.9),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "results.csv"
            results.to_csv(csv_path)

            # Verify CSV was written
            assert csv_path.exists()

            # Verify content
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                # Header + 2 data rows
                assert len(rows) == 3
                assert rows[0][0] == 'case_id'
                assert rows[1][0] == 'e4'
                assert rows[2][0] == 'e8'

    def test_empty_results(self):
        """Empty results should work without errors."""
        results = SweepResults()
        eps_results = results.by_sweep_type("epsilon")
        assert len(eps_results) == 0
