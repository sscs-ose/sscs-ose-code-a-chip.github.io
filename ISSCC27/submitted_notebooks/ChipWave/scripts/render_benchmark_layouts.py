"""Render actual delivered GDS representatives at one common physical scale."""
import argparse
import json
import os
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from study_protocol import digest,ranking,write_json

CASE=Path(__file__).resolve().parents[1]


def render(results,output):
    results,output=Path(results).resolve(),Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    data=json.loads((results/'analysis.json').read_text())
    cases=[dict(name='Common start',path=results/'baseline/common',score=1.,identity='high-frequency-common')]
    for flow in ('F0','F1','F2'):
        candidates=[(c,r['job']['id']) for r in data['rows'] if r['terminal'] and r['job']['workflow']==flow
                    for c in r['candidates'] if c['rank_eligible']]
        if candidates:
            candidate,session=min(candidates,key=lambda item:(*ranking(item[0]),item[1]))
            cases.append(dict(name=flow+' representative: '+session+' / '+str(candidate['candidate_index']),
                path=results/'ppa'/session/'candidates'/f'{candidate["candidate_index"]:02d}'/'physical',
                score=candidate['score'],identity='high-frequency-'+flow))
    boxes=[]
    for case in cases:
        summary=json.loads((case['path']/'evidence/summary.json').read_text())
        paths=list((case['path']/'evidence/orfs-work/results').glob('**/6_final.gds'))
        if len(paths)!=1 or digest(paths[0])!=summary['gds']['sha256']:raise ValueError('Wrong delivered GDS')
        case.update(gds=paths[0],summary=summary);boxes.append(summary['gds']['bbox_microns'])
    left=min(b['left'] for b in boxes);bottom=min(b['bottom'] for b in boxes)
    size=max(max(b['right'] for b in boxes)-left,max(b['top'] for b in boxes)-bottom)
    margin=.04*size;viewport=[left-margin,bottom-margin,left+size+margin,bottom+size+margin]
    columns=2 if len(cases)>1 else 1;rows=(len(cases)+columns-1)//columns
    fig,axes=plt.subplots(rows,columns,figsize=(5.3*columns,5.4*rows),squeeze=False)
    for i,(case,axis) in enumerate(zip(cases,axes.flat)):
        image=output/f'benchmark_layout_{i}.png'
        env=dict(os.environ,QT_QPA_PLATFORM='offscreen',CHIP_CASE_GDS=str(case['gds']),
            CHIP_CASE_LAYOUT_IMAGE=str(image),CHIP_CASE_LAYER_PROPERTIES=str(CASE/'toolchain/orfs/flow/platforms/sky130hd/sky130hd.lyp'),
            CHIP_CASE_VIEWPORT_MICRONS=json.dumps(viewport))
        subprocess.run([os.environ.get('KLAYOUT_CMD','klayout'),'-b','-r',str(CASE/'scripts/render_gds_macro.py')],
                       env=env,check=True,timeout=180)
        axis.imshow(plt.imread(image));axis.axis('off')
        hf=next((r for r in data.get('high_frequency',{}).get('rows',[]) if r['selection']['identity']==case['identity']),None)
        if hf and hf['terminal']:
            reasons=', '.join(reason.replace('_',' ') for reason in hf.get('failure_classes',[]))
            status='qualified' if hf['evaluation']['rank_eligible'] else 'not qualified'+(' ('+reasons+')' if reasons else '')
        elif hf:
            status='pending'
        else:
            status='selection pending' if data.get('high_frequency',{}).get('selection_pending',True) else 'not selected'
        axis.set_title(case['name']+f'\n95 MHz Q={case["score"]:.4f}; footprint {case["summary"]["metrics"]["die_area_um2"]/1e6:.4f} mm²'
                       +'\n100 MHz challenge: '+status,fontsize=10)
    for axis in list(axes.flat)[len(cases):]:axis.axis('off')
    fig.suptitle('Delivered 95 MHz routed cores; identical layers and physical scale',fontsize=12)
    fig.tight_layout()
    for extension in ('svg','png'):fig.savefig(output/('benchmark_layouts.'+extension),bbox_inches='tight',dpi=180)
    plt.close(fig)
    write_json(output/'benchmark_layouts.source.json',dict(analysis_sha256=digest(results/'analysis.json'),same_physical_scale=True,
        viewport_microns=viewport,cases=[dict(name=c['name'],gds_sha256=digest(c['gds']),score=c['score']) for c in cases],
        selection='Common start and lowest unrounded Q new qualified representative per workflow; 100 MHz qualification is a separate one-attempt challenge.'))
    print('BENCHMARK_ACTUAL_GDS_RENDERED',len(cases))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();render(args.results,args.output)
