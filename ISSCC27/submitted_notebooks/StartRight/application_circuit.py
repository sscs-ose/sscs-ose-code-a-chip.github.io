"""Declared intact-circuit storage and temperature application histories.
SPDX-License-Identifier: Apache-2.0
"""
import math,re
import numpy as np
from guard_circuit import generate,generate_condition
from por_circuit import measure
from reset_contract import waveform,segment
CONDITIONS={'slow_trough':dict(temp_C=27,kind='trough'),'triangle':dict(temp_C=27,kind='triangle'),'warm_trough':dict(temp_C=85,kind='trough')}
HISTORIES=tuple(CONDITIONS)+('cold_storage','hot_shallow_reset')
def supply(kind):
    points=[[0.,0.],[.0003,0.],[.0053,1.8],[.020,1.8],[.025,1.8]]
    if kind=='trough':points += [[.0251,1.62],[.0261,1.62],[.0262,1.8]]
    elif kind=='triangle':
        for i in range(4):
            t=.025+i*.001;points += [[t+.00025,1.62],[t+.00075,1.98],[t+.001,1.8]]
    else:raise ValueError(kind)
    return points+[[.048001,1.8]]

def _ripple(condition,variant,max_step=2e-6):
    text,args=generate('none',True,variant,max_step);vp=supply(CONDITIONS[condition]['kind']);args[1]=vp
    pwl=' '.join(f'{t:.17g} {v:.17g}' for t,v in vp)
    text,n=re.subn(r'(?m)^VDVDD .*$', 'VDVDD dvdd 0 PWL('+pwl+')',text);assert n==1
    text,n=re.subn(r'(?m)^\.temp 27$', '.temp '+str(CONDITIONS[condition]['temp_C']),text);assert n==1
    return text,args

def _storage(d,args):
    reference=measure(d[:,:16],*args,True)
    t,v=waveform(d[:,0],dict(q=d[:,1],reset=d[:,2],vdd=d[:,3],avdd=d[:,11]))
    ts,s=segment(t,v,.02102501,float(t[-1]))
    supply_ok=bool(np.min(s['vdd'])>=1.62-1e-6 and np.max(s['vdd'])<=1.98+1e-6 and np.min(s['avdd'])>=3.135)
    storage=bool(np.min(s['q'])>=1.44)
    inactive=bool(np.min(s['reset']-.8*s['vdd'])>=0)
    qualified=bool(reference['events'][0]['pass_contract'] and reference['declared_precondition_verified'] and supply_ok and storage and inactive)
    return dict(reference=reference,normal_storage_pass=storage,reset_inactive_pass=inactive,supply_in_declared_band=supply_ok,qualified=qualified,
                minimum_q_V=float(np.min(s['q'])),minimum_reset_V=float(np.min(s['reset'])),minimum_reset_margin_V=float(np.min(s['reset']-.8*s['vdd'])),final_q_V=float(s['q'][-1]),
                scope='Post-write Q >= 1.44 V and reset-bar >= 0.8*DVDD throughout sampled piecewise-linear observation. Allowed application supply band is 1.62 to 1.98 V, not an upstream guarantee or physical qualification. A release-band violation and actual state loss are separate outcomes.')


def generate_application(history,variant,max_step=2e-6):
    if history not in HISTORIES or variant not in ('original','digital_guard'):
        raise ValueError('Declare a supported history and variant')
    if isinstance(max_step,bool) or not math.isfinite(max_step) or max_step<=0:
        raise ValueError('A positive finite maximum step is required')
    if history=='hot_shallow_reset':
        text,args=generate_condition('shallow_depth',variant,max_step)
        return text.replace('.temp 27\n','.temp 125\n'),args
    text,args=_ripple('slow_trough' if history=='cold_storage' else history,variant,max_step)
    if history=='cold_storage':text=text.replace('.temp 27\n','.temp -40\n')
    return text,args

def measure_application(data,args,history):
    if history not in HISTORIES:raise ValueError('Unknown application history')
    if history=='hot_shallow_reset':
        reference=measure(data[:,:16],*args,True)
        result=dict(reference=reference,qualified=bool(reference['events'][0]['pass_contract'] and reference['declared_precondition_verified'] and reference['observed_pass']))
        functional=reference['observed_pass']
    else:
        result=_storage(data,args)
        functional=result['normal_storage_pass'] and result['reset_inactive_pass'] and result['supply_in_declared_band']
    reference=result['reference']
    if not reference['events'][0]['pass_contract']:diagnosis='not_exercised_cold_start'
    elif not reference['declared_precondition_verified']:diagnosis='not_exercised_prior_state'
    elif functional:diagnosis='requirement_met'
    else:diagnosis='functional_requirement_missed'
    result.update(history=history,diagnosis=diagnosis,functional_requirement_met=bool(functional),
        scope='Declared intact schematic application. A valid cold start and ordinary prior-state write are required before interpreting storage or reset action. Whole post-write storage and reset-bar margins are separate. Finite samples with linear interpolation; no physical or continuous-domain qualification.')
    assert result['qualified']==(diagnosis=='requirement_met')
    return result
