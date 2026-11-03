#!/usr/bin/env python3
"""Plot every physical variant from published raw-report-derived measurements."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def plot():
    path=ROOT/'results/ppa/summary.json'
    data=json.loads(path.read_text())
    assert data['complete'] and data['passed']
    rows=data['rows'];labels=[str(r['initial_core_utilization_percent'])+'% initial utilization'+
        ('\n10% repair margins' if r.get('repair_margins_percent') else '') for r in rows]
    fig,axes=plt.subplots(2,2,figsize=(10,7))
    for ax,(metric,scale,title,precision) in zip(axes.flat,[
        ('die_area_um2',1e-6,'Core footprint (mm²)',4),
        ('placed_instance_area_um2',1e-6,'Standard-cell instance area (mm²)',4),
        ('estimated_total_power_w',1000,'Tool-estimated core power (mW)',3),
        ('estimated_fmax_hz',1e-6,'STA-estimated Fmax (MHz)',2)]):
        for i,r in enumerate(rows):
            if r['metrics'] is None:
                ax.text(i,0.04,'N/A',ha='center',transform=ax.get_xaxis_transform());continue
            value=r['metrics'][metric]*scale
            color='#64748b' if i==0 else '#087f8c'
            ax.bar(i,value,color=color if r['qualified'] else '#b45309',
                   hatch=None if r['qualified'] else '//',width=.6)
            ax.annotate(f'{value:.{precision}f}',(i,value),xytext=(0,4),textcoords='offset points',ha='center')
        ax.set_xticks(range(len(rows)),[label.replace(' initial utilization',' initial\nutilization') for label in labels],fontsize=8);ax.set_ylabel(title)
        ax.set_ylim(bottom=0);ax.margins(y=.16)
    fig.suptitle('Same RTL and 100 ns constraints; Sky130HD TT / 25 °C / 1.8 V\nAll scheduled variants; power and Fmax are estimates')
    fig.tight_layout()
    for suffix in ('png','svg'):fig.savefig(ROOT/'figures'/('ppa_comparison.'+suffix),dpi=160,bbox_inches='tight')
    plt.close(fig)
    print('PPA_COMPARISON_FIGURE_RENDERED')


if __name__=='__main__':plot()
