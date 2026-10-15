# Layout

## From the flow to the layout

The flow writes two files from its pick (notebook §9.4). Nothing in them is typed by hand:

* `vga_core_12t.spice` is the LVS reference netlist: subcircuit `vga_core_12t`, pins
  `vdd gnd vin_p vin_n iref vctrl_p vctrl_n v_out`.
* `vga_core_12t_sizes.json` is the same design as data, for the layout generator. For each device it gives the type,
  finger count `nf`, length `L_um`, copies `m` and total width `W_total_um`. Every finger is `finger_width_um` = 5 µm
  wide. The file also holds the bias values and the internal nets that must be labelled.

## The final layout (notebook §13)

| File | What it is |
|:--|:--|
| `vga_core_12t.gds` | The layout, top cell `vga_core_12t`, built by the generator from the two files above |
| `vga_core_12t_placement.txt` | The generator's placement report: units per device, arrays, centroid error of each matched group |
| `generator/gen_vga12t.py` | The parametric gLayout generator (Vrinda Pandey) |
| `generator/verify12t.py`, `generator/prove_signoff.sh` | The author's DRC / LVS / extraction scripts and the sign-off proof, negative controls included |
| `generator/analyze_layout.py` | Parasitics per net, symmetry of matched nets, junction areas, routing-resistance estimate |
| `reports/drc_report.txt`, `reports/lvs_report.txt`, `reports/extract_report.txt`, `reports/*_status.json` | Native sign-off and extraction, in the generator's environment |
| `reports/signoff_proof_native.txt` | Native proof: fingerprints, size check, DRC, LVS, negative controls |
| `reports/container_repro/` | The same sign-off rerun inside IIC-OSIC-TOOLS, with its tool versions (`CONTAINER_ENV.txt`) |
| `reports/vga_core_12t_lvs_extracted.spice` | The netlist extracted for LVS |
| `reports/pex/vga_core_12t_pex.spice` | Parasitic extraction, run natively: every transistor finger as drawn, dummies included, with its junction areas and perimeters, and every parasitic capacitor (C only) |
| `reports/layout_analysis.txt` | Output of `analyze_layout.py` on the extraction |
| `layout_report.json` | The sign-off verdicts the notebook reads (written by `tools/import_signoff.py` from the reports) |
| `layout1/` | The first layout, drawn for an interim sizing. Its extraction feeds §9.3 |

Matching assumed by the flow and built by the generator:
* M2/M3: one 2-D common-centroid array with dummies.
* M1/M4: interdigitated, n-well tied to `vdd`.
* M6–M9: one matched group.
* M5, M10, M11, M12: one array of unit devices, with M10 and M11 on the same centroid (their mismatch moves the
  output DC level).

The reports are as the author's scripts wrote them, except for two edits: absolute paths are shortened to `~/`,
and the native proof's host name is replaced by "native (author machine, gLayout venv)". The fingerprints, verdicts
and counts are unchanged.

## Rerunning

* **Post-layout gate** (ngspice and the SKY130 models): `python tools/postlayout_pick.py --rerun`, about 20
  minutes. It rewrites `cache/postlayout_verify.json`, `cache/postlayout_verify_c1p5.json` and
  `cache/postlayout_equiv_cwire.json`. Without `--rerun` it computes only the caches that are missing.
* **Sign-off verdicts**: `python tools/import_signoff.py` re-reads the reports into `layout_report.json`. It checks
  that the SHA-256 recorded in both proof files matches the committed GDS, netlist and sizes file, and that all six
  negative controls ran and were rejected. The notebook repeats the hash check on every run.
* **DRC, LVS and extraction**: the author's scripts, in IIC-OSIC-TOOLS (or any machine with KLayout, Magic and
  Netgen) with `PDK_ROOT` set:
  * `generator/prove_signoff.sh` writes the proof file. It expects a folder whose `layout/` subfolder holds the GDS,
    netlist and sizes file (set `GL12` to that folder), and it needs `generator/` on `PYTHONPATH`.
  * `generator/verify12t.py` provides `drc`, `lvs` and `extract`.
  * Without `PDK_ROOT`, the KLayout sky130A deck is skipped.
* **Regenerating the GDS**: `generator/gen_vga12t.py --json vga_core_12t_sizes.json --spice vga_core_12t.spice --out
  vga_core_12t.gds`. This needs gLayout, which is not in IIC-OSIC-TOOLS.

`scripts/layout_flow.py` also has a generic DRC/LVS/extraction stage (`run()`). Its LVS does not ignore dummy
transistors, so it is not used for this layout.
