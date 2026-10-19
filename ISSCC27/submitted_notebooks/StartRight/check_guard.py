"""Check requirement-first selection and missing-data abstention.
SPDX-License-Identifier: Apache-2.0
"""
import copy
from guard_policy import choose
from guard_evidence import policy_evidence

def checks(saved):
    evidence=policy_evidence(saved)
    assert choose(evidence,required=['slow_zero','warm_storage'],anchor='slow_zero')=='original'
    assert choose(evidence,required=['half_depth','short_zero','slow_zero','warm_storage'],anchor='slow_zero')=='digital_guard'
    assert choose(evidence,required=['slow_zero','unmeasured_ringing'],anchor='slow_zero') is None
    cheap=copy.deepcopy(evidence)
    for row in cheap['rows']:
        if row['variant']=='original':row['source_work_delivered_J']=0.
    assert choose(cheap,required=['half_depth','slow_zero'],anchor='slow_zero')=='digital_guard'
    missing=copy.deepcopy(evidence)
    for row in missing['rows']:
        if row['condition']=='slow_zero':row.update(status='unresolved',functional_requirement_met=False)
    assert choose(missing,required=['slow_zero'],anchor='slow_zero') is None
    return dict(limited_choice='original',expanded_choice='digital_guard',missing_history=None,cheap_failure_excluded=True,incomplete_anchor_abstains=True,scope='Software fixtures and post-hoc teaching policies, not circuit acquisitions or optimizer advantage.')
