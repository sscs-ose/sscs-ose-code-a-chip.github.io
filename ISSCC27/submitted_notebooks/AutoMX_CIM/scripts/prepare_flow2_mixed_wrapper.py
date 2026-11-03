#!/usr/bin/env python3
"""Generate a complete three-macro RTL wrapper and its connectivity inventory."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_wrapper_design as d
from scripts import audit_flow2_adc_ip as ip
from scripts import flow2_integration_common as common


def blackbox(cell, ports):
    lines = ["`default_nettype none", "(* blackbox *) module "+cell+" (",
             ",\n".join(f"    {direction} wire {name}" for name, direction in ports), ");", "endmodule", "`default_nettype wire", ""]
    return "\n".join(lines)


def generate(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not output.is_relative_to(root):
        raise ValueError("generated files must stay in checkout")
    output.mkdir(parents=True, exist_ok=True)
    public = ip._lef_pins((root/ip.FILES["lef"]).read_text(encoding="utf-8"))
    core_ports = [(p, "inout" if p in ("VPWR", "VGND") else "output" if p.startswith(("BL", "HP", "HN", "TRACK_")) else "input") for p in d.core.PINS]
    cond_ports = [(p, "inout" if p in ("VPWR", "VGND") else "output" if p in ("AINP", "AINN", "BIAS_MON") else "input") for p in d.COND_PINS]
    adc_ports = [(p, "inout" if p in ("VDD", "VSS") else "output" if p.startswith(("result_out", "conversion_finished")) else "input") for p in public]

    bb = blackbox(d.core.CELL, core_ports)+blackbox(d.COND, cond_ports)
    # OpenSTA links LEF bus members through vector ports. Literal escaped
    # scalar names containing brackets are escaped again by its Verilog
    # reader, leaving all result/config ITerms disconnected (_09).
    buses = ("config_1_in", "config_2_in", "result_out")
    expected = {f"{bus}[{i}]" for bus in buses for i in range(16)}
    actual = {p for p in public if "[" in p}
    if actual != expected:
        raise ValueError("pinned ADC bus contract changed")
    adc_scalar = [(p, dr) for p, dr in adc_ports if "[" not in p]
    bb += blackbox("adc_top", adc_scalar + [
        ("[15:0] config_1_in", "input"),
        ("[15:0] config_2_in", "input"),
        ("[15:0] result_out", "output")])
    ports = """input wire clk_i, rst_ni,
    input wire cfg_valid_i, output wire cfg_ready_o,
    input wire [1:0] cfg_row_i, input wire [3:0] cfg_wpos_i, cfg_wneg_i,
    input wire cal_valid_i, output wire cal_ready_o,
    input wire [8:0] cal_address_i, input wire [11:0] cal_threshold_i,
    output wire calibrated_o,
    input wire eval_valid_i, output wire eval_ready_o,
    input wire signed [19:0] act_x2_i, input wire raw_mode_i,
    output wire result_valid_o, input wire result_ready_i,
    output wire signed [47:0] result_acc_o, output wire [95:0] raw_codes_o,
    output wire result_calibrated_o, fault_o,
    output wire BIAS_MON,
    inout wire VPWR, VGND"""
    lines = ["`default_nettype none", "module "+d.TOP+" (", "    "+ports, ");",
        "wire [15:0] wp, wn, adc_word; wire [3:0] wlp, wln, sel;",
        "wire pre_b, track, adc_rst_n, adc_start, clk_vcm, eoc, eoc_osr;",
        "wire "+", ".join(p for p in d.core.PINS if p.startswith(("BL", "HP", "HN", "TRACK_")))+";",
        "wire AINP, AINN;", "automx_cim_readout_seq seq_i (",
        ",\n".join("."+p+"("+p+")" for p in ("clk_i", "rst_ni", "cfg_valid_i", "cfg_ready_o", "cfg_row_i", "cfg_wpos_i", "cfg_wneg_i",
            "cal_valid_i", "cal_ready_o", "cal_address_i", "cal_threshold_i", "calibrated_o", "eval_valid_i", "eval_ready_o", "act_x2_i",
            "raw_mode_i", "result_valid_o", "result_ready_i", "result_acc_o", "raw_codes_o", "result_calibrated_o", "fault_o"))+",",
        ".weight_pos_o(wp), .weight_neg_o(wn), .wlp_o(wlp), .wln_o(wln), .pre_b_o(pre_b), .track_o(track),",
        ".select_o(sel), .adc_rst_no(adc_rst_n), .adc_start_o(adc_start), .clk_vcm_o(clk_vcm),",
        ".adc_eoc_i(eoc_osr), .adc_word_i(adc_word));"]
    core_map = {p:p for p in d.core.PINS}
    core_map.update(PRE_B="pre_b", TRACK="track")
    for row in range(4):
        for pol in ("P", "N"):
            core_map[f"WL{pol}{row}"]=("wlp" if pol=="P" else "wln")+f"[{row}]"
        for col in range(4):
            core_map[f"WPOS_{row}_{col}"]=f"wp[{4*row+col}]"
            core_map[f"WNEG_{row}_{col}"]=f"wn[{4*row+col}]"
    lines += [d.core.CELL+" core_i ("+", ".join(f".{p}({core_map[p]})" for p in d.core.PINS)+");"]
    cond_map = {p:(f"sel[{p[-1]}]" if p.startswith("SEL") else p) for p in d.COND_PINS}
    lines += [d.COND+" condition_i ("+", ".join(f".{p}({cond_map[p]})" for p in d.COND_PINS)+");"]
    adc_map = dict(zip(public, d.adc_connections(public)))
    mapping = {"VPWR":"VPWR", "VGND":"VGND", "ADC_RST_N":"adc_rst_n", "ADC_START":"adc_start", "CLK_VCM":"clk_vcm",
               "ADC_EOC":"eoc", "ADC_EOC_OSR":"eoc_osr"}
    mapping.update({f"ADC_D{i}":f"adc_word[{i}]" for i in range(16)})
    adc_connections = [f".{p}({mapping.get(adc_map[p],adc_map[p])})" for p, _ in adc_scalar]
    # Config bits are logic constants, not supply wires: native LVS (_03)
    # found 32 VPWR/VGND-tied ADC config ITerms that neither PDN nor router
    # connects. Constants become sky130 conb_1 tie cells (hilomap).
    constants = {"VPWR": "1'b1", "VGND": "1'b0"}
    for bus in buses:
        table = constants if bus.startswith("config_") else mapping
        nodes = [table.get(adc_map[f"{bus}[{i}]"], adc_map[f"{bus}[{i}]"]) for i in reversed(range(16))]
        if bus.startswith("config_") and not set(nodes) <= set(constants.values()):
            raise ValueError("ADC config bits must be logic constants")
        adc_connections.append(f".{bus}({{{', '.join(nodes)}}})")
    lines += ["adc_top adc_i ("+", ".join(adc_connections)+");", "endmodule", "`default_nettype wire", ""]
    files = {"wrapper_blackboxes.sv":bb, d.TOP+".sv":"\n".join(lines), "conditioner.reference.spice":d.schematic()}
    for name, content in files.items():
        path = output/name
        if path.exists() and path.read_text(encoding="utf-8") != content:
            raise FileExistsError("generated wrapper differs; use a new tag: "+str(path))
        if not path.exists():
            path.write_text(content, encoding="utf-8")
    report = {"format":"automx-cim-mixed-wrapper-connectivity-v1", "status":"CONNECTIVITY_PREPARED_NOT_PHYSICAL_PASS",
        "top":d.TOP,"macros":[d.core.CELL,d.COND,"adc_top"],"conditioner_devices":d.expected_conditioner(),
        "body_mapping":{"core.VSUBS":"native core VGND", "nfet.B":"VGND", "pfet.B":"VPWR", "precharge.S":"VPWR", "follower.S":"BUF, distinct from B"},
        "adc_reference":"native ADC switched-capacitor VCM, driven by clk_vcm; startup must be measured",
        "decoder":"304 programmable thresholds; result_calibrated stays false in raw mode",
        "PWM":"12 real standard-cell buffer taps; actual widths require post-route characterization",
        "files":{n:common._sha(output/n) for n in files},
        "pending":["conditioner bias/gain/CM/load", "ADC EOC", "new operating point/calibration/holdout", "composite DRC/LVS/PEX", "wrapper LIB/STA/PVT"]}
    common._save(output/"connectivity.json",report)
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--tag",default="mixed_wrapper_20261020_01")
    a=p.parse_args();common.tag_ok(a.tag)
    print(json.dumps(generate(a.root,a.root/common.BUILD/a.tag/"design"),indent=2))
