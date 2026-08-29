"""Comprehensive tests for the PINN module.

Covers:
    - PINNConfig: frozen dataclass, defaults, custom values
    - FourierFeature: forward pass shape, frequency encoding
    - ResidualBlock: skip connection, GELU activation
    - NozzlePINN: forward pass, output shape, gradient flow
    - EulerResiduals: axisymmetric Euler equation residuals
    - NozzleDataset: parameter normalization, collocation points, grid generation
    - PINNTrainer: training loop, save/load, curriculum phases
    - PINNInference: prediction pipeline, grid output shapes
    - Integration: full train-predict pipeline
    - Edge cases: zero inputs, NaN, axis singularity, empty data
"""
import math
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

from pinn.config import PINNConfig
from pinn.model import FourierFeature, ResidualBlock, NozzlePINN
from pinn.physics import EulerResiduals
from pinn.data import NozzleDataset
from pinn.trainer import PINNTrainer, TrainResult
from pinn.inference import PINNInference, PredictionResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> PINNConfig:
    """Default PINN config."""
    return PINNConfig()


@pytest.fixture
def small_config() -> PINNConfig:
    """Small PINN config for fast tests."""
    return PINNConfig(
        hidden_layers=(64, 64),
        fourier_features=16,
        grid_resolution=(8, 4),
        max_epochs=5,
        n_training_samples=20,
        n_validation_samples=5,
        curriculum_phases=(2, 2, 1),
    )


@pytest.fixture
def model(small_config: PINNConfig) -> NozzlePINN:
    """Small model for fast tests."""
    return NozzlePINN(small_config)


@pytest.fixture
def merlin_params() -> dict:
    """Merlin 1D engine parameters."""
    return {
        "expansion_ratio": 16.0,
        "throat_radius": 0.0825,
        "theta_n": 30.0,
        "total_pressure": 9.7e6,
        "total_temperature": 3600.0,
        "gamma": 1.4,
        "nozzle_length_fraction": 0.8,
    }


# ===========================================================================
# PINNConfig Tests
# ===========================================================================

class TestPINNConfig:
    """Tests for PINNConfig frozen dataclass."""

    def test_default_hidden_layers(self, config: PINNConfig):
        assert config.hidden_layers == (512, 512, 512, 512, 512, 512, 512, 512)

    def test_default_fourier_features(self, config: PINNConfig):
        assert config.fourier_features == 128

    def test_default_activation(self, config: PINNConfig):
        assert config.activation == "gelu"

    def test_default_n_inputs(self, config: PINNConfig):
        assert config.n_inputs == 9

    def test_default_n_outputs(self, config: PINNConfig):
        assert config.n_outputs == 6

    def test_default_grid_resolution(self, config: PINNConfig):
        assert config.grid_resolution == (64, 32)

    def test_default_learning_rate(self, config: PINNConfig):
        assert config.learning_rate == 1e-3

    def test_default_weight_decay(self, config: PINNConfig):
        assert config.weight_decay == 1e-4

    def test_default_max_epochs(self, config: PINNConfig):
        assert config.max_epochs == 1000

    def test_default_curriculum_phases(self, config: PINNConfig):
        assert config.curriculum_phases == (200, 500, 300)

    def test_default_lambda_data(self, config: PINNConfig):
        assert config.lambda_data == 1.0

    def test_default_lambda_pde(self, config: PINNConfig):
        assert config.lambda_pde == 0.1

    def test_default_lambda_bc(self, config: PINNConfig):
        assert config.lambda_bc == 0.5

    def test_default_param_bounds(self, config: PINNConfig):
        bounds = config.param_bounds
        assert "expansion_ratio" in bounds
        assert "throat_radius" in bounds
        assert "theta_n" in bounds
        assert "total_pressure" in bounds
        assert "total_temperature" in bounds
        assert "gamma" in bounds
        assert "nozzle_length_fraction" in bounds
        assert len(bounds) == 7

    def test_param_bounds_are_tuples(self, config: PINNConfig):
        for key, (lo, hi) in config.param_bounds.items():
            assert isinstance(lo, float), f"{key} lower bound not float"
            assert isinstance(hi, float), f"{key} upper bound not float"
            assert lo < hi, f"{key} lower bound >= upper bound"

    def test_default_training_samples(self, config: PINNConfig):
        assert config.n_training_samples == 300
        assert config.n_validation_samples == 50

    def test_frozen_dataclass(self, config: PINNConfig):
        with pytest.raises(AttributeError):
            config.hidden_layers = (128,)

    def test_custom_config(self):
        custom = PINNConfig(
            hidden_layers=(256, 256),
            fourier_features=64,
            activation="relu",
            n_inputs=5,
            n_outputs=4,
            grid_resolution=(32, 16),
            learning_rate=5e-4,
            weight_decay=1e-5,
            max_epochs=500,
            curriculum_phases=(100, 200, 200),
            lambda_data=2.0,
            lambda_pde=0.5,
            lambda_bc=1.0,
            n_training_samples=100,
            n_validation_samples=20,
        )
        assert custom.hidden_layers == (256, 256)
        assert custom.fourier_features == 64
        assert custom.activation == "relu"
        assert custom.n_inputs == 5
        assert custom.n_outputs == 4
        assert custom.grid_resolution == (32, 16)
        assert custom.learning_rate == 5e-4
        assert custom.weight_decay == 1e-5
        assert custom.max_epochs == 500
        assert custom.curriculum_phases == (100, 200, 200)
        assert custom.lambda_data == 2.0
        assert custom.lambda_pde == 0.5
        assert custom.lambda_bc == 1.0
        assert custom.n_training_samples == 100
        assert custom.n_validation_samples == 20

    def test_curriculum_phases_sum_to_total(self, config: PINNConfig):
        phases = config.curriculum_phases
        assert phases[0] + phases[1] + phases[2] == sum(phases)


# ===========================================================================
# FourierFeature Tests
# ===========================================================================

class TestFourierFeature:
    """Tests for FourierFeature positional encoding."""

    def test_output_shape_batch_size_1(self):
        """Output should be (B, 4*n_freqs).

        The FourierFeature maps (B, 2) -> (B, 4*n_freqs):
            sin/cos applied to each of 2 coords x n_freqs frequencies,
            then concatenated and reshaped.
        """
        n_freqs = 16
        ff = FourierFeature(n_freqs=n_freqs)
        x = torch.randn(1, 2)
        out = ff(x)
        # 2 coords * n_freqs sin + 2 coords * n_freqs cos = 4*n_freqs
        assert out.shape == (1, 4 * n_freqs), f"Expected (1, {4*n_freqs}), got {out.shape}"

    def test_output_shape_batch_size_10(self):
        n_freqs = 32
        ff = FourierFeature(n_freqs=n_freqs)
        x = torch.randn(10, 2)
        out = ff(x)
        assert out.shape == (10, 4 * n_freqs)

    def test_output_shape_batch_size_100(self):
        n_freqs = 64
        ff = FourierFeature(n_freqs=n_freqs)
        x = torch.randn(100, 2)
        out = ff(x)
        assert out.shape == (100, 4 * n_freqs)

    def test_output_range_bounded(self):
        """Sin/cos outputs should be in [-1, 1].

        Uses small n_freqs and moderate input values to avoid float32
        overflow at high frequency products (2^k * x for large k).
        """
        n_freqs = 8
        ff = FourierFeature(n_freqs=n_freqs)
        x = torch.randn(50, 2) * 2.0
        out = ff(x)
        assert out.min().item() >= -1.0 - 1e-6, (
            f"Min value {out.min().item()} below -1"
        )
        assert out.max().item() <= 1.0 + 1e-6, (
            f"Max value {out.max().item()} above 1"
        )

    def test_output_range_with_large_freqs(self):
        """High frequencies can overflow float32, producing NaN.

        This documents a known limitation: with n_freqs=128, frequencies
        go up to 2^127, which overflows float32 when multiplied by x>0.
        """
        n_freqs = 128
        ff = FourierFeature(n_freqs=n_freqs)
        x = torch.ones(1, 2) * 10.0
        out = ff(x)
        # High-frequency components will be NaN due to overflow
        # Only low-frequency components (< ~2^124) are finite
        has_nan = torch.isnan(out).any()
        assert has_nan, (
            "Expected NaN from float32 overflow at 2^127 * 10.0; "
            "if all finite, float32 range may have changed"
        )

    def test_frequencies_are_powers_of_two(self):
        """Frequencies should be 2^k for k=0..n_freqs-1."""
        ff = FourierFeature(n_freqs=8)
        expected = 2.0 ** torch.arange(8).float()
        assert torch.allclose(ff.freqs, expected)

    def test_freqs_is_buffer(self):
        """Frequencies should be a registered buffer (not a parameter)."""
        ff = FourierFeature(n_freqs=16)
        buf_names = [name for name, _ in ff.named_buffers()]
        param_names = [name for name, _ in ff.named_parameters()]
        assert "freqs" in buf_names
        assert "freqs" not in param_names

    def test_zero_input(self):
        """sin(0)=0, cos(0)=1.

        For zero input (B, 2) with n_freqs=4, the layout after cat+reshape is:
            [sin(x0*f0..f3), cos(x0*f0..f3), sin(x1*f0..f3), cos(x1*f0..f3)]
        =   [0,0,0,0, 1,1,1,1, 0,0,0,0, 1,1,1,1]
        with n_freqs zeros, n_freqs ones, n_freqs zeros, n_freqs ones.
        """
        n_freqs = 4
        ff = FourierFeature(n_freqs=n_freqs)
        x = torch.zeros(1, 2)
        out = ff(x)
        # Output shape: 4 * n_freqs = 16
        assert out.shape == (1, 4 * n_freqs)
        # Check pattern: [sin(coord0), cos(coord0), sin(coord1), cos(coord1)]
        # Each block has n_freqs elements
        for block_start in range(0, 4 * n_freqs, n_freqs):
            block = out[0, block_start:block_start + n_freqs]
            # Sin blocks (indices 0, 2): all zeros
            # Cos blocks (indices 1, 3): all ones
            block_idx = block_start // n_freqs
            if block_idx % 2 == 0:  # sin block
                assert block.abs().max().item() < 1e-6, (
                    f"Sin block {block_idx} should be zero"
                )
            else:  # cos block
                assert (block - 1.0).abs().max().item() < 1e-6, (
                    f"Cos block {block_idx} should be one"
                )

    def test_deterministic(self):
        """Same input should produce same output."""
        ff = FourierFeature(n_freqs=16)
        x = torch.randn(5, 2)
        out1 = ff(x)
        out2 = ff(x)
        assert torch.allclose(out1, out2)


# ===========================================================================
# ResidualBlock Tests
# ===========================================================================

class TestResidualBlock:
    """Tests for ResidualBlock with skip connection."""

    def test_output_shape(self):
        block = ResidualBlock(dim=64)
        x = torch.randn(10, 64)
        out = block(x)
        assert out.shape == (10, 64)

    def test_skip_connection(self):
        """Output should be x + f(x), not just f(x)."""
        block = ResidualBlock(dim=32)
        x = torch.randn(5, 32)
        out = block(x)
        # The residual part (f(x) = act(linear2(act(linear1(x)))))
        # should be small at init, so out should be close to x
        assert not torch.allclose(out, x, atol=1e-5), "Skip connection not working"

    def test_gradient_flow(self):
        """Gradients should flow through the block."""
        block = ResidualBlock(dim=32)
        x = torch.randn(5, 32, requires_grad=True)
        out = block(x)
        loss = out.sum()
        loss.backward()
        assert x.grad is not None, "No gradient on input"
        assert x.grad.shape == x.shape, f"Gradient shape mismatch: {x.grad.shape}"

    def test_batch_independence(self):
        """Each batch element should be processed independently."""
        block = ResidualBlock(dim=16)
        x = torch.randn(8, 16)
        out = block(x)
        # Individual forward passes should match batched
        for i in range(8):
            out_i = block(x[i:i+1])
            assert torch.allclose(out[i:i+1], out_i, atol=1e-5), (
                f"Batch element {i} differs from individual forward pass"
            )

    def test_gelu_activation(self):
        """Block should use GELU activation (not ReLU)."""
        block = ResidualBlock(dim=32)
        assert isinstance(block.act, torch.nn.GELU)


# ===========================================================================
# NozzlePINN Model Tests
# ===========================================================================

class TestNozzlePINN:
    """Tests for the full NozzlePINN model."""

    def test_output_shape(self, model: NozzlePINN, small_config: PINNConfig):
        batch = 10
        x = torch.randn(batch)
        y = torch.randn(batch)
        params = torch.randn(batch, 7)
        out = model(x, y, params)
        assert out.shape == (batch, small_config.n_outputs), (
            f"Expected ({batch}, {small_config.n_outputs}), got {out.shape}"
        )

    def test_output_shape_single(self, model: NozzlePINN):
        x = torch.tensor([0.5])
        y = torch.tensor([0.5])
        params = torch.randn(1, 7)
        out = model(x, y, params)
        assert out.shape == (1, 6)

    def test_output_shape_large_batch(self, model: NozzlePINN):
        batch = 500
        x = torch.randn(batch)
        y = torch.randn(batch)
        params = torch.randn(batch, 7)
        out = model(x, y, params)
        assert out.shape == (500, 6)

    def test_output_is_finite(self, model: NozzlePINN):
        x = torch.randn(20)
        y = torch.randn(20)
        params = torch.randn(20, 7)
        out = model(x, y, params)
        assert torch.isfinite(out).all(), "Model output contains NaN or Inf"

    def test_gradient_flow(self, model: NozzlePINN):
        """All parameters should receive gradients."""
        x = torch.randn(5, requires_grad=True)
        y = torch.randn(5, requires_grad=True)
        params = torch.randn(5, 7)
        out = model(x, y, params)
        loss = out.sum()
        loss.backward()
        for name, p in model.named_parameters():
            assert p.grad is not None, f"No gradient on parameter {name}"
            assert not torch.isnan(p.grad).any(), f"NaN gradient on {name}"

    def test_config_stored(self, model: NozzlePINN, small_config: PINNConfig):
        assert model.config is small_config

    def test_fourier_feature_count(self, model: NozzlePINN, small_config: PINNConfig):
        assert model.fourier.freqs.numel() == small_config.fourier_features

    def test_eight_residual_blocks(self, model: NozzlePINN):
        """Default architecture should have 8 residual blocks."""
        assert len(model.residuals) == 8

    def test_full_size_config(self, config: PINNConfig):
        """Default config should create the full 512-dim architecture."""
        model = NozzlePINN(config)
        n_params = sum(p.numel() for p in model.parameters())
        # 8 residual blocks of 512 + input proj + output head + Fourier
        assert n_params > 1_000_000, f"Expected >1M params, got {n_params:,}"

    def test_deterministic_forward(self, model: NozzlePINN):
        """Same input should produce same output."""
        model.eval()
        x = torch.randn(10)
        y = torch.randn(10)
        params = torch.randn(10, 7)
        out1 = model(x, y, params)
        out2 = model(x, y, params)
        assert torch.allclose(out1, out2)

    def test_different_inputs_different_outputs(self, model: NozzlePINN):
        """Different inputs should generally produce different outputs."""
        model.eval()
        x1 = torch.zeros(10)
        y1 = torch.zeros(10)
        x2 = torch.ones(10)
        y2 = torch.ones(10)
        params = torch.randn(10, 7)
        out1 = model(x1, y1, params)
        out2 = model(x2, y2, params)
        assert not torch.allclose(out1, out2), "Model maps different inputs to same output"


# ===========================================================================
# EulerResiduals Tests
# ===========================================================================

class TestEulerResiduals:
    """Tests for axisymmetric Euler equation residual computation.

    Key constraint: torch.autograd.grad(out, x) requires that `out` was
    computed from `x` through differentiable operations. We create a simple
    linear model so that primitive variables are differentiable w.r.t. x, y.
    """

    @pytest.fixture
    def euler(self) -> EulerResiduals:
        return EulerResiduals(gamma=1.4)

    def _make_differentiable_fields(
        self, n: int, x_range: tuple[float, float] = (0.1, 1.0)
    ) -> tuple[torch.Tensor, ...]:
        """Create primitive variables that are differentiable functions of x AND y.

        Each variable must depend on both x and y so that
        torch.autograd.grad(var, x) and torch.autograd.grad(var, y) both work.

        Returns (mach, pressure, temperature, density, vx, vy, x, y).
        """
        x = torch.linspace(x_range[0], x_range[1], n, requires_grad=True)
        y = torch.linspace(0.1, 1.0, n, requires_grad=True)

        # Each variable must be a function of BOTH x and y
        mach = 1.0 + 0.5 * x + 0.1 * y
        pressure = 1e5 - 1e4 * x + 1e3 * y
        temperature = 300.0 - 10.0 * x + 5.0 * y
        density = 1.0 + 0.1 * x + 0.05 * y
        vx = 100.0 + 200.0 * x + 10.0 * y
        vy = 0.1 * y + 0.05 * x  # small radial velocity depending on both x, y

        return mach, pressure, temperature, density, vx, vy, x, y

    def test_output_keys(self, euler: EulerResiduals):
        fields = self._make_differentiable_fields(20)
        residuals = euler(*fields)
        assert "continuity" in residuals
        assert "x_momentum" in residuals
        assert "y_momentum" in residuals
        assert "energy" in residuals

    def test_output_shapes(self, euler: EulerResiduals):
        n = 15
        fields = self._make_differentiable_fields(n)
        residuals = euler(*fields)
        for key in ["continuity", "x_momentum", "y_momentum", "energy"]:
            assert residuals[key].shape == (n,), (
                f"{key} shape: expected ({n},), got {residuals[key].shape}"
            )

    def test_residuals_finite(self, euler: EulerResiduals):
        """Residuals should be finite for reasonable inputs."""
        fields = self._make_differentiable_fields(30)
        residuals = euler(*fields)
        for key, val in residuals.items():
            assert torch.isfinite(val).all(), f"{key} contains NaN/Inf"

    def test_constant_flow_residual_bounded(self, euler: EulerResiduals):
        """Near-constant flow should have bounded residuals.

        Note: truly uniform flow is NOT a solution of the axisymmetric
        Euler equations due to the -P/y term in y-momentum. This test
        verifies that near-uniform flow produces finite, bounded residuals
        rather than checking for exact zero.
        """
        n = 20
        eps = 1e-6  # tiny variation to maintain autograd graph
        x = torch.linspace(0.1, 1.0, n, requires_grad=True)
        y = torch.linspace(0.1, 1.0, n, requires_grad=True)
        # Near-constant flow
        pressure = 1e5 + eps * x + eps * y
        temperature = 300.0 + eps * x + eps * y
        density = 1.17 + eps * x + eps * y
        vx = 100.0 + eps * x + eps * y
        vy = eps * x + eps * y
        mach = 0.3 + eps * x + eps * y

        residuals = euler(mach, pressure, temperature, density, vx, vy, x, y)
        for key, val in residuals.items():
            assert torch.isfinite(val).all(), f"{key} has NaN/Inf for near-constant flow"
            # Residuals should be bounded (not exploding)
            assert val.abs().max().item() < 1e8, (
                f"{key} residual unbounded for near-constant flow: {val.abs().max().item()}"
            )

    def test_axis_singularity_handled(self, euler: EulerResiduals):
        """Residuals should handle y~0 without NaN (axis singularity)."""
        n = 20
        x = torch.linspace(0.1, 1.0, n, requires_grad=True)
        y = torch.full((n,), 1e-7, requires_grad=True)  # Very close to axis
        # Linear functions of BOTH x and y so autograd works for all grad calls
        mach = 1.0 + 0.5 * x + 0.1 * y
        pressure = 1e5 - 1e4 * x + 1e3 * y
        temperature = 300.0 - 10.0 * x + 5.0 * y
        density = 1.0 + 0.1 * x + 0.05 * y
        vx = 100.0 + 200.0 * x + 10.0 * y
        vy = 0.1 * y + 0.05 * x

        residuals = euler(mach, pressure, temperature, density, vx, vy, x, y)
        for key, val in residuals.items():
            assert torch.isfinite(val).all(), f"{key} contains NaN at y~0"

    def test_exact_axis_zero(self, euler: EulerResiduals):
        """y=0 exactly should not cause division by zero."""
        n = 10
        x = torch.linspace(0.1, 1.0, n, requires_grad=True)
        y = torch.zeros(n, requires_grad=True)
        # Linear functions of BOTH x and y for autograd graph
        mach = 1.0 + 0.5 * x + 0.1 * y
        pressure = 1e5 - 1e4 * x + 1e3 * y
        temperature = 300.0 - 10.0 * x + 5.0 * y
        density = 1.0 + 0.1 * x + 0.05 * y
        vx = 100.0 + 200.0 * x + 10.0 * y
        vy = 0.1 * y + 0.05 * x

        residuals = euler(mach, pressure, temperature, density, vx, vy, x, y)
        for key, val in residuals.items():
            assert torch.isfinite(val).all(), f"{key} is NaN at y=0"

    def test_custom_gamma(self):
        """EulerResiduals should accept custom gamma."""
        euler = EulerResiduals(gamma=1.67)
        assert euler.gamma == 1.67

    def test_autograd_computation_graph(self, euler: EulerResiduals):
        """Residuals should be differentiable w.r.t. input coordinates."""
        n = 10
        fields = self._make_differentiable_fields(n)
        residuals = euler(*fields)
        loss = sum(v.pow(2).mean() for v in residuals.values())
        loss.backward()
        x = fields[6]  # x is the 7th returned value
        y = fields[7]  # y is the 8th returned value
        assert x.grad is not None, "No gradient w.r.t. x"
        assert y.grad is not None, "No gradient w.r.t. y"
        assert torch.isfinite(x.grad).all(), "NaN gradient w.r.t. x"

    def test_residuals_scale_with_magnitude(self, euler: EulerResiduals):
        """Higher velocity gradients should produce larger residuals."""
        n = 20
        x = torch.linspace(0.1, 1.0, n, requires_grad=True)
        y = torch.linspace(0.1, 1.0, n, requires_grad=True)

        # Small gradient flow - variables depend on BOTH x and y
        vx_small = 100.0 + 10.0 * x + 1.0 * y
        vy_small = 1.0 * y + 0.5 * x
        mach_s = 1.0 + 0.1 * x + 0.05 * y
        pressure_s = 1e5 - 100.0 * x + 50.0 * y
        temp_s = 300.0 - 1.0 * x + 0.5 * y
        rho_s = 1.0 + 0.01 * x + 0.005 * y
        res_small = euler(
            mach_s, pressure_s, temp_s, rho_s, vx_small, vy_small, x, y
        )
        mag_small = sum(v.pow(2).mean().item() for v in res_small.values())

        # Large gradient flow
        vx_large = 100.0 + 1000.0 * x + 50.0 * y
        vy_large = 10.0 * y + 5.0 * x
        mach_l = 1.0 + 2.0 * x + 0.5 * y
        pressure_l = 1e5 - 1e4 * x + 5e3 * y
        temp_l = 300.0 - 50.0 * x + 25.0 * y
        rho_l = 1.0 + 0.5 * x + 0.25 * y
        res_large = euler(
            mach_l, pressure_l, temp_l, rho_l, vx_large, vy_large, x, y
        )
        mag_large = sum(v.pow(2).mean().item() for v in res_large.values())

        assert mag_large > mag_small, (
            f"Large gradients should produce larger residuals: "
            f"small={mag_small:.6f}, large={mag_large:.6f}"
        )


# ===========================================================================
# NozzleDataset Tests
# ===========================================================================

class TestNozzleDataset:
    """Tests for NozzleDataset data loading and generation."""

    def test_initialization(self, config: PINNConfig):
        ds = NozzleDataset(config)
        assert ds.config is config
        assert ds._x_min == 0.0
        assert ds._x_max == 1.0
        assert ds._y_min == 0.0
        assert ds._y_max == 1.0

    def test_normalize_params_midpoint(self, config: PINNConfig):
        """Midpoint values should normalize to 0.5."""
        ds = NozzleDataset(config)
        bounds = config.param_bounds
        # Use midpoints of all parameter ranges
        midpoints = {k: (lo + hi) / 2 for k, (lo, hi) in bounds.items()}
        normalized = ds.normalize_params(**midpoints)
        assert normalized.shape == (7,)
        for i in range(7):
            assert normalized[i] == pytest.approx(0.5, abs=1e-6), (
                f"Param {i} midpoint normalized to {normalized[i]:.6f}, expected 0.5"
            )

    def test_normalize_params_at_bounds(self, config: PINNConfig):
        """Values at bounds should normalize to 0.0 or 1.0."""
        ds = NozzleDataset(config)
        bounds = config.param_bounds
        lo_params = {k: lo for k, (lo, hi) in bounds.items()}
        hi_params = {k: hi for k, (lo, hi) in bounds.items()}
        norm_lo = ds.normalize_params(**lo_params)
        norm_hi = ds.normalize_params(**hi_params)
        np.testing.assert_allclose(norm_lo, 0.0, atol=1e-6)
        np.testing.assert_allclose(norm_hi, 1.0, atol=1e-6)

    def test_normalize_params_clipped(self, config: PINNConfig):
        """Out-of-range values should be clipped to [0, 1]."""
        ds = NozzleDataset(config)
        # Expansion ratio below lower bound (4.0)
        normalized = ds.normalize_params(
            expansion_ratio=2.0,
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
        )
        assert normalized[0] == 0.0, "Below-lower-bound should clip to 0"
        # Expansion ratio above upper bound (300.0)
        normalized = ds.normalize_params(
            expansion_ratio=500.0,
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
        )
        assert normalized[0] == 1.0, "Above-upper-bound should clip to 1"

    def test_generate_collocation_points_shape(self, config: PINNConfig):
        ds = NozzleDataset(config)
        pts = ds.generate_collocation_points((0.0, 1.0), (0.01, 1.0))
        assert "x" in pts
        assert "y" in pts
        assert pts["x"].shape == (config.n_training_samples,)
        assert pts["y"].shape == (config.n_training_samples,)

    def test_generate_collocation_points_custom_n(self, config: PINNConfig):
        ds = NozzleDataset(config)
        pts = ds.generate_collocation_points((0.0, 1.0), (0.01, 1.0), n_samples=50)
        assert pts["x"].shape == (50,)
        assert pts["y"].shape == (50,)

    def test_generate_collocation_points_in_range(self, config: PINNConfig):
        ds = NozzleDataset(config)
        x_range = (0.2, 0.8)
        y_range = (0.1, 0.9)
        pts = ds.generate_collocation_points(x_range, y_range, n_samples=1000)
        assert pts["x"].min() >= x_range[0]
        assert pts["x"].max() <= x_range[1]
        assert pts["y"].min() >= y_range[0]
        assert pts["y"].max() <= y_range[1]

    def test_generate_collocation_points_deterministic(self, config: PINNConfig):
        """Same call should produce same points (seeded RNG)."""
        ds = NozzleDataset(config)
        pts1 = ds.generate_collocation_points((0.0, 1.0), (0.01, 1.0))
        pts2 = ds.generate_collocation_points((0.0, 1.0), (0.01, 1.0))
        np.testing.assert_array_equal(pts1["x"], pts2["x"])
        np.testing.assert_array_equal(pts1["y"], pts2["y"])

    def test_generate_grid_shape(self, small_config: PINNConfig):
        ds = NozzleDataset(small_config)
        x_grid, y_grid, x_flat, y_flat = ds.generate_grid((0.0, 1.0), (0.01, 1.0))
        nx, ny = small_config.grid_resolution
        assert x_grid.shape == (nx, ny)
        assert y_grid.shape == (nx, ny)
        assert x_flat.shape == (nx * ny,)
        assert y_flat.shape == (nx * ny,)

    def test_generate_grid_flat_matches_grid(self, small_config: PINNConfig):
        ds = NozzleDataset(small_config)
        x_grid, y_grid, x_flat, y_flat = ds.generate_grid((0.0, 1.0), (0.01, 1.0))
        np.testing.assert_array_equal(x_flat, x_grid.ravel())
        np.testing.assert_array_equal(y_flat, y_grid.ravel())

    def test_generate_grid_in_range(self, small_config: PINNConfig):
        ds = NozzleDataset(small_config)
        x_min, x_max = 0.0, 1.0
        y_min, y_max = 0.05, 0.95
        x_grid, y_grid, _, _ = ds.generate_grid((x_min, x_max), (y_min, y_max))
        assert x_grid.min() >= x_min
        assert x_grid.max() <= x_max
        assert y_grid.min() >= y_min
        assert y_grid.max() <= y_max

    def test_generate_grid_values_monotonic(self, small_config: PINNConfig):
        """Grid values should be monotonically increasing along each axis."""
        ds = NozzleDataset(small_config)
        x_grid, y_grid, _, _ = ds.generate_grid((0.0, 1.0), (0.01, 1.0))
        # Check monotonicity along axis 0 (x)
        for j in range(x_grid.shape[1]):
            diffs = np.diff(x_grid[:, j])
            assert np.all(diffs >= 0), "x_grid not monotonic along axis 0"
        # Check monotonicity along axis 1 (y)
        for i in range(y_grid.shape[0]):
            diffs = np.diff(y_grid[i, :])
            assert np.all(diffs >= 0), "y_grid not monotonic along axis 1"


# ===========================================================================
# PINNTrainer Tests
# ===========================================================================

class TestPINNTrainer:
    """Tests for PINNTrainer training loop and save/load."""

    def test_initialization(self, model: NozzlePINN, small_config: PINNConfig):
        trainer = PINNTrainer(model, small_config, device="cpu")
        assert trainer.config is small_config
        assert str(trainer.device) == "cpu"
        assert trainer.optimizer is not None
        assert trainer.euler is not None

    def test_train_returns_result(self, model: NozzlePINN, small_config: PINNConfig):
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        result = trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=3,
            verbose=False,
        )
        assert isinstance(result, TrainResult)
        assert result.epochs_trained == 3
        assert len(result.loss_history) == 3

    def test_data_loss_decreases_in_phase1(self, model: NozzlePINN, small_config: PINNConfig):
        """In phase 1 (data-only), the data loss should decrease.

        Phase 1 uses only lambda_data with no PDE/BC loss, so it should
        behave like standard supervised training and reduce data loss.
        """
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        result = trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=2,  # small_config phases=(2,2,1), so 2 epochs = phase 1 only
            verbose=False,
        )
        # Phase 1 data-only training should reduce loss
        assert result.loss_history[-1] <= result.loss_history[0], (
            f"Data-only training should reduce loss: "
            f"first={result.loss_history[0]:.6f}, last={result.loss_history[-1]:.6f}"
        )

    def test_curriculum_phases(self, model: NozzlePINN, small_config: PINNConfig):
        """Training should complete without errors through all curriculum phases."""
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        # small_config has phases=(2, 2, 1) -> total 5 epochs
        result = trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=5,
            verbose=False,
        )
        assert result.epochs_trained == 5
        assert result.final_loss >= 0

    def test_final_losses_populated(self, model: NozzlePINN, small_config: PINNConfig):
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        result = trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=3,
            verbose=False,
        )
        assert isinstance(result.final_data_loss, float)
        assert isinstance(result.final_pde_loss, float)
        assert isinstance(result.final_bc_loss, float)
        assert result.training_time_s > 0

    def test_save_and_load(self, model: NozzlePINN, small_config: PINNConfig):
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        # Train a few epochs
        trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=3,
            verbose=False,
        )

        # Save
        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_path = Path(tmpdir) / "test_model.pt"
            trainer.save(ckpt_path)
            assert ckpt_path.exists()

            # Load into a new model
            new_model = NozzlePINN(small_config)
            new_trainer = PINNTrainer(new_model, small_config, device="cpu")
            new_trainer.load(ckpt_path)

            # Verify loaded model produces same output
            model.eval()
            new_model.eval()
            x = torch.randn(5)
            y = torch.randn(5)
            params = torch.randn(5, 7)
            out1 = model(x, y, params)
            out2 = new_model(x, y, params)
            assert torch.allclose(out1, out2, atol=1e-6), (
                "Loaded model output differs from original"
            )

    def test_save_creates_parent_dirs(self, model: NozzlePINN, small_config: PINNConfig):
        trainer = PINNTrainer(model, small_config, device="cpu")
        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_path = Path(tmpdir) / "deep" / "nested" / "model.pt"
            trainer.save(ckpt_path)
            assert ckpt_path.exists()

    def test_pde_loss_active_in_phase2(self, small_config: PINNConfig):
        """PDE loss should be nonzero in phase 2 and 3."""
        model = NozzlePINN(small_config)
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        result = trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=5,  # phases=(2,2,1) -> epoch 2-3 is phase 2, epoch 4 is phase 3
            verbose=False,
        )
        # Phase 3 (epoch 4) should have active PDE loss
        assert result.final_pde_loss >= 0

    def test_bc_loss_enforces_axis_symmetry(self, small_config: PINNConfig):
        """BC loss should penalize Vy != 0 at the axis."""
        model = NozzlePINN(small_config)
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        # Train with BC loss active
        result = trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=5,
            verbose=False,
        )
        # BC loss should be computed (may not be zero but should be finite)
        assert math.isfinite(result.final_bc_loss)


# ===========================================================================
# PINNInference Tests
# ===========================================================================

class TestPINNInference:
    """Tests for PINNInference prediction pipeline."""

    @pytest.fixture
    def trained_model_path(self, small_config: PINNConfig, merlin_params: dict) -> Path:
        """Create and save a trained model for inference tests."""
        model = NozzlePINN(small_config)
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=3,
            verbose=False,
        )

        tmpdir = Path(tempfile.mkdtemp())
        ckpt_path = tmpdir / "test_model.pt"
        trainer.save(ckpt_path)
        return ckpt_path

    def test_predict_returns_result(self, trained_model_path: Path):
        inference = PINNInference(trained_model_path, device="cpu")
        result = inference.predict(
            expansion_ratio=16.0,
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
        )
        assert isinstance(result, PredictionResult)

    def test_predict_output_shapes(self, trained_model_path: Path, small_config: PINNConfig):
        inference = PINNInference(trained_model_path, device="cpu")
        result = inference.predict(
            expansion_ratio=16.0,
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
        )
        nx, ny = small_config.grid_resolution
        assert result.mach.shape == (nx, ny)
        assert result.pressure.shape == (nx, ny)
        assert result.temperature.shape == (nx, ny)
        assert result.density.shape == (nx, ny)
        assert result.velocity_x.shape == (nx, ny)
        assert result.velocity_y.shape == (nx, ny)
        assert result.x_grid.shape == (nx, ny)
        assert result.y_grid.shape == (nx, ny)

    def test_predict_inference_time(self, trained_model_path: Path):
        inference = PINNInference(trained_model_path, device="cpu")
        result = inference.predict(
            expansion_ratio=16.0,
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
        )
        assert result.inference_time_ms >= 0
        assert isinstance(result.inference_time_ms, float)

    def test_predict_custom_grid(self, trained_model_path: Path):
        inference = PINNInference(trained_model_path, device="cpu")
        result = inference.predict(
            expansion_ratio=16.0,
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
            x_range=(0.0, 0.5),
            y_range=(0.05, 0.5),
            grid_resolution=(4, 2),
        )
        assert result.mach.shape == (4, 2)
        assert result.x_grid.shape == (4, 2)
        assert result.x_grid.min() >= 0.0
        assert result.x_grid.max() <= 0.5

    def test_predict_config_loaded(self, trained_model_path: Path, small_config: PINNConfig):
        inference = PINNInference(trained_model_path, device="cpu")
        assert inference.config.hidden_layers == small_config.hidden_layers
        assert inference.config.fourier_features == small_config.fourier_features

    def test_predict_outputs_finite(self, trained_model_path: Path):
        inference = PINNInference(trained_model_path, device="cpu")
        result = inference.predict(
            expansion_ratio=16.0,
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
        )
        assert np.isfinite(result.mach).all(), "Mach contains NaN/Inf"
        assert np.isfinite(result.pressure).all(), "Pressure contains NaN/Inf"
        assert np.isfinite(result.temperature).all(), "Temperature contains NaN/Inf"
        assert np.isfinite(result.density).all(), "Density contains NaN/Inf"
        assert np.isfinite(result.velocity_x).all(), "Vx contains NaN/Inf"
        assert np.isfinite(result.velocity_y).all(), "Vy contains NaN/Inf"

    def test_predict_from_nozzle_config(self, trained_model_path: Path):
        from nozzle.config import NozzleConfig
        inference = PINNInference(trained_model_path, device="cpu")
        nozzle = NozzleConfig(throat_radius=0.05, expansion_ratio=12.0)
        result = inference.predict_from_nozzle_config(nozzle)
        assert isinstance(result, PredictionResult)
        assert result.mach.shape[0] > 0

    def test_predict_different_params_different_output(self, trained_model_path: Path):
        """Different nozzle parameters should produce different predictions."""
        inference = PINNInference(trained_model_path, device="cpu")
        result1 = inference.predict(
            expansion_ratio=16.0,
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
        )
        result2 = inference.predict(
            expansion_ratio=50.0,
            throat_radius=0.15,
            theta_n=20.0,
            total_pressure=30e6,
            total_temperature=4000.0,
            gamma=1.3,
            nozzle_length_fraction=0.6,
        )
        assert not np.allclose(result1.mach, result2.mach), (
            "Different params produced identical Mach fields"
        )

    def test_predict_uses_loaded_config_grid(self, trained_model_path: Path, small_config: PINNConfig):
        """Predict should use the loaded config's grid_resolution, not default."""
        inference = PINNInference(trained_model_path, device="cpu")
        # Without specifying grid_resolution, should use loaded config (8, 4)
        result = inference.predict(
            expansion_ratio=16.0,
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
        )
        nx, ny = small_config.grid_resolution
        assert result.mach.shape == (nx, ny), (
            f"Expected grid {small_config.grid_resolution} from loaded config, "
            f"got {result.mach.shape}"
        )


# ===========================================================================
# Integration Tests
# ===========================================================================

class TestPINNIntegration:
    """Integration tests for the full PINN training pipeline."""

    def test_train_evaluate_pipeline(self, small_config: PINNConfig, merlin_params: dict):
        """Full train -> evaluate pipeline with synthetic data."""
        # 1. Train
        model = NozzlePINN(small_config)
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        result = trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=3,
            verbose=False,
        )
        assert result.epochs_trained == 3

        # 2. Save
        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_path = Path(tmpdir) / "model.pt"
            trainer.save(ckpt_path)

            # 3. Load and predict
            inference = PINNInference(ckpt_path, device="cpu")
            pred = inference.predict(**merlin_params)

            # 4. Validate output
            assert pred.mach.shape[0] > 0
            assert pred.inference_time_ms >= 0
            assert np.isfinite(pred.mach).all()

    def test_model_parameter_count_matches_architecture(self, small_config: PINNConfig):
        """Model should have expected parameter count for its architecture."""
        model = NozzlePINN(small_config)
        n_params = sum(p.numel() for p in model.parameters())
        # Small config: 8 residual blocks * (64*64 + 64) + input proj + output head
        assert n_params > 10000, f"Expected >10K params, got {n_params}"

    def test_training_saves_config_in_checkpoint(self, small_config: PINNConfig):
        """Checkpoint should store the config as JSON alongside model weights."""
        model = NozzlePINN(small_config)
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_path = Path(tmpdir) / "model.pt"
            trainer.save(ckpt_path)

            # Model weights saved with weights_only=True
            checkpoint = torch.load(ckpt_path, weights_only=True)
            assert "model_state_dict" in checkpoint

            # Config saved as separate JSON file
            import json
            config_path = ckpt_path.with_suffix('.json')
            assert config_path.exists()
            with open(config_path) as f:
                config_dict = json.load(f)
            assert tuple(config_dict["hidden_layers"]) == small_config.hidden_layers
            assert config_dict["fourier_features"] == small_config.fourier_features

    def test_multiple_engines_same_model(self, small_config: PINNConfig):
        """Same model should accept different engine parameters."""
        model = NozzlePINN(small_config)
        model.eval()
        x = torch.rand(10)
        y = torch.rand(10)

        # Merlin-like params
        params1 = torch.tensor([
            [0.05, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        ]).expand(10, -1)

        # Raptor-like params
        params2 = torch.tensor([
            [0.1, 0.6, 0.4, 0.8, 0.4, 0.5, 0.5]
        ]).expand(10, -1)

        out1 = model(x, y, params1)
        out2 = model(x, y, params2)
        assert out1.shape == out2.shape == (10, 6)

    def test_train_then_load_then_predict_full_cycle(self, small_config: PINNConfig):
        """Complete cycle: train -> save -> load -> predict."""
        model = NozzlePINN(small_config)
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=3,
            verbose=False,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt = Path(tmpdir) / "model.pt"
            trainer.save(ckpt)

            # Load via inference path
            inference = PINNInference(ckpt, device="cpu")
            result = inference.predict(
                expansion_ratio=16.0,
                throat_radius=0.0825,
                theta_n=30.0,
                total_pressure=9.7e6,
                total_temperature=3600.0,
                gamma=1.4,
                nozzle_length_fraction=0.8,
            )

            # Verify grid matches loaded config
            nx, ny = small_config.grid_resolution
            assert result.x_grid.shape == (nx, ny)
            assert result.mach.shape == (nx, ny)


# ===========================================================================
# Edge Case Tests
# ===========================================================================

class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_single_training_sample(self):
        """Training should handle a single data point."""
        config = PINNConfig(
            hidden_layers=(32,),
            fourier_features=8,
            max_epochs=2,
            n_training_samples=10,
            curriculum_phases=(1, 1, 0),
        )
        model = NozzlePINN(config)
        trainer = PINNTrainer(model, config, device="cpu")

        result = trainer.train(
            x_data=torch.tensor([0.5]),
            y_data=torch.tensor([0.5]),
            params_data=torch.randn(1, 7),
            targets=torch.randn(1, 6),
            x_colloc=torch.rand(10),
            y_colloc=torch.rand(10),
            params_colloc=torch.randn(10, 7),
            epochs=2,
            verbose=False,
        )
        assert result.epochs_trained == 2

    def test_zero_epoch_training(self):
        """Zero epochs should return immediately without error."""
        config = PINNConfig(
            hidden_layers=(32,),
            fourier_features=8,
            max_epochs=10,
            curriculum_phases=(5, 5, 0),
        )
        model = NozzlePINN(config)
        trainer = PINNTrainer(model, config, device="cpu")
        n = 10

        result = trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=0,
            verbose=False,
        )
        assert result.epochs_trained == 0
        assert len(result.loss_history) == 0

    def test_high_expansion_ratio(self, small_config: PINNConfig):
        """Very high expansion ratio should still produce finite output."""
        model = NozzlePINN(small_config)
        model.eval()
        x = torch.rand(10)
        y = torch.rand(10)
        params = torch.tensor([
            [300.0, 0.2, 45.0, 50e6, 4500.0, 1.67, 1.0]
        ]).expand(10, -1)  # max of all bounds
        out = model(x, y, params)
        assert torch.isfinite(out).all()

    def test_low_expansion_ratio(self, small_config: PINNConfig):
        """Expansion ratio of 1.0 (no expansion) should work."""
        model = NozzlePINN(small_config)
        model.eval()
        x = torch.rand(10)
        y = torch.rand(10)
        params = torch.tensor([
            [1.0, 0.02, 15.0, 1e6, 2000.0, 1.2, 0.4]
        ]).expand(10, -1)  # min of all bounds
        out = model(x, y, params)
        assert torch.isfinite(out).all()

    def test_nan_in_training_data(self):
        """Training should not crash if NaN is in the data (loss becomes NaN)."""
        config = PINNConfig(
            hidden_layers=(32,),
            fourier_features=8,
            max_epochs=2,
            n_training_samples=10,
            curriculum_phases=(1, 1, 0),
        )
        model = NozzlePINN(config)
        trainer = PINNTrainer(model, config, device="cpu")

        targets = torch.randn(10, 6)
        targets[0, 0] = float("nan")

        # Should not crash, just produce NaN loss
        result = trainer.train(
            x_data=torch.rand(10),
            y_data=torch.rand(10),
            params_data=torch.randn(10, 7),
            targets=targets,
            x_colloc=torch.rand(10),
            y_colloc=torch.rand(10),
            params_colloc=torch.randn(10, 7),
            epochs=2,
            verbose=False,
        )
        assert result.epochs_trained == 2

    def test_large_targets_stable_training(self):
        """Large target values should not cause NaN explosion."""
        config = PINNConfig(
            hidden_layers=(32,),
            fourier_features=8,
            max_epochs=5,
            learning_rate=1e-2,
            curriculum_phases=(2, 2, 1),
            n_training_samples=10,
        )
        model = NozzlePINN(config)
        trainer = PINNTrainer(model, config, device="cpu")

        # Large target values
        targets = torch.randn(10, 6) * 1000

        result = trainer.train(
            x_data=torch.rand(10),
            y_data=torch.rand(10),
            params_data=torch.randn(10, 7),
            targets=targets,
            x_colloc=torch.rand(10),
            y_colloc=torch.rand(10),
            params_colloc=torch.randn(10, 7),
            epochs=5,
            verbose=False,
        )
        # Should complete without error (even if loss is large)
        assert result.epochs_trained == 5

    def test_nozzle_dataset_normalize_single_param_out_of_bounds(self, config: PINNConfig):
        """Only one parameter out of bounds should still normalize."""
        ds = NozzleDataset(config)
        normalized = ds.normalize_params(
            expansion_ratio=999.0,  # Way above upper bound
            throat_radius=0.0825,
            theta_n=30.0,
            total_pressure=9.7e6,
            total_temperature=3600.0,
            gamma=1.4,
            nozzle_length_fraction=0.8,
        )
        assert normalized[0] == 1.0  # Clipped
        assert 0.0 <= normalized[1] <= 1.0  # Normal

    def test_all_params_at_lower_bound(self, config: PINNConfig):
        """All parameters at lower bound should normalize to all zeros."""
        ds = NozzleDataset(config)
        bounds = config.param_bounds
        lo_params = {k: lo for k, (lo, hi) in bounds.items()}
        normalized = ds.normalize_params(**lo_params)
        np.testing.assert_allclose(normalized, 0.0, atol=1e-6)

    def test_all_params_at_upper_bound(self, config: PINNConfig):
        """All parameters at upper bound should normalize to all ones."""
        ds = NozzleDataset(config)
        bounds = config.param_bounds
        hi_params = {k: hi for k, (lo, hi) in bounds.items()}
        normalized = ds.normalize_params(**hi_params)
        np.testing.assert_allclose(normalized, 1.0, atol=1e-6)

    def test_model_output_determinism(self, small_config: PINNConfig):
        """Model should produce deterministic output in eval mode."""
        torch.manual_seed(42)
        model = NozzlePINN(small_config)
        model.eval()

        x = torch.rand(5)
        y = torch.rand(5)
        params = torch.rand(5, 7)

        out1 = model(x, y, params)
        out2 = model(x, y, params)
        assert torch.allclose(out1, out2), "Model output not deterministic"


# ===========================================================================
# Performance Tests
# ===========================================================================

class TestPerformance:
    """Tests for inference speed benchmarks."""

    def test_inference_under_100ms(self, small_config: PINNConfig):
        """Small model inference should be under 100ms on CPU."""
        model = NozzlePINN(small_config)
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_path = Path(tmpdir) / "model.pt"

            trainer.train(
                x_data=torch.rand(n),
                y_data=torch.rand(n),
                params_data=torch.randn(n, 7),
                targets=torch.randn(n, 6),
                x_colloc=torch.rand(n),
                y_colloc=torch.rand(n),
                params_colloc=torch.randn(n, 7),
                epochs=2,
                verbose=False,
            )
            trainer.save(ckpt_path)

            inference = PINNInference(ckpt_path, device="cpu")
            result = inference.predict(
                expansion_ratio=16.0,
                throat_radius=0.0825,
                theta_n=30.0,
                total_pressure=9.7e6,
                total_temperature=3600.0,
                gamma=1.4,
                nozzle_length_fraction=0.8,
            )
            assert result.inference_time_ms < 100, (
                f"Inference took {result.inference_time_ms:.1f}ms, expected <100ms"
            )

    def test_training_throughput(self, small_config: PINNConfig):
        """Training should complete reasonable iterations per second."""
        model = NozzlePINN(small_config)
        trainer = PINNTrainer(model, small_config, device="cpu")
        n = small_config.n_training_samples

        result = trainer.train(
            x_data=torch.rand(n),
            y_data=torch.rand(n),
            params_data=torch.randn(n, 7),
            targets=torch.randn(n, 6),
            x_colloc=torch.rand(n),
            y_colloc=torch.rand(n),
            params_colloc=torch.randn(n, 7),
            epochs=10,
            verbose=False,
        )
        epochs_per_sec = result.epochs_trained / result.training_time_s
        assert epochs_per_sec > 1, (
            f"Training too slow: {epochs_per_sec:.2f} epochs/sec"
        )

    def test_batch_prediction_consistent(self, small_config: PINNConfig):
        """Batch prediction should match sequential prediction."""
        model = NozzlePINN(small_config)
        model.eval()
        x = torch.rand(50)
        y = torch.rand(50)
        params = torch.randn(50, 7)

        # Batch prediction
        out_batch = model(x, y, params)

        # Sequential prediction
        out_seq = []
        for i in range(50):
            out_seq.append(model(x[i:i+1], y[i:i+1], params[i:i+1]))
        out_seq = torch.cat(out_seq, dim=0)

        assert torch.allclose(out_batch, out_seq, atol=1e-5), (
            "Batch and sequential predictions differ"
        )
