import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio.functional as aF

import src.data.dataset as ds


class RandomAddNoise(nn.Module):
    """ Add random noise to the input waveform.

    """
    def __init__(
        self, 
        p, 
        snr_min, 
        snr_max, 
        noise_kwargs, 
    ):
        super().__init__()

        noise_set = ds.NoiseDataset(**noise_kwargs)
        noise_tensor = []
        for noise, _ in noise_set:
            noise_tensor.append(noise[0])

        self.register_buffer('noise_tensor', torch.stack(noise_tensor))
        self.p = p
        self.snr_min = snr_min
        self.snr_max = snr_max

    def forward(self, waveform):
        if torch.rand(1) < self.p:
            waveform = waveform.squeeze(1)
            bsz = waveform.shape[0]

            noise_idx = torch.randint(0, len(self.noise_tensor), (bsz,))

            noises = self.noise_tensor[noise_idx]
            snrs = torch.randint(
                self.snr_min, self.snr_max, (bsz,)
            ).to(waveform.device)

            noisy_waveform = aF.add_noise(waveform, noises, snr=snrs)
            return noisy_waveform.unsqueeze(1) 
        else:
            return waveform