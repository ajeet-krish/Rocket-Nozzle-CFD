"""Tests for post-processing functions."""
import pytest
import numpy as np
from pathlib import Path

from cfd.vtu_parser import VTUData
from viz.postprocessing import (
    compute_density_gradient,
    extract_wall_pressure,
)


class TestVTUData:
    """Tests for VTUData dataclass."""

    def test_default_values(self) -> None:
        """VTUData should accept all fields."""
        data = VTUData(
            coordinates=np.array([[0, 0, 0], [1, 0, 0]]),
            mach=None,
            pressure=None,
            temperature=None,
            density=None,
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        assert data.coordinates.shape == (2, 3)
        assert data.mach is None
        assert data.pressure is None

    def test_with_arrays(self) -> None:
        """VTUData should hold numpy arrays."""
        coords = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        mach = np.array([0.0, 0.5, 1.0])
        data = VTUData(
            coordinates=coords,
            mach=mach,
            pressure=None,
            temperature=None,
            density=None,
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        assert data.mach is not None
        assert len(data.mach) == 3


class TestDensityGradient:
    """Tests for compute_density_gradient (cKDTree-based)."""

    def test_constant_density(self) -> None:
        """Constant density should give zero gradient everywhere."""
        coords = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.5, 1.0, 0.0],
        ])
        data = VTUData(
            coordinates=coords,
            mach=None,
            pressure=None,
            temperature=None,
            density=np.array([1.0, 1.0, 1.0, 1.0]),
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        grad = compute_density_gradient(data)
        assert np.allclose(grad, 0.0, atol=1e-10)

    def test_linear_density_2d(self) -> None:
        """Linear density field should give constant gradient magnitude."""
        # Create a regular grid with density = x
        x = np.linspace(0, 1, 5)
        y = np.linspace(0, 1, 5)
        xx, yy = np.meshgrid(x, y)
        coords = np.column_stack([xx.ravel(), yy.ravel(), np.zeros(25)])
        density = coords[:, 0].copy()  # density = x

        data = VTUData(
            coordinates=coords,
            mach=None,
            pressure=None,
            temperature=None,
            density=density,
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        grad = compute_density_gradient(data)

        # All interior points should have gradient magnitude ~1.0 (df/dx=1, df/dy=0)
        # Interior points have enough neighbors for accurate gradient
        interior_mask = (coords[:, 0] > 0.01) & (coords[:, 0] < 0.99)
        assert np.allclose(grad[interior_mask], 1.0, atol=0.15)

    def test_no_density(self) -> None:
        """Missing density should return zeros."""
        data = VTUData(
            coordinates=np.array([[0, 0, 0], [1, 0, 0]]),
            mach=None,
            pressure=None,
            temperature=None,
            density=None,
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        grad = compute_density_gradient(data)
        assert len(grad) == 2
        assert np.allclose(grad, 0.0)

    def test_gradient_magnitude_nonnegative(self) -> None:
        """Gradient magnitudes should be non-negative."""
        coords = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ])
        density = np.array([1.0, 2.0, 3.0, 1.5, 2.5])
        data = VTUData(
            coordinates=coords,
            mach=None,
            pressure=None,
            temperature=None,
            density=density,
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        grad = compute_density_gradient(data)
        assert np.all(grad >= 0.0)

    def test_smooth_gradient_not_noisy(self) -> None:
        """Gradient of smooth density field should be smooth, not noisy."""
        # Create dense 2D grid with smooth Gaussian density
        x = np.linspace(-1, 1, 20)
        y = np.linspace(-1, 1, 20)
        xx, yy = np.meshgrid(x, y)
        coords = np.column_stack([xx.ravel(), yy.ravel(), np.zeros(400)])
        # Gaussian: density = exp(-r^2)
        r2 = coords[:, 0] ** 2 + coords[:, 1] ** 2
        density = np.exp(-r2)

        data = VTUData(
            coordinates=coords,
            mach=None,
            pressure=None,
            temperature=None,
            density=density,
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        grad = compute_density_gradient(data)

        # Interior gradient should be smooth (low variance relative to mean)
        interior_mask = (
            (np.abs(coords[:, 0]) < 0.9)
            & (np.abs(coords[:, 1]) < 0.9)
        )
        grad_interior = grad[interior_mask]
        # Coefficient of variation should be bounded
        assert grad_interior.std() / (grad_interior.mean() + 1e-12) < 0.5


class TestExtractWallPressure:
    """Tests for extract_wall_pressure."""

    def test_centerline_extraction(self) -> None:
        """Should extract points near centerline (y ~ 0)."""
        coords = np.array([
            [0.0, 0.0, 0.0],
            [0.1, 0.01, 0.0],
            [0.2, 0.0, 0.0],
            [0.3, 0.05, 0.0],
        ])
        pressure = np.array([100.0, 90.0, 80.0, 70.0])
        data = VTUData(
            coordinates=coords,
            mach=None,
            pressure=pressure,
            temperature=None,
            density=None,
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        x, p = extract_wall_pressure(data, nozzle_exit_x=0.3)
        # Should get points where y < 0.001
        assert len(x) == 2
        assert np.allclose(x, [0.0, 0.2])
        assert np.allclose(p, [100.0, 80.0])

    def test_no_pressure(self) -> None:
        """Missing pressure should return zeros."""
        coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        data = VTUData(
            coordinates=coords,
            mach=None,
            pressure=None,
            temperature=None,
            density=None,
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        x, p = extract_wall_pressure(data, nozzle_exit_x=1.0)
        assert len(x) == 2
        assert np.allclose(p, 0.0)
