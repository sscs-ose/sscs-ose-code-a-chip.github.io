"""Hand-solvable RC checks and rejection controls for the mechanism lesson.
SPDX-License-Identifier: Apache-2.0
"""
import copy
import numpy as np
from sequence_analysis import ideal_rc
from mechanism_lab import prediction_plan, score_prediction, paired_control


def checks(summary=None, retained=None, commanded=None):
    assert abs(ideal_rc([[0.,0.],[1.,1.]],1.,1.,[1.])[0]-np.exp(-1)) < 1e-12
    assert abs(ideal_rc([[0.,1.],[1.,1.]],1.,1.,[1.])[0]-(1-np.exp(-1))) < 1e-12
    plan=prediction_plan()
    assert len(plan['predictions'])==2 and plan['predictions'][0]['predicted_c_V'] < plan['predictions'][1]['predicted_c_V']
    checked=3
    if summary is not None:
        for p in summary['plan']['predictions']:
            from pathlib import Path
            import json
            folder=Path(summary['output_dir'])/('dip_'+str(p['dip_V']).replace('.','p'))
            record=json.loads((folder/'run.json').read_text())
            record['output_dir']=str(folder)  # Replay extracted evidence, never the author's machine path.
            if record['status']!='completed':continue
            observed=score_prediction(p,record,summary['plan']['node_tolerance_V'])
            expected=next(r for r in summary['outcomes'] if r['dip_V']==p['dip_V'])
            assert {k:v for k,v in observed.items() if k!='record'}=={k:v for k,v in expected.items() if k!='record'}
            wrong=copy.deepcopy(p);wrong['dip_V']+=.01
            try:score_prediction(wrong,record)
            except ValueError:pass
            else:raise AssertionError('Mismatched prediction accepted')
            wrong=copy.deepcopy(p);wrong['predicted_c_V']+=.1
            assert not score_prediction(wrong,record)['node_prediction_met']
            checked+=3
    if retained is not None and commanded is not None:
        paired_control(retained,commanded)
        wrong=copy.deepcopy(commanded);wrong['scenario']['recovery']['rise_s']*=2
        try:paired_control(retained,wrong)
        except ValueError:pass
        else:raise AssertionError('Unmatched supply history accepted')
        checked+=2
    return checked
