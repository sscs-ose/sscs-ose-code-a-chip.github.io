"""Measure routed PWM cones with SKY130 transistor cells, SPEF RC and CIM PEX loading."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,csv,json,re,subprocess,time,sys
import numpy as np


def clean(value):return value.strip().replace('\\','')

def structural(path):
    cells={};drivers={}
    for model,name,body in re.findall(r'(sky130_fd_sc_hd__\w+)\s+(\\?\S+)\s*\((.*?)\);',Path(path).read_text(),re.S):
        pins={p:clean(n) for p,n in re.findall(r'\.(\w+)\s*\(([^()]*)\)',body)};name=clean(name)
        cells[name]={'model':model,'pins':pins}
        for pin in ('X','Y','Q','Q_N','GCLK','HI','LO'):
            if pin in pins:drivers[pins[pin]]=(name,pin)
    assert cells and drivers;return cells,drivers


def spef(path):
    names={};nets={};cur=None;section=None;mapping=False
    def expand(s):
        if not s.startswith('*'):return clean(s)
        m=re.match(r'\*(\d+)(.*)',s);return clean(names[int(m[1])]+m[2])
    for line in Path(path).read_text().splitlines():
        f=line.split()
        if not f:continue
        if f[0]=='*NAME_MAP':mapping=True;continue
        if f[0] in ('*PORTS','*D_NET'):mapping=False
        if mapping and re.fullmatch(r'\*\d+',f[0]):names[int(f[0][1:])]=' '.join(f[1:]);continue
        if f[0]=='*D_NET':cur={'name':expand(f[1]),'conn':[],'caps':[],'res':[]};nets[cur['name']]=cur;section=None;continue
        if f[0]=='*END':cur=None;continue
        if not cur:continue
        if f[0] in ('*CONN','*CAP','*RES'):section=f[0];continue
        if section=='*CONN' and f[0] in ('*P','*I'):cur['conn'].append((expand(f[1]),f[2]))
        elif section=='*CAP' and f[0].isdigit():cur['caps'].append((expand(f[1]),expand(f[2]) if len(f)==4 else '0',float(f[-1])*1e-12))
        elif section=='*RES' and f[0].isdigit():cur['res'].append((expand(f[1]),expand(f[2]),float(f[3])))
    return nets


def subcircuits(path):
    text=Path(path).read_text();out={}
    for m in re.finditer(r'(?im)^\.subckt\s+(\S+)\s+([^\n]+)\n(.*?)^\.ends[^\n]*',text,re.S|re.M):
        out[m[1]]=(m[2].split(),m[0])
    return out


def pin_caps(path):
    text=Path(path).read_text();result={}
    for block in re.split(r'\n\s*cell\s*\(',text)[1:]:
        model=block.split(')',1)[0].strip('" ')
        for pin,part in re.findall(r'pin\s*\(\s*"?([\w]+)"?\s*\)\s*\{(.*?)(?=\n\s*pin\s*\(|\Z)',block,re.S):
            if not re.search(r'direction\s*:\s*"?input',part):continue
            cap=re.search(r'(?m)^\s*capacitance\s*:\s*([\deE.+-]+)',part)
            if cap:result[(model,pin)]=float(cap[1])*1e-12
    return result


def prepare(root,readout,parent,work,rc_model="distributed",core_views=None):
    root=Path(root).resolve();readout=Path(readout).resolve();parent=Path(parent).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    netlist=next(readout.glob('*.nl.v'));rc=next(readout.glob('*.spef'))
    cells,drivers=structural(netlist);nets=spef(rc);parent_nets=spef(parent)
    parent_netlist=parent.parent.parent/'cold_pnr/design/runs/cold/results/routing/automx_cim_mixed_signal_proto.nl.v'
    parent_cells,_=structural(parent_netlist)
    std=root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd';subs=subcircuits(std/'spice/sky130_fd_sc_hd.spice')
    caps=pin_caps(std/'lib/sky130_fd_sc_hd__tt_025C_1v80.lib')
    outputs=[f'{p}_o[{i}]' for p in ('wlp','wln') for i in range(4)]
    static=set([f'acts[{i}]' for i in range(20)]+['phase_b','rst_ni','clk_i'])
    dynamic={'launch',*[f'state[{i}]' for i in range(5)]};selected=set();boundary=set();used_nets=set();d_sources={};clock_sources={}
    def visit(net):
        if net in used_nets:return
        used_nets.add(net)
        if net in static:boundary.add(net);return
        if net not in drivers:raise ValueError('Unresolved cone input '+net)
        inst,pin=drivers[net];cell=cells[inst]
        if pin in ('Q','Q_N') and net not in dynamic and 'launch_local' not in net:boundary.add(net);return
        selected.add(inst)
        for p,n in cell['pins'].items():
            if p in ('X','Y','Q','Q_N','GCLK','HI','LO'):continue
            if pin in ('Q','Q_N') and p=='D':d_sources[(inst,p)]=net;continue
            if pin in ('Q','Q_N') and p=='CLK':clock_sources[(inst,p)]=net;continue
            visit(n)
    for o in outputs:visit(o)
    aliases={};counter=[0]
    def node(name):
        if name=='0':return '0'
        if name not in aliases:counter[0]+=1;aliases[name]=f'n{counter[0]}'
        return aliases[name]
    def endpoint(net,inst=None,pin=None):
        if net in nets:
            if inst is not None:
                wanted=inst+':'+pin
                if any(c==wanted for c,_ in nets[net]['conn']):return node(wanted)
            if inst is None and any(c==net for c,_ in nets[net]['conn']):return node(net)
        return node(net)
    lines=[];active_sections=[]
    for net in used_nets:
        if net in nets:active_sections.append(('child',nets[net]))
    parent_links={};parent_selected=set();parent_sections={}
    parent_conn={c:s for s in parent_nets.values() for c,_ in s['conn']}
    def parent_path(conn,port):
        s=parent_conn[conn];parent_sections[s['name']]=s
        ds=[c for c,d in s['conn'] if d=='O'];assert len(ds)==1,(s['name'],ds)
        driver=ds[0]
        if driver=='seq_i:'+port:
            return
        inst,pin=driver.rsplit(':',1);cell=parent_cells[inst];parent_selected.add(inst)
        for p in cell['pins']:
            if p not in ('X','Y','Q','Q_N','GCLK','HI','LO'):parent_path(inst+':'+p,port)
    for port in outputs:
        found=[s for s in parent_nets.values() if any(c=='seq_i:'+port for c,_ in s['conn'])]
        assert len(found)==1,(port,len(found));s=found[0]
        physical='WL'+('P' if port.startswith('wlp') else 'N')+re.search(r'\[(\d+)\]',port)[1]
        corepin='core_i:'+physical
        parent_path(corepin,port)
        parent_links[physical]='parent:'+corepin
        lines.append(f'RJ_{physical} {endpoint(port)} {node("parent:seq_i:"+port)} .001')
    active_sections.extend(('parent',s) for s in parent_sections.values())
    active_nodes={'0'}
    for prefix,s in active_sections:
        def qualify(x):return x if prefix=='child' or x=='0' else 'parent:'+x
        active_nodes.update(qualify(x) for x,_ in s['conn'])
        active_nodes.update(qualify(x) for a,b,_ in s['res'] for x in (a,b))
    cap_seen={};counts={'rc_resistors':0,'wire_capacitors':0,'excluded_pin_loads':0}
    for prefix,s in active_sections:
        qualify=lambda x:x if prefix=='child' or x=='0' else 'parent:'+x
        assert rc_model=='distributed'
        for a,b,v in (s['res'] if rc_model=='distributed' else []):
            counts['rc_resistors']+=1;lines.append(f'RW{counts["rc_resistors"]} {node(qualify(a))} {node(qualify(b))} {max(v,.001):.12g}')
        for a,b,v in (s['caps'] if rc_model=='distributed' else []):
            a,b=qualify(a),qualify(b)
            if v<=0:continue
            key=tuple(sorted((a,b)))
            if b!='0' and key in cap_seen and cap_seen[key]!=(prefix,s['name']):continue
            cap_seen[key]=(prefix,s['name'])
            if a not in active_nodes:a='0'
            if b not in active_nodes:b='0'
            if a==b:continue
            counts['wire_capacitors']+=1;lines.append(f'CW{counts["wire_capacitors"]} {node(a)} {node(b)} {v:.12g}')
        if prefix=='child':
            for conn,direction in s['conn']:
                if direction!='I' or ':' not in conn:continue
                inst,pin=conn.rsplit(':',1)
                if inst in selected or inst not in cells:continue
                value=caps.get((cells[inst]['model'],pin),0)
                if value:
                    counts['excluded_pin_loads']+=1;lines.append(f'CP{counts["excluded_pin_loads"]} {node(conn)} 0 {value:.12g}')
        else:
            for conn,direction in s['conn']:
                if direction!='I' or ':' not in conn:continue
                inst,pin=conn.rsplit(':',1)
                if inst in parent_selected or inst not in parent_cells:continue
                value=caps.get((parent_cells[inst]['model'],pin),0)
                if value:
                    counts['excluded_pin_loads']+=1;lines.append(f'CP{counts["excluded_pin_loads"]} {node("parent:"+conn)} 0 {value:.12g}')
    source_nodes={}
    for net in boundary:
        if net in drivers:inst,pin=drivers[net];n=endpoint(net,inst,pin)
        else:n=endpoint(net)
        source_nodes[net]=n
    ff_names=sorted({inst for inst,pin in clock_sources})
    sta=work/'clock_boundary.tcl';library=std/'lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    sta.write_text(f'read_liberty {{{library}}}\nread_verilog {{{netlist}}}\nlink_design automx_cim_readout_seq\ncreate_clock -name clk -period 40 [get_ports clk_i]\nread_spef {{{rc}}}\nset_input_transition .1 [all_inputs]\nset_load .004 [all_outputs]\nset_output_delay 0 -clock clk [all_outputs]\nset_propagated_clock [all_clocks]\n'+''.join(f'puts "CLOCK_BOUNDARY {ff}"\nreport_checks -from [get_pins {{{ff}/Q}}] -to [all_outputs] -group_count 1 -format full_clock_expanded -fields {{slew}} -digits 6\n' for ff in ff_names)+'exit\n')
    from scripts.standalone_runtime import container
    q=subprocess.run(container(root,'sta',['-exit',sta],'automx-pwm-clock-'+str(__import__('os').getpid()),work),capture_output=True,text=True,timeout=120)
    (work/'clock_boundary.log').write_text(q.stdout+q.stderr);assert q.returncode==0
    clock_timing={}
    for ff in ff_names:
        matches=[line for line in q.stdout.splitlines() if ff+'/CLK' in line]
        assert matches,('Missing propagated clock boundary',ff)
        prefix=matches[0].split(ff+'/CLK',1)[0];values=list(map(float,re.findall(r'[-+]?\d+\.\d+',prefix)))
        assert len(values)>=3,(ff,matches[0]);clock_timing[ff]={'slew_ns':values[0],'arrival_ns':values[-1]}
    for i,inst in enumerate(sorted(selected)):
        cell=cells[inst];ports=subs[cell['model']][0];pins=[]
        for pin in ports:
            if pin in ('VPWR','VPB'):pins.append('VPWR');continue
            if pin in ('VGND','VNB'):pins.append('0');continue
            net=cell['pins'][pin]
            if (inst,pin) in d_sources:
                key='D_'+d_sources[(inst,pin)];n=node(key);source_nodes[key]=n
            elif (inst,pin) in clock_sources:
                key='CLK_'+inst;n=node(key);source_nodes[key]=n
            else:n=endpoint(net,inst,pin)
            pins.append(n)
        lines.append(f'XG{i} '+ ' '.join(pins)+' '+cell['model'])
    for i,inst in enumerate(sorted(parent_selected)):
        cell=parent_cells[inst];ports=subs[cell['model']][0];pins=[]
        for pin in ports:
            pins.append('VPWR' if pin in ('VPWR','VPB') else ('0' if pin in ('VGND','VNB') else node('parent:'+inst+':'+pin)))
        lines.append(f'XP{i} '+' '.join(pins)+' '+cell['model'])
    model_names={cells[i]['model'] for i in selected}|{parent_cells[i]['model'] for i in parent_selected}
    modeltext='\n'.join(subs[m][1] for m in sorted(model_names))
    (work/'cone_cells.spice').write_text(modeltext+'\n');(work/'cone_network.spice').write_text('\n'.join(lines)+'\n')
    debug={n:endpoint(n,*drivers[n]) for n in ['launch',*[f'state[{i}]' for i in range(5)],'tap[1]','tap[12]','wlp_o[0]'] if n in drivers and drivers[n][0] in selected}
    info={'debug_nodes':debug,'status':'PREPARED','rc_model':rc_model,'readout_netlist':str(netlist),'child_spef':str(rc),'parent_spef':str(parent),'cell_count':len(selected),'parent_buffer_count':len(parent_selected),'models':sorted(model_names),**counts,'source_nodes':source_nodes,'clock_timing':clock_timing,'output_nodes':{k:node(v) for k,v in parent_links.items()},'aliases':aliases,
       'scope':'Transistor mapped pulse cone and launch/state FFs with routed child/parent RC, actual CIM/acquisition PEX input load, Liberty input-cap loads on excluded fanouts. Quiet excluded coupling neighbors are grounded. FF clock-boundary arrival and slew are measured with propagated extracted-RC STA; no supply-grid/noise signoff.'}
    (work/'cone.json').write_text(json.dumps(info,indent=2)+'\n');return info


def deck(root,work,info,row,negative,magnitude,corner='tt',temperature=25,supply=1.8):
    root=Path(root);work=Path(work);v=supply;acts=[0]*4;acts[row]=-magnitude if negative else magnitude;ns=info['source_nodes'];lines=['Routed PWM driver with physical CIM PEX loading',f'.lib "{root}/pdks/analog/sky130A/libs.tech/ngspice/sky130.lib.spice" {corner}',f'.param mc_mm_switch=0','.option klu method=gear reltol=1e-3 abstol=1e-12 rshunt=1e12',f'.temp {temperature}',f'VVDD VPWR 0 {v}',f'.include "{work}/cone_cells.spice"',f'.include "{work}/cone_network.spice"',f'.include "{info.get("core_pex",root/"inputs/core_acquisition.pex.spice")}"',f'.include "{root}/inputs/conditioner.spice"']
    def source(name,n,value):lines.append(f'V{name} {n} 0 {value}')
    for net,n in ns.items():
        if net.startswith('CLK_'):
            timing=info['clock_timing'][net[4:]];delay=timing['arrival_ns'];edge=max(timing['slew_ns'],.005)/.6
            value=f'PWL(0 0 {.2+delay-edge/2}n 0 {.2+delay+edge/2}n {v} {2+delay-edge/2}n {v} {2+delay+edge/2}n 0 {5+delay-edge/2}n 0 {5+delay+edge/2}n {v} 20n {v})'
        elif net=='clk_i':value='0'
        elif net=='rst_ni':value=f'PWL(0 0 .05n 0 .1n {v} 20n {v})'
        elif net=='phase_b':value=str(v if row>=2 else 0)
        elif net.startswith('acts['):
            bit=int(re.search(r'\[(\d+)\]',net)[1]);value=str(v if ((acts[bit//5]&31)>>(bit%5))&1 else 0)
        elif net.startswith('D_'):
            name=net[2:]
            old=0 if name=='launch' or 'launch_local' in name else (3>>int(re.search(r'\[(\d+)\]',name)[1]))&1
            new=1 if name=='launch' or 'launch_local' in name else (4>>int(re.search(r'\[(\d+)\]',name)[1]))&1
            value=f'PWL(0 {v*old} 4n {v*old} 4.1n {v*new} 20n {v*new})'
        else:raise ValueError(net)
        source('B'+str(len(lines)),n,value)
    from scripts.flow2_adc_partition import ports
    from scripts.run_flow2_core_acquisition import PINS,CELL
    mapping={'VPWR':'VPWR','VGND':'0','PRE_B':'PRE_B','TRACK':'TRACK'}
    for pin,n in info['output_nodes'].items():mapping[pin]=n
    source('PRE','PRE_B',f'PWL(0 0 2n 0 2.1n {v} 20n {v})');source('TRACK','TRACK',str(v))
    for pin in PINS:
        if pin.startswith(('WPOS','WNEG')):mapping[pin]='VPWR' if pin.startswith('WPOS') else '0'
    lines.append('XCORE '+' '.join(mapping.get(p,p) for p in PINS)+' '+CELL+'_pex')
    cond='automx_cim_condition_mux_proto';cp=ports((root/'inputs/conditioner.spice').read_text(),cond)
    lines.append('XCOND '+' '.join('VPWR' if p=='VPWR' else ('0' if p=='VGND' or p.startswith('SEL') else p) for p in cp)+' '+cond)
    probes=['time',*[f'v({n})' for n in [*info['output_nodes'].values(),*info.get('debug_nodes',{}).values(),'BLP0','BLN0','HP0','HN0']]]
    lines+=['.save '+' '.join(probes[1:]),'.control','set filetype=ascii','tran 10p 20n 0 100p','write pulse.raw '+' '.join(probes),'.endc','.end','']
    return '\n'.join(lines)


def run(root,readout,parent,work,jobs=4,pilot=False,rc_model="distributed",core_views=None):
    root=Path(root).resolve();work=Path(work).resolve();readout=Path(readout).resolve();parent=Path(parent).resolve()
    snapshots=work/'declared_inputs';snapshots.mkdir(parents=True,exist_ok=True)
    core=Path(core_views).resolve() if core_views else root/'inputs'
    loading=core/'core_acquisition.grouped.pex.spice'
    if not loading.is_file():loading=core/'core_acquisition.fast.pex.spice'
    if not loading.is_file():loading=core/'core_acquisition.pex.spice'
    for label,path in [('readout.v',next(readout.glob('*.nl.v'))),('child.spef',next(readout.glob('*.spef'))),('parent.spef',parent),('core_pex.spice',loading),('conditioner.spice',root/'inputs/conditioner.spice'),('measurement_source.py',Path(__file__).resolve())]:
        target=snapshots/label
        if target.exists():assert target.read_bytes()==path.read_bytes(),('Measurement input changed; use an empty work directory',label)
        else:__import__('shutil').copy2(path,target)
    info=prepare(root,readout,parent,work,rc_model)
    info['core_pex']=str(loading)
    (work/'cone.json').write_text(json.dumps(info,indent=2)+'\n')
    requests=[(r,s,m) for r in range(4) for s in (False,True) for m in (0,1,2,3,4,6,8,12)]
    if pilot:requests=[(0,False,m) for m in (0,1,2,4,8,12)]
    from scripts.flow2_waveforms import read_raw
    def measure(case):
        row,neg,mag=case;folder=work/f'row{row}_{"n" if neg else "p"}_{mag}'
        if (folder/'measured.json').is_file():return json.loads((folder/'measured.json').read_text())
        folder.mkdir(exist_ok=True);(folder/'pulse.spice').write_text(deck(root,work,info,*case))
        if (folder/'pulse.raw').exists():(folder/'pulse.raw').unlink()
        start=time.monotonic()
        with (folder/'ngspice.log').open('w') as stream:q=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(folder),'--library',str(root/'tools/ngspice/libngspice.so')],cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
        if q.returncode:raise RuntimeError(str(folder)+': '+(folder/'ngspice.log').read_text()[-1500:])
        raw=read_raw(folder/'pulse.raw');t=raw['time'];name='WL'+('N' if neg else 'P')+str(row);values=raw['v('+info['output_nodes'][name].lower()+')'];mask=t>4e-9;high=(values>.9)&mask
        indices=np.flatnonzero(np.diff(high.astype(int)));edges=[]
        for i in indices:
            if t[i]<4e-9:continue
            edges.append(float(t[i]+(.9-values[i])*(t[i+1]-t[i])/(values[i+1]-values[i])))
        width=edges[1]-edges[0] if len(edges)>=2 else 0.
        down=np.flatnonzero((t>4e-9)&(t<20e-9));chosen={int(down[0]),int(down[-1])};pending=[(int(down[0]),int(down[-1]))]
        while pending:
            a,b=pending.pop()
            if b<=a+1:continue
            linear=values[a]+(values[b]-values[a])*(t[a+1:b]-t[a])/(t[b]-t[a])
            error=np.abs(values[a+1:b]-linear);i=a+1+int(error.argmax())
            if float(error.max())>.002:chosen.add(i);pending.extend([(a,i),(i,b)])
        selected=np.array(sorted(chosen));reduction_error=float(np.max(np.abs(np.interp(t[down],t[selected],values[selected])-values[down])))
        assert reduction_error<=.002000001
        other_peak=max(float(raw['v('+n.lower()+')'][mask].max()) for pin,n in info['output_nodes'].items() if pin!=name)
        differential=raw['v(bln0)']-raw['v(blp0)']
        delta=float(np.interp(19e-9,t,differential)-np.interp(4e-9,t,differential))
        result={'row':row,'negative':neg,'magnitude':mag,'width_ps':width*1e12,'peak_v':float(values[mask].max()),'rising_edges':int(sum(np.diff(high.astype(int))==1)),
            'other_wordline_peak_v':other_peak,'bitline_differential_change_v':delta,
            'held_differential_v':float(np.interp(19e-9,t,raw['v(hn0)']-raw['v(hp0)'])),
            'debug_peaks':{k:float(raw['v('+v.lower()+')'][mask].max()) for k,v in info.get('debug_nodes',{}).items()},'elapsed_s':time.monotonic()-start,'folder':str(folder),'waveform_max_error_v':reduction_error,'waveform':{'time_ns':(t[selected]*1e9-5).tolist(),'voltage_v':values[selected].tolist()}}
        (folder/'measured.json').write_text(json.dumps(result,indent=2)+'\n');print('PHYSICAL_PWM',row,int(neg),mag,f'{width*1e12:.2f}ps',f'peak={values[mask].max():.3f}V',flush=True);return result
    with ThreadPoolExecutor(max_workers=jobs) as pool:rows=list(pool.map(measure,requests))
    ordered=[];charge_order=[]
    for row,neg in sorted({(r['row'],r['negative']) for r in rows}):
        points=sorted((r for r in rows if r['row']==row and r['negative']==neg),key=lambda r:r['magnitude'])
        ordered.append(all(b['width_ps']>a['width_ps'] for a,b in zip(points,points[1:])))
        charge_order.append(all(abs(b['bitline_differential_change_v'])>abs(a['bitline_differential_change_v']) for a,b in zip(points,points[1:])))
    result={'status':'MEASURED','scope':info['scope'],'rc_model':rc_model,'cone':{k:v for k,v in info.items() if k not in ('aliases','source_nodes')},'measurements':rows,
        'zero_code_ok':all(r['peak_v']<.18 and r['other_wordline_peak_v']<.18 for r in rows if r['magnitude']==0),
        'nonzero_full_swing':all(r['width_ps']>0 and r['peak_v']>1.62 for r in rows if r['magnitude']>0),
        'single_pulse_ok':all(r['rising_edges']==int(r['magnitude']>0) for r in rows),
        'unselected_lines_quiet':all(r['other_wordline_peak_v']<.18 for r in rows),
        'strict_width_order':all(ordered),
        'strict_bitline_order':all(charge_order),
        'bitline_polarity_ok':all((-1 if r['negative'] else 1)*r['bitline_differential_change_v']>0 for r in rows if r['magnitude']>0)}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('PHYSICAL_PWM_COMPLETE',result['zero_code_ok'],result['nonzero_full_swing'],flush=True);return result

def spice_worker(folder,library,max_step_ps=100,reltol=1e-3):
    from scripts.portable_cim_sar import SharedSpice
    folder=Path(folder).resolve();text=(folder/'pulse.spice').read_text().replace('reltol=1e-3',f'reltol={reltol}')
    control=text.split('.control',1)[1]
    probes=re.search(r'write pulse.raw (.*?)\n',control)[1]
    (folder/'worker.spice').write_text(text.split('.control',1)[0]+'.end\n')
    with (folder/'shared_ngspice.log').open('w') as log:
        spice=SharedSpice(library,log)
        for cmd in ('set ngbehavior=hsa','set skywaterpdk','set num_threads=1','set noinit'):
            spice.command(cmd)
        spice.command('version');spice.command('source '+str(folder/'worker.spice'));spice.command('option klu')
        spice.command(f'tran 10p 20n 0 {max_step_ps}p')
        spice.command('set filetype=ascii')
        spice.command('write '+str(folder/'pulse.raw')+' '+probes)
        assert (folder/'pulse.raw').is_file(), 'ngspice did not write the requested vectors'
        assert spice.vector('time')[-1]>=19.99e-9
        spice.command('destroy all')

if __name__=='__main__':
    if '--worker' in sys.argv:
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]));spice_worker(sys.argv[sys.argv.index('--worker')+1],sys.argv[sys.argv.index('--library')+1],float(sys.argv[sys.argv.index('--max-step-ps')+1]) if '--max-step-ps' in sys.argv else 100,float(sys.argv[sys.argv.index('--reltol')+1]) if '--reltol' in sys.argv else 1e-3);sys.exit(0)
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--readout',type=Path,required=True);p.add_argument('--parent',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--jobs',type=int,default=4);p.add_argument('--pilot',action='store_true');p.add_argument('--rc-model',choices=['distributed'],default='distributed');p.add_argument('--core-views',type=Path);a=p.parse_args();run(a.root,a.readout,a.parent,a.work,a.jobs,a.pilot,a.rc_model,a.core_views)
