"""Figures from declared raw acquisitions, with evidence kind kept visible.
SPDX-License-Identifier: Apache-2.0
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


LABELS = {'frozen_rc_sr': 'RC', 'detector_10M_sr': 'Supply sensing', 'rc_mos_discharge_sr': 'RC + MOS discharge'}
COLORS = {'frozen_rc_sr': '#555555', 'detector_10M_sr': '#0072B2', 'rc_mos_discharge_sr': '#D55E00'}


def connections():
    fig, ax = plt.subplots(figsize=(11, 4.8)); ax.set(xlim=(0, 11), ylim=(0, 5)); ax.axis('off')
    def box(x, y, w, h, text, color='#edf4f8'):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.12',facecolor=color,edgecolor='#667788'))
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=10)
    def arrow(a,b,label=None):
        ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=1.6,color='#334455'))
        if label:ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.12,label,ha='center',fontsize=9)
    box(.2,3.1,2.5,1.25,'Reset network\nRC or supply-sensitive\noutput c, active low')
    box(4.6,3.1,2.6,1.2,'b = NAND(a, c)\nSKY130 MOS')
    box(4.6,.7,2.6,1.2,'a = NAND(b, set_n)\nSKY130 MOS')
    box(8.4,3.1,2.1,1.2,'Same output load\n100 kohm / MOS\n100 fF')
    arrow((2.85,3.7),(4.4,3.7),'c');arrow((7.35,3.7),(8.25,3.7),'b')
    ax.plot([7.4,7.7,7.7,4.0,4.0],[3.4,3.4,2.6,2.6,1.4],color='#334455')
    arrow((4.,1.4),(4.4,1.4),'b')
    ax.plot([7.4,8.,8.,3.5,3.5],[1.2,1.2,2.3,2.3,3.3],color='#334455')
    arrow((3.5,3.3),(4.4,3.3),'a')
    arrow((1.2,1.2),(4.4,1.2),'set_n through 1 kohm')
    ax.text(.2,4.85,'A normal input can establish the other state before the same supply cycle',fontsize=13,weight='bold')
    ax.text(.2,.05,'Logic view of the transistor deck. Desired reset: a = 0, b = 1. Normal SET_A: a = 1, b = 0.\nNAND c is a logic input; this load has no direct reset-injection PMOS.',fontsize=10)
    fig.tight_layout();return fig


def comparison(retained, commanded):
    fig, axes = plt.subplots(3,2,figsize=(11,8),sharex=True,sharey='row',layout='constrained')
    for column, record in enumerate([retained,commanded]):
        for row in record['cases']:
            if row['status'] != 'measured':continue
            raw = __import__('pathlib').Path(record['output_dir'])/'raw'/row['case']
            d = np.loadtxt(raw/'cold.dat',skiprows=1); f = np.loadtxt(raw/'interface.dat',skiprows=1)
            key = row['configuration']['id']; color = COLORS[key]
            axes[1,column].plot(d[:,0]*1e3,d[:,3],color=color,label=LABELS[key])
            axes[2,column].plot(d[:,0]*1e3,d[:,2],color=color,label=LABELS[key])
        axes[0,column].plot(f[:,0]*1e3,f[:,1],color='black',label='VDD')
        axes[0,column].plot(f[:,0]*1e3,f[:,2],color='#CC79A7',ls='--',label='set_n')
        axes[0,column].set_title('Retain intended state' if column==0 else 'Normal command writes the other state')
        for ax in axes[:,column]:
            ax.grid(alpha=.2);ax.set_ylim(-.12,2.05);ax.legend(fontsize=8,loc='center right')
        axes[2,column].set_xlabel('Time (ms)')
    axes[0,0].set_ylabel('Supply / input (V)');axes[1,0].set_ylabel('Reset input c (V)');axes[2,0].set_ylabel('Latch output b (V)')
    fig.suptitle(f"Fresh SPICE: {commanded['scenario']['corner'].upper()}, 27 C, 1.8 V; ideal R/C, 1 kohm input driver",fontsize=12)
    return fig


def print_results(record):
    print('Circuit | State/timing passed | Prior state checked | Other state tested | Restoration observed')
    for r in record['cases']:
        print(' | '.join(str(x) for x in [LABELS[r['configuration']['id']],r['observed_pass'],r.get('declared_precondition_verified'),r.get('alternate_state_exercised'),r.get('sampled_restoration_observed')]))
