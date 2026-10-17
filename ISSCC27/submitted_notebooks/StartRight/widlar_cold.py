import json
import numpy as np
from pilot import simulate
from widlar_pilot import STUDY
from widlar_confirm import setup


def cold_deck(ramp=1e-3,startup_width=None,gmin=1e-15,max_step=5e-5):
    stop=ramp+.05
    return 'Inverse-Widlar physical cold start from zero source\n'+setup(gmin,startup_width).replace('.option scale=1u','.option method=gear maxord=2 scale=1u')+f'''VDD vdd 0 PWL(0 0 1u 0 {ramp+1e-6} 1.8 {stop} 1.8)
.control
set wr_singlescale
set wr_vecnames
tran 1u {stop} 0 {max_step}
wrdata cold.dat v(a) v(b) v(c) i(VDD) v(vdd)
quit
.endc
.end
'''

if __name__=='__main__':
    rows=[]
    for ramp in [1e-6,.001,.1]:
        for width in [None,.42]:
            for g in [1e-12,1e-15]:
                name=f'widlar_cold_ramp{ramp}_startup{width}_gmin{g}'
                folder=simulate(name,cold_deck(ramp,width,g))
                d=np.loadtxt(folder/'cold.dat',skiprows=1)
                row={'name':name,'ramp_s':ramp,'startup_width_um':width,'gmin_S':g,'tstop_s':float(d[-1,0]),'final_b_V':float(d[-1,2]),'final_source_A':float(-d[-1,4]),'final_vdd_V':float(d[-1,5])}
                rows.append(row);print(json.dumps(row),flush=True)
                (STUDY/'cold_start.json').write_text(json.dumps(rows,indent=2))
