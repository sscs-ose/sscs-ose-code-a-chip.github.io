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
| `generator/pex_rc.py` | The author's RC extraction script (Magic `extresist`), separate from the hash-pinned `verify12t.py` |
| `reports/drc_report.txt`, `reports/lvs_report.txt`, `reports/extract_report.txt`, `reports/*_status.json` | Native sign-off and extraction, in the generator's environment |
| `reports/signoff_proof_native.txt` | Native proof: tool versions, fingerprints (layout files and `verify12t.py`), size check, DRC, LVS, negative controls |
| `reports/container_repro/` | The same sign-off rerun inside IIC-OSIC-TOOLS, with its tool versions and image digest (`CONTAINER_ENV.txt`) |
| `reports/vga_core_12t_lvs_extracted.spice` | The netlist extracted for LVS |
| `reports/pex/vga_core_12t_pex.spice` | Parasitic extraction, run natively: every transistor finger as drawn, dummies included, with its junction areas and perimeters, and every parasitic capacitor (C only) |
| `reports/pex/vga_core_12t_pex_rc.spice`, `reports/pex/rc_report.txt` | The extraction with resistance (Magic `extresist`, run natively): the same transistor fingers and capacitance, plus the resistance of every wire, supply and ground meshes included; the report checks the capacitance against the capacitance-only extraction and gives each signal net's resistance and RC pole |
| `reports/layout_analysis.txt` | Output of `analyze_layout.py` on the extraction |
| `reports/antenna/` | Magic `antennacheck` on the flattened GDS, run natively (17 Oct), with its script `demo_antenna.sh`, tool versions, summary and raw logs. A control cell (a gate wired to a large metal plate) must be flagged, so a check that cannot flag anything is detected |
| `reports/extra_drc/` | The official KLayout deck's checks that are off by default (off-grid shapes, floating metal), switched on and run natively (17 Oct) on the GDS, with controls that must be flagged, the script `demo_extra_drc.sh`, tool versions, the report databases (`*.lyrdb`) and logs. This is not an antenna check: no KLayout antenna deck was run |
| `layout_report.json` | The sign-off verdicts the notebook reads (written by `tools/import_signoff.py` from the reports) |
| `layout1/` | The first layout, drawn for an interim sizing. Its extraction feeds §9.3 |

Matching assumed by the flow and built by the generator:
* M2/M3: one 2-D common-centroid array with dummies.
* M1/M4: interdigitated, n-well tied to `vdd`.
* M6–M9: one matched group.
* M5, M10, M11, M12: one array of unit devices, with M10 and M11 on the same centroid (their mismatch moves the
  output DC level).

The reports are as the author's scripts wrote them, except for two edits: absolute paths are shortened to `~/`
(this includes the antenna and extra-DRC logs and report databases, where the author's home directory name is replaced
by `~`), and the native proof's host name is replaced by "native (author machine, gLayout venv)". The fingerprints,
verdicts and counts are unchanged.

**The 44 extraction warnings.** Magic's extraction of the layout prints 44 warnings, and the antenna check does not change
that count (`reports/antenna/verify_demo_antenna/layout.log`: 44 before, 44 after). The layout has 44 dummy transistors,
each with drain, gate and source on one rail, and Magic reports a device with fewer distinct connections than a normal one
as a warning and connects the remainder to that rail (the author reports the message as `device missing 1 terminal`; the
message text itself is not in the committed logs). The committed extracted netlist `reports/pex/vga_core_12t_pex.spice` has
724 transistors, of which 44 have drain, gate and source on one net: 36 NMOS on `gnd` and 8 PMOS on `vdd`. LVS ignores these
shorted devices by design; they are in the extraction used for the post-layout gate and add junction capacitance to the rails.

## Rerunning

* **Post-layout gate** (ngspice and the SKY130 models): `python tools/postlayout_pick.py --rerun`, about 20
  minutes. It rewrites `cache/postlayout_verify.json`, `cache/postlayout_verify_c1p5.json` and
  `cache/postlayout_equiv_cwire.json`. Without `--rerun` it computes only the caches that are missing.
* **Post-layout with resistance**: `python tools/postlayout_pick.py --rc` runs the RC netlist through the same gate at the corners that bound the capacitance-only result and at tt, with ngspice's KLU solver (about an hour per corner). It writes `cache/postlayout_verify_rc.json`.
* **Sign-off verdicts**: `python tools/import_signoff.py` re-reads the reports into `layout_report.json`. It checks
  that the SHA-256 recorded in both proof files matches the committed GDS, netlist, sizes file and `verify12t.py`, and that all six
  negative controls ran and were rejected. The notebook repeats the hash check on every run.
* **Antenna and extra deck checks**: `reports/antenna/demo_antenna.sh` and `reports/extra_drc/demo_extra_drc.sh` (Magic; KLayout
  with the `sky130A_mr.drc` deck and `PDK_ROOT`). Both expect a folder whose `layout/` subfolder holds the GDS (set `GL12`).
  `python tools/import_signoff.py` reads their raw logs and report databases into `layout_report.json` and checks that the
  GDS fingerprint they print is the committed GDS.
* **DRC, LVS and extraction**: the author's scripts, in IIC-OSIC-TOOLS (or any machine with KLayout, Magic and
  Netgen) with `PDK_ROOT` set:
  * `generator/prove_signoff.sh` writes the proof file. It expects a folder whose `layout/` subfolder holds the GDS,
    netlist and sizes file (set `GL12` to that folder), and it needs `generator/` on `PYTHONPATH`.
  * `generator/verify12t.py` provides `drc`, `lvs` and `extract`.
  * Without `PDK_ROOT`, the KLayout sky130A deck is skipped.
  * The script stops in its pre-flight when the Python cannot import gLayout, because the third DRC deck would not run;
    inside IIC-OSIC-TOOLS, where gLayout is not installed, run it with `SKIP_GLAYOUT=1` (the proof then says so).
  * Magic prints `Unknown layer/datatype in boundary, layer=64 type=44` for five shapes when it loads the GDS: its
    sky130A setup does not map the p-well marker layer, so Magic's DRC and extraction do not see them. The layout has
    no deep n-well.
* **Regenerating the GDS**: `generator/gen_vga12t.py --json vga_core_12t_sizes.json --spice vga_core_12t.spice --out
  vga_core_12t.gds`. This needs gLayout, which is not in IIC-OSIC-TOOLS.

`scripts/layout_flow.py` also has a generic DRC/LVS/extraction stage (`run()`). Its LVS does not ignore dummy
transistors, so it is not used for this layout.
