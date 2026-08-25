"""Tests for RANS configuration."""
import pytest
from pathlib import Path

from cfd.rans_config import SU2RANSConfig


class TestSU2RANSConfig:
    """Tests for SU2RANSConfig and .cfg file generation."""

    def test_default_values(self) -> None:
        """Verify default RANS config values."""
        config = SU2RANSConfig()
        assert config.turb_model == "SST"
        assert config.wall_heat_flux == 0.0
        assert config.wall_temperature == 300.0
        assert config.freestream_turbulence_intensity == 0.05
        assert config.freestream_viscosity_ratio == 10.0
        assert config.conv_num_method_turb == "SCALAR_UPWIND"
        assert config.muscl_turb is False

    def test_inherits_euler_defaults(self) -> None:
        """RANS config should inherit Euler defaults."""
        config = SU2RANSConfig()
        assert config.total_pressure == 10e6
        assert config.total_temperature == 3500.0
        assert config.static_pressure == 101325.0
        assert config.gamma == 1.4
        assert config.gas_constant == 287.058

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """write() should create a config_rans.cfg file."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        assert config_path.exists()
        assert config_path.name == "config_rans.cfg"

    def test_cfg_contains_rans(self, tmp_path: Path) -> None:
        """Config should specify SOLVER=RANS."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert "SOLVER= RANS" in content

    def test_cfg_contains_turb_model(self, tmp_path: Path) -> None:
        """Config should specify KIND_TURB_MODEL=SST."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert "KIND_TURB_MODEL= SST" in content

    def test_cfg_contains_wall_heatflux(self, tmp_path: Path) -> None:
        """Config should contain MARKER_HEATFLUX."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert "MARKER_HEATFLUX" in content

    def test_cfg_contains_turb_numerics(self, tmp_path: Path) -> None:
        """Config should contain turbulence numerics."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert "CONV_NUM_METHOD_TURB= SCALAR_UPWIND" in content
        assert "MUSCL_TURB= NO" in content
        assert "TIME_DISCRE_TURB= EULER_IMPLICIT" in content

    def test_cfg_contains_axisymmetric(self, tmp_path: Path) -> None:
        """Config should specify AXISYMMETRIC=YES."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert "AXISYMMETRIC= YES" in content

    def test_cfg_contains_cfl_adapt(self, tmp_path: Path) -> None:
        """Config should have CFL adaptation enabled."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert "CFL_ADAPT= YES" in content
        assert "CFL_ADAPT_PARAM" in content

    def test_cfg_contains_turb_output_fields(self, tmp_path: Path) -> None:
        """Config should output turbulence fields."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert "RMS_TKE" in content
        assert "RMS_DENSITY" in content

    def test_custom_turb_model(self, tmp_path: Path) -> None:
        """Custom turbulence model should appear in config."""
        config = SU2RANSConfig(turb_model="SA")
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert "KIND_TURB_MODEL= SA" in content

    def test_custom_heat_flux(self, tmp_path: Path) -> None:
        """Custom heat flux should appear in config."""
        config = SU2RANSConfig(wall_heat_flux=1000.0)
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert "MARKER_HEATFLUX= ( wall, 1000.0 )" in content

    def test_returned_path_is_in_directory(self, tmp_path: Path) -> None:
        """Returned path should be inside the specified directory."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        assert config_path.parent == tmp_path

    def test_config_file_not_empty(self, tmp_path: Path) -> None:
        """Config file should not be empty."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert len(content) > 100

    def test_mesh_filename_override(self, tmp_path: Path) -> None:
        """Mesh filename can be overridden."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path, mesh_filename="custom.su2")
        content = config_path.read_text()
        assert "MESH_FILENAME= custom.su2" in content

    def test_mesh_filename_default(self, tmp_path: Path) -> None:
        """Default mesh filename should be used."""
        config = SU2RANSConfig()
        config_path = config.write(tmp_path)
        content = config_path.read_text()
        assert f"MESH_FILENAME= {config.mesh_filename}" in content
