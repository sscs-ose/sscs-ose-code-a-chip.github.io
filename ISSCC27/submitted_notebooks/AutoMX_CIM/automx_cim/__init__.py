"""AutoMX-CIM numerical contract and export helpers.

This package is deliberately independent of PyTorch and the physical flow so
that a Code-a-Chip notebook can run the golden model on a CPU-only install.
"""

from .mxfp4 import MXFP4Block, decode_mxfp4, encode_mxfp4
from .projection import QTEAProjection, from_qtea_payload, mxfp4_qtea_projection
from .qtea_adapter import from_qtea_packed, from_qtea_unpacked, unpack_ternary_base3
from .fixed_point import (
    AutoMXFixedConfig, FixedPointFormat, FixedProjectionResult,
    fixed_mxfp4_qtea_projection,
)
from .golden import projection_ablation
from .export import AutoMXImage, AutoMXVector, export_automx_image, export_automx_vector
from .config import Sky130MHAConfig
from .environment import capture_environment, write_environment_receipt
from .attention import (
    MHAResult, Stage1Result, TinyMHAWeights, error_metrics, mha_fp32,
    mha_mxfp4_ternary, run_stage1, ternary_projection_from_matrix,
    write_stage1_receipt,
)
from .scheduler import TileCommand, build_tiny_mha_schedule, validate_schedule, write_stage2_schedule
from .circuit import (
    E2M1_MAGNITUDES_X2, Stage4Artifact, discover_sky130_model_library,
    generate_stage4_spice,
)
from .spice import parse_measurements, validate_measurements, run_stage4_manifest

__all__ = [
    "MXFP4Block", "decode_mxfp4", "encode_mxfp4",
    "QTEAProjection", "from_qtea_payload", "mxfp4_qtea_projection",
    "from_qtea_packed", "from_qtea_unpacked", "unpack_ternary_base3",
    "AutoMXFixedConfig", "FixedPointFormat", "FixedProjectionResult",
    "fixed_mxfp4_qtea_projection", "projection_ablation",
    "AutoMXImage", "AutoMXVector", "export_automx_image", "export_automx_vector",
    "Sky130MHAConfig", "capture_environment", "write_environment_receipt",
    "TinyMHAWeights", "MHAResult", "Stage1Result", "ternary_projection_from_matrix",
    "mha_fp32", "mha_mxfp4_ternary", "error_metrics", "run_stage1", "write_stage1_receipt",
    "TileCommand", "build_tiny_mha_schedule", "validate_schedule", "write_stage2_schedule",
    "E2M1_MAGNITUDES_X2", "Stage4Artifact", "discover_sky130_model_library",
    "generate_stage4_spice", "parse_measurements", "validate_measurements",
    "run_stage4_manifest",
]
