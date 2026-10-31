#!/usr/bin/env python3
"""Render actual baseline/selected GDS with an identical physical viewport."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def render():
    data=json.loads((ROOT/'results/ppa/summary.json').read_text())
    assert data['passed'] and data['complete']
    names=['baseline10',data['selected']]
    gds=[];summaries=[]
    for name in names:
        paths=list((ROOT/'results/ppa'/name).glob('orfs-work/results/**/6_final.gds'))
        assert len(paths)==1
        gds.append(paths[0])
        summary=json.loads((ROOT/'results/ppa'/name/'summary.json').read_text())
        assert hashlib.sha256(paths[0].read_bytes()).hexdigest()==summary['gds']['sha256']
        summaries.append(summary)
    boxes=[s['gds']['bbox_microns'] for s in summaries]
    left=min(b['left'] for b in boxes);bottom=min(b['bottom'] for b in boxes)
    size=max(max(b['right'] for b in boxes)-left,max(b['top'] for b in boxes)-bottom)
    margin=.05*size
    viewport=[left-margin,bottom-margin,left+size+margin,bottom+size+margin]
    layers=ROOT/'toolchain/orfs/flow/platforms/sky130hd/sky130hd.lyp'
    images=[]
    for name,path in zip(names,gds):
        image=ROOT/'figures'/('ppa_'+name+'_layout.png');images.append(image)
        env=dict(os.environ,QT_QPA_PLATFORM='offscreen',CHIP_CASE_GDS=str(path),
                 CHIP_CASE_LAYOUT_IMAGE=str(image),CHIP_CASE_LAYER_PROPERTIES=str(layers),
                 CHIP_CASE_VIEWPORT_MICRONS=json.dumps(viewport))
        subprocess.run([os.environ.get('KLAYOUT_CMD','klayout'),'-b','-r',str(ROOT/'scripts/render_gds_macro.py')],env=env,check=True,timeout=180)
    fig,axes=plt.subplots(1,2,figsize=(10,5))
    for ax,image,name,summary in zip(axes,images,names,summaries):
        ax.imshow(plt.imread(image));ax.axis('off')
        area=summary['metrics']['die_area_um2']/1e6
        target=next(r['initial_core_utilization_percent'] for r in data['rows'] if r['name']==name)
        row=next(r for r in data['rows'] if r['name']==name)
        margin_note='; 10% repair margins' if row.get('repair_margins_percent') else ''
        ax.set_title(f'{target}% initial utilization{margin_note}\nCore footprint {area:.4f} mm²',fontsize=10)
    fig.suptitle('Actual GDS, identical layers and physical viewport; unchanged RTL')
    fig.tight_layout()
    for suffix in ('png','svg'):fig.savefig(ROOT/'figures'/('ppa_layout_comparison.'+suffix),dpi=160,bbox_inches='tight')
    plt.close(fig)
    record={'source_summary':'results/ppa/summary.json','cases':names,'physical_viewport_microns':viewport,
            'identical_physical_scale':True,'renderer':'KLayout actual GDS; routing layers only',
            'gds_sha256':[s['gds']['sha256'] for s in summaries]}
    (ROOT/'figures/ppa_layout_comparison.source.json').write_text(json.dumps(record,indent=2)+'\n')
    print('ACTUAL_PPA_LAYOUT_COMPARISON_RENDERED')


if __name__=='__main__':render()
