"""Rebuild top views from a hash-bound routed checkpoint, with native logs.

Fresh synthesis checks the same RTL. Placement/routing is an explicitly
reused checkpoint, not a claim of a new cold-start PnR or fabrication signoff.
"""
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.flow2_runall_support import item,digest,save

TOP='automx_cim_mixed_signal_proto'
NATIVE='mixed_wrapper_srv_20261022_04_impl_gds'


def inputs(flow):
    from scripts import flow2_integration_common as c
    from scripts import run_flow2_wrapper_postroute as p
    receipt=flow.root/c.BASE/'antenna_streamout_srv_20261022_03/summary.json'
    source=json.loads(receipt.read_text())
    views={k:c._verified(flow.root,v) for k,v in source['views'].items()}
    design=flow.root/c.BUILD/NATIVE/'design';run=design/'runs'/NATIVE
    settings=json.loads((design/'config.json').read_text());pdk=p.native.notebook.DEFAULT_PDK/'sky130A'
    recorded=json.loads((flow.root/c.BASE/NATIVE/'inputs.json').read_text())['sources']
    seq=[v for v in recorded if v['path']=='rtl/automx_cim_readout_seq.sv']
    if len(seq)!=1 or c._verified(flow.root,seq[0])!=flow.root/'rtl/automx_cim_readout_seq.sv':
        raise ValueError('routed checkpoint RTL changed; full PnR is required')
    return source,views,design,run,settings,pdk


def synthesize(flow):
    source,views,design,run,settings,pdk=inputs(flow)
    work=flow.work/'synthesis';work.mkdir(exist_ok=True)
    library=run/'tmp/synthesis/trimmed.lib'
    script=work/'synthesize.ys';mapped=work/(TOP+'.mapped.v')
    files=[Path(p) for p in settings['VERILOG_FILES']];blackbox=Path(settings['VERILOG_FILES_BLACKBOX'])
    script.write_text(f'read_liberty -lib -ignore_miss_dir "{library}"\n'
        f'read_verilog -lib -sv "{blackbox}"\n'+
        ''.join(f'read_verilog -sv "{p}"\n' for p in files)+
        f'hierarchy -check -top {TOP}\nsynth -top {TOP} -flatten\n'
        f'dfflibmap -liberty "{library}"\nabc -liberty "{library}" -D 40000\n'
        'clean\ncheck -assert\nselect -assert-none t:$*\n'+
        f'stat -liberty "{library}"\nwrite_verilog -noattr -noexpr "{mapped}"\n')
    cmd=flow.container('yosys',['-s',script],'synthesis',work)
    result=flow.run('synthesis',cmd,inputs=[script,library,blackbox,*files],outputs=[mapped],timeout_s=360)
    flow.outputs['mapped_synthesis']=item(mapped)
    flow.outputs['route_checkpoint']={'path':str(views['odb']),'sha256':digest(views['odb']),
        'scope':'Previously routed checkpoint; fresh synthesis does not reroute or replace it.'}
    return result


def streamout(flow):
    from scripts.run_flow2_antenna_streamout import validate_streamout_log,component_masters
    source,views,design,run,settings,pdk=inputs(flow)
    work=flow.work/'streamout';work.mkdir(exist_ok=True)
    definition=work/(TOP+'.def');lef=work/(TOP+'.lef');gds=work/(TOP+'.gds')
    export=work/'export.tcl'
    export.write_text(f'read_db {{{views["odb"]}}}\nwrite_def {{{definition}}}\nwrite_abstract_lef {{{lef}}}\nputs AUTOMX_RUNALL_EXPORT_DONE\nexit\n')
    flow.run('export',flow.container('openroad',['-exit',export],'export',work),
        cwd=work,inputs=[export,views['odb']],outputs=[definition,lef],timeout_s=90)
    library=work/'library.gds';script=work/'library.py'
    script.write_text('import pya\nl=pya.Layout()\nl.read('+repr(str(views['gds']))+')\n'
        'c=l.cell('+repr(TOP)+');assert c is not None\nl.delete_cell(c.cell_index())\n'
        'l.write('+repr(str(library))+')\nprint("KLayout: macro/cell library extracted from verified source GDS")\n')
    flow.run('library',['klayout','-b','-r',script],inputs=[script,views['gds']],outputs=[library],cwd=work,timeout_s=90)
    klayout=pdk/'libs.tech/klayout';tech=klayout/'tech'
    lefs=[pdk/'libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef',
        pdk/'libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef',
        pdk/'libs.ref/sky130_fd_sc_hd/lef/sky130_ef_sc_hd.lef',*[Path(p) for p in settings['EXTRA_LEFS']]]
    stream=Path('/home/nam/dependencies/openlane_src/scripts/klayout/stream_out.py')
    args={'input':definition,'output':work/'raw_streamout.gds','design_name':TOP,'input_lefs':';'.join(map(str,lefs)),
        'input_gds_files':library,'seal_gds':'NULL','lyt':tech/'sky130A.lyt','lyp':tech/'sky130A.lyp','lym':tech/'sky130A.map'}
    command=['-b','-rm',stream]
    for key,value in args.items():command+=['-rd',key+'='+str(value)]
    result=flow.run('streamout',flow.container('klayout',command,'streamout',work),
        inputs=[definition,library,stream,*lefs],outputs=[work/'raw_streamout.gds'],cwd=work,timeout_s=180)
    validate_streamout_log(Path(result['log']['path']).read_text())
    # DEF creates VIA helpers, and merging the source library can insert the
    # same via shapes a second time. Remove only byte-identical leaf shapes;
    # the following full hierarchy audit must still match the source exactly.
    dedup=work/'deduplicate.py';dedup_proof=work/'deduplicate.json'
    dedup.write_text('import pya,json\nl=pya.Layout();l.read('+repr(str(work/'raw_streamout.gds'))+')\nremoved={}\n'
        'for c in l.each_cell():\n if not c.name.startswith("VIA_"):continue\n assert c.child_instances()==0\n n=0\n'
        ' for ly in l.layer_indexes():\n  seen=set()\n  for shape in list(c.shapes(ly).each()):\n   key=str(shape)\n'
        '   if key in seen:shape.delete();n+=1\n   else:seen.add(key)\n'
        ' if n:removed[c.name]=n\n'
        'l.write('+repr(str(gds))+')\njson.dump(removed,open('+repr(str(dedup_proof))+',"w"),indent=2)\n'
        'print("KLayout: removed identical duplicate VIA leaf shapes only",removed)\n')
    flow.run('deduplicate_vias',['klayout','-b','-r',dedup],inputs=[dedup,work/'raw_streamout.gds'],outputs=[gds,dedup_proof],cwd=work,timeout_s=90)
    expected=component_masters(definition)
    save(work/'masters.json',expected)
    flow.outputs.update({k:item(p) for k,p in (('gds',gds),('lef',lef),('def',definition))})
    flow.outputs['source_gds']=item(views['gds'])
    return gds


def audit_gds(flow):
    source,views,design,run,settings,pdk=inputs(flow)
    gds=Path(flow.outputs['gds']['path']);work=flow.work/'gds_audit';work.mkdir(exist_ok=True)
    script=work/'audit.py';proof=work/'geometry.json';expected=flow.work/'streamout/masters.json'
    # Shape strings include full coordinates/layers and instance transforms;
    # compare every cell, not only die bounds or component counts.
    script.write_text('''import pya,json,hashlib
from collections import Counter
def signature(path):
 l=pya.Layout();l.read(path);cells={};pending=[l.cell("automx_cim_mixed_signal_proto")];seen=set()
 while pending:
  c=pending.pop()
  if c.name in seen:continue
  seen.add(c.name);pending.extend(l.cell(i.cell_index) for i in c.each_inst())
  rows=[]
  for layer in l.layer_indexes():
   info=l.get_info(layer)
   for s in c.shapes(layer).each():rows.append((str(info),str(s)))
  inst=sorted((l.cell(i.cell_index).name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b)) for i in c.each_inst())
  cells[c.name]=hashlib.sha256(repr((sorted(rows),inst)).encode()).hexdigest()
 return l,cells
'''+f'a,old=signature({str(views["gds"])!r})\nb,new=signature({str(gds)!r})\n'+
        'assert a.dbu==b.dbu and old==new,"GDS geometry differs from LVS-bound source"\n'
        f'masters=json.load(open({str(expected)!r}))\nt=b.cell({TOP!r})\n'
        'count=Counter()\nfor i in t.each_inst():\n if b.cell(i.cell_index).name in masters:count[b.cell(i.cell_index).name]+=i.na*i.nb if i.is_regular_array() else 1\n'
        'assert dict(count)==masters,"incomplete GDS instances"\n'
        f'json.dump(dict(status="EXACT_GDS_CELL_GEOMETRY_AND_INSTANCES_MATCH",cells=len(new),instances=sum(count.values()),masters=len(count)),open({str(proof)!r},"w"),indent=2)\n'
        'print("KLayout: all cell geometry, placements and component inventory match the source")\n')
    flow.run('geometry',['klayout','-b','-r',script],inputs=[script,gds,views['gds'],expected],outputs=[proof],cwd=work,timeout_s=180)
    deck=pdk/'libs.tech/klayout/drc/sky130A_mr.drc';xml=work/'drc_enabled.xml';report_path=work/'drc_summary.json'
    flags=['-rd','beol=true','-rd','offgrid=true','-rd','feol=false','-rd','thr=4']
    command=flow.container('klayout',['-b','-r',deck,'-rd','input='+str(gds),'-rd','report='+str(xml),*flags],'drc_enabled',work)
    previous=work/'klayout_drc_enabled.step.json';reuse_incomplete=False
    if flow.settings.reuse and previous.is_file():
        candidate=json.loads(previous.read_text())
        if candidate['returncode']==124 and candidate['identity']['command']==list(map(str,command)):
            try:
                from scripts.flow2_runall_support import verified
                for value in [*candidate['identity']['sources'],candidate['log']]:verified(value)
            except (ValueError,OSError):pass
            else:reuse_incomplete=True
    try:
        if reuse_incomplete:
            print('REUSE bounded INCOMPLETE DRC attempt: waiver only, never DRC-clean. Use a new tag/reuse=False to retry.')
            flow.log(candidate['log']['path']);flow.receipts['klayout_drc_enabled']=item(previous)
            raise RuntimeError('prior bounded DRC attempt remains incomplete')
        result=flow.run('klayout_drc_enabled',command,inputs=[deck,gds],outputs=[xml],cwd=work,timeout_s=180)
    except RuntimeError:
        failed=json.loads((work/'klayout_drc_enabled.step.json').read_text())
        if failed['returncode']!=124:raise
        drc={'status':'INCOMPLETE_TIMEOUT','violations':None,'rule_groups':{'BEOL':True,'OFFGRID':True,'FEOL':False},'log':failed['log']}
    else:
        from scripts.flow2_klayout_checks import summarize
        measured=summarize(xml);count=measured['violations']
        drc={'status':'MEASURED_RULES_CLEAN' if count==0 else 'MEASURED_WITH_VIOLATIONS','violations':count,
            'rule_groups':{'BEOL':True,'OFFGRID':True,'FEOL':False},**measured,'report':item(xml),'log':result['log']}
        flow.outputs['gds_klayout_drc']=item(xml)
    drc['scope']='Native BEOL and off-grid checks; FEOL, seal and floating-metal checks remain open. Earlier no-flag empty reports are not DRC-clean evidence.'
    save(report_path,drc)
    flow.outputs['gds_geometry_proof']=item(proof);flow.outputs['gds_drc_summary']=item(report_path)
    print('New top: exact source geometry match. Enabled KLayout checks:',json.dumps(drc,indent=2))
    return json.loads(proof.read_text())


def lvs(flow):
    from scripts import flow2_integration_common as c
    from scripts.run_flow2_wrapper_transistor_lvs import validate_netgen
    source,views,design,run,settings,pdk=inputs(flow)
    if 'gds_geometry_proof' not in flow.outputs:raise ValueError('exact GDS geometry proof required before LVS reuse')
    old=flow.root/c.BASE/'chip_gds_signal_lvs_srv_20261023_01/summary.json';data=json.loads(old.read_text())
    physical=c._verified(flow.root,data['physical']);reference=c._verified(flow.root,data['reference'])
    binary=flow.root/c.BUILD/'netgen_tool_srv_20261022_01/install/bin/netgen'
    work=flow.work/'signal_lvs';work.mkdir(exist_ok=True);log=work/'netgen.log'
    flow.run('signal_lvs',[binary,'-batch','lvs',str(physical)+' '+TOP,str(reference)+' '+TOP,
        pdk/'libs.tech/netgen/sky130A_setup.tcl',log],inputs=[old,physical,reference,binary],outputs=[log],cwd=work,timeout_s=90)
    validate_netgen(log.read_text())
    flow.outputs['signal_lvs']=item(log)
    print('Netgen unique signal match; extraction reused through exact full-GDS geometry equivalence. PG/body/transistor scope remains separate.')


def timing(flow):
    from scripts.run_flow2_chip_sta import prototype_sdc,timing_metrics
    from scripts.run_flow2_wrapper_postroute import clock_model
    source,views,design,run,settings,pdk=inputs(flow)
    work=flow.work/'timing';work.mkdir(exist_ok=True)
    config=dict(re.findall(r'^set ::env\(([^)]+)\) "([^\n]*)"$',(run/'config.tcl').read_text(),re.M))
    sdc=work/'prototype.sdc';sdc.write_text(prototype_sdc(Path(config['CURRENT_SDC']).read_text(),40))
    spef=work/(TOP+'.spef');rawlib=work/(TOP+'.raw.lib');library=work/(TOP+'.digital_tt.lib');script=work/'timing.tcl'
    rcx=work/'rcx.tcl'
    rcx.write_text(f'read_liberty {{{config["LIB_TYPICAL"]}}}\nread_db {{{views["odb"]}}}\nset_thread_count 8\n'
        f'define_process_corner -ext_model_index 0 X\nextract_parasitics -ext_model_file {{{config["RCX_RULES"]}}} -lef_res\n'
        f'write_spef {{{spef}}}\nputs AUTOMX_RCX_DONE\nexit\n')
    flow.run('rcx',flow.container('openroad',['-exit',rcx],'rcx',work),inputs=[rcx,views['odb'],Path(config['LIB_TYPICAL']),Path(config['RCX_RULES'])],outputs=[spef],cwd=work,timeout_s=180)
    base=f'read_liberty {{{config["LIB_TYPICAL"]}}}\nread_db {{{views["odb"]}}}\nread_sdc {{{sdc}}}\nread_spef {{{spef}}}\nset_propagated_clock [all_clocks]\n'
    script.write_text(base+
        'check_setup -verbose\nreport_parasitic_annotation\nputs AUTOMX_SETUP_BEGIN\nreport_worst_slack -max\nputs AUTOMX_SETUP_END\n'
        'puts AUTOMX_HOLD_BEGIN\nreport_worst_slack -min\nputs AUTOMX_HOLD_END\n'
        'report_checks -path_delay min_max -group_count 3\nreport_check_types -max_slew -max_capacitance -max_fanout -violators\n'
        'puts AUTOMX_CHIP_STA_DONE\nexit\n')
    result=flow.run('timing',flow.container('openroad',['-exit',script],'timing',work),
        inputs=[script,views['odb'],sdc,spef,Path(config['LIB_TYPICAL'])],cwd=work,timeout_s=180)
    # The pinned OpenSTA can crash exporting an ETM after filtered path reports;
    # export in a fresh process using the identical ODB/SPEF/SDC instead.
    etm=work/'etm.tcl';etm.write_text(base+f'write_timing_model {{{rawlib}}}\nputs AUTOMX_ETM_DONE\nexit\n')
    flow.run('etm',flow.container('openroad',['-exit',etm],'etm',work),
        inputs=[etm,views['odb'],sdc,spef,Path(config['LIB_TYPICAL'])],outputs=[rawlib],cwd=work,timeout_s=180)
    metrics=timing_metrics(Path(result['log']['path']).read_text())
    if min(metrics.values())<0:raise ValueError('nominal digital setup/hold fail')
    library.write_text(clock_model(rawlib.read_text(),'clk_i'))
    flow.outputs.update({k:item(p) for k,p in (('spef',spef),('lib',library),('sdc',sdc))})
    flow.outputs['nominal_timing']={**metrics,'frequency_mhz':25,'scope':'TT constrained digital paths; analog arcs, coverage/slew/fanout and other PVT corners remain open.'}
    print('Fresh nominal timing:',metrics)
    return metrics


def power(flow):
    source,views,design,run,settings,pdk=inputs(flow)
    work=flow.work/'power';work.mkdir(exist_ok=True);output=work/'power.json'
    script=flow.root/'scripts/flow2_chip_pg_check.py'
    library=pdk/'libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    flow.run('power',flow.container('openroad',['-exit','-python',script,'--odb',views['odb'],'--lib',library,'--output',output],'power',work),
        inputs=[script,views['odb'],library],outputs=[output],cwd=work,timeout_s=120)
    report=json.loads(output.read_text())
    if report['status']!='PG_CONNECTED_EQUIVALENT_GEOMETRY' or report['geometry_changed'] or report['published_views_changed']:
        raise ValueError('PG connectivity failed')
    flow.outputs['power']=item(output);print(json.dumps(report,indent=2));return report


def parse_library(flow):
    work=flow.work/'timing';library=Path(flow.outputs['lib']['path']);script=work/'parse.tcl'
    script.write_text(f'read_liberty {{{library}}}\nif {{[llength [get_lib_cells */{TOP}]] != 1}} {{exit 2}}\nputs AUTOMX_RUNALL_LIB_PARSE_DONE\nexit\n')
    report=flow.run('lib_parse',flow.container('sta',['-exit',script],'lib_parse',work),inputs=[script,library],cwd=work,timeout_s=60)
    text=Path(report['log']['path']).read_text()
    if 'AUTOMX_RUNALL_LIB_PARSE_DONE' not in text or 'Error:' in text:raise ValueError('OpenSTA Liberty parse failed')
    return report


def synthesize_sar(flow):
    _,_,_,run,_,_=inputs(flow)
    work=flow.work/'sar_synthesis';work.mkdir(exist_ok=True)
    folder=flow.root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition/verilog/rtl'
    files=[folder/p for p in ('adc_control_nonbinary.v','adc_row_col_decoder.v','adc_osr.v','adc_core_digital.v')]
    lib=run/'tmp/synthesis/trimmed.lib';script=work/'synthesize.ys';mapped=work/'adc_core_digital.mapped.v'
    script.write_text(f'read_liberty -lib "{lib}"\n'+''.join(f'read_verilog "{p}"\n' for p in files)+
        'hierarchy -check -top adc_core_digital\nsynth -top adc_core_digital -flatten\n'+
        f'dfflibmap -liberty "{lib}"\nabc -liberty "{lib}"\nclean\ncheck -assert\nselect -assert-none t:$*\nstat -liberty "{lib}"\nwrite_verilog -noattr -noexpr "{mapped}"\n')
    result=flow.run('sar_synthesis',flow.container('yosys',['-s',script],'sar_synthesis',work),inputs=[script,lib,*files],outputs=[mapped],cwd=work,timeout_s=180)
    flow.outputs['mapped_sar']=item(mapped)
    print('Fresh synthesis of the same upstream SAR RTL used by the transistor co-simulation; not a replacement routed ADC macro.')
    return result
