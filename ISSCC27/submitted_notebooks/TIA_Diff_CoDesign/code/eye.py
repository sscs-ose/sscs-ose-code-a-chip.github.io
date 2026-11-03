"""Deterministic linear NRZ and PAM4 reconstruction from complex TIA responses."""
import numpy as np


def prbs15_bits(count, seed=1):
    """First count bits of b[n+15] = b[n+14] XOR b[n], period 32767.

    Initial b[0:15] is the least-significant-bit-first representation of seed.
    This explicitly defines the PRBS convention and reproducible initial state.
    """
    count, seed = int(count), int(seed)
    if count < 1 or not 0 < seed < 2**15:
        raise ValueError('Use a positive bit count and a nonzero 15-bit seed')
    bits = np.empty(count + 15, dtype=np.uint8)
    bits[:15] = [(seed >> i) & 1 for i in range(15)]
    for i in range(count):
        bits[i + 15] = bits[i + 14] ^ bits[i]
    return bits[:count]


def pam4_word(nsym=2048, input_pp=200e-6, seed=1):
    """Gray mapping: 00/01/11/10 -> levels 0/1/2/3, rectangular NRZ pulses."""
    if int(nsym) < 64 or not np.isfinite(input_pp) or input_pp <= 0:
        raise ValueError('Use at least 64 symbols and a positive current swing')
    bits = prbs15_bits(2 * int(nsym), seed)
    levels = np.array([0, 1, 3, 2], dtype=np.uint8)[2 * bits[::2] + bits[1::2]]
    if len(np.unique(levels)) != 4:
        raise ValueError('The selected PRBS word does not contain all PAM4 levels')
    return levels, (levels.astype(float) / 3 - .5) * float(input_pp)


def nrz_word(nsym=2048, input_pp=200e-6, seed=1):
    """Binary NRZ/PAM2 current levels with the same peak-to-peak swing as PAM4."""
    if int(nsym) < 64 or not np.isfinite(input_pp) or input_pp <= 0:
        raise ValueError('Use at least 64 symbols and a positive current swing')
    levels = prbs15_bits(int(nsym), seed)
    if len(np.unique(levels)) != 2:
        raise ValueError('The selected PRBS word does not contain both NRZ levels')
    return levels, (levels.astype(float) - .5) * float(input_pp)


def _checked_response(response):
    f, zt = np.asarray(response['f'], float), np.asarray(response['zt'], complex)
    if (f.ndim != 1 or zt.shape != f.shape or len(f) < 3
            or not np.all(np.isfinite(f)) or not np.all(np.isfinite(zt))
            or f[0] < 0 or np.any(np.diff(f) <= 0) or abs(zt[0]) == 0):
        raise ValueError('Response needs finite complex Zt on an increasing frequency grid')
    return f, zt


def _gaps(samples, levels, nlevels=4):
    groups = [samples[levels == k] for k in range(nlevels)]
    lower = np.array([np.min(x, axis=0) for x in groups])
    upper = np.array([np.max(x, axis=0) for x in groups])
    return lower[1:] - upper[:-1], lower, upper


def _positive_window(margin, centre):
    """Width of the positive interval containing centre, interpolated in samples."""
    if margin[centre] <= 0:
        return 0.0
    left = right = int(centre)
    while left > 0 and margin[left - 1] > 0:
        left -= 1
    while right + 1 < len(margin) and margin[right + 1] > 0:
        right += 1
    lo, hi = float(left), float(right)
    if left > 0:
        lo -= margin[left] / (margin[left] - margin[left - 1])
    if right + 1 < len(margin):
        hi += margin[right] / (margin[right] - margin[right + 1])
    return max(0.0, hi - lo)


def reconstruct_eye(response, baud=53.125e9, nsym=2048, osr=32,
                    input_pp=200e-6, seed=1, taper_fraction=.8, modulation='PAM4'):
    """Reconstruct a periodic finite-word, noiseless linear NRZ or PAM4 eye.

    Complex Zt is interpolated in Cartesian coordinates.  Below the first saved
    frequency, its real part is held constant and its imaginary part approaches
    zero linearly at DC; this is an explicit completion, not measured DC data.
    A raised-cosine taper removes the last 20% of the available frequency band,
    followed by zero response above that band.  The input mean is removed.
    """
    f, zt = _checked_response(response)
    osr, nsym = int(osr), int(nsym)
    if (not np.isfinite(baud) or baud <= 0 or osr < 8 or osr % 2
            or not 0 < taper_fraction <= 1):
        raise ValueError('Use positive baud, an even OSR >=8, and taper_fraction in (0,1]')
    if modulation not in ('NRZ', 'PAM4'):
        raise ValueError('Choose NRZ (PAM2) or PAM4')
    nlevels = 4 if modulation == 'PAM4' else 2
    bits_per_symbol = 2 if modulation == 'PAM4' else 1
    levels, symbols = (pam4_word if modulation == 'PAM4' else nrz_word)(nsym, input_pp, seed)
    fs = float(baud) * osr
    x = np.repeat(symbols - symbols.mean(), osr)
    fk = np.fft.rfftfreq(len(x), 1 / fs)
    h = np.interp(fk, f, zt.real) + 1j * np.interp(fk, f, zt.imag)
    if f[0] > 0:
        low = fk < f[0]
        h[low] = zt[0].real + 1j * zt[0].imag * fk[low] / f[0]
    start, stop = float(f[-1]) * taper_fraction, float(f[-1])
    taper = np.ones_like(fk)
    if start < stop:
        band = (fk > start) & (fk < stop)
        taper[band] = .5 * (1 + np.cos(np.pi * (fk[band] - start) / (stop - start)))
    taper[fk >= stop] = 0
    # A polarity flip is only for display; the recorded complex phase is retained.
    polarity = 1.0 if zt[0].real >= 0 else -1.0
    y = polarity * np.fft.irfft(np.fft.rfft(x) * h * taper, len(x))

    # Estimate whole-symbol propagation delay, then optimize one common sampling
    # phase for every eye.  PAM4 uses one phase for all three eyes.
    lowband = f <= min(f[-1], max(f[0] + 2 * (f[1] - f[0]), baud / 4))
    delay = -np.polyfit(2 * np.pi * f[lowband], np.unwrap(np.angle(zt[lowband])), 1)[0]
    delay_samples = int(round(delay * fs))
    guard = min(32, nsym // 8)
    ids = np.arange(guard, nsym - guard)
    centres = ids * osr + osr // 2
    shifts = np.arange(delay_samples - 2 * osr, delay_samples + 2 * osr + 1)
    scores = []
    for shift in shifts:
        gaps, _, _ = _gaps(y[(centres + shift) % len(y)], levels[ids], nlevels)
        scores.append(float(np.min(gaps)))
    scores = np.asarray(scores)
    tolerance = max(1e-15, np.max(abs(y)) * 1e-12)
    # A flat-gain channel has many equally open phases.  Resolve numerical ties
    # toward the estimated propagation delay, keeping its sampling point central.
    tied = shifts[scores >= scores.max() - tolerance]
    shift = int(min(tied, key=lambda value: abs(value - delay_samples)))
    y = np.roll(y, -shift)
    sample_matrix = y.reshape(nsym, osr)[ids]
    gaps, lower, upper = _gaps(sample_matrix, levels[ids], nlevels)
    centre = osr // 2
    heights = gaps[:, centre]
    thresholds = (lower[1:, centre] + upper[:-1, centre]) / 2
    margins = np.minimum(lower[1:] - thresholds[:, None], thresholds[:, None] - upper[:-1])
    # Include the next phase endpoint to give an unambiguous 0..1 UI interval.
    widths = [_positive_window(np.r_[m, m[0]], centre) / osr for m in margins]
    common_width = _positive_window(np.r_[margins.min(axis=0), margins[:, 0].min()], centre) / osr
    ideal_spacing = abs(zt[0]) * float(input_pp) / (nlevels - 1)
    minimum_height = min(heights)
    metrics = dict(eye_heights_mv=(heights * 1e3).tolist(), min_eye_mv=float(minimum_height * 1e3),
                   eye_width_ui=[float(w) for w in widths], common_width_ui=float(common_width),
                   common_width_ps=float(common_width / baud * 1e12),
                   phase_ui=float(((centre + shift) % osr) / osr),
                   deskew_ps=float(shift / fs * 1e12), polarity_flipped=polarity < 0,
                   ideal_spacing_1ghz_mv=float(ideal_spacing * 1e3),
                   opening_pct=float(100 * minimum_height / ideal_spacing),
                   output_pp_mv=float(np.ptp(y) * 1e3), response_points=len(f),
                   response_min_ghz=float(f[0] / 1e9), response_max_ghz=float(f[-1] / 1e9),
                   response_step_max_ghz=float(np.max(np.diff(f)) / 1e9),
                   taper_start_ghz=start / 1e9, taper_stop_ghz=stop / 1e9)
    if modulation == 'PAM4':
        metrics.update(lower_eye_mv=float(heights[0] * 1e3), middle_eye_mv=float(heights[1] * 1e3),
                       upper_eye_mv=float(heights[2] * 1e3))
    if 'fn' in response and 'inoise' in response:
        fn, ni = np.asarray(response['fn'], float), np.asarray(response['inoise'], float)
        good = ((fn >= f[0]) & (fn <= f[-1]) & np.isfinite(fn)
                & np.isfinite(ni) & (ni >= 0)) if fn.shape == ni.shape else np.zeros(0, bool)
        if np.count_nonzero(good) >= 3 and np.all(np.diff(fn[good]) > 0):
            nf = fn[good]
            zn = np.interp(nf, f, zt.real) + 1j * np.interp(nf, f, zt.imag)
            integrate = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
            rms = np.sqrt(integrate((ni[good] * abs(zn))**2, nf))
            metrics.update(output_noise_rms_mv=float(rms * 1e3),
                           noise_band_ghz=[float(nf[0]/1e9), float(nf[-1]/1e9)])
    return dict(metrics=metrics, waveform=y, levels=levels, osr=osr, guard=guard,
                settings=dict(baud=float(baud), nsym=nsym, osr=osr, input_pp=float(input_pp), seed=int(seed),
                              modulation=modulation, bits_per_symbol=bits_per_symbol, bit_rate=float(baud) * bits_per_symbol))


def _eye_density(eye, voltage_edges, samples_per_ui=256, centered=False):
    """Count all retained eye traces; finer linear interpolation is display-only."""
    y, osr, guard = eye['waveform'], eye['osr'], eye['guard']
    nsym = len(y) // osr
    starts = np.arange(guard, nsym - guard - 1)
    offsets = np.arange(2 * osr + 1)
    first = starts * osr - (osr // 2 if centered else 0)
    traces = y[first[:, None] + offsets] * 1e3
    original_t = offsets / osr
    fine_t = (np.arange(2 * samples_per_ui) + .5) / samples_per_ui
    dense = np.array([np.interp(fine_t, original_t, trace) for trace in traces])
    time_edges = np.linspace(0, 2, 2 * samples_per_ui + 1)
    density, _, _ = np.histogram2d(np.broadcast_to(fine_t, dense.shape).ravel(), dense.ravel(),
                                    bins=(time_edges, voltage_edges))
    return density.T
