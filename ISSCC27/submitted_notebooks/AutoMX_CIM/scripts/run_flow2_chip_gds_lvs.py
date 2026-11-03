#!/usr/bin/env python3
"""Bounded GDS routing/macro LVS including explicit power connections.

Actual GDS parent geometry is retained. Native standard-cell maglef and three
analog LEFs replace device interiors; this is NOT full transistor/body LVS.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post
from scripts.run_flow2_wrapper_ground_repair import cached_mag
from scripts.run_flow2_wrapper_transistor_lvs import validate_netgen
from scripts.check_flow2_signal_lvs import signal_spice,signal_verilog


def import_precision_tech(text):
    """Permit 1 nm import precision; retain every extraction and DRC rule byte.

    Native gridlimit=5 otherwise snaps valid 1 nm GDS vertices before LVS.
    This local reader derivative is never used to certify native DRC.
    """
    result,count=re.subn(r'(?m)^(\s*gridlimit\s+)5\s*$',lambda m:m[1]+'1',text)
    if count!=5:raise ValueError('unexpected native gridlimit declarations')
    return result


def filter_pg_instances(source,destination,expected):
    """Keep routing/labels and every signal instance verbatim; drop PG-only interiors.

    Logical export already omits these exact instances. No tap/decap/body
    interior continuity is certified by this macro-boundary comparison.
    """
    removed=Counter();skip=False
    with source.open() as src,destination.open('w') as out:
        for line in src:
            if line.startswith('use '):
                fields=line.split();skip=fields[1] in expected
                if skip:removed[fields[1]]+=1
                elif len(fields)>3:line=' '.join(fields[:3])+'\n'
            elif line.startswith('<<'):skip=False
            if not skip:out.write(line)
    if dict(removed)!=expected:raise ValueError('GDS PG-only inventory differs from logical export')
    return dict(removed)


def run(root, *, tag, source_tag='antenna_streamout_srv_20261022_03', timeout_s=180, execute=False,prepared_tag=None,signal_only=False):
    root=Path(root).resolve();common.tag_ok(tag);common.tag_ok(source_tag)
    if not 1<=timeout_s<=300: raise ValueError('bounded GDS LVS budget required')
    if (root/common.BASE/tag/'inputs.json').exists(): raise FileExistsError('fresh GDS LVS tag required')
    receipt=root/common.BASE/source_tag/'summary.json';data=json.loads(receipt.read_text())
    if data.get('status')!='GDS_PROTOTYPE_KLAYOUT_CLEAN_SIGNAL_LVS_ONLY': raise ValueError('audited GDS required')
    gds=common._verified(root,data['views']['gds'])
    lvs_receipt=root/common.BASE/data['signal_lvs_tag']/'summary.json'
    lvs=json.loads(lvs_receipt.read_text())
    if lvs.get('status')!='SIGNAL_ONLY_DEF_LEF_LVS_MATCH_NO_PG_BODY_QUALIFICATION': raise ValueError('signal source required')
    # Use the powered, unnormalized logical export of this very ODB.
    raw=root/common.BUILD/lvs['source_tag']/'signal_scope.v'
    export=root/common.BUILD/lvs['source_tag']/'export.json'
    omitted=json.loads(export.read_text())['removed_masters']
    native=root/common.BUILD/'mixed_wrapper_srv_20261022_04_impl_gds/design'
    config=native/'config.json';settings=json.loads(config.read_text())
    lefs=[Path(p) for p in settings['EXTRA_LEFS']]
    pdk=post.native.notebook.DEFAULT_PDK/'sky130A'
    netgen=root/common.BUILD/'netgen_tool_srv_20261022_01/install/bin/netgen'
    toolfiles=[netgen,*sorted(netgen.parent.parent.rglob('*.so'))]
    normalizer=Path(signal_spice.__code__.co_filename)
    sources=[common._item(root,p) for p in (receipt,gds,lvs_receipt,raw,export,config,Path(__file__),normalizer,
        ROOT/'scripts/run_flow2_wrapper_ground_repair.py',*lefs,*toolfiles)]
    prepared=None
    if prepared_tag:
        common.tag_ok(prepared_tag)
        prior=root/common.BASE/prepared_tag/'summary.json';pdata=json.loads(prior.read_text())
        plog=root/common.BASE/prepared_tag/'read_gds.log'
        if (pdata.get('source_tag')!=source_tag or common._item(root,gds) not in pdata.get('sources',[]) or
            pdata.get('checks',{}).get('read_gds',{}).get('returncode')!=0 or
            'AUTOMX_GDS_PARENT_SAVED' not in plog.read_text() or 'snapped to grid' in plog.read_text()):
            raise ValueError('completed unsnapped GDS import required for reuse')
        prepared=root/common.BUILD/prepared_tag/'raw_top.mag'
        sources.extend(common._item(root,p) for p in (prior,plog,prepared))
    report=dict(format='automx-cim-chip-gds-macro-lvs-v1',tag=tag,source_tag=source_tag,
        status='PREPARED',qualification='NOT_QUALIFIED',sources=sources,checks={},signal_only=signal_only,
        scope='Actual GDS parent routing with native standard-cell maglef/analog LEF boundaries; '
              'powered ODB logical reference; PG-only interiors omitted on both sides. '
              'No transistor/body/tap/decap interior or RC qualification.')
    if not execute:return report
    store=common.Store(root,tag,dict(sources=sources,timeout_s=timeout_s,signal_only=signal_only,image=post.native.notebook.DEFAULT_IMAGE,
        magic_tech_sha256=common._sha(pdk/'libs.tech/magic/sky130A.tech'),
        netgen_setup_sha256=common._sha(pdk/'libs.tech/netgen/sky130A_setup.tcl')))
    snap=store.build/'executed_host_sources';snap.mkdir()
    (snap/Path(__file__).name).write_bytes(Path(__file__).read_bytes())

    def step(name,cmd,budget=timeout_s):
        def invoke(work):
            try:return subprocess.run(cmd,cwd=store.build,text=True,capture_output=True,timeout=budget)
            except subprocess.TimeoutExpired as error:
                if cmd[0]=='docker': subprocess.run(['docker','rm','-f',cmd[cmd.index('--name')+1]],capture_output=True,timeout=15)
                out=error.stdout or b''
                if isinstance(out,bytes):out=out.decode(errors='replace')
                return subprocess.CompletedProcess(cmd,124,out,'\nBOUNDED_TIMEOUT\n')
        result,_=store.step(name,cmd,executor=invoke)
        report['checks'][name]=dict(returncode=result.returncode,log=common._item(root,store.folder/(name+'.log')))
        common.save_summary(store.folder/'summary.json',report)
        if result.returncode:raise ValueError(name+' incomplete, exit='+str(result.returncode))
        return result.stdout+result.stderr

    def magic(name,tcl):
        path=store.build/(name+'.tcl');path.write_text(tcl)
        cmd=post.container_command(root,'magic',['-dnull','-noconsole','-rcfile',store.build/'magicrc',path], 'automx-'+tag+'-'+name)
        cmd[cmd.index('-w')+1]=str(store.build)
        return step(name,cmd)

    try:
        technology=pdk/'libs.tech/magic/sky130A.tech'
        fine=store.build/'sky130A.tech';fine.write_text(import_precision_tech(technology.read_text()))
        report['reader_technology']=dict(native_path=str(technology),native_sha256=common._sha(technology),
            derived=common._item(root,fine),change='Only five gridlimit 5 declarations -> 1; extraction/DRC rules unchanged',
            native_DRC_qualification=False)
        rc=store.build/'magicrc'
        rc.write_text(f'set ::env(PDK_ROOT) {{{pdk.parent}}}\nset ::env(MAGTYPE) maglef\nsource {{{pdk/"libs.tech/magic/sky130A.magicrc"}}}\ntech load {{{fine}}}\n')
        top=post.TOP
        # Flatten only helper vias so their cut/metal geometry survives saving
        # the parent. Use 1 nm grid in BOTH processes, without snapping GDS.
        if prepared:
            report['reused_gds_import']=prepared_tag
            parent=prepared
        else:
            text=magic('read_gds',f'crashbackups stop\ndrc off\nscalegrid 1 5\ngds rescale yes\ngds flatglob {{VIA*}}\ngds read {{{gds}}}\nload {top}\n'
                f'save {{{store.build/"raw_top.mag"}}}\nputs AUTOMX_GDS_PARENT_SAVED\nquit -noprompt\n')
            if 'AUTOMX_GDS_PARENT_SAVED' not in text:raise ValueError('GDS read incomplete')
            if 'snapped to grid' in text:raise ValueError('GDS geometry was snapped during import')
            parent=store.build/'raw_top.mag'
        clean=store.build/(top+'.mag')
        report['omitted_pg_only_instances_by_master']=filter_pg_instances(parent,clean,omitted)
        report['physical_pg_only_instances_omitted']=sum(omitted.values())
        lines=['crashbackups stop','drc off','scalegrid 1 5',f'lef read {{{pdk/"libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"}}}']
        lines += [f'lef read {{{p}}}' for p in lefs]
        spice=store.build/'gds_macro.spice'
        lines += [f'load {{{clean}}}','select top cell','extract do local','extract no capacitance',
            'extract no coupling','extract no resistance','extract no adjust','extract unique','extract',
            'ext2spice lvs',f'ext2spice -o {{{spice}}}','puts AUTOMX_GDS_MACRO_EXTRACT_DONE','quit -noprompt']
        text=magic('extract','\n'.join(lines)+'\n')
        if 'AUTOMX_GDS_MACRO_EXTRACT_DONE' not in text or not spice.is_file():raise ValueError('GDS extraction incomplete')
        # Never claim a match if a referenced standard cell was missing.
        if 'couldn\'t be read' in text or 'not found' in text.lower():raise ValueError('unresolved layout cells')
        comparison,reference=spice,raw
        if signal_only:
            ptext,scope=signal_spice(spice.read_text())
            vtext,count=signal_verilog(raw.read_text(),scope['removed_ports_by_master'])
            if not count or count!=scope['standard_instances']:raise ValueError('signal instance inventory differs')
            comparison=store.build/'signal_only.spice';comparison.write_text(ptext)
            reference=store.build/'signal_only.v';reference.write_text(vtext)
            report['normalization']=scope
            report['scope']+=' Standard-cell formal PG/body ports omitted on both sides; analog PG and rail-tied signal inputs retained.'
        log=store.build/'netgen.log'
        text=step('lvs',[str(netgen),'-batch','lvs',str(comparison)+' '+top,str(reference)+' '+top,
            str(pdk/'libs.tech/netgen/sky130A_setup.tcl'),str(log)],120)
        validate_netgen(log.read_text()+'\n'+text)
        report.update(status='GDS_SIGNAL_MACRO_LVS_MATCH_NO_STANDARD_PG_BODY_QUALIFICATION' if signal_only else 'GDS_POWERED_MACRO_LVS_MATCH',
            physical_spice=common._item(root,comparison),reference=common._item(root,reference),lvs_log=common._item(root,log))
        for source in sources:common._verified(root,source)
    except Exception as error:report.update(status='BLOCKED_CHIP_GDS_MACRO_LVS',error=type(error).__name__+': '+str(error))
    finally:common.save_summary(store.folder/'summary.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--tag',required=True);p.add_argument('--source-tag',default='antenna_streamout_srv_20261022_03')
    p.add_argument('--timeout-s',type=int,default=180);p.add_argument('--prepared-tag')
    p.add_argument('--signal-only',action='store_true')
    p.add_argument('--run',action='store_true');a=p.parse_args()
    r=run(a.root,tag=a.tag,source_tag=a.source_tag,timeout_s=a.timeout_s,execute=a.run,prepared_tag=a.prepared_tag,signal_only=a.signal_only)
    print(json.dumps(r,indent=2))
    if a.run and r['status'] not in ('GDS_POWERED_MACRO_LVS_MATCH','GDS_SIGNAL_MACRO_LVS_MATCH_NO_STANDARD_PG_BODY_QUALIFICATION'):raise SystemExit(1)
