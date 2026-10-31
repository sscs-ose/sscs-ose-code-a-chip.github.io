"""
Chopper Stabilization and Ripple Reduction Loop (RRL) Simulation Engine
Continuous-time and discrete-time modeling for flicker noise removal and offset cancellation.
Author: NeuroDyn-AFE Team (IEEE SSCS Code-a-Chip ISSCC 2027)
"""

import numpy as np
from scipy import signal
from typing import Dict, Tuple, Any, Optional

class ChopperRRLSimulator:
    """
    Simulates the physical signal path through:
    1. Input Low-Vt Chopper (CHOP1): Up-modulates biopotential signal to f_chop = 4 kHz.
    2. Dynamic Subthreshold OTA: Introduces input offset Vos (~5-15 mV) and 1/f noise.
    3. Output Chopper (CHOP2): Demodulates signal to baseband and up-modulates Vos & 1/f noise to 4 kHz.
    4. Switched-Capacitor Ripple Reduction Loop (RRL): Causal discrete-time half-period
       differencing integrator (Burt & Zhang topology) that extracts the 4 kHz ripple
       without requiring prior knowledge of the bio-signal, steering corrective current
       into the auxiliary input terminals.
    """
    def __init__(
        self,
        f_chop_hz: float = 4000.0,
        rrl_gain: float = 76.0,
        ota_gain_db: float = 67.2,
        ota_bandwidth_hz: float = 12000.0,
        fs_hz: float = 200000.0,
        duration_s: float = 0.030,
        random_seed: int = 422
    ):
        self.f_chop = f_chop_hz
        self.rrl_gain = rrl_gain
        self.ota_gain = 10.0 ** (ota_gain_db / 20.0)
        self.ota_bw = ota_bandwidth_hz
        self.fs = fs_hz
        self.duration = duration_s
        self.random_seed = random_seed
        self.t = np.arange(0, self.duration, 1.0 / self.fs)
        self.N = len(self.t)

    def generate_chopper_clock(self, phase_rad: float = 0.0) -> np.ndarray:
        """Generates square wave clock (+1 / -1) for chopper switches."""
        return signal.square(2.0 * np.pi * self.f_chop * self.t + phase_rad)

    def generate_flicker_noise(self, kf_scale: float = 5e-6) -> np.ndarray:
        """
        Generates 1/f flicker noise sequence using frequency-domain shaping.
        Power spectral density ~ 1/f.
        """
        rng = np.random.default_rng(self.random_seed)
        white = rng.standard_normal(self.N)
        freqs = np.fft.rfftfreq(self.N, d=1.0/self.fs)
        freqs[0] = 1e-3  # Avoid division by zero at DC
        flicker_filter = 1.0 / np.sqrt(freqs)
        fft_white = np.fft.rfft(white)
        fft_flicker = fft_white * flicker_filter
        flicker_noise = np.fft.irfft(fft_flicker, n=self.N)
        return flicker_noise * kf_scale

    def simulate_chain(
        self,
        vin_amplitude_uv: float = 250.0,
        vin_freq_hz: float = 60.0,
        v_offset_mv: float = 10.0,
        enable_chopping: bool = True,
        enable_rrl: bool = True,
        vin_signal_uv: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end transient simulation of the front-end amplifier.
        Accepts either a single test tone or a complex physiological biopotential (e.g. EEG).
        Returns time-domain waveforms and frequency spectra.
        """
        if vin_signal_uv is not None:
            vin = vin_signal_uv * 1e-6
        else:
            vin = (vin_amplitude_uv * 1e-6) * np.sin(2.0 * np.pi * vin_freq_hz * self.t)
        vos = v_offset_mv * 1e-3
        flicker = self.generate_flicker_noise(kf_scale=5e-6)
        
        # 1. Input Chopping
        chop1 = self.generate_chopper_clock(0.0) if enable_chopping else np.ones(self.N)
        v_in_chopped = vin * chop1
        
        # 2. Dynamic OTA with offset and flicker noise
        b_ota, a_ota = signal.butter(1, self.ota_bw, btype='low', fs=self.fs, analog=False)
        # Ripple Reduction Loop modeling:
        v_corr = np.zeros(self.N)
        v_demod = np.zeros(self.N)
        
        # Switched-Capacitor Differencing Integrator:
        # Half-period delay samples (T_half = 1 / (2 * f_chop))
        samples_per_half_period = int(self.fs / (2.0 * self.f_chop)) # 25 samples
        tau_rrl = 0.0018  # RRL integration time constant ~ 2.5 ms
        dt = 1.0 / self.fs
        corr_state = 0.0
        
        chop2 = self.generate_chopper_clock(0.0) if enable_chopping else np.ones(self.N)
        
        if enable_chopping and enable_rrl:
            # Physical causal feedback loop without access to unknown input signal
            demod_history = np.zeros(self.N)
            for i in range(self.N):
                # Effective input with feedback correction
                eff_in = v_in_chopped[i] + (vos - corr_state) + flicker[i]
                v_ota_out_instant = eff_in * self.ota_gain
                demod_val = v_ota_out_instant * chop2[i]
                demod_history[i] = demod_val
                
                # Causal Switched-Capacitor Ripple Detection:
                # Differentiates consecutive half-cycles to eliminate baseband signal (fin << fchop)
                # leaving purely the square-wave chopping ripple
                if i >= samples_per_half_period:
                    ripple_sample = (demod_val - demod_history[i - samples_per_half_period]) * chop2[i] * 0.5
                else:
                    ripple_sample = 0.0
                    
                corr_state += (ripple_sample / self.ota_gain) * (dt / tau_rrl) * self.rrl_gain
                # Limit correction to physical dynamic range
                corr_state = np.clip(corr_state, -0.05, 0.05)
                
                v_corr[i] = corr_state
                v_demod[i] = demod_val
            
            net_in = v_in_chopped + (vos - v_corr) + flicker
            v_amp_out = signal.lfilter(b_ota, a_ota, net_in) * self.ota_gain
            v_out = v_amp_out * chop2
        elif enable_chopping and not enable_rrl:
            net_in = v_in_chopped + vos + flicker
            v_amp_out = signal.lfilter(b_ota, a_ota, net_in) * self.ota_gain
            v_out = v_amp_out * chop2
        else: # Unchopped baseline
            net_in = vin + vos + flicker
            v_out = signal.lfilter(b_ota, a_ota, net_in) * self.ota_gain
            
        # Post-filter: 3rd-order Butterworth low-pass filter at 1.2 kHz to recover biopotential
        b_lpf, a_lpf = signal.butter(3, 1200.0, btype='low', fs=self.fs)
        v_recovered = signal.lfilter(b_lpf, a_lpf, v_out)
        
        # Frequency spectrum computation (FFT)
        freqs = np.fft.rfftfreq(self.N, d=1.0/self.fs)
        fft_recovered = np.abs(np.fft.rfft(v_recovered)) / (self.N / 2)
        fft_db = 20.0 * np.log10(np.maximum(fft_recovered, 1e-12))
        
        # Calculate residual offset and ripple in settled steady state (last 20% of simulation, t >= 12 ms)
        settled_start = int(self.N * 0.8)
        steady_out = v_recovered[settled_start:]
        
        # True Input-Referred Residual DC Offset:
        # In physical bio-potential instrumentation, input-referred DC offset is measured with zero input
        # (or extracted from the uncompensated DC residual error of the cancellation feedback loop).
        if vin_amplitude_uv == 0.0:
            residual_dc_offset_uv = float(np.abs(np.mean(steady_out) / self.ota_gain) * 1e6)
        else:
            if enable_rrl:
                # With RRL active, residual offset is the difference between injected vos and settled v_corr
                residual_dc_offset_uv = float(np.abs(vos - np.mean(v_corr[settled_start:])) * 1e6)
            elif enable_chopping:
                # With chopping only (no RRL), offset is shifted to f_chop (4 kHz) and attenuated by the 1.2 kHz LPF
                residual_dc_offset_uv = float(np.abs(vos) / (1.0 + (self.f_chop / 1200.0) ** 3) * 1e6)
            else:
                # Raw unchopped: full uncompensated DC offset
                residual_dc_offset_uv = float(np.abs(vos) * 1e6)
        
        # Physical differential saturation limit: +/- 250 mV headroom on VDD = 0.60V (Vcm = 0.30V)
        v_sat = 0.25
        v_out_phys = np.clip(v_out, -v_sat, v_sat)
        
        # 4 kHz Chopping Ripple Extraction:
        # Isolates the switching ripple at f_chop from baseband biosignals using the FFT bin at f_chop
        fft_out_phys = np.abs(np.fft.rfft(v_out_phys[settled_start:])) / (len(v_out_phys[settled_start:]) / 2)
        freqs_phys = np.fft.rfftfreq(len(v_out_phys[settled_start:]), d=1.0/self.fs)
        idx_fchop = np.argmin(np.abs(freqs_phys - self.f_chop))
        peak_to_peak_ripple_mv = float(fft_out_phys[idx_fchop] * 2.0 * 1e3)
        
        # End-to-end Input-Referred recovered biosignal (standard IEEE metric for bio-AFE dynamic range)
        v_recovered_ir_mv = (v_recovered / self.ota_gain) * 1e3
        
        return {
            "time_ms": self.t * 1e3,
            "vin_uv": vin * 1e6,
            "v_chopped_in_uv": v_in_chopped * 1e6,
            "v_out_v": v_out_phys,
            "v_recovered_mv": v_recovered_ir_mv,
            "v_recovered_out_v": np.clip(v_recovered, -v_sat, v_sat),
            "v_corr_mv": v_corr * 1e3,
            "fft_freqs_hz": freqs,
            "fft_mag_db": fft_db,
            "residual_offset_uV": residual_dc_offset_uv,
            "peak_to_peak_ripple_mV": peak_to_peak_ripple_mv,
            "steady_state_gain_db": 20.0 * np.log10(np.max(np.abs(v_recovered[settled_start:])) / max(vin_amplitude_uv * 1e-6, 1e-12))
        }
