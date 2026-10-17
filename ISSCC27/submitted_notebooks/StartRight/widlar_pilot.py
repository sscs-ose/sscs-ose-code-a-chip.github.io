"""Inverse-Widlar pilot based on Wang et al., MWSCAS 2012, Fig. 1.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import json
import numpy as np
from pilot import models,simulate,OUT

STUDY=OUT.parent/'widlar'
STUDY.mkdir(exist_ok=True)

def core(pwidth=12,startup_width=None,broken=False,mirror_width=None,mirror_length=1,n1length=1,nstacklength=1):
    gate='vin' if broken else 'b'
    mirror_width=pwidth if mirror_width is None else mirror_width
    result=f'''XM5 a a vdd vdd sky130_fd_pr__pfet_01v8 w={pwidth} l=1
XM1 a {gate} 0 0 sky130_fd_pr__nfet_01v8 w=4 l={n1length}
XM4 b a vdd vdd sky130_fd_pr__pfet_01v8 w={mirror_width} l={mirror_length}
XM2 b b c 0 sky130_fd_pr__nfet_01v8 w=4 l={nstacklength}
XM3 c c 0 0 sky130_fd_pr__nfet_01v8 w=4 l={nstacklength}
CA a 0 100f
CB b 0 100f
CC c 0 100f
'''
    if startup_width is not None:
        result+=f'XMS a a b 0 sky130_fd_pr__nfet_01v8 w={startup_width} l=1\n'
    return result

def dc_deck(pwidth=12,startup_width=None,corner='tt',step=.002,direction=1,vdd=1.8,temp=27,mirror_width=None,mirror_length=1,n1length=1,nstacklength=1):
    start,end,increment=(0,vdd,step) if direction==1 else (vdd,0,-step)
    return 'Inverse-Widlar gate-cut DC return curve\n'+models(corner)+f'.temp {temp}\nVDD vdd 0 {vdd}\nVIN vin 0 0\n'+core(pwidth,startup_width,True,mirror_width,mirror_length,n1length,nstacklength)+f'''.control
set wr_singlescale
set wr_vecnames
dc VIN {start} {end} {increment}
wrdata return.dat v(b) v(a) v(c) i(VDD) i(VIN)
quit
.endc
.end
'''

def find_roots(data):
    """Return sampled zeros and sign-change candidates, including scan endpoints.

    A finite grid can still miss unsampled tangent roots or close crossings.
    A sampled zero interval has no isolated root interpretation here.
    """
    data=np.asarray(data)
    if data.ndim!=2 or len(data)<2 or data.shape[1]<2 or not np.isfinite(data[:,:2]).all():
        raise ValueError('A finite return curve with at least two points is required.')
    ordered=data[np.argsort(data[:,0])]
    x=ordered[:,0];f=ordered[:,1]-x
    if np.any(np.diff(x)<=0):raise ValueError('Sweep coordinates must be distinct.')
    zeros=np.flatnonzero(f==0)
    if np.any(np.diff(zeros)==1):raise ValueError('Non-isolated sampled zero interval; refine or reformulate the scan.')
    roots=[]
    for k in zeros:
        lo=max(0,k-1);hi=min(len(x)-1,k+1)
        slope=(ordered[hi,1]-ordered[lo,1])/(x[hi]-x[lo])
        roots.append({'vin_V':float(x[k]),'local_return_slope':float(slope),'classification':'candidate stable' if abs(slope)<1 else 'candidate unstable','bracket_V':[float(x[k]),float(x[k])]})
    for k in range(len(x)-1):
        if f[k]*f[k+1]<0:
            root=x[k]-f[k]*(x[k+1]-x[k])/(f[k+1]-f[k])
            slope=(ordered[k+1,1]-ordered[k,1])/(x[k+1]-x[k])
            roots.append({'vin_V':float(root),'local_return_slope':float(slope),'classification':'candidate stable' if abs(slope)<1 else 'candidate unstable','bracket_V':[float(x[k]),float(x[k+1])]})
    return sorted(roots,key=lambda r:r['vin_V'])

if __name__=='__main__':
    results=[]
    for pw in [4,8,12,24]:
        name=f'widlar_dc_p{pw}_no_startup'
        folder=simulate(name,dc_deck(pwidth=pw,step=.002))
        data=np.loadtxt(folder/'return.dat',skiprows=1)
        row={'name':name,'pwidth_um':pw,'roots':find_roots(data),'max_abs_cut_gate_current_A':float(np.max(np.abs(data[:,5])))}
        results.append(row)
        print(json.dumps(row),flush=True)
    (STUDY/'screen.json').write_text(json.dumps(results,indent=2))




def audit_return_case(folder,expected_points=None):
    """Check this gate-cut bench before interpreting its return curve.

    Passing these checks does not prove that every equilibrium was found.
    The gate-current limit assumes the selected zero-DC-gate-leakage models.
    """
    folder=Path(folder)
    reasons=[]
    data=np.loadtxt(folder/'return.dat',skiprows=1)
    if data.ndim!=2 or data.shape[1]!=6 or not np.isfinite(data).all():
        return {'accepted':False,'reasons':['Unexpected or nonfinite data shape']}
    if expected_points is not None and len(data)!=expected_points:
        reasons.append('Incomplete sweep row count')
    if not (np.all(np.diff(data[:,0])>0) or np.all(np.diff(data[:,0])<0)):
        reasons.append('Sweep coordinate is not strictly monotone')
    gate_current=float(abs(data[:,5]).max())
    if gate_current>=1e-18:
        reasons.append('Nonzero cut-gate current violates this unloaded gate-cut bench')
    log=(folder/'ngspice.log').read_text(errors='replace')
    fallback='Transient op started' in log
    if fallback:
        reasons.append('Transient operating-point fallback was used during the DC run')
    if 'Error' in log or 'fatal error' in log.lower():
        reasons.append('Simulator reported an error')
    return {'accepted':not reasons,'reasons':reasons,'points':len(data),'max_abs_cut_gate_current_A':gate_current,'dc_transient_fallback':fallback}
