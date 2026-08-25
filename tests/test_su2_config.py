"""Tests for SU2 configuration file generation."""
import pytest
from pathlib import Path
from cfd.config import SU2NozzleConfig


class TestSU2NozzleConfig:
    """Tests for SU2NozzleConfig and .cfg file generation."""

    @pytest.fixture
    def default_config(self):
        """Default SU2 configuration."""
        return SU2NozzleConfig()

    @pytest.fixture
    def custom_config(self):
        """Custom SU2 configuration."""
        return SU2NozzleConfig(
            total_pressure=5e6,
            total_temperature=3000.0,
            static_pressure=50000.0,
            gamma=1.3,
            gas_constant=290.0,
            iterations=10000,
            cfl_number=2.0,
        )

    def test_default_values(self, default_config):
        """Verify default SU2 config values."""
        assert default_config.solver == "EULER"
        assert default_config.axisymmetric is True
        assert default_config.total_pressure == 10e6
        assert default_config.total_temperature == 3500.0
        assert default_config.static_pressure == 101325.0
        assert default_config.gamma == 1.4
        assert default_config.gas_constant == 287.058
        assert default_config.iterations == 5000
        assert default_config.cfl_number == 1.0

    def test_write_creates_file(self, default_config, tmp_path):
        """write() should create a .cfg file."""
        config_path = default_config.write(tmp_path)
        assert config_path.exists(), f"Config file should exist at {config_path}"
        assert config_path.name == "config.cfg"

    def test_cfg_contains_solver(self, default_config, tmp_path):
        """Config file should specify SOLVER=EULER."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert "SOLVER= EULER" in content

    def test_cfg_contains_axisymmetric(self, default_config, tmp_path):
        """Config file should specify AXISYMMETRIC= YES."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert "AXISYMMETRIC= YES" in content

    def test_cfg_contains_gamma(self, default_config, tmp_path):
        """Config file should contain gamma value."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert f"GAMMA_VALUE= {default_config.gamma}" in content

    def test_cfg_contains_gas_constant(self, default_config, tmp_path):
        """Config file should contain gas constant."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert f"GAS_CONSTANT= {default_config.gas_constant}" in content

    def test_cfg_contains_boundary_markers(self, default_config, tmp_path):
        """Config file should define boundary markers."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert "MARKER_EULER=" in content
        assert "MARKER_SYM=" in content
        assert "MARKER_TOTAL_CONDITIONS=" in content
        assert "MARKER_OUTLET=" in content

    def test_cfg_contains_iterations(self, default_config, tmp_path):
        """Config file should contain iteration count."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert f"ITER= {default_config.iterations}" in content

    def test_cfg_contains_cfl(self, default_config, tmp_path):
        """Config file should contain CFL number."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert f"CFL_NUMBER= {default_config.cfl_number}" in content

    def test_cfg_contains_output_config(self, default_config, tmp_path):
        """Config file should have output settings."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert "TABULAR_FORMAT= CSV" in content
        assert "OUTPUT_FILES=" in content

    def test_cfg_contains_linear_solver(self, default_config, tmp_path):
        """Config file should have linear solver settings."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert "LINEAR_SOLVER= FGMRES" in content
        assert "LINEAR_SOLVER_PREC= ILU" in content

    def test_custom_config_values_in_file(self, custom_config, tmp_path):
        """Custom config values should appear in file."""
        config_path = custom_config.write(tmp_path)
        content = config_path.read_text()
        assert f"GAMMA_VALUE= {custom_config.gamma}" in content
        assert f"ITER= {custom_config.iterations}" in content
        assert f"CFL_NUMBER= {custom_config.cfl_number}" in content
        assert f"GAS_CONSTANT= {custom_config.gas_constant}" in content

    def test_mesh_filename_override(self, default_config, tmp_path):
        """Mesh filename can be overridden."""
        config_path = default_config.write(tmp_path, mesh_filename="custom.su2")
        content = config_path.read_text()
        assert "MESH_FILENAME= custom.su2" in content

    def test_mesh_filename_default(self, default_config, tmp_path):
        """Default mesh filename should be used."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert f"MESH_FILENAME= {default_config.mesh_filename}" in content

    def test_returned_path_is_in_directory(self, default_config, tmp_path):
        """Returned path should be inside the specified directory."""
        config_path = default_config.write(tmp_path)
        assert config_path.parent == tmp_path

    def test_config_file_not_empty(self, default_config, tmp_path):
        """Config file should not be empty."""
        config_path = default_config.write(tmp_path)
        content = config_path.read_text()
        assert len(content) > 100, "Config file should contain substantial content"
