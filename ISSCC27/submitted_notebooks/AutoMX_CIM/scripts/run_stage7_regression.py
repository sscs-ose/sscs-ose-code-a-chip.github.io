"""Verilator proof of the base-only 32x8 controller against the Python oracle."""

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
from automx_cim.config import Sky130MHAConfig  # noqa: E402
from automx_cim.fixed_point import fixed_mxfp4_qtea_projection  # noqa: E402
from automx_cim.mxfp4 import MXFP4Block  # noqa: E402
from automx_cim.projection import QTEAProjection  # noqa: E402


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _vectors() -> dict[str, object]:
    acts = np.array([(row % 7) - 3 for row in range(32)], dtype=np.int8)
    weights = np.zeros((32, 8), dtype=np.int8)
    for row in range(32):
        weights[row, row % 8] = 1
        weights[row, (row + 1) % 8] = -1
    alpha_q = np.array([4096 + 128 * col for col in range(8)], dtype=np.int64)
    codes = (np.abs(acts).astype(np.uint8) | (np.where(acts < 0, 8, 0).astype(np.uint8))).reshape(1, 32)
    activation = MXFP4Block(codes, np.array([127], dtype=np.uint8))
    payload = QTEAProjection(ternary=weights, alpha=(alpha_q / 4096).reshape(8, 1),
                             beta=np.zeros((8, 1)), col_v=np.ones(32))
    oracle = fixed_mxfp4_qtea_projection(activation, payload)
    group = [int(v) for v in oracle.group_accumulator[0]]
    return {"activation_x2": acts.astype(int).tolist(), "ternary": weights.astype(int).tolist(),
            "alpha_q12": alpha_q.astype(int).tolist(), "e8m0": 127,
            "group_acc_q24": group, "scaled_acc_q24": [v >> 1 for v in group]}


def _testbench(vectors: dict[str, object]) -> str:
    acts = vectors["activation_x2"]
    weights = vectors["ternary"]
    alpha = vectors["alpha_q12"]
    group = vectors["group_acc_q24"]
    scaled = vectors["scaled_acc_q24"]
    init = [f"    req_scale_e8m0_i = 8'd{int(vectors['e8m0'])};"]
    for row in range(32):
        pos = sum((weights[row][col] == 1) << col for col in range(8))
        neg = sum((weights[row][col] == -1) << col for col in range(8))
        literal = f"-5'sd{-acts[row]}" if acts[row] < 0 else f"5'sd{acts[row]}"
        init.append(f"    weight_pos[{row}]=8'd{pos}; weight_neg[{row}]=8'd{neg}; act[{row}]={literal};")
    def signed_literal(value: int, bits: int) -> str:
        return f"-{bits}'sd{-value}" if value < 0 else f"{bits}'sd{value}"

    init += [f"    alpha[{col}]=16'd{alpha[col]}; expected[{col}]={signed_literal(group[col], 48)}; "
             f"scaled_expected[{col}]={signed_literal(scaled[col], 48)};" for col in range(8)]
    return r'''
`timescale 1ns/1ps
module automx_ternary_cim_4x4 (
    input logic clk_i, rst_ni, cfg_valid_i, output logic cfg_ready_o,
    input logic [1:0] cfg_row_i, input logic [3:0] cfg_wpos_i, cfg_wneg_i,
    input logic eval_valid_i, output logic eval_ready_o,
    input logic signed [19:0] act_x2_i,
    output logic result_valid_o, input logic result_ready_i,
    output logic signed [47:0] result_acc_o,
    inout wire VPWR, VGND
);
    // Behavioral wrapper shim: the exact digital macro model supplies the
    // value, while nine extra cycles exercise a non-combinational sense/ADC
    // handshake. This is not an ADC accuracy or physical timing claim.
    logic model_cfg_ready, model_eval_ready, model_valid;
    logic signed [47:0] model_result;
    logic pending;
    logic [3:0] wait_cycles;
    assign cfg_ready_o = model_cfg_ready && !pending;
    assign eval_ready_o = model_eval_ready && !pending;
    assign result_valid_o = pending && wait_cycles == 0;
    automx_ternary_cim_4x4_model model_i (
        .clk_i, .rst_ni, .cfg_valid_i(cfg_valid_i && !pending),
        .cfg_ready_o(model_cfg_ready), .cfg_row_i,
        .cfg_wpos_i, .cfg_wneg_i, .eval_valid_i(eval_valid_i && !pending),
        .eval_ready_o(model_eval_ready), .act_x2_i,
        .result_valid_o(model_valid), .result_ready_i(!pending),
        .result_acc_o(model_result),
        .VPWR(), .VGND()
    );
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            pending <= 0;
            wait_cycles <= 0;
            result_acc_o <= '0;
        end else if (model_valid && !pending) begin
            result_acc_o <= model_result;
            wait_cycles <= 4'd9;
            pending <= 1;
        end else if (pending && wait_cycles != 0) begin
            wait_cycles <= wait_cycles - 1'b1;
        end else if (result_valid_o && result_ready_i) begin
            pending <= 0;
        end
    end
endmodule

module tb_stage7;
    logic clk_i=0, rst_ni=0;
    always #5 clk_i = ~clk_i;
    logic cfg_valid_i=0, cfg_ready_o;
    logic [4:0] cfg_row_i=0;
    logic [7:0] cfg_wpos_i=0, cfg_wneg_i=0;
    logic cfg_alpha_valid_i=0, cfg_alpha_ready_o;
    logic [2:0] cfg_alpha_col_i=0;
    logic [15:0] cfg_alpha_q_i=0;
    logic req_valid_i=0, req_ready_o;
    logic signed [159:0] req_act_x2_i=0;
    logic [7:0] req_scale_e8m0_i=127;
    logic rsp_valid_o, rsp_ready_i=0;
    logic signed [383:0] rsp_group_acc_q_o, rsp_scaled_acc_q_o;
    logic [7:0] weight_pos [0:31], weight_neg [0:31];
    logic signed [4:0] act [0:31];
    logic [15:0] alpha [0:7];
    logic signed [47:0] expected [0:7], scaled_expected [0:7];
    integer calls=0;

    automx_cim_tile_controller dut (.*);

    always @(posedge clk_i) begin
        if (rst_ni && dut.macro_eval_valid && dut.macro_eval_ready) begin
            if (dut.row_group !== 3'(calls / 2) || dut.col_group !== 1'(calls % 2))
                $fatal(1, "macro schedule mismatch at call %0d", calls);
            calls = calls + 1;
        end
    end

    task automatic write_row(input integer r);
        @(negedge clk_i);
        cfg_valid_i=1; cfg_row_i=5'(r);
        cfg_wpos_i=weight_pos[r]; cfg_wneg_i=weight_neg[r];
        if (!cfg_ready_o) $fatal(1, "weight config not ready");
        @(negedge clk_i); cfg_valid_i=0;
    endtask
    task automatic write_alpha(input integer c);
        @(negedge clk_i);
        cfg_alpha_valid_i=1; cfg_alpha_col_i=3'(c); cfg_alpha_q_i=alpha[c];
        if (!cfg_alpha_ready_o) $fatal(1, "alpha config not ready");
        @(negedge clk_i); cfg_alpha_valid_i=0;
    endtask

    initial begin
__INITIALIZE__
        repeat (2) @(negedge clk_i); rst_ni=1;
        if (req_ready_o) $fatal(1, "request accepted before all config words");
        for (integer r=0; r<32; r=r+1) write_row(r);
        for (integer c=0; c<8; c=c+1) write_alpha(c);
        for (integer r=0; r<32; r=r+1)
            req_act_x2_i[5*r +: 5]=act[r];
        @(negedge clk_i);
        if (!req_ready_o) $fatal(1, "request not ready after config");
        req_valid_i=1;
        @(negedge clk_i); req_valid_i=0;
        for (integer n=0; n<500 && !rsp_valid_o; n=n+1) @(negedge clk_i);
        if (!rsp_valid_o) $fatal(1, "controller timeout");
        if (calls != 16) $fatal(1, "expected 16 macro calls, got %0d", calls);
        for (integer c=0; c<8; c=c+1) begin
            if ($signed(rsp_group_acc_q_o[48*c +: 48]) !== expected[c])
                $fatal(1, "group accumulator mismatch c=%0d got=%0d expected=%0d", c,
                       $signed(rsp_group_acc_q_o[48*c +: 48]), expected[c]);
            if ($signed(rsp_scaled_acc_q_o[48*c +: 48]) !== scaled_expected[c])
                $fatal(1, "scaled accumulator mismatch c=%0d", c);
        end
        repeat (3) @(negedge clk_i);
        if (!rsp_valid_o) $fatal(1, "response not held under backpressure");
        rsp_ready_i=1;
        @(negedge clk_i);
        if (rsp_valid_o) $fatal(1, "response not consumed");
        $display("STAGE7_BASE_ONLY_PASS calls=%0d", calls);
        $finish;
    end
endmodule
'''.replace("__INITIALIZE__", "\n".join(init))


def run(root: Path, timeout_s: int = 180) -> dict[str, object]:
    root = root.resolve()
    receipt_path = root / "results/receipts/stage7_regression.json"
    if receipt_path.is_file():
        receipt_path.unlink()  # old PASS cannot survive a failed rerun
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    if (config.physical_mode, config.logical_rows, config.logical_cols) != ("ternary_base_only", 32, 8):
        raise ValueError("Stage 7 controller currently supports frozen base-only 32x8 configuration")
    manifest_path = root / "results/receipts/mha_tiny_schedule_manifest.json"
    schedule_path = root / "results/receipts/mha_tiny_schedule.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("config_sha256") != config.sha256 or manifest.get("command_count") != 66:
        raise ValueError("Stage-2 schedule/config is missing or stale")
    if manifest.get("files", {}).get("schedule", {}).get("sha256") != _hash(schedule_path):
        raise ValueError("Stage-2 schedule file changed after receipt")
    verilator = shutil.which("verilator")
    if not verilator:
        raise RuntimeError("Verilator is required on the SKY130 server")
    build = root / "build/stage7_regression"
    build.mkdir(parents=True, exist_ok=True)
    vectors = _vectors()
    testbench = build / "tb_stage7.sv"
    testbench.write_text(_testbench(vectors), encoding="utf-8")
    vector_path = build / "vectors.json"
    vector_path.write_text(json.dumps(vectors, indent=2) + "\n", encoding="utf-8")
    sources = [root / "rtl/automx_cim_tile_controller.sv",
               root / "rtl/automx_ternary_cim_4x4_model.sv", testbench]
    provenance_sources = [*sources, root / "scripts/run_stage7_regression.py"]
    command = [verilator, "--binary", "--timing", "-sv", "--top-module", "tb_stage7",
               "--Mdir", str(build / "obj_dir"), *(str(path) for path in sources)]
    compile_result = subprocess.run(command, cwd=build, text=True, capture_output=True, timeout=timeout_s, check=False)
    compile_log = build / "verilator_compile.log"
    compile_log.write_text(compile_result.stdout + compile_result.stderr, encoding="utf-8")
    binary = build / "obj_dir/Vtb_stage7"
    execute_result = None
    if compile_result.returncode == 0:
        execute_result = subprocess.run([str(binary)], cwd=build, text=True, capture_output=True,
                                        timeout=timeout_s, check=False)
    run_log = build / "verilator_run.log"
    run_log.write_text("" if execute_result is None else execute_result.stdout + execute_result.stderr, encoding="utf-8")
    passed = (compile_result.returncode == 0 and execute_result is not None
              and execute_result.returncode == 0 and "STAGE7_BASE_ONLY_PASS calls=16" in execute_result.stdout)
    receipt = {
        "format": "automx-cim-stage7-regression-v1", "status": "PASS" if passed else "FAIL",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(), "mode": "ternary_base_only",
        "config_sha256": config.sha256, "stage2_manifest_sha256": _hash(manifest_path),
        "vectors_sha256": _hash(vector_path),
        "sources": {str(path.relative_to(root)): _hash(path) for path in provenance_sources
                    if path.is_relative_to(root)},
        "macro_invocations": 16 if passed else None,
        "reference": "fixed_mxfp4_qtea_projection group_accumulator; E8M0 Q24 arithmetic shift",
        "simulation_macro": "automx_ternary_cim_4x4_model plus 9-cycle delayed handshake; not physical sense/ADC",
        "compile_log": str(compile_log), "run_log": str(run_log),
        "verilator_returncode": compile_result.returncode,
        "simulation_returncode": None if execute_result is None else execute_result.returncode,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if not passed:
        raise RuntimeError(f"Stage-7 Verilator failed; see {compile_log} and {run_log}")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timeout-s", type=int, default=180)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.timeout_s), indent=2))
