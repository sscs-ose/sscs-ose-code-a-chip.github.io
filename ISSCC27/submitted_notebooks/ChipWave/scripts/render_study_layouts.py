"""Render the actual common GDS and a predeclared best new qualified search result."""
from pathlib import Path
import argparse
import json
import os
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from study_protocol import digest, ranking, write_json

CASE=Path(__file__).resolve().parents[1]


def render(results,output,baseline_only=False):
    cases=[{'name':'Common baseline','path':results/'baseline/mhz95-run03','score':1.}]
    if not baseline_only:
        plan=json.loads((results/'protocol.json').read_text());candidates=[]
        for job in plan['ppa']['sessions']:
            summary=json.loads((results/'ppa'/job['id']/'results/search-summary.json').read_text())
            candidates.extend(dict(row,session=job['id']) for row in summary['candidates'] if row['rank_eligible'])
        if candidates:
            best=min(candidates,key=ranking)
            cases.append({'name':best['session']+' · candidate '+str(best['candidate_index']),
                'path':results/'ppa'/best['session']/'candidates'/f"{best['candidate_index']:02d}"/'physical',
                'score':best['score']})
    output.mkdir(parents=True,exist_ok=True)
    boxes=[]
    for case in cases:
        case['summary']=json.loads((case['path']/'evidence/summary.json').read_text())
        paths=list((case['path']/'evidence/orfs-work/results').glob('**/6_final.gds'))
        if len(paths)!=1 or digest(paths[0])!=case['summary']['gds']['sha256']:
            raise ValueError('Selected GDS identity mismatch')
        case['gds']=paths[0];boxes.append(case['summary']['gds']['bbox_microns'])
    left=min(box['left'] for box in boxes);bottom=min(box['bottom'] for box in boxes)
    size=max(max(box['right'] for box in boxes)-left,max(box['top'] for box in boxes)-bottom)
    margin=.04*size;viewport=[left-margin,bottom-margin,left+size+margin,bottom+size+margin]
    fig,axes=plt.subplots(1,len(cases),figsize=(5.4*len(cases),5.2),squeeze=False)
    for i,(case,axis) in enumerate(zip(cases,axes[0])):
        image=output/f'study_layout_{i}.png'
        env=dict(os.environ,QT_QPA_PLATFORM='offscreen',CHIP_CASE_GDS=str(case['gds']),
            CHIP_CASE_LAYOUT_IMAGE=str(image),CHIP_CASE_LAYER_PROPERTIES=str(CASE/'toolchain/orfs/flow/platforms/sky130hd/sky130hd.lyp'),
            CHIP_CASE_VIEWPORT_MICRONS=json.dumps(viewport))
        subprocess.run([os.environ.get('KLAYOUT_CMD','klayout'),'-b','-r',str(CASE/'scripts/render_gds_macro.py')],
                       env=env,check=True,timeout=180)
        axis.imshow(plt.imread(image));axis.axis('off')
        axis.set_title(case['name']+f"\nQ = {case['score']:.3f}; footprint {case['summary']['metrics']['die_area_um2']/1e6:.4f} mm²",fontsize=11)
    fig.suptitle('Actual 95 MHz routed cores · identical layers and physical scale',fontsize=13)
    fig.tight_layout()
    for extension in ('png','svg'):fig.savefig(output/('study_layouts.'+extension),dpi=180,bbox_inches='tight')
    plt.close(fig)
    write_json(output/'study_layouts.source.json',{'cases':[{'name':case['name'],'gds_sha256':case['summary']['gds']['sha256'],
        'score':case['score']} for case in cases],'viewport_microns':viewport,'same_physical_scale':True,
        'selection':'Common baseline and lowest-Q new qualified search candidate; no geometry inferred from area numbers'})
    print('STUDY_ACTUAL_GDS_RENDERED')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--baseline-only',action='store_true')
    args=parser.parse_args();render(args.results.resolve(),args.output.resolve(),args.baseline_only)
