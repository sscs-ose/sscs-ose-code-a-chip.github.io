"""Minimal independent Python baseline for complete, monotone-supply records.

Not a general contract engine. Independent scalar/event code makes comparison
inspectable; exclusions are checked explicitly, not silently called PASS.
Apache-2.0.
"""
import numpy as np


def check(a):
    if a.ndim!=2 or a.shape[1]!=6 or not np.isfinite(a).all():
        raise ValueError('Need six finite waveform columns')
    t=a[:,0]
    if len(t)<2 or t[0]>1e-12 or not np.all(np.diff(t)>0) or np.max(np.diff(t))>2.000001e-6:
        raise ValueError('Baseline needs complete, finely sampled initial history')
    if np.any(np.diff(a[:,1]) < -1e-10) or a[0,1]>=3:
        raise ValueError('Baseline covers monotone startup from below 3 V only')
    def edges(column,level):
        v=a[:,column];out=[]
        for i in range(1,len(t)):
            if v[i-1]<level<=v[i]:
                out.append(t[i-1]+(level-v[i-1])*(t[i]-t[i-1])/(v[i]-v[i-1]))
        return out
    osc=[x for x in edges(2,.9) if x>=.0015]
    por=edges(3,.9);window=[x for x in por if x>=.0015]
    delay=window[0]-osc[0] if window and osc and window[0]>=osc[0] else None
    triggers=edges(1,3.)
    if not triggers: function='NOT_TRIGGERED'
    elif any(triggers[0]<=x<=triggers[0]+.002+1e-12 for x in por): function='PASS'
    elif t[-1]>=triggers[0]+.002-1e-12: function='FAIL'
    else: function='INSUFFICIENT_EVIDENCE'
    return {'measurement':'VALID' if delay is not None else 'INVALID',
            'scalar_spec':'NOT_EVALUATED' if delay is None else ('PASS' if .0005<=delay<=.002 else 'FAIL'),
            'functional':function,'startup_s':delay}
