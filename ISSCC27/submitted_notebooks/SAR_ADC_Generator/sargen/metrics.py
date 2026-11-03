"""Static and dynamic ADC metrics: transfer curve, INL/DNL, histogram, FFT/ENOB."""

import numpy as np


def coherent_tone(fs: float, n_samples: int, cycles: int) -> float:
    """Input frequency for coherent sampling (`cycles` should be odd and coprime with n_samples)."""
    return cycles * fs / n_samples


def fft_metrics(codes, bits: int, cycles: int, n_harmonics: int = 7) -> dict:
    """SNDR / SFDR / ENOB from a coherently sampled sine (rectangular window)."""
    x = np.asarray(codes, dtype=float)
    n = len(x)
    x = x - x.mean()
    spec = np.abs(np.fft.rfft(x)) ** 2
    spec[1:-1] *= 2                       # single-sided power
    p_sig = spec[cycles]
    p_noise_dist = spec[1:].sum() - p_sig
    harmonics = []
    for h in range(2, n_harmonics + 1):
        k = (h * cycles) % n
        k = n - k if k > n // 2 else k    # alias into first Nyquist zone
        if 0 < k < len(spec) and k != cycles:
            harmonics.append(k)
    spur = np.delete(spec[1:], cycles - 1).max()
    sndr = 10 * np.log10(p_sig / p_noise_dist)
    thd = 10 * np.log10(spec[harmonics].sum() / p_sig) if harmonics else float("nan")
    ref = spec.max()
    return dict(
        sndr_db=float(sndr),
        sfdr_db=float(10 * np.log10(p_sig / spur)),
        thd_db=float(thd),
        enob=float((sndr - 1.76) / 6.02),
        ideal_sqnr_db=6.02 * bits + 1.76,
        freq_bins=np.arange(len(spec)) / n,          # in units of fs
        spectrum_dbfs=10 * np.log10(spec / ref + 1e-30),
        harmonic_bins=harmonics,
    )


def histogram_inl_dnl(codes, bits: int) -> dict:
    """Code-density (histogram) test for a linear ramp that slightly overdrives both ends."""
    hist = np.bincount(np.asarray(codes, dtype=int), minlength=2**bits)
    inner = hist[1:-1].astype(float)
    dnl = inner / inner.mean() - 1
    inl = np.cumsum(dnl)
    inl = inl - np.linspace(0, inl[-1], len(inl))  # end-point fit
    missing = int((inner == 0).sum())
    return dict(hist=hist, codes=np.arange(1, 2**bits - 1), dnl=dnl, inl=inl,
                dnl_max=float(np.abs(dnl).max()), inl_max=float(np.abs(inl).max()),
                missing_codes=missing)


def transition_levels(vin, codes, bits: int) -> np.ndarray:
    """Input voltage where the output first reaches each code 1..2^N-1 (monotonic ramp)."""
    vin = np.asarray(vin)
    codes = np.asarray(codes)
    t = np.full(2**bits - 1, np.nan)
    for k in range(1, 2**bits):
        hit = np.nonzero(codes >= k)[0]
        if len(hit):
            j = hit[0]
            t[k - 1] = vin[j] if j == 0 else 0.5 * (vin[j] + vin[j - 1])
    return t


def transition_inl_dnl(transitions, vref: float, bits: int) -> dict:
    """INL/DNL from transition levels against the ideal staircase (absolute, in LSB)."""
    lsb = vref / 2**bits
    t = np.asarray(transitions)
    ideal = lsb * np.arange(1, 2**bits)        # ideal transitions for a truncating ADC
    inl = (t - ideal) / lsb
    dnl = np.diff(t) / lsb - 1
    return dict(t=t, inl=inl, dnl=dnl, offset_lsb=float(inl[0]),
                gain_error_lsb=float(inl[-1] - inl[0]),
                inl_max=float(np.nanmax(np.abs(inl - np.linspace(inl[0], inl[-1], len(inl))))),
                dnl_max=float(np.nanmax(np.abs(dnl))))


def walden_fom(power_w: float, enob: float, fs: float) -> float:
    """Walden figure of merit [J/conversion-step]."""
    return power_w / (2**enob * fs)
