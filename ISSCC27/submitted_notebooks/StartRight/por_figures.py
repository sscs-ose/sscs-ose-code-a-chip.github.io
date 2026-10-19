"""Show audited equal-fraction reset-IP comparisons.
SPDX-License-Identifier: Apache-2.0
"""
import matplotlib.pyplot as plt
from por_evidence import load_vectors


def show(record):
    fig,axes=plt.subplots(4,1,figsize=(10.5,8),sharex=True)
    cases=[('common_domain_absolute','analog','#0077bb','AVDD: 3.3 to 0 V; DVDD stays 1.8 V'),('fraction_controls','digital_zero','#dd7722','DVDD: 1.8 to 0 V; AVDD stays 3.3 V')]
    for group,event,color,label in cases:
        row=next(r for r in record['cases'] if r['group']==group and r['domain']==event and r['command'] and r['solver']=='sparse');d=load_vectors(row)
        for ax,col in zip(axes,[11,3,2,1]):ax.plot(d[:,0]*1e3,d[:,col],color=color,label=label,lw=1.6)
    for ax,label in zip(axes,['Analog supply (V)','Digital supply (V)','Reset-bar output (V)','Stored Q (V)']):
        ax.set_ylabel(label);ax.grid(alpha=.18);ax.axvspan(25,28.001,color='grey',alpha=.07)
    axes[0].legend(loc='lower left');axes[0].set_ylim(-.15,3.6)
    for ax in axes[1:]:ax.set_ylim(-.1,2.05)
    axes[-1].axhspan(0,.36,color='#009988',alpha=.1);axes[-1].annotate('Required reset value: Q = 0',xy=(44,.05),xytext=(32,.45),arrowprops=dict(arrowstyle='->',color='#0077bb'),color='#0077bb')
    axes[-1].annotate('Normal clock/data writes Q = 1',xy=(21.01,1.75),xytext=(5,1.1),arrowprops=dict(arrowstyle='->',color='#555555'),fontsize=10)
    axes[-1].set_xlabel('Time (ms)');axes[-1].set_xlim(0,48.1)
    fig.suptitle('Saved model data: a finite zero-volt interval can retain stored state\nPublished dual-rail POR with SKY130 DFF; TT, 27 C, sparse/Gear',fontsize=12)
    fig.text(.5,.012,'GMIN 1e-15 S, RELTOL 1e-6, ABSTOL 1e-14 A, VNTOL 1e-6 V, max step 2 us.\nChanged rail at zero for 1 ms; model gate leakage disabled. No upstream defect or hardware retention claim.',ha='center',fontsize=8,va='bottom')
    fig.tight_layout(rect=[0,.06,1,.935]);return fig
