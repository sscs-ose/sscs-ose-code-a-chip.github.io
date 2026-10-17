import json
from pathlib import Path
from loaded_startup import LOAD_STUDY
base=json.loads((LOAD_STUDY/'measured_results.json').read_text())
pvt=json.loads((LOAD_STUDY/'pvt_qualification.json').read_text())['cases']
recovery=json.loads((LOAD_STUDY/'recovery.json').read_text())
heldout=json.loads((LOAD_STUDY/'heldout.json').read_text())['cases']
assert len(pvt)==45 and len(recovery)==12 and len(heldout)==4
assert all(r['meets_contract']==(r['startup_width_um'] is not None) for r in pvt)
assert all(r['meets_contract'] for r in recovery+heldout)
assert all(r['meets_contract']==(r['width_um'] is not None) for r in base['cases'])
summary={'nominal_loaded_cold_cases':len(base['cases']),'nominal_assisted_passes':sum(r['meets_contract'] for r in base['cases']),'pvt_assisted_passes':sum(r['meets_contract'] for r in pvt),'pvt_control_failures':sum(not r['meets_contract'] for r in pvt),'recovery_passes':sum(r['meets_contract'] for r in recovery),'heldout_passes':sum(r['meets_contract'] for r in heldout),'measurement_analytic_error_s':base['analytic_settling_event_error_s'],'max_selected_energy_refinement_change':max(abs(r['energy_relative_change']) for r in base['refined']),'max_selected_readiness_refinement_change':max(abs(r['ready_relative_change']) for r in base['refined']),'scope':'Finite schematic tests with the declared default-zero NRD/NRS model configuration. PVT targets are condition-specific intended operating points, not PVT current accuracy. No mismatch, extraction or silicon claim.'}
(LOAD_STUDY/'validation_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
