import numpy as np


def find_switching_times(
    trace,
    t_start,
    t_end,
    vdd=1.8,
    edge="rising",
):
    """
    Find all times at which a signal crosses 50% VDD within an interval.

    Parameters
    ----------
    trace   : (x, y) tuple of numpy arrays (time, voltage)
    t_start : start of search window (in ns)
    t_end   : end of search window (in ns)
    vdd     : supply voltage (threshold = vdd / 2)
    edge    : "rising" or "falling"

    Returns
    -------
    List of crossing times in ns.
    """
    t, v = np.asarray(trace[0], dtype=float), np.asarray(trace[1], dtype=float)
    threshold = vdd / 2

    mask = (t >= t_start) & (t <= t_end)
    t_w = t[mask]
    v_w = v[mask]

    crossings = []
    for i in range(len(t_w) - 1):
        crossed = False
        if edge == "rising" and v_w[i] < threshold <= v_w[i + 1]:
            crossed = True
        elif edge == "falling" and v_w[i] >= threshold > v_w[i + 1]:
            crossed = True

        if not crossed:
            continue

        frac = (threshold - v_w[i]) / (v_w[i + 1] - v_w[i])
        crossings.append(t_w[i] + frac * (t_w[i + 1] - t_w[i]))

    return crossings


def find_switching_time(
    trace,
    t_start,
    t_end,
    vdd=1.8,
    edge="rising",
    occurrence=1
):
    """
    Find the time at which a signal crosses 50% VDD within an interval.

    Parameters
    ----------
    trace      : (x, y) tuple of numpy arrays (time, voltage)
    t_start    : start of search window (in ns)
    t_end      : end of search window (in ns)
    vdd        : supply voltage (threshold = vdd / 2)
    edge       : "rising" or "falling"
    occurrence : which crossing to return (1-based)

    Returns
    -------
    Crossing time in ns, or None if not found.
    """
    crossings = find_switching_times(
        trace,
        t_start=t_start,
        t_end=t_end,
        vdd=vdd,
        edge=edge,
    )
    if occurrence <= 0:
        raise ValueError("occurrence must be >= 1")
    if len(crossings) < occurrence:
        return None
    return crossings[occurrence - 1]


def get_sample(
    trace,
    t_start,
    t_end
):
    """
    Returns the sample of a given trace in the specified interval.

    Parameters
    ----------
    trace      : (x, y) tuple of numpy arrays (time, voltage)
    t_start    : start of sample window
    t_end      : end of sample window

    Returns
    -------
    A sample of the given trace
    """
    t, v = trace
    mask = (t >= t_start) & (t < t_end)
    t_w = t[mask]
    v_w = v[mask]

    return (t_w, v_w)


def apply_time_shift(
    trace,
    time_shift
):
    """
    Returns the trace but with a time phase applied to the time data.

    Parameters
    ----------
    trace       : (x, y) tuple of numpy arrays (time, voltage)
    time_shift  : Amount to shift the time by

    Returns
    -------
    A shifted trace
    """
    t, v = trace
    t_shifted = t + time_shift

    return (t_shifted, v)


def decode_ctrl(traces, vthresh=0.9):
    """Convert 6 CTRL bit traces into a single integer waveform."""
    time = traces["CTRL0"][0]
    ctrl_int = np.zeros(len(time))
    for i in range(6):
        _, v = traces[f"CTRL{i}"]
        ctrl_int += (v > vthresh).astype(float) * (1 << i)
    return (time, ctrl_int)


def decode_q(traces, vthresh=0.9, bits = 6):
    """Convert 6 Q bit traces into a single integer waveform."""
    time = traces["Q0_node"][0]
    ctrl_int = np.zeros(len(time))
    for i in range(bits):
        _, v = traces[f"Q{i}_node"]
        ctrl_int += (v > vthresh).astype(float) * (1 << i)
    return (time, ctrl_int)