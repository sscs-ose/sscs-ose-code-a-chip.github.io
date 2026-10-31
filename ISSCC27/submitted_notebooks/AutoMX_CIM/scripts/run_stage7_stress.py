"""Extra Verilator vectors for the base-only controller; not analog sign-off."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.fixed_point import fixed_mxfp4_qtea_projection  # noqa: E402
from automx_cim.mxfp4 import MXFP4Block  # noqa: E402
from automx_cim.projection import QTEAProjection  # noqa: E402
from scripts.run_stage7_regression import _testbench  # noqa: E402


CODE_FOR_X2 = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 6: 5, 8: 6, 12: 7}
MIN_Q24, MAX_Q24 = -(1 << 47), (1 << 47) - 1


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _scale(value: int, code: int) -> int:
    if code < 128:
        return value >> (128 - code)
    return max(MIN_Q24, min(MAX_Q24, value << (code - 128)))


def make_vectors(acts: list[int], weights: list[list[int]],
                 alpha_q12: list[int], scale_e8m0: int) -> dict[str, object]:
    if len(acts) != 32 or any(abs(value) not in CODE_FOR_X2 for value in acts):
        raise ValueError("need 32 signed E2M1 x2 values")
    if len(weights) != 32 or any(len(row) != 8 or any(value not in (-1, 0, 1) for value in row)
                                 for row in weights):
        raise ValueError("need 32x8 ternary weights")
    if len(alpha_q12) != 8 or any(not 0 <= value <= 65535 for value in alpha_q12):
        raise ValueError("need eight unsigned Q12 alpha words")
    if not 0 <= scale_e8m0 <= 255:
        raise ValueError("E8M0 scale must be one byte")
    codes = np.array([CODE_FOR_X2[abs(value)] | (8 if value < 0 else 0)
                      for value in acts], dtype=np.uint8).reshape(1, 32)
    activation = MXFP4Block(codes, np.array([scale_e8m0], dtype=np.uint8))
    payload = QTEAProjection(ternary=np.array(weights, dtype=np.int8),
                             alpha=(np.array(alpha_q12) / 4096).reshape(8, 1),
                             beta=np.zeros((8, 1)), col_v=np.ones(32))
    oracle = fixed_mxfp4_qtea_projection(activation, payload)
    group = [int(value) for value in oracle.group_accumulator[0]]
    return {"activation_x2": acts, "ternary": weights, "alpha_q12": alpha_q12,
            "e8m0": scale_e8m0, "group_acc_q24": group,
            "scaled_acc_q24": [_scale(value, scale_e8m0) for value in group]}


def scenarios() -> dict[str, dict[str, object]]:
    weight = [[1 if (row + col) % 4 == 0 else -1 if (row + col) % 4 == 1 else 0
               for col in range(8)] for row in range(32)]
    extreme_weight = [[1 if col % 2 == 0 else -1 for col in range(8)]
                      for _ in range(32)]
    cancel_weight = [[1 if col < 4 else (-1 if row % 2 == 0 else 1)
                      for col in range(8)] for row in range(32)]
    codes = (0, 1, 2, 3, 4, 6, 8, 12)
    varied_act = [codes[row % 8] * (-1 if row % 3 == 0 else 1) for row in range(32)]
    alpha = [4096 + 256 * col for col in range(8)]
    return {
        "zero_low_scale": make_vectors([0] * 32, weight, alpha, 0),
        "extreme_high_scale": make_vectors([12] * 32, extreme_weight, [65535] * 8, 255),
        "signed_cancellation": make_vectors([12 if row % 2 == 0 else -12 for row in range(32)],
                                             cancel_weight, alpha, 128),
        "mixed_codes": make_vectors(varied_act, weight, alpha, 126),
    }


def run(root: Path, timeout_s: int = 180) -> dict[str, object]:
    root = root.resolve()
    target = root / "results/receipts/stage7_stress.json"
    if target.is_file():
        target.unlink()  # never retain a stale PASS after a failed rerun
    baseline_path = root / "results/receipts/stage7_regression.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("status") != "PASS":
        raise ValueError("Stage-7 base-only baseline regression must PASS first")
    for relative, digest in baseline.get("sources", {}).items():
        source = (root / relative).resolve()
        if not source.is_relative_to(root) or not source.is_file() or _digest(source) != digest:
            raise ValueError(f"Stage-7 baseline source changed: {relative}")
    verilator = shutil.which("verilator")
    if not verilator:
        raise RuntimeError("Verilator is required for Stage-7 stress regression")
    sources = [root / "rtl/automx_cim_tile_controller.sv",
               root / "rtl/automx_ternary_cim_4x4_model.sv"]
    build = root / "build/stage7_stress"
    results = {}
    for name, vectors in scenarios().items():
        folder = build / name
        folder.mkdir(parents=True, exist_ok=True)
        testbench = folder / "tb_stage7.sv"
        testbench.write_text(_testbench(vectors), encoding="utf-8")
        vector_path = folder / "vectors.json"
        vector_path.write_text(json.dumps(vectors, indent=2) + "\n", encoding="utf-8")
        command = [verilator, "--binary", "--timing", "-sv", "--top-module", "tb_stage7",
                   "--Mdir", str(folder / "obj_dir"), *(str(path) for path in sources), str(testbench)]
        compiled = subprocess.run(command, cwd=folder, text=True, capture_output=True,
                                  timeout=timeout_s, check=False)
        compile_log = folder / "verilator_compile.log"
        compile_log.write_text(compiled.stdout + compiled.stderr, encoding="utf-8")
        executed = None
        if compiled.returncode == 0:
            executed = subprocess.run([str(folder / "obj_dir/Vtb_stage7")], cwd=folder,
                                      text=True, capture_output=True, timeout=timeout_s, check=False)
        run_log = folder / "verilator_run.log"
        run_log.write_text("" if executed is None else executed.stdout + executed.stderr,
                           encoding="utf-8")
        passed = (compiled.returncode == 0 and executed is not None and executed.returncode == 0
                  and "STAGE7_BASE_ONLY_PASS calls=16" in executed.stdout)
        results[name] = {"status": "PASS" if passed else "FAIL", "compile_returncode": compiled.returncode,
                         "run_returncode": None if executed is None else executed.returncode,
                         "vectors_sha256": _digest(vector_path), "testbench_sha256": _digest(testbench),
                         "compile_log": str(compile_log.relative_to(root)),
                         "run_log": str(run_log.relative_to(root))}
        if not passed:
            break
    receipt = {"format": "automx-cim-stage7-stress-v1",
               "status": "PASS" if len(results) == len(scenarios()) and all(item["status"] == "PASS" for item in results.values()) else "FAIL",
               "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "baseline_receipt_sha256": _digest(baseline_path),
               "sources": {str(path.relative_to(root)): _digest(path)
                           for path in (*sources, root / "scripts/run_stage7_regression.py",
                                        root / "scripts/run_stage7_stress.py")},
               "scenario_count": len(scenarios()), "scenarios": results,
               "scope": "four independent base-only vectors; still no full-MHA RTL or analog ADC proof"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if receipt["status"] != "PASS":
        raise RuntimeError(f"Stage-7 stress failed; inspect logs under {build}")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timeout-s", type=int, default=180)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.timeout_s), indent=2))
