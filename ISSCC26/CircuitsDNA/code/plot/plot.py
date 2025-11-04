#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os
import matplotlib.pyplot as plt

history_path = "/home/junyi/projects/Quant/runs_qat/resnet20/history_ft_resnet20_lut_0.5.json"   
save_path    = "/home/junyi/projects/Quant/runs_qat/resnet20/history_ft_resnet20_lut_0.5.png"     
title        = "Approx Mult. Training Curves"
smooth_alpha = 0  # Exponential smoothing parameters, 0 or None indicate that no smoothing is used.


def _resolve_alpha(alpha):
    if alpha is None:
        return None
    try:
        alpha = float(alpha)
    except (TypeError, ValueError):
        return None
    if alpha <= 0:
        return None
    return alpha


ema_alpha = _resolve_alpha(smooth_alpha)
raw_alpha = 0.35 if ema_alpha else 0.9

def ema(xs, alpha=0.2):
    if xs is None: return None
    out = []
    m = None
    for v in xs:
        m = v if m is None else (alpha * v + (1 - alpha) * m)
        out.append(m)
    return out

def load_history(p):
    with open(p, "r") as f:
        raw = json.load(f)
    keys = ["train_loss", "test_loss", "train_acc", "test_acc"]
    if isinstance(raw, list):
        hist = {k: [] for k in keys}
        for entry in raw:
            for k in keys:
                hist[k].append(entry.get(k, 0.0))
        return hist
    for k in keys:
        raw.setdefault(k, [])
    return raw

history = load_history(history_path)
epochs = list(range(1, len(history["train_loss"]) + 1))

TL, TeL = history["train_loss"], history["test_loss"]
TA, TeA = history["train_acc"], history["test_acc"]

if ema_alpha:
    TLs, TeLs = ema(TL, ema_alpha), ema(TeL, ema_alpha)
    TAs, TeAs = ema(TA, ema_alpha), ema(TeA, ema_alpha)
else:
    TLs, TeLs, TAs, TeAs = TL, TeL, TA, TeA

plt.figure(figsize=(12,5))

# Loss
plt.subplot(1,2,1)
plt.plot(epochs, TL,  label="Train Loss", alpha=raw_alpha)
plt.plot(epochs, TeL, label="Test Loss",  alpha=raw_alpha)
if ema_alpha:
    plt.plot(epochs, TLs, label=f"Train Loss (EMA {ema_alpha:.2f})", alpha=1.0)
    plt.plot(epochs, TeLs, label=f"Test Loss (EMA {ema_alpha:.2f})", alpha=1.0)
plt.xlabel("Epoch"); plt.ylabel("Loss"); plt.title("Loss")
plt.grid(True); plt.legend()

# Accuracy
plt.subplot(1,2,2)
plt.plot(epochs, [a*100 for a in TA],  label="Train Acc (%)", alpha=raw_alpha)
plt.plot(epochs, [a*100 for a in TeA], label="Test Acc (%)",  alpha=raw_alpha)
if ema_alpha:
    plt.plot(epochs, [a*100 for a in TAs],  label=f"Train Acc (EMA {ema_alpha:.2f})", alpha=1.0)
    plt.plot(epochs, [a*100 for a in TeAs], label=f"Test Acc (EMA {ema_alpha:.2f})", alpha=1.0)
plt.xlabel("Epoch"); plt.ylabel("Accuracy (%)"); plt.title("Accuracy")
plt.grid(True); plt.legend()

plt.suptitle(title)
plt.tight_layout(rect=[0,0,1,0.96])

if save_path:
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    plt.savefig(save_path, dpi=180)
    print(f"Saved: {save_path}")

plt.show()
