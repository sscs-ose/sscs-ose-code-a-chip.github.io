"""Finite detector sizing choices used by the measured design study.
SPDX-License-Identifier: Apache-2.0
"""
import re,math


def validate_scale(scale):
    if isinstance(scale,bool) or scale not in (1,2,4):
        raise ValueError('Detector scale must be one of the declared choices: 1, 2, 4')
    return int(scale)


def scale_detector(text,scale):
    scale=validate_scale(scale)
    for device,length in [('XMNDET',2.),('XMPDET',.5),('XMNDRV',.5)]:
        text,count=re.subn(r'(?m)^('+device+r' .*\bl=)\S+',lambda m:m[1]+format(length*scale,'.17g'),text)
        if count!=1:raise ValueError('Expected one detector transistor: '+device)
    text,count=re.subn(r'(?m)^(RDET det_supply det )(\S+)',lambda m:m[1]+format(float(m[2])*scale,'.17g'),text)
    if count!=1:raise ValueError('Expected one detector resistor')
    return text


def choose(cases):
    """Choose among complete three-history groups; abstain without a working group.

    Input rows contain scale, history and the measured result. A lower source-work
    value never compensates for missing state coverage or failed normal storage.
    This is an ordinary finite constrained search, not a new optimizer.
    """
    if len({r['comparison_id'] for r in cases})!=1 or len({r['supply_V'] for r in cases})!=1:
        raise ValueError('Choose only within one declared matched comparison')
    choices=[]
    for scale in sorted({r['scale'] for r in cases}):
        group=[r for r in cases if r['scale']==scale]
        if len(group)!=3 or {r['history'] for r in group}!={'retained','normal','no_dip'}:continue
        by={r['history']:r['result'] for r in group}
        a,b,n=(by[k] for k in ['retained','normal','no_dip'])
        if not all(r.get('status')=='measured' for r in by.values()):continue
        if not (a['observed_pass'] and a['declared_precondition_verified'] and not a['alternate_state_exercised']):continue
        if not (b['observed_pass'] and b['declared_precondition_verified'] and b['sampled_restoration_observed']):continue
        nominal=next(r['supply_V'] for r in group if r['history']=='no_dip')
        if not (n['declared_precondition_verified'] and n['alternate_state_exercised'] and n['minimum_q_final_hold_V']>=.8*nominal):continue
        work=[r['source_work']['delivered_J'] for r in [a,b]]
        if not all(math.isfinite(w) and w>=0 for w in work):continue
        choices.append((sum(work),scale))
    return min(choices)[1] if choices else None
