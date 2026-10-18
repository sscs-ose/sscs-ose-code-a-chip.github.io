"""Replay experiments and a prediction/evidence/explanation journal. Apache-2.0.

No network, simulation, widget runtime or paid service. Explicit Python parameters
are the portable controls; all selections refer to recorded data.
"""
from pathlib import Path
from dataclasses import replace
import json
import hashlib
import numpy as np
from evidence import assess_run, rising_crossings
from functional import FunctionalContract, assess_function

ROOT=Path(__file__).resolve().parent
CASES={
    'old_nonlinear':'tt27_continuous_nanoamp',
    'corrected_nonlinear':'tt27_continuous_fossi',
    'old_linear':'tt27_linear_probe',
    'corrected_linear':'tt27_linear_fossi',
    'slow_supply':'tt27_continuous_fossi_slow',
    'dc_original':'tt27_continuous_wrapped',
    'dc_removed':'tt27_continuous_init0',
}


def load_case(case):
    if case not in CASES: raise ValueError('Select a recorded case: '+', '.join(CASES))
    p=ROOT/'data/runs'/CASES[case]
    return np.loadtxt(p/'wave.tsv',skiprows=1),p


def experiment(case='corrected_nonlinear', *, observe_until_ms=None,
               measurement_start_ms=1.5, threshold_v=.9, scalar_max_ms=2.,
               deadline_ms=2.):
    """Reassess a recorded trace; no SPICE execution and no synthetic waveforms.

    The replay measure uses first osc/POR events in the selected window. It does
    not compare a changed rule to the unchanged historical scalar export.
    The complete original extraction check is included as archive_audit.
    """
    a,p=load_case(case)
    end=a[-1,0]*1e3 if observe_until_ms is None else float(observe_until_ms)
    settings=[end,measurement_start_ms,threshold_v,scalar_max_ms,deadline_ms]
    if not all(np.isfinite(settings)) or not (0<end<=a[-1,0]*1e3+1e-9 and
            0<=measurement_start_ms<end and .2<=threshold_v<=1.6 and
            .5<=scalar_max_ms<=4 and .1<=deadline_ms<=4):
        raise ValueError('Use a recorded time range; start < end; threshold 0.2–1.6 V; scalar max 0.5–4 ms; deadline 0.1–4 ms')
    view=a[a[:,0]<=end*1e-3+1e-12]
    if len(view)<2: raise ValueError('At least two recorded samples required')
    f=assess_function(view[:,0],view[:,1],view[:,3],replace(FunctionalContract(),response_deadline_s=deadline_ms*1e-3))
    events=[]
    for col in (2,3):
        times=rising_crossings(view[:,0],view[:,col],threshold_v)
        events.append(times[times>=measurement_start_ms*1e-3])
    measurement='VALID';reason='required ordered events observed';delay=None
    if not all(len(e) for e in events):
        missing=', '.join(label for label,e in zip(('oscillator','POR'),events) if not len(e))
        measurement='INVALID'
        reason=f'no {missing} rising crossing of {threshold_v:g} V in the selected {measurement_start_ms:g}–{end:g} ms window'
    elif events[1][0]<events[0][0]:
        measurement='INVALID';reason='POR precedes oscillator reference event'
    else: delay=float(events[1][0]-events[0][0])
    scalar='NOT_EVALUATED' if delay is None else ('PASS' if .5e-3<=delay<=scalar_max_ms*1e-3 else 'FAIL')
    archive=assess_run(p)
    if archive['execution']!='COMPLETE':
        raise ValueError('Recorded simulation did not complete; this teaching selector cannot certify it')
    return dict(case=case, source='RECORDED SPICE DATA; no new simulation',
                source_wave_sha256=hashlib.sha256((p/'wave.tsv').read_bytes()).hexdigest(),
                settings=dict(observe_until_ms=end,measurement_start_ms=measurement_start_ms,
                              threshold_v=threshold_v,scalar_max_ms=scalar_max_ms,deadline_ms=deadline_ms),
                execution=archive['execution'],measurement=measurement,measurement_reason=reason,
                scalar_spec=scalar,startup_s=delay,functional=f,archive_audit=archive,
                measurement_scope='selected-window waveform extraction; not a new SPICE scalar export')


def plot_cases(cases, reports=None, *, internal=False, observe_until_ms=None):
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(len(cases),1,figsize=(10,3.1*len(cases)),sharex=True,squeeze=False)
    max_ms=max(load_case(c)[0][-1,0]*1e3 for c in cases)
    for i,case in enumerate(cases):
        a,p=load_case(case);ax=axes[i,0]
        limit=reports[i]['settings']['observe_until_ms'] if reports else observe_until_ms
        if limit is not None: a=a[a[:,0]<=limit*1e-3+1e-12]
        for col,label,style,color in [(1,'AVDD','-','#b86e00'),(2,'osc_ck',':','#657582'),(3,'POR assertion','-','#006d77')]:
            ax.plot(a[:,0]*1e3,a[:,col],label=label,ls=style,color=color,lw=1.2)
        if internal:
            q=p/'internal.tsv'
            if q.exists():
                headers=q.read_text().splitlines()[0].split();b=np.loadtxt(q,skiprows=1)
                if limit is not None: b=b[b[:,0]<=limit*1e-3+1e-12]
                j=headers.index('v(xipor.xiana.force_pdnb_avdd)')
                ax.plot(b[:,0]*1e3,b[:,j],label='Analog comparator enable',ls='--',color='#8055a2')
            else: ax.text(.02,.88,'Internal probe not recorded for this case',transform=ax.transAxes)
        if reports:
            r=reports[i];s=r['settings'];f=r['functional']
            ax.axvspan(s['measurement_start_ms'],s['observe_until_ms'],alpha=.08,color='#006d77',label='Selected measurement window')
            for key,label,style in [('trigger_s','T1 supply trigger','--'),('deadline_s','T1 deadline',':'),('witness_s','T1 POR witness','-.')]:
                if f.get(key) is not None: ax.axvline(f[key]*1e3,color='#333',ls=style,lw=1,label=label)
            ax.axvline(s['observe_until_ms'],color='#b00020',lw=1.3,label='Observation end')
            ax.set_title(f"{case} | measure {r['measurement']} | scalar {r['scalar_spec']} | T1 {f['status']}",fontsize=10)
        else: ax.set_title(case+' | recorded SPICE waveform')
        if limit is not None and limit<max_ms:
            ax.axvspan(limit,max_ms,color='#dddddd',alpha=.5,label='Not observed in this view')
        ax.set(xlim=(0,max_ms),ylim=(-.15,3.65),ylabel='Voltage (V)')
        ax.grid(alpha=.15);ax.legend(loc='upper left',fontsize=7,ncol=3)
    axes[-1,0].set_xlabel('Time (ms)');fig.tight_layout()
    return fig


def explain(report):
    f=report['functional'];reason=f['reason'];s=report['settings']
    trigger=f.get('trigger_s');deadline=f.get('deadline_s');witness=f.get('witness_s')
    timing=(f'AVDD crosses 3.0 V at {trigger*1e3:.3f} ms, so the T1 deadline is {deadline*1e3:.3f} ms. '
            if trigger is not None else '')
    if reason=='deadline_not_observed':
        detail=(f'This view ends at {s["observe_until_ms"]:.3f} ms, before the deadline. '
                'Observe through the deadline before calling the missing response a failure.')
    elif reason.startswith('deadline_observed_without_new_por_rise'):
        detail=('The record covers that deadline while the supply stays valid, but no new POR rising edge appears after the trigger. '
                'An earlier high POR level does not satisfy this edge-based requirement.')
    elif reason=='new_por_rise_observed_within_deadline':
        detail=f'A new POR edge is observed at {witness*1e3:.3f} ms, within the deadline. This witnesses the narrow T1 response.'
    elif f['status']=='NOT_TRIGGERED':
        detail='No rising supply trigger is observed. This does not demonstrate the circuit response and is not a functional pass.'
    else:
        detail='The required evidence is incomplete or outside the first-startup assumptions: '+reason.replace('_',' ')+'.'
    return (f"Recorded execution: {report['execution']}. Selected-window measurement: "
            f"{report['measurement']} ({report['measurement_reason']}). Scalar bounds: "
            f"{report['scalar_spec']}. T1 function: {f['status']}. "+timing+detail+
            ' T1 is an educational assumption; neither '
            'this status nor an unchanged simulator exit code establishes full circuit compliance.')


class Investigation:
    """Small explicit interaction state machine; saved locally only on request."""
    def __init__(self):
        self.entries={}
        self.history=[]

    def predict(self, task, prediction, reason):
        if not prediction.strip() or not reason.strip():
            raise ValueError('Record a prediction and your reason before opening evidence')
        if task in self.entries:
            self.history.append(dict(task=task,entry=json.loads(json.dumps(self.entries[task]))))
        self.entries[task]=dict(prediction=prediction,reason=reason)

    def observe(self, task, case, **kwargs):
        if task not in self.entries: raise ValueError('Predict first')
        e=self.entries[task];e.pop('explanation',None);e.pop('feedback',None)
        e['report']=experiment(case,**kwargs)
        return e['report']

    def reflect(self, task, explanation):
        if not explanation.strip(): raise ValueError('Explain the evidence before asking for feedback')
        e=self.entries[task]
        if 'report' not in e: raise ValueError('Observe first')
        e['explanation']=explanation
        e['feedback']=('Compare your prediction "'+e['prediction']+'" with the evidence. '+
                       explain(e['report'])+' If they differ, revise the event, coverage or contract assumption, '
                       'and name the waveform observation that changed your view. Free-text reasoning is not automatically graded.')
        return e['feedback']

    def save(self, path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'current':self.entries,'prior_attempts':self.history},indent=2,ensure_ascii=False),encoding='utf-8')


def hypothesis_feedback(hypothesis):
    options={
        'dc_override': 'Removing DC override alone leaves the event missing (dc_original vs dc_removed). This rejects sufficiency of that explanation, not every initialization effect.',
        'resistor_only': 'Corrected HVL restores a valid result for BOTH resistor variants. Simplifying the resistor is not necessary for the corrected nominal case.',
        'hvl_dependency': 'The matched HVL interventions support a dependency-level explanation. The level-shifter fix already existed upstream; these experiments do not prove the historical designer used the old cells.',
        'window_only': 'Changing a window can admit the early POR edge, but cannot create a new post-supply-trigger edge. Extraction rules and T1 ask different questions.',
    }
    if hypothesis not in options: raise ValueError('Choose '+', '.join(options))
    return options[hypothesis]
