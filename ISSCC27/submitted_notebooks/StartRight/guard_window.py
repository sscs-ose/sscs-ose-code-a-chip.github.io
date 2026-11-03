"""Isolated frozen-guard DC characterization, not a reset-action proof.
SPDX-License-Identifier: Apache-2.0
"""
import numpy as np
import pilot
from guard_circuit import GUARD
CORNERS=('tt','ff','ss','sf','fs')
TEMPERATURES=(-40,27,85,125)
RESISTANCES_MOHM=(5,10,20,40,80,160)
def _frozen(corner, temp, direction):
    assert corner in CORNERS and temp in TEMPERATURES and direction in ('up', 'down')
    sweep = '0.4 1.98 0.001' if direction == 'up' else '1.98 0.4 -0.001'
    return 'Frozen digital guard, POR input held high for isolated DC characterization\n' + pilot.models(corner) + f'''
.temp {temp}
.option reltol=1e-6 abstol=1e-14 vntol=1e-6 gmin=1e-15 warn=1
VDVDD dvdd 0 1.8
* POR release input is an ideal wire to DVDD in this isolated test.
RRELEASE porb_l dvdd 1u
''' + GUARD + f'''
.control
set numdgt=17
set wr_singlescale
set wr_vecnames
dc VDVDD {sweep}
wrdata transfer.dat v(dvdd) v(combined_reset) v(dbsense) v(dbok) i(VDVDD)
quit
.endc
.end
'''

def measure_window(d):
    assert d.ndim == 2 and d.shape == (1581, 6) and np.isfinite(d).all()
    # Normalize direction for comparison. No hysteresis assumption enters the verdict.
    if d[0, 1] > d[-1, 1]:
        d = d[::-1]
    v, reset = d[:, 1], d[:, 2]
    assert np.all(np.diff(v) > 0) and abs(v[0]-.4) < 1e-8 and abs(v[-1]-1.98) < 1e-8
    assert np.max(abs(d[:, 0]-v)) < 1e-8
    low = reset-.2*v
    high = reset-.8*v
    def crossings(margin):
        out = []
        for i in range(len(v)-1):
            if margin[i] == 0:
                out.append(float(v[i]))
            elif margin[i]*margin[i+1] < 0:
                out.append(float(v[i]+(v[i+1]-v[i])*(-margin[i])/(margin[i+1]-margin[i])))
        if margin[-1] == 0:
            out.append(float(v[-1]))
        return out
    return dict(low_band_crossings_V=crossings(low), high_band_crossings_V=crossings(high),
        asserted_at_1p35=bool(np.interp(1.35,v,low)<=0),
        released_at_1p62=bool(np.interp(1.62,v,high)>=0),
        asserted_through_1p35=bool(np.all(low[v<=1.35+1e-9]<=0)),
        released_from_1p62=bool(np.all(high[v>=1.62-1e-9]>=0)),
        reset_at_1p35_V=float(np.interp(1.35,v,reset)), reset_at_1p62_V=float(np.interp(1.62,v,reset)),
        supply_current_at_1p8_A=float(-np.interp(1.8,v,d[:,5])),
        scope='Isolated steady-state guard with POR input held high. Logic teaching bands are 20% asserted and 80% released. Neither a dynamic reset proof nor full POR/DFF process qualification.')


def generate_window(corner='tt',temp_C=27,direction='up',resistance_Mohm=40):
    if corner not in CORNERS or temp_C not in TEMPERATURES or direction not in ('up','down'):
        raise ValueError('Declare a supported corner, temperature and sweep direction')
    if isinstance(resistance_Mohm,bool) or resistance_Mohm not in RESISTANCES_MOHM:
        raise ValueError('Declare one of the finite resistor choices')
    text=_frozen(corner,temp_C,direction)
    assert text.count('RDB dvdd dbsense 40meg\n')==1
    return text.replace('RDB dvdd dbsense 40meg\n',f'RDB dvdd dbsense {resistance_Mohm}meg\n')

def crossing_brackets(data):
    d=np.asarray(data)
    measure_window(d)
    if d[0,1]>d[-1,1]:d=d[::-1]
    v=d[:,1];result={}
    for name,fraction in [('low',.2),('high',.8)]:
        margin=d[:,2]-fraction*v
        result[name]=[[float(v[i]),float(v[i+1])] for i in range(len(v)-1) if margin[i]*margin[i+1]<0 or margin[i]==0]
    return result

def crossing_brackets(data):
    d=np.asarray(data)
    measure_window(d)
    if d[0,1]>d[-1,1]:d=d[::-1]
    v=d[:,1];result={}
    for name,fraction in [('low',.2),('high',.8)]:
        margin=d[:,2]-fraction*v
        result[name]=[[float(v[i]),float(v[i+1])] for i in range(len(v)-1) if margin[i]*margin[i+1]<0 or margin[i]==0]
    return result
