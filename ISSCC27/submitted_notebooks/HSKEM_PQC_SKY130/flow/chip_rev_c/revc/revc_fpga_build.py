"""Build summary of the rev C FPGA (fpga_revc) in the format of codeachip/results/fpga/maxopt_final_build.json.

Every value is parsed from the Quartus reports of fpga_revc/quartus/output_files and from the rev C board CSV
(hskem_revc/results/board/c3_repeat_100.csv); none is typed in. The SOF itself contains the provisioning key and
is only hashed here.
usage: py revc_fpga_build.py <out.json>
"""
import csv
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
Q = ROOT / "fpga_revc/quartus/output_files"
P = "DE25Nano_TrustEdge"
REF = json.loads((ROOT / "codeachip/results/fpga/maxopt_final_build.json").read_text())

fit = (Q / f"{P}.fit.summary").read_text()
sta = (Q / f"{P}.sta.summary").read_text()
rpt = (Q / f"{P}.sta.rpt").read_text(errors="replace")
ent = (Q / f"{P}.fit.rpt").read_text(errors="replace")


def summary_slack(kind: str) -> float:
    return float(re.search(rf"Type  : {kind} 'CLOCK1_50'\nSlack : (-?[\d.]+)", sta)[1])


def alms_needed(node: str) -> str:
    return re.search(rf"^;\s+\|{node}\|\s+;\s+([\d.]+) \(", ent, re.M)[1]


def entity(node: str) -> dict:
    # one row of "Fitter Resource Utilization by Entity", read by the column names of its header
    head = [c.strip() for c in re.search(r"^; Compilation Hierarchy Node .*$", ent, re.M)[0].split(";")[1:-1]]
    row = [c.strip() for c in re.search(rf"^;\s+\|{node}\|\s+;.*$", ent, re.M)[0].split(";")[1:-1]]
    col = dict(zip(head, row))
    return {"alms_needed": col["ALMs needed [=A-B+C]"].split()[0], "m20k": int(col["M20Ks"]),
            "dsp": int(col["DSP Blocks needed [=A-B]"].split()[0])}


fmax = re.search(r"^; ([\d.]+) MHz\s+; [\d.]+ MHz\s+; CLOCK1_50\s+;[^;]*; (.+?)\s+;", rpt, re.M)
h = hashlib.sha256((Q / f"{P}.sof").read_bytes()).hexdigest()
runs = list(csv.DictReader(open(ROOT / "hskem_revc/results/board/c3_repeat_100.csv")))
dec = sorted({int(r["decaps_cycles"]) for r in runs}); enc = [int(r["encaps_cycles"]) for r in runs]
res = {
    "project": "fpga_revc (copy of fpga_maxopt with the rev C session edits, TRUSTEDGE_REVC)",
    "defines": REF["defines"] + ["REVC"],
    "device": f'{re.search(r"Family : (.+)", fit)[1].strip()} {re.search(r"Device : (\S+)", fit)[1]} (DE25-Nano)',
    "alms": re.search(r"Logic utilization \(in ALMs\) : ([\d,]+ / [\d,]+) \( (\d+) % \)", fit).expand(r"\1 (\2 %)"),
    "dsp_blocks": int(re.search(r"Total DSP Blocks : (\d+)", fit)[1]),
    "ram_blocks": int(re.search(r"Total RAM Blocks : (\d+)", fit)[1]),
    "clock1_50_setup_slack_ns": summary_slack("Setup"),
    "clock1_50_hold_slack_ns": summary_slack("Hold"),
    "fmax_mhz": float(fmax[1]),
    "timing_model": fmax[2].replace(" Model", "") + " (worst case)",
    "sof_sha256": h,
    "sof_note": REF["sof_note"],
    "board_run": (f"revc_c3_repeat.csv: {sum(r['result_pass'] == '1' for r in runs)}/{len(runs)} PASS, decaps "
                  f"{', '.join(f'{d:,}' for d in dec)} cycles, encaps {min(enc):,}-{max(enc):,}"),
    "entities_alms_needed": {
        "kyber_ntt_engine_packed2 (u_shared_ntt)": entity("u_shared_ntt"),
        "K-PKE encryption incl. sampler, products and codec (u_mlkem512_encaps_partial)":
            {"alms_needed": alms_needed("u_mlkem512_encaps_partial")},
        "decapsulation controller (u_mlkem512_decaps_partial)": {"alms_needed": alms_needed("u_mlkem512_decaps_partial")},
        "Keccak sponge (u_shared_mlkem_sponge)": {"alms_needed": alms_needed("u_shared_mlkem_sponge")},
    },
    "entities_source": "Fitter Resource Utilization by Entity, fpga_revc/quartus/output_files/DE25Nano_TrustEdge.fit.rpt",
}
assert res["sof_sha256"].upper().startswith("473E864A") and res["sof_sha256"].upper().endswith("4726DA")
pathlib.Path(sys.argv[1]).write_text(json.dumps(res, indent=2) + "\n")
print(json.dumps({k: v for k, v in res.items() if k not in ("defines", "sof_note")}, indent=1))
