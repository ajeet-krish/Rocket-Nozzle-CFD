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
        assert config.half_angle == pytest.approx(13.84, abs=0.01)
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
            converging_length=0.2,
            diverging_length=1.0,
            num_points=500,
        )
        assert config.throat_radius == 0.1
        assert config.expansion_ratio == 25.0
        assert config.half_angle == pytest.approx(21.80, abs=0.01)
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

    def test_half_angle_derived_from_geometry(self):
        """half_angle should be computed from expansion_ratio and diverging_length."""
        config = NozzleConfig(
            throat_radius=0.05, expansion_ratio=12.0, diverging_length=0.5,
        )
        expected_exit = 0.05 * math.sqrt(12.0)
        expected_angle = math.degrees(math.atan(
            (expected_exit - 0.05) / 0.5
        ))
        assert config.half_angle == pytest.approx(expected_angle, rel=1e-10)

    def test_bell_fraction_default(self):
        """Default NozzleConfig should not have bell_fraction (removed)."""
        config = NozzleConfig()
        assert not hasattr(config, "bell_fraction")

    def test_ideal_length(self):
        """Ideal bell length should follow Rao formula."""
        config = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        expected = 0.5 * (
            math.sqrt(config.exit_radius) - math.sqrt(config.throat_radius)
        ) * math.sqrt(config.throat_radius + config.exit_radius)
        assert config.ideal_length == pytest.approx(expected, rel=1e-10)


class TestNozzleConfigValidation:
    """Tests for NozzleConfig.validate() classmethod."""

    def test_validate_default(self):
        """Default config should pass validation."""
        config = NozzleConfig.validate()
        assert config.throat_radius == 0.05

    def test_validate_custom(self):
        """Custom valid config should pass validation."""
        config = NozzleConfig.validate(
            throat_radius=0.1, expansion_ratio=25.0, diverging_length=1.0,
        )
        assert config.throat_radius == 0.1
        assert config.expansion_ratio == 25.0

    def test_validate_negative_throat_radius(self):
        """Negative throat_radius should raise ValueError."""
        with pytest.raises(ValueError, match="throat_radius must be > 0"):
            NozzleConfig.validate(throat_radius=-0.05)

    def test_validate_zero_throat_radius(self):
        """Zero throat_radius should raise ValueError."""
        with pytest.raises(ValueError, match="throat_radius must be > 0"):
            NozzleConfig.validate(throat_radius=0.0)

    def test_validate_low_expansion_ratio(self):
        """Expansion ratio < 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="expansion_ratio must be >= 1.0"):
            NozzleConfig.validate(expansion_ratio=0.5)

    def test_validate_negative_diverging_length(self):
        """Negative diverging_length should raise ValueError."""
        with pytest.raises(ValueError, match="diverging_length must be > 0"):
            NozzleConfig.validate(diverging_length=-1.0)

    def test_validate_too_few_points(self):
        """num_points < 2 should raise ValueError."""
        with pytest.raises(ValueError, match="num_points must be >= 2"):
            NozzleConfig.validate(num_points=1)

    def test_validate_returns_frozen(self):
        """Validated config should still be frozen."""
        config = NozzleConfig.validate()
        with pytest.raises(AttributeError):
            config.throat_radius = 0.1  # type: ignore[misc]
