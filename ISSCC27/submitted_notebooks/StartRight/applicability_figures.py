"""Contrast valid storage, blocked prior writing and an exercised reset miss.
SPDX-License-Identifier: Apache-2.0
"""
import matplotlib.pyplot as plt
from applicability_evidence import load_vectors

def show(record):
    fig,axes=plt.subplots(3,3,figsize=(12,7.5),sharex='col')
    columns=[('ripple','triangle','27 C: benign supply variation\nStorage passes',24.8,29.2),
             ('temperature','cold_storage','-40 C: cold release fails\nPrior Q=1 is never established',0,48.001),
             ('temperature','hot_shallow_reset','125 C: prior Q=1 verified\nShallow reset misses',24.8,29.2)]
    for col,(group,history,title,lo,hi) in enumerate(columns):
        for variant,color,label in [('original','#b36b00','Original POR'),('digital_guard','#176b55','POR + guard')]:
            row=next(r for r in record['cases'] if r['group']==group and r['history']==history and r['variant']==variant)
            d=load_vectors(row);t=d[:,0]*1000;mask=(t>=lo)&(t<=hi)
            for ax,index in zip(axes[:,col],[3,2,1]):
                ax.plot(t[mask],d[mask,index],color=color,label=label,lw=1.3);ax.set_ylim(-.1,2.05);ax.set_xlim(lo,hi);ax.grid(alpha=.2)
        axes[0,col].set_title(title,fontsize=10);axes[2,col].set_xlabel('Time (ms)')
    for ax,label in zip(axes[:,0],['DVDD (V)','Consumer reset-bar (V)','Q (V)']):ax.set_ylabel(label)
    axes[0,0].legend(fontsize=8);fig.suptitle('Saved Windows model data: qualification depends on the requested history',fontsize=12)
    fig.text(.06,.025,'TT models at listed temperatures, 2 us maximum step. Complete acquisition, valid prior state and functional success are distinct.',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,.94));return fig
