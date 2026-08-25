"""Tests for nozzle contour generation."""
import math
import numpy as np
import pytest
from nozzle.config import NozzleConfig
from nozzle.geometry import generate_contour


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
        """Contour should have num_points - 1 points (duplicate throat removed)."""
        x, y = default_contour
        # generate_contour drops the duplicate throat point via x_diverge[1:]
        expected = default_config.num_points - 1
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
        # Duplicate throat point is dropped
        assert len(x) == 49
        assert len(y) == 49

    def test_throat_at_zero(self, default_contour):
        """Throat (minimum radius) should be at x=0."""
        x, y = default_contour
        # Find the point closest to x=0
        throat_idx = np.argmin(np.abs(x))
        assert abs(x[throat_idx]) < 0.01, (
            f"Throat should be at x~0, found x={x[throat_idx]}"
        )

    def test_exit_radius_from_conical_formula(self, default_config, default_contour):
        """Exit radius should match conical formula: R_throat + L_div * tan(half_angle)."""
        x, y = default_contour
        half_angle_rad = math.radians(default_config.half_angle)
        expected_exit_radius = (
            default_config.throat_radius
            + default_config.diverging_length * math.tan(half_angle_rad)
        )
        actual_exit_radius = y[-1]
        assert actual_exit_radius == pytest.approx(expected_exit_radius, rel=1e-6), (
            f"Exit radius should be {expected_exit_radius:.4f}m (from conical formula), "
            f"got {actual_exit_radius:.4f}m"
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
        """Diverging section should span correct length."""
        x, y = default_contour
        max_x = np.max(x)
        assert max_x == pytest.approx(default_config.diverging_length, rel=0.01), (
            f"Exit should be at x={default_config.diverging_length}m, "
            f"got x={max_x:.4f}m"
        )

    def test_negative_radii_absent(self, default_contour):
        """No negative radial coordinates."""
        _, y = default_contour
        assert np.all(y >= 0), f"Found negative radii: {y[y < 0]}"

    def test_conical_area_ratio(self):
        """Verify exit/throat area ratio matches the conical formula result."""
        config = NozzleConfig(
            throat_radius=0.05,
            half_angle=15.0,
            diverging_length=0.5,
        )
        _, y = generate_contour(config)
        half_angle_rad = math.radians(config.half_angle)
        expected_exit_r = config.throat_radius + config.diverging_length * math.tan(half_angle_rad)
        expected_area_ratio = (expected_exit_r / config.throat_radius) ** 2
        actual_area_ratio = (y[-1] / config.throat_radius) ** 2
        assert actual_area_ratio == pytest.approx(expected_area_ratio, rel=1e-6), (
            f"Area ratio should be {expected_area_ratio:.2f} (from conical formula), "
            f"got {actual_area_ratio:.2f}"
        )
