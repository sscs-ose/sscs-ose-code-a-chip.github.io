"""Matched saved recovery histories with fixed voltage axes.
SPDX-License-Identifier: Apache-2.0
"""
import matplotlib.pyplot as plt
from guard_evidence import load_vectors

def show(record):
    fig,axes=plt.subplots(3,2,figsize=(10,7))
    for col,condition in enumerate(['short_zero','slow_zero']):
        for variant,color,label in [('original','#b36b00','Original POR'),('digital_guard','#176b55','POR + digital guard')]:
            row=next(r for r in record['cases'] if r['group']=='challenge' and r['condition']==condition and r['variant']==variant)
            d=load_vectors(row);scale=1e6 if col==0 else 1e3;x=(d[:,0]-.025)*scale;lo,hi=(-2,25) if col==0 else (-1,24);mask=(x>=lo)&(x<=hi)
            for ax,index in zip(axes[:,col],[3,2,1]):ax.plot(x[mask],d[mask,index],color=color,label=label,lw=1.2);ax.set_ylim(-.1,1.95);ax.set_xlim(lo,hi);ax.grid(alpha=.2)
        axes[0,col].set_title('2 us zero hold, 10 us recovery' if col==0 else '1 ms zero hold, 10 ms recovery')
        axes[2,col].set_xlabel('Time from event start ('+('us' if col==0 else 'ms')+')')
    for ax,label in zip(axes[:,0],['DVDD (V)','Consumer reset-bar (V)','Q (V)']):ax.set_ylabel(label)
    axes[0,0].legend(fontsize=8);fig.suptitle('Saved model data: compare short and slow recovery histories',fontsize=12)
    fig.text(.07,.025,'Primary 2 us maximum step. TT, 27 C schematic study; added passives ideal, default diffusion geometry, gate tunnelling off.',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,.95));return fig
