"""Frozen schematic reference-supervisor adapter.
SPDX-License-Identifier: Apache-2.0
"""
import math,re
import numpy as np
import reference_loop as bg
from por_circuit import generate as por_generate,measure
from guard_circuit import generate as guard_generate,generate_condition
from application_circuit import supply
from reset_contract import waveform,segment
source=bg.source
CASES={'cold_storage':(-40,'none'),'cold_shallow':(-40,'shallow_depth'),
       'nominal_storage':(27,'none'),'nominal_shallow':(27,'shallow_depth'),
       'hot_storage':(125,'none'),'hot_shallow':(125,'shallow_depth'),
       'nominal_analog':(27,'analog')}
VARIANTS=('original','digital_guard','reference_supervisor')

def pnp_models():
    # Exact nominal values from the pinned nonfet file. Do not overwrite the
    # published POR's unrelated parameter declarations in the control.
    original=source.NONFET.read_text(encoding='utf-8');text=''
    names=['dkispp','dkbfpp','dknfpp','dkispp5x','dkbfpp5x','dknfpp5x','dkisepp5x']
    names += ['sky130_fd_pr__model__parasitic__diode_ps2nw__'+kind+'_mult' for kind in ('ajunction','pjunction')]
    for name in names:
        values={m[1] for m in re.finditer(r'(?<!\w)'+name+r'\s*=\s*([^\s$]+)',original)}
        assert len(values)==1,(name,values)
        text+=f'.param {name}={next(iter(values))}\n'
    for size in ('W0p68L0p68','W3p40L3p40'):
        text+=f'.include "{(source.PNP/("sky130_fd_pr__pnp_05v5_"+size+".model.spice")).as_posix()}"\n'
    return text

def controller():
    reference=bg.build(27,True)
    start=reference.index('* Same-primitive')
    body=reference[start:reference.index('\n.control',start)]
    # Node renaming only; the licensed amplifier and startup topology is kept.
    body=re.sub(r'\bvdd\b','avdd',body,flags=re.I)
    return body+'''
* Real five-MOS comparator, biased by the self-biased reference mirror.
RCMPTOP dvdd vsense 220k
RCMPBOTTOM vsense 0 1meg
XCMPTAIL cmp_tail gdrv avdd avdd sky130_fd_pr__pfet_g5v0d10v5 L=2 W=8
XCMPP1 cmp_d1 vsense cmp_tail avdd sky130_fd_pr__pfet_g5v0d10v5 L=2 W=20
XCMPP2 cmpout vref cmp_tail avdd sky130_fd_pr__pfet_g5v0d10v5 L=2 W=20
XCMPN1 cmp_d1 cmp_d1 0 0 sky130_fd_pr__nfet_g5v0d10v5 L=2 W=4
XCMPN2 cmpout cmp_d1 0 0 sky130_fd_pr__nfet_g5v0d10v5 L=2 W=4
* High-voltage NMOS isolates the comparator from the 1.8 V inverter gate.
RLEVEL dvdd level_n 1meg
XLEVEL level_n cmpout 0 0 sky130_fd_pr__nfet_g5v0d10v5 L=.5 W=1
XRESET_P ref_reset level_n dvdd dvdd sky130_fd_pr__pfet_01v8 L=.15 W=2
XRESET_N ref_reset level_n 0 0 sky130_fd_pr__nfet_01v8 L=.15 W=.42
'''

def build_pair(case,variant,max_step=2e-6):
    temp,event=CASES[case];assert variant in ('original','reference_supervisor')
    if event=='shallow_depth':text,args=generate_condition(event,'original',max_step)
    else:text,*args=por_generate(event,True,max_step)
    assert text.count('.temp 27\n')==1
    text=text.replace('.temp 27\n',f'.temp {temp}\n')
    if variant=='reference_supervisor':
        text,count=re.subn(r'(?m)^XPOR .*$', '* Published POR instance replaced by reference supervisor.',text);assert count==1
        text,count=re.subn(r'(?m)^XDUT clk d porb_l ', 'XDUT clk d ref_reset ',text);assert count==1
        text=text.replace(f'.temp {temp}\n',pnp_models()+f'.temp {temp}\n')
        text=text.replace('v(porb_l)','v(ref_reset)')
        text=text.replace('v(porb_h) v(por_l) v(xpor.net9)','v(vref) v(gdrv) v(cmpout)')
        for prefix in ('.save ','wrdata history.dat '):
            text,count=re.subn(r'(?m)^'+re.escape(prefix)+r'(.*)$',lambda m:prefix+m[1]+' v(vsense) v(level_n) v(cmp_tail)',text);assert count==1
        assert text.count('.save ')==1;text=text.replace('.save ',controller()+'.save ',1)
    assert not re.search(r'(?im)^\s*\.(ic|nodeset)\b',text) and not re.search(r'(?im)^\s*[BEGFI]\w+\s',text)
    return text,args

def assess(d,args,case):
    reference=measure(d[:,:16],*args,True);storage=CASES[case][1]=='none'
    t,v=waveform(d[:,0],dict(q=d[:,1],reset=d[:,2],vdd=d[:,3]))
    _,post=segment(t,v,.02102501,float(t[-1]))
    preserves=bool(np.min(post['q'])>=1.44);inactive=bool(np.min(post['reset']-.8*post['vdd'])>=0)
    functional=preserves and inactive if storage else reference['observed_pass']
    if not reference['events'][0]['pass_contract']:diagnosis='not_exercised_cold_start'
    elif not reference['declared_precondition_verified']:diagnosis='not_exercised_prior_state'
    elif functional:diagnosis='requirement_met'
    else:diagnosis='functional_requirement_missed'
    return dict(reference=reference,qualified=diagnosis=='requirement_met',diagnosis=diagnosis,
        storage_requirement=storage,normal_storage_pass=preserves if storage else None,reset_inactive_pass=inactive if storage else None,
        minimum_postwrite_q_V=float(np.min(post['q'])),
        scope='Matched published DFF, ordinary clock/data write, load, supplies and source-work measurement. New controller replaces the POR instance and uses the analog rail for a real self-biased reference/comparator. Its original POR diagnostic columns are replaced by real reference/gate/comparator signals. No fabricated probe values, ideal reference or state forcing. Finite TT-temperature development evidence, not PVT qualification or an optimized supervisor.')

def generate(case,variant,max_step=2e-6,group='primary'):
    if case not in CASES or variant not in VARIANTS or group not in ('primary','step','trough'):
        raise ValueError('Declare a supported reference case, variant and history group')
    if isinstance(max_step,bool) or not math.isfinite(max_step) or max_step<=0:
        raise ValueError('Positive finite maximum step required')
    if variant=='digital_guard':
        temp,event=CASES[case]
        if event=='shallow_depth':text,args=generate_condition(event,variant,max_step)
        else:text,args=guard_generate(event,True,variant,max_step)
        assert text.count('.temp 27\n')==1
        text=text.replace('.temp 27\n',f'.temp {temp}\n')
    else:text,args=build_pair(case,variant,max_step)
    if group=='trough':
        if CASES[case][1]!='none':raise ValueError('Trough challenge requires a storage case')
        vp=supply('trough');args[1]=vp
        pwl=' '.join(f'{t:.17g} {v:.17g}' for t,v in vp)
        text,count=re.subn(r'(?m)^VDVDD .*$', 'VDVDD dvdd 0 PWL('+pwl+')',text);assert count==1
    return text,args

def measure_application(data,args,case,variant):
    d=np.asarray(data)
    if d.ndim!=2 or d.shape[1]!=(16 if variant=='original' else 19) or not np.isfinite(d).all():
        raise ValueError('Missing or nonfinite declared reference-controller probes')
    return assess(d,args,case)
