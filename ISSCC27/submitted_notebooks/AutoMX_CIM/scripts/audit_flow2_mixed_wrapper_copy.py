#!/usr/bin/env python3
"""Read-only native-result audit; no simulator or physical tool is launched."""
from __future__ import annotations
import argparse
import json
from hashlib import sha256
from pathlib import Path
import re
import sys
from zipfile import ZipFile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import run_flow2_mixed_wrapper as campaign
from scripts import run_flow2_conditioner as cond
from scripts import flow2_waveforms as waves


def audit(source):
    source=Path(source).resolve()
    index_path=source/'export.json'
    index=json.loads(index_path.read_text(encoding='utf-8'))
    for item in index['files']:
        p=(source/item['path']).resolve()
        if not p.is_relative_to(source) or not p.is_file() or campaign.common._sha(p)!=item['sha256']:
            raise ValueError('downloaded artifact differs: '+item['path'])
    archive=source/Path(index['archive']['path']).name
    if not archive.is_file() or campaign.common._sha(archive)!=index['archive']['sha256']:
        raise ValueError('downloaded diagnostics ZIP differs')
    with ZipFile(archive) as z:
        bad=z.testzip()
        if bad:raise ValueError('diagnostics ZIP CRC failed: '+bad)
    report=json.loads((source/'summary.json').read_text(encoding='utf-8'))
    child=report['child_tags'];block=report['branches']['conditioner']
    raw=source/campaign.common.BUILD/child['conditioner']/'tt_schematic_0/attempt_000/conditioner.raw'
    measured=cond.analyze_point(raw)
    bench=(raw.parent/'bench.spice').read_text(encoding='utf-8')
    native_ref=re.search(r'(?m)^\.include "([^"]+)"',bench)[1]
    native_root=native_ref.split('/physical/')[0]
    views={}
    for kind,item in zip(('nfet','pfet','cap'),block['inputs']['sources'][:3]):
        path=Path(native_root+'/'+item['path']);views[kind]={'cell':path.stem,'gds':path}
    topology={'same_layout_recipe':sha256(cond.layout(ROOT,views).encode()).hexdigest()==block['inputs']['layout'],
              'same_reference':sha256(cond.design.schematic().encode()).hexdigest()==block['inputs']['reference']}
    if not all(topology.values()):raise ValueError('conditioner topology changed; do not reuse old native checks')
    adcbase=source/campaign.common.BUILD/child['adc_c_only']/'negative/sessions'
    latest=sorted(adcbase.glob('attempt_*/segment_*.raw'))
    latest=max(latest,key=lambda p:float(waves.read_raw(p)['time'][-1])) if latest else None
    adc={'status':report['branches']['adc_c_only']['status'],'scope':'incomplete trajectory; no later behavior inferred'}
    if latest:
        v=waves.read_raw(latest);time=v['time'];after=time>=20e-9
        adc.update(raw=latest.relative_to(source).as_posix(),raw_sha256=campaign.common._sha(latest),
                   last_raw_s=float(time[-1]),points=len(time))
        adc['post_start_maxima_v']={n:float(np.max(v[n][after])) for n in ('v(eoc)','v(eoc_osr)')}
        adc['fresh_1p62V_rising_edges']={n:int(np.sum((v[n][1:]>=1.62)&(v[n][:-1]<1.62)&(time[1:]>=22e-9)))
                                         for n in ('v(eoc)','v(eoc_osr)')}
        native=latest.parent/'native.log'
        refs=re.findall(r'Reference value\s*:\s*([+\-\d.eE]+)',native.read_text(errors='replace'))
        adc['last_solver_reference_s']=float(refs[-1]) if refs else None
    return {'format':'automx-cim-mixed-wrapper-native-copy-review-v1',
        'source':str(source),'source_summary_sha256':campaign.common._sha(source/'summary.json'),
        'export_verified_files':len(index['files']),'zip_crc':'PASS',
        'rtl':report['branches']['rtl']['status'],
        'conditioner_physical':{k:block.get(k) for k in ('status','magic_drc_violations','klayout_drc_violations','transistor_lvs_match','parasitics','substrate_rc_audit')},
        'conditioner_completed_raw_reanalysis':measured,
        'physical_reuse_source_identity':topology,
        'conditioner_previous_parser_error':block.get('electrical'),
        'adc':adc,'gds':report['branches']['gds'],
        'not_signoff':'one conditioner schematic point recovered; other seven points, top wrapper native flow and ADC acceptance remain pending'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'server_results/flow2_wrapper_integration/mixed_wrapper_20261020_01')
    p.add_argument('--output',type=Path,default=ROOT/'docs/flow2_mixed_wrapper_01_review_20261020.json')
    a=p.parse_args();r=audit(a.source)
    if not a.output.resolve().is_relative_to(ROOT):raise ValueError('review output must stay in checkout')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,indent=2))
