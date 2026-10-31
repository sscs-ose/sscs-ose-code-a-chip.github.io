"""Draw workflow figures and measured study plots from one preserved results tree."""
from __future__ import annotations

import argparse
import html
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from study_protocol import digest, ranking, write_json
from summarize_ppa_study import infrastructure_costs

COLORS = {'W0':'#64748b', 'W1':'#087f8c', 'W2':'#8b5cf6'}
MARKERS = {'W0':'s', 'W1':'o', 'W2':'^'}
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'svg.fonttype':'none',
    'axes.spines.top':False, 'axes.spines.right':False, 'axes.titleweight':'bold', 'figure.dpi':160})


class WorkflowFigure:
    def __init__(self, width, height, title, description):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(description)}</desc>',
            '<defs><pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#23334c"/></pattern>',
            '<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#7dd3fc"/></marker>',
            '<marker id="feedback" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#fbbf24"/></marker></defs>',
            f'<rect width="{width}" height="{height}" rx="16" fill="#101827"/><rect width="{width}" height="{height}" fill="url(#dots)"/>',
            '<g font-family="DejaVu Sans,Arial,sans-serif">']
        self.text(28,38,title,25,'#f8fafc',True)

    def text(self,x,y,text,size=15,color='#cbd5e1',bold=False):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{html.escape(text)}</text>')

    def card(self,x,y,w,h,label,lines,kind='agent',tag=None):
        color = {'agent':'#38bdf8','tool':'#2dd4bf','gate':'#c4b5fd','input':'#94a3b8'}[kind]
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#18283f" stroke="{color}" stroke-width="1.5"/>')
        self.parts.append(f'<circle cx="{x+15}" cy="{y+22}" r="4" fill="{color}"/>')
        self.text(x+27,y+28,label,16,'#f8fafc',True)
        for i,line in enumerate(lines):
            self.text(x+14,y+57+i*22,line,13)
        if tag:
            self.parts.append(f'<rect x="{x+10}" y="{y+h-33}" width="{w-20}" height="24" rx="5" fill="#312454"/>')
            self.text(x+18,y+h-16,tag,12,'#ddd6fe')

    def arrow(self,x1,y1,x2,y2,feedback=False,bend=None):
        points=f'M{x1} {y1} L{x2} {y2}' if bend is None else f'M{x1} {y1} L{x1} {bend} L{x2} {bend} L{x2} {y2}'
        self.parts.append(f'<path d="{points}" fill="none" stroke="{"#fbbf24" if feedback else "#7dd3fc"}" stroke-width="2"'
                          f' marker-end="url(#{"feedback" if feedback else "arrow"})"'+(' stroke-dasharray="6 4"' if feedback else '')+'/>')

    def save(self,path):
        path.write_text(''.join(self.parts)+'</g></svg>')


def overview(output):
    f=WorkflowFigure(1440,820,'ChipWave · configure, freeze, execute, compare',
        'Built-in specification-to-GDS roles and workflow, custom fixed-contract experiments, immutable deliveries and independent engineering gates.')
    f.text(28,76,'Built-in templates + project-local roles, recipes, tools, skills and IP',17)
    f.card(28,105,1384,100,'Freeze the experiment',
        ['Inputs · role prompts/model · permissions · dependencies · tool versions · IP · budgets · acceptance · selection rule'],
        'gate', 'Change a configuration → create a new frozen experiment; retain the previous run')
    labels=[('Design entry',['Requirements or design','Optional existing IP'],'input','immutable source'),
            ('Specification',['Author + closure reviewer','CSIR compiler / constraints'],'agent','specification + acceptance'),
            ('RTL / integration',['RTL designer + integrator','Implement or adapt IP'],'agent','versioned source delivery'),
            ('Verification',['Independent verifier','Functional / protocol checks'],'gate','release only on pass'),
            ('Physical design',['Synthesis / P&R roles','Open-source EDA tools'],'tool','STA · electrical · DRC · LVS'),
            ('GDS / evidence',['GDS exporter','Layout + reports'],'tool','qualified result or failure')]
    for i,(label,lines,kind,tag) in enumerate(labels):
        x=28+i*234
        f.card(x,260,214,160,label,lines,kind,tag)
        if i<5:f.arrow(x+214,337,x+234,337)
    f.text(28,238,'STANDARD PATH · grouped view of the 20-task specification-to-GDS recipe',15,'#7dd3fc',True)
    f.arrow(1030,420,590,420,True,465)
    f.text(380,490,'Evidence returns to the existing responsible task; engineering gates run again',15,'#fcd34d')
    f.card(28,530,438,164,'Experiment A · roles and IP',
        ['Same dot4 contract: fresh RTL or raw IP','Single role or designer + reviewer','12 real trials; independent final checker'],'agent','Focused contract; no repeated CSIR authoring')
    f.card(496,530,438,164,'Experiment B · PPA workflows',
        ['Same verified CPU + NPU and 95 MHz target','Rules / one optimizer / optimizer + reviewer','Three new physical candidates per search'],'agent','EDA executes independently of AI decisions')
    f.card(964,530,448,164,'Compare with retained evidence',
        ['Success + failures + unused budget slots','Time · Tokens · repairs · area · energy','Source-bound workload and parasitic checks'],'gate','Search finished ≠ chip qualified')
    f.text(28,742,'Built-in engineering path and custom research workflows share Role, TaskGraph, Artifact and feedback mechanisms.',15)
    f.text(28,779,'Measured: within-run feedback. Cross-design RSI / skill self-improvement is not evaluated here.',14,'#94a3b8')
    f.save(output/'study_platform.svg')


def tutorial_figure(results,output):
    data=json.loads((results/'tutorial/summary.json').read_text())
    assert data['passed'] and len(data['lessons'])==4
    f=WorkflowFigure(1400,700,'Four edits, four frozen workflows',
        'Four executed offline lessons show role customization, an independent reviewer, dependency changes, and existing-IP integration.')
    titles=['1 · Derive a custom role','2 · Add an independent verifier',
            '3 · Check before review','4 · Replace the execution unit with raw IP']
    for i,(lesson,title) in enumerate(zip(data['lessons'],titles)):
        x=28+(i%2)*700;y=100+(i//2)*285
        f.text(x,y,title,19,'#e0f2fe',True)
        order=['designer','audit'] if i==0 else ['designer','verifier','audit'] if i==1 else ['designer','audit','verifier']
        labels={'designer':'Custom designer','audit':'Tool checker','verifier':'Verifier'}
        for j,name in enumerate(order):
            xx=x+j*214
            lines=['Replay saved RTL'] if name=='designer' else ['Run Icarus checks']
            if i==3 and name=='designer':lines=['4 unchanged PEs + adapter']
            f.card(xx,y+24,194,104,labels[name],lines,'tool' if name=='audit' else 'agent')
            if j:f.arrow(xx-20,y+76,xx,y+76)
        if len(order)>2:
            f.arrow(x+98,y+24,x+528,y+24,False,y+12)
            f.arrow(x+528,y+128,x+98,y+128,True,y+164)
            f.arrow(x+314,y+128,x+98,y+128,True,y+164)
            f.text(x+135,y+187,'failed review → same designer',13,'#fcd34d')
        assert lesson['state']=='complete' and lesson['model_calls']==0
        f.text(x,y+222,'Executed: all tasks satisfied · 0 new model calls',14,'#5eead4')
        f.text(x,y+243,'Saved, independently checked trial: '+lesson['trial'],12,'#94a3b8')
    f.text(28,675,'Offline lessons replay generated artifacts and execute real checks; separate opt-in commands run new AI trials.',14)
    f.save(output/'study_tutorial.svg')


def ppa_workflows(output):
    f=WorkflowFigure(1440,760,'PPA exploration · the decision workflow is the variable',
        'W0 deterministic heuristic, W1 AI optimizer, W2 AI optimizer and independent reviewer; all share frozen hardware, tools, budgets and engineering gates.')
    f.text(28,78,'Fixed RTL · 95 MHz · 36 legal parameter tuples · max 3 new physical candidates / session',16)
    for i,workflow in enumerate(('W0','W1','W2')):
        y=130+i*180
        f.text(28,y+30,workflow,24,'#e0f2fe',True)
        f.text(28,y+57,'1 search' if workflow=='W0' else '3 sessions',12)
        f.card(140,y,270,120,'Report-driven rules' if workflow=='W0' else 'AI PPA optimizer',
            ['Read actual session history','Choose one unseen legal tuple'],'tool' if workflow=='W0' else 'agent')
        if workflow=='W2':
            f.arrow(410,y+58,445,y+58)
            f.card(445,y,230,120,'Independent reviewer',['Check evidence + proposal','Reject → original optimizer'],'agent')
            f.arrow(560,y+120,340,y+120,True,y+134)
            f.arrow(675,y+58,710,y+58)
        else:
            f.arrow(410,y+58,710,y+58)
            f.text(456,y+42,'no review role',13,'#94a3b8')
        f.card(710,y,300,120,'EDA + energy measurement',
            ['Synthesis → route → extraction','Workload VCD + SPEF → energy'],'tool')
        f.arrow(1010,y+58,1045,y+58)
        f.card(1045,y,365,120,'Common engineering gates',
            ['Function · timing · electrical · DRC · LVS','Source / clock / activity / RC completeness'],'gate')
        f.arrow(1228,y+120,275,y+120,True,y+147)
        f.text(470,y+168,'pass or fail → next proposal; budget exhausted → final summary',13,'#fcd34d')
    f.text(28,716,'W1 / W2: 1,200 s aggregate AI time; EDA waiting separate. Failures consume slots. No RTL or checker changes.',15)
    f.save(output/'study_ppa_workflows.svg')


def save(fig,output,name):
    fig.savefig(output/(name+'.svg'),bbox_inches='tight')
    fig.savefig(output/(name+'.png'),bbox_inches='tight',dpi=180)
    plt.close(fig)


def generation(results,output):
    data=json.loads((results/'generation/analysis.json').read_text())
    assert data['complete'] and len(data['rows'])==12
    fig,axes=plt.subplots(1,3,figsize=(12.5,3.7))
    labels=['Fresh\nSingle','Fresh\nMulti','Raw IP\nSingle','Raw IP\nMulti']
    palette=['#087f8c','#4f46e5','#087f8c','#4f46e5']
    for i,cell in enumerate(data['cells']):
        rows=[row for row in data['rows'] if row['job']['input']==cell['input'] and row['job']['roles']==cell['roles']]
        axes[0].bar(i,cell['passed'],color=palette[i],width=.6)
        axes[0].text(i,cell['passed']+.08,f"{cell['passed']}/3",ha='center')
        times=[row['engineering_seconds'] for row in rows]
        axes[1].scatter([i-.09,i,i+.09],times,color=palette[i],s=35,zorder=3)
        axes[1].plot([i-.22,i+.22],[statistics.median(times)]*2,color='#111827',linewidth=2)
        axes[2].bar(i,cell['median_uncached_input_tokens']/1000,color=palette[i],width=.6)
        axes[2].bar(i,cell['median_output_tokens']/1000,bottom=cell['median_uncached_input_tokens']/1000,
                    color='#cbd5e1',width=.6)
    for ax in axes:ax.set_xticks(range(4),labels);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axes[0].set(ylim=(0,3.7),ylabel='Independent final passes',title='Correctness')
    axes[1].set(ylabel='Engineering workflow (seconds)',title='Every trial; black line = median')
    axes[2].set(ylabel='Median Tokens (thousands)',title='Component medians: input + output')
    axes[2].text(.02,.97,'Colored: uncached input\nGray: output',transform=axes[2].transAxes,va='top',fontsize=8)
    fig.suptitle('Small dot4 task · 3 repeats per cell · same model, contract and 1,200 s budget',fontsize=12)
    fig.tight_layout();save(fig,output,'study_generation')
    write_json(output/'study_generation.source.json',{'analysis_sha256':digest(results/'generation/analysis.json'),
        'rows':12,'scope':'Descriptive small-sample comparison; no confidence or general model capability claim'})


def searches(results,output):
    plan=json.loads((results/'protocol.json').read_text())
    analysis=json.loads((results/'ppa/analysis.json').read_text())
    assert analysis['complete']
    accounted={row['id']:row for row in analysis['rows']}
    sessions=[json.loads((results/'ppa'/job['id']/'results/search-summary.json').read_text()) for job in plan['ppa']['sessions']]
    assert all(session['finished'] for session in sessions)
    _,startup_seconds=infrastructure_costs(results)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    fig2,ax=plt.subplots(figsize=(7.5,5))
    qualified_points=[]
    for session in sessions:
        workflow=session['job']['workflow'];color=COLORS[workflow]
        style={1:'-',2:'--',3:':'}[session['job']['repetition']]
        rows={row['candidate_index']:row for row in session['candidates']}
        best=1.;x=[0];y=[1.];wall=[0]
        for slot in sorted(session['slots'],key=lambda item:item['candidate_index']):
            if slot['status']=='unused':continue
            row=rows.get(slot['candidate_index'])
            if row is None and slot['status']!='launched_incomplete':
                raise ValueError('Consumed plot slot lacks an evaluation or an explicit incomplete status')
            if row and row['rank_eligible']:best=min(best,row['score'])
            x.append(slot['candidate_index']);y.append(best)
            elapsed=row['elapsed_search_seconds'] if row else accounted[session['job']['id']]['total_wall_seconds']
            wall.append((elapsed+startup_seconds.get(session['job']['id'],0))/60)
            if row and row['rank_eligible']:
                ax.scatter(row['area_ratio'],row['energy_ratio'],s=45,color=color,alpha=.85,marker=MARKERS[workflow])
                qualified_points.append(dict(row,workflow=workflow))
            else:
                axes[0].scatter(slot['candidate_index'],best,marker='x',s=35,color=color,zorder=5)
        axes[0].step(x,y,where='post',color=color,alpha=.85,linestyle=style,label=session['job']['id'])
        axes[1].step(wall,y,where='post',color=color,alpha=.85,linestyle=style,label=session['job']['id'])
    for axis in axes:
        axis.axhline(1,color='#cbd5e1',linestyle=':');axis.grid(alpha=.2)
        axis.set_ylabel('Best qualified incumbent Q')
    axes[0].set(xlabel='Consumed physical-candidate slots',xticks=[0,1,2,3],title='Physical search efficiency')
    axes[1].set(xlabel='Wall time (min; EDA and startup interruptions included)',title='Elapsed cost to reach an incumbent')
    axes[1].legend(fontsize=8,ncol=2)
    fig.suptitle('All seven searches; × marks an unqualified or incomplete slot; baseline cost separate',fontsize=11)
    fig.tight_layout();save(fig,output,'study_search_efficiency')
    ax.scatter([1],[1],marker='*',s=160,color='#111827',label='Common baseline',zorder=10)
    for workflow,color in COLORS.items():ax.scatter([],[],color=color,label=workflow,marker=MARKERS[workflow])
    offsets={'W0':(12,24),'W1':(12,-56),'W2':(-105,25)}
    for workflow in COLORS:
        group=[row for row in qualified_points if row['workflow']==workflow]
        if group:
            best=min(group,key=ranking)
            repeated=sum(row['area_ratio']==best['area_ratio'] and row['energy_ratio']==best['energy_ratio'] for row in group)
            label=workflow+f" best Q={best['score']:.3f}\n{repeated} candidate{'s' if repeated!=1 else ''} at this point"
            ax.annotate(label,(best['area_ratio'],best['energy_ratio']),
                xytext=offsets[workflow],textcoords='offset points',fontsize=9,color=COLORS[workflow],
                arrowprops={'arrowstyle':'-','color':COLORS[workflow],'linewidth':.8})
    xs=[1,*[row['area_ratio'] for row in qualified_points]];ys=[1,*[row['energy_ratio'] for row in qualified_points]]
    xpad=max((max(xs)-min(xs))*.3,.04);ypad=max((max(ys)-min(ys))*.35,.04)
    low=max(.01,min(xs)-xpad);high=max(xs)+xpad
    curve=[low+(high-low)*i/99 for i in range(100)]
    ax.plot(curve,[1/x for x in curve],color='#cbd5e1',linestyle='--',linewidth=1,label='Equal score Q = 1')
    ax.set_xlim(low,high);ax.set_ylim(max(.01,min(ys)-ypad),max(ys)+ypad)
    failed=sum(session['physical_launches'] for session in sessions)-len(qualified_points)
    ax.set(xlabel='Standard-cell area / baseline area',ylabel='Geometric mean workload energy / baseline',
           title='Qualified area–energy tradeoffs')
    ax.text(.02,.02,f'{failed} unqualified or incomplete slots; see the result table',
            transform=ax.transAxes,fontsize=8)
    ax.grid(alpha=.2);ax.legend();fig2.tight_layout();save(fig2,output,'study_area_energy')
    provenance={'analysis_sha256':digest(results/'ppa/analysis.json'),
        'protocol_sha256':digest(results/'protocol.json'),
        'search_summaries_sha256':{job['id']:digest(results/'ppa'/job['id']/'results/search-summary.json')
                                 for job in plan['ppa']['sessions']},
        'qualified_points':len(qualified_points),'unqualified_or_incomplete_slots':failed,
        'scope':'All scheduled sessions; incomplete slots consume attempts but have no invented chip measurements'}
    for name in ('study_search_efficiency','study_area_energy'):
        write_json(output/(name+'.source.json'),provenance)


def run(results,output,foundations=False):
    output.mkdir(parents=True,exist_ok=True)
    overview(output);tutorial_figure(results,output);ppa_workflows(output);generation(results,output)
    if not foundations:searches(results,output)
    write_json(output/'study_figures.json',{'source':str(results),'foundations_only':foundations,
        'figures':[p.name for p in output.glob('study_*.svg')],
        'scope':'Workflow diagrams describe declared structure; numeric plots use actual saved trials'})
    print('STUDY_FIGURES_RENDERED')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--foundations',action='store_true')
    args=parser.parse_args();run(args.results.resolve(),args.output.resolve(),args.foundations)
