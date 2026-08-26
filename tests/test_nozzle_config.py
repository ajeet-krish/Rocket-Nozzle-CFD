"""Tests for NozzleConfig dataclass."""
import math
import pytest
from nozzle.config import NozzleConfig
from nozzle.presets import merlin_1d, raptor_sl, generic_test


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


class TestNozzleConfigV2Fields:
    """Tests for NozzleConfig v2 fields and defaults."""

    def test_v2_default_values(self):
        """Verify v2 default field values."""
        config = NozzleConfig()
        assert config.chamber_length == 0.0
        assert config.chamber_radius == 0.0
        assert config.convergent_half_angle == 45.0
        assert config.throat_radius_of_curvature == 0.0
        assert config.theta_n == 30.0

    def test_v2_custom_values(self):
        """Verify v2 fields accept custom values."""
        config = NozzleConfig(
            chamber_length=0.1,
            chamber_radius=0.0833,
            convergent_half_angle=30.0,
            throat_radius_of_curvature=0.04,
            theta_n=25.0,
        )
        assert config.chamber_length == 0.1
        assert config.chamber_radius == 0.0833
        assert config.convergent_half_angle == 30.0
        assert config.throat_radius_of_curvature == 0.04
        assert config.theta_n == 25.0

    def test_v2_frozen_dataclass(self):
        """NozzleConfig v2 should still be immutable."""
        config = NozzleConfig()
        with pytest.raises(AttributeError):
            config.chamber_length = 0.1  # type: ignore[misc]

    def test_effective_inlet_radius_default(self):
        """Default: chamber_radius=0, so inlet = 1.5x throat."""
        config = NozzleConfig(throat_radius=0.05)
        assert config.effective_inlet_radius == pytest.approx(0.075, rel=1e-10)

    def test_effective_inlet_radius_custom(self):
        """Custom chamber_radius should override the default."""
        config = NozzleConfig(throat_radius=0.05, chamber_radius=0.1)
        assert config.effective_inlet_radius == pytest.approx(0.1, rel=1e-10)

    def test_total_length_default(self):
        """Default total_length = converging + diverging (no chamber)."""
        config = NozzleConfig(
            converging_length=0.1, diverging_length=0.5
        )
        assert config.total_length == pytest.approx(0.6, rel=1e-10)

    def test_total_length_with_chamber(self):
        """total_length includes chamber_length when set."""
        config = NozzleConfig(
            chamber_length=0.1, converging_length=0.15, diverging_length=0.5
        )
        assert config.total_length == pytest.approx(0.75, rel=1e-10)


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

    def test_validate_negative_chamber_length(self):
        """Negative chamber_length should raise ValueError."""
        with pytest.raises(ValueError, match="chamber_length must be >= 0"):
            NozzleConfig.validate(chamber_length=-0.1)

    def test_validate_negative_chamber_radius(self):
        """Negative chamber_radius should raise ValueError."""
        with pytest.raises(ValueError, match="chamber_radius must be >= 0"):
            NozzleConfig.validate(chamber_radius=-0.05)

    def test_validate_convergent_half_angle_too_low(self):
        """convergent_half_angle < 10 should raise ValueError."""
        with pytest.raises(ValueError, match="convergent_half_angle must be between 10 and 80"):
            NozzleConfig.validate(convergent_half_angle=5.0)

    def test_validate_convergent_half_angle_too_high(self):
        """convergent_half_angle > 80 should raise ValueError."""
        with pytest.raises(ValueError, match="convergent_half_angle must be between 10 and 80"):
            NozzleConfig.validate(convergent_half_angle=85.0)

    def test_validate_negative_throat_radius_of_curvature(self):
        """Negative throat_radius_of_curvature should raise ValueError."""
        with pytest.raises(ValueError, match="throat_radius_of_curvature must be >= 0"):
            NozzleConfig.validate(throat_radius_of_curvature=-0.01)

    def test_validate_theta_n_too_low(self):
        """theta_n < 5 should raise ValueError."""
        with pytest.raises(ValueError, match="theta_n must be between 5 and 60"):
            NozzleConfig.validate(theta_n=3.0)

    def test_validate_theta_n_too_high(self):
        """theta_n > 60 should raise ValueError."""
        with pytest.raises(ValueError, match="theta_n must be between 5 and 60"):
            NozzleConfig.validate(theta_n=65.0)

    def test_validate_v2_boundary_values(self):
        """Boundary values for v2 fields should pass."""
        config = NozzleConfig.validate(
            chamber_length=0.0,
            chamber_radius=0.0,
            convergent_half_angle=10.0,
            throat_radius_of_curvature=0.0,
            theta_n=5.0,
        )
        assert config.convergent_half_angle == 10.0
        assert config.theta_n == 5.0


class TestNozzleConfigPresets:
    """Tests for preset nozzle configurations."""

    def test_merlin_1d(self):
        """Merlin 1D preset should have correct geometry."""
        config = merlin_1d()
        assert config.throat_radius == 0.0825
        assert config.expansion_ratio == 16.0
        assert config.chamber_length == pytest.approx(0.09993, rel=1e-3)
        assert config.chamber_radius == 0.0833
        assert config.convergent_half_angle == 45.0
        assert config.throat_radius_of_curvature == 0.04
        assert config.theta_n == 30.0
        assert config.num_points == 300
        assert config.exit_radius == pytest.approx(
            0.0825 * math.sqrt(16.0), rel=1e-10
        )
        assert config.total_length == pytest.approx(
            0.09993 + 0.15 + 0.334, rel=1e-3
        )

    def test_raptor_sl(self):
        """Raptor SL preset should have correct geometry."""
        config = raptor_sl()
        assert config.throat_radius == 0.0825
        assert config.expansion_ratio == 34.0
        assert config.chamber_length == 0.1
        assert config.chamber_radius == 0.0833
        assert config.convergent_half_angle == 45.0
        assert config.throat_radius_of_curvature == 0.04
        assert config.theta_n == 30.0
        assert config.num_points == 300
        assert config.exit_radius == pytest.approx(
            0.0825 * math.sqrt(34.0), rel=1e-10
        )

    def test_generic_test(self):
        """Generic test preset should match v1 defaults."""
        config = generic_test()
        assert config.throat_radius == 0.05
        assert config.expansion_ratio == 12.0
        assert config.converging_length == 0.1
        assert config.diverging_length == 0.5
        assert config.num_points == 200
        # v1 compatible: no chamber, linear convergent
        assert config.chamber_length == 0.0
        assert config.chamber_radius == 0.0
        assert config.throat_radius_of_curvature == 0.0
        assert config.effective_inlet_radius == pytest.approx(0.075, rel=1e-10)
        assert config.total_length == pytest.approx(0.6, rel=1e-10)

    def test_presets_pass_validation(self):
        """All presets should pass validation."""
        for preset_fn in [merlin_1d, raptor_sl, generic_test]:
            config = preset_fn()
            # Re-validate to ensure all fields are within range
            NozzleConfig.validate(**config.__dict__)

    def test_generic_test_v1_equivalence(self):
        """Generic test preset should produce identical geometry to v1 defaults."""
        v1_config = NozzleConfig(
            throat_radius=0.05,
            expansion_ratio=12.0,
            converging_length=0.1,
            diverging_length=0.5,
            num_points=200,
        )
        preset_config = generic_test()
        assert v1_config == preset_config
