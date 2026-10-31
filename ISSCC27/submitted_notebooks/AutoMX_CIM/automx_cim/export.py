"""Phase-2 export/import contract for portable AutoMX-CIM memory images."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

from .fixed_point import AutoMXFixedConfig, fixed_mxfp4_qtea_projection
from .mxfp4 import BLOCK_SIZE, MXFP4Block
from .projection import QTEAProjection

IMAGE_FORMAT = "automx-cim-image-v1"
VECTOR_FORMAT = "automx-cim-vector-v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hex_width(bits: int) -> int:
    return (bits + 3) // 4


def _write_memh(path: Path, values: np.ndarray, bits: int) -> None:
    """Write one fixed-width two's-complement hexadecimal word per line."""
    mask = (1 << bits) - 1
    width = _hex_width(bits)
    words = np.asarray(values, dtype=np.int64).reshape(-1)
    path.write_text("".join(f"{int(value) & mask:0{width}x}\n" for value in words), encoding="ascii")


def _read_memh(path: Path, bits: int, signed: bool) -> np.ndarray:
    words = [line.strip() for line in path.read_text(encoding="ascii").splitlines() if line.strip()]
    raw = np.asarray([int(word, 16) for word in words], dtype=np.int64)
    if signed:
        sign = 1 << (bits - 1)
        raw = np.where((raw & sign) != 0, raw - (1 << bits), raw)
    return raw.astype(np.int64)


def _write_plane(path: Path, plane: np.ndarray) -> None:
    """Write K rows; leftmost character is M-1 and rightmost is output 0."""
    matrix = np.asarray(plane, dtype=np.uint8)
    path.write_text(
        "".join("".join(str(int(bit)) for bit in row[::-1]) + "\n" for row in matrix),
        encoding="ascii",
    )


def _read_plane(path: Path, k: int, m: int) -> np.ndarray:
    rows = [line.strip() for line in path.read_text(encoding="ascii").splitlines() if line.strip()]
    if len(rows) != k or any(len(row) != m or set(row) - {"0", "1"} for row in rows):
        raise ValueError(f"malformed binary plane {path.name}")
    return np.asarray([[int(bit) for bit in row[::-1]] for row in rows], dtype=np.uint8)


def _file_record(path: Path, *, kind: str, bits: int, signed: bool,
                 count: int, order: str) -> dict:
    return {
        "kind": kind, "word_bits": bits, "signed": signed, "count": count,
        "order": order, "sha256": _sha256(path),
    }


@dataclass(frozen=True)
class AutoMXImage:
    """Quantized P/N planes and side-memory contents for one projection."""

    wpos: np.ndarray
    wneg: np.ndarray
    alpha_q: np.ndarray
    beta_q: np.ndarray
    col_v_q: np.ndarray
    residual_q: np.ndarray
    manifest: dict

    # Compatibility aliases. Image-v1 values are integer hardware words.
    @property
    def alpha(self) -> np.ndarray:
        return self.alpha_q

    @property
    def beta(self) -> np.ndarray:
        return self.beta_q

    @property
    def col_v(self) -> np.ndarray:
        return self.col_v_q

    @property
    def residual(self) -> np.ndarray:
        return self.residual_q

    def write(self, directory: str | Path) -> dict:
        """Write RTL-readable files and return the final checksummed manifest."""
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        k, m = self.wpos.shape
        groups = k // BLOCK_SIZE
        paths = {name: out / name for name in (
            "wpos.memb", "wneg.memb", "alpha.memh", "beta.memh",
            "col_v.memh", "residual.memh",
        )}
        _write_plane(paths["wpos.memb"], self.wpos)
        _write_plane(paths["wneg.memb"], self.wneg)
        # Group-major makes all M output words for one MX block contiguous.
        _write_memh(paths["alpha.memh"], self.alpha_q.T, 16)
        _write_memh(paths["beta.memh"], self.beta_q.T, 16)
        _write_memh(paths["col_v.memh"], self.col_v_q, 16)
        _write_memh(paths["residual.memh"], self.residual_q, 16)
        files = {
            "wpos.memb": _file_record(paths["wpos.memb"], kind="memb", bits=m,
                                      signed=False, count=k, order="K rows; char M-1..0"),
            "wneg.memb": _file_record(paths["wneg.memb"], kind="memb", bits=m,
                                      signed=False, count=k, order="K rows; char M-1..0"),
            "alpha.memh": _file_record(paths["alpha.memh"], kind="memh", bits=16,
                                       signed=False, count=groups * m, order="group-major [G][M]"),
            "beta.memh": _file_record(paths["beta.memh"], kind="memh", bits=16,
                                      signed=True, count=groups * m, order="group-major [G][M]"),
            "col_v.memh": _file_record(paths["col_v.memh"], kind="memh", bits=16,
                                       signed=False, count=k, order="K"),
            "residual.memh": _file_record(paths["residual.memh"], kind="memh", bits=16,
                                          signed=True, count=k * m, order="row-major [K][M]"),
        }
        manifest = {**self.manifest, "files": files}
        (out / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf8"
        )
        return manifest

    @classmethod
    def read(cls, directory: str | Path, *, verify: bool = True) -> "AutoMXImage":
        """Read an image and optionally verify every recorded digest."""
        root = Path(directory)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf8"))
        if manifest.get("format") != IMAGE_FORMAT:
            raise ValueError("unsupported AutoMX-CIM image format")
        k, m = int(manifest["shape"]["K"]), int(manifest["shape"]["M"])
        groups = k // BLOCK_SIZE
        if verify:
            for name, record in manifest["files"].items():
                if _sha256(root / name) != record["sha256"]:
                    raise ValueError(f"checksum mismatch for {name}")
        wpos = _read_plane(root / "wpos.memb", k, m)
        wneg = _read_plane(root / "wneg.memb", k, m)
        alpha_q = _read_memh(root / "alpha.memh", 16, False).reshape(groups, m).T
        beta_q = _read_memh(root / "beta.memh", 16, True).reshape(groups, m).T
        col_v_q = _read_memh(root / "col_v.memh", 16, False).reshape(k)
        residual_q = _read_memh(root / "residual.memh", 16, True).reshape(k, m)
        if np.any(wpos & wneg):
            raise ValueError("P/N planes overlap")
        return cls(wpos, wneg, alpha_q, beta_q, col_v_q, residual_q, manifest)


@dataclass(frozen=True)
class AutoMXVector:
    """One activation and exact integer group-accumulator expectation."""

    act_x2: np.ndarray
    scale_e8m0: np.ndarray
    expected_group_acc: np.ndarray
    manifest: dict

    def write(self, directory: str | Path) -> dict:
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        paths = {name: out / name for name in (
            "activation_x2.memh", "activation_scale.memh", "expected_group_acc.memh",
        )}
        _write_memh(paths["activation_x2.memh"], self.act_x2, 5)
        _write_memh(paths["activation_scale.memh"], self.scale_e8m0, 8)
        _write_memh(paths["expected_group_acc.memh"], self.expected_group_acc, 48)
        groups, m = self.expected_group_acc.shape
        files = {
            "activation_x2.memh": _file_record(paths["activation_x2.memh"], kind="memh", bits=5,
                                               signed=True, count=self.act_x2.size, order="K"),
            "activation_scale.memh": _file_record(paths["activation_scale.memh"], kind="memh", bits=8,
                                                  signed=False, count=groups, order="G"),
            "expected_group_acc.memh": _file_record(paths["expected_group_acc.memh"], kind="memh", bits=48,
                                                    signed=True, count=groups * m,
                                                    order="group-major [G][M]"),
        }
        manifest = {**self.manifest, "files": files}
        (out / "vector_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf8"
        )
        return manifest


def export_automx_image(
    payload: QTEAProjection,
    config: AutoMXFixedConfig = AutoMXFixedConfig(),
) -> AutoMXImage:
    """Quantize a canonical projection into the Phase-2 hardware image."""
    ternary = np.asarray(payload.ternary, dtype=np.int8)
    k, m = ternary.shape
    residual = np.zeros((k, m)) if payload.residual is None else payload.residual
    wpos = (ternary == 1).astype(np.uint8)
    wneg = (ternary == -1).astype(np.uint8)
    manifest = {
        "format": IMAGE_FORMAT,
        "contract": "automx-fixed-v1",
        "orientation": "KxM (input rows, output columns)",
        "shape": {"K": k, "M": m, "groups": k // BLOCK_SIZE},
        "mxfp4": {"element": "E2M1", "scale": "E8M0", "block_size": BLOCK_SIZE},
        "fixed_point": {
            "alpha": "UQ4.12/16", "col_v": "UQ4.12/16",
            "beta": "Q3.12/16", "residual": "Q3.12/16",
            "group_accumulator": "signed/48, 24 fractional bits",
            "rounding": "nearest-ties-to-even", "overflow": "saturate",
        },
        "weight_encoding": "two disjoint physical P/N planes; 2 bits/weight before side memories",
        "residual_layout": "dense KxM Q3.12 baseline; sparse 1:N compaction is post-baseline",
    }
    return AutoMXImage(
        wpos, wneg,
        config.alpha.quantize(payload.alpha),
        config.beta.quantize(payload.beta),
        config.col_v.quantize(payload.col_v),
        config.residual.quantize(residual),
        manifest,
    )


def export_automx_vector(
    activation: MXFP4Block,
    payload: QTEAProjection,
    config: AutoMXFixedConfig = AutoMXFixedConfig(),
    *, vector_id: str = "vector_0000", seed: int | None = None,
) -> AutoMXVector:
    """Create one exact regression vector from the fixed-point oracle."""
    result = fixed_mxfp4_qtea_projection(activation, payload, config)
    k, m = payload.shape
    manifest = {
        "format": VECTOR_FORMAT, "contract": "automx-fixed-v1", "id": vector_id,
        "seed": seed, "shape": {"K": k, "M": m, "groups": k // BLOCK_SIZE},
        "comparison_point": "signed 48-bit group_acc_q before E8M0 output scaling",
        "accumulator_fraction_bits": result.accumulator_fraction_bits,
    }
    return AutoMXVector(
        activation.signed_magnitude_x2().reshape(-1).astype(np.int64),
        activation.scale_e8m0.reshape(-1).astype(np.uint8),
        result.group_accumulator.astype(np.int64), manifest,
    )
