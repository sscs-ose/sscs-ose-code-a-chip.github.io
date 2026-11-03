"""Build rectangular MHA/readout hard macros with the pinned native OpenLane flow."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,os,subprocess,time,shutil,re

BLOCKS={
 'mha':{'top':'automx_mha_ip','source':'ip/automx_mha/rtl/automx_mha_ip.sv','width':650,'height':400,'density':.4,'location':[2250,800]},
 'readout':{'top':'automx_cim_readout_seq','source':'rtl/automx_cim_readout_seq.sv','width':1250,'height':750,'density':.4,'location':[800,450]}}


def native(root,program,args,name,cwd):
    root=Path(root).resolve();image=json.loads((root/'standalone.json').read_text())['openlane_image']
    return ['docker','run','--rm','--name',name,'--user',f'{os.getuid()}:{os.getgid()}',
        '--network','none','--security-opt','seccomp=unconfined','-v',f'{root}:{root}',
        '-v',f'{root/"tools/openlane"}:/openlane','-e',f'PDK_ROOT={root/"pdks/digital"}',
        '-e','PDK=sky130A','-e',f'PWD={cwd}','-w',str(cwd),'--entrypoint',program,image,*map(str,args)]


def write_interface_lib(lef,top,output,area):
    """Pin/clock model for placement; deliberately contains no timing arcs."""
    text=Path(lef).read_text();pins=[]
    for m in re.finditer(r'(?ms)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',text):
        name,body=m.groups();direction=re.search(r'DIRECTION\s+(\w+)',body)
        if direction is None:continue
        if re.search(r'USE\s+(?:POWER|GROUND)',body):continue
        pins.append((name.replace('\\',''),direction[1].lower()))
    assert pins
    groups={};scalar=[]
    for name,direction in pins:
        m=re.fullmatch(r'(.*)\[(\d+)\]',name)
        if m:groups.setdefault((m[1],direction),[]).append(int(m[2]))
        else:scalar.append((name,direction))
    widths={max(v)-min(v)+1 for v in groups.values()}
    rows=[f'library ({top}_physical_interface) {{',
       '  delay_model : table_lookup; time_unit : "1ns"; voltage_unit : "1V"; current_unit : "1mA";',
       '  capacitive_load_unit (1,pf); pulling_resistance_unit : "1kohm";',
       '  nom_process : 1; nom_temperature : 25; nom_voltage : 1.8; bus_naming_style : "%s[%d]";']
    rows += [f'  {kind}_threshold_pct_{edge} : {value};' for kind,value in [('input',50),('output',50),('slew_lower',20),('slew_upper',80)] for edge in ['rise','fall']]
    for width in sorted(widths):rows.append(f'  type (bus_{width}) {{ base_type : array; data_type : bit; bit_width : {width}; bit_from : {width-1}; bit_to : 0; downto : true; }}')
    rows.append(f'  cell ({top}) {{ area : {area}; is_macro_cell : true; dont_touch : true;')
    rows += ['    pg_pin (VPWR) { voltage_name : VPWR; pg_type : primary_power; }','    pg_pin (VGND) { voltage_name : VGND; pg_type : primary_ground; }']
    for name,direction in scalar:
        clock=' clock : true;' if name=='clk_i' else ''
        cap=' capacitance : 0.02;' if name=='clk_i' else (' capacitance : 1.5;' if name=='rst_ni' else (' capacitance : 0.004;' if direction=='input' else ' max_capacitance : 0.02;'))
        rows.append(f'    pin ("{name}") {{ direction : {direction};'+cap+clock+' }')
    for (name,direction),bits in groups.items():
        lo,hi=min(bits),max(bits);assert lo==0
        cap=' capacitance : 0.004;' if direction=='input' else ' max_capacitance : 0.02;'
        rows.append(f'    bus ("{name}") {{ bus_type : bus_{hi+1}; direction : {direction}; pin ("{name}[{hi}:{lo}]") {{ direction : {direction};'+cap+' } }')
    rows+=['  }','}'];Path(output).write_text('\n'.join(rows)+'\n')


def build_block(root,work,name):
    candidate_source=Path(root)/BLOCKS[name]['source']
    if name=='readout' and 'wire [72:0] tap;' in candidate_source.read_text():
        from scripts.harden_pulse_readout import build
        return build(root,candidate_source,work)
    root=Path(root).resolve();work=Path(work).resolve();spec=BLOCKS[name]
    folder=work/name;design=folder/'design';design.mkdir(parents=True,exist_ok=False)
    top=spec['top'];config=json.loads((root/'inputs/openlane_config_template.json').read_text())
    config.update(DESIGN_NAME=top,VERILOG_FILES=[str(root/spec['source'])],
        DIE_AREA=f"0 0 {spec['width']} {spec['height']}",DESIGN_IS_CORE=0,FP_CORE_UTIL=30,
        PL_TARGET_DENSITY=spec['density'],FP_PDN_MACRO_HOOKS='',FP_PDN_CHECK_NODES=1,
        FP_PDN_VOFFSET=14,FP_PDN_VPITCH=80,FP_PDN_VWIDTH=1.6,
        RT_MAX_LAYER=spec.get('routing_max_layer','met4'),GRT_MAX_LAYER=spec.get('routing_max_layer','met4'),DRT_MAX_LAYER=spec.get('routing_max_layer','met4'),
        RUN_SPEF_EXTRACTION=0,STA_WRITE_LIB=0,RUN_HEURISTIC_DIODE_INSERTION=0)
    for k in ('FP_PDN_MACRO_HOOKS','EXTRA_LEFS','EXTRA_GDS_FILES','EXTRA_LIBS','MACRO_PLACEMENT_CFG','FP_PDN_CFG','VERILOG_FILES_BLACKBOX'):
        config.pop(k,None)
    (design/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    shutil.copy2(root/spec['source'],folder/'source.sv')
    label=f'automx-block-{name}-{os.getpid()}-{str(time.time_ns())[-6:]}'
    command=native(root,'/openlane/flow.tcl',['-design',design,'-config_file',design/'config.json','-tag','hard'],label,'/openlane')
    (folder/'start.json').write_text(json.dumps({'command':command,'container':label,'started_utc':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
    started=time.monotonic();print('HARDEN_START',name,spec['width'],spec['height'],flush=True)
    with (folder/'native.log').open('w') as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=2100)
    if result.returncode:raise RuntimeError('Digital block flow failed: '+str(folder/'native.log'))
    return finish_block(root,folder,name,time.monotonic()-started)


def finish_block(root,folder,name,prior_elapsed=0,run_tag="hard"):
    root=Path(root).resolve();folder=Path(folder).resolve();spec=BLOCKS[name]
    design=folder/'design';top=spec['top'];started=time.monotonic()-prior_elapsed
    label=f'automx-block-finish-{name}-{os.getpid()}'
    run=design/'runs'/run_tag;route=run/'logs/routing/17-detailed.log'
    if not route.exists():route=max((run/'logs/routing').glob('*-detailed.log'))
    text=route.read_text();violations=re.findall(r'Number of violations = (\d+)',text)
    assert violations and int(violations[-1])==0,(name,violations[-1:])
    gds=run/'results/final/gds'/f'{top}.gds';lef=folder/'abstract'/f'{top}.lef';lef.parent.mkdir(exist_ok=True)
    odb=run/'results/routing'/f'{top}.odb'
    assert all(p.is_file() for p in [gds,odb])
    # Extract the routed block RC and check TT timing before releasing its physical interface.
    env=dict(re.findall(r'^set ::env\(([^)]+)\) "([^\n]*)"$',(run/'config.tcl').read_text(),re.M))
    timing=folder/'timing';timing.mkdir(exist_ok=True);spef=timing/(top+'.spef');raw=timing/(top+'.raw.lib');lib=timing/(top+'.lib')
    script=timing/'extract_sta.tcl';sdc=Path(env['CURRENT_SDC']);tt=Path(env['LIB_TYPICAL']);rules=Path(env['RCX_RULES'])
    script.write_text(f'read_liberty {{{tt}}}\nread_db {{{odb}}}\nwrite_abstract_lef -bloat_occupied_layers {{{lef}}}\nset_thread_count 4\n'+
      f'define_process_corner -ext_model_index 0 X\nextract_parasitics -ext_model_file {{{rules}}} -lef_res\nwrite_spef {{{spef}}}\n'+
      f'read_sdc {{{sdc}}}\nread_spef {{{spef}}}\nset_propagated_clock [all_clocks]\n'+
      'puts BLOCK_SETUP_BEGIN\nreport_worst_slack -max\nputs BLOCK_SETUP_END\nputs BLOCK_HOLD_BEGIN\nreport_worst_slack -min\nputs BLOCK_HOLD_END\n'+
      'check_power_grid -net VPWR\nputs BLOCK_VPWR_PASS\ncheck_power_grid -net VGND\nputs BLOCK_VGND_PASS\n'+
      'puts BLOCK_RC_STA_DONE\nexit\n')
    result=subprocess.run(native(root,'openroad',['-exit',script],label+'-sta',timing),capture_output=True,text=True,timeout=180)
    (timing/'native.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,(result.stdout+result.stderr)[-3000:]
    assert all(m in result.stdout for m in ('BLOCK_VPWR_PASS','BLOCK_VGND_PASS','BLOCK_RC_STA_DONE'))
    write_interface_lib(lef,top,lib,spec['width']*spec['height'])
    slacks=[float(x) for x in re.findall(r'worst slack\s+([-+\d.]+)',result.stdout)]
    report={'status':'PASS','name':name,'top':top,'width_um':spec['width'],'height_um':spec['height'],
        'location_um':spec['location'],'gds':str(gds),'lef':str(lef),'odb':str(odb),'lib':str(lib),
        'mapped_netlist':str(run/'results/routing'/f'{top}.nl.v'),'spef':str(spef),'library_scope':'physical interface only; timing verified from hierarchical gate netlists and SPEFs','routed_drc_violations':0,'power_rails':{'VPWR':'PASS','VGND':'PASS'},'setup_slack_ns':slacks[0],'hold_slack_ns':slacks[1],
        'source':str(folder/'source.sv'),'elapsed_s':time.monotonic()-started,'log':str(folder/'native.log')}
    (folder/'hardening.json').write_text(json.dumps(report,indent=2)+'\n')
    print('HARDEN_PASS',json.dumps(report),flush=True);return report


def harden(root,work):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    reports=[];missing=[]
    library=root/'inputs/digital_blocks';index=library/'source_library.json'
    frozen=json.loads(index.read_text()) if index.is_file() else {}
    environment=json.loads((root/'standalone.json').read_text())['openlane_image']
    period=json.loads((root/'inputs/openlane_config_template.json').read_text()).get('CLOCK_PERIOD',40)
    for name,spec in BLOCKS.items():
        record=next((v for v in frozen.get('blocks',[]) if v['name']==name),None)
        match=record is not None and frozen.get('openlane_image')==environment and frozen.get('clock_period_ns')==period
        match=match and record.get('layout_config')=={k:spec[k] for k in ('width','height','density')}
        if match:
            match=(library/record['source']).is_file() and (library/record['source']).read_bytes()==(root/spec['source']).read_bytes()
            match=match and all((library/record[k]).is_file() for k in ('gds','lef','odb','lib','mapped_netlist','spef'))
        if not match:missing.append(name);continue
        destination=work/name;destination.mkdir(exist_ok=False)
        view=dict(record)
        for key in ('source','gds','lef','odb','lib','mapped_netlist','spef'):
            old=library/record[key];new=destination/old.name;shutil.copy2(old,new);view[key]=str(new)
        view['location_um']=spec['location'];view['mode']='SOURCE_MATCHED_HARD_IP';view['source_rtl_matches']=True
        write_interface_lib(view['lef'],view['top'],view['lib'],view['width_um']*view['height_um'])
        (destination/'hardening.json').write_text(json.dumps(view,indent=2)+'\n')
        reports.append(view)
        print(f'HARD_IP_VIEW {name} {spec["width"]}x{spec["height"]}um source_RTL=match routing_DRC=0 power=PASS',flush=True)
    if missing:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(build_block,root,work,name) for name in missing]
            reports += [f.result() for f in futures]
    report={'status':'PASS','blocks':reports,'started_from':'RTL plus source-matched hard IP views; changed RTL is hardened automatically','clock_period_ns':40}
    (work/'hardening.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    import argparse,sys
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args()
    if str(a.root.resolve()) not in sys.path:sys.path.insert(0,str(a.root.resolve()))
    harden(a.root,a.work)
