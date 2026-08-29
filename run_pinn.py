#!/usr/bin/env python3
"""PINN CLI for nozzle flow prediction.

Usage:
    uv run python run_pinn.py --mode train --engine merlin-1d --epochs 10
    uv run python run_pinn.py --mode evaluate --engine merlin-1d
    uv run python run_pinn.py --mode predict --engine merlin-1d
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np

from pinn.config import PINNConfig
from pinn.model import NozzlePINN
from pinn.data import NozzleDataset
from pinn.trainer import PINNTrainer
from pinn.inference import PINNInference


# Engine parameter presets matching the CFD pipeline
ENGINE_PARAMS = {
    "merlin-1d": {
        "expansion_ratio": 16.0,
        "throat_radius": 0.0825,
        "theta_n": 30.0,
        "total_pressure": 9.7e6,
        "total_temperature": 3600.0,
        "gamma": 1.4,
        "nozzle_length_fraction": 0.8,
    },
    "raptor-sl": {
        "expansion_ratio": 34.0,
        "throat_radius": 0.0825,
        "theta_n": 28.0,
        "total_pressure": 33e6,
        "total_temperature": 3500.0,
        "gamma": 1.4,
        "nozzle_length_fraction": 0.8,
    },
    "rs-25": {
        "expansion_ratio": 77.5,
        "throat_radius": 0.136,
        "theta_n": 25.0,
        "total_pressure": 20.6e6,
        "total_temperature": 3500.0,
        "gamma": 1.4,
        "nozzle_length_fraction": 0.8,
    },
    "rl10b-2": {
        "expansion_ratio": 285.0,
        "throat_radius": 0.077,
        "theta_n": 20.0,
        "total_pressure": 4.2e6,
        "total_temperature": 3500.0,
        "gamma": 1.4,
        "nozzle_length_fraction": 0.8,
    },
}

CHECKPOINT_DIR = Path("output/pinn")


def cmd_train(args: argparse.Namespace) -> int:
    """Train PINN model with synthetic data (no VTU required)."""
    import torch

    engine = args.engine
    params = ENGINE_PARAMS[engine]

    print(f"Training PINN for {engine}")
    print(f"  Expansion ratio: {params['expansion_ratio']}")
    print(f"  Throat radius: {params['throat_radius']} m")
    print(f"  Total pressure: {params['total_pressure']/1e6:.1f} MPa")

    config = PINNConfig()
    model = NozzlePINN(config)

    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Model parameters: {n_params:,}")

    # Generate synthetic training data from isentropic relations
    dataset = NozzleDataset(config)
    n_train = config.n_training_samples
    n_val = config.n_validation_samples

    rng = np.random.default_rng(42)
    x_train = rng.uniform(0.0, 1.0, n_train).astype(np.float32)
    y_train = rng.uniform(0.01, 1.0, n_train).astype(np.float32)
    params_np = dataset.normalize_params(**params)
    params_train = np.tile(params_np, (n_train, 1)).astype(np.float32)

    # Synthetic targets: isentropic-like profiles
    targets_train = _generate_synthetic_targets(x_train, y_train, params)

    # Collocation points
    x_colloc = rng.uniform(0.0, 1.0, n_train).astype(np.float32)
    y_colloc = rng.uniform(0.01, 1.0, n_train).astype(np.float32)
    params_colloc = np.tile(params_np, (n_train, 1)).astype(np.float32)

    # Train
    trainer = PINNTrainer(model, config)
    result = trainer.train(
        x_data=torch.from_numpy(x_train),
        y_data=torch.from_numpy(y_train),
        params_data=torch.from_numpy(params_train),
        targets=torch.from_numpy(targets_train),
        x_colloc=torch.from_numpy(x_colloc),
        y_colloc=torch.from_numpy(y_colloc),
        params_colloc=torch.from_numpy(params_colloc),
        epochs=args.epochs,
    )

    # Save checkpoint
    ckpt_path = CHECKPOINT_DIR / f"{engine}_pinn.pt"
    trainer.save(ckpt_path)

    print(f"\nTraining complete:")
    print(f"  Epochs: {result.epochs_trained}")
    print(f"  Final loss: {result.final_loss:.6f}")
    print(f"  Training time: {result.training_time_s:.1f}s")
    print(f"  Checkpoint: {ckpt_path}")

    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Evaluate trained PINN model."""
    engine = args.engine
    ckpt_path = CHECKPOINT_DIR / f"{engine}_pinn.pt"

    if not ckpt_path.exists():
        print(f"Error: No checkpoint found at {ckpt_path}")
        print(f"Run training first: uv run python run_pinn.py --mode train --engine {engine}")
        return 1

    print(f"Evaluating PINN for {engine}")

    inference = PINNInference(ckpt_path)
    params = ENGINE_PARAMS[engine]

    result = inference.predict(**params)

    print(f"  Grid: {result.x_grid.shape}")
    print(f"  Mach range: [{result.mach.min():.3f}, {result.mach.max():.3f}]")
    print(f"  Pressure range: [{result.pressure.min():.0f}, {result.pressure.max():.0f}] Pa")
    print(f"  Inference time: {result.inference_time_ms:.1f} ms")

    # Save results
    output_dir = CHECKPOINT_DIR / engine
    output_dir.mkdir(parents=True, exist_ok=True)

    np.savez(
        output_dir / "prediction.npz",
        x=result.x_grid,
        y=result.y_grid,
        mach=result.mach,
        pressure=result.pressure,
        temperature=result.temperature,
        density=result.density,
        velocity_x=result.velocity_x,
        velocity_y=result.velocity_y,
    )

    summary = {
        "engine": engine,
        "mach_min": float(result.mach.min()),
        "mach_max": float(result.mach.max()),
        "inference_time_ms": result.inference_time_ms,
        "grid_shape": list(result.x_grid.shape),
    }
    with open(output_dir / "eval_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"  Results saved to {output_dir}")
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    """Run prediction and generate visualization."""
    engine = args.engine
    ckpt_path = CHECKPOINT_DIR / f"{engine}_pinn.pt"

    if not ckpt_path.exists():
        print(f"Error: No checkpoint found at {ckpt_path}")
        return 1

    inference = PINNInference(ckpt_path)
    params = ENGINE_PARAMS[engine]

    result = inference.predict(**params)

    # Plot Mach contour
    try:
        import matplotlib.pyplot as plt
        from matplotlib.tri import Triangulation

        fig, axes = plt.subplots(2, 3, figsize=(15, 8))

        fields = [
            (result.mach, "Mach", "jet"),
            (result.pressure, "Pressure (Pa)", "viridis"),
            (result.temperature, "Temperature (K)", "hot"),
            (result.density, "Density (kg/m3)", "plasma"),
            (result.velocity_x, "Vx (m/s)", "coolwarm"),
            (result.velocity_y, "Vy (m/s)", "coolwarm"),
        ]

        for ax, (data, label, cmap) in zip(axes.flat, fields):
            x = result.x_grid
            y = result.y_grid

            # Mirrored contour (axisymmetric)
            x_all = np.concatenate([x.ravel(), x.ravel()])
            y_all = np.concatenate([y.ravel(), -y.ravel()])
            d_all = np.concatenate([data.ravel(), data.ravel()])

            triang = Triangulation(x_all, y_all)
            contour = ax.tricontourf(triang, d_all, levels=20, cmap=cmap)
            ax.tricontour(triang, d_all, levels=20, colors="k", linewidths=0.3, alpha=0.3)
            plt.colorbar(contour, ax=ax, label=label)
            ax.set_xlabel("x (normalized)")
            ax.set_ylabel("y (normalized)")
            ax.set_aspect("equal")

        fig.suptitle(
            f"PINN Prediction: {engine} (inference: {result.inference_time_ms:.1f} ms)",
            fontsize=14,
        )
        plt.tight_layout()

        plot_dir = Path("docs/assets/images") / engine / "pinn"
        plot_dir.mkdir(parents=True, exist_ok=True)
        plot_path = plot_dir / "pinn_prediction.png"
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"  Plot saved: {plot_path}")

    except ImportError:
        print("  Matplotlib not available, skipping plot")

    return 0


def _generate_synthetic_targets(
    x: np.ndarray,
    y: np.ndarray,
    params: dict,
    gamma: float = 1.4,
) -> np.ndarray:
    """Generate synthetic training targets using isentropic relations.

    Creates approximate flow field data for training without requiring
    actual SU2 VTU files. Uses the isentropic area-Mach relation to
    compute local Mach number from a quadratic area profile.

    Args:
        x: (N,) normalized x-coordinates
        y: (N,) normalized y-coordinates
        params: Engine parameters
        gamma: Ratio of specific heats

    Returns:
        (N, 6) target values [Mach, P, T, rho, Vx, Vy]
    """
    from scipy.optimize import brentq
    from validation.isentropic import area_mach_relation, exit_mach_from_area_ratio

    epsilon = params["expansion_ratio"]
    p0 = params["total_pressure"]
    T0 = params["total_temperature"]

    # Get exit Mach from isentropic area-Mach relation
    mach_exit = exit_mach_from_area_ratio(epsilon, gamma)

    # Model nozzle area profile: quadratic from inlet to throat to exit
    # Throat at x=0.5 (area_ratio=1), exit at x=1.0 (area_ratio=epsilon)
    t = 2.0 * (x - 0.5)  # ranges from -1 (inlet) to 0 (throat) to 1 (exit)
    local_area_ratio = 1.0 + (epsilon - 1.0) * t ** 2

    # Solve for Mach from local area ratio using isentropic relation
    mach = np.zeros_like(x, dtype=np.float64)
    for i, ar in enumerate(local_area_ratio):
        if abs(ar - 1.0) < 1e-10:
            mach[i] = 1.0  # At throat
        elif ar > 1.0:
            # Supersonic branch (diverging section)
            try:
                mach[i] = brentq(
                    lambda M: area_mach_relation(M, gamma) - ar,
                    1.0 + 1e-6, 10.0,
                )
            except ValueError:
                mach[i] = mach_exit * min(1.0, max(0.0, (x[i] - 0.3) / 0.7))
        else:
            # Subsonic branch (converging section, ar < 1 is unphysical here)
            mach[i] = 0.1  # Low subsonic at inlet

    # Radial profile: slight variation near axis
    mach = mach * (0.8 + 0.2 * y)

    # Isentropic relations
    pressure = p0 * (1.0 + (gamma - 1.0) / 2.0 * mach ** 2) ** (
        -gamma / (gamma - 1.0)
    )
    temperature = T0 * (1.0 + (gamma - 1.0) / 2.0 * mach ** 2) ** (-1.0)
    density = pressure / (287.058 * temperature + 1e-10)

    # Velocities
    speed_of_sound = np.sqrt(gamma * 287.058 * temperature)
    vx = mach * speed_of_sound
    vy = np.zeros_like(vx)

    targets = np.column_stack([mach, pressure, temperature, density, vx, vy])
    return targets.astype(np.float32)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PINN for nozzle flow prediction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Train for 10 epochs:     uv run python run_pinn.py --mode train --engine merlin-1d --epochs 10
  Evaluate model:          uv run python run_pinn.py --mode evaluate --engine merlin-1d
  Predict and plot:        uv run python run_pinn.py --mode predict --engine merlin-1d
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["train", "evaluate", "predict"],
        required=True,
        help="Execution mode",
    )
    parser.add_argument(
        "--engine",
        choices=list(ENGINE_PARAMS.keys()),
        default="merlin-1d",
        help="Engine preset (default: merlin-1d)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Training epochs (default: 100)",
    )

    args = parser.parse_args()

    import torch

    print(f"PINN Nozzle Flow Prediction")
    print(f"  PyTorch: {torch.__version__}")
    print(f"  Device: cpu")
    print(f"  Mode: {args.mode}")
    print()

    if args.mode == "train":
        return cmd_train(args)
    elif args.mode == "evaluate":
        return cmd_evaluate(args)
    elif args.mode == "predict":
        return cmd_predict(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
