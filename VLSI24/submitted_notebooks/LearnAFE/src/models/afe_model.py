import torch.nn as nn
import torchvision.transforms as vtransforms

import src.models as mdl


class LearnAFE_v2(nn.Module):
    def __init__(
        self,
        n_filter,
        sample_rate,
        config_path,
        hop_length,
        overlap,
        freeze,
        max_sample_len,
        backbone,
    ):
        super(LearnAFE_v2, self).__init__()
        self.n_filter = n_filter
        self.sample_rate = sample_rate
        self.config_path = config_path
        self.hop_length = hop_length
        self.overlap = overlap
        self.freeze = freeze
        self.max_sample_len = max_sample_len
        self.backbone = backbone

        self.bpf = mdl.DSF_Filtering(
            n_filter = self.n_filter,
            sample_rate = self.sample_rate,
            config_path = self.config_path,
            freeze = self.freeze,
        )
        self.spk = mdl.IAF_Spec(
            n_neuron = self.n_filter,
            hop_length = self.hop_length,
            config_path = self.config_path,
            overlap = self.overlap,
            freeze = self.freeze,
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