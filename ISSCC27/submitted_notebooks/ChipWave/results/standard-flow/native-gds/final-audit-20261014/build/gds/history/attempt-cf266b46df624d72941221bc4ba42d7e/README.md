# Final GDS export and installed-scope audit

Deliverable: `nebula_cpu_npu_top.gds`. `manifest.json` binds the frozen layout, stream-out, layer map, actual instantiated-master coverage, readability, DRC/LVS and SHA256SUMS. The accepted ODB, netlist, parasitics and PnR reports are read-only and verified before/after export. `negative/` contains deliberately damaged checker controls; those files are excluded from release.

Original export/audit recipe (requires the original native input captures; preserved for provenance, not a reason to rerun completed physical stages):

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

For the captured feedback revision, reuse the completed export/design checks after exact binding instead of restarting them:

```bash
python3 -B build/gds/revalidate_prior.py
/tmp/chipnebula-pinned-tools/bin/klayout -b -r build/gds/reuse_tool_probe.py
python3 -B build/gds/audit_acceptance.py
/tmp/chipnebula-public-repro-user37/bin/python build/gds/check_gates.py
python3 -B build/gds/finalize.py
```

The prior failed audit is retained under `history/attempt-7c5b8dafd74c4a8aa0b22ba361d3a618/`. Native captured root delivery and V2 synthesis resolve their earlier missing-input findings; the historical resource exceedance is a failure, independent evaluator release remains pending, and the owner power/area inventories explicitly report unavailable post-route workload/activity measurements. Direct check outcomes, dependency-qualified acceptance and physical/export versus whole-project verdicts are distinct in the final ledger. The read-only KLayout executable probe qualifies evidence reuse without rerunning any GDS/design check.

The export driver reads the final ODB with the qualified OpenROAD binary at two threads and writes a DEF only under build/gds. The DEF must equal the accepted final DEF byte-for-byte. Installed ORFS def2stream merges frozen library GDS using the preserved technology layer map. KLayout verifies the top, populated cells, actual master multiplicities, all signal/PG port labels, and per-cell geometry identity against the upstream export. The frozen DRC/LVS decks retain their installed four-thread configuration.

Positive DRC must have zero markers. Positive hierarchical LVS must match the real top and extract nonzero MOS devices. An isolated top-level 0.05 um metal1 shape must trigger m1.1; deleting poly gate geometry in the instantiated inverter master must make device LVS mismatch. Exit codes alone are insufficient: the report databases are parsed and asserted.

`project_acceptance.json` and `.md` audit all 48 frozen checks, 443 requirement IDs and 26 required adapters. Mandatory missing/deferred evidence keeps the project verdict failed. `check_gates.py` records both frozen Gate evaluations and asserts that the incomplete project is rejected. GDS readability and installed-scope closure do not constitute formal signoff or tapeout release. No RTL/synthesis/functional rerun is performed; qualified prior functional evidence and unchanged PnR evidence retain their original identities. Formal corner/rule/model gaps are listed in the acceptance report.

For this continuation, the native feedback captures were not recaptured. Their previously authorized immutable Git objects remain available, and `resume_audit.py` archives only the relevant original contract/RTL/synthesis evidence under `evidence/` after checking the recorded SHA256 values. It verifies all current input Git blobs, physical-source hashes and tool/view hashes without rerunning design checks. Historical paths in unchanged adapter or upstream audit records resolve through `resume_validation.json` → `archive`.

```bash
python3 -B build/gds/resume_audit.py
/tmp/chipnebula-public-repro-user37/bin/python build/gds/check_gates.py
python3 -B build/gds/finalize.py
```

The project Gate is expected to reject the honest failed ledger: the historical resource requirement failed, and mandatory independent evaluator-release, final-design workload/power and remaining typed-adapter proofs are incomplete. Run `finalize.py` without redirecting its output into the checksum-covered directory.
