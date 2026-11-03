"""Timing/corner-qualified native SAR partition with actual PWM waveform inputs."""
from pathlib import Path
import argparse,gzip,json,re,sys,ctypes as C
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.portable_cim_sar import SharedSpice as BaseSpice,RTL,cap_map,bottom as nominal_bottom
from scripts import portable_cim_sar as nominal
from scripts import flow2_adc_partition as adc

class SharedSpice(BaseSpice):
    def __init__(self,path,log):
        super().__init__(path,log);self.target=0.;self.quiet_step_s=10e-9;self.edge_step_s=200e-12
        sync_type=C.CFUNCTYPE(C.c_int,C.c_double,C.POINTER(C.c_double),C.c_double,C.c_int,C.c_int,C.c_int,C.c_void_p)
        def synchronize(actual,delta,old,redo,ident,location,user):
            bound=self.edge_step_s if actual>=self.target-10e-9 else self.quiet_step_s
            if delta[0]>bound:delta[0]=bound
            return 0
        self.sync_callback=sync_type(synchronize)
        self.lib.ngSpice_Init_Sync(self.callbacks[3],None,self.sync_callback,C.byref(self.ident),None)
    def advance(self,seconds):
        if seconds<=0:return
        target=self.time+seconds;self.target=target
        self.command('delete all');self.command(f'stop when time > {target:.17g}')
        self.command('resume' if self.started else getattr(self,'tran_command','tran 100p 100u 0 10n'))
        self.started=True;self.time=float(self.vector('time')[-1])
        if self.time<target-2e-16 or self.time>target+2.1e-9:raise ValueError('native phase boundary not reached')

def bottom(entries,state,side,supply=1.8):
    return nominal_bottom(entries,state,side)*supply/1.8

def coupled_deck(root,acts,weights,column,total,model_override=None,pwm_unit_ps=50,profile=None):
    profile=profile or {};supply=float(profile.get('supply_v',1.8));cm=supply/2
    text,external,vectors=nominal.coupled_deck(root,acts,weights,column,total,model_override,pwm_unit_ps)
    text=re.sub(r'(?m)^(\.lib ".*?") tt$',lambda m:m[1]+' '+profile.get('corner','tt'),text)
    text=text.replace('.temp 25',f".temp {profile.get('temperature_c',25)}")
    if profile.get('core_pex',True):
        text=text.replace(str(Path(root)/'inputs/core_acquisition.spice'),str(profile.get('core_pex_path',Path(root)/'inputs/core_acquisition.pex.spice')))
        text=re.sub(r'(?m)^(XCORE .*?) automx_cim_core_acquisition_proto$',r'\1 automx_cim_core_acquisition_proto_pex',text)
    elif profile.get('core_schematic'):
        text=text.replace(str(Path(root)/'inputs/core_acquisition.spice'),str(profile['core_schematic']))
    timing=profile.get('timing',{});pulse=float(timing.get('pulse_ns',120));pre=float(timing.get('pre_release_ns',80));hold=float(timing.get('track_end_ns',160));select=float(timing.get('select_ns',240))
    pwm=None
    if profile.get('pwm_measurements'):
        pwm=json.loads(Path(profile['pwm_measurements']).read_text())['measurements']
    text=text.replace('.option klu method=gear reltol=1e-3 abstol=1e-12', f".option klu method=gear reltol=1e-3 abstol=1e-12 rshunt={float(profile.get('rshunt_ohm',1e12)):.9g}")
    text=text.replace('.save ',f'.nodeset v(AINP)={cm} v(AINN)={cm} v(CTOPP)={cm} v(CTOPN)={cm} v(LATCH_Q)=0 v(LATCH_QN)={supply}\n.save ')
    output=[]
    for line in text.splitlines():
        if line.startswith('V'):
            # Scale voltage values only, never transistor dimensions/model cards.
            line=re.sub(r'(?<![\w.])1\.8(?![\w.])',str(supply),line)
            line=re.sub(r'(?<![\w.])(?:0?\.9)(?![\w.])',str(cm),line)
        if line.startswith('VPRE '):line=f'VPRE PRE_B 0 PWL(0 0 {pre}n 0 {pre+.1}n {supply} 100u {supply})'
        elif line.startswith('VTRACK '):line=f'VTRACK TRACK 0 PWL(0 {supply} {hold}n {supply} {hold+.1}n 0 100u 0)'
        elif re.match(r'VSEL\d ',line):
            c=int(line[4]);line=f'VSEL{c} SEL{c} 0 '+(f'PWL(0 0 {select}n 0 {select+.1}n {supply} 100u {supply})' if c==column else '0')
        elif re.match(r'VWL[PN]\d ',line):
            fields=line.split();row=int(fields[0][-1]);negative=fields[0][3]=='N';mag=max(-acts[row] if negative else acts[row],0)
            if not mag:line=' '.join(fields[:3])+' 0'
            elif pwm is not None:
                match=next(m for m in pwm if m['row']==row and m['negative']==negative and m['magnitude']==mag)
                wave=match['waveform'];points=[(0.,0.),*[(pulse+t,voltage*supply/1.8) for t,voltage in zip(wave['time_ns'],wave['voltage_v'])],(pulse+15,0.),(100000.,0.)]
                assert all(b[0]>a[0] for a,b in zip(points,points[1:])),points[:4]
                line=' '.join(fields[:3])+' PWL('+' '.join(f'{t:.9g}n {v:.9g}' for t,v in points)+')'
            else:line=' '.join(fields[:3])+f' PULSE(0 {supply} {pulse}n 5p 5p {mag*pwm_unit_ps}p 100u)'
        output.append(line)
    return '\n'.join(output)+'\n',external,vectors

def simulate(root,work,shared_library,acts,weights,column=0,model_override=None,pwm_unit_ps=50,profile=None):
    profile=profile or {};supply=float(profile.get("supply_v",1.8));common_mode=supply/2
    root=Path(root);work=Path(work);work.mkdir(parents=True,exist_ok=True)
    acts=list(map(int,acts));weights=np.asarray(weights,dtype=int)
    if len(acts)!=4 or weights.shape!=(4,4) or not set(weights.flat)<= {-1,0,1} or not set(map(abs,acts))<={0,1,2,3,4,6,8,12,16,24}:
        raise ValueError('4x4 ternary tile and E2M1 x2 input required')
    source=root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition'
    entries=cap_map((source/'spice'/adc.FILES[2]).read_text());total=sum(c for c,_,_ in entries)
    circuit,external,vectors=coupled_deck(root,acts,weights,column,total,model_override,pwm_unit_ps,profile)
    deck=work/'coupled.spice';deck.write_text(circuit)
    log=(work/'ngspice.log').open('w');spice=SharedSpice(shared_library,log);spice.quiet_step_s=float(profile.get("quiet_step_ns",10))*1e-9;spice.tran_command=f"tran 100p 100u 0 {float(profile.get('quiet_step_ns',10))}n"
    rtl=RTL(source/'verilog/rtl',work)
    initial={'VSAMPLE':supply,'VSAMPLEN':0,'VBOTTOMP':common_mode,'VBOTTOMN':common_mode}
    for key in external:spice.initial(key,initial.get(key,0))
    for command in ('set ngbehavior=hsa','set skywaterpdk','set num_threads=1','set noinit'):
        spice.command(command)
    spice.command('version');spice.command('source '+str(deck))
    spice.command('option klu')
    trace=[]
    try:
        spice.advance(float(profile.get("timing",{}).get("adc_start_ns",920))*1e-9-10e-9)
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
        observed={n:spice.vector(n.lower()) for n in vectors}
        mask=observed['time']>=edge+10e-9
        if np.count_nonzero(mask)<2:raise ValueError('missing stable-word interval')
        word=0
        for bit in range(16):
            values=observed[f'v(RESULT_{bit})'][mask]
            if np.all(values>=.9*supply):word|=1<<bit
            elif not np.all(values<=.1*supply):raise ValueError('unstable native bridged result bit')
        if word!=state['result'] or word&15:raise ValueError('RTL/native result bridge differs')
        spice.command('set filetype=ascii')
        spice.command('write '+str(work/'coupled.raw')+' '+' '.join(vectors))
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
        raw=work/'coupled.raw'
        with raw.open('rb') as source,gzip.open(work/'coupled.raw.gz','wb',compresslevel=1) as destination:
            __import__('shutil').copyfileobj(source,destination)
        raw.unlink();report['waveform']='coupled.raw.gz'
        (work/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    finally:
        if not (work/'summary.json').exists():
            (work/'bridge_history.json').write_text(json.dumps(spice.hist,indent=2)+'\n')
            spice.lib.ngSpice_Command(('write '+str(work/'partial.raw')+' '+' '.join(vectors)).encode())
        rtl.close();log.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--case',type=Path,required=True);a=p.parse_args();d=json.loads(a.case.read_text());simulate(a.root,a.work,a.library,d['activation_x2'],d['weights'],d.get('column',0),pwm_unit_ps=d.get('pwm_unit_ps',50),profile=d.get('profile'))
