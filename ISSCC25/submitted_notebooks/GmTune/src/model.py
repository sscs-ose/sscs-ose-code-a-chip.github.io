import numpy as np
import torch.nn as nn

import src.netlist as nl 
import src.visualizing as vs

from scipy.stats import linregress
from scipy.integrate import simpson


class GmSpice(nn.Module):
    def __init__(
        self,
        VDD = 1.8,
        VCM = 1.3,
        WM1 = 12,
        WM3 = 10,
        WM4 = 40,
        VG_step = 0.02,
        linear_threshold = 0.99,
        spice_path = 'src/spice/',
        ckpt_path = 'ckpts/',
        verbose = False,
    ):
        super(GmSpice, self).__init__()
        self.VDD = VDD
        self.VCM = VCM
        self.WM1 = WM1
        self.WM3 = WM3
        self.WM4 = WM4
        self.VG_step = VG_step
        self.linear_threshold = linear_threshold
        self.spice_path = spice_path
        self.ckpt_path = ckpt_path
        self.verbose = verbose

        self.filepath = spice_path + "/GmCMFF.spice"
        nl.write_netlist(self.filepath)
        if verbose:
            print("Netlist file wroten at", self.filepath)

    def forward(self, VG_delta):
        VG_min = self.VCM - VG_delta
        VG_max = self.VCM + VG_delta
        VG = np.arange(VG_min, VG_max, self.VG_step)

        GMs = []
        BWs = []
        IRNs = []
        Ps = []
        for v in VG:
            netlist_para = np.array([self.VDD, v, self.VCM, self.WM4, self.WM4, self.WM1, self.WM3])
            nl.write_paras(tuple(netlist_para), self.spice_path)
            out, err = nl.run_netlist(self.filepath)
            if self.verbose:
                print(out.decode(), "\n")
            
            gmpath = self.ckpt_path + "/Gm.txt"
            gm_freq = np.loadtxt(gmpath, skiprows=1)
            gm = gm_freq[0, 1]
            bw_idx = np.argmin(np.abs(gm_freq[:, 1] - gm * 0.707))
            bw = gm_freq[bw_idx, 0]
            GMs.append(gm)
            BWs.append(bw)

            irnpath = self.ckpt_path + "/IRN.txt"
            irn_freq = np.loadtxt(irnpath, skiprows=1)
            irn_idx = np.argmin(np.abs(irn_freq[:, 0] - 5e7))
            irn = irn_freq[irn_idx, 1]
            IRNs.append(irn)

            ibpath = self.ckpt_path + "/IB.txt"
            ib = np.loadtxt(ibpath)[1]
            i1path = self.ckpt_path + "/I1.txt"
            i1 = np.loadtxt(i1path)[1]
            i2path = self.ckpt_path + "/I2.txt"
            i2 = np.loadtxt(i2path)[1]
            p = self.VDD * (ib + i1 + i2) * 2
            Ps.append(p)

        GMs = np.array(GMs)
        BWs = np.array(BWs)
        IRNs = np.array(IRNs)
        Ps = np.array(Ps)
        start, end = self._linear(VG, GMs)

        vg_region = VG[start:end + 1]
        gm_region = GMs[start:end + 1]
        bw_region = BWs[start:end + 1]
        irn_region = IRNs[start:end + 1]
        ps_region = Ps[start:end + 1]
        print("Best linear region of Vg: {:.3f} to {:.3f}".format(vg_region[0], vg_region[-1]))
        print("Best linear region of Gm: {:.5f} to {:.5f}".format(gm_region[0] * 1000, gm_region[-1] * 1000))

        vs.plot_metrics(VG, GMs, BWs, IRNs, Ps, start, end)
        metrics = self._metric(vg_region, gm_region, bw_region, irn_region, ps_region)

        return metrics
    
    def _linear(self, VG, GMs):
        best_region = None
        current_region = []

        for start in range(len(GMs)):
            for end in range(start + 2, len(GMs) + 1):
                x_region = VG[start:end]
                y_region = GMs[start:end]
                
                slope, intercept, r_value, p_value, std_err = linregress(x_region, y_region)
                
                if r_value**2 >= self.linear_threshold and slope > 0:
                    current_region = (start, end - 1)
                else:
                    break

            if best_region is None or (current_region[1] - current_region[0] > best_region[1] - best_region[0]):
                best_region = current_region
        
        return best_region
    
    def _metric(self, vg_region, gm_region, bw_region, irn_region, ps_region):
        # gm_score = 500 * (gm_region[-1] - gm_region[0]) * (vg_region[-1] - vg_region[0])
        vg_region = vg_region[-1] - vg_region[0]
        gm_region = (gm_region[-1] - gm_region[0]) * 1e3
        # power_score = simpson(ps_region, x=vg_region)
        power_max = (ps_region*1e3).max()
        bandwidth = (bw_region/1e9).max()
        input_noise = (irn_region*1e9).min()

        return vg_region, gm_region, power_max, bandwidth, input_noise