# Final GDS export and installed-scope audit

Deliverable: `nebula_cpu_npu_top.gds`. `manifest.json` binds the frozen layout, stream-out, layer map, actual instantiated-master coverage, readability, DRC/LVS and SHA256SUMS. The accepted ODB, netlist, parasitics and PnR reports are read-only and verified before/after export. `negative/` contains deliberately damaged checker controls; those files are excluded from release.

Reproduce in the workspace with the frozen installed tools and views:

```bash
source /tmp/chipnebula-pinned-tools/env.sh
source /opt/rh/gcc-toolset-13/enable
export NUM_CORES=2
export PYTHONDONTWRITEBYTECODE=1
python3 -B build/gds/run_export.py
python3 -B build/gds/audit_acceptance.py
/tmp/chipnebula-public-repro-user37/bin/python build/gds/check_gates.py
python3 -B build/gds/finalize.py
```

The export driver reads the final ODB with the qualified OpenROAD binary at two threads and writes a DEF only under build/gds. The DEF must equal the accepted final DEF byte-for-byte. Installed ORFS def2stream merges frozen library GDS using the preserved technology layer map. KLayout verifies the top, populated cells, actual master multiplicities, all signal/PG port labels, and per-cell geometry identity against the upstream export. The frozen DRC/LVS decks retain their installed four-thread configuration.

Positive DRC must have zero markers. Positive hierarchical LVS must match the real top and extract nonzero MOS devices. An isolated top-level 0.05 um metal1 shape must trigger m1.1; deleting poly gate geometry in the instantiated inverter master must make device LVS mismatch. Exit codes alone are insufficient: the report databases are parsed and asserted.

`project_acceptance.json` and `.md` audit all 48 frozen checks, 443 requirement IDs and 26 required adapters. Mandatory missing/deferred evidence keeps the project verdict failed. `check_gates.py` records both frozen Gate evaluations and asserts that the incomplete project is rejected. GDS readability and installed-scope closure do not constitute formal signoff or tapeout release. No RTL/synthesis/functional rerun is performed; qualified prior functional evidence and unchanged PnR evidence retain their original identities. Formal corner/rule/model gaps are listed in the acceptance report.
