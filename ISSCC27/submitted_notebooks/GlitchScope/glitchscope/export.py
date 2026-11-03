"""Export glitch-accurate activity: VCD (waveform viewing) and SAIF (OpenSTA read_saif)."""
from __future__ import annotations

from collections import defaultdict


class ActivityRecorder:
    """Collects per-cycle traces (analyze(on_trace=...)) on an absolute time axis."""

    def __init__(self, network, period_fs, t0_fs=100_000, initial=None):
        self.net, self.period, self.t0 = network, int(period_fs), t0_fs
        self.changes = defaultdict(list)      # net -> [(abs_time_fs, value)]
        self.initial = dict(initial or {})
        self.ncycles = 0

    def __call__(self, k, res):
        base = (k - 1) * self.period - self.t0
        for e in res["trace"]:
            self.changes[e.net].append((base + e.time_fs, e.new_value))
        self.ncycles = max(self.ncycles, k)

    def write_vcd(self, path, init_values, timescale="1fs"):
        nets = sorted(set(self.changes) | set(init_values))
        ids = {n: _vcd_id(i) for i, n in enumerate(nets)}
        ev = sorted((t, ids[n], v) for n, ch in self.changes.items() for t, v in ch)
        with open(path, "w") as fh:
            fh.write(f"$timescale {timescale} $end\n$scope module glitchscope $end\n")
            for n in nets:
                fh.write(f"$var wire 1 {ids[n]} {n.replace(' ', '_')} $end\n")
            fh.write("$upscope $end\n$enddefinitions $end\n#0\n$dumpvars\n")
            for n in nets:
                fh.write(f"{init_values.get(n, 0)}{ids[n]}\n")
            fh.write("$end\n")
            last = None
            for t, i, v in ev:
                if t != last:
                    fh.write(f"#{max(0, t)}\n"); last = t
                fh.write(f"{v}{i}\n")

    def net_activity(self, init_values):
        """{net: (T0_fs, T1_fs, TC)} over the recorded window."""
        dur = self.ncycles * self.period
        act = {}
        for n in set(self.changes) | set(init_values):
            v, t_prev, t1 = init_values.get(n, 0), 0, 0
            ch = sorted(self.changes.get(n, []))
            for t, nv in ch:
                t = max(0, min(dur, t))
                if v == 1:
                    t1 += t - t_prev
                v, t_prev = nv, t
            if v == 1:
                t1 += dur - t_prev
            act[n] = (dur - t1, t1, len(ch))
        return act

    def write_saif(self, path, init_values, design="top", instance="top", flops=()):
        """SAIF in the form OpenSTA's read_saif annotates: NET entries are resolved as
        pins of the enclosing instance, so each leaf cell gets its own INSTANCE block
        listing its pins; top-level ports are listed under the top instance.
        Times in ps (OpenSTA accepts us/ns/ps only)."""
        act = self.net_activity(init_values)
        dur_ps = self.ncycles * self.period // 1000
        esc = lambda n: n.replace("[", "\\[").replace("]", "\\]")

        def dur(net):
            t0, t1, tc = act.get(net, (self.ncycles * self.period, 0, 0))
            t1p = int(round(t1 / 1000))
            return f"(T0 {dur_ps - t1p}) (T1 {t1p}) (TX 0) (TC {tc})"

        L = ['(SAIFILE', '(SAIFVERSION "2.0")', '(DIRECTION "backward")', f'(DESIGN "{design}")',
             '(DIVIDER / )', '(TIMESCALE 1 ps)', f'(DURATION {dur_ps})', f'(INSTANCE {instance}']
        ports = list(self.net.primary_inputs) + list(self.net.primary_outputs)
        L.append('  (NET')
        L += [f'    ({esc(n)} {dur(n)})' for n in dict.fromkeys(ports)]
        L.append('  )')
        for c in self.net.cells:
            pins = dict(c.inputs); pins[c.library_output_pin or "Y"] = c.output
            L.append(f'  (INSTANCE {c.name} (NET')
            L += [f'    ({p} {dur(n)})' for p, n in pins.items()]
            L.append('  ))')
        for f in flops:
            L.append(f'  (INSTANCE {f.name} (NET')
            L += [f'    ({f.d_pin} {dur(f.d)})'] + [f'    ({pin} {dur(net)})' for net, pin, _ in f.outputs]
            L.append('  ))')
        L += [')', ')']
        open(path, "w").write("\n".join(L) + "\n")


def _vcd_id(i):
    chars = [chr(c) for c in range(33, 127)]
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, len(chars))
        s = chars[r] + s
    return s
