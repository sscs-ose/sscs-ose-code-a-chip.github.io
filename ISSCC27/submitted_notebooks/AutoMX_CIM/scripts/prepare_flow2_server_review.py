#!/usr/bin/env python3
"""Copy the host sources/docs needed to review the wrapper campaign.

The snapshot is supplemental reading material, never an EDA PASS. Native
parents export their own ZIP; this copies only small source/doc files so no
large mirror is duplicated on a nearly full disk.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

FILES = [
    'README.md', 'CODEX_SERVER_FLOW_HANDOFF.md', 'results/receipts/wrapper_signoff.json',
    'docs/flow2_route_recovery_focus_20261022.xml', 'docs/flow2_postroute_notebook_focus_20261022.xml',
    'docs/flow2_cache_cleanup_20261022.json', 'docs/flow2_obsolete_outputs_cleanup_20261022.json',
    'tests/test_stage7_2p2.py', 'tests/test_wrapper_load_common_mode.py',
    'tests/test_post49_calibration_tt.py', 'tests/test_post49_pvt_smoke.py',
    'tests/test_post49_readiness.py', 'tests/test_stage6_characterization.py',
    'scripts/run_flow2_wrapper_postroute.py', 'scripts/run_flow2_wrapper_loaded_conditioner.py',
    'scripts/prepare_flow2_core_full_drc.py', 'physical/sky130/wrapper_prototype/repair_core_taps.tcl',
    'scripts/run_flow2_core_tap_pex.py', 'scripts/run_flow2_core_tap_transient.py',
    'tests/test_flow2_core_tap_transient.py', 'docs/flow2_core_tap_focus_20261022.xml',
    'docs/flow2_system_regression_20261022_continued.xml',
    'docs/flow2_core_tap_rc_20261022.md',
    'docs/flow2_ground_closure_20261022.md',
    'docs/flow2_identical_outputs_dedup_20261022.json', 'docs/flow2_ground_cleanup_20261022.json',
    'scripts/run_flow2_wrapper_ground_repair.py', 'scripts/flow2_ground_bridge_gds.py',
    'scripts/check_flow2_ground_delta.py', 'scripts/flow2_ground_roi.py',
    'physical/sky130/wrapper_prototype/repair_wrapper_ground.tcl',
    'tests/test_flow2_ground_repair.py', 'tests/test_flow2_antenna_analysis.py',
    'docs/flow2_ground_repair_focus_20261022.xml', 'docs/flow2_ground_lvs_focus_20261022.xml',
    'docs/flow2_ground_pdn_focus_20261022.xml', 'docs/flow2_ground_notebook_focus_20261022.xml',
    'docs/flow2_ground_antenna_focus_20261022.xml',
    'scripts/analyze_flow2_antenna.py', 'tests/test_flow2_antenna_analysis.py',
    'docs/flow2_streamout_core_focus_20261022.xml', 'docs/flow2_streamout_integrity_focus_20261022.xml',
    'docs/flow2_notebook_continued_focus_20261022.xml', 'results/receipts/stage8_preflight.json',
    'tests/test_flow2_core_full_drc.py', 'tests/conftest.py',
    'docs/flow2_system_regression_20261022.xml', 'docs/flow2_execution_ledger.md',
    'scripts/run_flow2_wrapper_physical_recovery.py', 'scripts/flow2_wrapper_run_state.py',
    'scripts/run_flow2_mixed_wrapper_gds.py', 'scripts/prepare_flow2_mixed_wrapper.py',
    'scripts/flow2_split_fanout_odb.py', 'scripts/run_flow2_wrapper_transistor_lvs.py',
    'scripts/run_flow2_analog_server_audit.py', 'scripts/build_flow2_mha_usage_registry.py',
    'scripts/run_flow2_mixed_wrapper.py', 'scripts/flow2_integration_common.py',
    'scripts/flow2_wrapper_physical.py', 'scripts/flow2_wrapper_container_runtime.py',
    'scripts/flow2_wrapper_pdn.py', 'physical/sky130/wrapper_prototype/pdn_mixed_wrapper.tcl',
    'scripts/run_flow2_wrapper_route_recovery.py', 'scripts/flow2_wrapper_route_checkpoint.py',
    'scripts/run_flow2_stage6_tt_prototype.py', 'scripts/run_flow2_adc_intrinsic_pilot.py',
    'scripts/prepare_flow2_server_review.py',
    'AutoMX_CIM_Sky130_MHA.ipynb', 'flow_2.md',
    'docs/CODEX_PROGRESS_20261022.md', 'docs/project_progress_20261021.md',
    'docs/flow2_prototype_interface.md', 'docs/flow2_fast_prototype_20261021.md',
    'docs/flow2_analog_server_audit_20261021.md', 'docs/flow2_analog_server_audit_20261021.json',
    'docs/flow2_mha_usage_registry_20261021.md', 'docs/flow2_mha_usage_registry_20261021.json',
    'docs/flow2_server_wrapper_regression_20261021.xml', 'docs/flow2_server_evidence_regression_20261021.xml',
    'docs/flow2_server_analog_lvs_regression_20261021.xml',
    'results/sky130/flow2_wrapper_integration/drt03_residual_analysis.json',
    'tests/test_flow2_mixed_wrapper.py', 'tests/test_flow2_core_bound_fanout.py',
    'tests/test_flow2_analog_server_audit.py', 'tests/test_flow2_mha_usage_registry.py',
    'tests/test_flow2_adc_intrinsic_pilot.py',
    'tests/test_mha_notebook_story.py', 'tests/test_notebook_stage4_stage5.py',
]
GLOBS = ['tests/test_flow2_wrapper*.py', 'docs/CODEX_PROGRESS_*.md', 'docs/flow2_*regression_2026102*.xml',
         'results/sky130/flow2_wrapper_integration/wrapper_postroute_srv_20261022_01/*',
         'results/sky130/flow2_wrapper_integration/core_full_drc_srv_20261022_02/*.json',
         'results/sky130/flow2_wrapper_integration/core_tap_pex_srv_20261022_01/*summary.json',
         'results/sky130/flow2_wrapper_integration/core_tap_transient_srv_20261022_02/*summary.json',
         'results/sky130/flow2_wrapper_integration/wrapper_preview_srv_20261022_04/*',
         'results/sky130/flow2_wrapper_integration/wrapper_streamout_srv_20261022_04/*',
         'results/sky130/flow2_wrapper_integration/ground_repair_srv_20261022_02/*',
         'build/flow2_wrapper_integration/ground_repair_srv_20261022_02/executed_host_sources/*',
         'build/flow2_wrapper_integration/ground_repair_srv_20261022_02/geometry.json',
         'build/flow2_wrapper_integration/ground_repair_srv_20261022_02/gds_delta.json',
         'build/flow2_wrapper_integration/ground_repair_srv_20261022_02/netgen.log',
         'build/flow2_wrapper_integration/pg_access_srv_20261022_01/early_pdn_probe*',
         'build/flow2_wrapper_integration/server_notebook_validation_20261022/summary_ground_eco.json',
         'build/flow2_wrapper_integration/wrapper_streamout_srv_20261022_04/*.xml',
         'build/flow2_wrapper_integration/wrapper_streamout_srv_20261022_04/*.lib',
         'build/flow2_wrapper_integration/wrapper_streamout_srv_20261022_04/*.tcl',
         'build/flow2_wrapper_integration/wrapper_streamout_srv_20261022_04/executed_host_sources/*',
         'build/flow2_wrapper_integration/server_notebook_validation_20261022/summary_core_tap.json',
         'results/sky130/flow2_wrapper_integration/mixed_wrapper_srv_20261022_04_impl_gds_postroute/*',
         'build/flow2_wrapper_integration/wrapper_loaded_srv_20261022_05/summary.json',
         'build/flow2_wrapper_integration/server_notebook_validation_20261022/summary.json',
         'results/sky130/flow2_wrapper_integration/server_bus_probe/*.json',
         'results/sky130/flow2_wrapper_integration/*_analysis.json',
         'build/flow2_wrapper_integration/server_notebook_validation/*']


def main(root, out):
    files = set(FILES)
    for pattern in GLOBS:
        files.update(p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file())
    manifest = []
    for rel in sorted(files):
        source = root / rel
        if not source.is_file():
            continue
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest.append({'path': rel, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                         'bytes': source.stat().st_size})
    (out / 'source_manifest.json').write_text(json.dumps({
        'format': 'automx-cim-server-review-v1', 'files': manifest,
        'native_receipt_policy': 'Native source identities are immutable; review snapshot is supplemental, not an EDA PASS.'},
        indent=2) + '\n')
    print(len(manifest), 'files', sum(x['bytes'] for x in manifest), 'bytes')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--out', type=Path, default=None)
    a = p.parse_args()
    root = a.root.resolve()
    main(root, (a.out or root / 'build/flow2_wrapper_integration/server_review').resolve())
