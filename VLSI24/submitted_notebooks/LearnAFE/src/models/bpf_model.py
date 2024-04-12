import torch
import torch.nn as nn


class DSF_Filtering(nn.Module):
    def __init__(
        self,
        n_filter,
        sample_rate,
        config_path,
        f_min=0,
        f_max=None,
        freeze=False,
    ):
        super(DSF_Filtering, self).__init__()
        self.n_filter = n_filter
        self.config_path = config_path
        self.f_min = f_min
        self.f_max = f_max if f_max else sample_rate // 2
        self.freeze = freeze
        
        afe_config = {}
        path = 'AFE_Config/Design/' + self.config_path + '.txt'
        with open(path, 'r') as file:
            for line in file:
                name, value = line.strip().split('\t')
                afe_config[name] = float(value)
        gm1 = torch.tensor(afe_config['I2']) / 0.059
        Ir = torch.tensor(afe_config['I1'] / afe_config['I2'])
        
        power = torch.arange(0, self.n_filter)
        gm1 = gm1 * torch.tensor(afe_config['scale']).pow(power)
        self.register_buffer('gm1', gm1)
        self.Ir = nn.Parameter(torch.full((self.n_filter, ), Ir), requires_grad=not self.freeze)

        C1 = torch.tensor(afe_config['C1_W']**2 * 2e-3 + afe_config['C1_W'] * 0.76e-3)
        self.register_buffer('C1', torch.full((self.n_filter, ), C1))
        C2 = torch.tensor(afe_config['C2_W']**2 * 2e-3 + afe_config['C2_W'] * 0.76e-3)
        self.Cr = nn.Parameter(torch.full((self.n_filter, ), C2/C1), requires_grad=not self.freeze)

    def forward(self, waveform):
        n_freqs = waveform.shape[-1] // 2 + 1
        f = torch.linspace(self.f_min, self.f_max, n_freqs)
        w = f * torch.tensor(2*torch.pi*1j, dtype=torch.complex64)
        self.w = w.to(waveform.device)

        Ir = torch.clamp(self.Ir, 1.7, 3.0)
        gm2 = (Ir - 1) * (self.gm1 * 0.059) / 0.038
        Cr = torch.clamp(self.Cr, 1.0)
        C2 = Cr * self.C1
        a1 = (self.gm1 / (2*self.C1)).unsqueeze(1)
        b1 = (self.gm1 / (2*C2)).unsqueeze(1)
        b0 = (self.gm1 * gm2 / (4 * self.C1 * C2)).unsqueeze(1)

        h = - a1 * self.w / (self.w**2 + b1 * self.w + b0)
        abs_h = torch.abs(h)
        abs_h = (abs_h - abs_h.min()) / (abs_h.max() - abs_h.min())
        waveform_fft = torch.fft.rfft(waveform, dim=-1)
        filtered_fft = abs_h * waveform_fft
        filtered_waveform = torch.fft.irfft(filtered_fft, dim=-1)
        return filtered_waveform