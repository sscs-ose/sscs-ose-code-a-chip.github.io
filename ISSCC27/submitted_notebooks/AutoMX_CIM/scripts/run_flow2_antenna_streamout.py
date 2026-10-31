#!/usr/bin/env python3
"""Stream a separately named antenna prototype after clean ODB/signal LVS.

Uses pinned OpenLane KLayout streamout and real cell GDS, never LEF boxes as
physical macros. Canonical signoff/baseline are unchanged; no PG/transistor or
analog qualification inferred from signal-only LVS.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post


def component_masters(path):
    counts=Counter();active=False;declared=None
    with Path(path).open() as stream:
        for line in stream:
            if line.startswith('COMPONENTS '):active=True;declared=int(line.split()[1]);continue
            if line.startswith('END COMPONENTS'):break
            if active and line.lstrip().startswith('- '):counts[line.split()[2]]+=1
    if declared is None or sum(counts.values()) != declared:
        raise ValueError('complete DEF component inventory required')
    return dict(counts)


def validate_streamout_log(text):
    if 'Macro not found in LEF' in text or 'All LEF cells have matching GDS cells.' not in text:
        raise ValueError('missing real LEF/GDS cells in streamout')


def run(root, *, tag, candidate_tag, signal_lvs_tag, execute=False, prepared_tag=None):
    root=Path(root).resolve()
    for value in (tag,candidate_tag,signal_lvs_tag):common.tag_ok(value)
    if (root/common.BASE/tag/'inputs.json').exists():raise FileExistsError('fresh streamout tag required')
    source_path=root/common.BASE/candidate_tag/'summary.json';data=json.loads(source_path.read_text())
    lvs_path=root/common.BASE/signal_lvs_tag/'summary.json';lvs=json.loads(lvs_path.read_text())
    if (data.get('independent_drc_bytes') != 0 or
            data.get('preservation',{}).get('status') != 'PASS_PRESERVATION_ONLY' or
            lvs.get('status') != 'SIGNAL_ONLY_DEF_LEF_LVS_MATCH_NO_PG_BODY_QUALIFICATION' or
            lvs.get('candidate_tag') != candidate_tag):
        raise ValueError('independent DRC0, preservation and exact candidate signal LVS required')
    odb=common._verified(root,data['candidate_odb'])
    ground_path=root/common.BASE/data['ground_tag']/'summary.json';ground=json.loads(ground_path.read_text())
    baseline=common._verified(root,ground['views']['gds'])
    native=root/common.BUILD/ground['source_tag']/'design'
    config=native/'config.json';settings=json.loads(config.read_text());lefs=list(map(Path,settings['EXTRA_LEFS']))
    pdk=post.native.notebook.DEFAULT_PDK/'sky130A'
    lefs=[pdk/'libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef',
          pdk/'libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef',
          pdk/'libs.ref/sky130_fd_sc_hd/lef/sky130_ef_sc_hd.lef',*lefs]
    stream=post.native.notebook.DEFAULT_SOURCE/'scripts/klayout/stream_out.py'
    tech=pdk/'libs.tech/klayout/tech';deck=pdk/'libs.tech/klayout/drc/sky130A_mr.drc'
    placement_worker=root/'scripts/check_flow2_gds_placements.py'
    sources=[common._item(root,p) for p in (source_path,lvs_path,ground_path,odb,baseline,config,Path(__file__),placement_worker)]
    prepared=None
    if prepared_tag:
        common.tag_ok(prepared_tag)
        previous_path=root/common.BASE/prepared_tag/'summary.json';previous=json.loads(previous_path.read_text())
        if (previous['candidate_tag'] != candidate_tag or
                previous.get('checks',{}).get('export',{}).get('returncode') != 0 or
                common._item(root,odb) not in previous['sources']):
            raise ValueError('prepared DEF/LEF must come from the exact candidate ODB')
        prepared=[root/common.BUILD/prepared_tag/(post.TOP+'.'+kind) for kind in ('def','lef')]
        sources += [common._item(root,p) for p in (previous_path,*prepared)]
    report={'format':'automx-cim-antenna-streamout-prototype-v1','tag':tag,'candidate_tag':candidate_tag,
        'signal_lvs_tag':signal_lvs_tag,'status':'PREPARED','qualification':'NOT_QUALIFIED',
        'baseline_changed':False,'sources':sources,'antenna':{k:data['antenna'][k] for k in ('net_violations','pin_violations')},
        'native_ordering_delta':data['connectivity_delta'],
        'scope':'Separate GDS prototype from independently clean ODB and signal-only DEF/LEF LVS. '
                'No GDS-extracted full-PG/body/transistor LVS/PEX, new STA, ADC or analog qualification.'}
    if not execute:return report
    required=(384 if prepared else 512)*1024**2
    if shutil.disk_usage(root).free < required:raise ValueError('insufficient free disk for streamout: '+str(required))
    identity={'sources':sources,'streamout_script':{'path':str(stream),'sha256':common._sha(stream)},
              'layer_map_sha256':common._sha(tech/'sky130A.map'),'deck_sha256':common._sha(deck),
              'lefs':[{'path':str(p),'sha256':common._sha(p)} for p in lefs],
              'prepared_tag':prepared_tag,'streamout_image':post.native.notebook.DEFAULT_IMAGE,
              'klayout_host_version':subprocess.check_output(['klayout','-b','-v'],text=True,
                  env=dict(os.environ,QT_QPA_PLATFORM='offscreen')).strip()}
    store=common.Store(root,tag,identity);frozen=store.build/'executed_host_sources';frozen.mkdir()
    (frozen/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (frozen/placement_worker.name).write_bytes(placement_worker.read_bytes())
    report['checks']={}
    def step(name,cmd,budget=120,env=None):
        def invoke(work):
            try:return subprocess.run(cmd,cwd=store.build,text=True,capture_output=True,timeout=budget,
                                      env=env if env is not None else dict(os.environ,QT_QPA_PLATFORM='offscreen'))
            except subprocess.TimeoutExpired as error:
                if cmd[0]=='docker':subprocess.run(['docker','rm','-f',cmd[cmd.index('--name')+1]],capture_output=True,timeout=15)
                value=error.stdout or b''
                if isinstance(value,bytes):value=value.decode(errors='replace')
                return subprocess.CompletedProcess(cmd,124,value,'\nBOUNDED_TIMEOUT\n')
        result,_=store.step(name,cmd,executor=invoke);report['checks'][name]={'returncode':result.returncode,'log':common._item(root,store.folder/(name+'.log'))}
        common.save_summary(store.folder/'summary.json',report)
        if result.returncode:raise ValueError(name+' failed: '+str(result.returncode))
        return result.stdout+result.stderr
    def container(program,args,name):
        cmd=post.container_command(root,program,args,'automx-'+tag+'-'+name);cmd[cmd.index('-w')+1]=str(store.build);return cmd
    gds=store.build/(post.TOP+'.gds');lef=store.build/(post.TOP+'.lef');definition=store.build/(post.TOP+'.def')
    try:
        if prepared:
            definition,lef=prepared
            report['checks']['export']={'returncode':0,'reused_from':prepared_tag}
        else:
            tcl=store.build/'export.tcl';tcl.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(definition)+'}\nwrite_abstract_lef {'+str(lef)+'}\nputs AUTOMX_FULL_EXPORT_DONE\nexit\n')
            text=step('export',container('openroad',['-exit',tcl],'export'),60)
            if 'AUTOMX_FULL_EXPORT_DONE' not in text:raise ValueError('native DEF/LEF export incomplete')
        library=store.build/'library.gds';script=store.build/'library.py'
        script.write_text('import pya\nl=pya.Layout()\nl.read('+repr(str(baseline))+')\n'
            'c=l.cell('+repr(post.TOP)+')\nassert c is not None\nl.delete_cell(c.cell_index())\n'
            'assert l.cell('+repr(post.TOP)+') is None\nl.write('+repr(str(library))+')\n')
        step('library',['klayout','-b','-r',str(script)],60)
        args={'input':definition,'output':gds,'design_name':post.TOP,'input_lefs':';'.join(map(str,lefs)),
              'input_gds_files':library,'seal_gds':'NULL','lyt':tech/'sky130A.lyt','lyp':tech/'sky130A.lyp','lym':tech/'sky130A.map'}
        cmd=['klayout','-b','-rm',str(stream)]
        for key,value in args.items():cmd+=['-rd',key+'='+str(value)]
        cmd=container('klayout',cmd[1:],'streamout')
        text=step('streamout',cmd,120)
        validate_streamout_log(text)
        expected=store.build/'expected_masters.json';expected.write_text(json.dumps(component_masters(definition)))
        audit=store.build/'audit.py'
        audit.write_text('import pya,json\nfrom collections import Counter\n'
            'l=pya.Layout();l.read('+repr(str(gds))+')\nt=l.cell('+repr(post.TOP)+')\nassert t is not None\n'
            'expected=json.load(open('+repr(str(expected))+'))\nactual=Counter()\n'
            'for inst in t.each_inst():\n name=inst.cell.name\n if name in expected:actual[name]+=inst.na*inst.nb if inst.is_regular_array() else 1\n'
            'assert dict(actual)==expected,(actual,expected)\n'
            'json.dump({"status":"ALL_DEF_COMPONENTS_PRESENT","instances":sum(actual.values()),"masters":len(actual)},open('+repr(str(store.build/'instance_audit.json'))+',"w"),indent=2)\n')
        step('instance_audit',['klayout','-b','-r',str(audit)],60)
        report['instance_audit']=json.loads((store.build/'instance_audit.json').read_text())
        placement=store.build/'placement_check.py'
        placement_output=store.build/'placement_audit.json'
        arguments=[str(placement_worker),'--baseline',str(baseline),'--candidate',str(gds),
                   '--masters',str(expected),'--diodes',str(data['preservation']['after']['new_diodes']),
                   '--output',str(placement_output)]
        placement.write_text('import sys,runpy\nsys.argv='+repr(arguments)+'\nrunpy.run_path('
                             +repr(str(placement_worker))+',run_name="__main__")\n')
        step('placement_audit',['klayout','-b','-r',str(placement)],60)
        report['placement_audit']={'report':common._item(root,placement_output),
            'worker':common._item(root,placement_worker),'baseline':common._item(root,baseline),
            'candidate':common._item(root,gds)}
        xml=store.build/'klayout.xml'
        step('klayout',container('klayout',['-b','-r',deck,'-rd','input='+str(gds),'-rd','report='+str(xml),'-rd','feol=true','-rd','beol=true','-rd','offgrid=true'],'drc'),180)
        tree=ET.parse(xml).getroot()
        if tree.tag != 'report-database':raise ValueError('invalid KLayout report')
        from scripts.flow2_klayout_checks import summarize
        measured=summarize(xml);violations=measured['violations'];report['klayout_violations']=violations
        report['klayout_rule_groups']={'feol':True,'beol':True,'offgrid':True}
        if violations:raise ValueError('streamed GDS KLayout DRC is not zero')
        store.physical.mkdir(parents=True)
        for path in (gds,lef):os.link(path,store.physical/path.name)
        report.update(status='GDS_PROTOTYPE_KLAYOUT_CLEAN_SIGNAL_LVS_ONLY',
                      views={key:common._item(root,p) for key,p in [('gds',store.physical/gds.name),('lef',store.physical/lef.name),('def',definition),('odb',odb)]})
        env=os.environ.copy();env.update(QT_QPA_PLATFORM='offscreen',AUTOMX_GDS=str(gds),AUTOMX_PNG=str(store.folder/'top.png'),AUTOMX_TOP=post.TOP)
        step('render',['klayout','-z','-x','-r',str(root/'scripts/render_flow2_wrapper_gds.py')],60,env)
        report['png']=common._item(root,store.folder/'top.png')
        for item in sources:common._verified(root,item)
    except Exception as error:report.update(status='BLOCKED_ANTENNA_STREAMOUT',error=type(error).__name__+': '+str(error))
    finally:common.save_summary(store.folder/'summary.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--tag',required=True);p.add_argument('--candidate-tag',required=True);p.add_argument('--signal-lvs-tag',required=True)
    p.add_argument('--prepared-tag',help='reuse completed native DEF/LEF export after a streamout-only failure')
    p.add_argument('--run',action='store_true');a=p.parse_args();r=run(a.root,tag=a.tag,candidate_tag=a.candidate_tag,signal_lvs_tag=a.signal_lvs_tag,execute=a.run,prepared_tag=a.prepared_tag)
    print(json.dumps(r,indent=2))
    if a.run and r['status']!='GDS_PROTOTYPE_KLAYOUT_CLEAN_SIGNAL_LVS_ONLY':raise SystemExit(1)
