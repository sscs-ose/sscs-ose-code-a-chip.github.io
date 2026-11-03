"""Read preserved trial receipts; distinguish final scores from diagnostic deliveries."""
import json
import math
import statistics
from collections import Counter

from capacity_protocol import CHECKPOINTS, TASKS, MODELS, summarize

OUTCOMES=('functional_pass','gds_pass','joint_pass','constraint_pass','final_score')


def invocation_costs(runtime):
    rows=[]
    for folder in sorted((runtime/'invocations').glob('*')):
        request=json.loads((folder/'request.json').read_text())
        path=folder/'result.json'
        result=json.loads(path.read_text()) if path.exists() else {}
        rows.append(dict(invocation=folder.name,role=request.get('role'),stage=request.get('stage'),
            terminal=path.exists(),tokens=result.get('invocation_tokens'),
            active_seconds=result.get('invocation_active_seconds'),
            physical_seconds=result.get('invocation_physical_seconds'),reason=result.get('reason')))
    named=[r for r in rows if r['role'] is not None]
    counts=Counter(r['stage'] for r in rows if r['stage'] is not None)
    return dict(invocations=rows,call_count=len(rows),
        role_count=len({r['role'] for r in named}),
        role_switches=sum(a['role']!=b['role'] for a,b in zip(named,named[1:])),
        repeated_stage_calls=sum(max(0,n-1) for n in counts.values()),
        scope='Actual serial dispatches; role switches and repeated stages are proxies, not proven useful handoffs or repairs')


def observation(row):
    """Invalid measurements remain in the full denominator with zero credited outcomes."""
    if row.get('measurement_valid') is not True:
        return dict(terminal=row.get('terminal'),**{k:0 if k=='final_score' else False for k in OUTCOMES})
    if any(type(row.get(k)) is not bool for k in OUTCOMES[:-1]):
        raise ValueError('Malformed outcome flags')
    value=row.get('final_score')
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=100:
        raise ValueError('Malformed final score')
    f,g,j,h=(row[k] for k in OUTCOMES[:-1])
    if j!=(f and g) or (h and not j) or (value>0 and not h):
        raise ValueError('Contradictory three-layer outcome')
    return dict(terminal=True,**{k:row[k] for k in OUTCOMES})


def distribution(values):
    known=[v for v in values if v is not None]
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in known):
        raise ValueError('Invalid cost')
    return dict(known=len(known),missing=len(values)-len(known),
        total=sum(known) if known else None,median=statistics.median(known) if known else None)


def transitions(row):
    if 'physical_attempts' not in row:return 'unresolved_measurement'
    attempts=row['physical_attempts']
    diagnostics={r['physical_attempt']:r for r in row.get('physical_diagnostics',[])}
    if len(attempts)<2:return 'fewer_than_two_attempts'
    if len(attempts)>2:raise ValueError('Physical attempt quota exceeded')
    a,b=(diagnostics.get(r['identity'],{}) for r in attempts)
    if not all(r.get('measurement_valid') is True for r in (a,b)):return 'unresolved_measurement'
    a,b=observation(a),observation(b)
    if a['constraint_pass'] and not b['constraint_pass']:return 'qualified_to_unqualified'
    if b['constraint_pass'] and not a['constraint_pass']:return 'unqualified_to_qualified'
    if not a['constraint_pass']:return 'both_unqualified'
    if b['final_score']>a['final_score']:return 'qualified_score_improved'
    if b['final_score']<a['final_score']:return 'qualified_score_regressed'
    return 'qualified_score_unchanged'


def read_trials(root,category):
    protocol=json.loads((root/'protocol.json').read_text())
    jobs=protocol[category+'_jobs'];rows=[]
    for job in jobs:
        path=root/'trials'/category/job['id']/'result.json'
        if not path.exists():
            rows.append(dict(job=job,terminal=False,status='unfinished' if path.parent.exists() else 'not_started'))
            continue
        row=json.loads(path.read_text())
        if row['job']!=job or row.get('model')!=job['model'] or row.get('reasoning')!='high':
            raise ValueError('Trial identity/model mismatch: '+job['id'])
        if row.get('terminal') is not True:raise ValueError('Nonterminal result receipt: '+job['id'])
        points=row['checkpoints']
        if [p['budget'] for p in points]!=list(CHECKPOINTS):raise ValueError('Missing/duplicate checkpoints')
        if any(p.get('selection')=='physical_attempt_diagnostic' for p in points):
            raise ValueError('Diagnostic substituted for primary endpoint')
        if any(row[k]!=points[-1][k] for k in OUTCOMES):raise ValueError('Final differs from latest endpoint')
        if row.get('measurement_valid') is True and not (
                row.get('usage',{}).get('measurement_valid') is True and points[-1].get('measurement_valid') is True):
            raise ValueError('Valid trial contradicts its usage or final measurement evidence')
        observation(row)
        rows.append(row)
    expected={j['id'] for j in jobs}
    if any(p.parent.name not in expected for p in (root/'trials'/category).glob('*/result.json')):
        raise ValueError('Unregistered trial in formal/pilot result directory')
    return rows


def cohort(rows):
    terminal=[r for r in rows if r.get('terminal') is True]
    complete=len(terminal)==len(rows)
    valid=[r for r in terminal if r.get('measurement_valid') is True and
           r.get('status')!='infrastructure_error' and r.get('frontend_status')!='infrastructure_error']
    metrics=summarize([observation(r) for r in rows]) if complete else None
    costs={key:distribution([r.get(key) for r in terminal]) for key in
        ('preparation_seconds','active_frontend_seconds','physical_wait_seconds','grading_seconds','total_wall_seconds')}
    for key in ('actual_tokens','overshoot_tokens','cached_input_tokens'):
        costs[key]=distribution([r.get('usage',{}).get(key) for r in terminal])
    costs['physical_attempts']=distribution([len(r['physical_attempts']) if 'physical_attempts' in r else None for r in terminal])
    for key in ('call_count','role_switches','repeated_stage_calls'):
        costs[key]=distribution([r.get('coordination',{}).get(key) for r in terminal])
    for key in ('development','synthesis_sta','physical'):
        costs['tool_'+key]=distribution([sum(a['kind']==key for a in r['tools']['attempts'])
            if 'tools' in r else None for r in terminal])
    first={}
    for endpoint in ('functional_pass','joint_pass','constraint_pass'):
        first[endpoint]={unit:distribution([r.get('first_observed_success_'+unit,{}).get(endpoint)
            for r in valid]) for unit in ('tokens','seconds')}
    return dict(n=len(rows),terminal=len(terminal),valid=len(valid),complete=complete,full_denominator=metrics,
        valid_samples=summarize([observation(r) for r in valid]) if complete and valid else None,
        costs=costs,first_observed_success=first,
        status_counts=dict(Counter(r.get('status','unknown') for r in rows)),
        physical_transitions=dict(Counter(transitions(r) for r in terminal)),
        failure_reasons=dict(Counter(reason for r in terminal for reason in r['checkpoints'][-1].get('failure_reasons',[]))))


def analyze(root,category='formal'):
    rows=read_trials(root,category)
    groups={}
    for row in rows:
        j=row['job'];groups.setdefault((j['model'],j['workflow'],j['task']),[]).append(row)
    cells=[dict(model=m,workflow=w,task=t,**cohort(group)) for (m,w,t),group in sorted(groups.items())]
    workflows=[]
    for model,workflow in sorted({(m,w) for m,w,t in groups}):
        tasks=[c for c in cells if c['model']==model and c['workflow']==workflow]
        complete=all(c['complete'] for c in tasks) and {c['task'] for c in tasks}==set(TASKS)
        means=None
        if complete:
            keys=[k+'_rate' for k in OUTCOMES[:-1]]+['average_score']
            means={k:sum(c['full_denominator'][k] for c in tasks)/len(TASKS) for k in keys}
        workflows.append(dict(model=model,workflow=workflow,complete=complete,equal_task_means=means))
    checkpoints=[]
    for budget in CHECKPOINTS:
        checkpoint_rows=[]
        for row in rows:
            if row.get('terminal'):
                point=next(p for p in row['checkpoints'] if p['budget']==budget)
                point=dict(point,terminal=True,measurement_valid=bool(row.get('usage',{}).get('measurement_valid')) and point.get('measurement_valid') is True)
                checkpoint_rows.append(dict(point,job=row['job']))
            else:checkpoint_rows.append(row)
        for model,workflow in sorted({(m,w) for m,w,t in groups}):
            tasks=[]
            for task in TASKS:
                sample=[r for r in checkpoint_rows if r['job']['model']==model and r['job']['workflow']==workflow and r['job']['task']==task]
                tasks.append(summarize([observation(r) for r in sample]) if sample and all(r.get('terminal') for r in sample) else None)
            means=None
            if all(tasks):means={k:sum(t[k] for t in tasks)/len(TASKS) for k in ('functional_pass_rate','average_score')}
            checkpoints.append(dict(model=model,workflow=workflow,budget=budget,equal_task_means=means))
    return dict(category=category,planned=len(rows),terminal=sum(r.get('terminal') is True for r in rows),
        complete=all(r.get('terminal') for r in rows),cells=cells,workflows=workflows,checkpoints=checkpoints,
        sessions=[dict(id=r['job']['id'],terminal=r.get('terminal'),status=r['status'],
            credited=observation(r) if r.get('terminal') else None,
            physical_transition=transitions(r) if r.get('terminal') else None) for r in rows],
        notes=['Incomplete cohorts have no reported success rates or scores.',
            'Full denominators retain invalid and infrastructure outcomes; missing costs are not zero.',
            'GDS rate is independent of functionality. Nested funnel uses F, F and G, F and G and H.',
            'Equal-task means weight each of the four tasks equally; three repeats are descriptive.',
            'First observed success uses three checkpoints and submitted physical sources; unknown or unreached costs remain null.',
            'Diagnostic physical success never substitutes for the final submitted snapshot.'])
