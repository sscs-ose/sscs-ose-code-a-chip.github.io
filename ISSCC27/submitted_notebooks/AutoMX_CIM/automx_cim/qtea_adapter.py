"""Adapters from QTEA in-memory and packed layer payloads.

QTEA stores a linear layer as ``(output rows, input columns)``.  AutoMX-CIM
uses the hardware-facing ``K x M`` orientation.  These adapters are deliberately
Torch-free: tensors are accepted through their detach/cpu/numpy protocol.
"""

from __future__ import annotations

import numpy as np

from .mxfp4 import BLOCK_SIZE
from .projection import QTEAProjection

_REQUIRED = {
    "rows", "cols", "group_size", "residual_group", "ternary", "col_v",
    "group_alpha", "group_beta", "salient_cols", "residual_index",
    "residual_value", "residual_scale",
}
_POWERS = np.asarray([1, 3, 9, 27, 81], dtype=np.int32)


def _as_numpy(value, *, float8_to_float: bool = False) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    # NumPy does not currently accept Torch float8 tensors.  QTEA's packed
    # residual may therefore need conversion to float32 before numpy().
    if float8_to_float and "float8" in str(getattr(value, "dtype", "")):
        value = value.float()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def _validate_common(payload: dict, target_group_size: int) -> tuple[int, int, int]:
    missing = sorted(_REQUIRED - set(payload))
    if missing:
        raise ValueError(f"QTEA payload missing fields: {missing}")
    if target_group_size != BLOCK_SIZE:
        raise ValueError("AutoMX-CIM fixes target_group_size to 32")
    rows, cols = int(payload["rows"]), int(payload["cols"])
    source_group = int(payload["group_size"])
    if rows <= 0 or cols <= 0 or source_group <= 0:
        raise ValueError("QTEA rows, cols and group_size must be positive")
    if cols % source_group or source_group % BLOCK_SIZE:
        raise ValueError("QTEA group size must be an integer multiple of 32")
    return rows, cols, source_group


def unpack_ternary_base3(packed, cols: int, group_size: int) -> np.ndarray:
    """Decode QTEA's five-trits-per-byte representation without Torch."""
    data = _as_numpy(packed).astype(np.uint8, copy=False)
    if data.ndim != 2 or cols % group_size:
        raise ValueError("packed ternary must be a 2-D array and cols a multiple of group_size")
    bytes_per_group = (group_size + 4) // 5
    expected = (data.shape[0], (cols // group_size) * bytes_per_group)
    if data.shape != expected:
        raise ValueError(f"packed ternary shape {data.shape} does not match {expected}")
    digits = (data.reshape(data.shape[0], -1, 1).astype(np.int32) // _POWERS) % 3 - 1
    digits = digits.reshape(data.shape[0], -1, bytes_per_group * 5)
    return digits[:, :, :group_size].reshape(data.shape[0], cols).astype(np.int8)


def _expand_residual(
    payload: dict, rows: int, cols: int, *, packed: bool
) -> np.ndarray:
    salient = _as_numpy(payload["salient_cols"]).astype(np.int64).reshape(-1)
    residual_group = int(payload["residual_group"])
    if residual_group <= 0 or rows % residual_group:
        raise ValueError("rows must be divisible by residual_group")
    values = _as_numpy(payload["residual_value"], float8_to_float=packed).astype(np.float64)
    residual = np.zeros((rows, cols), dtype=np.float64)
    if not salient.size:
        if values.size:
            raise ValueError("residual values exist but salient_cols is empty")
        return residual
    if np.any(salient < 0) or np.any(salient >= cols) or np.unique(salient).size != salient.size:
        raise ValueError("salient_cols must contain unique valid column indices")
    count = rows // residual_group
    if values.shape != (salient.size, count):
        raise ValueError("QTEA residual values have the wrong shape")

    if packed:
        packed_index = _as_numpy(payload["residual_index"]).astype(np.uint8)
        expected_bytes = (count + 3) // 4
        if packed_index.shape != (salient.size, expected_bytes):
            raise ValueError("packed QTEA residual index has the wrong shape")
        indices = np.stack([(packed_index >> shift) & 3 for shift in (0, 2, 4, 6)], axis=2)
        indices = indices.reshape(salient.size, -1)[:, :count]
        scales = _as_numpy(payload["residual_scale"]).astype(np.float64).reshape(-1)
        if scales.shape != (salient.size,) or np.any(scales <= 0) or not np.all(np.isfinite(scales)):
            raise ValueError("packed residual_scale must be one finite positive value per salient column")
        values = values / scales[:, None]
    else:
        indices = _as_numpy(payload["residual_index"]).astype(np.int64)
        if indices.shape != values.shape:
            raise ValueError("unpacked residual index/value shapes differ")
    if np.any(indices < 0) or np.any(indices >= residual_group):
        raise ValueError("QTEA residual index is outside its 1:N group")
    base = np.arange(count, dtype=np.int64) * residual_group
    for item, column in enumerate(salient):
        residual[base + indices[item], column] = values[item]
    return residual


def _build(payload: dict, ternary_rows_cols: np.ndarray, *, packed: bool,
           target_group_size: int) -> QTEAProjection:
    rows, cols, source_group = _validate_common(payload, target_group_size)
    if ternary_rows_cols.shape != (rows, cols):
        raise ValueError("QTEA ternary shape does not match rows x cols")
    if not set(np.unique(ternary_rows_cols)).issubset({-1, 0, 1}):
        raise ValueError("decoded QTEA ternary contains an invalid trit")
    alpha_src = _as_numpy(payload["group_alpha"]).astype(np.float64)
    beta_src = _as_numpy(payload["group_beta"]).astype(np.float64)
    expected_metadata = (rows, cols // source_group)
    if alpha_src.shape != expected_metadata or beta_src.shape != expected_metadata:
        raise ValueError("QTEA alpha/beta shape does not match source group size")
    col_v = _as_numpy(payload["col_v"]).astype(np.float64)
    if col_v.shape != (cols,):
        raise ValueError("QTEA col_v must contain one value per input column")
    if not all(np.all(np.isfinite(x)) for x in (alpha_src, beta_src, col_v)):
        raise ValueError("QTEA metadata must be finite")
    repeat = source_group // BLOCK_SIZE
    residual = _expand_residual(payload, rows, cols, packed=packed)
    return QTEAProjection(
        ternary=ternary_rows_cols.T.astype(np.int8),
        alpha=np.repeat(alpha_src, repeat, axis=1),
        beta=np.repeat(beta_src, repeat, axis=1),
        col_v=col_v,
        residual=residual.T,
        group_size=BLOCK_SIZE,
    )


def from_qtea_unpacked(payload: dict, target_group_size: int = BLOCK_SIZE) -> QTEAProjection:
    """Import the direct dictionary returned by ``QTEA.quantize()``."""
    rows, cols, _ = _validate_common(payload, target_group_size)
    ternary = _as_numpy(payload["ternary"])
    if ternary.shape != (rows, cols):
        raise ValueError("expected unpacked QTEA ternary shape (rows, cols)")
    return _build(payload, ternary.astype(np.int8), packed=False,
                  target_group_size=target_group_size)


def from_qtea_packed(payload: dict, target_group_size: int = BLOCK_SIZE) -> QTEAProjection:
    """Import the dictionary returned by ``QTEA.pack_layer()``.

    Loading the outer ``torch.save`` checkpoint remains the caller's job.  This
    function converts one layer dictionary and has no runtime Torch dependency.
    """
    rows, cols, source_group = _validate_common(payload, target_group_size)
    ternary = unpack_ternary_base3(payload["ternary"], cols, source_group)
    if ternary.shape[0] != rows:
        raise ValueError("packed QTEA ternary row count does not match rows")
    return _build(payload, ternary, packed=True, target_group_size=target_group_size)
