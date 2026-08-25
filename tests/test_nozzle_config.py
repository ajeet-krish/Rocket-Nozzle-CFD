"""Tests for NozzleConfig dataclass."""
import math
import pytest
from nozzle.config import NozzleConfig


class TestNozzleConfig:
    """Tests for NozzleConfig properties and defaults."""

    def test_default_values(self):
        """Verify default configuration values."""
        config = NozzleConfig()
        assert config.throat_radius == 0.05
        assert config.expansion_ratio == 12.0
        assert config.half_angle == 15.0
        assert config.converging_length == 0.1
        assert config.diverging_length == 0.5
        assert config.num_points == 200

    def test_exit_radius_calculation(self):
        """Exit radius = throat_radius * sqrt(expansion_ratio)."""
        config = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        expected = 0.05 * math.sqrt(12.0)
        assert config.exit_radius == pytest.approx(expected, rel=1e-10), (
            f"Exit radius should be {expected:.6f}m, got {config.exit_radius:.6f}m"
        )

    def test_exit_radius_custom(self):
        """Test exit radius with different parameters."""
        config = NozzleConfig(throat_radius=0.1, expansion_ratio=4.0)
        assert config.exit_radius == pytest.approx(0.2, rel=1e-10)

    def test_throat_area_calculation(self):
        """Throat area = pi * throat_radius^2."""
        config = NozzleConfig(throat_radius=0.05)
        expected = math.pi * 0.05**2
        assert config.throat_area == pytest.approx(expected, rel=1e-10)

    def test_exit_area_calculation(self):
        """Exit area = pi * exit_radius^2."""
        config = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        expected = math.pi * config.exit_radius**2
        assert config.exit_area == pytest.approx(expected, rel=1e-10)

    def test_exit_area_equals_expansion_ratio_times_throat_area(self):
        """Exit area / throat area should equal expansion_ratio."""
        config = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        area_ratio = config.exit_area / config.throat_area
        assert area_ratio == pytest.approx(config.expansion_ratio, rel=1e-10), (
            f"Area ratio should equal expansion ratio {config.expansion_ratio}, "
            f"got {area_ratio}"
        )

    def test_frozen_dataclass(self):
        """NozzleConfig should be immutable (frozen)."""
        config = NozzleConfig()
        with pytest.raises(AttributeError):
            config.throat_radius = 0.1  # type: ignore[misc]

    def test_custom_config(self):
        """Test creating config with custom values."""
        config = NozzleConfig(
            throat_radius=0.1,
            expansion_ratio=25.0,
            half_angle=20.0,
            converging_length=0.2,
            diverging_length=1.0,
            num_points=500,
        )
        assert config.throat_radius == 0.1
        assert config.expansion_ratio == 25.0
        assert config.half_angle == 20.0
        assert config.converging_length == 0.2
        assert config.diverging_length == 1.0
        assert config.num_points == 500

    def test_equal_configs(self):
        """Two configs with same params should be equal."""
        c1 = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        c2 = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        assert c1 == c2

    def test_different_configs_not_equal(self):
        """Configs with different params should not be equal."""
        c1 = NozzleConfig(throat_radius=0.05)
        c2 = NozzleConfig(throat_radius=0.1)
        assert c1 != c2
