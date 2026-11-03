"""
PrecisionFit -- floating-point reference filter and test signals.

Filter A (primary, used for optimization/development):
  17-tap symmetric lowpass FIR, designed with SciPy's Parks-McClellan
  (equiripple) method. Symmetric coefficients let us halve the multiplier
  count in RTL later (h[n] == h[N-1-n]) -- a real, standard FIR optimization,
  and it applies identically to every candidate design so comparisons stay
  fair.

Filter B (generalization test, Week 4): a second, different spec -- do NOT
  touch this file's FILTER_B_SPEC while iterating on Filter A. It exists
  to prove the method isn't overfit to one filter.
"""
import numpy as np
from scipy import signal

from paths import RESULTS_DIR

# ---------------------------------------------------------------------------
# Filter A: primary design used for all optimization work
# ---------------------------------------------------------------------------
FILTER_A_SPEC = dict(
    numtaps=17,             # odd length -> exact linear phase, clean symmetric center tap
    fs=48_000,              # sample rate, Hz (audio-rate, motivates the "audio" framing)
    passband_edge=4_000,    # Hz
    stopband_edge=10_000,   # Hz
    passband_ripple_db=0.5,  # max allowed passband ripple
    stopband_atten_db=40.0,  # min required stopband attenuation
)
# NOTE (deviation from the guide's example numbers, and why): the guide's
# original Filter A spec (passband edge 4 kHz, stopband edge 7 kHz, 0.5 dB /
# 40 dB) is not achievable with a 17-tap linear-phase FIR -- a 3 kHz
# transition at fs=48 kHz needs ~31 taps at that ripple/attenuation. The
# guide anticipates exactly this and says to loosen the spec or bump numtaps.
# We keep numtaps=17 (so the whole "N=17 -> 9 multipliers via symmetric
# folding" architecture in section 3.1 is preserved) and widen the transition
# band instead. Measured at design time: 0.383 dB ripple, 42.3 dB attenuation,
# i.e. it passes with real margin but is still a non-trivial filter.

# ---------------------------------------------------------------------------
# Filter B: second spec, only used in the Week 4 generalization test
# ---------------------------------------------------------------------------
FILTER_B_SPEC = dict(
    numtaps=17,
    fs=48_000,
    passband_edge=6_000,    # Hz
    stopband_edge=11_000,   # Hz
    passband_ripple_db=0.5,
    stopband_atten_db=35.0,
)
# Same 17-tap constraint as Filter A, wider passband / relaxed attenuation --
# measured at design time 0.389 dB ripple, 37.2 dB attenuation (passes).


def design_filter(spec: dict) -> np.ndarray:
    """Parks-McClellan equiripple FIR design. Returns float64 coefficients."""
    fs = spec["fs"]
    nyq = fs / 2
    passband_ripple_lin = (10 ** (spec["passband_ripple_db"] / 20) - 1) / \
                          (10 ** (spec["passband_ripple_db"] / 20) + 1)
    stopband_atten_lin = 10 ** (-spec["stopband_atten_db"] / 20)
    weight_pass = 1 / passband_ripple_lin
    weight_stop = 1 / stopband_atten_lin

    h = signal.remez(
        spec["numtaps"],
        [0, spec["passband_edge"], spec["stopband_edge"], nyq],
        [1, 0],
        weight=[weight_pass, weight_stop],
        fs=fs,
    )
    return h


def verify_spec(h: np.ndarray, spec: dict, n_fft: int = 8192) -> dict:
    """Check a coefficient set against its spec. Returns measured margins."""
    w, H = signal.freqz(h, worN=n_fft, fs=spec["fs"])
    mag_db = 20 * np.log10(np.abs(H) + 1e-300)

    pass_mask = w <= spec["passband_edge"]
    stop_mask = w >= spec["stopband_edge"]

    passband_ripple_measured = mag_db[pass_mask].max() - mag_db[pass_mask].min()
    stopband_atten_measured = -mag_db[stop_mask].max()

    return dict(
        passband_ripple_db=passband_ripple_measured,
        stopband_atten_db=stopband_atten_measured,
        passband_ok=passband_ripple_measured <= spec["passband_ripple_db"],
        stopband_ok=stopband_atten_measured >= spec["stopband_atten_db"],
        freqs=w,
        mag_db=mag_db,
    )


def make_test_signals(fs: int, n_samples: int = 4096, seed: int = 0) -> dict:
    """
    Standard signal set used throughout the project:
      - impulse: isolates the impulse response exactly
      - step: settling behavior
      - full_scale: worst-case amplitude chirp (saturation/overflow stress)
      - random_wideband: white-ish uniform noise, generic accuracy statistics
      - random_music_like: pink-ish noise, more representative of audio content
      - multitone: known frequencies inside/outside passband for response verification
    All signals are normalized to roughly [-1, 1) (i.e. Q-format-ready float).
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n_samples) / fs

    impulse = np.zeros(n_samples)
    impulse[0] = 1.0
    step = np.ones(n_samples)

    full_scale = 0.999 * signal.chirp(t, f0=1, f1=fs / 2, t1=t[-1], method="linear")

    random_wideband = rng.uniform(-0.9, 0.9, n_samples)

    white = rng.normal(0, 1, n_samples)
    freqs = np.fft.rfftfreq(n_samples)
    freqs[0] = freqs[1]
    shaping = 1 / np.sqrt(freqs)
    pink = np.fft.irfft(np.fft.rfft(white) * shaping, n=n_samples)
    pink = 0.8 * pink / np.max(np.abs(pink))

    multitone = 0.3 * (np.sin(2 * np.pi * 1000 * t) +
                       np.sin(2 * np.pi * 5000 * t) +
                       np.sin(2 * np.pi * 9000 * t))

    return dict(
        impulse=impulse, step=step, full_scale=full_scale,
        random_wideband=random_wideband, random_music_like=pink,
        multitone=multitone,
    )


def float_reference(x_float: np.ndarray, h_float: np.ndarray) -> np.ndarray:
    """
    Causal (zero-padded) floating-point FIR reference -- the exact same
    indexing convention the fixed-point model and the RTL both use:
        y[i] = sum_j h[j] * x[i-j],  x[k] = 0 for k < 0
    """
    return np.convolve(x_float, h_float, mode="full")[:len(x_float)]


if __name__ == "__main__":
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    h = design_filter(FILTER_A_SPEC)
    v = verify_spec(h, FILTER_A_SPEC)
    print(f"Filter A: {len(h)} taps")
    print(f"  passband ripple: {v['passband_ripple_db']:.3f} dB "
          f"(spec: <= {FILTER_A_SPEC['passband_ripple_db']}), ok={v['passband_ok']}")
    print(f"  stopband atten:  {v['stopband_atten_db']:.3f} dB "
          f"(spec: >= {FILTER_A_SPEC['stopband_atten_db']}), ok={v['stopband_ok']}")
    print(f"  symmetric: {np.allclose(h, h[::-1])}")
    np.save(RESULTS_DIR / "filter_a_coeffs_float.npy", h)

    hb = design_filter(FILTER_B_SPEC)
    vb = verify_spec(hb, FILTER_B_SPEC)
    print(f"\nFilter B: {len(hb)} taps")
    print(f"  passband ripple: {vb['passband_ripple_db']:.3f} dB "
          f"(spec: <= {FILTER_B_SPEC['passband_ripple_db']}), ok={vb['passband_ok']}")
    print(f"  stopband atten:  {vb['stopband_atten_db']:.3f} dB "
          f"(spec: >= {FILTER_B_SPEC['stopband_atten_db']}), ok={vb['stopband_ok']}")
    print(f"  symmetric: {np.allclose(hb, hb[::-1])}")
    np.save(RESULTS_DIR / "filter_b_coeffs_float.npy", hb)
