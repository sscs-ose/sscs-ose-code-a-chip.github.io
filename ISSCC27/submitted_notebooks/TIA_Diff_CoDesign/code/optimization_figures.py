"""Plot constraint reduction and the feasible TPE objective against proposal number."""
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
import figure_style as STYLE

SCHEMA='tia-constrained-objective-history-v1'


def from_report(report,source_sha256,selected_trial=None):
    """Keep every trial and its largest signed constraint; omit paths and device data."""
    def compact(row):
        constraints=np.asarray(row['constraints'],dtype=float)
        if constraints.shape!=(16,) or not np.isfinite(constraints).all():
            raise ValueError('Expected sixteen finite constraints per trial')
        metrics=row.get('metrics_surrogate')
        bandwidth=float(metrics['bw_ghz']) if metrics is not None else None
        return dict(trial=int(row['trial']),objective=float(row['objective']),bandwidth_ghz=bandwidth,
                    max_constraint=float(constraints.max()),
                    nonbandwidth_max_constraint=float(np.delete(constraints,1).max()),
                    feasible=bool(row['feasible']),status=row['status'])
    config=report['config'];selected=report.get('fine_grid_replay')
    if selected_trial is not None:
        matches=[r for r in report.get('fine_grid_replays',[]) if r['trial']==selected_trial and r['feasible']]
        if len(matches)!=1:raise ValueError('Qualified proposal is not an exact feasible candidate replay')
        selected=matches[0]
    return dict(schema=SCHEMA,objective='negative bandwidth in GHz',constraint_count=16,
        source_report_sha256=source_sha256,source_checkpoint_sha256=report['xmodel_sha256'],
        initialization=report['initialization'],
        batch_size=int(config['jobs']),seed=int(config['seed']),search_step_ghz=float(config['optimization_step_ghz']),
        replay_step_ghz=float(report['final_grid_ghz']),records=[compact(row) for row in report['rows']],
        fine_grid_replays=[compact(row) for row in report.get('fine_grid_replays',[])],
        optimizer_selected_replay=compact(report['fine_grid_replay']) if report.get('fine_grid_replay') is not None else None,
        selected_replay=compact(selected) if selected is not None else None)


def curves(history):
    if history.get('schema')=='tia-two-phase-objective-history-v1':
        return [curves(phase) for phase in history['random_searches']]
    if history.get('schema')!=SCHEMA:raise ValueError('Unsupported objective-history schema')
    rows=history['records'];trial=np.asarray([row['trial'] for row in rows],dtype=int)
    if not len(rows) or not np.array_equal(trial,np.arange(len(rows))):
        raise ValueError('Trial records must be unique, ordered and contiguous from zero')
    objective=np.asarray([row['objective'] for row in rows],dtype=float)
    complete=np.asarray([row['status']=='complete' for row in rows])
    feasible=np.asarray([row['feasible'] for row in rows],dtype=bool)
    maximum=np.asarray([row['max_constraint'] for row in rows],dtype=float)
    bandwidth=np.asarray([np.nan if row['bandwidth_ghz'] is None else row['bandwidth_ghz'] for row in rows])
    if (not np.isfinite(objective).all() or not np.isfinite(maximum).all()
            or not np.isfinite(bandwidth[complete]).all()):
        raise ValueError('Completed trials require finite objectives, constraints and bandwidths')
    if not np.array_equal(feasible,complete & (maximum<=0)):
        raise ValueError('Feasibility flags disagree with trial status or signed constraints')
    if not np.allclose(objective[complete],-bandwidth[complete],rtol=0,atol=1e-10):
        raise ValueError('Completed trial objectives must equal negative bandwidth')
    best=np.minimum.accumulate(np.where(feasible,objective,np.inf))
    best[~np.isfinite(best)]=np.nan
    violation=np.minimum.accumulate(np.where(complete,np.maximum(maximum,0),np.inf))
    violation[~np.isfinite(violation)]=np.nan
    return dict(trial=trial+1,objective=objective,complete=complete,feasible=feasible,
                best=best,best_violation=violation)


def build(output,history=None,report=None):
    STYLE.configure()
    if (history is None)==(report is None):raise ValueError('Provide one history or raw optimizer report')
    if report is not None:
        path=Path(report);raw=path.read_bytes()
        data=from_report(json.loads(raw),hashlib.sha256(raw).hexdigest())
    else:
        data=json.loads(Path(history).read_text())
    if data.get('schema')=='tia-two-phase-objective-history-v1':
        return two_phase(output,data)
    values=curves(data);x=values['trial'];valid=values['complete'];feasible=values['feasible']
    fig,axes=plt.subplots(1,2,figsize=(23,9.5))
    constraint_color,objective_color,selection_color='#4c6878','#1d6480','#b45f35'
    axes[0].step(x,values['best_violation'],where='post',color=constraint_color,linewidth=2.,label='Best constraint violation')
    axes[0].axhline(0,color='#87939b',linewidth=.9,linestyle='--')
    axes[0].set_yscale('symlog',linthresh=.01,linscale=.65)
    finite_violation=values['best_violation'][np.isfinite(values['best_violation'])]
    axes[0].set_ylim(-.003,max(.03,1.6*float(finite_violation.max())) if len(finite_violation) else 1.)
    STYLE.panel(axes[0],'(a) Feasibility search',y=-.27)
    axes[0].set(xlabel='Proposal number',ylabel='Best constraint violation',xlim=(1,max(2,len(x))))
    axes[0].text(.03,.30,r'$V=\max(0,\max_k g_k)$; best so far',
                 transform=axes[0].transAxes,color=constraint_color)
    axes[1].step(x,values['best'],where='post',color=objective_color,linewidth=2.2,label='Best feasible objective')
    previous=np.r_[np.nan,values['best'][:-1]]
    changes=np.isfinite(values['best']) & (~np.isfinite(previous) | (values['best']<previous))
    axes[1].scatter(x[changes],values['best'][changes],s=37,color=objective_color,edgecolors='white',linewidths=.7,zorder=3)
    selected=data['selected_replay']
    if selected is not None:
        if not selected['feasible'] or selected['max_constraint']>0:
            raise ValueError('The selected candidate replay must be feasible')
        label='Selected design (surrogate score)'
        axes[1].scatter(selected['trial']+1,selected['objective'],marker='*',s=155,color=selection_color,
                        edgecolors='white',linewidths=.7,zorder=4,label=label)
        axes[1].annotate(f"{selected['objective']:.2f}",(selected['trial']+1,selected['objective']),
                         xytext=(-12,32),textcoords='offset points',ha='right',color=selection_color)
    if feasible.any():
        first=np.flatnonzero(feasible)[0]
        axes[0].axvline(x[first],color='#87939b',linewidth=.9,linestyle=':')
        axes[0].annotate(f'First feasible: {x[first]:,}',(x[first],0),xytext=(-16,48),
                         textcoords='offset points',ha='right',color='#36434c',
                         arrowprops=dict(arrowstyle='-',color='#87939b',linewidth=.8))
        padding=max(40.,.06*(len(x)-x[first]))
        axes[1].set_xlim(max(.5,x[first]-padding),len(x)+padding)
        points=values['best'][np.isfinite(values['best'])]
        bounds=list(points)
        if selected is not None:bounds.append(selected['objective'])
        low,high=min(bounds),max(bounds);margin=max(.08,.18*(high-low))
        axes[1].set_ylim(low-margin,high+margin)
        indices=np.flatnonzero(changes)
        for index in sorted({int(indices[0]),int(indices[-1])}):
            if selected is not None and x[index]==selected['trial']+1:continue
            offset=(14,18) if index==indices[0] else (-14,-33)
            axes[1].annotate(f"{values['best'][index]:.2f}",(x[index],values['best'][index]),
                             xytext=offset,textcoords='offset points',
                             ha='left' if index==indices[0] else 'right',color=objective_color)
    if not feasible.any():
        axes[1].text(.5,.5,'No feasible search trial',transform=axes[1].transAxes,ha='center',va='center')
        axes[1].set_xlim(1,max(2,len(x)))
    STYLE.panel(axes[1],'(b) Feasible objective (detail)',y=-.27)
    axes[1].set(xlabel='Proposal number',ylabel='Objective −BW (GHz)')
    axes[1].ticklabel_format(axis='y',style='plain',useOffset=False)
    for ax in axes:
        ax.grid(axis='y',alpha=.18,linewidth=.7);ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5,integer=True))
    handles,labels=[],[]
    for ax in axes:
        h,l=ax.get_legend_handles_labels();handles.extend(h);labels.extend(l)
    fig.legend(handles,labels,loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,.01))
    fig.subplots_adjust(left=.08,right=.98,top=.98,bottom=.32,wspace=.30)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    STYLE.save(fig,output,'figure-09b')
    plt.close(fig)
    return dict(trials=len(x),complete=int(valid.sum()),feasible=int(feasible.sum()),invalid_or_failed=int((~valid).sum()),
                first_feasible_objective=float(values['best'][np.isfinite(values['best'])][0]) if feasible.any() else None,
                best_search_objective=float(np.nanmin(values['best'])) if feasible.any() else None,
                selected_replay_objective=selected['objective'] if selected is not None else None)


def two_phase(output,data):
    """Keep TPE proposal progress separate from paired EM/ANN refinement."""
    curves(data)
    records=[row for phase in data['random_searches'] for row in phase['records']]
    valid=np.array([row['status']=='complete' and row['nonbandwidth_max_constraint']<=0 for row in records])
    bandwidth=np.array([row['bandwidth_ghz'] if row['bandwidth_ghz'] is not None else -np.inf for row in records])
    best=np.maximum.accumulate(np.where(valid,bandwidth,-np.inf))
    best[~np.isfinite(best)]=np.nan
    refinement=data['refinement']['records']
    violation=np.minimum.accumulate([max(0.,max(row['joint_constraints'])) for row in refinement])
    fig,axes=plt.subplots(1,2,figsize=(23,9.5))
    axes[0].step(np.arange(1,len(records)+1),best,where='post',color='#24689b',linewidth=2.)
    axes[0].axhline(34.,color='gray',linestyle='--',linewidth=1.,label='34 GHz proposal requirement')
    axes[0].set(xlabel='TPE proposal number',ylabel='Best BW meeting non-bandwidth constraints (GHz)')
    axes[1].step(np.arange(1,len(refinement)+1),violation,where='post',color='#b45f35',linewidth=2.)
    axes[1].axhline(0,color='gray',linestyle='--',linewidth=1.)
    axes[1].set_yscale('symlog',linthresh=.001)
    axes[1].set(xlabel='Paired ANN/EM evaluation',ylabel='Best joint constraint violation')
    axes[0].legend(frameon=False)
    for ax,label in zip(axes,('(a) Random joint search','(b) EM-guided active refinement')):
        STYLE.panel(ax,label,y=-.27)
        ax.grid(axis='y',alpha=.2)
        ax.spines[['top','right']].set_visible(False)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5,integer=True))
    fig.subplots_adjust(left=.08,right=.99,top=.98,bottom=.28,wspace=.32)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    STYLE.save(fig,output,'figure-09b');plt.close(fig)
    return dict(random_proposals=len(records),paired_refinement_evaluations=len(refinement))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--history',type=Path,help='Compact recorded history; defaults to the submission data')
    inputs.add_argument('--report',type=Path,help='Full result.json from a new optimizer run')
    parser.add_argument('--output',type=Path,default=ROOT/'runs/optimization_figures')
    args=parser.parse_args();print(json.dumps(build(args.output,args.history,args.report),indent=2))
