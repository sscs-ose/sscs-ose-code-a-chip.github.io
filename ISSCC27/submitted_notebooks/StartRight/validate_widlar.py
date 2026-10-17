from pathlib import Path
import json
import numpy as np
from pilot import OUT
from widlar_pilot import STUDY,audit_return_case

scans=json.loads((STUDY/'confirmed_return_scans.json').read_text())
checks={}
for a,b in [scans[:2],scans[2:]]:
    forward=np.loadtxt(OUT/a['name']/'return.dat',skiprows=1)
    reverse=np.loadtxt(OUT/b['name']/'return.dat',skiprows=1)[::-1]
    assert audit_return_case(OUT/a['name'],3601)['accepted']
    assert audit_return_case(OUT/b['name'],3601)['accepted']
    assert len(forward)==3601 and len(reverse)==3601
    assert abs(forward[:,5]).max()<1e-18 and abs(reverse[:,5]).max()<1e-18
    delta=float(abs(forward[:,1]-reverse[:,1]).max())
    assert delta<1e-7
    checks[f'gmin_{a["gmin_S"]}_forward_reverse_max_V']=delta
assert [len(x['roots']) for x in scans]==[1,1,3,3]
ops=json.loads((STUDY/'intact_operating_points.json').read_text())
assert len(ops)==3 and max(x['b_error_V'] for x in ops)<1e-6
checks['max_intact_root_error_V']=max(x['b_error_V'] for x in ops)
nums=json.loads((STUDY/'numerical_checks.json').read_text())
assert len(nums)==8
for r in nums:
    assert (r['ready_time_s'] is not None)==(r['startup_width_um'] is not None)
checks['cold_start_numerical_cases_passed']=len(nums)
conds=json.loads((STUDY/'condition_screen.json').read_text())
assert len(conds)==30 and all(x['status']=='complete' for x in conds)
for r in conds:
    d=np.loadtxt(OUT/r['name']/'return.dat',skiprows=1)
    assert audit_return_case(OUT/r['name'],901)['accepted']
    assert len(d)==901 and abs(d[:,5]).max()<1e-18
    if r['startup_width_um'] is not None: assert len(r['roots'])==1
checks['condition_scans_completed']=len(conds)
checks['unassisted_conditions_with_3_candidate_roots']=sum(len(r['roots'])==3 for r in conds if r['startup_width_um'] is None)
checks['startup_conditions_with_1_candidate_root']=sum(len(r['roots'])==1 for r in conds if r['startup_width_um'] is not None)
contact=OUT/'widlar_geometryTrue_gmin1e-12'/'return.dat'
if not contact.exists(): contact=Path(__file__).resolve().parent/'results/fixtures/rejected_contact/return.dat'
if contact.exists():
    audit=audit_return_case(contact.parent)
    assert not audit['accepted']
    checks['invalid_contact_case_correctly_rejected']=audit
    d=np.loadtxt(contact,skiprows=1)
    checks['excluded_contact_trial']={'reason':'DC solver invoked transient operating-point fallback and cut-gate current was nonzero; not accepted as a valid unloaded DC return curve','max_abs_cut_gate_current_A':float(abs(d[:,5]).max())}
checks['scope']='Finite-grid model evidence with explicit junction geometry and default zero NRD/NRS. No global state-exclusion or silicon guarantee.'
(STUDY/'validation.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))

