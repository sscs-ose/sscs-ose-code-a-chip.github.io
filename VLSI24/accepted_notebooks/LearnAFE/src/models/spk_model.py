import torch
import torch.nn as nn
import torch.nn.functional as F


class IAF_Spec(nn.Module):
    def __init__(
        self,
        n_neuron,
        config_path,
        hop_length,
        overlap=False,
        freeze=True,
    ):
        super(IAF_Spec, self).__init__()
        self.n_neuron = n_neuron
        self.hop_length = hop_length
        self.overlap = overlap
        self.freeze = freeze
        if overlap:
            self.win_length = 2 * hop_length
        else:
            self.win_length = hop_length
        
        afe_config = {}
        path = 'AFE_Config/Design/' + config_path + '.txt'
        with open(path, 'r') as file:
            for line in file:
                name, value = line.strip().split('\t')
                afe_config[name] = float(value)
        C = torch.tensor(afe_config['C_spk'])
        Vth = torch.tensor(afe_config['Vth'])

        self.CV = nn.Parameter(torch.full((self.n_neuron, ), C*Vth), requires_grad = not self.freeze)

    def forward(self, waveform):
        waveform = torch.clamp(torch.abs(waveform), 0.0, 0.5)
        frames = self._framing(waveform).sum(dim=-1)
        specgram = frames / self.CV.unsqueeze(1)
        if not self.overlap:
            specgram = specgram[..., 0:-1] + specgram[..., 1:]
        return specgram.unsqueeze(1)

    def _framing(self, waveform):
        t_len = waveform.shape[-1]
        n_frames = torch.ceil(torch.tensor(t_len / self.hop_length)).int()
        pad_len = n_frames * self.hop_length - t_len
        waveform = F.pad(waveform, (0, pad_len), 'constant', 0)
        waveforms = waveform.unfold(
            -1, self.win_length, self.hop_length
        ).to(waveform.device)
        return waveforms