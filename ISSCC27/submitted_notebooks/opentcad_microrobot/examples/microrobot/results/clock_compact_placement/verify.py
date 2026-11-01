"""Focused generator compatibility and evidence checks; never simulates."""
import json
from pathlib import Path
import sys

DEST=Path(__file__).resolve().parent
REPO=DEST.parents[3]
sys.path.insert(0,str(DEST))
import run_variant as experiment
from examples.microrobot import clock_layout as layout


def main():
    manifest=json.loads((DEST/'sha256.json').read_text())
    for name,value in manifest.items():assert experiment.sha(DEST/name)==value,name
    devices=layout.physical_source()[1]
    entries=layout.specs(devices)
    assert entries==layout.specs(devices,placement='baseline')
    for placement in ['unknown']:
        try:layout.specs(devices,placement=placement)
        except ValueError:pass
        else:raise AssertionError('Unknown placement accepted')
    pdk=Path('/usr/local/share/pdk/sky130A')
    trailer='\nputs "OPENTCAD_FLOW_DONE"\nquit -noprompt\n'
    for directory,routing in [('contact_escape_v2','baseline'),('stage_local_v1','stage_local')]:
        base=experiment.LOCAL/directory
        assert layout.generate_script(pdk,entries)+trailer==(base/'generate_cells.tcl').read_text()
        pins=json.loads((base/'instance_pins.json').read_text())
        script,tracks=layout.routing_script(entries,pins,routing=routing)
        assert script+trailer==(base/'route_extract.tcl').read_text()
        assert tracks==json.loads((base/'tracks.json').read_text())
    compact=layout.specs(devices,placement='compact_x')
    assert layout.generate_script(pdk,compact)+trailer==(experiment.PHYSICAL/'generate_cells.tcl').read_text()
    pins=json.loads((experiment.PHYSICAL/'instance_pins.json').read_text())
    script,tracks=layout.routing_script(compact,pins,routing='stage_local')
    assert script+trailer==(experiment.PHYSICAL/'route_extract.tcl').read_text()
    experiment.inputs()
    metrics=json.loads((DEST/'metrics.json').read_text())
    for case in metrics['cases'].values():
        assert case['full_completion'] and case['columns']==8 and case['all_finite']
        assert case['first_time_s']==0 and case['actual_stop_s']==.004
        assert case['nondecreasing_time'] and not case['log_abort_markers']
    assert metrics['execution']['simulator_invocations']==1 and metrics['execution']['returncode']==0
    assert (DEST/'clock_layout.py.snapshot').read_bytes()==(REPO/'examples/microrobot/clock_layout.py').read_bytes()
    assert not list(DEST.rglob('clock.dat')) and not list(DEST.rglob('*.pdf'))
    preview=json.loads((DEST/'layout_preview.json').read_text())
    assert preview['paint_extent_um']==metrics['area']['compact_x']['paint_extent_um']
    edges=metrics['cases']['compact_x_25ns']['edges']
    result={'default_and_explicit_baseline_placement_identical':True,
            'default_placement_and_baseline_routing_Tcl_byte_identical_to_historical':True,
            'existing_stage_local_placement_and_routing_Tcl_byte_identical':True,
            'compact_generated_and_routed_Tcl_reproducible':True,'unknown_placement_rejected':True,
            'all_physical_preflight_gates_and_translated_cells_pins_pass':True,
            'canonical_device_signatures_verified_before_simulation':True,
            'full_transients_complete':True,'one_new_simulator_invocation':True,
            'compact_steady_Q_rises':edges['steady_q_rise_count'],
            'sustained_clock_rises_per_Q_period':edges['clock_rises_between_successive_sustained_q_rises'],
            'actual_paint_preview_extent_matches':True,'generator_snapshot_matches':True,
            'previous_manifest_verified':True,'raw_transients_and_PDF_not_exported':True}
    experiment.dump(DEST/'verification.json',result)
    experiment.dump(DEST/'sha256.json',{str(p.relative_to(DEST)):experiment.sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='sha256.json' and '__pycache__' not in p.parts})
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
