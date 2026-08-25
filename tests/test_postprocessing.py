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
    """Tests for compute_density_gradient."""

    def test_constant_density(self) -> None:
        """Constant density should give zero gradient."""
        data = VTUData(
            coordinates=np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]]),
            mach=None,
            pressure=None,
            temperature=None,
            density=np.array([1.0, 1.0, 1.0]),
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        grad = compute_density_gradient(data)
        assert np.allclose(grad, 0.0)

    def test_linear_density(self) -> None:
        """Linear density should give constant gradient at interior points."""
        data = VTUData(
            coordinates=np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]]),
            mach=None,
            pressure=None,
            temperature=None,
            density=np.array([1.0, 2.0, 3.0]),
            velocity_x=None,
            velocity_y=None,
            tke=None,
        )
        grad = compute_density_gradient(data)
        # Central finite difference: boundary points are 0, interior is 1.0
        assert np.allclose(grad, [0.0, 1.0, 0.0])

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
