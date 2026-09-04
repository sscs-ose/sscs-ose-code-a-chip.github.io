#!/usr/bin/env python3
"""
NeuroSAR quick demo — generates data, trains a small model,
runs inference, and produces key figures.

Usage:
    python scripts/run_demo.py
    python scripts/run_demo.py --epochs 100 --samples 2000
"""

import argparse
import os
import sys

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DESIGN, FIGURES
from src.utils import seed_everything, get_device, ensure_dir
from src.dataset import generate_synthetic_dataset, save_dataset
from src.train_pinn import train
from src.evaluate import load_model, infer_single, evaluate_dataset
from src.plotting import (
    plot_conversion_summary,
    plot_dac_waveform,
    plot_comparator_regen,
    save_figure,
)
from src.fom_analysis import parameter_sweep_2d
from src.plotting import plot_fom_heatmap

import numpy as np


def main():
    parser = argparse.ArgumentParser(description="NeuroSAR Demo")
    parser.add_argument("--epochs", type=int, default=100,
                        help="Training epochs (default 100)")
    parser.add_argument("--samples", type=int, default=4000,
                        help="Dataset size (default 4000)")
    parser.add_argument("--skip-train", action="store_true",
                        help="Skip training, use existing checkpoint")
    args = parser.parse_args()

    device = get_device()
    print("=" * 60)
    print("  NeuroSAR — Quick Demo")
    print(f"  Device: {device}")
    print("=" * 60)

    # Step 1: Generate dataset
    print("\n[1/5] Generating synthetic dataset ...")
    data = generate_synthetic_dataset(n_samples=args.samples)
    save_dataset(data)

    # Step 2: Train PINN
    if not args.skip_train:
        print(f"\n[2/5] Training PINN for {args.epochs} epochs ...")
        best_path = train(epochs=args.epochs, device=device)
    else:
        print("\n[2/5] Skipping training (--skip-train)")
        best_path = None

    # Step 3: Load model and evaluate
    print("\n[3/5] Evaluating model ...")
    model = load_model(best_path, device)
    metrics = evaluate_dataset(model, data, device, n_samples=500)

    # Step 4: Generate waveform figures
    print("\n[4/5] Generating figures ...")
    result = infer_single(model, vin=0.9, gm=500e-6, cu=10e-15)
    ensure_dir(FIGURES)

    fig_dac = plot_dac_waveform(result["vdac"])
    save_figure(fig_dac, "demo_dac_waveform", formats=["png"])

    t_local = np.linspace(0, 1, DESIGN.n_time_steps)
    fig_comp = plot_comparator_regen(result["vcomp"], t_local)
    save_figure(fig_comp, "demo_comparator_regen", formats=["png"])

    fig_summary = plot_conversion_summary(
        result["vdac"], result["vdiff"], result["vcomp"], t_local
    )
    save_figure(fig_summary, "demo_conversion_summary", formats=["png"])

    # Step 5: Quick FoM sweep
    print("\n[5/5] Running FoM sweep ...")
    sweep = parameter_sweep_2d(
        model,
        param_x="cu", param_y="gm",
        x_range=(1e-15, 50e-15), y_range=(50e-6, 2e-3),
        n_grid=15,
    )
    fig_energy = plot_fom_heatmap(
        sweep["x_vals"], sweep["y_vals"], sweep["energy"],
        "C_unit (F)", "g_m (S)", "Energy (J)", "Energy vs Cu & gm",
    )
    save_figure(fig_energy, "demo_energy_heatmap", formats=["png"])

    print("\n" + "=" * 60)
    print("  Demo complete!")
    print(f"  Figures saved to: {FIGURES}")
    print("  Next: open notebooks/06_NeuroSAR_Interactive_Demo.ipynb")
    print("=" * 60)


if __name__ == "__main__":
    main()
