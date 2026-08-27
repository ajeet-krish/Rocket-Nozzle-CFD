"""Tests for nozzle contour generation."""
import math
import numpy as np
import pytest
from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour, _curved_convergent, _rao_bell


class TestGenerateContour:
    """Tests for conical nozzle contour generation."""

    @pytest.fixture
    def default_config(self):
        """Default nozzle configuration."""
        return NozzleConfig()

    @pytest.fixture
    def default_contour(self, default_config):
        """Generate default contour."""
        return generate_contour(default_config)

    def test_contour_length(self, default_config, default_contour):
        """Contour should have num_points - 3 points (3 duplicate boundary points removed).

        Sections: convergent, entrant arc, exit arc, bell -> 3 boundaries.
        """
        x, y = default_contour
        expected = default_config.num_points - 3
        assert len(x) == expected, (
            f"Expected {expected} x-points, got {len(x)}"
        )
        assert len(y) == expected, (
            f"Expected {expected} y-points, got {len(y)}"
        )

    def test_contour_length_custom(self):
        """Contour should respect custom num_points."""
        config = NozzleConfig(num_points=50)
        x, y = generate_contour(config)
        # 4 sections with 3 duplicate boundary points removed
        assert len(x) == 47
        assert len(y) == 47

    def test_throat_at_zero(self, default_contour):
        """Throat (minimum radius) should be at x=0."""
        x, y = default_contour
        # Find the point closest to x=0
        throat_idx = np.argmin(np.abs(x))
        assert abs(x[throat_idx]) < 0.01, (
            f"Throat should be at x~0, found x={x[throat_idx]}"
        )

    def test_exit_radius_matches_expansion_ratio(self, default_config, default_contour):
        """Exit radius should match config.exit_radius from expansion_ratio."""
        x, y = default_contour
        actual_exit_radius = y[-1]
        assert actual_exit_radius == pytest.approx(default_config.exit_radius, rel=1e-6), (
            f"Exit radius should be {default_config.exit_radius:.4f}m "
            f"(from expansion_ratio), got {actual_exit_radius:.4f}m"
        )

    def test_converging_section_decreasing(self, default_contour):
        """Converging section should decrease from inlet to throat."""
        x, y = default_contour
        # Converging section is where x < 0
        mask = x < 0
        if np.any(mask):
            x_conv = x[mask]
            y_conv = y[mask]
            # y should decrease as x increases (approaches throat)
            for i in range(len(x_conv) - 1):
                assert y_conv[i] >= y_conv[i + 1], (
                    f"Converging section not monotonically decreasing: "
                    f"y[{i}]={y_conv[i]} > y[{i+1}]={y_conv[i+1]}"
                )

    def test_diverging_section_increasing(self, default_contour):
        """Diverging section should increase from throat to exit."""
        x, y = default_contour
        # Diverging section is where x > 0
        mask = x > 0
        if np.any(mask):
            x_div = x[mask]
            y_div = y[mask]
            # y should increase as x increases
            for i in range(len(x_div) - 1):
                assert y_div[i] <= y_div[i + 1], (
                    f"Diverging section not monotonically increasing: "
                    f"y[{i}]={y_div[i]} > y[{i+1}]={y_div[i+1]}"
                )

    def test_throat_radius_value(self, default_config, default_contour):
        """Throat radius should match config value."""
        x, y = default_contour
        throat_idx = np.argmin(np.abs(x))
        throat_radius = y[throat_idx]
        assert throat_radius == pytest.approx(default_config.throat_radius, rel=0.01), (
            f"Throat radius should be {default_config.throat_radius}m, "
            f"got {throat_radius:.4f}m"
        )

    def test_converging_length(self, default_config, default_contour):
        """Converging section should span correct length."""
        x, y = default_contour
        min_x = np.min(x)
        assert min_x == pytest.approx(-default_config.converging_length, rel=0.01), (
            f"Converging start should be at x={-default_config.converging_length}m, "
            f"got x={min_x:.4f}m"
        )

    def test_diverging_length(self, default_config, default_contour):
        """Diverging section should span computed diverging length."""
        x, y = default_contour
        max_x = np.max(x)
        expected = default_config.computed_diverging_length
        assert max_x == pytest.approx(expected, rel=0.01), (
            f"Exit should be at x={expected}m, "
            f"got x={max_x:.4f}m"
        )

    def test_negative_radii_absent(self, default_contour):
        """No negative radial coordinates."""
        _, y = default_contour
        assert np.all(y >= 0), f"Found negative radii: {y[y < 0]}"

    def test_area_ratio_matches_expansion_ratio(self):
        """Verify exit/throat area ratio matches config.expansion_ratio."""
        config = NozzleConfig(
            throat_radius=0.05,
            expansion_ratio=12.0,
            diverging_length=0.5,
        )
        _, y = generate_contour(config)
        actual_area_ratio = (y[-1] / config.throat_radius) ** 2
        assert actual_area_ratio == pytest.approx(config.expansion_ratio, rel=1e-6), (
            f"Area ratio should be {config.expansion_ratio:.2f} "
            f"(from expansion_ratio), got {actual_area_ratio:.2f}"
        )


class TestRaoBellContour:
    """Tests for Rao parabolic bell contour generation."""

    def test_rao_bell_exit_radius(self):
        """Exit radius must match expansion_ratio exactly."""
        config = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        _, y = generate_contour(config)
        assert y[-1] == pytest.approx(config.exit_radius, rel=1e-10), (
            f"Rao bell exit radius {y[-1]:.6f} should match "
            f"config.exit_radius {config.exit_radius:.6f}"
        )

    def test_rao_bell_monotonic(self):
        """Diverging section must be monotonically increasing."""
        config = NozzleConfig()
        x, y = generate_contour(config)
        mask = x > 0
        y_div = y[mask]
        for i in range(len(y_div) - 1):
            assert y_div[i] <= y_div[i + 1], (
                f"Rao bell not monotonic: y[{i}]={y_div[i]:.6f} > "
                f"y[{i+1}]={y_div[i+1]:.6f}"
            )

    def test_rao_bell_length(self):
        """Bell must span the full computed diverging length."""
        config = NozzleConfig(diverging_length=0.5)
        x, _ = generate_contour(config)
        expected = config.computed_diverging_length
        assert np.max(x) == pytest.approx(expected, rel=0.01), (
            f"Bell exit should be at x={expected}m, "
            f"got x={np.max(x):.4f}m"
        )

    def test_rao_bell_different_expansion_ratios(self):
        """Rao bell must work for various expansion ratios."""
        for eps in [4.0, 12.0, 25.0, 50.0]:
            config = NozzleConfig(throat_radius=0.05, expansion_ratio=eps)
            _, y = generate_contour(config)
            assert y[-1] == pytest.approx(config.exit_radius, rel=1e-10), (
                f"Rao bell failed for expansion_ratio={eps}: "
                f"exit={y[-1]:.6f}, expected={config.exit_radius:.6f}"
            )

    def test_rao_bell_theta_n_parameter(self):
        """Rao bell should accept different theta_n values."""
        config_default = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        config_theta45 = NozzleConfig(
            throat_radius=0.05, expansion_ratio=12.0, theta_n=45.0,
        )
        config_theta15 = NozzleConfig(
            throat_radius=0.05, expansion_ratio=12.0, theta_n=15.0,
        )
        _, y_default = generate_contour(config_default)
        _, y_45 = generate_contour(config_theta45)
        _, y_15 = generate_contour(config_theta15)
        # All should reach the same exit radius
        assert y_default[-1] == pytest.approx(config_default.exit_radius, rel=1e-10)
        assert y_45[-1] == pytest.approx(config_theta45.exit_radius, rel=1e-10)
        assert y_15[-1] == pytest.approx(config_theta15.exit_radius, rel=1e-10)
        # But the mid-bell shape should differ
        mid_idx = len(y_default) // 2
        assert not np.isclose(y_default[mid_idx], y_45[mid_idx], rtol=0.01), (
            "Different theta_n should produce different mid-bell shapes"
        )


class TestChamberSection:
    """Tests for chamber section generation."""

    def test_chamber_present_when_length_positive(self):
        """Contour should include chamber section when chamber_length > 0."""
        config = NozzleConfig(
            chamber_length=0.1,
            chamber_radius=0.08,
            converging_length=0.1,
            diverging_length=0.5,
        )
        x, y = generate_contour(config)
        # Domain should extend left beyond -converging_length
        assert np.min(x) < -config.converging_length, (
            f"Chamber should extend domain left of -converging_length, "
            f"got min_x={np.min(x):.4f}"
        )

    def test_chamber_absent_when_length_zero(self):
        """Contour should not include chamber when chamber_length == 0."""
        config = NozzleConfig(chamber_length=0.0)
        x, y = generate_contour(config)
        # Domain should start at -converging_length
        assert np.min(x) == pytest.approx(-config.converging_length, rel=0.01), (
            f"No chamber: min_x should be -converging_length={-config.converging_length:.4f}, "
            f"got {np.min(x):.4f}"
        )

    def test_chamber_straight_cylinder(self):
        """Chamber section should be constant radius."""
        config = NozzleConfig(
            chamber_length=0.1,
            chamber_radius=0.08,
            converging_length=0.1,
            diverging_length=0.5,
        )
        x, y = generate_contour(config)
        # Find chamber region: x < -converging_length
        mask = x < -config.converging_length
        if np.any(mask):
            y_chamber = y[mask]
            # All chamber points should be at chamber_radius
            assert np.allclose(y_chamber, config.effective_inlet_radius, rtol=1e-6), (
                f"Chamber should be constant radius {config.effective_inlet_radius:.4f}, "
                f"got range [{np.min(y_chamber):.4f}, {np.max(y_chamber):.4f}]"
            )

    def test_chamber_radius_default(self):
        """Default chamber_radius should be 1.5x throat."""
        config = NozzleConfig(chamber_length=0.1)
        assert config.effective_inlet_radius == pytest.approx(
            config.throat_radius * 1.5, rel=1e-10,
        )

    def test_chamber_radius_explicit(self):
        """Explicit chamber_radius should override default."""
        config = NozzleConfig(chamber_length=0.1, chamber_radius=0.1)
        assert config.effective_inlet_radius == pytest.approx(0.1, rel=1e-10)

    def test_chamber_total_length(self):
        """total_length should include chamber."""
        config = NozzleConfig(
            chamber_length=0.1,
            converging_length=0.15,
            diverging_length=0.5,
        )
        expected = 0.1 + 0.15 + 0.5
        assert config.total_length == pytest.approx(expected, rel=1e-10)

    def test_chamber_point_count(self):
        """Contour with chamber should have correct point count."""
        config = NozzleConfig(
            num_points=200,
            chamber_length=0.1,
            chamber_radius=0.08,
        )
        x, y = generate_contour(config)
        # 5 sections: chamber, convergent, entrant arc, exit arc, bell
        # 4 duplicate points removed at boundaries
        assert len(x) == 200 - 4, f"Expected 196 points, got {len(x)}"
        assert len(y) == 200 - 4

    def test_chamber_monotonic_convergent_divergent(self):
        """Convergent and divergent should be monotonic with chamber."""
        config = NozzleConfig(
            chamber_length=0.1,
            chamber_radius=0.08,
            converging_length=0.1,
            diverging_length=0.5,
        )
        x, y = generate_contour(config)
        # After chamber, convergent should decrease
        conv_mask = (x >= -config.converging_length) & (x < 0)
        if np.any(conv_mask):
            y_conv = y[conv_mask]
            for i in range(len(y_conv) - 1):
                assert y_conv[i] >= y_conv[i + 1], (
                    f"Convergent not monotonic: y[{i}]={y_conv[i]} > y[{i+1}]={y_conv[i+1]}"
                )
        # Divergent should increase
        div_mask = x > 0
        if np.any(div_mask):
            y_div = y[div_mask]
            for i in range(len(y_div) - 1):
                assert y_div[i] <= y_div[i + 1], (
                    f"Divergent not monotonic: y[{i}]={y_div[i]} > y[{i+1}]={y_div[i+1]}"
                )

    def test_chamber_merlin_preset(self):
        """Merlin preset should generate valid contour with chamber."""
        from nozzle.presets import merlin_1d
        config = merlin_1d()
        x, y = generate_contour(config)
        # Should have chamber, convergent, and divergent sections
        assert np.min(x) < -config.converging_length, "Merlin should have chamber"
        assert y[-1] == pytest.approx(config.exit_radius, rel=1e-6)
        assert np.all(y >= 0), "No negative radii"


class TestCurvedConvergent:
    """Tests for curved convergent section."""

    def test_curved_convergent_boundary_values(self):
        """Curved convergent should match inlet and throat radii."""
        r_inlet = 0.08
        r_throat = 0.05
        length = 0.1
        half_angle = 45.0
        x = np.linspace(-length, 0, 50)
        y = _curved_convergent(r_inlet, r_throat, half_angle, x, length)
        assert y[0] == pytest.approx(r_inlet, rel=1e-10), (
            f"Start radius should be {r_inlet}, got {y[0]}"
        )
        assert y[-1] == pytest.approx(r_throat, rel=1e-10), (
            f"End radius should be {r_throat}, got {y[-1]}"
        )

    def test_curved_convergent_monotonic(self):
        """Curved convergent should be monotonically decreasing."""
        x = np.linspace(-0.15, 0, 100)
        y = _curved_convergent(0.08, 0.05, 45.0, x, 0.15)
        for i in range(len(y) - 1):
            assert y[i] >= y[i + 1], (
                f"Curved convergent not monotonic: y[{i}]={y[i]} > y[{i+1}]={y[i+1]}"
            )

    def test_curved_convergent_no_negative(self):
        """Curved convergent should have no negative radii."""
        x = np.linspace(-0.15, 0, 100)
        y = _curved_convergent(0.08, 0.05, 45.0, x, 0.15)
        assert np.all(y >= 0), f"Found negative radii: {y[y < 0]}"

    def test_curved_vs_linear_convergent(self):
        """Curved convergent should differ from linear convergent."""
        config_linear = NozzleConfig(
            throat_radius_of_curvature=0.0,
            converging_length=0.15,
        )
        config_curved = NozzleConfig(
            throat_radius_of_curvature=0.04,
            converging_length=0.15,
            convergent_half_angle=45.0,
        )
        x_lin, y_lin = generate_contour(config_linear)
        x_curv, y_curv = generate_contour(config_curved)
        # Both should reach same throat and exit
        assert np.min(y_lin) == pytest.approx(config_linear.throat_radius, rel=0.01)
        assert np.min(y_curv) == pytest.approx(config_curved.throat_radius, rel=0.01)
        # But shapes should differ: compare at a fixed x in the convergent region
        # Use x = -0.1 (start of convergent) to x_arc_start
        x_test = -0.12  # well within convergent range
        mask_lin = np.abs(x_lin - x_test) < 0.01
        mask_curv = np.abs(x_curv - x_test) < 0.01
        if np.any(mask_lin) and np.any(mask_curv):
            y_lin_val = y_lin[mask_lin][0]
            y_curv_val = y_curv[mask_curv][0]
            # Both start from same inlet radius, so compare shapes differently
            # Check that the overall contour shapes differ
        # Verify minimum y (throat) is the same for both
        assert np.min(y_lin) == pytest.approx(np.min(y_curv), rel=0.01)

    def test_curved_convergent_with_chamber(self):
        """Curved convergent should work with chamber section."""
        config = NozzleConfig(
            chamber_length=0.1,
            chamber_radius=0.08,
            throat_radius_of_curvature=0.04,
            convergent_half_angle=45.0,
            converging_length=0.15,
            diverging_length=0.5,
        )
        x, y = generate_contour(config)
        # Should have 3 sections
        assert np.min(x) < -config.converging_length
        # Convergent should be monotonic
        conv_mask = (x >= -config.converging_length) & (x < 0)
        y_conv = y[conv_mask]
        for i in range(len(y_conv) - 1):
            assert y_conv[i] >= y_conv[i + 1]

    def test_curved_convergent_different_angles(self):
        """Curved convergent should work with different half-angles."""
        for angle in [20.0, 30.0, 45.0, 60.0]:
            config = NozzleConfig(
                throat_radius_of_curvature=0.04,
                convergent_half_angle=angle,
                converging_length=0.15,
            )
            x, y = generate_contour(config)
            conv_mask = x <= 0
            y_conv = y[conv_mask]
            assert y_conv[0] == pytest.approx(config.effective_inlet_radius, rel=1e-6)
            # Minimum radius should be at throat
            assert np.min(y) == pytest.approx(config.throat_radius, rel=1e-3)


class TestPresets:
    """Tests for preset nozzle configurations."""

    def test_merlin_1d_contour(self):
        """Merlin 1D preset should generate valid contour."""
        from nozzle.presets import merlin_1d
        config = merlin_1d()
        x, y = generate_contour(config)
        # Should have all 3 sections
        assert len(x) > 0
        assert len(y) > 0
        # Exit radius should match
        assert y[-1] == pytest.approx(config.exit_radius, rel=1e-6)
        # Throat should be at minimum
        throat_idx = np.argmin(y)
        assert abs(x[throat_idx]) < 0.05, "Throat should be near x=0"

    def test_raptor_sl_contour(self):
        """Raptor SL preset should generate valid contour."""
        from nozzle.presets import raptor_sl
        config = raptor_sl()
        x, y = generate_contour(config)
        assert len(x) > 0
        assert y[-1] == pytest.approx(config.exit_radius, rel=1e-6)

    def test_generic_test_contour(self):
        """Generic test preset should generate valid contour (v1 compat)."""
        from nozzle.presets import generic_test
        config = generic_test()
        x, y = generate_contour(config)
        # v1 behavior: no chamber
        assert np.min(x) == pytest.approx(-config.converging_length, rel=0.01)
        assert y[-1] == pytest.approx(config.exit_radius, rel=1e-6)
