#!/usr/bin/env python3
"""Publication figures computed from preserved measured evidence."""
from pathlib import Path
import json
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
plt.rcParams.update({'font.size':10,'svg.fonttype':'none','figure.dpi':150})


def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.svg',bbox_inches='tight')
    fig.savefig(ROOT/'figures'/f'{name}.png',bbox_inches='tight')
    plt.close(fig)


def operators():
    evidence=json.loads((ROOT/'results/operators-first/summary.json').read_text())
    assert evidence['passed'] and len(evidence['rows'])==21
    names=['DOT64','GEMM8','CONV3']
    fig,axes=plt.subplots(1,2,figsize=(10,3.6))
    for mode,offset,color,label in [('scalar',-.18,'#64748b','RV32I software multiply'),('xdot4',.18,'#087f8c','Xnebula (packing included)')]:
        groups=[[r['cycles'] for r in evidence['rows'] if r['workload']==name and r['mode']==mode] for name in names]
        axes[0].bar([i+offset for i in range(3)],[statistics.mean(g) for g in groups],width=.32,color=color,label=label)
        for i,g in enumerate(groups):axes[0].scatter([i+offset]*len(g),g,color='black',s=9,zorder=3)
    axes[0].set_yscale('log');axes[0].set_ylabel('Complete program cycles (log scale)')
    axes[0].set_xticks(range(3),names);axes[0].legend(fontsize=8)
    for i,name in enumerate(names):
        values=[r['speedup'] for r in evidence['speedups'] if r['workload']==name]
        axes[1].bar(i,statistics.mean(values),color='#087f8c',width=.55)
        axes[1].scatter([i]*len(values),values,color='black',s=14,zorder=3)
        axes[1].text(i,statistics.mean(values)+.2,f'{statistics.mean(values):.2f}×',ha='center')
    axes[1].set_ylabel('Scalar cycles / Xnebula cycles');axes[1].set_ylim(0,9)
    axes[1].set_xticks(range(3),names)
    fig.suptitle('Identical signed INT8 inputs; three memory-response seeds; exact retirement match')
    fig.tight_layout();save(fig,'operators')


def comparison():
    path=ROOT/'results/comparison/summary.json'
    if not path.exists():return
    evidence=json.loads(path.read_text())
    if not evidence['complete']:return
    fig,axes=plt.subplots(1,2,figsize=(9,3.5))
    for i,mode in enumerate(['direct','platform']):
        rows=[r for r in evidence['rows'] if r['mode']==mode]
        assert len(rows)==5
        axes[0].bar(i,sum(r['passed'] for r in rows),width=.55,color=('#64748b','#087f8c')[i])
        axes[1].scatter([i+(r['trial']-3)*.04 for r in rows],[r['elapsed_seconds'] for r in rows],s=35,color=('#64748b','#087f8c')[i])
    for ax in axes:ax.set_xticks([0,1],['Direct Codex','ChipWave'])
    axes[0].set_ylim(0,5.6);axes[0].set_ylabel('Trials passing the frozen final checker / 5')
    axes[1].set_ylabel('Model workflow + public checks (seconds)')
    fig.suptitle('Scoped NPU pilot: same model, contract, development tools and 600 s budget')
    fig.tight_layout();save(fig,'platform_comparison')


if __name__=='__main__':
    operators();comparison();print('EVIDENCE_FIGURES_RENDERED')
