"""Build finite, offline GUI choices from the verified Python checker. Apache-2.0.

No new SPICE runs, dependency downloads or browser-side engineering algorithm.
"""
from pathlib import Path
from io import BytesIO
import base64, hashlib, html, itertools, json, os, time
os.environ.update(MPLBACKEND='Agg',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import matplotlib.pyplot as plt
from lesson import experiment, plot_cases, explain, hypothesis_feedback
from evidence import verify_manifest

P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    started=time.perf_counter();verify_manifest(P)
    plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'font.size':10})
    images={};variants={}
    names={'old_nonlinear':'Old HVL / nonlinear resistor','corrected_nonlinear':'Corrected HVL / nonlinear resistor',
           'old_linear':'Old HVL / simplified resistor','corrected_linear':'Corrected HVL / simplified resistor',
           'dc_original':'Original DC setting','dc_removed':'DC override removed','slow_supply':'Slow supply ramp'}
    def picture(cases,reports=None,internal=False,preview=False):
        fig=plot_cases(cases,reports,internal=internal,observe_until_ms=4.4 if preview else None)
        for ax,c in zip(fig.axes,cases):
            ax.set_title(names[c]+' | recorded SPICE evidence',fontsize=10)
        b=BytesIO();fig.savefig(b,format='png',dpi=120,bbox_inches='tight');plt.close(fig)
        raw=b.getvalue();key=hashlib.sha256(raw).hexdigest()
        images[key]='data:image/png;base64,'+base64.b64encode(raw).decode()
        return key
    def compact(r):
        return {k:r[k] for k in ['case','source','source_wave_sha256','settings','execution','measurement',
            'measurement_reason','scalar_spec','startup_s','functional','measurement_scope']}
    def add(key,cases,kwargs=None,internal=False,conditions=''):
        kwargs=kwargs or [{} for _ in cases]
        reports=[experiment(c,**kw) for c,kw in zip(cases,kwargs)]
        variants[key]=dict(image=picture(cases,reports,internal),reports=[compact(r) for r in reports],
            result=compact(reports[-1]),explanation=explain(reports[-1]),
            alt='Recorded AVDD, oscillator and POR waveforms, with observed-window and event markers for '+', '.join(names[c] for c in cases),
            conditions=conditions or 'tt / 27 °C; AVDD 0–3.3 V; DVDD 1.8 V. Record identities and rule settings are listed below.')
    for end in [2,2.5,3,3.5,4]:
        add('window:'+str(end),['old_nonlinear'],[dict(observe_until_ms=end)],
            conditions=f'Old HVL, nonlinear resistor, 2 ms supply ramp. Observe only through {end:g} ms. Gray space is unobserved; no future signal is drawn.')
    for model in ['linear','nonlinear']:
        add('model:hvl_dependency:'+model,['old_'+model,'corrected_'+model],internal=model=='linear',
            conditions='Change only the HVL dependency in this matched comparison. The SECOND case is the prediction target. The upstream correction is not our fix.')
        add('model:resistor_only:'+model,['corrected_nonlinear','corrected_linear'],
            conditions='Hold corrected HVL fixed; compare nonlinear and simplified resistor representations. The SECOND case is the target.')
        add('model:dc_override:'+model,['dc_original','dc_removed'],
            conditions='Matched original setup: remove only the AVDD DC override. This pair is separate from the later 1e-9 current-tolerance set. The SECOND case is the target.')
        add('model:window_only:'+model,['old_nonlinear','old_nonlinear'],[dict(measurement_start_ms=1.5),dict(measurement_start_ms=0)],
            conditions='Same recorded old-HVL circuit. First measurement starts at 1.5 ms; SECOND at 0 ms. T1 stays unchanged. Only a measurement definition changes.')
    for start,threshold,upper in itertools.product([1,1.5,2],[.6,.9,1.2],[1,1.25,1.5,2]):
        key='rules:'+':'.join(f'{x:g}' for x in [start,threshold,upper])
        add(key,['corrected_nonlinear'],[dict(measurement_start_ms=start,threshold_v=threshold,scalar_max_ms=upper)],
            conditions=f'Same corrected nonlinear record. Extraction starts {start:g} ms at {threshold:g} V; scalar range 0.5–{upper:g} ms. T1 independently remains 3 V / 0.9 V / 2 ms.')
    for end in [4.4,6]:
        add('challenge:'+str(end),['slow_supply'],[dict(observe_until_ms=end)],
            conditions=f'Corrected HVL, nonlinear resistor, 4 ms AVDD ramp. Selected observation ends at {end:g} ms. This is a held-out view of a real record, not a new defect.')
    preview=dict(variants['challenge:4.4']);preview['image']=picture(['slow_supply'],preview=True)
    # No result/explanation field in the preview exposed before the challenge answer.
    preview={k:preview[k] for k in ['image','reports','alt','conditions']}
    payload=dict(release='0.5.0-rc1',kind='Finite Python-precomputed reassessments of recorded SPICE evidence',
        evidence_manifest_sha256=sha(P/'MANIFEST.json'),
        checker_sources={n:sha(P/n) for n in ['lesson.py','evidence.py','functional.py','build_controls.py']},
        variants=variants,challenge_preview=preview,images=images,
        hypotheses={h:hypothesis_feedback(h) for h in ['hvl_dependency','resistor_only','dc_override','window_only']})
    # Payload is separate for independent equivalence testing; the usable page embeds it for file:// offline use.
    (P/'CONTROL_DATA.json').write_text(json.dumps(payload,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
    template=(P/'ui/template.html').read_text(encoding='utf-8')
    page=template.replace('/*STYLE*/',(P/'ui/style.css').read_text()).replace('/*SCRIPT*/',(P/'ui/app.js').read_text(encoding='utf-8'))
    page=page.replace('/*DATA*/',json.dumps(payload,separators=(',',':'),ensure_ascii=False).replace('<','\\u003c'))
    (P/'INVESTIGATION_DESK.html').write_text(page,encoding='utf-8')
    # Standalone novice introduction uses the unchanged normal recorded waveform.
    intro=(P/'ui/start.html').read_text(encoding='utf-8').replace('/*STYLE*/',(P/'ui/style.css').read_text()).replace('/*NORMAL*/',images[variants['rules:1.5:0.9:2']['image']])
    (P/'START_HERE.html').write_text(intro,encoding='utf-8')
    # Static, native-HTML disclosure sequence works with JS disabled and no kernel.
    sections=[]
    tasks=[('1 · Observation window','Predict measurement validity and T1 status for 2.5 ms, then for 4 ms. Explain what additional evidence matters.',['window:2.5','window:4']),
           ('2 · Test a hypothesis','Predict what the corrected dependency changes. Name one alternative explanation and a falsifying observation.',['model:hvl_dependency:linear','model:dc_override:linear']),
           ('3 · Change one rule','Predict the effect of changing only the scalar upper limit from 2 ms to 1 ms. Which judgment changes?',['rules:1.5:0.9:2','rules:1.5:0.9:1']),
           ('4 · Independent challenge','Using only 4.4 ms of the slow-supply record, judge measurement and T1 separately. Write the next evidence request and a plain-language check.',['challenge:4.4','challenge:6'])]
    for title,question,keys in tasks:
        parts=[f'<section class="card"><h2>{title}</h2><p>{question}</p><p><strong>Before opening evidence:</strong> record your prediction and reason on paper or in a text document. After observing, write your explanation before revealing feedback.</p>']
        if keys[0]=='challenge:4.4':parts.append('<img alt="Limited slow-supply record; future hidden" src="'+images[preview['image']]+'">')
        for k in keys:
            v=variants[k];label={'window:2.5':'Old library: observe until 2.5 ms','window:4':'Same old library: observe until 4 ms','model:hvl_dependency:linear':'Compare old and corrected libraries — predict the second plot','model:dc_override:linear':'Compare original and removed DC setting — predict the second plot','rules:1.5:0.9:2':'Corrected record: maximum delay 2 ms','rules:1.5:0.9:1':'Same corrected record: maximum delay 1 ms','challenge:4.4':'Slow supply: inspect only the first 4.4 ms','challenge:6':'Longer record — open only after your initial answer'}[k]
            parts.append('<details><summary>'+html.escape(label)+'</summary><p class="provenance">REAL RECORDED SPICE DATA · Python-precomputed check · no new simulation</p><p>'+html.escape(v['conditions'])+'</p><img alt="'+html.escape(v['alt'],quote=True)+'" src="'+images[v['image']]+'"><details><summary>After writing your explanation, reveal feedback</summary><p>'+html.escape(v['explanation'])+'</p></details></details>')
        parts.append('</section>');sections.extend(parts)
    static='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Trust Before Pass — static worksheet</title><style>'+(P/'ui/style.css').read_text()+'</style></head><body><header><p class="eyebrow">NO SCRIPTS · NO PYTHON</p><h1>Static investigation worksheet</h1><p>First visit? <a href="START_HERE.html">Read the introduction and normal waveform</a>. Keep FEEDBACK_FORM.txt beside you, or use paper. Work through the four tasks in order.</p><p>Use paper or a text document to record predictions. Native disclosure controls reveal finite recorded evidence and explanations. This is a static fallback, not live simulation or automatic grading.</p><p class="provenance">T1 is a teaching assumption: new POR rise within 2 ms of an AVDD rise through 3 V, under stated supply/sampling conditions. It is not the original designer’s established acceptance specification.</p><p><a href="INVESTIGATION_DESK.html">Return to the experiment controls</a></p></header><main>'+''.join(sections)+'</main><footer>Real archived SPICE data; known upstream HVL fix retains authorship. No reader outcomes claimed.</footer></body></html>'
    (P/'STATIC_WORKBOOK.html').write_text(static,encoding='utf-8')
    record=dict(release=payload['release'],variants=len(variants),unique_images=len(images),wall_s=time.perf_counter()-started,
        new_download_bytes=0,new_simulations=0,html_bytes=(P/'INVESTIGATION_DESK.html').stat().st_size,
        static_bytes=(P/'STATIC_WORKBOOK.html').stat().st_size,payload_sha256=sha(P/'CONTROL_DATA.json'),
        checker_sources=payload['checker_sources'],gui_sources={str(n):sha(P/n) for n in ['ui/template.html','ui/style.css','ui/app.js','ui/start.html']})
    (P/'CONTROL_BUILD.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__':build()
