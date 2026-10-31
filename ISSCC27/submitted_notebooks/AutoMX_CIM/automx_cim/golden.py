"""High-level Phase-1 golden-model entry points and ablations."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .fixed_point import AutoMXFixedConfig, FixedProjectionResult, fixed_mxfp4_qtea_projection
from .mxfp4 import MXFP4Block
from .projection import QTEAProjection, mxfp4_qtea_projection


def projection_ablation(activation: MXFP4Block, payload: QTEAProjection) -> dict[str, np.ndarray]:
    """Return nested feature ablations using one common MXFP4 activation."""
    zeros_beta = np.zeros_like(payload.beta)
    zeros_residual = np.zeros_like(payload.ternary, dtype=np.float64)
    ternary_only = replace(payload, beta=zeros_beta, col_v=np.ones_like(payload.col_v),
                           residual=zeros_residual)
    with_v = replace(payload, beta=zeros_beta, residual=zeros_residual)
    with_beta = replace(payload, residual=zeros_residual)
    return {
        "ternary_only": mxfp4_qtea_projection(activation, ternary_only),
        "ternary_col_v": mxfp4_qtea_projection(activation, with_v),
        "ternary_col_v_beta": mxfp4_qtea_projection(activation, with_beta),
        "full_residual": mxfp4_qtea_projection(activation, payload),
    }


__all__ = [
    "AutoMXFixedConfig", "FixedProjectionResult", "fixed_mxfp4_qtea_projection",
    "projection_ablation",
]
