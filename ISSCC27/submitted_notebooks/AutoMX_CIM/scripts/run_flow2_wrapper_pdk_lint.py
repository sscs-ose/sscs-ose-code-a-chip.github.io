#!/usr/bin/env python3
"""Fast full-top lint using the actual pinned OpenLane container and PDK.

This uses real PDK Verilog definitions through OpenLane's run_verilator,
with an independent run directory. No TB buffer fixture, SPICE, placement
or routing is used and the failed source run remains unchanged.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_mixed_wrapper_gds as gds
from scripts import run_notebook_core_bound as notebook
from scripts import run_flow2_acquisition_layout as acq

SOURCE=common.BUILD/'mixed_wrapper_20261020_02_gds/design'


def probe_tcl(work, tag, *, synthesis=False):
    if any(c in Path(work).as_posix() for c in '{}\n\r'):raise ValueError('unsupported probe path')
    common.tag_ok(tag)
    lines=['package require openlane',f'prep -design {{{Path(work).as_posix()}}} -tag {tag}']
    for key in gds.PDK_GATE_SETTINGS:
        lines.append(f'if {{$::env({key}) != 1}} {{error "required library/lint gate disabled: {key}"}}')
    lines+=['run_verilator','puts AUTOMX_FULL_WRAPPER_PDK_LINT_PASS']
    if synthesis:
        lines+=['run_synthesis','puts AUTOMX_FULL_WRAPPER_PDK_SYNTHESIS_PASS']
    return '\n'.join([*lines,''])


def run(root, *, source_design=None, tag='wrapper_pdk_lint_20261020_01',execute=False,timeout_s=180,synthesis=False,
        openlane_source=notebook.DEFAULT_SOURCE,openlane_pdk=notebook.DEFAULT_PDK):
    root=Path(root).resolve();common.tag_ok(tag)
    source=Path(source_design).resolve() if source_design else root/SOURCE
    if not source.is_relative_to(root):raise ValueError('source design must stay in checkout')
    conf=json.loads((source/'config.json').read_text(encoding='utf-8'))
    if conf.get('DESIGN_NAME')!=gds.d.TOP:raise ValueError('full mixed-wrapper top required')
    conf.update(gds.PDK_GATE_SETTINGS)
    report={'status':'PREPARED','top':gds.d.TOP,'synthesis_requested':synthesis,
            'scope':'native full-top PDK lint/synthesis; no routing or analog signoff'}
    if not execute:return dict(report,configuration=conf)
    if sys.platform!='linux':raise RuntimeError('native PDK lint runs on prepared Linux server only')
    notebook._requirements(root,Path(openlane_source),Path(openlane_pdk),notebook.DEFAULT_IMAGE)
    sources=[source/'config.json',*[Path(p) for p in conf['VERILOG_FILES']],Path(conf['VERILOG_FILES_BLACKBOX'])]
    library=Path(openlane_pdk)/'sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    if not library.is_file():raise FileNotFoundError(library)
    store=common.Store(root,tag,{'sources':[acq._item(root,p) for p in sources],
        'flags':gds.PDK_GATE_SETTINGS,'runner':common._sha(Path(__file__)), 'synthesis':synthesis,
        'image':notebook.DEFAULT_IMAGE,'openlane_pdk':str(openlane_pdk),
        'stdcell_liberty_sha256':common._sha(library)})
    name='automx-pdk-lint-'+tag.lower()
    try:
        script=store.build/'native_lint/lint.tcl'
        cmd=notebook.docker_command(root,tag,Path(openlane_source),Path(openlane_pdk),notebook.DEFAULT_IMAGE)
        cmd=cmd[:cmd.index(notebook.DEFAULT_IMAGE)+1]+['-interactive','-file',str(script)]
        cmd[2:2]=['--name',name]
        def execute_probe(work):
            common._save(work/'config.json',conf)
            script.write_text(probe_tcl(work,tag,synthesis=synthesis),encoding='utf-8')
            try:return acq.stage5._run(cmd,work,timeout_s)
            finally:
                # Stop only this probe's container, including after Ctrl+C.
                try:subprocess.run(['docker','stop','--time','5',name],stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,timeout=15,check=False)
                except (OSError,subprocess.TimeoutExpired):pass
        result,_=store.step('native_lint',cmd,executor=execute_probe)
        if result.returncode or 'AUTOMX_FULL_WRAPPER_PDK_LINT_PASS' not in result.stdout:
            raise RuntimeError('full-wrapper PDK lint failed; inspect native_lint.log')
        if synthesis and 'AUTOMX_FULL_WRAPPER_PDK_SYNTHESIS_PASS' not in result.stdout:
            raise RuntimeError('full-wrapper native synthesis failed; inspect native_lint.log')
        report.update(status='PASS_FULL_WRAPPER_PDK_SYNTHESIS' if synthesis else 'PASS_FULL_WRAPPER_PDK_LINT',inputs=store.identity)
    except KeyboardInterrupt:
        report['status']='INTERRUPTED_FULL_WRAPPER_PDK_LINT';raise
    except Exception as error:report.update(status='BLOCKED_FULL_WRAPPER_PDK_LINT',error=f'{type(error).__name__}: {error}')
    finally:
        common.save_summary(store.folder/'summary.json',report);common.bundle(root,tag)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--source-design',type=Path);p.add_argument('--tag',default='wrapper_pdk_lint_20261020_01')
    p.add_argument('--run',action='store_true');p.add_argument('--timeout-s',type=int,default=180)
    p.add_argument('--synthesis',action='store_true',help='run actual OpenLane Yosys synthesis after lint')
    a=p.parse_args();r=run(a.root,source_design=a.source_design,tag=a.tag,execute=a.run,timeout_s=a.timeout_s,synthesis=a.synthesis)
    print(json.dumps(r,indent=2))
    if a.run and r['status']!=('PASS_FULL_WRAPPER_PDK_SYNTHESIS' if a.synthesis else 'PASS_FULL_WRAPPER_PDK_LINT'):raise SystemExit(1)
