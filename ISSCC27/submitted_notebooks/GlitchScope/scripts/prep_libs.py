"""Prepare one typical-corner Liberty file per open PDK (decompressed; ASAP7's per-family
files merged into one library) for the multi-PDK study.

    python scripts/prep_libs.py <ORFS checkout> <output dir>
"""
import gzip, re, sys
from pathlib import Path

ORFS, OUT = Path(sys.argv[1]) / "flow/platforms", Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
SOURCES = {
    "gf180mcu_7t_3v3": ["gf180/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_3v30.lib.gz"],
    "sky130hd_1v8": ["sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"],
    "ihp_sg13g2_1v2": ["ihp-sg13g2/lib/sg13g2_stdcell_typ_1p20V_25C.lib"],
    "nangate45_1v1": ["nangate45/lib/NangateOpenCellLibrary_typical.lib"],
    "asap7_rvt_0v7": [f"asap7/lib/NLDM/asap7sc7p5t_{f}_RVT_TT_nldm_{d}.lib{z}" for f, d, z in
                      (("INVBUF", "220122", ".gz"), ("SIMPLE", "211120", ".gz"), ("AO", "211120", ".gz"),
                       ("OA", "211120", ".gz"), ("SEQ", "220123", ""))],
    "gt2n_w31_svt_0v7": ["gt2n/lib/gt2_6t_w31_svt_tt_0p7v25c.lib"],
}


def text(p):
    p = ORFS / p
    if not p.exists() and p.suffix != ".gz" and Path(str(p) + ".gz").exists():
        p = Path(str(p) + ".gz")
    return gzip.open(p, "rt", errors="replace").read() if p.suffix == ".gz" else p.read_text(errors="replace")


for name, files in SOURCES.items():
    texts = [text(f) for f in files]
    if len(texts) == 1:
        merged = texts[0]
    else:   # keep the first library's header, append the cell groups of the others
        first = texts[0].rstrip()
        assert first.endswith("}")
        body = []
        for t in texts[1:]:
            i = t.index("{", re.search(r"\blibrary\s*\(", t).end())
            j = t.rstrip().rindex("}")
            inner = t[i + 1:j]
            k = re.search(r"^\s*cell\s*\(", inner, re.M)
            body.append(inner[k.start():] if k else "")
        merged = first[:-1] + "\n".join(body) + "\n}\n"
    (OUT / f"{name}.lib").write_text(merged)
    print(f"{name:20s} {len(merged) / 1e6:6.1f} MB  cells={len(re.findall(r'^\s*cell\s*\(', merged, re.M))}")
