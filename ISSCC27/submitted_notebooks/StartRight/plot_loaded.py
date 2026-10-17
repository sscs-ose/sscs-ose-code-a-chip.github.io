from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pilot import OUT
from loaded_startup import LOAD_STUDY

m=json.loads((LOAD_STUDY/'measured_results.json').read_text())
fig,ax=plt.subplots(1,2,figsize=(10,3.9),layout='constrained')
for w,label,color in [(None,'No startup','#777777'),(.42,'Startup W = 0.42 µm','#1667a5'),(1.0,'Startup W = 1 µm','#b54a25')]:
    name=f'loaded_cold_r100000.0_w{w}_ramp1e-06'
    if w is not None:name=f'loaded_refined_w{w}_ramp1e-06'
    d=np.loadtxt(OUT/name/'cold.dat',skiprows=1)
    mask=d[:,0]>0
    ax[0].semilogx(d[mask,0]*1e6,d[mask,7]*1e6,label=label,color=color)
target=m['contract']['target_A']*1e6
ax[0].axhspan(target*.95,target*1.05,color='green',alpha=.1)
ax[0].set(xlim=(.1,200),ylim=(-.02,.95),xlabel='Time from simulation start (µs)',ylabel='Useful output current (µA)',title='Fast ramp: both startup sizes work')
ax[0].legend(fontsize=8,loc='upper left')
slow=[next(r for r in m['refined'] if r['width_um']==w and r['ramp_s']==.001) for w in [.42,1.0]]
ax[1].bar(['0.42 µm','1 µm'],[r['source_energy_to_ready_J']*1e9 for r in slow],color=['#1667a5','#b54a25'],width=.5)
for i,r in enumerate(slow):ax[1].text(i,r['source_energy_to_ready_J']*1e9+.12,f'{r["source_energy_to_ready_J"]*1e9:.2f} nJ',ha='center')
ax[1].set(ylim=(0,10),xlabel='Startup NMOS width (L = 1 µm)',ylabel='Net source work to readiness (nJ)',title='1 ms ramp: larger device uses more energy')
fig.suptitle('Loaded SKY130 example: about 0.773 µA into a 100 kΩ load',fontsize=12)
fig.savefig(LOAD_STUDY/'loaded_tradeoff.png',dpi=160)
print(LOAD_STUDY/'loaded_tradeoff.png')
