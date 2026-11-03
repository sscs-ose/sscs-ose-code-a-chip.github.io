"""Plot completed registered cohorts only; preserve zeros, overlaps and missing costs."""
import argparse
import json
import statistics
import sys
from pathlib import Path

from capacity_integration_physical import ROOT,CASE
from capacity_protocol import MODELS,WORKFLOWS,TASKS
from capacity_results import analyze,read_trials
from study_protocol import digest,write_json

sys.path.append(str(CASE/'scripts'))
from plot_study import plt,save

COLORS=dict(zip(WORKFLOWS,('#334155','#0891b2','#4f46e5','#059669','#d97706')))
MARKERS=dict(zip(WORKFLOWS,('o','s','^','D','x')))


def decoration(ax,title,ylabel):
    ax.set(title=title,ylabel=ylabel)
    ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)


def outcomes(data,output):
    fig,axes=plt.subplots(1,2,figsize=(13.4,4.5),squeeze=False)
    metrics=('functional_pass_rate','gds_pass_rate','joint_pass_rate','constraint_pass_rate')
    labels=('Function','GDS independently','Function + GDS','All constraints')
    palette=('#64748b','#0891b2','#6366f1','#059669')
    for ax,(name,model) in zip(axes[0],MODELS.items()):
        rows=[r for r in data['workflows'] if r['model']==model]
        for i,(key,label,color) in enumerate(zip(metrics,labels,palette)):
            ax.bar([x+(i-1.5)*.19 for x in range(len(rows))],
                [100*r['equal_task_means'][key] for r in rows],width=.18,label=label,color=color)
        ax.set_xticks(range(len(rows)),[r['workflow'] for r in rows]);ax.set_ylim(0,105)
        decoration(ax,name.title()+' · 12 sessions per workflow','Equal-task pass rate (%)')
    axes[0,0].legend(loc='upper center',bbox_to_anchor=(1.1,-.15),ncols=4,frameon=False)
    fig.suptitle('Delivery outcomes · all planned trials remain in the denominator')
    fig.tight_layout();save(fig,output,'capacity_outcomes')


def token_curves(data,output):
    fig,axes=plt.subplots(2,2,figsize=(12.8,8))
    coincident=[]
    for row,(name,model) in enumerate(MODELS.items()):
        flows=[r['workflow'] for r in data['workflows'] if r['model']==model]
        for column,metric in enumerate(('functional_pass_rate','average_score')):
            ax=axes[row,column];seen={}
            for flow in flows:
                points=sorted((r for r in data['checkpoints'] if r['model']==model and r['workflow']==flow),key=lambda r:r['budget'])
                values=tuple(r['equal_task_means'][metric]*(100 if column==0 else 1) for r in points)
                seen.setdefault(values,[]).append(flow)
                ax.plot([r['budget']/1e6 for r in points],values,marker=MARKERS[flow],
                    color=COLORS[flow],label=flow,linestyle='--' if flow in ('C1','C3') else '-',alpha=.85)
            same=[' = '.join(names) for names in seen.values() if len(names)>1]
            if same:
                note='Coincident: '+ '; '.join(same)
                ax.text(.02,.98,note,transform=ax.transAxes,va='top',fontsize=8)
                coincident.append(dict(model=model,metric=metric,groups=same))
            ax.set(ylim=(-3,108),xticks=(.25,.5,1),xlabel='Shared logical Token ceiling (millions)')
            decoration(ax,name.title(), 'Functional pass (%)' if column==0 else 'Mean complete-flow score')
            ax.legend(ncols=len(flows),loc='lower center',bbox_to_anchor=(.5,-.32),fontsize=8,frameon=False)
    fig.suptitle('Budget checkpoints use the latest eligible snapshot; declines are retained')
    fig.tight_layout(rect=(0,.04,1,.96));save(fig,output,'capacity_token_curves')
    return coincident


def cost_points(rows,output):
    fig,axes=plt.subplots(2,3,figsize=(14.5,8))
    measures=(('Logical Tokens','usage','actual_tokens',1e6,'Millions (including excess)'),
              ('Agent activity','', 'active_frontend_seconds',60,'Minutes'),
              ('Physical attempts','', 'physical_attempts',1,'Attempts, including failures'))
    for row,(name,model) in enumerate(MODELS.items()):
        flows=[f for f in WORKFLOWS if any(r['job']['model']==model and r['job']['workflow']==f for r in rows)]
        for ax,(title,parent,key,scale,unit) in zip(axes[row],measures):
            for x,flow in enumerate(flows):
                sample=[r for r in rows if r['job']['model']==model and r['job']['workflow']==flow]
                values=[]
                for r in sample:
                    value=(r.get(parent,{}) if parent else r).get(key)
                    if value is not None:values.append((len(value) if key=='physical_attempts' else value)/scale)
                if values:
                    ax.scatter([x]*len(values),values,color=COLORS[flow],s=27,alpha=.55)
                    ax.plot([x-.22,x+.22],[statistics.median(values)]*2,color='#111827',linewidth=2)
                ax.text(x,.99,f'{len(values)}/{len(sample)}',transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=8)
            ax.set_xticks(range(len(flows)),flows);ax.set_ylim(bottom=-.06,top=(2.35 if key=='physical_attempts' else None))
            decoration(ax,name.title()+' · '+title,unit)
    fig.suptitle('Actual per-session costs · points stay at their true values · black line = median\nCounts above each group show available / planned measurements')
    fig.tight_layout(rect=(0,0,1,.94));save(fig,output,'capacity_costs')


def physical_feedback(data,output):
    categories=('unqualified_to_qualified','qualified_to_unqualified','qualified_score_improved',
        'qualified_score_regressed','qualified_score_unchanged','both_unqualified','unresolved_measurement','fewer_than_two_attempts')
    labels=('Qualified after repair','Lost qualification','Qualified score improved','Qualified score regressed',
        'Qualified score unchanged','Both unqualified','Unresolved measurement','Fewer than two attempts')
    groups=data['workflows'];values=[]
    for group in groups:
        cells=[r for r in data['cells'] if r['model']==group['model'] and r['workflow']==group['workflow']]
        values.append([sum(c['physical_transitions'].get(key,0) for c in cells) for key in categories])
    fig,ax=plt.subplots(figsize=(13.2,5.5))
    ax.imshow(values,cmap='Blues',vmin=0,vmax=12,aspect='auto')
    for y,row in enumerate(values):
        for x,n in enumerate(row):ax.text(x,y,str(n),ha='center',va='center',color='white' if n>7 else '#111827')
    ax.set_xticks(range(len(labels)),labels,rotation=30,ha='right')
    ax.set_yticks(range(len(groups)),[('Luna' if r['model']==MODELS['luna'] else 'Sol')+' '+r['workflow'] for r in groups])
    ax.set_title('First → second physical attempt · each row accounts for 12 planned sessions')
    fig.tight_layout();save(fig,output,'capacity_physical_feedback')


def observed_costs(rows,output):
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    endpoints=('functional_pass','joint_pass','constraint_pass')
    for y,(name,model) in enumerate(MODELS.items()):
        flows=[f for f in WORKFLOWS if any(r['job']['model']==model and r['job']['workflow']==f for r in rows)]
        for ax,endpoint,label in zip(axes[y],endpoints,('Function','Function + GDS','All constraints')):
            for x,flow in enumerate(flows):
                group=[r for r in rows if r['job']['model']==model and r['job']['workflow']==flow]
                values=[r['first_observed_success_tokens'][endpoint]/1e6 for r in group
                    if r.get('measurement_valid') and r.get('first_observed_success_tokens',{}).get(endpoint) is not None]
                if values:
                    ax.scatter([x]*len(values),values,color=COLORS[flow],s=30,alpha=.55)
                    ax.plot([x-.2,x+.2],[statistics.median(values)]*2,color='#111827',linewidth=2)
                ax.text(x,1.04,f'{len(values)}/{len(group)}',ha='center',fontsize=8)
            ax.set(xticks=range(len(flows)),xticklabels=flows,ylim=(-.04,1.12))
            decoration(ax,name.title()+' · '+label,'First observed success (million Tokens)')
    fig.suptitle('Observed success costs · counts show observations / planned sessions\nUnreached or invalid costs have no point; checkpoints and physical submissions define observation granularity')
    fig.tight_layout(rect=(0,0,1,.94));save(fig,output,'capacity_first_success')


def coordination(rows,output):
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    for y,(name,model) in enumerate(MODELS.items()):
        flows=[f for f in WORKFLOWS if any(r['job']['model']==model and r['job']['workflow']==f for r in rows)]
        for ax,key,title in zip(axes[y],('call_count','role_switches','repeated_stage_calls'),
                               ('Role invocations','Role changes','Repeated stage calls')):
            for x,flow in enumerate(flows):
                group=[r for r in rows if r['job']['model']==model and r['job']['workflow']==flow]
                values=[r['coordination'][key] for r in group if r.get('coordination',{}).get(key) is not None]
                if values:
                    ax.scatter([x]*len(values),values,color=COLORS[flow],s=30,alpha=.55)
                    ax.plot([x-.2,x+.2],[statistics.median(values)]*2,color='#111827',linewidth=2)
                ax.text(x,.99,f'{len(values)}/{len(group)}',transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=8)
            ax.set(xticks=range(len(flows)),xticklabels=flows,ylim=(-.2,None))
            decoration(ax,name.title()+' · '+title,'Actual dispatch count')
    fig.suptitle('Coordination activity from executed calls · counts show available / planned measurements\nRole changes and repeated stages are activity proxies, not proof of useful handoffs or repairs')
    fig.tight_layout(rect=(0,0,1,.94));save(fig,output,'capacity_coordination')


def physical_tradeoffs(rows,output):
    fig,axes=plt.subplots(2,4,figsize=(14,7.5),squeeze=False)
    records=[];overlaps=[]
    for y,(name,model) in enumerate(MODELS.items()):
        for ax,task in zip(axes[y],TASKS):
            sample=[r for r in rows if r['job']['model']==model and r['job']['task']==task]
            positions={};qualified=0
            for row in sample:
                final=row['checkpoints'][-1];flow=row['job']['workflow']
                valid=row.get('measurement_valid') is True and final.get('constraint_pass') is True
                ratios=final.get('ratios')
                if valid and (not ratios or not final.get('measurements')):
                    raise ValueError('Qualified final delivery is missing its raw measurements or ratios')
                records.append(dict(job=row['job'],measurement_valid=row.get('measurement_valid'),
                    qualified=valid,final_score=row['final_score'],measurements=final.get('measurements'),
                    ratios=ratios,failure_reasons=final.get('failure_reasons',[])))
                if valid and ratios:
                    point=(ratios['cell_area'],ratios['energy']);qualified+=1
                    positions.setdefault(point,[]).append(flow+' r'+str(row['job']['repetition']))
                    ax.scatter(*point,color=COLORS[flow],marker=MARKERS[flow],s=42,alpha=.75)
            ax.scatter(1,1,marker='*',color='#111827',s=75,label='Reference')
            ax.axvline(1,color='#94a3b8',linewidth=.7);ax.axhline(1,color='#94a3b8',linewidth=.7)
            for point,names in positions.items():
                if len(names)>1:
                    overlaps.append(dict(model=model,task=task,area=point[0],energy=point[1],sessions=names))
                    ax.annotate('n='+str(len(names)),point,xytext=(5,5),textcoords='offset points',fontsize=8)
            ax.text(.03,.97,f'{qualified}/{len(sample)} qualified final deliveries',transform=ax.transAxes,
                va='top',fontsize=8)
            ax.set_xlabel('Standard-cell area / reference')
            decoration(ax,name.title()+' · '+task,'Geometric-mean unit energy / reference')
    for flow in WORKFLOWS:
        axes[0,0].scatter([],[],color=COLORS[flow],marker=MARKERS[flow],label=flow)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='lower center',ncols=6,frameon=False)
    fig.suptitle('Physical tradeoffs of final constraint-qualified deliveries\nFailed and invalid sessions remain in outcome rates and the complete measurement ledger; overlapping points are not shifted')
    fig.tight_layout(rect=(0,.04,1,.93));save(fig,output,'capacity_ppa_tradeoffs')
    write_json(output/'capacity_final_measurements.json',dict(rows=records,coincident_points=overlaps,
        scope='All planned final submissions. Null measurements remain unavailable; physical-attempt diagnostics never replace final submissions.'))


def plot(root,output,*,category='formal'):
    if category!='formal':raise ValueError('Formal comparison figures require the formal cohort')
    data=analyze(root,category)
    if not data['complete']:raise ValueError('Incomplete experiment: do not generate outcome charts')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    rows=read_trials(root,category)
    outcomes(data,output);overlaps=token_curves(data,output);cost_points(rows,output);physical_feedback(data,output)
    observed_costs(rows,output);coordination(rows,output);physical_tradeoffs(rows,output)
    write_json(output/'results.source.json',dict(
        source_sha256={'protocol.json':digest(root/'protocol.json'),**{
            str(p.relative_to(root)):digest(p) for p in sorted((root/'trials'/category).glob('*/result.json'))}},
        code_sha256=digest(Path(__file__)),coincident_curves=overlaps,
        scope='Full formal roster; real coordinates, no jitter; missing costs retained as unknown',
        figures=['capacity_outcomes','capacity_token_curves','capacity_costs','capacity_physical_feedback',
                 'capacity_first_success','capacity_coordination','capacity_ppa_tradeoffs']))
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'publication/figures')
    args=parser.parse_args();plot(ROOT,args.output)
    print(json.dumps(dict(figures=7,formal_complete=True)))
