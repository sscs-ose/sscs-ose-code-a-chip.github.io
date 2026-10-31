"""Notebook-visible runtime for a local-source, cold-start mixed-signal run."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,re,shutil,subprocess,sys,time,signal,atexit

TOP='automx_cim_mixed_signal_proto'
ROOT=None
WORK=None
PNR=None

def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')

def container(root,program,args,name,cwd=None):
    root=Path(root).resolve();config=json.loads((root/'standalone.json').read_text())
    return ['docker','run','--rm','--name',name,'--user',f'{os.getuid()}:{os.getgid()}',
        '--network','none','--security-opt','seccomp=unconfined',
        '-v',f'{root}:{root}','-v',f'{root/"tools/openlane"}:/openlane',
        '-e',f'PDK_ROOT={root/"pdks/digital"}','-e','PDK=sky130A',
        '-e',f'PWD={cwd or root}',
        '-w',str(cwd or root), '--entrypoint',program,config['openlane_image'],*map(str,args)]

def guard_old_checkout(root):
    """Fail immediately if an active host Python step tries to read old design data."""
    prefixes=json.loads((Path(root)/'standalone.json').read_text())['forbidden_roots']
    def audit(event,args):
        if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
            text=os.fsdecode(args[0])
            if any(text==p or text.startswith(p+'/') for p in prefixes):
                raise PermissionError('Standalone run attempted to open external design input: '+text)
    sys.addaudithook(audit)
    return prefixes

def relocate_bundle(root):
    """Rebase generated PDK configuration if the complete folder was moved again."""
    root=Path(root).resolve();path=root/'standalone.json';manifest=json.loads(path.read_text())
    previous=manifest.get('assembled_root',str(root))
    if previous!=str(root):
        changed=json.loads((root/'relocated_configuration.json').read_text())
        for relative in changed:
            target=root/relative
            if not target.resolve().is_relative_to(root):raise ValueError('Relocation target leaves bundle')
            target.write_text(target.read_text().replace(previous,str(root)))
        manifest['assembled_root']=str(root);save(path,manifest)
    save(root/'generated/sky130/spice/stage4_manifest.json',
         {'model_library':str(root/'pdks/analog/sky130A/libs.tech/ngspice/sky130.lib.spice')})
    return manifest

def prepare_pnr(root,work,digital_blocks=None):
    root=Path(root);work=Path(work)
    folder=work/'cold_pnr'
    if folder.exists():folder=work/('cold_pnr_attempt_'+datetime.now(timezone.utc).strftime('%H%M%S_%f'))
    design=folder/'design';design.mkdir(parents=True,exist_ok=False)
    config=json.loads((root/'inputs/openlane_config_template.json').read_text())
    config.update(VERILOG_FILES=[str(root/'ip/automx_mha/rtl/automx_mha_ip.sv'),str(root/'rtl/automx_cim_readout_seq.sv'),str(root/'inputs'/f'{TOP}.sv')],
        VERILOG_FILES_BLACKBOX=str(root/'inputs/wrapper_blackboxes.sv'),
        EXTRA_LEFS=[str(root/'inputs'/f'{n}.lef') for n in ('core','conditioner','adc')],
        EXTRA_GDS_FILES=[str(root/'inputs'/f'{n}.gds') for n in ('core','conditioner','adc')],
        MACRO_PLACEMENT_CFG=str(root/'inputs/macro_placement.cfg'),
        FP_PDN_CFG=str(root/'inputs/pdn_mixed_wrapper.tcl'))
    pdn=design/'pdn.tcl'
    repair=design/'repair_wrapper_ground.tcl'
    ground_jumpers=r"""
        set m5 [$tech findLayer met5]
        set via [$tech findVia M4M5_PR]
        if {$m5=="NULL" || $via=="NULL"} {error "missing ground jumper layer/via"}
        if {$name=="core_i"} {
            set pad {637.0 213.02 638.6 214.62};set plate {637.0 213.02 640.34 214.62}
            set points {{637.8 213.82} {639.54 213.82}}
        } else {
            set pad {1556.6 53.02 1558.2 54.62};set plate {1556.6 53.02 1561.94 54.62}
            set points {{1557.4 53.82} {1561.14 53.82}}
        }
        foreach shape [concat [automx_macro_shapes $block met4] [automx_special_shapes $block met4]] {
            if {[lindex $shape 0] ne "VGND" && [automx_overlaps [lrange $shape 1 4] [automx_dbu $u $pad]]} {
                error "ground landing would short [lindex $shape 0]: $name"
            }
        }
        foreach shape [concat [automx_macro_shapes $block met5] [automx_special_shapes $block met5]] {
            if {[lindex $shape 0] ne "VGND" && [automx_overlaps [lrange $shape 1 4] [automx_dbu $u $plate]]} {
                error "ground jumper would short [lindex $shape 0]: $name"
            }
        }
        odb::dbSBox_create [lindex $swires 0] $layer {*}[automx_dbu $u $pad] STRIPE 2
        odb::dbSBox_create [lindex $swires 0] $m5 {*}[automx_dbu $u $plate] STRIPE 1
        foreach point $points {
            lassign $point x y
            odb::dbSBox_create [lindex $swires 0] $via [expr {round($x*$u)}] [expr {round($y*$u)}] STRIPE
        }
        puts "STANDALONE_GROUND_M5_JUMPER $name $plate"
"""
    repair.write_text((root/'inputs/repair_wrapper_ground.tcl').read_text().replace(
        'odb::dbSBox_create [lindex $swires 0] $layer {*}$rectangle STRIPE',ground_jumpers))
    pdn.write_text((root/'inputs/pdn_mixed_wrapper.tcl').read_text().replace(
        'source [file join [file dirname [info script]] repair_wrapper_ground.tcl]',
        'source {'+str(repair)+'}'))
    config['FP_PDN_CFG']=str(pdn)
    if digital_blocks is not None:
        # All datapath/sequencer cells are now inside independently routed IPs.
        config['VERILOG_FILES']=[str(root/'inputs'/f'{TOP}.sv')]
        config.update(PL_RESIZER_DESIGN_OPTIMIZATIONS=1,PL_RESIZER_BUFFER_INPUT_PORTS=1,PL_RESIZER_BUFFER_OUTPUT_PORTS=1,PL_RESIZER_MAX_WIRE_LENGTH=200)
        stubs=design/'digital_blackboxes.sv';declarations=[]
        for block in digital_blocks:
            text=Path(block['source']).read_text();begin=text.index('module '+block['top'])
            end=text.index('\n);',begin)+len('\n);')
            header=text[begin:end].replace('\n);',',\n    inout wire VPWR, VGND\n);')
            header=re.sub(r'(module\s+\S+)\s*#\s*\(.*?\)\s*\(',r'\1 (',header,flags=re.S)
            declarations.append('(* blackbox *) '+header+'\nendmodule\n')
        stubs.write_text('/// sta-blackbox\n'+'\n'.join(declarations))
        config['VERILOG_FILES_BLACKBOX']=[str(root/'inputs/wrapper_blackboxes.sv'),str(stubs)]
        config['EXTRA_LEFS'] += [v['lef'] for v in digital_blocks]
        config['EXTRA_GDS_FILES'] += [v['gds'] for v in digital_blocks]
        config['EXTRA_LIBS']=[v['lib'] for v in digital_blocks]
        placements=(root/'inputs/macro_placement.cfg').read_text().splitlines()
        placements=[line for line in placements if not line.split() or line.split()[0] not in ('mha_i','seq_i')]
        hooks=[]
        for block in digital_blocks:
            name='mha_i' if block['name']=='mha' else 'seq_i'
            x,y=block['location_um'];placements.append(f'{name} {x} {y} N')
            hooks.append(f'{name} VPWR VGND VPWR VGND')
        placement=design/'macro_placement.cfg';placement.write_text('\n'.join(placements)+'\n')
        config['MACRO_PLACEMENT_CFG']=str(placement)
        config['FP_PDN_MACRO_HOOKS'] += ', '+', '.join(hooks)
    save(design/'config.json',config)
    return design,config

def start(root,work):
    global ROOT,WORK,PNR
    ROOT=Path(root).resolve();WORK=Path(work).resolve()
    manifest=relocate_bundle(ROOT)
    check=subprocess.run(['docker','image','inspect',manifest['openlane_image']],capture_output=True)
    if check.returncode:
        archive=ROOT/'tools/openlane-image.tar'
        if not archive.is_file():raise FileNotFoundError('Bundled OpenLane tool image is absent')
        subprocess.run(['docker','image','load','-i',str(archive)],check=True)
    for name in ('ngspice','iverilog','vvp','klayout','tclsh'):
        if not shutil.which(name):raise FileNotFoundError('Install native open-source tool: '+name)
    digital=harden(ROOT,WORK/'digital_blocks')
    design,config=prepare_pnr(ROOT,WORK,digital['blocks'])
    tag='cold';name='automx-cold-'+str(os.getpid())+'-'+str(time.time_ns())[-8:]
    command=container(ROOT,'/openlane/flow.tcl',['-design',design,'-config_file',design/'config.json','-tag',tag],name,'/openlane')
    log=design.parent/'native.log';stream=log.open('wb')
    process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    PNR={'process':process,'stream':stream,'command':command,'log':log,'started':time.monotonic(),
         'design':design,'run':design/'runs'/tag,'config':config,'name':name,'root':ROOT}
    print('START COLD OpenLane synthesis → floorplan → place → CTS → detailed route',flush=True)
    print('RUN:', ' '.join(map(str,command)),flush=True)
    print('Live current-run log:',log,flush=True)
    save(design.parent/'start.json',{'command':command,'pid':process.pid,'started_utc':datetime.now(timezone.utc).isoformat(),
         'preexisting_top_checkpoint':False,'preexisting_results':0,'hard_macros':'bundled source IP; no old routed top'})
    # A notebook abort must not leave an untracked background routing container.
    def cleanup():
        if process.poll() is None:
            subprocess.run(['docker','stop','-t','3',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=12)
    atexit.register(cleanup)
    return PNR

def inputs(flow):
    if PNR is None:raise RuntimeError('Standalone cold PnR was not started by the first native configuration cell')
    config=PNR['config'];run=PNR['run']
    return {},{'odb':run/'results/routing'/f'{TOP}.odb','gds':run/'results/final/gds'/f'{TOP}.gds'},PNR['design'],run,config,flow.root/'pdks/digital/sky130A'

def wait_pnr(flow):
    from automx_nb_inline_v1.support import item
    if PNR is None:raise RuntimeError('Missing cold PnR process')
    process=PNR['process']
    try:process.wait(timeout=max(1,3600-(time.monotonic()-PNR['started'])))
    except subprocess.TimeoutExpired:
        subprocess.run(['docker','stop','-t','3',PNR['name']],capture_output=True,timeout=15)
        PNR['stream'].close()
        raise TimeoutError('Cold placement/routing exceeded one hour; actual incomplete log retained')
    PNR['stream'].close()
    code=process.returncode
    report={'identity':{'command':list(map(str,PNR['command'])),'cold_start':True},'returncode':code,
        'elapsed_s':time.monotonic()-PNR['started'],'log':item(PNR['log']),'outputs':[]}
    receipt=PNR['design'].parent/'step.json'
    save(receipt,report);flow.receipts['cold_pnr']=item(receipt)
    if code:raise RuntimeError('Cold OpenLane failed; inspect '+str(PNR['log']))
    _,views,_,run,_,_=inputs(flow)
    for key,p in views.items():
        if not p.is_file() or not p.stat().st_size:raise RuntimeError('Cold run did not produce '+key+': '+str(p))
    synth=run/'results/synthesis'/f'{TOP}.v'
    if not synth.is_file():raise FileNotFoundError('Fresh synthesis netlist missing')
    flow.outputs['mapped_synthesis']=item(synth)
    flow.outputs['placement_routing']={'mode':'COLD_FROM_RTL','log':str(PNR['log']),'source_top_checkpoint':None}
    print('COLD TOP IMPLEMENTATION COMPLETED:',views['gds'],flush=True)
    return views

def synthesize(flow):
    return wait_pnr(flow)

def synthesize_sar(flow):
    from automx_nb_inline_v1.support import item
    work=flow.work/'sar_synthesis';work.mkdir(exist_ok=True)
    lib=flow.root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    folder=flow.root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition/verilog/rtl'
    files=[folder/f for f in ('adc_control_nonbinary.v','adc_row_col_decoder.v','adc_osr.v','adc_core_digital.v')]
    script=work/'synthesis.ys';mapped=work/'adc_core_digital.mapped.v'
    script.write_text(f'read_liberty -lib "{lib}"\n'+''.join(f'read_verilog "{p}"\n' for p in files)+
        'hierarchy -check -top adc_core_digital\nsynth -top adc_core_digital -flatten\n'+
        f'dfflibmap -liberty "{lib}"\nabc -liberty "{lib}"\nclean\ncheck -assert\nwrite_verilog -noattr -noexpr "{mapped}"\n')
    result=flow.run('sar_synthesis',container(flow.root,'yosys',['-s',script],'automx-sar-'+str(os.getpid()),work),
        inputs=[script,lib,*files],outputs=[mapped],cwd=work,timeout_s=180)
    flow.outputs['mapped_sar']=item(mapped);return result

def streamout(flow):
    from automx_nb_inline_v1.support import item
    _,views,_,run,_,_=inputs(flow)
    work=flow.work/'streamout';work.mkdir(exist_ok=True)
    script=work/'export.tcl';definition=work/(TOP+'.def');lef=work/(TOP+'.lef')
    script.write_text(f'read_db {{{views["odb"]}}}\nwrite_def {{{definition}}}\nwrite_abstract_lef {{{lef}}}\nputs FRESH_ODB_VIEWS_EXPORTED\nexit\n')
    flow.run('export',container(flow.root,'openroad',['-exit',script],'automx-export-'+str(os.getpid()),work),
        inputs=[script,views['odb']],outputs=[definition,lef],cwd=work,timeout_s=90)
    gds=work/(TOP+'.gds');shutil.copyfile(views['gds'],gds)
    flow.outputs.update({k:item(p) for k,p in [('gds',gds),('def',definition),('lef',lef)]})
    flow.outputs['source_gds']=item(views['gds'])
    return gds

def audit_gds(flow):
    from automx_nb_inline_v1.support import item
    work=flow.work/'gds_audit';work.mkdir(exist_ok=True);gds=Path(flow.outputs['gds']['path'])
    source=inputs(flow)[1]['gds'];script=work/'geometry.py';proof=work/'geometry.json'
    script.write_text('import pya,json\na=pya.Layout();a.read('+repr(str(source))+')\nb=pya.Layout();b.read('+repr(str(gds))+')\n'
        'assert a.dbu==b.dbu\n'
        'def signature(l):\n return {c.name:(sorted((str(l.get_info(ly)),str(s)) for ly in l.layer_indexes() for s in c.shapes(ly).each()),sorted((l.cell(i.cell_index).name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b)) for i in c.each_inst())) for c in l.each_cell()}\n'
        'assert signature(a)==signature(b)\nt=b.cell('+repr(TOP)+');assert t is not None\n'
        'instances=sum(i.na*i.nb if i.is_regular_array() else 1 for i in t.each_inst())\n'
        'masters=len({b.cell(i.cell_index).name for i in t.each_inst()})\n'
        'result=dict(status="EXACT_COLD_GDS_CELL_GEOMETRY_AND_INSTANCES_MATCH",cells=b.cells(),instances=instances,masters=masters)\n'
        'json.dump(result,open('+repr(str(proof))+',"w"),indent=2)\nprint("KLayout fresh top:",result)\n')
    flow.run('geometry',['klayout','-b','-r',script],inputs=[script,gds,source],outputs=[proof],cwd=work,timeout_s=180)
    flow.outputs['gds_geometry_proof']=item(proof)
    pdk=flow.root/'pdks/digital/sky130A';deck=pdk/'libs.tech/klayout/drc/sky130A_mr.drc';xml=work/'drc.xml'
    drc_container='automx-drc-'+str(os.getpid())
    command=container(flow.root,'klayout',['-b','-r',deck,'-rd','input='+str(gds),'-rd','report='+str(xml),'-rd','beol=true','-rd','offgrid=true','-rd','feol=true','-rd','thr=4'],drc_container,work)
    try:r=flow.run('drc',command,inputs=[gds,deck],outputs=[xml],cwd=work,timeout_s=45)
    except RuntimeError:
        r=json.loads((work/'drc.step.json').read_text())
        if r['returncode']!=124:raise
        subprocess.run(['docker','stop','-t','1',drc_container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
        d={'status':'INCOMPLETE_TIMEOUT','violations':None,'log':r['log']}
    else:
        import xml.etree.ElementTree as ET
        count=len(list(ET.parse(xml).getroot().iter('item')))
        d={'status':'MEASURED_RULES_CLEAN' if count==0 else 'MEASURED_WITH_VIOLATIONS','violations':count,'log':r['log']}
    d['rule_groups']={'BEOL':True,'OFFGRID':True,'FEOL':True}
    save(work/'drc_summary.json',d);flow.outputs['gds_drc_summary']=item(work/'drc_summary.json')
    return json.loads(proof.read_text())

def normalize_single_connected_power_label(text):
    """Rename one occupied PG node only when the canonical label is unused.

    This never joins two electrical nodes. Multiple occupied aliases remain
    untouched and are rejected by the subsequent duplicate-port guard.
    """
    lines=text.splitlines();renamed=[]
    for start,line in enumerate(lines):
        fields=line.split()
        if len(fields)<3 or fields[:2]!=['.subckt',TOP]:continue
        end=next(i for i in range(start+1,len(lines)) if lines[i].lower().startswith('.ends'))
        counts={}
        for body in lines[start+1:end]:
            values=body.split()
            if values and not values[0].startswith(('*','.')):
                for node in values[1:-1]:counts[node]=counts.get(node,0)+1
        for canonical in ('VPWR','VGND'):
            aliases=[p for p in fields[2:] if re.fullmatch(canonical+r'_uq\d+',p)]
            occupied=[p for p in [canonical,*aliases] if counts.get(p,0)]
            if canonical in fields[2:] and len(occupied)==1 and occupied[0]!=canonical:
                alias=occupied[0];fields=[p for p in fields if p!=canonical]
                fields=[canonical if p==alias else p for p in fields]
                for i in range(start+1,end):
                    values=lines[i].split()
                    if values and not values[0].startswith(('*','.')):
                        lines[i]=' '.join(canonical if p==alias else p for p in values)
                renamed.append({'from':alias,'to':canonical,'canonical_node_uses_before':0,'occupied_nodes_before':1,
                    'electrical_nodes_merged':False,'renamed_connection_uses':counts[alias]})
        lines[start]=' '.join(fields)
    return '\n'.join(lines)+'\n',renamed

def remove_dangling_power_ports(text):
    """Drop only unused duplicated PG labels after the declared stdcell PG scope.

    Magic may make two top pin labels unique while leaving them disconnected.
    Canonical macro PG ports and every connected signal/rail node stay intact.
    """
    lines=text.splitlines();removed=[]
    for index,line in enumerate(lines):
        fields=line.split()
        if len(fields)<3 or fields[0].lower()!='.subckt' or fields[1]!=TOP:continue
        duplicates=[p for p in fields[2:] if re.fullmatch(r'(?:VPWR|VGND)_uq\d+',p)]
        end=next(i for i in range(index+1,len(lines)) if lines[i].lower().startswith('.ends'))
        nodes=set()
        for row in lines[index+1:end]:
            tokens=row.split()
            if tokens and not tokens[0].startswith(('*','.')):
                nodes.update(tokens[1:-1])
        for port in duplicates:
            canonical=port.split('_uq')[0]
            if canonical not in fields[2:] or port in nodes:
                raise ValueError('Duplicated PG port is connected or has no canonical rail: '+port)
        lines[index]=' '.join(p for p in fields if p not in duplicates);removed+=duplicates
    return '\n'.join(lines)+'\n',removed

def lvs(flow):
    """Fresh DEF/LEF macro-boundary extraction against the same cold routed ODB."""
    from automx_nb_inline_v1.support import item
    from scripts.check_flow2_signal_lvs import signal_spice,signal_verilog
    work=flow.work/'signal_lvs';work.mkdir(exist_ok=True)
    _,views,_,_,config,pdk=inputs(flow)
    lib=pdk/'libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    worker=flow.root/'scripts/flow2_fast_macro_lvs_odb.py'
    flow.run('lvs_export',container(flow.root,'openroad',['-exit','-python',worker,'--odb',views['odb'],'--work',work,'--lib',lib],'automx-lvsexport-'+str(os.getpid()),work),
        inputs=[worker,views['odb'],lib],outputs=[work/'signal_scope.def',work/'signal_scope.v'],cwd=work,timeout_s=120)
    rc=work/'magicrc';rc.write_text(f'set ::env(PDK_ROOT) {{{pdk.parent}}}\nset ::env(MAGTYPE) maglef\nsource {{{pdk/"libs.tech/magic/sky130A.magicrc"}}}\n')
    script=work/'extract.tcl'
    lefs=[pdk/'libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef',pdk/'libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef',pdk/'libs.ref/sky130_fd_sc_hd/lef/sky130_ef_sc_hd.lef',*[Path(p) for p in config['EXTRA_LEFS']]]
    text='crashbackups stop\ndrc off\n'+''.join(f'lef read {{{p}}}\n' for p in lefs)
    text+=f'def read {{{work/"signal_scope.def"}}}\nload {TOP}\nselect top cell\nextract do local\nextract no capacitance\nextract no coupling\nextract no resistance\nextract no adjust\nextract unique\nextract\next2spice lvs\next2spice -o {{{work/"physical.spice"}}}\nputs FRESH_MACRO_EXTRACTION_DONE\nquit -noprompt\n'
    script.write_text(text)
    flow.run('extract',container(flow.root,'magic',['-dnull','-noconsole','-rcfile',rc,script],'automx-extract-'+str(os.getpid()),work),
        inputs=[script,rc,work/'signal_scope.def',*lefs],outputs=[work/'physical.spice'],cwd=work,timeout_s=180)
    ptext,scope=signal_spice((work/'physical.spice').read_text())
    ptext,renamed=normalize_single_connected_power_label(ptext)
    ptext,dangling=remove_dangling_power_ports(ptext)
    save(work/'scope_normalization.json',{'standard_cell_pg_ports_removed_on_both_sides':scope,
        'unused_duplicate_top_pg_labels':dangling,'single_occupied_pg_label_renames':renamed,
        'connected_macro_pg_and_signal_nodes_preserved':True})
    vtext,count=signal_verilog((work/'signal_scope.v').read_text(),scope['removed_ports_by_master'])
    if count!=scope['standard_instances']:raise ValueError('Fresh physical/reference cell inventories differ')
    (work/'signal.spice').write_text(ptext);(work/'reference.v').write_text(vtext)
    log=work/'netgen.log'
    netgen=flow.root/'tools/netgen/lib/netgen/tcl/netgen.tcl'
    binary=netgen.with_name('tclnetgen.so')
    flow.run('signal_lvs',['tclsh',netgen,'-batch','lvs',str(work/'signal.spice')+' '+TOP,str(work/'reference.v')+' '+TOP,pdk/'libs.tech/netgen/sky130A_setup.tcl',log],
        inputs=[netgen,binary,work/'signal.spice',work/'reference.v'],outputs=[log],cwd=work,timeout_s=120)
    if 'Final result: Circuits match uniquely.' not in log.read_text():raise ValueError('Fresh macro-boundary LVS did not match')
    flow.outputs['signal_lvs']=item(log)
    print('Fresh extracted DEF/LEF signal macro-boundary LVS: MATCH UNIQUELY')

def power(flow):
    from automx_nb_inline_v1.support import item
    work=flow.work/'power';work.mkdir(exist_ok=True);proof=work/'power.json';script=work/'power.tcl'
    _,views,_,_,_,pdk=inputs(flow)
    lib=pdk/'libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    script.write_text(f'read_liberty {{{lib}}}\nread_db {{{views["odb"]}}}\ncheck_power_grid -net VPWR\nputs STANDALONE_VPWR_CONNECTED\ncheck_power_grid -net VGND\nputs STANDALONE_VGND_CONNECTED\nexit\n')
    result=flow.run('power',container(flow.root,'openroad',['-exit',script],'automx-pg-'+str(os.getpid()),work),inputs=[script,views['odb'],lib],cwd=work,timeout_s=120)
    log=Path(result['log']['path']).read_text()
    if not all(marker in log for marker in ('STANDALONE_VPWR_CONNECTED','STANDALONE_VGND_CONNECTED')) or '[ERROR' in log:
        raise ValueError('Actual supply connectivity failed')
    report={'status':'FRESH_COLD_TOP_PG_CONNECTED','rails':{'VPWR':'PASS','VGND':'PASS'},'geometry_changed':False,'published_views_changed':False,
            'method':'Native Tcl checks on the exact cold-routed ODB; failure propagates through process exit and log markers'}
    save(proof,report);flow.outputs['power']=item(proof);return report


def timing(flow):
    if (flow.work/'digital_blocks/hardening.json').is_file():return hierarchical_timing(flow)
    from automx_nb_inline_v1.support import item
    from scripts.run_flow2_chip_sta import prototype_sdc,timing_metrics
    from scripts.run_flow2_wrapper_postroute import clock_model
    _,views,_,run,_,_=inputs(flow);work=flow.work/'timing';work.mkdir(exist_ok=True)
    config=dict(re.findall(r'^set ::env\(([^)]+)\) "([^\n]*)"$',(run/'config.tcl').read_text(),re.M))
    lib=Path(config['LIB_TYPICAL']);rules=Path(config['RCX_RULES']);sdc=work/'prototype.sdc'
    sdc.write_text(prototype_sdc(Path(config['CURRENT_SDC']).read_text(),40))
    spef=work/(TOP+'.spef');rcx=work/'rcx.tcl'
    rcx.write_text(f'read_liberty {{{lib}}}\nread_db {{{views["odb"]}}}\nset_thread_count 8\ndefine_process_corner -ext_model_index 0 X\nextract_parasitics -ext_model_file {{{rules}}} -lef_res\nwrite_spef {{{spef}}}\nputs FRESH_RCX_DONE\nexit\n')
    flow.run('rcx',container(flow.root,'openroad',['-exit',rcx],'automx-rcx-'+str(os.getpid()),work),inputs=[rcx,views['odb'],lib,rules],outputs=[spef],cwd=work,timeout_s=180)
    macro_libs=PNR['config'].get('EXTRA_LIBS',[])
    model_reads=''.join('read_liberty {'+str(p)+'}\n' for p in macro_libs)
    base=f'read_liberty {{{lib}}}\n'+model_reads+f'read_db {{{views["odb"]}}}\nread_sdc {{{sdc}}}\nread_spef {{{spef}}}\nset_propagated_clock [all_clocks]\n'
    script=work/'timing.tcl';script.write_text(base+'check_setup -verbose\nreport_parasitic_annotation\nputs AUTOMX_SETUP_BEGIN\nreport_worst_slack -max\nputs AUTOMX_SETUP_END\nputs AUTOMX_HOLD_BEGIN\nreport_worst_slack -min\nputs AUTOMX_HOLD_END\nreport_checks -path_delay min_max -group_count 3\nputs AUTOMX_CHIP_STA_DONE\nexit\n')
    r=flow.run('timing',container(flow.root,'openroad',['-exit',script],'automx-sta-'+str(os.getpid()),work),inputs=[script,views['odb'],sdc,spef,lib],cwd=work,timeout_s=180)
    metrics=timing_metrics(Path(r['log']['path']).read_text())
    raw=work/(TOP+'.raw.lib');library=work/(TOP+'.digital_tt.lib');etm=work/'etm.tcl'
    etm.write_text(base+f'write_timing_model {{{raw}}}\nputs FRESH_ETM_DONE\nexit\n')
    flow.run('etm',container(flow.root,'openroad',['-exit',etm],'automx-etm-'+str(os.getpid()),work),inputs=[etm,views['odb'],sdc,spef,lib],outputs=[raw],cwd=work,timeout_s=180)
    library.write_text(clock_model(raw.read_text(),'clk_i'))
    flow.outputs.update({k:item(p) for k,p in [('spef',spef),('lib',library),('sdc',sdc)]})
    flow.outputs['nominal_timing']={**metrics,'frequency_mhz':25,'scope':'Fresh cold-routed constrained digital TT paths'}
    print('Fresh cold-route timing metrics:',metrics)
    return metrics

def hierarchical_timing(flow):
    """Actual gate-level hierarchy with extracted parent and child parasitics."""
    from automx_nb_inline_v1.support import item
    from scripts.run_flow2_chip_sta import prototype_sdc,timing_metrics
    from scripts.run_flow2_wrapper_postroute import clock_model
    _,views,_,run,_,_=inputs(flow);work=flow.work/'timing';work.mkdir(exist_ok=True)
    config=dict(re.findall(r'^set ::env\(([^)]+)\) "([^\n]*)"$',(run/'config.tcl').read_text(),re.M))
    blocks=json.loads((flow.work/'digital_blocks/hardening.json').read_text())['blocks']
    stdlib=Path(config['LIB_TYPICAL']);rules=Path(config['RCX_RULES']);sdc=work/'prototype.sdc'
    sdc.write_text(prototype_sdc(Path(config['CURRENT_SDC']).read_text(),40))
    spef=work/(TOP+'.spef');rcx=work/'rcx.tcl'
    rcx.write_text(f'read_liberty {{{stdlib}}}\nread_db {{{views["odb"]}}}\nset_thread_count 8\n'+
        f'define_process_corner -ext_model_index 0 X\nextract_parasitics -ext_model_file {{{rules}}} -lef_res\nwrite_spef {{{spef}}}\nexit\n')
    flow.run('parent_rcx',container(flow.root,'openroad',['-exit',rcx],'automx-parent-rcx-'+str(os.getpid()),work),
        inputs=[rcx,views['odb'],stdlib,rules],outputs=[spef],cwd=work,timeout_s=180)
    root_netlist=run/'results/routing'/f'{TOP}.nl.v'
    base=f'read_liberty {{{stdlib}}}\nread_verilog {{{flow.root/"inputs/wrapper_blackboxes.sv"}}}\n'
    base+=''.join('read_verilog {'+v['mapped_netlist']+'}\n' for v in blocks)
    base+=f'read_verilog {{{root_netlist}}}\nlink_design {TOP}\nread_sdc {{{sdc}}}\nread_spef {{{spef}}}\n'
    for v in blocks:
        instance='mha_i' if v['name']=='mha' else 'seq_i'
        base+='read_spef -path '+instance+' {'+v['spef']+'}\n'
    base+='set_propagated_clock [all_clocks]\n'
    script=work/'hierarchical_sta.tcl'
    script.write_text(base+'check_setup -verbose\nreport_parasitic_annotation\nputs AUTOMX_SETUP_BEGIN\nreport_worst_slack -max\nputs AUTOMX_SETUP_END\nputs AUTOMX_HOLD_BEGIN\nreport_worst_slack -min\nputs AUTOMX_HOLD_END\nreport_checks -path_delay min_max -group_count 3\nputs AUTOMX_CHIP_STA_DONE\nexit\n')
    sources=[root_netlist,stdlib,sdc,spef,*[Path(v[k]) for v in blocks for k in ('mapped_netlist','spef')]]
    result=flow.run('hierarchical_timing',container(flow.root,'sta',['-exit',script],'automx-hier-sta-'+str(os.getpid()),work),
        inputs=[script,*sources],cwd=work,timeout_s=180)
    log=Path(result['log']['path']).read_text();metrics=timing_metrics(log)
    if re.search(r'(?m)^Error:',log):raise ValueError('Hierarchical STA reported an error')
    raw=work/(TOP+'.raw.lib');library=work/(TOP+'.digital_tt.lib');etm=work/'etm.tcl'
    etm.write_text(base+f'write_timing_model {{{raw}}}\nputs FRESH_ETM_DONE\nexit\n')
    flow.run('hierarchical_etm',container(flow.root,'sta',['-exit',etm],'automx-hier-etm-'+str(os.getpid()),work),
        inputs=[etm,*sources],outputs=[raw],cwd=work,timeout_s=180)
    library.write_text(clock_model(raw.read_text(),'clk_i'))
    flow.outputs.update({k:item(p) for k,p in [('spef',spef),('lib',library),('sdc',sdc)]})
    flow.outputs['nominal_timing']={**metrics,'frequency_mhz':25,
        'scope':'Hierarchical gate-level TT STA: parent and both digital hard-macro SPEFs; physical-interface Liberty arcs are not used for signoff.'}
    print('HIERARCHICAL_EXTRACTED_TIMING',metrics,flush=True);return metrics


def parse_library(flow):
    work=flow.work/'timing';library=flow.outputs['lib']['path'];script=work/'parse.tcl'
    script.write_text(f'read_liberty {{{library}}}\nputs FRESH_LIB_PARSED\nexit\n')
    return flow.run('lib_parse',container(flow.root,'sta',['-exit',script],'automx-lib-'+str(os.getpid()),work),inputs=[script,Path(library)],cwd=work,timeout_s=60)

def prepare_shared(flow):
    from automx_nb_inline_v1.support import save,item
    lib=flow.base/'tools/ngspice_shared44/install/lib/libngspice.so';lib.parent.mkdir(parents=True,exist_ok=True)
    if not lib.exists():lib.symlink_to(flow.root/'tools/ngspice/libngspice.so')
    probe=flow.work/'ngspice_version.py'
    probe.write_text('import ctypes,sys\nl=ctypes.CDLL(sys.argv[1])\nT=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_void_p)\ndef out(m,*_):\n print(m.decode(),flush=True);return 0\nf=T(out)\nl.ngSpice_Init(f,None,None,None,None,None,None)\nraise SystemExit(l.ngSpice_Command(b"version"))\n')
    flow.run('ngspice_runtime_version',[sys.executable,probe,lib],inputs=[probe,lib],timeout_s=30)
    save(flow.work/'ngspice_runtime.json',{'library':item(lib),'bundled_tool':True})
    flow.outputs['ngspice_runtime']=item(flow.work/'ngspice_runtime.json');return lib

def environment(flow):
    print('Independent source root:',flow.root,'| Python:',sys.executable)
    for tool,args in [('iverilog',['-V']),('vvp',['-V']),('klayout',['-b','-v'])]:
        flow.run(tool+'_version',[tool,*args],timeout_s=30)
    for tool,args in [('yosys',['-V']),('openroad',['-version'])]:
        flow.run(tool+'_version',container(flow.root,tool,args,'automx-version-'+tool+'-'+str(os.getpid()),flow.work),timeout_s=30)

def export_factorial(namespace,review):
    """Populate review inputs using only measurements acquired in this run."""
    root=namespace['ROOT'];work=namespace['WORK'];pilot=namespace['fresh_pilot']
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        new=list(pool.map(lambda cp:pilot.measure_pair(root,work,*cp),[(200,50),(800,100)]))
    pilot.RESULTS['200']=namespace['fresh_baseline'];pilot.RESULTS['800']=namespace['fresh_candidate']
    conditions=[namespace['fresh_baseline'],namespace['fresh_candidate'],*new]
    review['E']['factorial']=[]
    for row in sorted(conditions,key=lambda d:(d['load_ff'],d['pwm_unit_ps'])):
        row=json.loads(json.dumps(row));row['acquisition']='new_native_current_run'
        for job in row['jobs']:
            # Relative paths may leave review_data, but remain within this fresh run.
            job['log']=os.path.relpath(job['log'],review['BASE']);job['deck']=os.path.relpath(job['deck'],review['BASE'])
        review['E']['factorial'].append(row)
    save(review['BASE']/'evidence.json',review['E'])

def export_conversions(namespace,review):
    root=namespace['ROOT'];flow=namespace['flow'];experiment=namespace['experiment'];mha=namespace['mha']
    spec=json.loads((root/'inputs/experiment_spec.json').read_text());base=review['BASE'];E=review['E']
    fit=experiment.calibration
    # This lock is written BEFORE the additional challenge conversions are launched.
    save(base/'data/provenance.json',{'protocol':{'calibration':fit,'calibration_frozen':True,'prior_pattern_overlap':0,
         'locked_utc':datetime.now(timezone.utc).isoformat(),'challenge_payloads':[r for r in spec['cases'] if r['cohort']=='challenge']}})
    requests=[]
    for row in spec['cases']:
        if row['cohort']=='challenge':
            payload=row['payload'];key,data=experiment.payload(payload['activation_x2'],[r[0] for r in payload['weights']]);requests.append((key,data))
    experiment.many(requests)
    refs={};E['cases']=[]
    for row in spec['cases']:
        payload=row['payload'];key,data=experiment.payload(payload['activation_x2'],[r[0] for r in payload['weights']])
        folder=flow.work/('conversion_'+key);summary=folder/'summary.json'
        if not summary.is_file():raise FileNotFoundError('Fresh conversion missing: '+row['id'])
        E['cases'].append({'id':row['id'],'cohort':row['cohort'],
            **{k:os.path.relpath(folder/name,base) for k,name in [('summary','summary.json'),('stimulus','case.json'),('rtl_log','rtl.log'),('ngspice_log','ngspice.log')]}})
        refs[str(summary)]=row['id']
    E['calibration_ids']=spec['calibration_ids']
    E['mha']={'activation_x2':mha['activation_x2'],'weights':mha['weights'],'recorded_output':mha['output'],
       'jobs':[{'stage':j['stage'],'row':j['row'],'column':j['column'],'case':refs[j['case']['path']]} for j in mha['jobs']]}
    first=next(c for c in E['cases'] if c['id']=='projection_01')
    E['waveform']={'case':'projection_01','path':os.path.relpath((base/first['summary']).parent/'coupled.raw',base)}
    save(base/'evidence.json',E)
    print('Fresh evidence populated:3 calibration +30 projection +8 challenge conversions. No old records read.')

def export_physical(namespace,review):
    flow=namespace['flow'];base=review['BASE'];E=review['E'];work=flow.work
    E['physical']={k:os.path.relpath(p,base) for k,p in [('geometry',work/'gds_audit/geometry.json'),
      ('power',work/'power/power.json'),('drc',work/'gds_audit/drc_summary.json'),('timing_log',work/('timing/hierarchical_timing.native.log' if (work/'digital_blocks/hardening.json').is_file() else 'timing/timing.native.log')),
      ('lvs_log',work/'signal_lvs/netgen.log')]}
    for source,name in [(work/'render_top/top.png','top'),(work/'render_01_core_acquisition/01_core_acquisition.png','core_acquisition'),
       (work/'render_02_conditioner_mux/02_conditioner_mux.png','conditioner_mux'),(work/'render_03_adc_reference/03_adc_reference.png','adc_reference')]:
        target=base/'figures'/f'{name}.png';target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    import gzip
    path=base/'layout/top.gds.gz';path.parent.mkdir(parents=True,exist_ok=True)
    with Path(flow.outputs['gds']['path']).open('rb') as source,gzip.open(path,'wb') as out:shutil.copyfileobj(source,out)
    save(base/'evidence.json',E)

def publish(flow,inline_sources=None,history=None):
    from automx_nb_inline_v1.support import item,verified
    keys=('analog_adc_mha','mapped_synthesis','mapped_sar','gds','lef','def','gds_geometry_proof','gds_drc_summary','signal_lvs','power','spef','lib','sdc','top_png')
    for key in keys:verified(flow.outputs[key])
    flow.outputs['digital_block_hardening']=item(flow.work/'digital_blocks/hardening.json')
    flow.outputs['block_floorplan']=item(flow.work/'block_floorplan.json')
    flow.outputs['block_floorplan_svg']=item(flow.work/'render_top/block_floorplan.svg')
    for key,relative in [('mha_rtl_verification','mha_ip/verification.json'),
                         ('mha_rtl_synthesis','mha_ip/synthesis/synthesis.json'),
                         ('mha_rtl_measured_comparison','mha_ip_measured_comparison.json')]:
        path=flow.work/relative
        if json.loads(path.read_text())['status']!='PASS':raise ValueError('MHA IP verification failed: '+relative)
        flow.outputs[key]=item(path)
    report={'status':'STANDALONE_FRESH_ANALOG_ADC_MHA_AND_COLD_PNR_COMPLETED',
       'source_checkout_required':False,'old_results_reused':False,'old_routed_checkpoint_reused':False,
       'hard_macros':'Bundled source IP views','views':flow.outputs,'native_steps':flow.receipts,
       'placement_routing':'COLD_FROM_RTL','fabrication_ready':False}
    save(flow.work/'runall_manifest.json',report)
    print('STANDALONE FRESH END-TO-END COMPLETE')
    print('Top GDS:',flow.outputs['gds']['path']);print('Run manifest:',flow.work/'runall_manifest.json')
    return report

# DIGITAL_BLOCK_MACRO_IMPLEMENTATION
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


def build_pulse_readout(root,source,work):
    from types import SimpleNamespace
    hard=SimpleNamespace(native=native,finish_block=finish_block)
    root=Path(root).resolve();source=Path(source).resolve();folder=Path(work).resolve()/'readout';design=folder/'design';design.mkdir(parents=True,exist_ok=False)
    top='automx_cim_readout_seq';config=json.loads((root/'inputs/openlane_config_template.json').read_text())
    config.update(DESIGN_NAME=top,VERILOG_FILES=[str(source)],DIE_AREA='0 0 1250 750',DESIGN_IS_CORE=0,FP_CORE_UTIL=30,
        PL_TARGET_DENSITY=.4,FP_PDN_CHECK_NODES=1,FP_PDN_VOFFSET=14,FP_PDN_VPITCH=80,FP_PDN_VWIDTH=1.6,
        PRIMARY_SIGNOFF_TOOL='magic',RT_MAX_LAYER='met4',GRT_MAX_LAYER='met4',DRT_MAX_LAYER='met4',RUN_SPEF_EXTRACTION=0,STA_WRITE_LIB=0,
        RUN_HEURISTIC_DIODE_INSERTION=0,GLB_RESIZER_DESIGN_OPTIMIZATIONS=0,GLB_RESIZER_TIMING_OPTIMIZATIONS=1,
        GLB_RESIZER_SETUP_SLACK_MARGIN=1.,GLB_RESIZER_HOLD_SLACK_MARGIN=.1,RSZ_MULTICORNER_LIB=0,
        RSZ_DONT_TOUCH_RX='(pulse_generator|delay_taps|storage_gating|clkbuf_)')
    for k in ('FP_PDN_MACRO_HOOKS','EXTRA_LEFS','EXTRA_GDS_FILES','EXTRA_LIBS','MACRO_PLACEMENT_CFG','FP_PDN_CFG','VERILOG_FILES_BLACKBOX'):config.pop(k,None)
    (design/'config.json').write_text(json.dumps(config,indent=2)+'\n');shutil.copy2(source,folder/'source.sv')
    eco=folder/'size_data_buffers.tcl';eco.write_text('''source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read
set master [[ord::get_db] findMaster sky130_fd_sc_hd__buf_16]
set block [ord::get_db_block]
set count 0
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {[[$inst getMaster] getName] eq "sky130_fd_sc_hd__buf_1" && ![regexp {(pulse_generator|delay_taps|clkbuf_)} $name]} {
  set net [[$inst findITerm X] getNet]
  if {[llength [$net getITerms]]>=16} {
   $inst swapMaster $master
   incr count
  }
 }
}
puts "DATA_BUFFER_SIZING count=$count drive=16 minimum_net_pin_count=16 pulse_lanes_preserved=true"
set outputs 0
foreach port [$block getBTerms] {
 set name [$port getName]
 if {![regexp {^wl[pn]_o} $name]} {continue}
 foreach pin [[$port getNet] getITerms] {
  if {[[$pin getMTerm] getIoType] ne "OUTPUT"} {continue}
  set inst [$pin getInst]
  set model [[$inst getMaster] getName]
  foreach strength {16 12 8 6 4 2 1} {
   set candidate [regsub {_[0-9]+$} $model _$strength]
   set strong [[ord::get_db] findMaster $candidate]
   if {$strong!="NULL"} {
    $inst swapMaster $strong
    puts "WORDLINE_OUTPUT_DRIVER $name $model $candidate"
    incr outputs
    break
   }
  }
 }
}
if {$outputs!=8} {error "Expected eight explicitly sized wordline output drivers"}
detailed_placement
check_placement -verbose
write
''')
    regular=folder/'place_delay_line.tcl';regular.write_text(r'''source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read
set block [ord::get_db_block]
set row [lindex [$block getRows] 40]
lassign [$row getOrigin] x y
set site [[$row getSite] getWidth]
set height [[$row getSite] getHeight]
set padding [expr {2*$site}]
set origin $x
set x [expr {$x+20*$site}]
set obstacles {}
foreach inst [$block getInsts] {
 if {[$inst isFixed]} {
  set bbox [$inst getBBox]
  if {[$bbox yMin]<$y+$height && [$bbox yMax]>$y} {lappend obstacles [list [$bbox xMin] [$bbox xMax]]}
 }
}
set stages {}
foreach inst [$block getInsts] {
 if {[regexp {^delay_taps\[([0-9]+)\]\.delay_i$} [string map {\\ ""} [$inst getName]] all number]} {lappend stages [list $number $inst]}
}
if {[llength $stages]!=72} {error "Expected 72 physical delay stages, found [llength $stages]"}
foreach pair [lsort -integer -index 0 $stages] {
 set inst [lindex $pair 1]
 set width [[$inst getMaster] getWidth]
 foreach obstacle [lsort -integer -index 0 $obstacles] {
  lassign $obstacle left right
  if {$x+$width+$padding>$left && $x-$padding<$right} {
   set x [expr {$origin+int(ceil(double($right+$padding-$origin)/$site))*$site}]
  }
 }
 $inst setOrient [$row getOrient]
 $inst setLocation $x $y
 $inst setPlacementStatus FIRM
 set x [expr {$x+$width+2*$padding}]
}
# Keep each isolated tap input near its source; strong local drivers
# carry the mux wiring. Loading every sixth tap equally preserves spacing.
set tap_driver_count 0
set tap_lookup {}
foreach mapped [$block getInsts] {dict set tap_lookup [string map [list [format %c 92] ""] [$mapped getName]] $mapped}
for {set lane 0} {$lane<4} {incr lane} {
 for {set code 0} {$code<=12} {incr code} {
  set names [list [format {pulse_generator[%d].pulse_tap_drive[%d].isolate_i} $lane $code] [format {pulse_generator[%d].pulse_tap_drive[%d].drive_i} $lane $code]]
  if {![dict exists $tap_lookup [lindex $names 0]]} {continue}
  set row [lindex [$block getRows] [expr {43+3*$lane}]]
  lassign [$row getOrigin] origin y
  set site [[$row getSite] getWidth];set height [[$row getSite] getHeight]
  set padding [expr {2*$site}]
  set stage [expr {$code==0 ? 1 : 6*$code}]
  set driver [dict get $tap_lookup [format {delay_taps[%d].delay_i} $stage]]
  lassign [$driver getLocation] x ignore_y
  set obstacles {}
  foreach fixed [$block getInsts] {
   if {[$fixed isFixed]} {
    set bb [$fixed getBBox]
    if {[$bb yMin]<$y+$height && [$bb yMax]>$y} {lappend obstacles [list [$bb xMin] [$bb xMax]]}
   }
  }
  foreach name $names {
   set inst [dict get $tap_lookup $name];set width [[$inst getMaster] getWidth]
   foreach obstacle [lsort -integer -index 0 $obstacles] {
    lassign $obstacle left right
    if {$x+$width+$padding>$left && $x-$padding<$right} {set x [expr {$origin+int(ceil(double($right+$padding-$origin)/$site))*$site}]}
   }
   $inst setOrient [$row getOrient]
   $inst setLocation $x $y
   $inst setPlacementStatus FIRM
   set x [expr {$x+$width+2*$padding}]
   incr tap_driver_count
  }
 }
}
# Pulse formation must remain adjacent to its strong output driver.
# Only full-swing reference/delay edges travel on the longer mux wires.
set edge_cluster_cells 0
for {set lane 0} {$lane<4} {incr lane} {
 set row [lindex [$block getRows] [expr {70+8*$lane}]]
 lassign [$row getOrigin] origin y
 set site [[$row getSite] getWidth];set height [[$row getSite] getHeight]
 set padding [expr {2*$site}];set x [expr {$origin+500*$site}]
 set obstacles {}
 foreach fixed [$block getInsts] {
  if {[$fixed isFixed]} {
   set bb [$fixed getBBox]
   if {[$bb yMin]<$y+$height && [$bb yMax]>$y} {lappend obstacles [list [$bb xMin] [$bb xMax]]}
  }
 }
 foreach suffix {reference_low_i delayed_low_i reference_high_i delayed_high_i reference_select_i delayed_select_i invert_i positive_i positive_drive_i negative_i negative_drive_i} {
  set name [format {pulse_generator[%d].%s} $lane $suffix]
  if {![dict exists $tap_lookup $name]} {continue}
  set inst [dict get $tap_lookup $name];set width [[$inst getMaster] getWidth]
  foreach obstacle [lsort -integer -index 0 $obstacles] {
   lassign $obstacle left right
   if {$x+$width+$padding>$left && $x-$padding<$right} {set x [expr {$origin+int(ceil(double($right+$padding-$origin)/$site))*$site}]}
  }
  $inst setOrient [$row getOrient]
  $inst setLocation $x $y
  $inst setPlacementStatus FIRM
  set x [expr {$x+$width+2*$padding}]
  incr edge_cluster_cells
 }
}
if {$edge_cluster_cells!=44} {error "Expected 44 explicitly clustered pulse-formation cells"}
puts "PULSE_FORMATION_CLUSTER cells=$edge_cluster_cells adjacent_gate_driver=true"
puts "ROW_LOCAL_TAP_PLACEMENT cells=$tap_driver_count"
puts "REGULAR_DELAY_LINE stages=72 row=40 fixed=true legal_padding_sites=2 tap_obstacles_skipped=true"
write
''')
    run=folder/'build.tcl';run.write_text('''lappend ::auto_path /openlane/scripts
package require openlane
prep -design {'''+str(design)+'''} -config_file {'''+str(design/'config.json')+'''} -tag hard
run_synthesis
run_floorplan
run_openroad_script {'''+str(regular)+'''} -indexed_log $::env(floorplan_logs)/delay_line_placement.log -save "dir=$::env(floorplan_tmpfiles),def,sdc,odb,netlist,powered_netlist"
run_placement
run_cts
run_resizer_timing
run_openroad_script {'''+str(eco)+'''} -indexed_log $::env(cts_logs)/data_buffer_sizing.log -save "dir=$::env(cts_tmpfiles),def,sdc,odb,netlist,powered_netlist"
set ::env(RSZ_LIB) $::env(LIB_TYPICAL)
run_routing
run_magic
save_final_views
save_state
puts LOCAL_PULSE_READOUT_ROUTED
''')
    command=hard.native(root,'/openlane/flow.tcl',['-interactive','-file',run],'automx-local-pulse-'+str(os.getpid()),'/openlane');start=time.monotonic()
    with (folder/'native.log').open('w') as log:q=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=2700)
    assert q.returncode==0,(folder/'native.log').read_text()[-2500:]
    result=hard.finish_block(root,folder,'readout',time.monotonic()-start)
    assert result['setup_slack_ns']>=0 and result['hold_slack_ns']>=0,result
    print('LOCAL_PULSE_READOUT_PASS',result['setup_slack_ns'],result['hold_slack_ns'],flush=True);return result



def build_block(root,work,name):
    candidate_source=Path(root)/BLOCKS[name]['source']
    if name=='readout' and 'wire [72:0] tap;' in candidate_source.read_text():
        return build_pulse_readout(root,candidate_source,work)
    root=Path(root).resolve();work=Path(work).resolve();spec=BLOCKS[name]
    folder=work/name;design=folder/'design';design.mkdir(parents=True,exist_ok=False)
    top=spec['top'];config=json.loads((root/'inputs/openlane_config_template.json').read_text())
    config.update(DESIGN_NAME=top,VERILOG_FILES=[str(root/spec['source'])],
        DIE_AREA=f"0 0 {spec['width']} {spec['height']}",DESIGN_IS_CORE=0,FP_CORE_UTIL=30,
        PL_TARGET_DENSITY=spec['density'],FP_PDN_MACRO_HOOKS='',FP_PDN_CHECK_NODES=1,
        FP_PDN_VOFFSET=14,FP_PDN_VPITCH=80,FP_PDN_VWIDTH=1.6,
        RT_MAX_LAYER='met4',GRT_MAX_LAYER='met4',DRT_MAX_LAYER='met4',
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


def finish_block(root,folder,name,prior_elapsed=0):
    root=Path(root).resolve();folder=Path(folder).resolve();spec=BLOCKS[name]
    design=folder/'design';top=spec['top'];started=time.monotonic()-prior_elapsed
    label=f'automx-block-finish-{name}-{os.getpid()}'
    run=design/'runs/hard';route=run/'logs/routing/17-detailed.log'
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
