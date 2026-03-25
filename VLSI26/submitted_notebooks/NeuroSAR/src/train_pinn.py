"""
NeuroSAR training pipeline — end-to-end PINN training with logging,
checkpointing, and evaluation hooks.

Usage
-----
    python src/train_pinn.py                     # defaults
    python src/train_pinn.py --epochs 1000       # override
    python src/train_pinn.py --device cuda        # GPU
"""

import argparse
import os
import time
from typing import Dict, Optional

import torch
import torch.nn as nn
from torch.optim.lr_scheduler import CosineAnnealingLR, StepLR
from tqdm import tqdm

from src.config import TRAIN, DESIGN, CHECKPOINTS
from src.utils import seed_everything, get_device, ensure_dir
from src.dataset import (
    generate_synthetic_dataset,
    build_dataloaders,
    save_dataset,
    load_dataset,
    DESIGN_PARAM_NAMES,
)
from src.pinn_model import NeuroSARNet
from src.losses import total_pinn_loss


# =========================================================================
# Training loop
# =========================================================================

def train_one_epoch(
    model: NeuroSARNet,
    dataloader,
    optimiser: torch.optim.Optimizer,
    t_local: torch.Tensor,
    device: torch.device,
    n_bits: int,
    loss_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Train for one epoch, return average losses."""
    model.train()
    accum = {}
    n_batches = 0

    for batch in dataloader:
        params  = batch["params"].to(device)
        vdac_gt = batch["vdac"].to(device)
        vdiff_gt = batch["vdiff"].to(device)
        vcomp_gt = batch["vcomp"].to(device)
        energy_gt = batch["energy"].to(device)
        bits    = batch["bits"].to(device)

        B = params.shape[0]

        # Randomly sample a bit index per sample in the batch
        bit_idx = torch.randint(0, n_bits, (B,), device=device)

        # Gather ground truth for the selected bit
        target = {
            "vdac":   vdac_gt[torch.arange(B), bit_idx + 1].unsqueeze(-1),
            "vdiff":  vdiff_gt[torch.arange(B), bit_idx],
            "vcomp":  vcomp_gt[torch.arange(B), bit_idx],
            "energy": energy_gt.unsqueeze(-1),
        }

        # Forward
        pred = model(params, t_local, bit_idx.float())

        # Loss
        losses = total_pinn_loss(
            pred, target, params, t_local, bits,
            n_bits=n_bits, weights=loss_weights,
        )

        # Backward
        optimiser.zero_grad()
        losses["total"].backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimiser.step()

        # Accumulate
        for k, v in losses.items():
            accum[k] = accum.get(k, 0.0) + v.item()
        n_batches += 1

    return {k: v / n_batches for k, v in accum.items()}


@torch.no_grad()
def validate(
    model: NeuroSARNet,
    dataloader,
    t_local: torch.Tensor,
    device: torch.device,
    n_bits: int,
    loss_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Validation pass (no gradients)."""
    model.eval()
    accum = {}
    n_batches = 0

    for batch in dataloader:
        params  = batch["params"].to(device)
        vdac_gt = batch["vdac"].to(device)
        vdiff_gt = batch["vdiff"].to(device)
        vcomp_gt = batch["vcomp"].to(device)
        energy_gt = batch["energy"].to(device)
        bits    = batch["bits"].to(device)

        B = params.shape[0]
        bit_idx = torch.randint(0, n_bits, (B,), device=device)

        target = {
            "vdac":   vdac_gt[torch.arange(B), bit_idx + 1].unsqueeze(-1),
            "vdiff":  vdiff_gt[torch.arange(B), bit_idx],
            "vcomp":  vcomp_gt[torch.arange(B), bit_idx],
            "energy": energy_gt.unsqueeze(-1),
        }

        pred = model(params, t_local, bit_idx.float())
        losses = total_pinn_loss(
            pred, target, params, t_local, bits,
            n_bits=n_bits, weights=loss_weights,
        )

        for k, v in losses.items():
            accum[k] = accum.get(k, 0.0) + v.item()
        n_batches += 1

    return {k: v / max(n_batches, 1) for k, v in accum.items()}


# =========================================================================
# Main training driver
# =========================================================================

def train(
    epochs: int = TRAIN.epochs,
    lr: float = TRAIN.lr,
    device: Optional[torch.device] = None,
    dataset_path: Optional[str] = None,
    loss_weights: Optional[Dict[str, float]] = None,
) -> str:
    """
    Full training run.  Returns path to best checkpoint.
    """
    device = device or get_device()
    seed_everything(TRAIN.seed)
    ckpt_dir = ensure_dir(CHECKPOINTS)

    # ---- Dataset -------------------------------------------------------
    if dataset_path and os.path.exists(dataset_path):
        data = load_dataset(dataset_path)
    else:
        print("[NeuroSAR] Generating synthetic dataset ...")
        data = generate_synthetic_dataset()
        save_dataset(data)

    train_dl, val_dl, norm_stats = build_dataloaders(data)
    t_local = data["t_local"].to(device)
    n_bits = DESIGN.n_bits

    # ---- Model ---------------------------------------------------------
    model = NeuroSARNet(n_bits=n_bits, n_time=DESIGN.n_time_steps).to(device)
    print(f"[NeuroSAR] Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # ---- Optimiser + scheduler -----------------------------------------
    optimiser = torch.optim.AdamW(
        model.parameters(), lr=lr, weight_decay=TRAIN.weight_decay,
    )
    if TRAIN.scheduler == "cosine":
        scheduler = CosineAnnealingLR(optimiser, T_max=epochs, eta_min=lr * 0.01)
    else:
        scheduler = StepLR(optimiser, step_size=epochs // 3, gamma=0.3)

    # ---- Training loop -------------------------------------------------
    best_val_loss = float("inf")
    best_path = os.path.join(ckpt_dir, TRAIN.best_model_name)
    history = {"train": [], "val": []}

    print(f"[NeuroSAR] Training for {epochs} epochs on {device} ...")
    t0 = time.time()

    for epoch in range(1, epochs + 1):
        train_losses = train_one_epoch(
            model, train_dl, optimiser, t_local, device, n_bits, loss_weights,
        )
        val_losses = validate(model, val_dl, t_local, device, n_bits, loss_weights)
        scheduler.step()

        history["train"].append(train_losses)
        history["val"].append(val_losses)

        # Checkpoint best
        if val_losses["total"] < best_val_loss:
            best_val_loss = val_losses["total"]
            torch.save({
                "epoch": epoch,
                "model_state": model.state_dict(),
                "optimiser_state": optimiser.state_dict(),
                "val_loss": best_val_loss,
                "norm_stats": norm_stats,
                "config": {"n_bits": n_bits, "n_time": DESIGN.n_time_steps},
            }, best_path)

        # Periodic checkpoint
        if epoch % TRAIN.checkpoint_every == 0:
            ckpt_path = os.path.join(ckpt_dir, f"epoch_{epoch:04d}.pt")
            torch.save(model.state_dict(), ckpt_path)

        # Logging
        if epoch % 10 == 0 or epoch == 1:
            elapsed = time.time() - t0
            tl = train_losses
            vl = val_losses
            print(
                f"  Epoch {epoch:4d}/{epochs} | "
                f"train {tl['total']:.4e} (data {tl['data']:.3e} kcl {tl['kcl']:.3e} "
                f"charge {tl['charge']:.3e} ode {tl['comp_ode']:.3e}) | "
                f"val {vl['total']:.4e} | best {best_val_loss:.4e} | "
                f"{elapsed:.0f}s"
            )

    print(f"[NeuroSAR] Training complete. Best val loss: {best_val_loss:.4e}")
    print(f"[NeuroSAR] Best checkpoint → {best_path}")

    # Save history
    torch.save(history, os.path.join(ckpt_dir, "training_history.pt"))

    return best_path


# =========================================================================
# CLI entry
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Train NeuroSAR PINN")
    parser.add_argument("--epochs", type=int, default=TRAIN.epochs)
    parser.add_argument("--lr", type=float, default=TRAIN.lr)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--dataset", type=str, default=None,
                        help="Path to pre-generated dataset .pt file")
    args = parser.parse_args()

    device = torch.device(args.device) if args.device else None
    train(epochs=args.epochs, lr=args.lr, device=device, dataset_path=args.dataset)


if __name__ == "__main__":
    main()
