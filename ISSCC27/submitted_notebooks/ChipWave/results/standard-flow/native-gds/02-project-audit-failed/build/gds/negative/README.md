These GDS files are deliberately damaged negative controls, excluded from release and signoff delivery. The only valid exported design is `../nebula_cpu_npu_top.gds`.

`drc_width.gds` adds a 0.05 um metal1 width violation outside the design. `lvs_missing_gate.gds` deletes poly gate shapes from the instantiated `sky130_fd_sc_hd__inv_1` master. The fixed, unmodified decks must detect both changes; `mutations.json`, report databases and `../checks.json` retain the measured evidence.
