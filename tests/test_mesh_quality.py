"""Tests for mesh quality metrics."""
import pytest
from pathlib import Path
from cfd.mesh_quality import check_mesh_quality, validate_su2_mesh, MeshQualityResult


class TestMeshQuality:
    """Tests for mesh quality assessment."""

    def test_check_mesh_quality_returns_result(self, tmp_path):
        """check_mesh_quality should return a MeshQualityResult."""
        mesh_file = tmp_path / "test.su2"
        mesh_file.write_text("test content")
        result = check_mesh_quality(mesh_file)
        assert isinstance(result, MeshQualityResult)
        assert result.passed is True

    def test_check_mesh_quality_nonexistent(self, tmp_path):
        """check_mesh_quality should fail for non-existent file."""
        result = check_mesh_quality(tmp_path / "missing.su2")
        assert result.passed is False
        assert "does not exist" in result.notes

    def test_check_mesh_quality_custom_thresholds(self, tmp_path):
        """check_mesh_quality should accept custom thresholds."""
        mesh_file = tmp_path / "test.su2"
        mesh_file.write_text("test content")
        result = check_mesh_quality(
            mesh_file,
            min_orthogonality=30.0,
            max_aspect_ratio=20.0,
            max_expansion_ratio=1.5,
        )
        assert result.min_orthogonality == 30.0
        assert result.max_aspect_ratio == 20.0
        assert result.max_expansion_ratio == 1.5

    def test_validate_su2_mesh_with_markers(self, tmp_path):
        """validate_su2_mesh should pass when all markers are present."""
        mesh_file = tmp_path / "test.su2"
        content = "\n".join([
            "mesh file content",
            "MARKER_TAG= inlet",
            "MARKER_TAG= outlet",
            "MARKER_TAG= wall",
            "MARKER_TAG= symmetry",
        ])
        mesh_file.write_text(content)
        assert validate_su2_mesh(mesh_file) is True

    def test_validate_su2_mesh_missing_markers(self, tmp_path):
        """validate_su2_mesh should fail when markers are missing."""
        mesh_file = tmp_path / "test.su2"
        mesh_file.write_text("no markers here")
        assert validate_su2_mesh(mesh_file) is False

    def test_validate_su2_mesh_partial_markers(self, tmp_path):
        """validate_su2_mesh should fail with only some markers."""
        mesh_file = tmp_path / "test.su2"
        content = "\n".join([
            "MARKER_TAG= inlet",
            "MARKER_TAG= wall",
        ])
        mesh_file.write_text(content)
        assert validate_su2_mesh(mesh_file) is False

    def test_validate_su2_mesh_nonexistent(self, tmp_path):
        """validate_su2_mesh should handle non-existent file."""
        assert validate_su2_mesh(tmp_path / "missing.su2") is False

    def test_validate_su2_mesh_empty_file(self, tmp_path):
        """validate_su2_mesh should fail for empty file."""
        mesh_file = tmp_path / "empty.su2"
        mesh_file.write_text("")
        assert validate_su2_mesh(mesh_file) is False


class TestMeshQualityResult:
    """Tests for MeshQualityResult dataclass."""

    def test_result_creation(self):
        """MeshQualityResult should store all fields."""
        result = MeshQualityResult(
            n_nodes=1000,
            n_elements=500,
            min_orthogonality=45.0,
            max_aspect_ratio=10.0,
            max_expansion_ratio=1.2,
            has_negative_jacobians=False,
            passed=True,
            notes="All good",
        )
        assert result.n_nodes == 1000
        assert result.passed is True
        assert result.notes == "All good"

    def test_result_failed(self):
        """MeshQualityResult should support failed state."""
        result = MeshQualityResult(
            n_nodes=0, n_elements=0,
            min_orthogonality=0.0, max_aspect_ratio=float("inf"),
            max_expansion_ratio=float("inf"),
            has_negative_jacobians=True, passed=False,
            notes="Negative Jacobians detected",
        )
        assert result.passed is False
        assert result.has_negative_jacobians is True
