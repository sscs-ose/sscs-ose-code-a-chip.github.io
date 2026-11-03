"""--optimize on the 16x16 multiplier driven by a non-uniform workload (see scripts/workload_study.py): does the tool
recognise when glitch-aware placement does not pay for that data?

    python scripts/workload_optimize.py <liberty> dnn_int8      -> data/glitchfix/mul16_dnn_int8/optimize.json
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import glitchscope.optimize as opt  # noqa: E402
import glitchfix_study as gs  # noqa: E402
from workload_study import make_waves  # noqa: E402


def main():
    lib, kind = sys.argv[1], sys.argv[2]
    opt.random_waves = make_waves(kind)
    cfg = dict(gs.CASES["mul16_r"]) if hasattr(gs, "CASES") else None
    gs.run(lib, f"mul16_{kind}", cfg)


if __name__ == "__main__":
    main()
