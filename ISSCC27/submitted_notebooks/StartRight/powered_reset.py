"""Observe a reset input while its consumer supply satisfies the declared band.
SPDX-License-Identifier: Apache-2.0
Finite interpolated waveform evidence, not a causal or physical reset proof.
"""
import math
from reset_contract import segment,margins,waveform,Band


def witness(time_s,signals,*,bands,start_s,stop_s,minimum_duration_s):
    if not math.isfinite(minimum_duration_s) or minimum_duration_s<=0:raise ValueError('Positive finite witness duration required')
    t,v=waveform(time_s,signals);t,v=segment(t,v,start_s,stop_s);bounds=margins(v,bands);intervals=[]
    for i in range(len(t)-1):
        lo,hi=0.,1.
        for margin in bounds:
            a,b=margin[i],margin[i+1]
            if a<0 and b<0:lo,hi=1.,0.;break
            if a<0:lo=max(lo,float(-a/(b-a)))
            elif b<0:hi=min(hi,float(a/(a-b)))
        if lo<=hi:
            left=float(t[i]+lo*(t[i+1]-t[i]));right=float(t[i]+hi*(t[i+1]-t[i]))
            if intervals and left<=intervals[-1][1]+1e-14:intervals[-1][1]=max(intervals[-1][1],right)
            else:intervals.append([left,right])
    longest=max((b-a for a,b in intervals),default=0.)
    return dict(observed=longest>=minimum_duration_s,longest_interval_s=longest,intervals_s=intervals,
                scope='A declared input/supply witness over finite samples with linear interpolation. It does not establish a minimum pulse specification, causality, all internal states or silicon behavior.')


def fixtures():
    # The supply crosses 1 at 0.5 s; reset crosses 1 at 1.5 s.
    r=witness([0.,1.,2.],dict(vdd=[0.,2.,2.],reset=[0.,0.,2.]),bands=[Band('vdd',lower=1.),Band('reset',upper=1.)],start_s=0.,stop_s=2.,minimum_duration_s=.9)
    assert r['observed'] and abs(r['longest_interval_s']-1.)<1e-14
    # A low reset while power is absent does not qualify this powered witness.
    r=witness([0.,1.,2.],dict(vdd=[0.,0.,2.],reset=[0.,0.,2.]),bands=[Band('vdd',lower=1.),Band('reset',upper=.5)],start_s=0.,stop_s=2.,minimum_duration_s=.01)
    assert not r['observed']
    return 'Hand-computed crossing interval and unpowered-low negative fixture pass.'
