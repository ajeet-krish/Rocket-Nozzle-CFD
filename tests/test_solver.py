"""Tests for SU2 solver interface."""
import pytest
from pathlib import Path
from cfd.solver import SU2Solver, SU2Results


class TestSU2Results:
    """Tests for SU2Results dataclass."""

    def test_default_values(self) -> None:
        """Default results should have zero/false values."""
        results = SU2Results()
        assert results.exit_mach == 0.0
        assert results.converged is False
        assert results.iterations == 0
        assert results.residual_drop == 0.0
        assert results.exit_pressure == 0.0

    def test_dataclass_fields(self) -> None:
        """Results should accept all field values."""
        results = SU2Results(
            exit_mach=3.5,
            converged=True,
            iterations=2000,
            residual_drop=6.0,
            exit_pressure=50000.0,
        )
        assert results.exit_mach == 3.5
        assert results.converged is True
        assert results.iterations == 2000
        assert results.residual_drop == 6.0
        assert results.exit_pressure == 50000.0

    def test_history_default_empty(self) -> None:
        """History should default to empty list."""
        results = SU2Results()
        assert results.history == []
        assert isinstance(results.history, list)


class TestSU2Solver:
    """Tests for SU2Solver class."""

    def test_solver_initialization(self) -> None:
        """Solver should initialize with a binary path."""
        solver = SU2Solver()
        assert solver.su2_cfd is not None

    def test_solver_custom_binary(self, tmp_path: Path) -> None:
        """Solver should accept a custom binary path."""
        fake_binary = tmp_path / "su2_cfd"
        fake_binary.write_text("#!/bin/sh\n")
        solver = SU2Solver(su2_cfd=fake_binary)
        assert solver.su2_cfd == fake_binary

    def test_parse_history_empty(self, tmp_path: Path) -> None:
        """Parsing an empty history should return empty list."""
        solver = SU2Solver()
        history_file = tmp_path / "history.csv"
        history_file.write_text('"Comment line\n')
        result = solver._parse_history(history_file)
        assert result == []

    def test_parse_history_with_data(self, tmp_path: Path) -> None:
        """Parsing history with CSV data should return row dicts."""
        solver = SU2Solver()
        history_file = tmp_path / "history.csv"
        history_file.write_text(
            '"Comment line\n'
            'INNER_ITER,RMS_DENSITY\n'
            '1,-1.0\n'
            '2,-2.0\n'
        )
        result = solver._parse_history(history_file)
        assert len(result) == 2
        assert result[0]['INNER_ITER'] == '1'
        assert result[0]['RMS_DENSITY'] == '-1.0'
        assert result[1]['INNER_ITER'] == '2'

    def test_parse_history_missing_file(self, tmp_path: Path) -> None:
        """Parsing a non-existent file should return empty list."""
        solver = SU2Solver()
        result = solver._parse_history(tmp_path / "missing.csv")
        assert result == []

    def test_parse_results_convergence(self, tmp_path: Path) -> None:
        """parse_results should detect convergence from residual drop."""
        solver = SU2Solver()

        # Create a history file with large residual drop
        history_file = tmp_path / "history.csv"
        lines = ['"Comment\n', 'INNER_ITER,RMS_DENSITY\n']
        for i in range(1, 101):
            residual = -1.0 - (i * 0.05)
            lines.append(f'{i},{residual:.2f}\n')
        history_file.write_text(''.join(lines))

        results = solver.parse_results(tmp_path)
        assert results.iterations == 100
        assert results.converged is True
        assert results.residual_drop > 3.0

    def test_parse_results_no_history(self, tmp_path: Path) -> None:
        """parse_results with no history should return defaults."""
        solver = SU2Solver()
        results = solver.parse_results(tmp_path)
        assert results.exit_mach == 0.0
        assert results.converged is False
        assert results.iterations == 0
