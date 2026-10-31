"""Generate the committed deterministic K=32/M=8 Phase-2 baseline bundle."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from automx_cim import (  # noqa: E402
    QTEAProjection, encode_mxfp4, export_automx_image, export_automx_vector,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "vectors" / "baseline_k32_m8")
    args = parser.parse_args()
    rng = np.random.default_rng(2027)
    k, m = 32, 8
    residual = np.zeros((k, m), dtype=np.float64)
    # Two salient output lanes, exactly one residual in every four K entries.
    residual[0::4, 1] = rng.normal(0.0, 0.08, 8)
    residual[2::4, 6] = rng.normal(0.0, 0.08, 8)
    payload = QTEAProjection(
        ternary=rng.choice([-1, 0, 1], size=(k, m), p=[0.3, 0.4, 0.3]).astype(np.int8),
        alpha=rng.uniform(0.25, 1.25, size=(m, 1)),
        beta=rng.uniform(-0.2, 0.2, size=(m, 1)),
        col_v=rng.uniform(0.5, 1.5, size=k), residual=residual,
    )
    activation = encode_mxfp4(rng.normal(0.0, 1.25, size=k))
    export_automx_image(payload).write(args.output / "weights")
    export_automx_vector(
        activation, payload, vector_id="baseline_k32_m8_seed2027", seed=2027,
    ).write(args.output / "vector")
    print(args.output)


if __name__ == "__main__":
    main()
