"""Timing/corner-qualified native SAR partition with actual PWM waveform inputs."""
from pathlib import Path
import argparse,gzip,json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.portable_cim_sar import SharedSpice as BaseSpice,RTL,cap_map,bottom as nominal_bottom
from scripts import portable_cim_sar as nominal
from scripts import flow2_adc_partition as adc

from scripts.qualified_cim_sar import SharedSpice,coupled_deck,bottom

def simulate(root,work,shared_library,acts,weights,column=0,model_override=None,pwm_unit_ps=50,profile=None):
    profile=profile or {};supply=float(profile.get("supply_v",1.8));common_mode=supply/2
    root=Path(root);work=Path(work);work.mkdir(parents=True,exist_ok=True)
    acts=list(map(int,acts));weights=np.asarray(weights,dtype=int)
    if len(acts)!=4 or weights.shape!=(4,4) or not set(weights.flat)<= {-1,0,1} or not set(map(abs,acts))<={0,1,2,3,4,6,8,12,16,24}:
        raise ValueError('4x4 ternary tile and E2M1 x2 input required')
    source=root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition'
    session=get_session(root,work,shared_library,acts,weights,column,pwm_unit_ps,profile)
    spice=session.spice;external=session.external;vectors=session.vectors;entries=session.entries;total=session.total
    base=spice.time;session.configure(acts,weights,column,profile)
    (work/'coupled.spice').write_text(session.circuit)
    rtl=RTL(source/'verilog/rtl',work)
    trace=[]
    try:
        spice.advance(base+float(profile.get("timing",{}).get("adc_start_ns",920))*1e-9-10e-9-spice.time)
        # Resolve the physical latch through a real evaluation/reset pulse
        # while the input TG is still tracking, before starting SAR control.
        spice.drive('VCLKCOMP',supply);spice.advance(7e-9)
        spice.drive('VCLKCOMP',0.);spice.advance(3e-9)
        before=float(spice.vector('eoc_osr')[-1])
        if before>.18:raise ValueError('EOC already high before START')
        input_diff=float(spice.vector('ainp')[-1]-spice.vector('ainn')[-1])
        start=spice.time;spice.drive('VRST',supply);spice.drive('VSTART',supply)
        state=rtl.clock(0)
        def bridge(s):
            spice.drive('VSAMPLE',supply*s['sample']);spice.drive('VSAMPLEN',supply*s['sample_n'])
            for side in ('p','n'):spice.drive('VBOTTOM'+side.upper(),common_mode if s['sample'] else bottom(entries,s,side,supply))
            for key,bit in (('VEOC','eoc'),('VEOCOSR','eoc_osr')):spice.drive(key,supply*s[bit])
            for bit in range(16):spice.drive('VRESULT'+str(bit),supply*((s['result']>>bit)&1))
        bridge(state);spice.advance(2e-9)
        for cycle in range(24):
            spice.drive('VCLKCOMP',0.);spice.advance(3e-9)
            spice.drive('VCLKCOMP',supply);spice.advance(7e-9)
            q=float(spice.vector('latch_q')[-1])
            if not(q<=.1*supply or q>=.9*supply):
                spice.advance(20e-9);q=float(spice.vector('latch_q')[-1])
            if not(q<=.1*supply or q>=.9*supply):raise ValueError('transistor comparator did not resolve')
            decision=int(q>common_mode);state=rtl.clock(decision);bridge(state)
            trace.append(dict(cycle=cycle,time_s=spice.time,comparator_v=q,decision=decision,rtl=dict(state)))
            print('[RTL/SAR]',cycle,'decision',decision,'result',state['result'],'EOC',state['eoc_osr'],flush=True)
            spice.advance(3e-9)
            if cycle==1:spice.drive('VSTART',0.)
            if state['eoc_osr']:break
        if not state['eoc_osr'] or len(trace)<16:raise ValueError('real SAR RTL did not generate a fresh EOC')
        edge=spice.time;spice.advance(40e-9)
        window=spice.vector('time')>=base;observed={n:spice.vector(n.lower())[window] for n in vectors}
        mask=observed['time']>=edge+10e-9
        if np.count_nonzero(mask)<2:raise ValueError('missing stable-word interval')
        word=0
        for bit in range(16):
            values=observed[f'v(RESULT_{bit})'][mask]
            if np.all(values>=.9*supply):word|=1<<bit
            elif not np.all(values<=.1*supply):raise ValueError('unstable native bridged result bit')
        if word!=state['result'] or word&15:raise ValueError('RTL/native result bridge differs')
        np.savez_compressed(work/'waveforms.npz',**observed)
        meter_t=observed['time'];meter_v=observed['v(VPWR)']
        meter_int=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
        meter_energy={'start_s':float(meter_t[0]),'end_s':float(meter_t[-1]),'duration_s':float(meter_t[-1]-meter_t[0])}
        for key,probe in [('core_acquisition_vdd_j','VCORE_METER'),('conditioner_vdd_j','VCOND_METER'),('adc_vdd_j','VADC_METER')]:
            meter_energy[key]=float(meter_int(meter_v*observed['i('+probe+')'],meter_t))
        meter_bridge=np.zeros_like(meter_t)
        for node,source in [('BOTTOMP','VBOTTOMP'),('BOTTOMN','VBOTTOMN'),('SAMPLE','VSAMPLE'),('SAMPLE_N','VSAMPLEN'),('ADC_CLK_COMP','VCLKCOMP'),('VCM','VVCM')]:
            meter_bridge-=observed['v('+node+')']*observed['i('+source+')']
        meter_energy['adc_bridge_net_j']=float(meter_int(meter_bridge,meter_t))
        meter_energy['monitored_total_j']=sum(meter_energy[k] for k in ('core_acquisition_vdd_j','conditioner_vdd_j','adc_vdd_j','adc_bridge_net_j'))
        meter_vdd=float(meter_int(-meter_v*observed['i(VVDD)'],meter_t))
        if not np.isclose(meter_vdd,sum(meter_energy[k] for k in ('core_acquisition_vdd_j','conditioner_vdd_j','adc_vdd_j')),rtol=1e-5,atol=1e-18):raise ValueError('VDD branch energy does not balance')
        (work/'energy.json').write_text(json.dumps(meter_energy,indent=2)+'\n')
        print('MEASURED_ENERGY_J',json.dumps(meter_energy),flush=True)
        report=dict(profile=profile,energy=meter_energy,pwm_unit_ps=pwm_unit_ps,status='COUPLED_ANALOG_RTL_ADC_PARTITION_CONVERSION_PASS',
            activation_x2=acts,weights=weights.tolist(),column=column,expected_integer_sum=int(np.asarray(acts)@weights[:,column]),
            measured_input_diff_v=input_diff,result_word_16bit=word,result_code_12bit=word>>4,
            start_s=start,eoc_s=edge,start_to_eoc_s=edge-start,cycles=len(trace),trace=trace,
            capacitor_inventory=len(entries),capacitance_per_side_f=total,
            scope='Timing-profiled CIM/acquisition PEX and schematic conditioner, transistor ADC TG/comparator; '
                  'upstream SAR/decoder/OSR RTL in Icarus. CDAC C aggregation with ideal bottom drivers, '
                  'external ideal VCM/phase clock; noise-decoupling varactors omitted, comparator MOS/MIM retained. '
                  'No full transistor PEX, decoder hazards, power/noise/PVT signoff.')
        (work/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
        report.update(waveform='waveforms.npz',continuous_session=True,base_time_s=base)
        (work/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    finally:
        rtl.close()

class Session:
    def __init__(self,root,work,library,acts,weights,column,pwm_unit_ps,profile):
        self.root=root;self.profile=profile;self.supply=float(profile.get('supply_v',1.8))
        source=root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition'
        self.entries=cap_map((source/'spice'/adc.FILES[2]).read_text());self.total=sum(c for c,_,_ in self.entries)
        text,external,self.vectors=coupled_deck(root,acts,weights,column,self.total,pwm_unit_ps=pwm_unit_ps,profile=profile)
        lines=[]
        for line in text.splitlines():
            if re.match(r'^V(?:PRE|TRACK|SEL[0-3]|WL[PN][0-3]|WPOS_\d_\d|WNEG_\d_\d) ',line):
                parts=line.split();external[parts[0]]=parts[1];line=' '.join(parts[:3])+' external'
            lines.append(line)
        self.external=external;self.circuit='\n'.join(lines)+'\n';self.folder=work.parent.parent/'sessions'/work.name
        self.folder.mkdir(parents=True,exist_ok=True);deck=self.folder/'session.spice';deck.write_text(self.circuit)
        self.log=(self.folder/'ngspice.log').open('w');self.spice=SharedSpice(library,self.log)
        self.spice.quiet_step_s=float(profile.get('quiet_step_ns',10))*1e-9;self.spice.tran_command=f"tran 100p 10m 0 {float(profile.get('quiet_step_ns',10))}n"
        for key in external:self.spice.initial(key,{'VSAMPLE':self.supply,'VBOTTOMP':self.supply/2,'VBOTTOMN':self.supply/2}.get(key,0))
        for cmd in ('set ngbehavior=hsa','set skywaterpdk','set num_threads=1','set noinit'):self.spice.command(cmd)
        self.spice.command('source '+str(deck));self.spice.command('option klu')
    def points(self,name,points):
        history=self.spice.hist[name.lower()]
        assert all(t>self.spice.time for t,v in points)
        history.extend(points)
        for t,v in points:self.spice.lib.ngSpice_SetBkpt(t)
    def constant(self,name,value):
        b=self.spice.time;old=self.spice.hist[name.lower()][-1][1]
        self.points(name,[(b+2e-12,old),(b+102e-12,float(value))])
    def configure(self,acts,weights,column,profile):
        b=self.spice.time;v=self.supply;t=profile.get('timing',{});pre=t.get('pre_release_ns',80)*1e-9;hold=t.get('track_end_ns',160)*1e-9;sel=t.get('select_ns',240)*1e-9;pulse=t.get('pulse_ns',120)*1e-9
        self.points('VPRE',[(b+2e-12,self.spice.hist['vpre'][-1][1]),(b+102e-12,0),(b+pre,0),(b+pre+.1e-9,v)])
        self.points('VTRACK',[(b+2e-12,self.spice.hist['vtrack'][-1][1]),(b+102e-12,v),(b+hold,v),(b+hold+.1e-9,0)])
        for c in range(4):
            self.points('VSEL'+str(c),[(b+2e-12,self.spice.hist['vsel'+str(c)][-1][1]),(b+102e-12,0),(b+sel,0),(b+sel+.1e-9,v if c==column else 0)])
        pwm=json.loads(Path(profile['pwm_measurements']).read_text())['measurements'] if profile.get('pwm_measurements') else None
        for row in range(4):
            for pol in ('P','N'):
                name='VWL'+pol+str(row);mag=max(-acts[row] if pol=='N' else acts[row],0)
                pts=[(b+2e-12,0.)]
                if mag:
                    if pwm:
                        m=next(x for x in pwm if x['row']==row and x['negative']==(pol=='N') and x['magnitude']==mag)
                        pts.extend((b+pulse+tn*1e-9,voltage*v/1.8) for tn,voltage in zip(m['waveform']['time_ns'],m['waveform']['voltage_v']))
                    else:
                        pts.extend([(b+pulse,0.),(b+pulse+5e-12,v),(b+pulse+5e-12+mag*50e-12,v),(b+pulse+10e-12+mag*50e-12,0.)])
                self.points(name,pts)
            for c in range(4):
                self.constant(f'VWPOS_{row}_{c}',v if weights[row,c]>0 else 0)
                self.constant(f'VWNEG_{row}_{c}',v if weights[row,c]<0 else 0)
        for name,value in [('VSAMPLE',v),('VSAMPLEN',0),('VBOTTOMP',v/2),('VBOTTOMN',v/2),('VCLKCOMP',0),('VRST',0),('VSTART',0),('VEOC',0),('VEOCOSR',0)]:self.constant(name,value)

_SESSION=None
def get_session(root,work,library,acts,weights,column,pwm_unit_ps,profile):
    global _SESSION
    if _SESSION is None:_SESSION=Session(root,work,library,acts,weights,column,pwm_unit_ps,profile)
    assert (_SESSION.profile.get('corner','tt'),_SESSION.supply,_SESSION.profile.get('temperature_c',25),_SESSION.profile.get('core_pex',True))==(profile.get('corner','tt'),float(profile.get('supply_v',1.8)),profile.get('temperature_c',25),profile.get('core_pex',True))
    assert all(_SESSION.profile.get(k)==profile.get(k) for k in ('core_schematic','core_pex_path','rshunt_ohm','quiet_step_ns'))
    return _SESSION

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--batch',type=Path,required=True);a=p.parse_args()
    for entry in json.loads(a.batch.read_text()):
        work=Path(entry['folder']);d=json.loads((work/'case.json').read_text())
        simulate(a.root,work,a.library,d['activation_x2'],d['weights'],d['column'],profile=d.get('profile'))
        print('STREAM_CASE_PASS',work,flush=True)
