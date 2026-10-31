#!/usr/bin/env python3
"""Export a fresh nominal digital ETM from the exact post-ECO ODB and SPEF.

Analog macro timing remains uncharacterized. This is a digital integration
view, not a transistor characterization of the whole mixed-signal chip.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post


def run(root,*,tag,sta_tag,execute=False):
    root=Path(root).resolve();common.tag_ok(tag);common.tag_ok(sta_tag)
    if (root/common.BASE/tag/'inputs.json').exists():raise FileExistsError('fresh ETM tag required')
    receipt=root/common.BASE/sta_tag/'summary.json';data=json.loads(receipt.read_text())
    if data.get('status')!='CHIP_NOMINAL_RC_STA_MEASURED':raise ValueError('completed fresh RC/STA required')
    source=root/common.BASE/data['source_tag']/'summary.json';gds=json.loads(source.read_text())
    odb=common._verified(root,gds['views']['odb']);spef=common._verified(root,data['checks']['rcx']['spef'])
    sdc=common._verified(root,data['sdc'])
    lib=Path(data['external_sources'][0]['path'])
    if common._sha(lib)!=data['external_sources'][0]['sha256']:raise ValueError('Liberty source changed')
    sources=[common._item(root,p) for p in (receipt,source,odb,spef,sdc,Path(__file__))]
    report=dict(status='PREPARED',tag=tag,sta_tag=sta_tag,source_tag=data['source_tag'],sources=sources,
        qualification='NOT_QUALIFIED',scope=__doc__)
    if not execute:return report
    store=common.Store(root,tag,dict(sources=sources,library=data['external_sources'][0],image=post.native.notebook.DEFAULT_IMAGE))
    (store.build/'executed_runner.py').write_bytes(Path(__file__).read_bytes())
    def step(name,program,tcl):
        path=store.build/(name+'.tcl');path.write_text(tcl)
        cmd=post.container_command(root,program,['-exit',path],'automx-'+tag+'-'+name)
        cmd[cmd.index('-w')+1]=str(store.build)
        def invoke(work):
            try:return subprocess.run(cmd,cwd=store.build,text=True,capture_output=True,timeout=90)
            except subprocess.TimeoutExpired as error:
                subprocess.run(['docker','rm','-f','automx-'+tag+'-'+name],capture_output=True,timeout=15)
                out=error.stdout or b''
                if isinstance(out,bytes):out=out.decode(errors='replace')
                return subprocess.CompletedProcess(cmd,124,out,'\nBOUNDED_TIMEOUT\n')
        result,_=store.step(name,cmd,tcl=tcl,executor=invoke)
        if result.returncode:raise ValueError(name+' did not complete')
        return result.stdout+result.stderr
    try:
        raw=store.build/'nominal.raw.lib';view=store.build/(post.TOP+'.digital_tt.lib')
        text=step('export','openroad',f'read_liberty {{{lib}}}\nread_db {{{odb}}}\nread_sdc {{{sdc}}}\n'
            f'read_spef {{{spef}}}\nset_propagated_clock [all_clocks]\nwrite_timing_model {{{raw}}}\n'
            'puts AUTOMX_CHIP_ETM_DONE\nexit\n')
        if 'AUTOMX_CHIP_ETM_DONE' not in text:raise ValueError('ETM export marker missing')
        view.write_text(post.clock_model(raw.read_text(),'clk_i'))
        text=step('parse','sta',f'read_liberty {{{view}}}\n'
            f'if {{[llength [get_lib_cells */{post.TOP}]] != 1}} {{exit 2}}\n'
            'puts AUTOMX_CHIP_ETM_PARSE_DONE\nexit\n')
        if 'AUTOMX_CHIP_ETM_PARSE_DONE' not in text or 'Error:' in text:raise ValueError('ETM parse failed')
        for item in sources:common._verified(root,item)
        report.update(status='FRESH_NOMINAL_DIGITAL_ETM_PARSE_PASS',view=common._item(root,view),
            raw=common._item(root,raw),period_ns=data['period_ns'],corner=data['corner'])
    except Exception as error:report.update(status='BLOCKED_CHIP_ETM',error=type(error).__name__+': '+str(error))
    finally:common.save_summary(store.folder/'summary.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--tag',required=True);p.add_argument('--sta-tag',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    r=run(a.root,tag=a.tag,sta_tag=a.sta_tag,execute=a.run);print(json.dumps(r,indent=2))
    if a.run and r['status']!='FRESH_NOMINAL_DIGITAL_ETM_PARSE_PASS':raise SystemExit(1)
