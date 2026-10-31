"""Independent Verilator regression for the ideal two-read 2+2 macro model.

This proves digital sequencing and the unchanged tile handshake only. It
does not model analog conversion errors, establish the 20 ns cycle target,
or replace the Stage-7 baseline/stress receipts required by Stage 8.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automx_cim.config import Sky130MHAConfig  # noqa: E402
from scripts.run_stage7_regression import _testbench, _vectors  # noqa: E402


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _testbench_2p2(vectors: dict[str, object]) -> str:
    """Reuse the frozen oracle, replacing only the ideal macro implementation."""
    bench = _testbench(vectors)
    old = "automx_ternary_cim_4x4_model model_i ("
    marker = '        $display("STAGE7_BASE_ONLY_PASS calls=%0d", calls);'
    if bench.count(old) != 1 or bench.count(marker) != 1:
        raise ValueError("Stage-7 testbench template changed; review 2+2 adapter")
    bench = bench.replace(old, "automx_ternary_cim_4x4_2p2_model model_i (")
    return bench.replace(marker, '''        if (dut.macro_i.model_i.phase_a_count !== 8'd16 ||
            dut.macro_i.model_i.phase_b_count !== 8'd16)
            $fatal(1, "2+2 phase counts mismatch a=%0d b=%0d",
                   dut.macro_i.model_i.phase_a_count,
                   dut.macro_i.model_i.phase_b_count);
        $display("STAGE7_2P2_LOGICAL_PASS phases=16+16 calls=%0d", calls);
''' + marker)


def run(root: str | Path, timeout_s: int = 180) -> dict[str, object]:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    receipt_path = root / "results/receipts/stage7_2p2_regression.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    # A failed rerun must not leave an old PASS at this path.
    receipt_path.write_text(json.dumps({"format": "automx-cim-stage7-2p2-v1",
                                        "status": "BLOCKED_IN_PROGRESS"}, indent=2) + "\n",
                            encoding="utf-8")
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    if (config.physical_mode, config.logical_rows, config.logical_cols) != (
            "ternary_base_only", 32, 8):
        raise ValueError("2+2 logical regression requires frozen base-only 32x8 config")
    manifest_path = root / "results/receipts/mha_tiny_schedule_manifest.json"
    schedule_path = root / "results/receipts/mha_tiny_schedule.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("config_sha256") != config.sha256 or
            manifest.get("command_count") != 66 or
            manifest.get("files", {}).get("schedule", {}).get("sha256") != _hash(schedule_path)):
        raise ValueError("Stage-2 schedule/config is missing or stale")
    verilator = shutil.which("verilator") or shutil.which("verilator_bin")
    if not verilator:
        raise RuntimeError("Verilator is required; run this regression on the SKY130 server")

    build = root / "build/stage7_2p2_regression"
    build.mkdir(parents=True, exist_ok=True)
    vectors = _vectors()
    bench_path = build / "tb_stage7.sv"
    bench_path.write_text(_testbench_2p2(vectors), encoding="utf-8")
    vectors_path = build / "vectors.json"
    vectors_path.write_text(json.dumps(vectors, indent=2) + "\n", encoding="utf-8")
    controller = root / "rtl/automx_cim_tile_controller.sv"
    model = root / "rtl/automx_ternary_cim_4x4_2p2_model.sv"
    sources = [controller, model, bench_path]
    provenance = [*sources, root / "scripts/run_stage7_regression.py",
                  root / "scripts/run_stage7_2p2_regression.py"]
    compile_result = subprocess.run(
        [verilator, "--binary", "--timing", "-sv", "--top-module", "tb_stage7",
         "--Mdir", str(build / "obj_dir"), *(str(path) for path in sources)],
        cwd=build, text=True, capture_output=True, timeout=timeout_s, check=False)
    compile_log = build / "verilator_compile.log"
    compile_log.write_text(compile_result.stdout + compile_result.stderr,
                           encoding="utf-8")
    executable = build / "obj_dir/Vtb_stage7"
    if sys.platform == "win32":
        executable = executable.with_suffix(".exe")
    simulation = None
    if compile_result.returncode == 0:
        simulation = subprocess.run([str(executable)], cwd=build, text=True,
                                    capture_output=True, timeout=timeout_s,
                                    check=False)
    run_log = build / "verilator_run.log"
    run_log.write_text("" if simulation is None else simulation.stdout + simulation.stderr,
                       encoding="utf-8")
    passed = (compile_result.returncode == 0 and simulation is not None and
              simulation.returncode == 0 and
              "STAGE7_2P2_LOGICAL_PASS phases=16+16 calls=16" in simulation.stdout and
              "STAGE7_BASE_ONLY_PASS calls=16" in simulation.stdout)
    receipt = {
        "format": "automx-cim-stage7-2p2-v1",
        "status": "PASS_LOGICAL_2P2" if passed else "FAIL",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "ternary_base_only_two_read_2p2_ideal",
        "config_sha256": config.sha256,
        "stage2_manifest_sha256": _hash(manifest_path),
        "vectors_sha256": _hash(vectors_path),
        "sources": {str(path.relative_to(root)): _hash(path) for path in provenance},
        "macro_invocations": 16 if passed else None,
        "phase_a_reads": 16 if passed else None,
        "phase_b_reads": 16 if passed else None,
        "compile_log": str(compile_log.relative_to(root)),
        "run_log": str(run_log.relative_to(root)),
        "verilator_returncode": compile_result.returncode,
        "simulation_returncode": None if simulation is None else simulation.returncode,
        "scope": "ideal signed 2+2 arithmetic and ready/valid only; precharge/sample states are digital placeholders; no ADC, analog timing, PVT or wrapper physical sign-off",
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if not passed:
        raise RuntimeError(f"2+2 logical Verilator failed; inspect {compile_log} and {run_log}")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timeout-s", type=int, default=180)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.timeout_s), indent=2))
