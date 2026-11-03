"""CACE postprocess hook for a single, uncollated POR waveform. Apache-2.0.

Returns a finite startup time in seconds or raises ValueError. No zero/NaN
sentinel is emitted. This hook checks waveform prerequisites only; use the
full evidence gate separately for execution/log/scalar/provenance checks.
"""
import numpy as np


def postprocess(results, conditions):
    arrays=[np.asarray(results[k],dtype=float) for k in ('time','osc','por')]
    t,osc,por=arrays
    if t.ndim!=1 or len(t)<2 or any(v.shape!=t.shape for v in arrays):
        raise ValueError('Expected one uncollated time/osc/por trace')
    if not all(np.isfinite(v).all() for v in arrays) or not np.all(np.diff(t)>0):
        raise ValueError('Non-finite data or unordered time')
    stop=float(conditions.get('audit_stop_s',.004))
    start=float(conditions.get('audit_start_s',.0015))
    threshold=float(conditions.get('audit_threshold_v',.9))
    if not all(np.isfinite(v) for v in (stop,start,threshold)) or not 0<=start<stop:
        raise ValueError('Invalid declared window')
    if t[0]>start or t[-1]<stop-1e-12:
        raise ValueError('Incomplete declared time window')
    event=[]
    for label,v in [('osc',osc),('por',por)]:
        i=np.flatnonzero((v[:-1]<threshold)&(v[1:]>=threshold))
        crossings=t[i]+(threshold-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i])
        crossings=crossings[(crossings>=start)&(crossings<=stop)]
        if not len(crossings):raise ValueError('Missing '+label+' rising event in declared window')
        event.append(float(crossings[0]))
    if event[1]<event[0]:raise ValueError('POR precedes oscillator event')
    return {'startup_validated':[event[1]-event[0]]}
