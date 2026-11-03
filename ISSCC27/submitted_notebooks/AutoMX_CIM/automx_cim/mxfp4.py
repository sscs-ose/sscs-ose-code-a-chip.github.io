"""Finite OCP MXFP4 (E2M1 + E8M0, block 32) encoder/decoder.

The public OCP MX v1.0 format uses FP4 E2M1 elements and one E8M0
power-of-two scale for 32 elements.  This module makes the choices which a
hardware implementation must freeze: reduction-axis grouping, a
deterministic lower-magnitude choice on exactly equidistant levels,
finite-value saturation, and a canonical finite scale for an all-zero block.

NaN/Inf are intentionally rejected at this boundary.  Transformer inference
activations are expected to be finite; rejecting them is safer than silently
making a non-portable hardware rule.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


BLOCK_SIZE = 32
# Positive E2M1 values, indexed by the three low bits (exponent, mantissa).
# Index 0 is zero; the remaining values follow OCP's finite FP4 encoding.
_MAGNITUDES = np.asarray((0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0))
_MAGNITUDE_X2 = np.asarray((0, 1, 2, 3, 4, 6, 8, 12), dtype=np.int8)


@dataclass(frozen=True)
class MXFP4Block:
    """Packed MXFP4 values along the final (reduction) axis.

    ``codes`` holds standard sign/E2M1 element nibbles in uint8 containers;
    ``scale_e8m0`` holds the E8M0 byte.  A finite E8M0 byte represents
    ``2 ** (byte - 127)``.  Shapes are ``(..., blocks, 32)`` and
    ``(..., blocks)`` respectively.
    """

    codes: np.ndarray
    scale_e8m0: np.ndarray

    def __post_init__(self) -> None:
        if self.codes.dtype != np.uint8 or self.scale_e8m0.dtype != np.uint8:
            raise TypeError("MXFP4 codes and E8M0 scales must be uint8")
        if self.codes.ndim < 1 or self.codes.shape[-1] != BLOCK_SIZE:
            raise ValueError("codes must end in an MX block of 32 elements")
        if self.scale_e8m0.shape != self.codes.shape[:-1]:
            raise ValueError("one E8M0 scale is required for every 32-value block")
        if np.any(self.codes > 0x0F):
            raise ValueError("MXFP4 element code exceeds four bits")

    @property
    def shape(self) -> tuple[int, ...]:
        """Unblocked logical shape (the final axis is restored)."""
        return (*self.codes.shape[:-2], self.codes.shape[-2] * BLOCK_SIZE)

    def signed_magnitude_x2(self) -> np.ndarray:
        """Return integer E2M1 mantissas multiplied by two, including sign.

        This is the direct input to a bit-plane/ternary CIM implementation:
        values are in ``{0, ±1, ±2, ±3, ±4, ±6, ±8, ±12}`` and a block
        multiplier of ``2**(E8M0-128)`` restores the represented value.
        """
        mag = _MAGNITUDE_X2[self.codes & 0x07].astype(np.int16)
        return np.where((self.codes & 0x08) != 0, -mag, mag)


def _finite_scale_exponent(block: np.ndarray) -> int:
    maximum = float(np.max(np.abs(block)))
    if maximum == 0.0:
        # E8M0 has no literal zero.  Use its smallest finite normal scale;
        # zero element codes still decode to exact zero.
        return -127
    # Largest E2M1 magnitude is 6.  Ceiling avoids an avoidable saturation.
    return max(-127, min(127, math.ceil(math.log2(maximum / 6.0))))


def encode_mxfp4(values: np.ndarray, block_size: int = BLOCK_SIZE) -> MXFP4Block:
    """Quantize a finite array along its final axis to OCP MXFP4 blocks.

    ``block_size`` is exposed only to fail loudly: the standardized MXFP4
    contract used by AutoMX-CIM is block 32, so another value is not accepted.
    """
    if block_size != BLOCK_SIZE:
        raise ValueError("AutoMX-CIM fixes MXFP4 block_size to 32")
    x = np.asarray(values, dtype=np.float64)
    if x.ndim == 0 or x.shape[-1] % BLOCK_SIZE:
        raise ValueError("final activation axis must be a non-zero multiple of 32")
    if not np.all(np.isfinite(x)):
        raise ValueError("MXFP4 input must be finite")

    blocks = x.reshape(*x.shape[:-1], x.shape[-1] // BLOCK_SIZE, BLOCK_SIZE)
    scale_exp = np.empty(blocks.shape[:-1], dtype=np.int16)
    codes = np.empty(blocks.shape, dtype=np.uint8)
    flat_blocks = blocks.reshape(-1, BLOCK_SIZE)
    flat_exp = scale_exp.reshape(-1)
    flat_codes = codes.reshape(-1, BLOCK_SIZE)
    for i, block in enumerate(flat_blocks):
        exponent = _finite_scale_exponent(block)
        scale = math.ldexp(1.0, exponent)
        normalized = np.abs(block) / scale
        # argmin selects the lower code for an exactly equal distance.  This
        # is deterministic and is included in the generator's golden contract.
        mag_index = np.abs(normalized[:, None] - _MAGNITUDES[None, :]).argmin(axis=1)
        signs = (block < 0).astype(np.uint8)
        # Canonicalize negative zero to positive zero.
        signs[mag_index == 0] = 0
        flat_codes[i] = mag_index.astype(np.uint8) | (signs << 3)
        flat_exp[i] = exponent
    return MXFP4Block(codes=codes, scale_e8m0=(scale_exp + 127).astype(np.uint8))


def decode_mxfp4(block: MXFP4Block) -> np.ndarray:
    """Decode MXFP4 to float64, restoring the unblocked final axis."""
    magnitude = _MAGNITUDES[block.codes & 0x07]
    signed = np.where((block.codes & 0x08) != 0, -magnitude, magnitude)
    exponent = block.scale_e8m0.astype(np.int16) - 127
    decoded = signed * np.exp2(exponent[..., None])
    return decoded.reshape(block.shape)
