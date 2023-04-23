import sys
#import spice3read as s3r
import numpy as np
import pyMOSChar.spice3read as s3r
from pathlib import Path

result_path = Path("/headless/sim_results/dc_op")
opdat = s3r.read(str(result_path/ 'dc_op.out'))

gms = [entry for entry in opdat.keys() if '[gm]' in entry]
ids = [entry for entry in opdat.keys() if '[id]' in entry]
ids.remove('i(@m.xm10.msky130_fd_pr__nfet_01v8_lvt[id])')
gms.sort()
ids.sort()
vdsats = []
for i, x in enumerate(gms):
    gm = opdat[x]
    id = opdat[ids[i]]
    vdsats.append(2/(gm/id))


indx = range(1,10)
indx.insert(1,13)
vdsats = np.asarray(vdsats).flatten()
print('vdsats')
for i, n in enumerate(indx):
    print('vdsat{} = {}'.format(n,vdsats[i]))

vdd = opdat['v(vdd)']
va = opdat['v(va)']
vb = opdat['v(vb)']
vbg = opdat['v(vbg)']
vgate = opdat['v(vgate)']
vq = opdat['v(vq)']
vx = opdat['v(vx)']
vg = opdat['v(vg)']
vdsmargin1 = vdd - va - vdsats[0]
vdsmargin13 = vdd - vx - vdsats[1]
vdsmargin2 = vdd - vb - vdsats[2]
vdsmargin3 = vdd - vbg - vdsats[3]
vdsmargin4 = vdd - vgate - vdsats[4]
vdsmargin5 = vgate - vq- vdsats[5]
vdsmargin6 = vq - vdsats[6]
vdsmargin7 = vx - vdsats[7]
vdsmargin8 = vdd - vg - vdsats[8]
vdsmargin9 = vg - vq - vdsats[9]


vdsmargins = np.asarray([
    vdsmargin1,
    vdsmargin13,
    vdsmargin2,
    vdsmargin3,
    vdsmargin4,
    vdsmargin5,
    vdsmargin6,
    vdsmargin7,
    vdsmargin8,
    vdsmargin9
]).flatten()
print('vdsmargins')

for i, n in enumerate(indx):
    print('vds{}margin = {}'.format(n,vdsmargins[i]))

if np.all(vdsmargins > 0):
    print('All Vds margins are positive')
    print('The lowest Vds margin is {}'.format(np.min(vdsmargins)))
else:
    print('Vds margins are violated. Most violated is {}'.format(np.min(vdsmargins)))
    