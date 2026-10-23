"""Frozen schematic reference-supervisor adapter.
SPDX-License-Identifier: Apache-2.0
"""
import json,re
import numpy as np
import reference_devices as source
from reset_contract import Band,accepts,segment,source_work,waveform

def fit():
    data=json.loads((source.OUT/'characterization/results.json').read_text(encoding='utf-8'))
    rows={r['temp_C']:r for r in data['runs'] if r['nominal_current_uA']==1.}
    assert set(rows)==set(source.TEMPERATURES) and all(r['status']=='completed' for r in rows.values())
    cold,hot=rows[-40]['result'],rows[125]['result']
    k=(cold['vbe_unit_V']-hot['vbe_unit_V'])/(hot['delta_V']-cold['delta_V'])
    r1=rows[27]['result']['delta_V']/1e-6
    prediction={str(temp):r['result']['vbe_unit_V']+k*r['result']['delta_V'] for temp,r in rows.items()}
    return dict(nominal_branch_current_A=1e-6,R1_ohm=r1,R2_ohm=r1*k,ratio=k,ideal_bias_sum_prediction_V=prediction,
                characterization_raw_hashes={str(temp):r['raw_sha256'] for temp,r in rows.items()},
                scope='Conventional endpoint slope cancellation fitted from nominal ideal-PTAT-bias PNP characterization. This is development sizing, not an independently tested reference or reset threshold.')

def licensed_blocks():
    text=source.SOURCE.read_text(encoding='utf-8');blocks={}
    for name in ('error_amp','startup_injector'):
        matches=re.findall(r'(?ms)^\.subckt '+name+r'\b.*?^\.ends\s*$',text);assert len(matches)==1
        block=matches[0]
        if name=='startup_injector':
            old='XQS VSS VSS NE sky130_fd_pr__pnp_05v5_W0p68L0p68'
            assert block.count(old)==1
            block=block.replace(old,'XQS VSS VSS NE VSS sky130_fd_pr__pnp_05v5_W0p68L0p68')
        blocks[name]=block+'\n'
    return blocks

def build(temp,startup):
    assert temp in source.TEMPERATURES and isinstance(startup,bool)
    sizing=fit();blocks=licensed_blocks()
    text='Self-biased PNP reference feasibility, licensed amplifier and optional startup\n'+source.model_text(True)
    text+=f'''
.temp {temp}
.option reltol=1e-6 abstol=1e-14 vntol=1e-6 gmin=1e-15 method=gear warn=1
VAVDD vdd 0 PWL(0 0 100u 0 5m 3.3 20m 3.3)
* Same-primitive 1:8 PNP array and ideal resistors are this pilot's core.
R2A vref va {sizing['R2_ohm']:.17g}
R2B vref vb {sizing['R2_ohm']:.17g}
R1 vb eq8 {sizing['R1_ohm']:.17g}
XQ1 0 0 va 0 sky130_fd_pr__pnp_05v5_W3p40L3p40
XQ8 0 0 eq8 0 sky130_fd_pr__pnp_05v5_W3p40L3p40 m=8 mult=8
XMPOUT vref gdrv vdd vdd sky130_fd_pr__pfet_g5v0d10v5 L=2 W=8 nf=1 ad=2.32 as=2.32 pd=16.58 ps=16.58 nrd=0.03625 nrs=0.03625 sa=0 sb=0 sd=0 mult=2 m=2
XMPAMP tail gdrv vdd vdd sky130_fd_pr__pfet_g5v0d10v5 L=2 W=8 nf=1 ad=2.32 as=2.32 pd=16.58 ps=16.58 nrd=0.03625 nrs=0.03625 sa=0 sb=0 sd=0 mult=2 m=2
XAMP vb va gdrv tail vdd 0 error_amp
CLOAD vref 0 10p
'''
    if startup:text+='XSU gdrv vref vdd 0 startup_injector\n'
    text+=blocks['error_amp']+blocks['startup_injector']
    vectors='v(vref) v(vdd) i(VAVDD) v(gdrv) v(va) v(vb) v(eq8) v(tail)'
    text+=f'''
.control
set numdgt=17
set wr_singlescale
set wr_vecnames
tran 1u 20m 0 2u
wrdata reference.dat {vectors}
quit
.endc
.end
'''
    assert not re.search(r'(?im)^\s*\.(ic|nodeset)\b',text) and not re.search(r'(?im)^\s*tran .*\buic\b',text)
    assert not re.search(r'(?im)^\s*[BEGFI]\w+\s',text)
    return text

def measure(d):
    assert d.ndim==2 and d.shape[1]==9 and np.isfinite(d).all()
    t,v=waveform(d[:,0],dict(vref=d[:,1],vdd=d[:,2]))
    assert abs(t[0])<1e-12 and abs(t[-1]-.020)<1e-10
    assert np.max(abs(d[0,[1,2,4,5,6,7,8]]))<1e-5
    assert np.max(abs(d[:,2]-np.interp(t,[0,.0001,.005,.020],[0,0,3.3,3.3])))<1e-6
    _,last=segment(t,v,.019,.020)
    readiness=accepts(t,v,[Band('vref',lower=1.20,upper=1.26),Band('vdd',lower=3.135)],deadline_s=.015,hold_s=.001)
    work=source_work(t,dict(analog=(d[:,2],d[:,3])))
    return dict(reference_contract=readiness,qualified=readiness['pass_contract'],source_work=work,
        final_reference_V=float(d[-1,1]),minimum_reference_final_ms_V=float(np.min(last['vref'])),maximum_reference_final_ms_V=float(np.max(last['vref'])),
        final_core_input_difference_V=float(d[-1,6]-d[-1,5]),
        scope='Reference-only cold start at TT models and declared temperature, ideal resistors and 10 pF load. Actual source amplifier/startup MOS declarations retain their explicit geometry/contact values. No ideal current/reference/comparator or forced state. Readiness is 1.20 to 1.26 V by 15 ms through trace end, including at least 1 ms hold. Not full POR/DFF reset evidence, PVT qualification or silicon behavior.')
