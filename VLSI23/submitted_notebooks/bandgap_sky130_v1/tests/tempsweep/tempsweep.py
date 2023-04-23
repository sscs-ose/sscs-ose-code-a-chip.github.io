import sys
sys.path.append('../pyMOSChar')
import spice3read as s3r
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc

rc('text', usetex=True)
rc('font', family='serif')

data = s3r.read('../sims/tsmc_bandgap_real_tempsweep.raw')
vbg = data['v(vbg)'][0]
temp = data['temp-sweep'][0]
vbg0 = np.interp(0, temp, vbg)
vbg27 = np.interp(27, temp, vbg)
vbg70 = np.interp(70, temp, vbg)
ppm = (vbg70-vbg0)/vbg27/70*1e6
fig, ax = plt.subplots()
ax.plot(temp, vbg)
ax.plot(0, vbg0, '-bo', label='{} mV'.format(np.around(vbg0*1e3,3)))
ax.plot(27, vbg27, '-ro', label='{} mV'.format(np.around(vbg27*1e3,3)))
ax.plot(70, vbg70, '-yo', label='{} mV'.format(np.around(vbg70*1e3, )))
ax.grid()
ax.set_title('DC Temperature Sweep. Vref = {} mV. ppm = {}'.format(np.around(vbg27*1e3, 3), np.around(ppm, 3)))
ax.set_xlabel("Temperature $^\circ$C")
ax.set_ylabel('Vout (V)')
ax.legend()
plt.show()