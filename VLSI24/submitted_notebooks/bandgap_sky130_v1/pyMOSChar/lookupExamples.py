"""
Copyright 2022 John William Kustin

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from lookupMOS import lum
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pdb

filename = 'sky130.mos.jupyterData.dat' 
lk = lum(filename)  
VGS = np.linspace(0, 1.8, endpoint=True)
matplotlib.rc('xtick',labelsize=15)
matplotlib.rc('ytick',labelsize=15)
types = ['nfet', 'pfet']
for idx in range(len(types)):
    typ = types[idx]
    widths = lk.mosDat[typ]['width']
    lengths = lk.mosDat[typ]['length']
    id = np.squeeze(lk.lookup(typ, 'id', l=[l for l in lengths], vds=1.8 ,vsb=0, vgs=VGS))
    gm = np.squeeze(lk.lookup(typ, 'gm', l=[l for l in lengths], vds=1.8,vsb=0, vgs=VGS))
    vt = np.squeeze(lk.lookup(typ, 'vt', l=[l for l in lengths], vds=1.8,vsb=0, vgs=VGS))
    fT = np.squeeze(lk.lookup(typ, 'gm/cgg', l=[l for l in lengths], vds=1.8, vgs=VGS)/2/np.pi)
    K = [id[i]/(VGS-vt[i])**2 * lengths[i] / widths[i] for i in range(len(lengths))] # = 1/2 * mu_n * C_ox
    K_norm = [K[i] / (lengths[i] / widths[i]) for i in range(len(lengths))]
    figK, axK = plt.subplots()
    axK.set_xlabel('Vov (V)')
    axK.set_ylabel('log10 (1/2 * mu_n * C_ox) / (L / W)')
    axK.set_title('{} Normalized square Law K term'.format(typ))
    indc = (VGS-vt) > 0.
    VGSmesh = np.array(np.meshgrid(VGS, lengths))
    for i, k in enumerate(K_norm):
        idxx = np.squeeze(indc[i])
        x_axis = np.squeeze(VGS[idxx]-vt[i][indc[i]])
        y_axis = np.squeeze(np.log10(k[indc[i]]))
        axK.plot(x_axis, y_axis, label=lengths[i])
    axK.legend()
    fig, ax1 = plt.subplots(3)

    ax1[0].set_xlabel('Vov (V)')
    ax1[0].set_ylabel('gm/Id (S/A)')
    ax1[0].set_title('{} Tradeoff: gm/Id vs. fT.'.format(typ))
    lns1 = []
    lns2 = []
    gmonid = [gm[j]/id[j] for j in range(len(lengths))]
    fom = [gmonid[i]*np.squeeze(fT[i])/1e9 for i in range(len(lengths))]
    for i, gmid in enumerate(gmonid):
        lns1.append(ax1[0].plot(np.squeeze(VGS-vt[i]), np.squeeze(gmid), 'o--', label=lengths[i]))
    ax1[0].legend()
    ax2 = ax1[0].twinx()
    ax2.set_ylabel('fT (GHz)')

    for i, f in enumerate(fT):
        lns2.append(ax2.plot(np.squeeze(VGS-vt[i]), np.squeeze(f)/1e9, '+--', label='fT'))

    ax1[0].grid(True)
    fig.tight_layout()
    for i, gi in enumerate(gmonid):
        ax1[1].plot(np.squeeze(gi), np.squeeze(gi)*np.squeeze(fT[i])/1e9, 'o--', label=lengths[i])
    ax1[1].legend()
    for i, gi in enumerate(gmonid):
        ax1[2].plot(np.squeeze(VGS-vt[i]), np.squeeze(gi)*np.squeeze(fT[i])/1e9, 'o--', label=lengths[i])
    ax1[2].legend()

    ax1[1].set_xlabel('gm/Id (S/A)')
    ax1[1].set_ylabel('gm/Id*fT (S/A * GHz)')
    ax1[1].set_title('{} Figure of Merit.'.format(typ))
    ax1[1].grid(True)
    ax1[2].set_xlabel('Vov (V)')
    ax1[2].set_ylabel('gm/Id*fT (S/A * GHz)')
    ax1[2].set_title('{} Figure of Merit.'.format(typ))
    ax1[2].grid(True)
    fig.suptitle(filename + ' W = 1um')
    fig, ax = plt.subplots()
    ax.set_xlabel('Vgs (V)')
    ax.set_ylabel('I (uA)')
    if typ == 'pfet':
        ax.set_xlabel('-Vgs (V)')
        ax.set_ylabel('-I (uA)')
        VGS = -VGS
    else:
        ax.set_xlabel('Vgs (V)')
        ax.set_ylabel('I (uA)')

    ax.set_title('{} Id vs. Vgs. W = 1um'.format(typ))
    for i,idd in enumerate(id) :
        ax.plot(np.squeeze(VGS), idd*1e6, label=f'{lengths[i]} um')
    ax.legend()
plt.show()

# print('sizing for amplifier circuit')
# filename = 'mosSKY130__W1000000.0u.sky130_fd_pr__nfet_01v8_lvt.sky130_fd_pr__pfet_01v8_lvt.moreLengths.dat'
# lk.init(filename)
# nlengths = lk.mosDat['nfet']['length']
# plengths = lk.mosDat['pfet']['length']
# print('Available PMOS Lenghts: {}'.format(plengths))
# print('Available NMOS Lenghts: {}'.format(nlengths))

# gain = 75e3
# gmn = 100e-6 
# gm_id = 10
# id = gmn/gm_id
# gdsn = lk.lookup('nfet','gds', vds=1.8/2, vgs=0.7,l=8e6)
# gdsp = lk.lookup('pfet','gds', vds=0.6, vgs=0.6,l=8e6)
# idn = lk.lookup('nfet','id', vds=1.8/2, vgs=0.7,l=8e6)
# idp = lk.lookup('pfet','id', vds=0.6, vgs=0.6,l=8e6)
# gmidn = lk.lookup('nfet', 'gm/id', vds=1.8/2, vgs=0.7,l=8e6)
# gmidp = lk.lookup('pfet', 'gm/id', vds=0.6, vgs=0.6,l=8e6)
# gmn = lk.lookup('nfet', 'gm', vds=1.8/2, vgs=0.7,l=8e6)
# gmp = lk.lookup('pfet', 'gm', vds=0.6, vgs=0.6,l=8e6)
# JDnmos = lk.lookup('nfet', 'id', vds=1.8/2, vgs=0.7,l=8e6)/width
# JDpmos = lk.lookup('pfet', 'id', vds=0.6, vgs=0.6,l=8e6)/width
# indcn = np.unravel_index(np.argmin(np.abs(gmidn - gm_id)), (gmidn - gm_id).shape)
# indcp = np.unravel_index(np.argmin(np.abs(gmidp - gm_id)), (gmidp - gm_id).shape)

# # ro1 = 1/gdsn.flatten()[indcn]
# ro1 = 1/gdsn
# # ro4 = 1/gdsp.flatten()[indcp]
# ro4 = 1/gdsp
# # possible_gain = gmn[indcn] * ro1[indcn] * ro4[indcp] / (ro1[indcn] + ro4[indcp]) * (2*gmp[indcp] * ro4[indcp] + 1) / (2*(gmp[indcp] * ro4[indcp] + 1))

# possible_gain = gmn * (ro1 * ro4 / (ro1 + ro4)) * ((2*gmp * ro4 + 1) / (2*(gmp * ro4 + 1)))
# lIndx, vgsIndx = np.unravel_index(np.argmin(np.abs(possible_gain - gain)),possible_gain.shape)
# assert lIndx != None and vgsIndx != None
# wnmos = id/JDnmos[indcn]
# lnmos = nlengths[indcn[0]]
# print('nmos: {} / {} um'.format(wnmos,lnmos/1e6))
# wpmos = id/JDpmos[indcp]
# lpmos = plengths[indcp[0]]
# print('pmos: {} / {} um'.format(wpmos,lpmos/1e6))
# idn = idn[indcn]
# idp = idp[indcp]

# gm_n = gmn[indcn]
# gm_p = gmp[indcp]

# # current mirror and source sizing
# opVout = 1.2307
# JDpmos = lk.lookup('pfet', 'id', vds=1.8/2, vgs=-(opVout - 1.8))/width
# wpmos = id/JDpmos
# print('pmos mirror: {} um'.format(wpmos))
# JDnmos = lk.lookup('nfet', 'id', vds=1.8/2, vgs=1.8/2)/width
# wnmos = id/JDnmos
# print('nmos mirror: {} um'.format(wnmos))
