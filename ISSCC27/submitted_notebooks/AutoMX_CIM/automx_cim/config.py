"""Versioned, dependency-free configuration for the SKY130 tiny-MHA flow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .mxfp4 import BLOCK_SIZE


@dataclass(frozen=True)
class Sky130MHAConfig:
    """Frozen configuration for the first receipt-backed AutoMX demonstrator."""

    name: str = "sky130_mha_tiny"
    pdk: str = "sky130A"
    vdd: float = 1.8
    temperature_c: int = 25
    mx_block_size: int = BLOCK_SIZE
    physical_rows: int = 4
    physical_cols: int = 4
    logical_rows: int = BLOCK_SIZE
    logical_cols: int = 8
    sequence_length: int = 4
    d_model: int = BLOCK_SIZE
    n_heads: int = 2
    d_head: int = 16
    enable_sparse_residual: bool = False
    physical_mode: str = "ternary_base_only"
    seed: int = 2027
    ternary_threshold_ratio: float = 0.7

    def __post_init__(self) -> None:
        if not self.name or any(char.isspace() for char in self.name):
            raise ValueError("name must be a non-empty identifier without whitespace")
        if self.pdk != "sky130A":
            raise ValueError("the first physical flow is fixed to pdk='sky130A'")
        if self.vdd <= 0 or not -100 <= self.temperature_c <= 200:
            raise ValueError("vdd and temperature_c must be physically plausible")
        if self.mx_block_size != BLOCK_SIZE:
            raise ValueError("AutoMX-CIM fixes the MXFP4 block size to 32")
        if self.logical_rows != BLOCK_SIZE or self.d_model != self.logical_rows:
            raise ValueError("tiny-MHA v1 fixes d_model=logical_rows=32")
        if min(self.physical_rows, self.physical_cols, self.logical_cols, self.sequence_length) <= 0:
            raise ValueError("physical/logical dimensions and sequence_length must be positive")
        if self.d_model % self.logical_cols:
            raise ValueError("d_model must be divisible by logical_cols")
        if self.d_model != self.n_heads * self.d_head:
            raise ValueError("d_model must equal n_heads * d_head")
        if self.sequence_length < 2:
            raise ValueError("sequence_length must be at least two to exercise attention")
        if self.physical_mode not in {"ternary_base_only", "qtea_hybrid"}:
            raise ValueError("physical_mode must be ternary_base_only or qtea_hybrid")
        if self.physical_mode == "ternary_base_only" and self.enable_sparse_residual:
            raise ValueError("physical ternary base mode cannot enable a residual inside the macro")
        if not 0 < self.ternary_threshold_ratio <= 2:
            raise ValueError("ternary_threshold_ratio must be in (0, 2]")

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_json(self) -> str:
        return json.dumps(self.to_mapping(), sort_keys=True, separators=(",", ":"))

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Sky130MHAConfig":
        allowed = set(cls.__dataclass_fields__)
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown configuration keys: {sorted(unknown)}")
        return cls(**dict(data))

    @classmethod
    def from_json(cls, path: str | Path) -> "Sky130MHAConfig":
        source = Path(path)
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON configuration: {source}") from error
        if not isinstance(data, dict):
            raise ValueError("configuration JSON must be an object")
        return cls.from_mapping(data)
