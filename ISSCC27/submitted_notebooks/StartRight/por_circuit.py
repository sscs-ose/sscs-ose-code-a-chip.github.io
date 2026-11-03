"""Declared dual-supply POR/DFF experiment; no forced stored state.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import math,re
import numpy as np
from por_models import nominal_deck
from reset_contract import Band,Window,evaluate,source_work,waveform
from powered_reset import witness
HERE=Path(__file__).resolve().parent
EVENTS=('none','analog','digital','both','analog_half','digital_zero')


def generate(domain,command,max_step=2e-6,profile="common"):
    if domain not in EVENTS or not isinstance(command,bool):raise ValueError("Declare a known event and Boolean prior-state operation")
    if not math.isfinite(max_step) or max_step<=0 or profile not in ["common","strict"]:raise ValueError("Invalid integration setting")
    start=.025;down=start+1e-6;low_end=down+.001;rise_end=low_end+.002;stop=rise_end+.020
    alow=1.65 if domain=='analog_half' else (0. if domain in ['analog','both'] else 3.3)
    dlow=0. if domain=='digital_zero' else (.9 if domain in ['digital','both'] else 1.8)
    ap=[[0.,0.],[.0001,0.],[.005,3.3],[.020,3.3],[start,3.3],[down,alow],[low_end,alow],[rise_end,3.3],[stop,3.3]]
    vp=[[0.,0.],[.0003,0.],[.0053,1.8],[.020,1.8],[start,1.8],[down,dlow],[low_end,dlow],[rise_end,1.8],[stop,1.8]]
    dp=[[0.,0.],[stop,0.]] if not command else [[0.,0.],[.021,0.],[.02100001,1.8],[.02102,1.8],[.02102001,0.],[stop,0.]]
    cp=[[0.,0.],[.021005,0.],[.02100501,1.8],[.021006,1.8],[.02100601,0.],[stop,0.]]
    windows=[Window('cold',0.,.0053,.020),Window('recovery',low_end,rise_end,stop)]
    pwl=lambda rows:' '.join(f'{t:.17g} {v:.17g}' for t,v in rows)
    text=nominal_deck(True).replace('abstol=1e-15 vntol=1e-7','abstol=1e-14 vntol=1e-6');text=re.sub(r'(?s)\.control\n.*?\.endc\n','',text);text=re.sub(r'(?m)^\.save .*\n','',text)
    text=re.sub(r'(?m)^VAVDD .*$',f'VAVDD avdd 0 PWL({pwl(ap)})',text);text=re.sub(r'(?m)^VDVDD .*$',f'VDVDD dvdd 0 PWL({pwl(vp)})',text)
    p=HERE/'upstream';hvt=p/'skywater-pdk-libs-sky130_fd_pr/cells/pfet_01v8_hvt'
    extra=''.join(f'.include "{(hvt/n).as_posix()}"\n' for n in ['sky130_fd_pr__pfet_01v8_hvt__tt.corner.spice','sky130_fd_pr__pfet_01v8_hvt__mismatch.corner.spice'])
    extra+=f'.include "{(p/"skywater-pdk-libs-sky130_fd_sc_hd/cells/dfrtp/sky130_fd_sc_hd__dfrtp_1.spice").as_posix()}"\n'
    text=text.replace('.temp 27\n',extra+'.temp 27\n',1)
    vectors='v(q) v(porb_l) v(dvdd) i(VDVDD) v(clk) v(d) v(clkdrv) i(VCLK) v(ddrv) i(VDATA) v(avdd) i(VAVDD) v(porb_h) v(por_l) v(xpor.net9)'
    bench=f'''VCLK clkdrv 0 PWL({pwl(cp)})
VDATA ddrv 0 PWL({pwl(dp)})
RCLK clkdrv clk 1k
RDATA ddrv d 1k
XDUT clk d porb_l 0 0 dvdd dvdd q sky130_fd_sc_hd__dfrtp_1
CQ q 0 10f
.save {vectors}
.control
set numdgt=17
set wr_singlescale
set wr_vecnames
tran 1u {stop:.17g} 0 {max_step:.17g}
wrdata history.dat {vectors}
quit
.endc
'''
    assert text.count('.end\n')==1;text=text.replace('.end\n',bench+'.end\n')
    if profile=='strict':text=text.replace('abstol=1e-14 vntol=1e-6','abstol=1e-15 vntol=1e-7')
    return text,ap,vp,dp,cp,windows


def measure(data,ap,vp,dp,cp,windows,command):
    d=np.asarray(data)
    if d.ndim!=2 or d.shape[1]!=16 or not np.isfinite(d).all():raise ValueError('Missing or nonfinite POR vectors')
    t,values=waveform(d[:,0],dict(q=d[:,1],reset_b=d[:,2],vdd=d[:,3],avdd=d[:,11]))
    if np.max(abs(d[0,[1,2,3,11]]))>1e-5:raise ValueError('Not the declared physical zero-supply start')
    for name,p,col,tol in [('analog supply',ap,11,1e-6),('clock',cp,5,.005),('data',dp,6,.005)]:
        mask=np.ones(len(t),dtype=bool)
        if name!='analog supply':
            for time,_ in p:mask&=abs(t-time)>1e-7
        if not mask.any() or np.max(abs(d[mask,col]-np.interp(t[mask],[r[0] for r in p],[r[1] for r in p])))>tol:raise ValueError('Declared source witness differs: '+name)
    rails=[Band('vdd',lower=.95*1.8),Band('avdd',lower=.95*3.3)]
    intended=[Band('q',upper=.2*1.8)];alternate=[Band('q',lower=.8*1.8)]
    guard=.025-1e-7
    result=evaluate(t,values,supply_points=vp,windows=windows,state_bands=rails+intended,release_bands=rails+[Band('reset_b',lower=.95*1.8)],state_delay_s=.012,release_delay_s=.012,hold_s=.001,
        precondition_interval=(guard-5e-6,guard),prior_bands=alternate if command else intended,alternate_bands=alternate)
    work=source_work(t,dict(analog=(d[:,11],d[:,12]),digital=(d[:,3],d[:,4]),clock=(d[:,7],d[:,8]),data=(d[:,9],d[:,10])))
    result.update(source_work=work,final_q_V=float(d[-1,1]),minimum_q_final_hold_V=float(np.min(d[t>=t[-1]-.001,1])),maximum_q_final_hold_V=float(np.max(d[t>=t[-1]-.001,1])),
        scope='Declared dual-rail integration contract, not a published upstream guarantee. Analog and digital readiness bands both checked. All four independent sources counted. No cross-architecture energy ranking or defect claim from an unclaimed digital-rail requirement.')
    result['powered_reset_witness']=witness(t,dict(vdd=d[:,3],reset=d[:,2]),bands=[Band('vdd',lower=1.71),Band('reset',upper=.36)],start_s=.025,stop_s=.040001,minimum_duration_s=1e-7)
    return result
