"""Render measured application/RTL comparisons and a resumable progress report."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def summarize(root,work):
    root=Path(root).resolve();work=Path(work).resolve();fig=work/'figures';fig.mkdir(exist_ok=True)
    app=json.loads((work/'application/application_metrics.json').read_text())
    decoder=json.loads((work/'decoder/verification.json').read_text())
    rtl=json.loads((work/'application_rtl/verification.json').read_text())
    costs=json.loads((work/'costs/costs.json').read_text())
    subjects=app['test_subjects'];rng=np.random.default_rng(20261028)
    samples=rng.integers(0,len(subjects),(2000,len(subjects)))
    def f1(cm):
        tp=np.diag(cm);den=cm.sum(0)+cm.sum(1)
        return np.divide(2*tp,den,out=np.zeros(6),where=den!=0).mean()
    bootstrap={}
    for name in app['models']:
        cm=np.array([app['per_subject'][str(s)][name]['confusion_matrix'] for s in subjects])
        vals=np.array([f1(cm[i].sum(0)) for i in samples]);bootstrap[name]=vals
    paired={}
    for name in ('linear_features','uniform_retrained','uniform_frozen','identity_frozen'):
        delta=bootstrap['integer_mha']-bootstrap[name]
        paired[name]={'macro_f1_point_difference':app['models']['integer_mha']['macro_f1']-app['models'][name]['macro_f1'],
            'paired_subject_bootstrap_95_interval':np.quantile(delta,[.025,.975]).tolist(),'bootstrap_replicates':2000,'subjects':9}
    (work/'application/paired_subject_comparison.json').write_text(json.dumps(paired,indent=2)+'\n')
    names=['linear_features','uniform_retrained','integer_mha','float'];labels=['Linear features','Uniform, retrained','AutoMX integer','Float attention']
    fig1,axes=plt.subplots(1,2,figsize=(12,4))
    values=[app['models'][n]['macro_f1']*100 for n in names]
    axes[0].bar(labels,values,color=['#aab7b8','#85c1e9','#148f77','#566573'])
    axes[0].set(ylabel='Test macro-F1 / %',ylim=(0,100),title='Six activities, nine unseen subjects')
    axes[0].tick_params(axis='x',labelrotation=15)
    for i,v in enumerate(values):axes[0].text(i,v+1,f'{v:.2f}',ha='center')
    cm=np.array(app['models']['integer_mha']['confusion_matrix']);axes[1].imshow(cm,cmap='Blues');axes[1].set(title='AutoMX integer confusion matrix',xlabel='Predicted activity',ylabel='True activity',xticks=range(6),yticks=range(6))
    for i in range(6):
        for j in range(6):axes[1].text(j,i,str(cm[i,j]),ha='center',va='center',color='white' if cm[i,j]>cm.max()/2 else 'black')
    fig1.tight_layout();fig1.savefig(fig/'application_results.png',dpi=160);plt.close(fig1)
    latency=decoder['frame_latency'];fig2,axes=plt.subplots(1,2,figsize=(11,4))
    paths={row['path']:row for row in rtl['results']}
    vals=[paths.get('linear',{}).get('latency_us_mean',latency[0]['latency_us']),paths['binary']['latency_us_mean'],paths['digital']['latency_us_mean']]
    axes[0].bar(['Linear decode','Binary decode','Digital sign/add'],vals,color=['#c0392b','#148f77','#2874a6'])
    axes[0].set(ylabel='RTL frame latency / us',title='Matched HAR inputs, 25 MHz; functional ADC model')
    for i,v in enumerate(vals):axes[0].text(i,v+1,f'{v:.2f}',ha='center')
    mapped={r['design']:r['mapped_area_um2'] for r in costs['designs']}
    keys=['linear_readout','binary_readout','digital_attention'];labels=['Linear readout','Binary readout','Digital MHA + projector']
    axes[1].bar(labels,[mapped[k]/1000 for k in keys],color=['#c0392b','#148f77','#2874a6'])
    axes[1].set(ylabel='Mapped cell area / 1,000 um2',title='Different block scopes; not whole-chip area')
    axes[1].tick_params(axis='x',labelrotation=12);fig2.tight_layout();fig2.savefig(fig/'controller_comparison.png',dpi=160);plt.close(fig2)
    native_path=work/'native_application/verification.json';native=json.loads(native_path.read_text()) if native_path.exists() else None
    hard=[]
    for name in ('digital_blocks/readout/hardening.json','met5_candidate/readout/hardening.json'):
        p=work/name
        if p.exists():hard.append(json.loads(p.read_text()))
    quant=app['models']['integer_mha'];floating=app['models']['float']
    lines=['# AutoMX-CIM priority implementation — 28 October 2026','',
        'Executed in env_mamba. The original successful notebook, source and reports are retained under `experiments/priority_20261028/baseline/`.','',
        '## Results acquired','',
        f"- UCI HAR: {app['test_windows']} test windows, nine subject-disjoint test users, six classes; accuracy {quant['accuracy']*100:.3f}%, macro-F1 {quant['macro_f1']*100:.3f}%.",
        f"- Float macro-F1 {floating['macro_f1']*100:.3f}%; quantized loss {(floating['macro_f1']-quant['macro_f1'])*100:.3f} percentage points. Model selected with validation subjects before test evaluation.",
        f"- All test outputs match the independent integer reference. Actual RTL MHA, binary mixed readout and serial ternary hardware baseline each checked {app['test_windows']} frames / {app['test_windows']*8} output values with zero mismatches.",
        f"- Decoder: {decoder['cases']} exhaustive real-RTL cases; binary search takes {decoder['binary_min_cycles']}-{decoder['binary_max_cycles']} clocks versus 38.",
        f"- Canonical integrated RTL latency at 25 MHz: {latency[0]['latency_us']:.2f} -> {latency[1]['latency_us']:.2f} us, {latency[0]['latency_us']/latency[1]['latency_us']:.3f}x speedup. This uses identical functional ADC response timing, not a concurrent transistor simulation.",
        f"- Mapped readout area: {mapped['linear_readout']:.3f} -> {mapped['binary_readout']:.3f} um2 ({(mapped['binary_readout']/mapped['linear_readout']-1)*100:+.3f}%).",
        f"- Fair digital baseline: {mapped['digital_projection']:.3f} um2 projector and {mapped['digital_attention']:.3f} um2 MHA-plus-projector; mean RTL latency {rtl['results'][-1]['latency_us_mean']:.3f} us. Digital is faster at this tiny configuration; no CIM efficiency advantage is asserted.",'',
        '## Application interpretation','',
        f"Linear-feature macro-F1 is {app['models']['linear_features']['macro_f1']*100:.3f}%. Retrained uniform attention is {app['models']['uniform_retrained']['macro_f1']*100:.3f}%; the small learned-attention gap must be judged with the paired subject interval, not described as a decisive improvement.",
        'Feature extraction, embedding and classification remain software. Only the two-token MHA datapath is the hardware candidate. Circuit-backed frames and the dataset-wide RTL/algorithm evaluation have distinct coverage.','',
        '## Analog interface finding','',
        'Forty native conversions over eight column/phase banks found decreasing raw ADC code with increasing signed sum, whereas the old functional fixture assumed increasing code. The conditioner-to-ADC differential pair was crossed in both the physical top source and the new native worker. New calibration and application measurements use that corrected wiring. Historical partition measurements retain their original orientation and remain separate experiments.','']
    if native:
        lines.extend([f"Native application status: **{native['status']}**; {native['logical_conversions']} logical conversions; {native['unique_native_jobs']} fresh unique simulator jobs including calibration; {native['partial_decode_mismatches']} partial decode errors.",
          f"Native frame output mismatches: {[f['output_mismatches'] for f in native['frames']]}. These are native SAR/transistor measurements followed by measured-code RTL replay, not full-chip transistor co-simulation.",''])
    else:lines.extend(['Native calibration/application campaign is running; no completed native application result is asserted yet.',''])
    for h in hard:lines.append(f"Readout physical candidate: {h.get('status')}; router DRC {h.get('routed_drc_violations')}; TT setup/hold {h.get('setup_slack_ns')}/{h.get('hold_slack_ns')} ns; source `{h.get('source')}`.")
    lines.extend(['','## Measurement sequence','',
       'The electrical/service chapter measures loaded physical pulses, timing-aligned six-frame native coverage, calibration transfer, clock-aware controller cost, resident-state operation and clean extraction. Its reports identify the stimulus and power boundary for each result.','',
       '## Reproduction','',
       'Source entry points: `automx_cim/application_har.py`, `scripts/verify_binary_decoder.py`, `scripts/verify_har_application_rtl.py`, `scripts/measure_priority_costs.py`, `scripts/portable_cim_sar.py`, `scripts/run_har_native.py`. Results/logs: `experiments/priority_20261028/`.',''])
    report=root/'docs/PRIORITY_IMPLEMENTATION_20261028.md';report.write_text('\n'.join(lines))
    print('PRIORITY_REPORT',report,flush=True)
    return {'report':str(report),'figures':str(fig),'paired_subject_comparison':paired}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True);a=p.parse_args();summarize(a.root,a.work)
