"""Compare declared return curves and normalized cold starts across circuits."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pilot import HERE,OUT


def main():
    destination=HERE/'results/reuse'
    saved=json.loads((destination/'family_checks.json').read_text())
    assert saved['status']=='passed'
    fig,axes=plt.subplots(1,2,figsize=(11.5,4.5),layout='constrained')
    selected=[saved['original_circuit_regressions'][1],saved['original_circuit_regressions'][2]]
    selected += [next(r for r in saved['cases'] if r['circuit']==name and r['parameters']['gmin_S']==1e-15 and r['parameters']['load_resistance_ohm']==1e5 and r['parameters']['ramp_s']==1e-6) for name in ['beta_multiplier','resistor_biased_mirror']]
    labels=['Inverse-Widlar, unassisted','Inverse-Widlar, assisted','Beta multiplier, unassisted','Resistor-biased mirror']
    colors=['#aa4936','#174d86','#258355','#8b5a9b']
    for report,label,color in zip(selected,labels,colors):
        d=np.loadtxt(OUT/report['return_scans'][0]['case']/'return.dat',skiprows=1)
        axes[0].plot(d[:,0],d[:,1],label=label,color=color)
        roots=report['candidate_operating_points']
        axes[0].scatter([r['vin_V'] for r in roots],[r['vin_V'] for r in roots],s=24,color=color,zorder=4)
        d=np.loadtxt(OUT/report['loaded_test']['case']/'cold.dat',skiprows=1)
        axes[1].plot(d[:,0]*1e6,d[:,7]/report['loaded_test']['nominal_target_A'],label=label,color=color)
    axes[0].plot([0,1.8],[0,1.8],color='black',ls='--',lw=1,label='F(v) = v')
    axes[0].set(xlabel='Cut-gate input (V)',ylabel='Returned bias F(v) (V)',xlim=(0,1.8),ylim=(0,1.8),title='Same verification flow, different circuit behavior')
    axes[0].legend(fontsize=8,loc='upper left')
    axes[1].axhspan(.95,1.05,color='gray',alpha=.15,label='5% target band')
    axes[1].set(xlabel='Time from simulation start (µs)',ylabel='Output current / own intended target',xlim=(0,50),ylim=(-.03,1.15),title='Cold starts with the same 1 µs supply ramp')
    axes[1].legend(fontsize=8,loc='lower right')
    for ax in axes:ax.grid(alpha=.2)
    fig.supxlabel('TT, 27 °C, 1.8 V, GMIN = 1 fS. Current traces use a 100 kΩ load. Readiness also requires voltage/compliance and hold time.',fontsize=9)
    fig.savefig(destination/'reuse_evidence.png',dpi=180)
    print(destination/'reuse_evidence.png')

if __name__=='__main__':main()
