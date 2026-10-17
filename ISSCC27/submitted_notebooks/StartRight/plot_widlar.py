import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pilot import OUT
from widlar_pilot import STUDY

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(11,7.3),layout='constrained')
a,b,c,d=axes.flat
for name,label,color in [('widlar_confirm_g1e-12_dir1','GMIN = 1 pS (default)','#cb6c24'),('widlar_confirm_g1e-15_dir1','GMIN = 1 fS','#1667a5')]:
    x=np.loadtxt(OUT/name/'return.dat',skiprows=1)
    select=x[:,0]<=.2
    a.plot(x[select,0],x[select,1]-x[select,0],label=label,color=color)
    b.plot(x[:,0],x[:,1],label=label,color=color)
x=np.loadtxt(OUT/'widlar_startup_return_w0.42'/'return.dat',skiprows=1)
b.plot(x[:,0],x[:,1],label='1 fS + startup NMOS',color='#258342')
a.axhline(0,color='black',lw=.8)
a.set(xlabel='Cut-gate voltage (V)',ylabel='Return voltage minus input (V)',title='A. Lower GMIN exposes two extra crossings')
a.legend(fontsize=8)
b.plot([0,1.8],[0,1.8],'k--',lw=.8,label='Return = input')
b.set(xlabel='Cut-gate voltage (V)',ylabel='Returned bias voltage (V)',title='B. Startup device changes the return curve')
b.legend(fontsize=8,loc='upper left')
for name,label,color in [('widlar_cold_ramp1e-06_startupNone_gmin1e-12','No startup, 1 pS','#cb6c24'),('widlar_numerical_gear_g1e-15_wNone','No startup, 1 fS','#1667a5'),('widlar_numerical_gear_g1e-15_w0.42','With startup, 1 fS','#258342')]:
    x=np.loadtxt(OUT/name/'cold.dat',skiprows=1)
    positive=x[:,0]>0
    c.semilogx(x[positive,0]*1e6,x[positive,2],label=label,color=color)
c.axhspan(1.16009189*.95,1.16009189*1.05,color='#258342',alpha=.12)
c.set(xlabel='Time from simulation start (µs)',ylabel='Bias node b (V)',title='C. Cold start from a zero supply, 1 µs ramp',xlim=(.05,50001),ylim=(-.02,1.45))
c.legend(fontsize=8,loc='lower left')
rows=json.loads((STUDY/'condition_screen.json').read_text())
corners=['tt','ff','ss','sf','fs'];temps=[-20,27,85]
counts=np.empty((5,3))
for i,corner in enumerate(corners):
    for j,temp in enumerate(temps):
        pair=[r for r in rows if r['corner']==corner and r['temperature_C']==temp]
        no=next(r for r in pair if r['startup_width_um'] is None)
        yes=next(r for r in pair if r['startup_width_um'] is not None)
        counts[i,j]=len(no['roots'])
        d.text(j,i,f'{len(no["roots"])}/{len(yes["roots"])}',ha='center',va='center',fontsize=12)
d.imshow(counts,cmap='Blues',vmin=0,vmax=5,aspect='auto')
d.set(xticks=range(3),xticklabels=[f'{t} °C' for t in temps],yticks=range(5),yticklabels=[s.upper() for s in corners],title='D. Candidate roots: unassisted / with startup',xlabel='Finite 2 mV scans at GMIN = 1 fS')
fig.suptitle('StartRight: simulator settings can hide a startup problem',fontsize=14)
fig.savefig(STUDY/'startup_evidence.png',dpi=160)
print(STUDY/'startup_evidence.png')

