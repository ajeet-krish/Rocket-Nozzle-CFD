"""Tests for mesh generation."""
import pytest
from pathlib import Path
from nozzle.config import NozzleConfig
from cfd.mesh import generate_nozzle_mesh, validate_mesh, _compute_zone_fractions, _compute_zone_indices
from cfd.mesh_config import MeshConfig


class TestMeshGeneration:
    """Tests for structured O-grid mesh generation."""

    def test_mesh_generates_su2_file(self, tmp_path):
        """Mesh generation should produce a valid .su2 file."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            output_file=str(tmp_path / "test.su2"),
        )
        assert mesh_path.exists()
        assert mesh_path.stat().st_size > 0

    def test_mesh_has_all_markers(self, tmp_path):
        """Generated mesh should contain all required SU2 boundary markers."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            output_file=str(tmp_path / "test.su2"),
        )
        with open(mesh_path) as f:
            content = f.read()
        for marker in ["inlet", "outlet", "wall", "symmetry"]:
            assert f"MARKER_TAG= {marker}" in content, (
                f"Missing marker: {marker}"
            )

    def test_mesh_has_fluid_domain(self, tmp_path):
        """Generated mesh should have elements (fluid domain)."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            output_file=str(tmp_path / "test.su2"),
        )
        with open(mesh_path) as f:
            content = f.read()
        # SU2 mesh files start with NDIME and NELEM headers
        assert "NDIME= 2" in content
        assert "NELEM=" in content

    def test_mesh_file_nonempty(self, tmp_path):
        """Mesh file should have substantial content."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            output_file=str(tmp_path / "test.su2"),
        )
        assert mesh_path.stat().st_size > 1000

    def test_mesh_with_custom_config(self, tmp_path):
        """Mesh generation should work with custom MeshConfig."""
        nozzle_config = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        mesh_config = MeshConfig(
            converging_cells=20,
            throat_cells=15,
            diverging_cells=30,
            plume_cells=20,
            n_normal=40,
        )
        mesh_path = generate_nozzle_mesh(
            nozzle_config,
            output_file=str(tmp_path / "custom.su2"),
            mesh_config=mesh_config,
        )
        assert mesh_path.exists()

    def test_validate_mesh_returns_dict(self, tmp_path):
        """validate_mesh should return a dict with expected keys."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            output_file=str(tmp_path / "test.su2"),
        )
        result = validate_mesh(mesh_path)
        assert "exists" in result
        assert "file_size_bytes" in result
        assert result["exists"] is True
        assert result["file_size_bytes"] > 0

    def test_validate_mesh_nonexistent(self, tmp_path):
        """validate_mesh should handle non-existent files."""
        result = validate_mesh(tmp_path / "missing.su2")
        assert result["exists"] is False
        assert result["file_size_bytes"] == 0

    def test_backward_compatible_api(self, tmp_path):
        """Original API signature (n_axial, n_normal, etc.) should still work."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            n_axial=100,
            n_normal=40,
            first_cell_height=1e-5,
            output_file=str(tmp_path / "compat.su2"),
        )
        assert mesh_path.exists()


class TestMeshConfig:
    """Tests for MeshConfig dataclass."""

    def test_default_values(self):
        """Verify default MeshConfig values."""
        mc = MeshConfig()
        assert mc.converging_cells == 40
        assert mc.throat_cells == 30
        assert mc.diverging_cells == 70
        assert mc.plume_cells == 60
        assert mc.n_normal == 80
        assert mc.first_cell_height == 1e-6
        assert mc.growth_ratio == 1.15
        assert mc.plume_length_ratio == 30.0

    def test_n_axial_property(self):
        """n_axial should be sum of all zone cell counts."""
        mc = MeshConfig(
            converging_cells=10,
            throat_cells=20,
            diverging_cells=30,
            plume_cells=40,
        )
        assert mc.n_axial == 100

    def test_frozen_dataclass(self):
        """MeshConfig should be immutable."""
        mc = MeshConfig()
        with pytest.raises(AttributeError):
            mc.converging_cells = 50  # type: ignore[misc]

    def test_custom_config(self):
        """Custom MeshConfig should accept valid parameters."""
        mc = MeshConfig(
            converging_cells=25,
            throat_cells=20,
            diverging_cells=50,
            plume_cells=30,
            n_normal=60,
            first_cell_height=5e-7,
            growth_ratio=1.2,
        )
        assert mc.converging_cells == 25
        assert mc.first_cell_height == 5e-7


class TestZoneFractions:
    """Tests for zone fraction computation."""

    def test_fractions_sum_to_one(self):
        """Zone fractions should span [0, 1]."""
        mc = MeshConfig()
        f1, f2, f3 = _compute_zone_fractions(mc)
        assert 0 < f1 < f2 < f3 <= 1.0

    def test_fractions_proportional_to_cells(self):
        """Fractions should be proportional to cell counts."""
        mc = MeshConfig(converging_cells=10, throat_cells=10,
                         diverging_cells=10, plume_cells=10)
        f1, f2, f3 = _compute_zone_fractions(mc)
        assert f1 == pytest.approx(0.25, abs=0.01)
        assert f2 == pytest.approx(0.50, abs=0.01)
        assert f3 == pytest.approx(0.75, abs=0.01)


class TestZoneIndices:
    """Tests for zone index computation."""

    def test_indices_within_bounds(self):
        """Zone indices should be within contour bounds."""
        n = 200
        fracs = (0.2, 0.35, 0.7)
        i1, i2, i3 = _compute_zone_indices(n, fracs)
        assert 0 < i1 < i2 < i3 < n

    def test_indices_increase(self):
        """Zone indices should be strictly increasing."""
        n = 100
        fracs = (0.25, 0.40, 0.75)
        i1, i2, i3 = _compute_zone_indices(n, fracs)
        assert i1 < i2 < i3
