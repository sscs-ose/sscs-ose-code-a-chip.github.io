"""Frozen Phase-1 fixed-point contract and integer-equivalent golden model."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .mxfp4 import BLOCK_SIZE, MXFP4Block
from .projection import QTEAProjection


@dataclass(frozen=True)
class FixedPointFormat:
    """Saturating binary fixed-point format using round-to-nearest-even."""

    total_bits: int
    fraction_bits: int
    signed: bool = True

    def __post_init__(self) -> None:
        sign_bits = 1 if self.signed else 0
        if self.total_bits <= sign_bits or not 0 <= self.fraction_bits < self.total_bits:
            raise ValueError("invalid fixed-point width")

    @property
    def minimum_integer(self) -> int:
        return -(1 << (self.total_bits - 1)) if self.signed else 0

    @property
    def maximum_integer(self) -> int:
        return (1 << (self.total_bits - (1 if self.signed else 0))) - 1

    def quantize(self, value) -> np.ndarray:
        x = np.asarray(value, dtype=np.float64)
        if not np.all(np.isfinite(x)):
            raise ValueError("fixed-point input must be finite")
        rounded = np.rint(x * (1 << self.fraction_bits))
        return np.clip(rounded, self.minimum_integer, self.maximum_integer).astype(np.int64)

    def dequantize(self, integer) -> np.ndarray:
        return np.asarray(integer, dtype=np.float64) / (1 << self.fraction_bits)


@dataclass(frozen=True)
class AutoMXFixedConfig:
    """Phase-1 formats; changing one creates a different hardware contract."""

    alpha: FixedPointFormat = field(default_factory=lambda: FixedPointFormat(16, 12, False))
    col_v: FixedPointFormat = field(default_factory=lambda: FixedPointFormat(16, 12, False))
    beta: FixedPointFormat = field(default_factory=lambda: FixedPointFormat(16, 12, True))
    residual: FixedPointFormat = field(default_factory=lambda: FixedPointFormat(16, 12, True))
    accumulator_bits: int = 48

    def __post_init__(self) -> None:
        if self.alpha.fraction_bits + self.col_v.fraction_bits < self.beta.fraction_bits:
            raise ValueError("beta cannot have more fractional bits than alpha*col_v")
        if self.residual.fraction_bits != self.beta.fraction_bits:
            raise ValueError("beta and residual must use the same fractional width")
        if not 2 <= self.accumulator_bits <= 63:
            raise ValueError("accumulator_bits must fit the int64 reference model")


@dataclass(frozen=True)
class FixedProjectionResult:
    output: np.ndarray
    group_accumulator: np.ndarray
    accumulator_fraction_bits: int


def _saturate_signed(value: np.ndarray, bits: int) -> np.ndarray:
    minimum, maximum = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    return np.clip(value, minimum, maximum).astype(np.int64)


def fixed_mxfp4_qtea_projection(
    activation: MXFP4Block,
    payload: QTEAProjection,
    config: AutoMXFixedConfig = AutoMXFixedConfig(),
) -> FixedProjectionResult:
    """Evaluate the frozen integer datapath and expose each block accumulator.

    ``alpha*col_v`` defines the accumulator fractional width.  Beta and
    residual are left-shifted into that domain.  Each K=32 group is saturated
    to ``accumulator_bits``; E8M0 scaling is applied only when producing the
    floating diagnostic output.  RTL can compare the integer group array
    exactly and need not compare floating-point values.
    """
    k, m = payload.shape
    if activation.shape != (k,):
        raise ValueError(f"activation shape {activation.shape} does not match K={k}")
    groups = k // BLOCK_SIZE
    frac = config.alpha.fraction_bits + config.col_v.fraction_bits
    align = frac - config.beta.fraction_bits
    aq = config.alpha.quantize(payload.alpha)
    vq = config.col_v.quantize(payload.col_v).reshape(groups, BLOCK_SIZE)
    bq = config.beta.quantize(payload.beta)
    residual = np.zeros((k, m)) if payload.residual is None else payload.residual
    rq = config.residual.quantize(residual).reshape(groups, BLOCK_SIZE, m)
    ternary = np.asarray(payload.ternary, dtype=np.int64).reshape(groups, BLOCK_SIZE, m)
    act = activation.signed_magnitude_x2().astype(np.int64).reshape(groups, BLOCK_SIZE)
    group_acc = np.empty((groups, m), dtype=np.int64)
    for group in range(groups):
        base = (act[group, :, None] * ternary[group] * vq[group, :, None]).sum(axis=0)
        alpha_base = aq[:, group] * base
        beta_term = bq[:, group] * act[group].sum()
        residual_term = (act[group, :, None] * rq[group]).sum(axis=0)
        combined = alpha_base + ((beta_term + residual_term) << align)
        group_acc[group] = _saturate_signed(combined, config.accumulator_bits)
    scale = np.exp2(activation.scale_e8m0.astype(np.int16) - 128)
    output = (group_acc.astype(np.float64) * scale[:, None]).sum(axis=0) / (1 << frac)
    return FixedProjectionResult(output, group_acc, frac)
