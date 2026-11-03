# Copyright 2026 EDABK Laboratory. SPDX-License-Identifier: Apache-2.0.
# Portable native worker, identical circuit/energy implementation to the notebook.
from json import dumps as pretty
"""Native Icarus upstream SAR RTL <-> ngspice transistor feedback.

Co-simulation uses ideal electrical bridges and an external phase clock.
Comparator/input TG are real SKY130 devices. CDAC signal capacitors use the
exact upstream schematic inventory, with linear aggregation and ideal drivers.
"""
import bisect
import ctypes as C
import json
from pathlib import Path
import re
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import flow2_adc_partition as adc


class Vector(C.Structure):
    _fields_=[('name',C.c_char_p),('type',C.c_int),('flags',C.c_short),
              ('real',C.POINTER(C.c_double)),('complex',C.c_void_p),('length',C.c_int)]


class SharedSpice:
    def __init__(self,path,log):
        self.lib=C.CDLL(str(path));self.log=log;self.hist={};self.errors=[]
        char=C.CFUNCTYPE(C.c_int,C.c_char_p,C.c_int,C.c_void_p)
        exit_type=C.CFUNCTYPE(C.c_int,C.c_int,C.c_bool,C.c_bool,C.c_int,C.c_void_p)
        vsrc=C.CFUNCTYPE(C.c_int,C.POINTER(C.c_double),C.c_double,C.c_char_p,C.c_int,C.c_void_p)
        def output(message,*_):
            line=message.decode(errors='replace');self.log.write(line+'\n');self.log.flush()
            if re.search(r'(?i)\b(?:error:|fatal:)',line):self.errors.append(line)
            if 'Reference value' not in line:print('[ngspice] '+line,flush=True)
            return 0
        def voltage(value,t,name,*_):
            history=self.hist.get(name.decode().lower(),[(0.,0.)])
            times=[p[0] for p in history];i=bisect.bisect_right(times,t)-1
            if i<0:value[0]=history[0][1]
            elif i+1==len(history):value[0]=history[i][1]
            else:
                a,x=history[i];b,y=history[i+1];value[0]=x+(y-x)*(t-a)/(b-a)
            return 0
        self.callbacks=(char(output),char(lambda *_:0),exit_type(lambda *_:0),vsrc(voltage))
        self.lib.ngSpice_Init(*self.callbacks[:3],None,None,None,None)
        self.ident=C.c_int(0)
        self.lib.ngSpice_Init_Sync(self.callbacks[3],None,None,C.byref(self.ident),None)
        self.lib.ngSpice_Command.argtypes=[C.c_char_p];self.lib.ngSpice_Command.restype=C.c_int
        self.lib.ngGet_Vec_Info.argtypes=[C.c_char_p];self.lib.ngGet_Vec_Info.restype=C.POINTER(Vector)
        self.lib.ngSpice_SetBkpt.argtypes=[C.c_double];self.lib.ngSpice_SetBkpt.restype=C.c_bool
        self.started=False;self.time=0.

    def command(self,text):
        code=self.lib.ngSpice_Command(text.encode())
        if code:raise RuntimeError('ngspice command failed: '+text)
        if self.errors:raise RuntimeError(self.errors[-1])

    def initial(self,name,value):self.hist[name.lower()]=[(0.,float(value))]

    def drive(self,name,value):
        key=name.lower();h=self.hist[key];at=self.time+2e-12
        previous=h[-1][1]
        if float(value)==previous:return
        h.extend([(at,previous),(at+100e-12,float(value))])
        # External-source transitions must be explicit integration breakpoints;
        # otherwise a resumed solver can step across an unseen bridge edge.
        self.lib.ngSpice_SetBkpt(at);self.lib.ngSpice_SetBkpt(at+100e-12)

    def vector(self,name):
        pointer=self.lib.ngGet_Vec_Info(name.encode())
        if not pointer or pointer.contents.length<=0:raise ValueError('missing vector '+name)
        v=pointer.contents
        return np.ctypeslib.as_array(v.real,shape=(v.length,)).copy()

    def advance(self,seconds):
        target=self.time+seconds
        self.command('delete all')
        self.command(f'stop when time > {target:.17g}')
        self.command('resume' if self.started else 'tran 100p 4u 0 200p')
        self.started=True;self.time=float(self.vector('time')[-1])
        if self.time<target or self.time>target+1e-9:raise ValueError('native trajectory did not reach phase boundary')


RTL_FIELDS=('sample','sample_n','result','eoc','eoc_osr','pr','pro','pc','pb','p0','nr','nro','nc','nb','n0')


def testbench():
    fields=' '.join('%h' for _ in RTL_FIELDS)
    args='sample,sample_n,result,eoc,eoc_osr,pr,pro,pc,pb,p0,nr,nro,nc,nb,n0'
    return '''`timescale 1ns/1ps
module cosim;
reg clk=0,rst=1,decision=0;
integer value,rc;
wire sample,sample_n,eoc,eoc_osr,ena;
wire [15:0] result,pr,pro,nr,nro;
wire [31:0] pc,nc;
wire [2:0] pb,nb;
wire p0,n0;
adc_core_digital dut(.rst_n(rst),.config_1_in(16'h0400),.config_2_in(16'h8421),
 .result_out(result),.conv_finished_out(eoc),.conv_finished_osr_out(eoc_osr),
 .comparator_in(decision),.clk_dig_in(clk),.enable_loop_out(ena),
 .sample_matrix_out(sample),.sample_matrix_out_n(sample_n),
 .pmatrix_row_out_n(pr),.pmatrix_rowon_out_n(pro),.pmatrix_col_out_n(pc),
 .pmatrix_bincap_out_n(pb),.pmatrix_c0_out_n(p0),
 .nmatrix_row_out_n(nr),.nmatrix_rowon_out_n(nro),.nmatrix_col_out_n(nc),
 .nmatrix_bincap_out_n(nb),.nmatrix_c0_out_n(n0));
initial begin
 #1;rst=0;#1;clk=1;#1;clk=0;#1;rst=1;#1;
 $display("STATE '''+fields+'''",'''+args+''');$fflush();
 forever begin
  rc=$fscanf(32'h80000000,"%d",value);
  if(rc!=1)$finish;
  decision=value;#1;clk=1;#1;clk=0;#1;
  $display("STATE '''+fields+'''",'''+args+''');$fflush();
 end
end
endmodule
'''


class RTL:
    def __init__(self,source,work):
        work=Path(work);tb=work/'cosim.sv';tb.write_text(testbench())
        files=[Path(source)/f for f in ('adc_control_nonbinary.v','adc_row_col_decoder.v','adc_osr.v','adc_core_digital.v')]
        cmd=['iverilog','-g2012','-s','cosim','-o',str(work/'sar.vvp'),str(tb),*map(str,files)]
        compiled=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
        (work/'iverilog.log').write_text(compiled.stdout+compiled.stderr)
        print('[Icarus] '+' '.join(cmd)+'\n'+compiled.stdout+compiled.stderr,flush=True)
        if compiled.returncode:raise ValueError('upstream SAR RTL compilation failed')
        self.proc=subprocess.Popen(['vvp',str(work/'sar.vvp')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,text=True,bufsize=1)
        self.log=(work/'rtl.log').open('w');self.state=self.read()

    def read(self):
        line=self.proc.stdout.readline();self.log.write(line);self.log.flush()
        if not line.startswith('STATE '):raise ValueError('RTL bridge lost state: '+line)
        tokens=line.split()[1:]
        if len(tokens)!=len(RTL_FIELDS) or any(re.search('[xz]',t,re.I) for t in tokens):raise ValueError('unknown/partial RTL state')
        self.state=dict(zip(RTL_FIELDS,(int(t,16) for t in tokens)));return self.state

    def clock(self,decision):
        if decision not in (0,1):raise ValueError('binary comparator decision required')
        self.proc.stdin.write(str(decision)+'\n');self.proc.stdin.flush();return self.read()

    def close(self):
        self.proc.stdin.close();self.proc.wait(timeout=5);self.log.close()


def cap_map(text):
    blocks=adc.subcircuits(text);entries=[]
    for row in adc.cards(blocks['adc_array_matrix_12bit'])[1:]:
        f=row.split()
        if not f or not f[0].lower().startswith('x'):continue
        model=f[-1];caps=[r.split() for r in adc.cards(blocks[model]) if r.lower().startswith('c')]
        if not caps:continue
        mapping=dict(zip(adc.ports(blocks[model],model),f[1:-1]))
        entries.append((float(caps[0][3][:-1])*1e-15,mapping,model.endswith('_8')))
    if len(entries)!=515:raise ValueError('CDAC source inventory differs')
    return entries


def bottom(entries,state,side):
    def bit(node):
        if node=='VDD':return 1
        if node=='VSS':return 0
        if node=='en_C0_n':return state[side+'0']
        m=re.fullmatch(r'(row_n|rowon_n|col_n|en_bit_n)\[(\d+)\]',node)
        if not m:raise ValueError('unresolved CDAC control '+node)
        stem={'row_n':'r','rowon_n':'ro','col_n':'c','en_bit_n':'b'}[m[1]]
        return (state[side+stem]>>int(m[2]))&1
    charge=0.;total=sum(c for c,_,_ in entries)
    for cap,mapping,full in entries:
        high=((not bit(mapping['rowon_n'])) or ((not bit(mapping['row_n'])) and (not bit(mapping['col_n'])))) if full else not bit(mapping['en_n'])
        charge+=cap*float(high)*1.8
    return charge/total


def coupled_deck(root,acts,weights,column,total,model_override=None,pwm_unit_ps=50):
    from scripts.run_flow2_core_tap_transient import source
    from scripts import run_flow2_core_acquisition as core
    from scripts import flow2_wrapper_design as design
    from scripts import flow2_integration_common as common
    root=Path(root);views={'schematic':root/'inputs/core_acquisition.spice'};data={'pdk':str(root/'pdks/analog/sky130A')}
    cond=root/'inputs/conditioner.spice'
    model=Path(data['pdk'])/'libs.tech/ngspice/sky130.lib.spice'
    if model_override is not None:model=Path(model_override)
    upstream=root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition/spice'
    matrix=adc.subcircuits((upstream/adc.FILES[2]).read_text())
    comp=re.sub(r'(?im)^\.end\s*$','',(upstream/adc.FILES[3]).read_text())
    # Functional partition: retain every comparator MOS and MIM device.
    # The optional noise-decoupling varactor has an unstable native charge
    # model in this co-simulation; omit it explicitly, never certify noise/PEX.
    comp='\n'.join(row for row in adc.cards(comp) if 'sky130_fd_pr__cap_var_' not in row)
    lines=['Coupled CIM schematic + conditioner + native transistor SAR partition',
        f'.lib "{model}" tt','.param mc_mm_switch=0','.temp 25',
        '.option klu method=gear reltol=1e-3 abstol=1e-12',
        f'.include "{views["schematic"]}"',f'.include "{cond}"',matrix['adc_gate_switch'],comp,
        'VVDD VPWR 0 1.8','VVCM VCM 0 .9',
        'VCORE_METER VPWR VDD_CORE 0','VCOND_METER VPWR VDD_COND 0','VADC_METER VPWR VDD_ADC 0',
        'VPRE PRE_B 0 PWL(0 0 2n 0 2.05n 1.8 4u 1.8)',
        'VTRACK TRACK 0 PWL(0 1.8 8n 1.8 8.05n 0 4u 0)',
        'XCORE '+' '.join('0' if p=='VGND' else ('VDD_CORE' if p=='VPWR' else p) for p in core.PINS)+' '+core.CELL,
        'XCOND '+' '.join('0' if p=='VGND' else ('VDD_COND' if p=='VPWR' else p) for p in design.COND_PINS)+' '+design.COND]
    for row,a in enumerate(acts):
        for phase,magnitude in (('WLP',max(a,0)),('WLN',max(-a,0))):
            pulse=f'PULSE(0 1.8 5n 5p 5p {magnitude*pwm_unit_ps}p 10u)' if magnitude else '0'
            lines.append(f'V{phase}{row} {phase}{row} 0 {pulse}')
        for col in range(4):
            for pol,enabled in (('WPOS',weights[row][col]>0),('WNEG',weights[row][col]<0)):
                lines.append(f'V{pol}_{row}_{col} {pol}_{row}_{col} 0 '+('1.8' if enabled else '0'))
    lines += [f'VSEL{c} SEL{c} 0 '+('1.8' if c==column else '0') for c in range(4)]
    external={'VSAMPLE':'SAMPLE','VSAMPLEN':'SAMPLE_N','VBOTTOMP':'BOTTOMP','VBOTTOMN':'BOTTOMN',
        'VCLKCOMP':'ADC_CLK_COMP','VRST':'RST_N','VSTART':'START','VEOC':'EOC','VEOCOSR':'EOC_OSR'}
    external.update({f'VRESULT{b}':f'RESULT_{b}' for b in range(16)})
    lines += [f'{name} {node} 0 external' for name,node in external.items()]
    lines += [f'CDACP CTOPP BOTTOMP {total:.17g}',f'CDACN CTOPN BOTTOMN {total:.17g}',
        # BLP discharges for a positive product. Cross the ADC inputs so
        # ascending raw code matches the top's signed decoder contract.
        'XSP SAMPLE_N AINN SAMPLE CTOPP VDD_ADC 0 adc_gate_switch',
        'XSN SAMPLE_N AINP SAMPLE CTOPN VDD_ADC 0 adc_gate_switch',
        'XCOMP VDD_ADC 0 ADC_CLK_COMP CTOPP CTOPN COMP_TRIG LATCH_QN LATCH_Q adc_comp_latch']
    vectors=['time',*('v('+p+')' for p in ('AINP','AINN','CTOPP','CTOPN','LATCH_Q','COMP_TRIG',
        'ADC_CLK_COMP','SAMPLE','BOTTOMP','BOTTOMN','RST_N','START','EOC','EOC_OSR',
        'HP'+str(column),'HN'+str(column),*(f'RESULT_{b}' for b in range(16))))]
    # ENERGY_METERS_V1: zero-volt series probes do not change the circuit.
    vectors += ['v(VPWR)','v(VCM)','v(SAMPLE_N)',*('i('+name+')' for name in
      ('VVDD','VCORE_METER','VCOND_METER','VADC_METER','VVCM','VBOTTOMP','VBOTTOMN','VSAMPLE','VSAMPLEN','VCLKCOMP'))]
    lines += ['.save '+' '.join(vectors[1:]),'.end','']
    return '\n'.join(lines),external,vectors


def simulate(root,work,shared_library,acts,weights,column=0,model_override=None,pwm_unit_ps=50):
    root=Path(root);work=Path(work);work.mkdir(parents=True,exist_ok=True)
    acts=list(map(int,acts));weights=np.asarray(weights,dtype=int)
    if len(acts)!=4 or weights.shape!=(4,4) or not set(weights.flat)<= {-1,0,1} or not set(map(abs,acts))<={0,1,2,3,4,6,8,12,16,24}:
        raise ValueError('4x4 ternary tile and E2M1 x2 input required')
    source=root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition'
    entries=cap_map((source/'spice'/adc.FILES[2]).read_text());total=sum(c for c,_,_ in entries)
    circuit,external,vectors=coupled_deck(root,acts,weights,column,total,model_override,pwm_unit_ps)
    deck=work/'coupled.spice';deck.write_text(circuit)
    log=(work/'ngspice.log').open('w');spice=SharedSpice(shared_library,log)
    rtl=RTL(source/'verilog/rtl',work)
    initial={'VSAMPLE':1.8,'VSAMPLEN':0,'VBOTTOMP':.9,'VBOTTOMN':.9}
    for key in external:spice.initial(key,initial.get(key,0))
    for command in ('set ngbehavior=hsa','set skywaterpdk','set num_threads=1','set noinit'):
        spice.command(command)
    spice.command('version');spice.command('source '+str(deck))
    spice.command('option klu')
    trace=[]
    try:
        spice.advance(80e-9)
        # Resolve the physical latch through a real evaluation/reset pulse
        # while the input TG is still tracking, before starting SAR control.
        spice.drive('VCLKCOMP',1.8);spice.advance(7e-9)
        spice.drive('VCLKCOMP',0.);spice.advance(3e-9)
        before=float(spice.vector('eoc_osr')[-1])
        if before>.18:raise ValueError('EOC already high before START')
        input_diff=float(spice.vector('ainp')[-1]-spice.vector('ainn')[-1])
        start=spice.time;spice.drive('VRST',1.8);spice.drive('VSTART',1.8)
        state=rtl.clock(0)
        def bridge(s):
            spice.drive('VSAMPLE',1.8*s['sample']);spice.drive('VSAMPLEN',1.8*s['sample_n'])
            for side in ('p','n'):spice.drive('VBOTTOM'+side.upper(),.9 if s['sample'] else bottom(entries,s,side))
            for key,bit in (('VEOC','eoc'),('VEOCOSR','eoc_osr')):spice.drive(key,1.8*s[bit])
            for bit in range(16):spice.drive('VRESULT'+str(bit),1.8*((s['result']>>bit)&1))
        bridge(state);spice.advance(2e-9)
        for cycle in range(24):
            spice.drive('VCLKCOMP',0.);spice.advance(3e-9)
            spice.drive('VCLKCOMP',1.8);spice.advance(7e-9)
            q=float(spice.vector('latch_q')[-1])
            if not(q<=.18 or q>=1.62):
                spice.advance(20e-9);q=float(spice.vector('latch_q')[-1])
            if not(q<=.18 or q>=1.62):raise ValueError('transistor comparator did not resolve')
            decision=int(q>.9);state=rtl.clock(decision);bridge(state)
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
            if np.all(values>=1.62):word|=1<<bit
            elif not np.all(values<=.18):raise ValueError('unstable native bridged result bit')
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
        report=dict(energy=meter_energy,pwm_unit_ps=pwm_unit_ps,status='COUPLED_ANALOG_RTL_ADC_PARTITION_CONVERSION_PASS',
            activation_x2=acts,weights=weights.tolist(),column=column,expected_integer_sum=int(np.asarray(acts)@weights[:,column]),
            measured_input_diff_v=input_diff,result_word_16bit=word,result_code_12bit=word>>4,
            start_s=start,eoc_s=edge,start_to_eoc_s=edge-start,cycles=len(trace),trace=trace,
            capacitor_inventory=len(entries),capacitance_per_side_f=total,
            scope='Schematic CIM/S&H/conditioner and transistor ADC input TG/comparator directly coupled; '
                  'upstream SAR/decoder/OSR RTL in Icarus. CDAC C aggregation with ideal bottom drivers, '
                  'external ideal VCM/phase clock; noise-decoupling varactors omitted, comparator MOS/MIM retained. '
                  'No full transistor PEX, decoder hazards, power/noise/PVT signoff.')
        (work/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    finally:
        if not (work/'summary.json').exists():
            (work/'bridge_history.json').write_text(json.dumps(spice.hist,indent=2)+'\n')
            spice.lib.ngSpice_Command(('write '+str(work/'partial.raw')+' '+' '.join(vectors)).encode())
        rtl.close();log.close()


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--library',type=Path,required=True);p.add_argument('--case',type=Path,required=True)
    a=p.parse_args();data=json.loads(a.case.read_text())
    result=simulate(a.root,a.work,a.library,data['activation_x2'],data['weights'],data.get('column',0),pwm_unit_ps=data.get('pwm_unit_ps',50))
    print(pretty({k:v for k,v in result.items() if k!='trace'},indent=2))
