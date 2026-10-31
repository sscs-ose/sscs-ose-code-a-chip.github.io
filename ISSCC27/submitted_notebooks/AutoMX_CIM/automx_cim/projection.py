"""Golden projection for MXFP4 activations and QTEA-style ternary weights."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .mxfp4 import BLOCK_SIZE, MXFP4Block


@dataclass(frozen=True)
class QTEAProjection:
    """Hardware-facing QTEA payload for one ``K x M`` linear projection.

    The tensor orientation follows Ankhdjet's CiROM arrays: input/reduction
    axis first, output columns second.  ``alpha`` and ``beta`` are ``(M,G)``
    where ``G=K/group_size``.  ``col_v`` is per-input-column.  The optional
    residual is the already-expanded 1:4 FP8 residual, with zero at every
    non-selected entry; keeping it dense here makes the golden contract
    independent from its eventual side-SRAM packing.
    """

    ternary: np.ndarray
    alpha: np.ndarray
    beta: np.ndarray
    col_v: np.ndarray
    residual: np.ndarray | None = None
    group_size: int = BLOCK_SIZE

    def __post_init__(self) -> None:
        t = np.asarray(self.ternary)
        if t.ndim != 2 or not set(np.unique(t)).issubset({-1, 0, 1}):
            raise ValueError("ternary must be a K x M array with values {-1,0,+1}")
        k, m = t.shape
        if self.group_size != BLOCK_SIZE or k % self.group_size:
            raise ValueError("AutoMX-CIM requires K divisible into MX blocks of 32")
        g = k // self.group_size
        if np.asarray(self.alpha).shape != (m, g) or np.asarray(self.beta).shape != (m, g):
            raise ValueError("alpha and beta must have shape (M, K/32)")
        if np.asarray(self.col_v).shape != (k,):
            raise ValueError("col_v must have one factor for each K input")
        if self.residual is not None and np.asarray(self.residual).shape != (k, m):
            raise ValueError("residual must have the same K x M shape as ternary")

    @property
    def shape(self) -> tuple[int, int]:
        return tuple(np.asarray(self.ternary).shape)


def _as_numpy(value) -> np.ndarray:
    """Accept NumPy and CPU/GPU torch-like tensors without importing torch."""
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def from_qtea_payload(payload: dict, target_group_size: int = BLOCK_SIZE) -> QTEAProjection:
    """Adapt the *unpacked* dictionary returned by ``QTEA.quantize()``.

    QTEA stores matrices as ``(output rows, input columns)`` and normally
    uses groups of 128 input columns.  AutoMX-CIM uses a 32-element reduction
    block, so this adapter transposes the matrix and repeats each original
    alpha/beta group over its four MX blocks.  That preserves the existing
    QTEA reconstruction exactly; it does not silently re-quantize the model.

    The input must be the direct, unpacked result of ``QTEA.quantize()``, not
    the five-trit-per-byte output of ``pack_layer``.  This keeps the core
    package Torch-free and makes a later packed-payload reader an explicit,
    separately tested format decision.
    """
    # Kept here as the stable public API.  The format-specific implementation
    # lives in qtea_adapter so projection arithmetic stays independent of the
    # external checkpoint representation.
    from .qtea_adapter import from_qtea_unpacked

    return from_qtea_unpacked(payload, target_group_size=target_group_size)


def mxfp4_qtea_projection(activation: MXFP4Block, payload: QTEAProjection) -> np.ndarray:
    """Evaluate one quantized projection by the planned CIM arithmetic.

    This does not dequantize an activation and call generic floating GEMM.
    It uses signed E2M1 magnitudes times two, applies the E8M0 block scale,
    and exposes the three correction paths: ternary base, beta correction,
    and sparse residual.  It is therefore the golden model for the exporter
    and future RTL testbench.
    """
    k, m = payload.shape
    if activation.shape != (k,):
        raise ValueError(f"activation shape {activation.shape} does not match K={k}")
    ternary = np.asarray(payload.ternary, dtype=np.int64).reshape(-1, BLOCK_SIZE, m)
    alpha = np.asarray(payload.alpha, dtype=np.float64)
    beta = np.asarray(payload.beta, dtype=np.float64)
    col_v = np.asarray(payload.col_v, dtype=np.float64).reshape(-1, BLOCK_SIZE)
    residual = (np.zeros((k, m), dtype=np.float64) if payload.residual is None
                else np.asarray(payload.residual, dtype=np.float64)).reshape(-1, BLOCK_SIZE, m)

    smag2 = activation.signed_magnitude_x2().astype(np.float64)
    scale = np.exp2(activation.scale_e8m0.astype(np.int16) - 128).astype(np.float64)
    out = np.zeros(m, dtype=np.float64)
    for group in range(k // BLOCK_SIZE):
        x = smag2[group]
        # 0.5 is incorporated in scale: x contains magnitude multiplied by 2.
        base = (ternary[group] * (x * col_v[group])[:, None]).sum(axis=0)
        offset = x.sum()
        correction = (residual[group] * x[:, None]).sum(axis=0)
        out += scale[group] * (alpha[:, group] * base + beta[:, group] * offset + correction)
    return out
