#!/usr/bin/env python3
"""Render existing wrapper input macros to PNG while OpenLane runs separately.

Reads the active run's EXTRA_GDS_FILES; never writes into its design, inputs,
run directory, checkpoints or physical views. Requires the existing native
KLayout renderer, not a new EDA installation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
RUN_TAG='mixed_wrapper_20261021_05_impl_gds'
RENDERER=Path('scripts/render_flow2_wrapper_gds.py')
PNG_HEADER=b'\x89PNG\r\n\x1a\n'


def digest(path):
    h=sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def catalog(root,config_path,*,leaves=False):
    root=Path(root).resolve();config_path=Path(config_path).resolve()
    conf=json.loads(config_path.read_text(encoding='utf-8'))
    if conf.get('DESIGN_NAME')!='automx_cim_mixed_signal_proto':
        raise ValueError('select the mixed-wrapper design config.json')
    sources=conf.get('EXTRA_GDS_FILES')
    if not isinstance(sources,list) or len(sources)<3:
        raise ValueError('need at least CIM, conditioner and ADC input GDS files')
    jobs=[]
    def add(name,title,path,cell,required=True):
        path=Path(path)
        if not path.is_absolute():path=root/path
        path=path.resolve()
        jobs.append({'name':name,'title':title,'source':str(path),'cell':cell,
                     'required':required,'available':path.is_file() and path.stat().st_size>0})
    for src,(name,title,cell) in zip(sources,[
        ('01_core_acquisition','Core CIM + physical acquisition / sample-and-hold',
         'automx_cim_core_acquisition_proto'),
        ('02_conditioner_mux','Conditioner, bias and differential mux',
         'automx_cim_condition_mux_proto'),
        ('03_adc_reference','SAR ADC with its native reference circuitry','adc_top'),
        ('08_mha','MHA: QK transpose, softmax, context and projection control','automx_mha_ip'),
        ('09_readout','Readout, SAR sequencing and calibration','automx_cim_readout_seq')]):
        add(name,title,src,cell)
    add('04_passive_core','Stage-5 passive CIM core (standalone reference)',
        root/'physical/sky130/macro/automx_ternary_cim_4x4_core.gds',
        'automx_ternary_cim_4x4_core',False)
    if leaves:
        base=root/'physical/sky130/wrapper_prototype/leaf_cells'
        for name,title,relative,cell in [
            ('05_sample_nfet','Sampling NFET, 3.36 um','sample_fet_20261017_03/nfet/automx_cim_sample_nfet_3p36.gds','automx_cim_sample_nfet_3p36'),
            ('06_sample_pfet','Sampling PFET, 3.36 um','sample_fet_20261017_03/pfet/automx_cim_sample_pfet_3p36.gds','automx_cim_sample_pfet_3p36'),
            ('07_hold_mim','Physical MIM hold capacitor','hold_cap_mim3_20261017_02/automx_cim_hold_cap_mim3_approx20ff.gds','automx_cim_hold_cap_mim3_approx20ff')]:
            add(name,title,base/relative,cell,False)
    return jobs


def gallery(folder,report):
    cards=[]
    for job in report['jobs']:
        title=escape(job['title']);cell=escape(job['cell']);source=escape(job['source'])
        picture=(f'<a href="{job["png"]}"><img src="{job["png"]}" alt="{title}"></a>'
                 if job['status']=='RENDERED' else '<p>'+escape(job.get('error',job['status']))+'</p>')
        cards.append(f'<section><h2>{title}</h2>{picture}<p><code>{cell}</code></p>'
                     f'<details><summary>Source GDS</summary><code>{source}</code></details></section>')
    html='''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AutoMX-CIM physical components</title>
<style>body{font-family:system-ui;margin:24px;background:#f3f5f7;color:#202630}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px}
section{background:white;border:1px solid #dce1e7;border-radius:10px;padding:16px}
h2{font-size:18px}img{width:100%;height:340px;object-fit:contain}code{overflow-wrap:anywhere}
</style><h1>AutoMX-CIM: actual physical component layouts</h1>
<p>Existing input GDS, rendered by KLayout. These images are not a DRC/LVS or analog signoff result.</p><main>'''
    (folder/'index.html').write_text(html+'\n'.join(cards)+'</main></html>\n',encoding='utf-8')


def run(root, *, config_path=None,tag=None,leaves=False,execute=False,timeout_s=300):
    root=Path(root).resolve()
    config_path=Path(config_path) if config_path else root/f'build/flow2_wrapper_integration/{RUN_TAG}/design/config.json'
    jobs=catalog(root,config_path,leaves=leaves)
    report={'format':'automx-cim-component-layout-previews-v1','status':'PREPARED',
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'config':str(config_path.resolve()),'jobs':jobs,
        'scope':'existing GDS visualization only; no new physical/analog PASS inferred'}
    if not execute:return report
    if sys.platform!='linux':raise RuntimeError('run on the existing Linux EDA host')
    renderer=root/RENDERER
    if not renderer.is_file():raise FileNotFoundError(renderer)
    tool=shutil.which('klayout')
    if not tool:raise FileNotFoundError('KLayout is not on PATH in this terminal')
    if timeout_s<=0:raise ValueError('positive renderer timeout required')
    tag=tag or 'components_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,79}',tag):raise ValueError('use a simple preview tag')
    folder=root/'server_results/layout_previews'/tag
    if not folder.resolve().is_relative_to(root):raise ValueError('preview destination escapes checkout')
    folder.mkdir(parents=True,exist_ok=False)
    report['output_folder']=str(folder)
    # Positive niceness is inherited by the sequential KLayout children.
    os.nice(10)
    def note(message):
        line=f'[{datetime.now(timezone.utc).isoformat()}] {message}'
        print(line,flush=True)
        with (folder/'history.log').open('a',encoding='utf-8') as f:f.write(line+'\n')
    note('START component PNGs; sequential low-priority renders; active flow inputs are read-only')
    for job in jobs:
        if not job['available']:
            job['status']='MISSING_INPUT' if job['required'] else 'OPTIONAL_INPUT_NOT_PRESENT'
            note(job['name']+': '+job['status']);continue
        src=Path(job['source']);png=folder/(job['name']+'.png');log=folder/(job['name']+'.log')
        job['source_sha256']=digest(src)
        env=os.environ.copy()
        env.update(QT_QPA_PLATFORM='offscreen',AUTOMX_GDS=str(src),
                   AUTOMX_PNG=str(png),AUTOMX_TOP=job['cell'])
        note('RENDER '+job['name']+' from '+str(src))
        try:
            with log.open('w',encoding='utf-8') as stream:
                result=subprocess.run([tool,'-z','-x','-r',str(renderer)],cwd=root,env=env,
                                      stdout=stream,stderr=subprocess.STDOUT,timeout=timeout_s)
            job['returncode']=result.returncode
            if result.returncode or not png.is_file():raise RuntimeError('inspect '+log.name)
            with png.open('rb') as f:
                if f.read(8)!=PNG_HEADER:raise RuntimeError('KLayout did not produce PNG')
            if digest(src)!=job['source_sha256']:raise RuntimeError('input GDS changed during render')
            job.update(status='RENDERED',png=png.name,png_sha256=digest(png))
        except Exception as error:
            job.update(status='RENDER_FAILED',error=f'{type(error).__name__}: {error}')
        note(job['name']+': '+job['status'])
    report['rendered_pngs']=sum(j.get('status')=='RENDERED' for j in jobs)
    report['status']=('COMPONENT_PNGS_READY' if all(j.get('status')=='RENDERED' for j in jobs if j['required'])
                      else 'PARTIAL_COMPONENT_PREVIEWS')
    gallery(folder,report)
    (folder/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    note('END '+report['status']+'; download folder: '+str(folder))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--config',type=Path);p.add_argument('--tag');p.add_argument('--leaves',action='store_true')
    p.add_argument('--run',action='store_true');p.add_argument('--timeout-s',type=int,default=300)
    a=p.parse_args();r=run(a.root,config_path=a.config,tag=a.tag,leaves=a.leaves,execute=a.run,timeout_s=a.timeout_s)
    print(json.dumps(r,indent=2))
    if a.run and r['status']!='COMPONENT_PNGS_READY':raise SystemExit(1)
