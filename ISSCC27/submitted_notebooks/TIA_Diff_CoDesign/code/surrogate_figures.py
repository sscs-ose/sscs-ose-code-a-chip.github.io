"""Recreate surrogate fidelity and the documented transformer/spiral test examples."""
from environment import ROOT, configure
configure()
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import gdstk
import numpy as np
import skrf as rf
import surrogate as S
from results_figures import COLORS
import figure_style as STYLE

OUTPUT=None

def value(v):return f'{float(v):.2f}'

def save(fig,name):
    path=STYLE.save(fig,OUTPUT,Path(name).stem);plt.close(fig);return path

def layout(ax,path):
    cells=gdstk.read_gds(str(path)).top_level()
    if len(cells)!=1:raise ValueError('Expected one layout cell')
    for polygon in cells[0].get_polygons():
        if polygon.datatype==0:ax.add_patch(Polygon(polygon.points,facecolor=COLORS.get(polygon.layer,'#d8d8d8'),edgecolor='none',alpha=.55 if polygon.layer in (126,134) else .8))
    ax.autoscale_view();ax.set_aspect('equal');ax.set(xlabel='x (µm)',ylabel='y (µm)')

def examples_figure(records,model,name,kind):
    prediction=model.predict(np.asarray([r['geo'] for r in records]))
    fig,axes=plt.subplots(2,4,figsize=(31,16),constrained_layout=True,gridspec_kw={'width_ratios':[1,1.15,1.15,1.15]})
    colors=('#24689b','#bd6133','#438151')
    for i,(record,predicted) in enumerate(zip(records,prediction)):
        actual=record['s'];record['complete_matrix_mae_s']=float(np.abs(predicted-actual).mean())
        layout(axes[i,0],record['gds'])
        srf=('≥ ' if record['srf_lower_bound'] else '')+value(record['srf_ghz'])
        description=('Edge-coupled' if record.get('coupling',0)==0 else 'Broadside-coupled') if kind=='xfmr' else 'n='+str(int(record['geo'][2]))
        STYLE.panel(axes[i,0],f"({chr(97+4*i)}) Example {i}: {description}\nSRF: {srf} GHz",y=-.23)
        shown=((0,0),(1,0),(2,0)) if kind=='xfmr' else ((0,0),(1,0))
        for color,(a,b) in zip(colors,shown):
            label='S'+str(a+1)+str(b+1);axes[i,1].plot(S.FREQ/1e9,np.abs(actual[:,a,b]),color=color,label=label+' EM');axes[i,1].plot(S.FREQ/1e9,np.abs(predicted[:,a,b]),'--',color=color,label=label+' ANN')
        axes[i,1].set(ylabel='|Sij|');axes[i,1].legend(frameon=False,ncol=2)
        errors=np.stack([np.abs(predicted[:,a,b]-actual[:,a,b]) for a,b in model.kind.sel])
        for curve in errors:axes[i,2].plot(S.FREQ/1e9,curve,color='#89959d',alpha=.4,linewidth=.7)
        axes[i,2].plot(S.FREQ/1e9,errors.mean(axis=0),color=colors[0],label='Mean');axes[i,2].set(ylabel='Complex |ΔSij|');axes[i,2].legend(frameon=False)
        if kind=='xfmr':
            measured=S.xfmr_curves(S.FREQ,actual);estimated=S.xfmr_curves(S.FREQ,predicted)
            for color,j,label in ((colors[0],0,'Lp'),(colors[1],1,'Ls')):
                axes[i,3].plot(S.FREQ/1e9,measured[j]*1e9,color=color,label=label+' EM');axes[i,3].plot(S.FREQ/1e9,estimated[j]*1e9,'--',color=color,label=label+' ANN')
        else:
            for response,style,label in ((actual,'-','EM'),(predicted,'--','ANN')):
                z=-1/rf.network.s2y(response,50)[:,1,0];inductance=z.imag/(2*np.pi*S.FREQ)*1e9
                axes[i,3].plot(S.FREQ/1e9,inductance,style,color=colors[0],label=label)
        axes[i,3].set(ylabel='Extracted inductance (nH)',xlim=(1,30));axes[i,3].legend(frameon=False)
        for ax in axes[i,1:]:ax.set_xlabel('Frequency (GHz)');ax.grid(alpha=.2)
        for j,label in enumerate(('S-parameters','Complex error','Inductance'),1):
            STYLE.panel(axes[i,j],f'({chr(97+4*i+j)}) {label}',y=-.24)
    return save(fig,name)


def build(output,data_dir=None,transformer_training=None,spiral_training=None):
    global OUTPUT
    STYLE.configure()
    OUTPUT=Path(output);OUTPUT.mkdir(parents=True,exist_ok=True)
    data_dir=Path(data_dir or ROOT/'runs')
    training={'transformer':transformer_training,'spiral':spiral_training}
    examples=json.loads((ROOT/'data/test_examples.json').read_text())
    fig,axes=plt.subplots(3,2,figsize=(22,23),constrained_layout=True)
    for col,name in enumerate(('transformer','spiral')):
        directory=Path(training[name]) if training[name] is not None else ROOT/'models'
        report_path=directory/'report.json' if training[name] is not None else directory/(name+'_report.json')
        report=json.loads(report_path.read_text())
        model=S.Surrogate(str(directory/(name+'.pt')))
        with np.load(data_dir/(name+'_data.npz'),allow_pickle=False) as arrays:
            data=dict(arrays)
            positions={int(v):i for i,v in enumerate(data['idx'])}
            records=[]
            for row in examples:
                if row['kind']!=name:continue
                index=row['source_index'];i=positions[index]
                gds=data_dir/(name+'_gds')/(str(index)+'.gds')
                if not gds.is_file():raise FileNotFoundError('Regenerate the test-example layout: '+str(gds))
                extension='.s4p' if name=='transformer' else '.s2p'
                network=rf.Network(str(data_dir/(name+'_labels')/(str(index)+extension)))
                frequency,response=network.f[1:],network.s[1:]
                extracted=(S.xfmr_figures if name=='transformer' else S.spiral_figures)(frequency,response)
                srf=extracted['SRF']
                records.append(dict(geo=data['geo'][i],s=data['s'][i],gds=gds,
                    srf_ghz=srf/1e9,srf_lower_bound=bool(srf==frequency[-1]),
                    coupling=row['parameters'].get('sb',0)))
        # Frequency errors belong to the regenerated EM labels and selected checkpoint.
        fresh=S.test_metrics(model,data['geo'][data['te']],data['s'][data['te']])
        report.update({key:fresh[key] for key in ('freq_ghz','dS_f_median','dS_f_p90')})
        examples_figure(records,model,'figure-07.png' if name=='transformer' else 'figure-08.png',
                        'xfmr' if name=='transformer' else 'spiral')
        for member,history in enumerate(report['history_all']):
            h=np.asarray(history)
            axes[0,col].semilogy(h[:,0],h[:,3],color='#24689b',alpha=.4,label='Training' if member==0 else None)
            axes[0,col].semilogy(h[:,0],h[:,4],color='#bd6133',alpha=.4,label='Validation' if member==0 else None)
        axes[0,col].set(xlabel='Epoch',ylabel='Complex-S MAE')
        for member,history in enumerate(report['r2_history_all']):
            h=np.asarray(history)
            axes[1,col].plot(h[:,0],h[:,1],color='#24689b',alpha=.4,label='Training' if member==0 else None)
            axes[1,col].plot(h[:,0],h[:,2],color='#bd6133',alpha=.4,label='Validation' if member==0 else None)
        axes[1,col].set(xlabel='Epoch',ylabel='Full-matrix R²')
        axes[2,col].plot(report['freq_ghz'],report['dS_f_median'],color='#24689b',label='Median')
        axes[2,col].plot(report['freq_ghz'],report['dS_f_p90'],color='#bd6133',label='90th percentile')
        axes[2,col].set(xlabel='Frequency (GHz)',ylabel='Per-layout mean |ΔS|')
        for row,quantity in enumerate(('MAE','R²','Test error')):
            STYLE.panel(axes[row,col],f'({chr(97+2*row+col)}) {name.capitalize()}: {quantity}',y=-.25)
    for ax in axes.flat:ax.grid(alpha=.2);ax.legend(frameon=False)
    save(fig,'figure-06.png')
    print('Reconstructed surrogate learning curves, test errors, R² and test examples')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs/surrogate_figures')
    parser.add_argument('--data-dir',type=Path,default=ROOT/'runs')
    parser.add_argument('--transformer-training',type=Path)
    parser.add_argument('--spiral-training',type=Path)
    args=parser.parse_args();build(args.output,args.data_dir,args.transformer_training,args.spiral_training)
