"""Readiness and net source work from a sampled loaded startup waveform."""
import numpy as np

def measure_loaded(data,target,deadline,hold=.002,tolerance=.05):
    d=np.asarray(data)
    assert d.ndim==2 and d.shape[1]>=8 and len(d)>1 and np.isfinite(d).all()
    assert target>0 and np.all(np.diff(d[:,0])>0)
    margins=np.column_stack([d[:,7]-target*(1-tolerance),target*(1+tolerance)-d[:,7],d[:,5]-1.7,d[:,6]-.3])
    good=np.all(margins>=0,axis=1)
    outside=np.flatnonzero(~good)
    first=int(outside[-1]+1) if len(outside) else 0
    common={'method':'last entry into the valid band, linearly interpolated between samples; valid through the end','target_output_A':target,'deadline_s':deadline,'hold_s':hold}
    if first>=len(d):return {**common,'ready_time_s':None,'source_energy_to_ready_J':None,'meets_contract':False}
    t=d[:,0];power=-d[:,4]*d[:,5]
    if first==0:ready=float(t[0]);energy=0.0
    else:
        previous=first-1
        negative=margins[previous]<0
        fraction=float(np.max(-margins[previous,negative]/(margins[first,negative]-margins[previous,negative])))
        ready=float(t[previous]+fraction*(t[first]-t[previous]))
        boundary_power=power[previous]+fraction*(power[first]-power[previous])
        energy=float(np.trapezoid(power[:previous+1],t[:previous+1])+.5*(power[previous]+boundary_power)*(ready-t[previous]))
    if t[-1]-ready<hold:return {**common,'ready_time_s':None,'source_energy_to_ready_J':None,'meets_contract':False}
    return {**common,'ready_time_s':ready,'source_energy_to_ready_J':energy,'meets_contract':ready<=deadline,'first_valid_sample_s':float(t[first])}
