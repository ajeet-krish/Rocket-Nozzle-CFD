"""Tests for mesh quality metrics."""
import pytest
from pathlib import Path

import numpy as np

from cfd.mesh_quality import (
    MeshQualityResult,
    _compute_aspect_ratio,
    _compute_expansion_ratio,
    _compute_orthogonality,
    _element_area_quad,
    _element_center,
    _edge_length,
    _parse_su2_mesh,
    check_mesh_quality,
    validate_su2_mesh,
)


def _write_su2_mesh(path: Path, nodes: list[tuple[float, float]], elements: list[tuple[int, ...]], markers: dict | None = None) -> None:
    """Write a minimal SU2 mesh file for testing.

    Args:
        path: Output file path
        nodes: List of (x, y) coordinates
        elements: List of (n1, n2, n3, n4) quad connectivity (0-indexed)
        markers: Optional dict of {tag: [(n1, n2), ...]} boundary elements
    """
    lines = [
        "NDIME= 2",
        f"NELEM= {len(elements)}",
    ]
    for conn in elements:
        # Element type 9 = quad
        lines.append("9 " + " ".join(str(i) for i in conn))

    lines.append(f"NPOIN= {len(nodes)}")
    for x, y in nodes:
        lines.append(f"{x} {y} 0.0")

    markers = markers or {}
    lines.append(f"NMARK= {len(markers)}")
    for tag, elems in markers.items():
        lines.append(f"MARKER_TAG= {tag}")
        lines.append(f"MARKER_ELEMS= {len(elems)}")
        for conn in elems:
            # Element type 3 = line
            lines.append("3 " + " ".join(str(i) for i in conn))

    path.write_text("\n".join(lines) + "\n")


class TestParseSu2Mesh:
    """Tests for _parse_su2_mesh."""

    def test_parse_simple_quad_mesh(self, tmp_path):
        """Parse a simple 2-quad mesh."""
        # Two quads sharing one edge:
        #  3---4---5
        #  |   |   |
        #  0---1---2
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (2.0, 0.0),
            (0.0, 1.0), (1.0, 1.0), (2.0, 1.0),
        ]
        elements = [
            (0, 1, 4, 3),  # left quad
            (1, 2, 5, 4),  # right quad
        ]
        mesh_file = tmp_path / "test.su2"
        _write_su2_mesh(mesh_file, nodes, elements)

        parsed = _parse_su2_mesh(mesh_file)

        assert len(parsed.nodes) == 6
        assert len(parsed.elements) == 2
        np.testing.assert_allclose(parsed.nodes[0], [0.0, 0.0, 0.0])
        np.testing.assert_allclose(parsed.nodes[5], [2.0, 1.0, 0.0])

    def test_parse_elements_have_correct_shape(self, tmp_path):
        """Each parsed element row should be [type, n1, n2, n3, n4]."""
        nodes = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        elements = [(0, 1, 2, 3)]
        mesh_file = tmp_path / "test.su2"
        _write_su2_mesh(mesh_file, nodes, elements)

        parsed = _parse_su2_mesh(mesh_file)

        assert parsed.elements.shape == (1, 5)
        assert parsed.elements[0, 0] == 9  # quad type
        np.testing.assert_array_equal(parsed.elements[0, 1:], [0, 1, 2, 3])

    def test_parse_with_markers(self, tmp_path):
        """Parse markers from mesh file."""
        nodes = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        elements = [(0, 1, 2, 3)]
        markers = {
            "inlet": [(0, 3)],
            "wall": [(3, 2), (2, 1)],
        }
        mesh_file = tmp_path / "test.su2"
        _write_su2_mesh(mesh_file, nodes, elements, markers)

        parsed = _parse_su2_mesh(mesh_file)

        assert "inlet" in parsed.markers
        assert "wall" in parsed.markers
        assert len(parsed.markers["inlet"]) == 1
        assert len(parsed.markers["wall"]) == 2

    def test_parse_empty_file_raises(self, tmp_path):
        """Parsing an empty mesh file should raise ValueError."""
        mesh_file = tmp_path / "empty.su2"
        mesh_file.write_text("")

        with pytest.raises(ValueError, match="No nodes found"):
            _parse_su2_mesh(mesh_file)

    def test_parse_elements_only_no_nodes_raises(self, tmp_path):
        """Parsing a file with elements but no nodes should raise ValueError."""
        mesh_file = tmp_path / "bad.su2"
        mesh_file.write_text("NDIME= 2\nNELEM= 1\n9 0 1 2 3\nNPOIN= 0\n")

        with pytest.raises(ValueError, match="No nodes found"):
            _parse_su2_mesh(mesh_file)


class TestComputeOrthogonality:
    """Tests for _compute_orthogonality."""

    def test_orthogonality_on_uniform_grid(self, tmp_path):
        """Uniform rectilinear grid should have 90-degree orthogonality."""
        # 2x1 grid of unit squares:
        #  2---3---4
        #  |   |   |
        #  0---1---5
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (0.0, 1.0),
            (1.0, 1.0), (2.0, 1.0), (2.0, 0.0),
        ]
        elements = [
            (0, 1, 3, 2),  # left quad
            (1, 5, 4, 3),  # right quad
        ]
        mesh_file = tmp_path / "grid.su2"
        _write_su2_mesh(mesh_file, nodes, elements)
        parsed = _parse_su2_mesh(mesh_file)

        ortho = _compute_orthogonality(parsed.nodes, parsed.elements)

        assert len(ortho) == 1  # One interior face
        np.testing.assert_allclose(ortho[0], 90.0, atol=1e-10)

    def test_orthogonality_empty_for_single_element(self):
        """Single element has no interior faces."""
        nodes = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ])
        elements = np.array([[9, 0, 1, 2, 3]])

        ortho = _compute_orthogonality(nodes, elements)

        assert len(ortho) == 0

    def test_orthogonality_returns_degrees(self, tmp_path):
        """Orthogonality values should be in degrees."""
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (0.0, 1.0),
            (1.0, 1.0), (2.0, 1.0), (2.0, 0.0),
        ]
        elements = [
            (0, 1, 3, 2),
            (1, 5, 4, 3),
        ]
        mesh_file = tmp_path / "grid.su2"
        _write_su2_mesh(mesh_file, nodes, elements)
        parsed = _parse_su2_mesh(mesh_file)

        ortho = _compute_orthogonality(parsed.nodes, parsed.elements)

        # All values should be between 0 and 180 degrees
        assert np.all(ortho >= 0.0)
        assert np.all(ortho <= 180.0)


class TestComputeAspectRatio:
    """Tests for _compute_aspect_ratio."""

    def test_aspect_ratio_on_squares(self):
        """Square elements should have aspect ratio 1.0."""
        nodes = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ])
        elements = np.array([[9, 0, 1, 2, 3]])

        ar = _compute_aspect_ratio(nodes, elements)

        assert len(ar) == 1
        np.testing.assert_allclose(ar[0], 1.0, atol=1e-10)

    def test_aspect_ratio_on_rectangle(self):
        """2:1 rectangle should have aspect ratio 2.0."""
        nodes = np.array([
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [2.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ])
        elements = np.array([[9, 0, 1, 2, 3]])

        ar = _compute_aspect_ratio(nodes, elements)

        assert len(ar) == 1
        np.testing.assert_allclose(ar[0], 2.0, atol=1e-10)

    def test_aspect_ratio_multiple_elements(self):
        """Multiple elements should each have their own aspect ratio."""
        nodes = np.array([
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],  # square
            [2.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 1.0, 0.0], [2.0, 1.0, 0.0],  # 2:1 rect
        ])
        elements = np.array([
            [9, 0, 1, 2, 3],
            [9, 4, 5, 6, 7],
        ])

        ar = _compute_aspect_ratio(nodes, elements)

        assert len(ar) == 2
        np.testing.assert_allclose(ar[0], 1.0, atol=1e-10)
        np.testing.assert_allclose(ar[1], 2.0, atol=1e-10)

    def test_aspect_ratio_empty_for_no_elements(self):
        """Empty element array returns empty array."""
        nodes = np.zeros((4, 3))
        elements = np.zeros((0, 5), dtype=np.int64)

        ar = _compute_aspect_ratio(nodes, elements)

        assert len(ar) == 0


class TestComputeExpansionRatio:
    """Tests for _compute_expansion_ratio."""

    def test_expansion_ratio_on_uniform_mesh(self, tmp_path):
        """Uniform mesh should have expansion ratio 1.0."""
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (0.0, 1.0),
            (1.0, 1.0), (2.0, 1.0), (2.0, 0.0),
        ]
        elements = [
            (0, 1, 3, 2),
            (1, 5, 4, 3),
        ]
        mesh_file = tmp_path / "uniform.su2"
        _write_su2_mesh(mesh_file, nodes, elements)
        parsed = _parse_su2_mesh(mesh_file)

        er = _compute_expansion_ratio(parsed.nodes, parsed.elements)

        assert len(er) == 1  # One interior face
        np.testing.assert_allclose(er[0], 1.0, atol=1e-10)

    def test_expansion_ratio_on_nonuniform_mesh(self, tmp_path):
        """Adjacent elements with different sizes should have ER > 1."""
        # Two quads: left is 1x1, right is 2x1
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (3.0, 0.0),
            (0.0, 1.0), (1.0, 1.0), (3.0, 1.0),
        ]
        elements = [
            (0, 1, 4, 3),  # 1x1 quad
            (1, 2, 5, 4),  # 2x1 quad
        ]
        mesh_file = tmp_path / "nonuniform.su2"
        _write_su2_mesh(mesh_file, nodes, elements)
        parsed = _parse_su2_mesh(mesh_file)

        er = _compute_expansion_ratio(parsed.nodes, parsed.elements)

        assert len(er) == 1
        # Left area = 1.0, right area = 2.0, ER = 2.0/1.0 = 2.0
        np.testing.assert_allclose(er[0], 2.0, atol=1e-10)

    def test_expansion_ratio_empty_for_single_element(self):
        """Single element has no adjacent pairs."""
        nodes = np.array([
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        ])
        elements = np.array([[9, 0, 1, 2, 3]])

        er = _compute_expansion_ratio(nodes, elements)

        assert len(er) == 0


class TestElementCenter:
    """Tests for _element_center."""

    def test_center_of_unit_square(self):
        """Center of a unit square should be (0.5, 0.5, 0.0)."""
        nodes = np.array([
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        ])
        elem = np.array([9, 0, 1, 2, 3])

        center = _element_center(nodes, elem)

        np.testing.assert_allclose(center, [0.5, 0.5, 0.0])

    def test_center_of_triangle_element(self):
        """Center of a triangle (stored with 4 indices, last unused)."""
        nodes = np.array([
            [0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [1.0, 3.0, 0.0], [0.0, 0.0, 0.0],
        ])
        elem = np.array([9, 0, 1, 2, 3])

        center = _element_center(nodes, elem)

        # Mean of all 4 nodes including duplicate
        np.testing.assert_allclose(center, [0.75, 0.75, 0.0])


class TestElementArea:
    """Tests for _element_area_quad."""

    def test_area_of_unit_square(self):
        """Area of a unit square should be 1.0."""
        nodes = np.array([
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        ])
        elem = np.array([9, 0, 1, 2, 3])

        area = _element_area_quad(nodes, elem)

        np.testing.assert_allclose(area, 1.0)

    def test_area_of_rectangle(self):
        """Area of 2x3 rectangle should be 6.0."""
        nodes = np.array([
            [0.0, 0.0, 0.0], [3.0, 0.0, 0.0],
            [3.0, 2.0, 0.0], [0.0, 2.0, 0.0],
        ])
        elem = np.array([9, 0, 1, 2, 3])

        area = _element_area_quad(nodes, elem)

        np.testing.assert_allclose(area, 6.0)


class TestEdgeLength:
    """Tests for _edge_length."""

    def test_unit_length(self):
        """Distance from (0,0,0) to (1,0,0) should be 1.0."""
        nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

        length = _edge_length(nodes, 0, 1)

        np.testing.assert_allclose(length, 1.0)

    def test_diagonal_length(self):
        """Distance from (0,0,0) to (1,1,0) should be sqrt(2)."""
        nodes = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 0.0]])

        length = _edge_length(nodes, 0, 1)

        np.testing.assert_allclose(length, np.sqrt(2.0))


class TestCheckMeshQuality:
    """Tests for check_mesh_quality with actual mesh parsing."""

    def test_returns_result_on_valid_mesh(self, tmp_path):
        """check_mesh_quality should return a MeshQualityResult."""
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (0.0, 1.0),
            (1.0, 1.0), (2.0, 1.0), (2.0, 0.0),
        ]
        elements = [
            (0, 1, 3, 2),
            (1, 5, 4, 3),
        ]
        mesh_file = tmp_path / "test.su2"
        _write_su2_mesh(mesh_file, nodes, elements)

        result = check_mesh_quality(mesh_file)

        assert isinstance(result, MeshQualityResult)
        assert result.n_nodes == 6
        assert result.n_elements == 2
        assert result.has_negative_jacobians is False

    def test_fails_for_nonexistent_file(self, tmp_path):
        """check_mesh_quality should fail for non-existent file."""
        result = check_mesh_quality(tmp_path / "missing.su2")

        assert result.passed is False
        assert "does not exist" in result.notes

    def test_fails_for_empty_file(self, tmp_path):
        """check_mesh_quality should fail gracefully for empty file."""
        mesh_file = tmp_path / "empty.su2"
        mesh_file.write_text("")

        result = check_mesh_quality(mesh_file)

        assert result.passed is False
        assert "Failed to parse" in result.notes

    def test_passes_on_quality_mesh(self, tmp_path):
        """Uniform mesh should pass with default thresholds."""
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (0.0, 1.0),
            (1.0, 1.0), (2.0, 1.0), (2.0, 0.0),
        ]
        elements = [
            (0, 1, 3, 2),
            (1, 5, 4, 3),
        ]
        mesh_file = tmp_path / "good.su2"
        _write_su2_mesh(mesh_file, nodes, elements)

        result = check_mesh_quality(mesh_file)

        assert result.passed is True
        # Uniform mesh: orthogonality ~90, AR ~1.0, ER ~1.0
        assert result.min_orthogonality >= 20.0
        assert result.max_aspect_ratio <= 100.0
        assert result.max_expansion_ratio <= 2.0

    def test_fails_with_strict_thresholds(self, tmp_path):
        """Mesh should fail with unrealistically strict thresholds."""
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (0.0, 1.0),
            (1.0, 1.0), (2.0, 1.0), (2.0, 0.0),
        ]
        elements = [
            (0, 1, 3, 2),
            (1, 5, 4, 3),
        ]
        mesh_file = tmp_path / "test.su2"
        _write_su2_mesh(mesh_file, nodes, elements)

        # Require orthogonality > 95 degrees (impossible for this mesh)
        result = check_mesh_quality(mesh_file, min_orthogonality=95.0)

        assert result.passed is False

    def test_custom_thresholds(self, tmp_path):
        """check_mesh_quality should accept custom thresholds."""
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (0.0, 1.0),
            (1.0, 1.0), (2.0, 1.0), (2.0, 0.0),
        ]
        elements = [
            (0, 1, 3, 2),
            (1, 5, 4, 3),
        ]
        mesh_file = tmp_path / "test.su2"
        _write_su2_mesh(mesh_file, nodes, elements)

        result = check_mesh_quality(
            mesh_file,
            min_orthogonality=30.0,
            max_aspect_ratio=20.0,
            max_expansion_ratio=1.5,
        )

        assert isinstance(result, MeshQualityResult)

    def test_notes_include_metrics(self, tmp_path):
        """Notes string should contain metric summaries."""
        nodes = [
            (0.0, 0.0), (1.0, 0.0), (0.0, 1.0),
            (1.0, 1.0), (2.0, 1.0), (2.0, 0.0),
        ]
        elements = [
            (0, 1, 3, 2),
            (1, 5, 4, 3),
        ]
        mesh_file = tmp_path / "test.su2"
        _write_su2_mesh(mesh_file, nodes, elements)

        result = check_mesh_quality(mesh_file)

        assert "Nodes: 6" in result.notes
        assert "Elements: 2" in result.notes
        assert "Ortho:" in result.notes


class TestValidateSu2Mesh:
    """Tests for validate_su2_mesh."""

    def test_validate_with_all_markers(self, tmp_path):
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

    def test_validate_missing_markers(self, tmp_path):
        """validate_su2_mesh should fail when markers are missing."""
        mesh_file = tmp_path / "test.su2"
        mesh_file.write_text("no markers here")
        assert validate_su2_mesh(mesh_file) is False

    def test_validate_partial_markers(self, tmp_path):
        """validate_su2_mesh should fail with only some markers."""
        mesh_file = tmp_path / "test.su2"
        content = "\n".join([
            "MARKER_TAG= inlet",
            "MARKER_TAG= wall",
        ])
        mesh_file.write_text(content)
        assert validate_su2_mesh(mesh_file) is False

    def test_validate_nonexistent(self, tmp_path):
        """validate_su2_mesh should handle non-existent file."""
        assert validate_su2_mesh(tmp_path / "missing.su2") is False

    def test_validate_empty_file(self, tmp_path):
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
            n_nodes=0,
            n_elements=0,
            min_orthogonality=0.0,
            max_aspect_ratio=float("inf"),
            max_expansion_ratio=float("inf"),
            has_negative_jacobians=True,
            passed=False,
            notes="Negative Jacobians detected",
        )
        assert result.passed is False
        assert result.has_negative_jacobians is True
