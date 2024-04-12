import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import torchvision.transforms as vtransforms

import src.models as mdl
import src.utils.netlist as nl


class DSF_SpiceAC(nn.Module):
    def __init__(
        self,
        n_filter,
        sample_rate,
        netlist_dict,
        netlist_para,
        spice_path,
    ):
        super(DSF_SpiceAC, self).__init__()
        self.n_filter = n_filter
        self.sample_rate = sample_rate
        self.spice_path = spice_path

        print("Writing", spice_path + "/para.spice\n")
        nl.write_paras(netlist_para, spice_path)
        for i in range(self.n_filter):
            filepath = spice_path + "/DSF_BPF_ch%d.spice" % (i + 1)
            nl.write_netlist_AC(netlist_dict[i], filepath)
            print("Running simulation on DSF_BPF_ch%d netlist" % (i + 1))
            out, err = nl.run_netlist(filepath)
            print(out.decode(), "\n")

        n_freqs = self.sample_rate // 2 + 1
        fb = self._fresponse(n_freqs)
        self.register_buffer("fb", fb)

    def forward(self, waveform):
        assert (
            waveform.shape[-1] == self.sample_rate
        ), "Input waveform should be of length sample rate"

        waveform_fft = torch.fft.rfft(waveform, dim=-1)
        filtered_fft = self.fb * waveform_fft
        filtered_waveform = torch.fft.irfft(filtered_fft, dim=-1)
        return filtered_waveform

    def _fresponse(self, n_freqs):
        freqs = []
        gains = []
        for i in range(self.n_filter):
            filepath = self.spice_path + "/DSF_BPF_AC%d.txt" % (i + 1)
            data = np.loadtxt(filepath, skiprows=1)
            freqs.append(data[:, 0])
            gains.append(10 ** (data[:, 1] / 20))
        freqs = np.vstack(freqs)
        gains = np.vstack(gains)
        norm_gains = (gains - np.min(gains)) / (np.max(gains) - np.min(gains))

        if not (self.n_filter == freqs.shape[0] == gains.shape[0]):
            raise ValueError(
                "n_filter must be equal to the number of rows in the filter filte."
            )

        fb = np.zeros((self.n_filter, n_freqs))
        for i in range(self.n_filter):
            f_min = int(freqs[i][0] * n_freqs / np.max(freqs))
            f_max = int(freqs[i][-1] * n_freqs / np.max(freqs))
            fpts = f_max - f_min

            inter_freq = np.interp(
                np.linspace(freqs[i][0], freqs[i][-1], fpts),
                freqs[i],
                norm_gains[i],
            )

            fb[i] = np.pad(inter_freq, (f_min, n_freqs - f_max))

        return torch.from_numpy(fb).float()


class LAFE_Spice_v1(nn.Module):
    def __init__(
        self,
        n_filter,
        sample_rate,
        netlist_dict,
        netlist_para,
        spice_path,
        config_path,
        hop_length,
        overlap,
        max_sample_len,
        backbone,
    ):
        super(LAFE_Spice_v1, self).__init__()
        self.n_filter = n_filter
        self.sample_rate = sample_rate
        self.netlist_dict = netlist_dict
        self.netlist_para = netlist_para
        self.spice_path = spice_path
        self.config_path = config_path
        self.hop_length = hop_length
        self.overlap = overlap
        self.max_sample_len = max_sample_len
        self.backbone = backbone

        self.bpf = DSF_SpiceAC(
            n_filter=self.n_filter,
            sample_rate=self.sample_rate,
            netlist_dict=self.netlist_dict,
            netlist_para=self.netlist_para,
            spice_path=self.spice_path,
        )
        self.spk = mdl.IAF_Spec(
            n_neuron=self.n_filter,
            hop_length=self.hop_length,
            config_path=self.config_path,
            overlap=self.overlap,
        )
        self.crop = vtransforms.RandomCrop(
            size=(self.n_filter, self.max_sample_len),
            pad_if_needed=True,
            padding=0,
        )

    def forward(self, waveform):
        out = self.bpf(waveform)
        out = self.spk(out)
        out = self.crop(out)
        out = self.backbone(out)
        return out


class DSF_SpiceTrans(nn.Module):
    def __init__(
        self,
        n_filter,
        netlist_dict,
        netlist_para,
        spice_path,
    ):
        super(DSF_SpiceTrans, self).__init__()
        self.n_filter = n_filter
        self.spice_path = spice_path
        self.time_steps = torch.linspace(0, 1, 20000)

        print("Writing", spice_path + "/para.spice\n")
        nl.write_paras(netlist_para, spice_path)
        for i in range(self.n_filter):
            print("Writing", spice_path + "/DSF_BPF_ch%d.spice" % (i + 1))
            filepath = spice_path + "/DSF_BPF_ch%d.spice" % (i + 1)
            nl.write_netlist_Trans(netlist_dict[i], filepath)

    def forward(self, waveform):
        filtered_waveform = []
        count = waveform.shape[0]
        for i in range(count):
            print("Running trans simulation for waveform %d" % (i + 1))
            wf = waveform[i].detach().cpu().numpy()
            filtered_wf = self._trans(wf)
            filtered_waveform.append(filtered_wf)
        filtered_waveform = torch.stack(filtered_waveform).to(waveform.device)
        return filtered_waveform

    def _trans(self, wf):
        wf = wf / 100
        data = {"time": self.time_steps, "amplitude": wf[0]}
        df = pd.DataFrame(data)
        df.to_csv(self.spice_path + "/input_voltage.txt", sep=" ", index=False)
        for i in range(self.n_filter):
            filepath = self.spice_path + "/DSF_BPF_ch%d.spice" % (i + 1)
            print("Running simulation on DSF_BPF_ch%d netlist" % (i + 1))
            out, err = nl.run_netlist(filepath)
            print(out.decode(), "\n")

        filtered_wf = []
        for i in range(self.n_filter):
            path = self.spice_path + "/DSF_BPF_Trans%d.txt" % (i + 1)
            data = np.loadtxt(path, skiprows=1)
            filtered_wf.append(data[:, 1])
        filtered_wf = np.vstack(filtered_wf) * 100
        return torch.tensor(filtered_wf, dtype=torch.float32)


class LAFE_Spice_v2(nn.Module):
    def __init__(
        self,
        n_filter,
        netlist_dict,
        netlist_para,
        spice_path,
        config_path,
        hop_length,
        overlap,
        max_sample_len,
        backbone,
    ):
        super(LAFE_Spice_v2, self).__init__()
        self.n_filter = n_filter
        self.netlist_dict = netlist_dict
        self.netlist_para = netlist_para
        self.spice_path = spice_path
        self.config_path = config_path
        self.hop_length = hop_length
        self.overlap = overlap
        self.max_sample_len = max_sample_len
        self.backbone = backbone

        self.bpf = DSF_SpiceTrans(
            n_filter=self.n_filter,
            netlist_dict=self.netlist_dict,
            netlist_para=self.netlist_para,
            spice_path=self.spice_path,
        )
        self.spk = mdl.IAF_Spec(
            n_neuron=self.n_filter,
            hop_length=self.hop_length,
            config_path=self.config_path,
            overlap=self.overlap,
        )
        self.crop = vtransforms.RandomCrop(
            size=(self.n_filter, self.max_sample_len),
            pad_if_needed=True,
            padding=0,
        )

    def forward(self, waveform, spk=False):
        out = self.bpf(waveform)
        spks = self.spk(out)
        out = self.crop(spks)
        out = self.backbone(out)
        if spk:
            return out, spks
        return out
