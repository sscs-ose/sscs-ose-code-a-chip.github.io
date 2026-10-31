"""Plot measured F0/F1/F2 outcomes without moving coincident data or hiding failures."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from study_protocol import digest,write_json

COLORS={'F0':'#087f8c','F1':'#a855f7','F2':'#d97706'}
MARKERS={'F0':'o','F1':'s','F2':'^'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none',
    'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})


def save(fig,output,name):
    fig.savefig(output/(name+'.svg'),bbox_inches='tight')
    fig.savefig(output/(name+'.png'),bbox_inches='tight',dpi=180)
    plt.close(fig)


def plot(results,output):
    results,output=Path(results).resolve(),Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    analysis=json.loads((results/'analysis.json').read_text())
    terminal=[r for r in analysis['rows'] if r['terminal']]
    fig,axes=plt.subplots(1,2,figsize=(12,4.6))
    identical=defaultdict(list);points=[];failed=0
    for trial in terminal:
        flow=trial['job']['workflow'];name=trial['job']['id']
        best=1.;slots=[0];scores=[1.];seconds=[0.]
        by_index={c['candidate_index']:c for c in trial['candidates']}
        for index in range(1,trial['accepted_candidates']+1):
            candidate=by_index.get(index)
            if candidate and candidate['rank_eligible']:
                best=min(best,candidate['score'])
                points.append(dict(candidate,session=name,workflow=flow))
            else:
                failed+=1
                axes[0].scatter(index,best,color=COLORS[flow],marker='x',s=48,zorder=5)
                if candidate and candidate.get('elapsed_search_seconds') is not None:
                    axes[1].scatter(candidate['elapsed_search_seconds']/60,best,
                                    color=COLORS[flow],marker='x',s=48,zorder=5)
            slots.append(index);scores.append(best)
            seconds.append(candidate['elapsed_search_seconds']/60 if candidate else trial['total_seconds']/60)
        # Retained best is drawn through the actual session endpoint, including unused slots.
        wall=[*seconds,trial['total_seconds']/60];wall_y=[*scores,scores[-1]]
        style={1:'-',2:'--',3:':'}[trial['job']['repetition']]
        for ax,x,y in ((axes[0],slots,scores),(axes[1],wall,wall_y)):
            ax.step(x,y,where='post',color=COLORS[flow],linestyle=style,alpha=.85,label=name)
        identical[(tuple(slots),tuple(scores))].append(name)
    for ax in axes:
        ax.axhline(1,color='#94a3b8',linestyle=':',linewidth=1)
        ax.set_ylabel('Best qualified incumbent Q (lower is better)')
        ax.grid(alpha=.2)
    axes[0].set(xlabel='Accepted candidate slots (failures included)',xticks=[0,1,2,3],title='Search efficiency per tool attempt')
    axes[1].set(xlabel='Elapsed session time (min; EDA wait included)',title='Search efficiency per elapsed time')
    if terminal:axes[1].legend(fontsize=8,ncol=3)
    else:
        for ax in axes:ax.text(.5,.5,'New sessions pending',transform=ax.transAxes,ha='center',va='center')
    overlap=[' = '.join(names) for names in identical.values() if len(names)>1]
    note=(f'{len(terminal)}/9 completed sessions; {failed} accepted candidate'+('' if failed==1 else 's')+
          ' without a qualified result. Common-start and preparation costs reported separately.')
    if overlap:note+=' Coincident slot curves: '+'; '.join(overlap)+'.'
    fig.suptitle('Same CPU + NPU, shared actions and budget; only role organization changes')
    fig.text(.02,.01,textwrap.fill(note,150),fontsize=8,va='bottom')
    fig.tight_layout(rect=(0,.09,1,.94));save(fig,output,'benchmark_search_efficiency')

    fig,ax=plt.subplots(figsize=(8,5.6))
    coincident=defaultdict(list)
    for point in points:
        ax.scatter(point['area_ratio'],point['energy_ratio'],s=60,marker=MARKERS[point['workflow']],
            color=COLORS[point['workflow']],alpha=.8)
        coincident[(point['area_ratio'],point['energy_ratio'])].append(point['session']+'/'+str(point['candidate_index']))
    ax.scatter(1,1,marker='*',s=180,color='#111827',zorder=10,label='Common start')
    for flow,color in COLORS.items():
        ax.scatter([],[],color=color,marker=MARKERS[flow],label=flow)
    xs=[1,*[p['area_ratio'] for p in points]];ys=[1,*[p['energy_ratio'] for p in points]]
    xpad=max((max(xs)-min(xs))*.3,.025);ypad=max((max(ys)-min(ys))*.3,.025)
    lo=max(.01,min(xs)-xpad);hi=max(xs)+xpad
    curve=[lo+(hi-lo)*i/199 for i in range(200)]
    for q,style in ((1,'--'),(.98,':')):
        ax.plot(curve,[q/x for x in curve],color='#94a3b8',linestyle=style,linewidth=1,label=f'Q={q:g}')
    for i,((x,y),names) in enumerate(sorted(coincident.items())):
        label='\n'.join(textwrap.wrap(' = '.join(names),32))
        offset=(8,10 if i%2==0 else -18)
        if len(names)==1:
            offset=(-65,15) if math.hypot(x-1,y-1)<.005 else (8,-18)
        ax.annotate(label,(x,y),xytext=offset,
                    textcoords='offset points',fontsize=8,arrowprops=dict(arrowstyle='-',color='#64748b'))
    ax.set(xlabel='Standard-cell area / common-start area',ylabel='Geometric mean workload energy / common start',
        xlim=(lo,hi),ylim=(max(.01,min(ys)-ypad),max(ys)+ypad),title='Qualified candidates: area and energy are distinct outcomes')
    ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2)
    fig.text(.02,.015,f'{len(points)} qualified candidate'+('' if len(points)==1 else 's')+
        f'; {failed} accepted candidate'+('' if failed==1 else 's')+' without a qualified result.\n'
        'Coincident points retain their measured coordinates. Values use unrounded data; energy is model-estimated.',fontsize=8)
    fig.tight_layout(rect=(0,.07,1,1));save(fig,output,'benchmark_area_energy')

    fig,axes=plt.subplots(1,3,figsize=(12.5,4.6))
    positions=list(range(len(terminal)));labels=[r['job']['id'] for r in terminal]
    for i,row in enumerate(terminal):
        color=COLORS[row['job']['workflow']]
        axes[0].bar(i,row['agent_seconds'] if row['agent_seconds'] is not None else 0,color=color)
        axes[1].bar(i,row['reviews'],color=color)
        tokens=row.get('reported_tokens',row['tokens'])
        if tokens:
            # Input is total input (includes cached); reasoning is already part of output.
            uncached=(tokens['input_tokens']-tokens['cached_input_tokens'])/1000
            cached=tokens['cached_input_tokens']/1000;out=tokens['output_tokens']/1000
            partial=row['tokens'] is None
            hatch='//' if partial else None
            axes[2].bar(i,uncached,color=color,hatch=hatch)
            axes[2].bar(i,cached,bottom=uncached,color='#cbd5e1',hatch=hatch)
            axes[2].bar(i,out,bottom=uncached+cached,color='#334155',hatch=hatch)
            if partial:axes[2].text(i,uncached+cached+out,'≥',ha='center',va='bottom',fontsize=10)
        else:axes[2].text(i,0,'?',ha='center',va='bottom')
        if row['agent_seconds'] is None:axes[0].text(i,0,'?',ha='center',va='bottom')
    for ax in axes:
        ax.set_xticks(positions,labels,rotation=45,ha='right');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axes[0].set(title='Shared role budget consumed',ylabel='Aggregate role seconds')
    axes[0].axhline(1200,linestyle=':',color='#64748b',label='1200 s cap');axes[0].legend(fontsize=8)
    axes[1].set(title='Actual review participation',ylabel='Reviewer dispatches')
    axes[1].yaxis.set_major_locator(MaxNLocator(integer=True))
    axes[2].set(title='Recorded model usage',ylabel='Tokens (thousands)')
    axes[2].margins(y=.30)
    axes[2].text(.02,.98,'Color: uncached input\nLight: cached input; dark: output\n≥ / hatch: partial; ?: unavailable',
                 transform=axes[2].transAxes,va='top',fontsize=8)
    fig.suptitle('Coordination cost is counted, including review and failed attempts')
    fig.tight_layout();save(fig,output,'benchmark_coordination_cost')
    provenance=dict(analysis_sha256=digest(results/'analysis.json'),protocol_sha256=digest(results/'protocol.json'),
        terminal_sessions=len(terminal),qualified_points=len(points),unqualified_or_incomplete_slots=failed,
        coincident_points=[dict(area_ratio=k[0],energy_ratio=k[1],candidates=v) for k,v in coincident.items() if len(v)>1],
        scope='Measured data only. No jitter, interpolation of missing PPA, invented failure power or significance claims.')
    write_json(output/'benchmark_measured_sources.json',provenance)
    print('BENCHMARK_MEASURED_PLOTS_WRITTEN',len(terminal),'terminal sessions')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();plot(args.results,args.output)
