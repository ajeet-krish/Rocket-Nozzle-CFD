"""Tests for mesh generation."""
import pytest
from pathlib import Path
from nozzle.config import NozzleConfig
from cfd.mesh import generate_nozzle_mesh, validate_mesh
from cfd.mesh_config import MeshConfig


class TestMeshGeneration:
    """Tests for structured O-grid mesh generation."""

    def test_mesh_generates_su2_file(self, tmp_path):
        """Mesh generation should produce a valid .su2 file."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=False,
            output_file=str(tmp_path / "test.su2"),
        )
        assert mesh_path.exists()
        assert mesh_path.stat().st_size > 0

    def test_mesh_has_all_markers(self, tmp_path):
        """Generated mesh should contain all required SU2 boundary markers."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=False,
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
            plume_extension=False,
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
            plume_extension=False,
            output_file=str(tmp_path / "test.su2"),
        )
        assert mesh_path.stat().st_size > 1000

    def test_mesh_with_custom_config(self, tmp_path):
        """Mesh generation should work with custom parameters."""
        nozzle_config = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        mesh_path = generate_nozzle_mesh(
            nozzle_config,
            n_axial=30,
            n_normal=40,
            plume_extension=False,
            output_file=str(tmp_path / "custom.su2"),
        )
        assert mesh_path.exists()

    def test_validate_mesh_returns_dict(self, tmp_path):
        """validate_mesh should return a dict with expected keys."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=False,
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
            plume_extension=False,
            output_file=str(tmp_path / "compat.su2"),
        )
        assert mesh_path.exists()


class TestMeshPlumeExtension:
    """Tests for plume extension zone."""

    def test_plume_mesh_generates_su2_file(self, tmp_path):
        """Mesh with plume extension should produce a valid .su2 file."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=True,
            output_file=str(tmp_path / "plume.su2"),
        )
        assert mesh_path.exists()
        assert mesh_path.stat().st_size > 0

    def test_plume_mesh_has_farfield_marker(self, tmp_path):
        """Plume mesh should have farfield boundary marker."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=True,
            output_file=str(tmp_path / "plume.su2"),
        )
        with open(mesh_path) as f:
            content = f.read()
        assert "MARKER_TAG= farfield" in content

    def test_plume_mesh_has_all_markers(self, tmp_path):
        """Plume mesh should have all required markers."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=True,
            output_file=str(tmp_path / "plume.su2"),
        )
        with open(mesh_path) as f:
            content = f.read()
        # Nozzle markers
        for marker in ["inlet", "wall", "symmetry"]:
            assert f"MARKER_TAG= {marker}" in content, (
                f"Missing marker: {marker}"
            )
        # Plume markers
        for marker in ["farfield", "plume_outlet"]:
            assert f"MARKER_TAG= {marker}" in content, (
                f"Missing marker: {marker}"
            )

    def test_plume_mesh_larger_than_no_plume(self, tmp_path):
        """Mesh with plume should be larger than without."""
        config = NozzleConfig()
        mesh_no_plume = generate_nozzle_mesh(
            config,
            plume_extension=False,
            output_file=str(tmp_path / "no_plume.su2"),
        )
        mesh_with_plume = generate_nozzle_mesh(
            config,
            plume_extension=True,
            output_file=str(tmp_path / "with_plume.su2"),
        )
        assert mesh_with_plume.stat().st_size > mesh_no_plume.stat().st_size

    def test_plume_custom_ratios(self, tmp_path):
        """Mesh generation should accept custom plume ratios."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=True,
            plume_length_ratio=15.0,
            plume_radius_ratio=4.0,
            output_file=str(tmp_path / "custom_plume.su2"),
        )
        assert mesh_path.exists()

    def test_no_plume_mesh_no_farfield(self, tmp_path):
        """Mesh without plume should not have farfield marker."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=False,
            output_file=str(tmp_path / "no_plume.su2"),
        )
        with open(mesh_path) as f:
            content = f.read()
        assert "MARKER_TAG= farfield" not in content
        assert "MARKER_TAG= plume_outlet" not in content


class TestMeshKeyPoints:
    """Tests for improved key point selection (10+ points)."""

    def test_mesh_with_many_key_points(self, tmp_path):
        """Mesh generation should use 10+ key points for accurate spline."""
        config = NozzleConfig(num_points=200)
        # The mesh should generate successfully with the improved key points
        mesh_path = generate_nozzle_mesh(
            config,
            n_axial=60,
            n_normal=30,
            plume_extension=False,
            output_file=str(tmp_path / "keypoints.su2"),
        )
        assert mesh_path.exists()
        assert mesh_path.stat().st_size > 1000

    def test_mesh_with_chamber(self, tmp_path):
        """Mesh should work with chamber geometry (3-section contour)."""
        config = NozzleConfig(
            chamber_length=0.2,
            throat_radius_of_curvature=0.02,
        )
        mesh_path = generate_nozzle_mesh(
            config,
            n_axial=80,
            n_normal=40,
            plume_extension=False,
            output_file=str(tmp_path / "chamber.su2"),
        )
        assert mesh_path.exists()

    def test_mesh_with_small_expansion_ratio(self, tmp_path):
        """Mesh should handle small expansion ratios."""
        config = NozzleConfig(expansion_ratio=2.0)
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=False,
            output_file=str(tmp_path / "small_ratio.su2"),
        )
        assert mesh_path.exists()

    def test_mesh_with_large_expansion_ratio(self, tmp_path):
        """Mesh should handle large expansion ratios."""
        config = NozzleConfig(expansion_ratio=50.0)
        mesh_path = generate_nozzle_mesh(
            config,
            n_axial=100,
            n_normal=50,
            plume_extension=False,
            output_file=str(tmp_path / "large_ratio.su2"),
        )
        assert mesh_path.exists()


class TestMeshZoneDistribution:
    """Tests for zone-based cell distribution."""

    def test_default_zone_distribution(self, tmp_path):
        """Default mesh should use increased resolution (120x60)."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            plume_extension=False,
            output_file=str(tmp_path / "default.su2"),
        )
        assert mesh_path.exists()
        # Default n_axial=120, n_normal=60 should produce more elements
        assert mesh_path.stat().st_size > 5000

    def test_custom_zone_resolution(self, tmp_path):
        """Custom resolution should produce valid mesh."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            n_axial=40,
            n_normal=20,
            plume_extension=False,
            output_file=str(tmp_path / "custom_res.su2"),
        )
        assert mesh_path.exists()

    def test_high_resolution_mesh(self, tmp_path):
        """High resolution mesh should be larger than low resolution."""
        config = NozzleConfig()
        mesh_low = generate_nozzle_mesh(
            config,
            n_axial=30,
            n_normal=15,
            plume_extension=False,
            output_file=str(tmp_path / "low.su2"),
        )
        mesh_high = generate_nozzle_mesh(
            config,
            n_axial=120,
            n_normal=60,
            plume_extension=False,
            output_file=str(tmp_path / "high.su2"),
        )
        assert mesh_high.stat().st_size > mesh_low.stat().st_size

    def test_rans_mode_mesh(self, tmp_path):
        """RANS mode should produce valid mesh with BL refinement."""
        config = NozzleConfig()
        mesh_path = generate_nozzle_mesh(
            config,
            n_axial=60,
            n_normal=40,
            rans_mode=True,
            plume_extension=False,
            output_file=str(tmp_path / "rans.su2"),
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
        assert mc.plume_radius_ratio == 3.0

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

    def test_plume_radius_ratio_default(self):
        """Default plume_radius_ratio should be 3.0."""
        mc = MeshConfig()
        assert mc.plume_radius_ratio == 3.0

    def test_plume_radius_ratio_custom(self):
        """Custom plume_radius_ratio should be accepted."""
        mc = MeshConfig(plume_radius_ratio=5.0)
        assert mc.plume_radius_ratio == 5.0

    def test_plume_radius_ratio_validation(self):
        """plume_radius_ratio < 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="plume_radius_ratio"):
            MeshConfig(plume_radius_ratio=0.5)

    def test_zone_distribution_adds_up(self):
        """n_axial should equal sum of all zone cells."""
        mc = MeshConfig(
            converging_cells=24,
            throat_cells=15,
            diverging_cells=72,
            plume_cells=24,
        )
        assert mc.n_axial == 24 + 15 + 72 + 24
