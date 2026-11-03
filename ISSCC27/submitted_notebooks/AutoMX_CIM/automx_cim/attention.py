"""Stage-1 deterministic tiny-MHA reference and MXFP4/ternary replacement."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping

import numpy as np

from .config import Sky130MHAConfig
from .fixed_point import fixed_mxfp4_qtea_projection
from .mxfp4 import BLOCK_SIZE, encode_mxfp4
from .projection import QTEAProjection


_PROJECTION_NAMES = ("WQ", "WK", "WV", "WO")


@dataclass(frozen=True)
class TinyMHAWeights:
    """Four `K x M` matrices, directly compatible with `X @ W`."""

    wq: np.ndarray
    wk: np.ndarray
    wv: np.ndarray
    wo: np.ndarray

    def __post_init__(self) -> None:
        matrices = self.as_mapping()
        shapes = {name: np.asarray(value).shape for name, value in matrices.items()}
        if any(len(shape) != 2 for shape in shapes.values()) or len(set(shapes.values())) != 1:
            raise ValueError("WQ/WK/WV/WO must be finite matrices with one common shape")
        rows, columns = next(iter(shapes.values()))
        if rows != columns or rows % BLOCK_SIZE:
            raise ValueError("tiny MHA needs square projection matrices with K divisible by 32")
        if not all(np.all(np.isfinite(value)) for value in matrices.values()):
            raise ValueError("MHA weights must be finite")

    def as_mapping(self) -> dict[str, np.ndarray]:
        return {"WQ": self.wq, "WK": self.wk, "WV": self.wv, "WO": self.wo}


@dataclass(frozen=True)
class MHAResult:
    """Observable tensors for one MHA layer; all runtime attention remains digital."""

    output: np.ndarray
    q: np.ndarray
    k: np.ndarray
    v: np.ndarray
    scores: np.ndarray
    probabilities: np.ndarray
    context: np.ndarray


@dataclass(frozen=True)
class Stage1Result:
    """FP32 versus MXFP4/ternary MHA result and reproducibility inputs."""

    config: Sky130MHAConfig
    input_x: np.ndarray
    weights: TinyMHAWeights
    payloads: Mapping[str, QTEAProjection]
    fp32: MHAResult
    quantized: MHAResult
    metrics: Mapping[str, float]


def softmax(values: np.ndarray, axis: int = -1) -> np.ndarray:
    """Numerically stable digital softmax for the MHA reference."""
    array = np.asarray(values, dtype=np.float64)
    shifted = array - array.max(axis=axis, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=axis, keepdims=True)


def _validate_input(x: np.ndarray, d_model: int) -> np.ndarray:
    array = np.asarray(x, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != d_model or array.shape[0] < 2:
        raise ValueError("MHA input must be [sequence>=2, d_model]")
    if not np.all(np.isfinite(array)):
        raise ValueError("MHA input must be finite")
    return array


def mha_from_projections(
    q: np.ndarray, k: np.ndarray, v: np.ndarray, output_projection: np.ndarray, heads: int,
) -> MHAResult:
    """Execute the digital attention runtime from supplied Q/K/V projections."""
    q = np.asarray(q, dtype=np.float64)
    k = np.asarray(k, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    wo = np.asarray(output_projection, dtype=np.float64)
    if q.ndim != 2 or q.shape != k.shape or q.shape != v.shape:
        raise ValueError("Q, K, and V must have matching [sequence, d_model] shape")
    sequence, d_model = q.shape
    if not 0 < heads <= d_model or d_model % heads:
        raise ValueError("heads must divide d_model")
    if wo.shape != (d_model, d_model):
        raise ValueError("WO must be d_model x d_model")
    d_head = d_model // heads
    qh = q.reshape(sequence, heads, d_head).transpose(1, 0, 2)
    kh = k.reshape(sequence, heads, d_head).transpose(1, 0, 2)
    vh = v.reshape(sequence, heads, d_head).transpose(1, 0, 2)
    scores = qh @ kh.transpose(0, 2, 1) / np.sqrt(d_head)
    probabilities = softmax(scores, axis=-1)
    context = (probabilities @ vh).transpose(1, 0, 2).reshape(sequence, d_model)
    return MHAResult(
        output=context @ wo, q=q, k=k, v=v, scores=scores,
        probabilities=probabilities, context=context,
    )


def mha_fp32(input_x: np.ndarray, weights: TinyMHAWeights, heads: int) -> MHAResult:
    """Reference MHA with standard FP32-like projection arithmetic in float64."""
    x = _validate_input(input_x, np.asarray(weights.wq).shape[0])
    matrices = weights.as_mapping()
    return mha_from_projections(x @ matrices["WQ"], x @ matrices["WK"], x @ matrices["WV"], matrices["WO"], heads)


def ternary_projection_from_matrix(
    matrix: np.ndarray, threshold_ratio: float = 0.7,
) -> QTEAProjection:
    """Create an explicit base-only QTEA-compatible ternary approximation.

    It is a deterministic least-squares ternary baseline, not a replacement for
    QTEA's trained quantizer.  `col_v=1`, `beta=0`, and residual is absent so
    it is also the numerical contract for the first physical ternary macro.
    """
    weight = np.asarray(matrix, dtype=np.float64)
    if weight.ndim != 2 or weight.shape[0] % BLOCK_SIZE:
        raise ValueError("projection matrix must be K x M with K divisible by 32")
    if not np.all(np.isfinite(weight)) or not 0 < threshold_ratio <= 2:
        raise ValueError("matrix must be finite and threshold_ratio must be in (0, 2]")
    k, m = weight.shape
    groups = k // BLOCK_SIZE
    ternary = np.zeros((k, m), dtype=np.int8)
    alpha = np.zeros((m, groups), dtype=np.float64)
    for group in range(groups):
        start, end = group * BLOCK_SIZE, (group + 1) * BLOCK_SIZE
        block = weight[start:end]
        threshold = threshold_ratio * np.mean(np.abs(block), axis=0, keepdims=True)
        codes = np.where(np.abs(block) >= threshold, np.sign(block), 0).astype(np.int8)
        denominator = np.square(codes).sum(axis=0)
        numerator = (block * codes).sum(axis=0)
        alpha[:, group] = np.divide(numerator, denominator, out=np.zeros(m), where=denominator != 0)
        ternary[start:end] = codes
    return QTEAProjection(
        ternary=ternary, alpha=alpha, beta=np.zeros((m, groups)),
        col_v=np.ones(k), residual=None,
    )


def mxfp4_ternary_projection(input_x: np.ndarray, payload: QTEAProjection) -> np.ndarray:
    """Project each token with the frozen integer MXFP4/fixed-point oracle."""
    x = _validate_input(input_x, payload.shape[0])
    return np.stack([fixed_mxfp4_qtea_projection(encode_mxfp4(token), payload).output for token in x])


def mha_mxfp4_ternary(
    input_x: np.ndarray, payloads: Mapping[str, QTEAProjection], heads: int,
) -> MHAResult:
    """MHA where only Q/K/V/O projections use the AutoMX numerical path."""
    if set(payloads) != set(_PROJECTION_NAMES):
        raise ValueError("payloads must contain exactly WQ, WK, WV, and WO")
    q = mxfp4_ternary_projection(input_x, payloads["WQ"])
    k = mxfp4_ternary_projection(input_x, payloads["WK"])
    v = mxfp4_ternary_projection(input_x, payloads["WV"])
    # WO is a projection of the digital attention context, not of X.
    provisional = mha_from_projections(q, k, v, np.eye(q.shape[1]), heads)
    output = mxfp4_ternary_projection(provisional.context, payloads["WO"])
    return MHAResult(
        output=output, q=q, k=k, v=v, scores=provisional.scores,
        probabilities=provisional.probabilities, context=provisional.context,
    )


def error_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    """Numerical metrics reported separately for model and macro stages."""
    ref = np.asarray(reference, dtype=np.float64)
    got = np.asarray(candidate, dtype=np.float64)
    if ref.shape != got.shape:
        raise ValueError("reference and candidate shapes must match")
    delta = got - ref
    rms_reference = float(np.sqrt(np.mean(np.square(ref))))
    dot = float(np.vdot(ref.ravel(), got.ravel()))
    norm_product = float(np.linalg.norm(ref.ravel()) * np.linalg.norm(got.ravel()))
    return {
        "rmse": float(np.sqrt(np.mean(np.square(delta)))),
        "normalized_rmse": float(np.sqrt(np.mean(np.square(delta))) / max(rms_reference, np.finfo(np.float64).eps)),
        "cosine_similarity": dot / max(norm_product, np.finfo(np.float64).eps),
        "max_absolute_error": float(np.max(np.abs(delta))),
    }


def run_stage1(config: Sky130MHAConfig) -> Stage1Result:
    """Generate and evaluate the deterministic Stage-1 tiny-MHA experiment."""
    rng = np.random.default_rng(config.seed)
    input_x = rng.normal(0.0, 0.5, size=(config.sequence_length, config.d_model))
    matrices = [rng.normal(0.0, 0.2, size=(config.d_model, config.d_model)) for _ in _PROJECTION_NAMES]
    weights = TinyMHAWeights(*matrices)
    payloads = {
        name: ternary_projection_from_matrix(matrix, config.ternary_threshold_ratio)
        for name, matrix in weights.as_mapping().items()
    }
    fp32 = mha_fp32(input_x, weights, config.n_heads)
    quantized = mha_mxfp4_ternary(input_x, payloads, config.n_heads)
    return Stage1Result(
        config=config, input_x=input_x, weights=weights, payloads=payloads,
        fp32=fp32, quantized=quantized, metrics=error_metrics(fp32.output, quantized.output),
    )


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_stage1_receipt(result: Stage1Result, directory: str | Path) -> dict[str, object]:
    """Persist raw Stage-1 tensors and a small JSON evidence record."""
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    tensors_path = output / "stage1_mha_tiny.npz"
    json_path = output / "stage1_mha_tiny.json"
    weights = result.weights.as_mapping()
    np.savez_compressed(
        tensors_path,
        input_x=result.input_x,
        **{name: value for name, value in weights.items()},
        fp32_output=result.fp32.output,
        quantized_output=result.quantized.output,
        quantized_q=result.quantized.q,
        quantized_k=result.quantized.k,
        quantized_v=result.quantized.v,
        probabilities=result.quantized.probabilities,
    )
    payload_summary = {
        name: {
            "shape": list(payload.shape),
            "ternary_nonzero": int(np.count_nonzero(payload.ternary)),
            "ternary_total": int(np.asarray(payload.ternary).size),
            "mode": "base_only_col_v_1_beta_0_residual_disabled",
        }
        for name, payload in result.payloads.items()
    }
    receipt: dict[str, object] = {
        "format": "automx-cim-stage1-v1",
        "config": result.config.to_mapping(),
        "config_sha256": result.config.sha256,
        "physical_mode": result.config.physical_mode,
        "projection_quantizer": "deterministic ternary least-squares baseline; not trained QTEA",
        "attention_runtime": "digital QK^T, softmax, A@V",
        "metrics": dict(result.metrics),
        "shapes": {
            "input_x": list(result.input_x.shape),
            "output": list(result.fp32.output.shape),
            "probabilities": list(result.fp32.probabilities.shape),
        },
        "payloads": payload_summary,
        "files": {"tensors": {"path": tensors_path.name, "sha256": _file_sha256(tensors_path)}},
    }
    body = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    json_path.write_text(body, encoding="utf-8")
    return receipt
