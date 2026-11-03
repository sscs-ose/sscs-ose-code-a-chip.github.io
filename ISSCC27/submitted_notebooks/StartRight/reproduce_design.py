"""Fresh matched detector sizing comparison with normal-storage controls.
SPDX-License-Identifier: Apache-2.0
"""
import platform,sys
from external_consumer import HERE,run_external,save
from detector_design import choose
from scaling_evidence import audit


def main():
    saved=audit();runs=[];rows=[]
    for scale in [1,saved['summary']['selected_scale']]:
        for history in ['retained','normal','no_dip']:
            run=run_external(command=history!='retained',low_V=1.8 if history=='no_dip' else .9,detector_scale=scale)
            runs.append(dict(scale=scale,history=history,run=run));assert run['status']=='completed'
            expected=[True,True] if history=='retained' else ([False,True] if history=='normal' else [False,False])
            assert [r['observed_pass'] for r in run['cases']]==expected
            if history=='no_dip':assert all(r['minimum_q_final_hold_V']>=1.44 for r in run['cases'])
            sensing=next(r for r in run['cases'] if r['reset_network']=='supply_sensitive')
            rows.append(dict(comparison_id='fresh_tt',supply_V=1.8,scale=scale,history=history,result=sensing))
    selected=choose(rows);assert selected==4
    reductions=[]
    for history in ['retained','normal']:
        a,b=[next(r['result'] for r in rows if r['scale']==s and r['history']==history) for s in [1,4]]
        reductions.append(1-b['eligible_delivered_J']/a['eligible_delivered_J'])
    record=dict(status='passed',python=sys.version.split()[0],platform=platform.platform(),selected_scale=selected,working_work_reductions=reductions,runs=runs,
        scope='Twelve fresh TT acquisitions: RC and sensing in three histories at two declared sensing scales. RC is unchanged and repeated as a control. Energy comparison uses only working matched sensing circuits. The frozen choice is checked, not retuned; no full PVT, optimum or physical-area claim.')
    save(HERE/'results/reproduction/design_short.json',record);print('PASS: fresh finite sizing comparison and storage controls.',flush=True);return record


if __name__=='__main__':main()
