"""Reconstruct the published response, NRZ/PAM4 eyes and final GDS figures."""
from environment import ROOT, configure
configure()
import hashlib
import json
from pathlib import Path

import gdstk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon
import numpy as np
from wireline_eyes import build as build_eyes
from flow_figure import build as build_flow_figure
import figure_style as STYLE

COLORS = {50:'#aeb4bc',67:'#30935b',125:'#222222',126:'#287bc1',133:'#222222',134:'#ed6a72'}


def save(fig, output, stem):
    STYLE.save(fig,output,stem)
    plt.close(fig)


def response_figure(output,root=ROOT):
    STYLE.configure()
    root=Path(root)
    comparison = json.loads((root/'results/comparison.json').read_text())
    reflection_path = root/'results/output_reflection.npz'
    reflection_meta = json.loads((root/'results/output_reflection.json').read_text())
    if hashlib.sha256(reflection_path.read_bytes()).hexdigest() != reflection_meta['data_sha256']:
        raise ValueError('Output-reflection data differ from their recorded hash')
    for relative, expected in reflection_meta['source_sha256'].items():
        if hashlib.sha256((root/relative).read_bytes()).hexdigest() != expected:
            raise ValueError('Regenerate output-reflection data for the current circuit: '+relative)
    with np.load(reflection_path,allow_pickle=False) as data:
        reflection = {key:data[key].copy() for key in data.files}
    fig, axes = plt.subplots(2,2,figsize=(23,17),constrained_layout=True)
    axes = axes.ravel()
    for name,label,color,style in (('with_transformer','With transformer','#24689b','-'),
                                    ('without_transformer','Without transformer','#bd6133','--')):
        record = comparison['runs'][name]
        with np.load(root/record['curve_file'],allow_pickle=False) as data:
            f,z,fn,noise = (data[k] for k in ('f','zt','fn','inoise'))
        band=(f>=1e9)&(f<=60e9)
        axes[0].plot(f[band]/1e9,20*np.log10(abs(z[band])),style,color=color,label=label,linewidth=1.8)
        bw=record['metrics']['bw_ghz'];level=record['metrics']['zt_dbohm']-10*np.log10(2)
        axes[0].plot(bw,level,'o',color=color,markersize=4)
        axes[0].annotate(f'{bw:.2f} GHz',(bw,level),xytext=(bw+1,level+1.5),color=color,
                         arrowprops=dict(arrowstyle='-',color=color,linewidth=.7))
        gd=-np.gradient(np.unwrap(np.angle(z)),2*np.pi*f)*1e12
        band=(f>=1e9)&(f<=26e9)
        axes[1].plot(f[band]/1e9,gd[band],style,color=color,label=label,linewidth=1.8)
        band=(fn>=1e9)&(fn<=40e9)
        axes[2].plot(fn[band]/1e9,noise[band]*1e12,style,color=color,label=label,linewidth=1.8)
        np.testing.assert_array_equal(reflection['f'],f)
        band=(f>=1e9)&(f<=60e9)
        axes[3].plot(f[band]/1e9,20*np.log10(np.maximum(abs(reflection[name][band]),1e-15)),
                     style,color=color,label=label,linewidth=1.8)
    axes[0].set(xlim=(1,60),xlabel='Frequency (GHz)',ylabel='Differential transimpedance (dBΩ)')
    axes[1].set(xlim=(1,26),xlabel='Frequency (GHz)',ylabel='Group delay (ps)')
    axes[2].set(xlim=(1,40),xlabel='Frequency (GHz)',ylabel='Input-noise density (pA/√Hz)')
    axes[3].set(xlim=(1,60),xlabel='Frequency (GHz)',ylabel='S22 (dB)')
    axes[3].axhline(-10,color='gray',linestyle=':',linewidth=.8)
    for ax,title in zip(axes,('(a) Transimpedance','(b) Group delay','(c) Input-noise density',
                              '(d) Differential output reflection')):
        STYLE.panel(ax,title,y=-.25)
    for ax in axes:ax.grid(alpha=.2);ax.legend(frameon=False)
    save(fig,output,'figure-10')



def eye_figure(output,root=ROOT):
    root=Path(root)
    study=build_eyes(output,root=root)
    return next(row['metrics'] for row in study['figure_cases']
                if row['modulation']=='PAM4' and row['bit_rate_gbps']==106.25)



def layout_figure(output,root=ROOT):
    STYLE.configure()
    root=Path(root)
    fig,axes=plt.subplots(1,3,figsize=(25,9))
    for ax,name,title in zip(axes,('transformer','L1','LB'),('(a) Transformer','(b) L1','(c) Lb')):
        cells=gdstk.read_gds(str(root/'data/passives'/(name+'.gds'))).top_level()
        if len(cells)!=1:raise ValueError('Expected one top-level layout cell')
        for polygon in cells[0].get_polygons():
            if polygon.datatype==0:
                ax.add_patch(Polygon(polygon.points,facecolor=COLORS.get(polygon.layer,'#d8d8d8'),edgecolor='none',
                                     alpha=.55 if polygon.layer in (126,134) else .8))
        ax.autoscale_view();ax.set_aspect('equal');ax.set(xlabel='x (µm)',ylabel='y (µm)')
    fig.legend(handles=[Patch(color=COLORS[k],label=label) for k,label in ((50,'Metal4 ground'),(67,'Metal5'),(126,'TopMetal1'),(134,'TopMetal2'))],
               loc='lower center',ncol=4,frameon=False,bbox_to_anchor=(.5,.005))
    fig.subplots_adjust(left=.055,right=.99,top=.98,bottom=.28,wspace=.30)
    for ax,label in zip(axes,('(a) Transformer','(b) L1','(c) Lb')):
        box=ax.get_position()
        fig.text((box.x0+box.x1)/2,.14,label,ha='center',va='top')
    save(fig,output,'figure-12')



def build(output,root=ROOT):
    root=Path(root)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    build_flow_figure(output)
    response_figure(output,root=root)
    metrics=eye_figure(output,root=root)
    layout_figure(output,root=root)
    (output/'eye_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    return metrics



if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs/figures')
    parser.add_argument('--result-root',type=Path,required=True)
    args=parser.parse_args();metrics=build(args.output,root=args.result_root)
    print(f"PAM4 minimum eye height: {metrics['min_eye_mv']:.2f} mV")
