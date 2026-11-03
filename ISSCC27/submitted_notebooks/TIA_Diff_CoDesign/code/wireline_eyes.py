"""NRZ/PAM4 rate comparison from the recorded, EM-evaluated TIA response."""
from environment import ROOT, configure
configure()
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from eye import reconstruct_eye, _eye_density
import figure_style as STYLE

FIGURE_CASES=(('NRZ',50.0),('PAM4',50.0),('PAM4',106.25))
RATE_GRID_GBPS=(25.0,50.0,100.0,106.25)
SETTINGS=dict(nsym=2048,osr=32,input_pp=200e-6,seed=1)


def evaluate(response,modulation,bitrate_gbps):
    bits=2 if modulation=='PAM4' else 1
    eye=reconstruct_eye(response,baud=float(bitrate_gbps)*1e9/bits,modulation=modulation,**SETTINGS)
    record=dict(modulation=modulation,bit_rate_gbps=float(bitrate_gbps),
                baud_gbd=eye['settings']['baud']/1e9,settings=eye['settings'],metrics=eye['metrics'])
    return eye,record


def draw(eyes,records,output):
    STYLE.configure()
    fig,axes=plt.subplots(1,len(eyes),figsize=(26,8.5),constrained_layout=True)
    bound=np.ceil(max(np.max(abs(eye['waveform'])) for eye in eyes)*1.05e3/10)*10
    voltage_edges=np.linspace(-bound,bound,257)
    for panel,ax,eye,record in zip('abc',np.atleast_1d(axes),eyes,records):
        density=_eye_density(eye,voltage_edges,centered=True)
        expected=(len(eye['levels'])-2*eye['guard']-1)*512
        if density.sum()!=expected:raise ValueError('Eye display omitted waveform samples')
        ax.set_facecolor('black')
        ax.imshow(np.ma.masked_where(density==0,np.log1p(density)),origin='lower',aspect='auto',
                  extent=(0,2,-bound,bound),cmap='hot',vmin=0,vmax=np.log1p(density.max()),interpolation='bilinear')
        title=f"({panel}) {record['bit_rate_gbps']:.2f} Gb/s {record['modulation']}"
        STYLE.panel(ax,title,y=-.25)
        ax.set(xlabel='Time (UI)',xlim=(0,2),ylim=(-1.45*bound,1.04*bound),xticks=[0,.5,1,1.5,2])
        ui_ps=1e3/record['baud_gbd']
        scale_ps=min((1,2,5,10,20,50,100),key=lambda value:abs(value-ui_ps/2))
        x=.10;y=-bound*1.33
        ax.plot([x,x+scale_ps/ui_ps],[y,y],color='white',linewidth=2.2,solid_capstyle='butt')
        ax.text(x,y+bound*.08,f'{scale_ps:g} ps',color='white',va='bottom')
    axes[0].set_ylabel('Differential output voltage (mV)')
    STYLE.save(fig,output,'figure-11')
    plt.close(fig)


def build(output,root=ROOT):
    root=Path(root)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    response_path=root/'results/with_transformer.npz'
    response=dict(np.load(response_path,allow_pickle=False))
    eyes,records=zip(*(evaluate(response,*case) for case in FIGURE_CASES))
    draw(eyes,records,output)
    sweep=[evaluate(response,modulation,rate)[1]
           for modulation in ('NRZ','PAM4') for rate in RATE_GRID_GBPS]
    result=dict(response_file='results/with_transformer.npz',response_sha256=hashlib.sha256(response_path.read_bytes()).hexdigest(),
                reconstruction='finite_periodic_linear_noiseless_without_equalization',
                display='All retained traces; centered two-UI window; log(1 + count) scaled per panel; bilinear display interpolation.',
                figure_cases=list(records),rate_grid_gbps=list(RATE_GRID_GBPS),rate_sweep=sweep)
    (output/'wireline_eye_study.json').write_text(json.dumps(result,indent=2)+'\n')
    return result



if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs/wireline_eyes')
    parser.add_argument('--result-root',type=Path,required=True)
    args=parser.parse_args();result=build(args.output,root=args.result_root)
    for row in result['figure_cases']:
        print(f"{row['modulation']} {row['bit_rate_gbps']:.2f} Gb/s: {row['metrics']['min_eye_mv']:.2f} mV, "
              f"{row['metrics']['common_width_ui']:.2f} UI")
