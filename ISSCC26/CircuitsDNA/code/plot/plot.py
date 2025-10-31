#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os
import matplotlib.pyplot as plt


history_path = "./runs_fp32/history_fp32.json"   
save_path    = "./runs_fp32/curves_fp32.png"     
title        = "FP32 Training Curves"
smooth_alpha = 0.2   # 指数平滑参数，0 或 None 表示不用


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
        h = json.load(f)
    for k in ["train_loss","test_loss","train_acc","test_acc"]:
        h.setdefault(k, [])
    return h

history = load_history(history_path)
epochs = list(range(1, len(history["train_loss"]) + 1))

TL, TeL = history["train_loss"], history["test_loss"]
TA, TeA = history["train_acc"], history["test_acc"]

if smooth_alpha and smooth_alpha > 0:
    TLs, TeLs = ema(TL, smooth_alpha), ema(TeL, smooth_alpha)
    TAs, TeAs = ema(TA, smooth_alpha), ema(TeA, smooth_alpha)
else:
    TLs, TeLs, TAs, TeAs = TL, TeL, TA, TeA

plt.figure(figsize=(12,5))

# Loss
plt.subplot(1,2,1)
plt.plot(epochs, TL,  label="Train Loss", alpha=0.35)
plt.plot(epochs, TeL, label="Test Loss",  alpha=0.35)
if smooth_alpha:
    plt.plot(epochs, TLs, label=f"Train Loss (EMA {smooth_alpha})")
    plt.plot(epochs, TeLs, label=f"Test Loss (EMA {smooth_alpha})")
plt.xlabel("Epoch"); plt.ylabel("Loss"); plt.title("Loss")
plt.grid(True); plt.legend()

# Accuracy
plt.subplot(1,2,2)
plt.plot(epochs, [a*100 for a in TA],  label="Train Acc (%)", alpha=0.35)
plt.plot(epochs, [a*100 for a in TeA], label="Test Acc (%)",  alpha=0.35)
if smooth_alpha:
    plt.plot(epochs, [a*100 for a in TAs],  label=f"Train Acc (EMA {smooth_alpha})")
    plt.plot(epochs, [a*100 for a in TeAs], label=f"Test Acc (EMA {smooth_alpha})")
plt.xlabel("Epoch"); plt.ylabel("Accuracy (%)"); plt.title("Accuracy")
plt.grid(True); plt.legend()

plt.suptitle(title)
plt.tight_layout(rect=[0,0,1,0.96])

if save_path:
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    plt.savefig(save_path, dpi=180)
    print(f"Saved: {save_path}")

plt.show()
