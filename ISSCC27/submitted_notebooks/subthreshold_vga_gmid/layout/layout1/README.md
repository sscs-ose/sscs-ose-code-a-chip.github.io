# First layout (10 Oct 2026): the source of the wiring capacitance

This is the first layout of the 12T core, drawn with the team's glayout generator for an **earlier interim sizing**:
`vga_core_12t_sizes.json` here (M1/M4 64 × 5 µm L 2; M2/M3 128 × 5 µm L 8; M6–M9 8 × 5 µm L 2; unit 1 × 5 µm L 4 with
M5 × 11, M10 × 3, M11 × 3, M12 × 1). Those are not the final sizes (`../vga_core_12t_sizes.json`).

Why it is kept: its extraction (`vga_core_12t_pex.spice`, 59 capacitors of which 51 are non-zero, C only) is what the flow feeds back. The
capacitors are added to the first pass's pick, the lumped output capacitance that reproduces their effect is fitted,
and the flow is rerun with it (notebook §9.3, `scripts/wiring.py`, `tools/freeze_pick.py`).

Verification of this layout, as run by its author: DRC 0 violations (KLayout sky130A deck, glayout deck, magic full),
LVS "Circuits match uniquely" with no property errors against `vga_core_12t_ref.spice`, extraction OK. Reports:
`drc_report.txt`, `lvs_report.txt`, `extract_report.txt` and the `*_status.json` files.

Paths in the reports are shortened to `~/` (the author's home directory).
