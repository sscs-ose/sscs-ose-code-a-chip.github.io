"""Show audited intact reference-controller histories with fixed voltage axes.
SPDX-License-Identifier: Apache-2.0
"""
import matplotlib.pyplot as plt
from reference_evidence import load_vectors

def show(record):
    fig,axes=plt.subplots(3,3,figsize=(12,7.5),sharex='col',constrained_layout=True)
    colors={'original':'#777777','digital_guard':'#bd6500','reference_supervisor':'#155d9c'}
    labels={'original':'Published POR','digital_guard':'POR + nine-MOS guard','reference_supervisor':'Reference supervisor'}
    columns=[('primary','cold_shallow','-40 C: only the reference controller\nestablishes Q=1 before resetting',20.9,29.2),
        ('primary','hot_shallow','125 C: 1.35 V reset dip\nReference controller restores Q=0',24.8,29.2),
        ('trough','hot_storage','125 C: benign 1.62 V trough\nAll three preserve Q=1',24.8,29.2)]
    for col,(group,case,title,lo,hi) in enumerate(columns):
        for variant in colors:
            row=next(r for r in record['cases'] if r['kind']=='application' and r['case']==case and r['variant']==variant
                     and (r['id'].startswith('primary/') if group=='primary' else r.get('group')=='trough'))
            d=load_vectors(row);t=d[:,0]*1000;mask=(t>=lo)&(t<=hi)
            for ax,index in zip(axes[:,col],(3,2,1)):
                ax.plot(t[mask],d[mask,index],color=colors[variant],label=labels[variant],ls='--' if variant=='digital_guard' else '-',lw=1.2)
        axes[0,col].set_title(title,fontsize=10)
        for ax in axes[:,col]:ax.set_xlim(lo,hi);ax.set_ylim(-.1,2.0);ax.grid(alpha=.2)
        axes[2,col].set_xlabel('Time (ms)')
    for ax,label in zip(axes[:,0],('DVDD (V)','Consumer reset-bar (V)','Q (V)')):ax.set_ylabel(label)
    axes[0,0].legend(fontsize=7,loc='lower left')
    fig.suptitle('Saved Windows model data: verify the prior state before judging recovery\nTT schematic samples, 2 us maximum step; the reference/comparator use the existing 3.3 V rail',fontsize=12)
    return fig
