"""Reusable digital timing diagram; CPU cycles and event order are separate axes."""

from textwrap import shorten

from matplotlib.figure import Figure

from riscv_memory_visualizer.simulation.signals import SimulationTrace, SignalSeries


class WaveformView:
    """Render cycle observations above a detail panel for one cycle's events.

    Default: last 12 CPU cycles and the latest event group in that window.
    Setup events retain cycle=None. Event positions are sequence numbers with
    no physical duration or fractional-cycle interpretation. Text pools and
    line artists are bounded and reused; complete history stays in the trace.
    """

    CYCLE_NAMES = ("WL", "BL", "BL_bar", "Q", "Q_bar", "SELECTED", "READ", "WRITE",
                   "MEMORY_ACCESS", "ROW_SELECT", "COLUMN_SELECT", "CELL",
                   "IF", "ID_EX", "MEM_WB", "PC", "CYCLE")
    EVENT_NAMES = ("WL", "BL", "BL_bar", "Q", "Q_bar", "SELECTED", "READ", "WRITE", "CELL")
    MAX_LABELS = 12

    def __init__(self) -> None:
        self.figure = Figure(figsize=(16, 15), facecolor="white")
        self.axes = self.figure.add_axes((.13, .47, .83, .44))
        self.event_axes = self.figure.add_axes((.13, .16, .83, .23))
        self.title = self.figure.suptitle("Digital timing | no observations", fontsize=16)
        self.caption = self.figure.text(.13, .945,
            "Cycle panel: observed boundary state; READ/WRITE mark occurrences. Cell identity is shown in CELL.", fontsize=10)
        self.figure.text(.13, .02,
            "Logical simulation state and event timing, not an analog SPICE waveform.\n"
            "? = unknown/unobserved; N/A = unavailable in the model. Step segments hold observations, not physical delays.", fontsize=10)
        self.lines, self.labels, self.notes = self._build(self.axes, self.CYCLE_NAMES)
        self.event_lines, self.event_labels, self.event_notes = self._build(self.event_axes, self.EVENT_NAMES)
        self.marker = self.axes.axvline(0, color="#b45309", linewidth=1.2, linestyle="--")
        self.marker.set_visible(False)
        self.event_title = self.event_axes.set_title("No memory events recorded", loc="left", fontsize=11)
        self.axes.set_xlabel("CPU cycle (boundary observation)")
        self.event_axes.set_xlabel("Event insertion order within the displayed cycle — NOT additional CPU cycles")

    def _build(self, ax, names):
        lines, labels, notes = {}, {}, {}
        for index, name in enumerate(names):
            base = len(names) - index - 1
            lines[name], = ax.plot([], [], drawstyle="steps-post", color="#176b91", linewidth=1.4)
            labels[name] = [ax.text(0, base+.25, "", fontsize=8, va="center", clip_on=True)
                            for _ in range(self.MAX_LABELS)]
            notes[name] = ax.text(.01, base+.25, "", transform=ax.get_yaxis_transform(),
                                 fontsize=9, color="#666666", va="center")
            if name in ("WL", "BL", "BL_bar", "Q", "Q_bar", "SELECTED", "READ", "WRITE", "MEMORY_ACCESS"):
                for value in (0, 1):
                    ax.text(-.008, base+.6*value, str(value), transform=ax.get_yaxis_transform(),
                            ha="right", va="center", fontsize=6, color="#666666")
        ax.set_yticks([len(names)-i-1+.3 for i in range(len(names))], labels=names)
        ax.set_ylim(-.2, len(names))
        ax.set_xlim(-.2, 1)
        ax.grid(axis="x", color="#dce1e5", linewidth=.7)
        ax.tick_params(axis="y", length=0)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        return lines, labels, notes

    @staticmethod
    def _render_lane(series: SignalSeries, samples, base, line, labels, note, *, event=False):
        for label in labels:
            label.set_visible(False)
        note.set_text("")
        line.set_data([], [])
        if not series.available:
            note.set_text("N/A — not modeled")
            return
        if not samples:
            note.set_text("No observations")
            return
        xs = [s.event_order if event else s.cycle for s in samples]
        if series.kind == "binary":
            ys = [float("nan") if s.value is None else base + .6*s.value for s in samples]
            # A short display tail makes a single observation visible, without adding a sample/cycle.
            line.set_data(xs + [xs[-1]+.8], ys + [ys[-1]])
            chosen = [(x, s) for x, s in zip(xs, samples) if s.value is None][-len(labels):]
        else:
            line.set_data(xs + [xs[-1]+.8], [base+.05]*(len(xs)+1))
            chosen = list(zip(xs, samples))
            if len(chosen) > len(labels):
                chosen = [chosen[round(i*(len(chosen)-1)/(len(labels)-1))] for i in range(len(labels))]
        for label, (x, sample) in zip(labels, chosen):
            value = "?" if sample.value is None else str(sample.value)
            label.set_text(shorten(value, width=22, placeholder="…"))
            label.set_position((x+.03, base+.3))
            label.set_visible(True)

    def draw(self, trace: SimulationTrace, *, start_cycle: int | None = None,
             end_cycle: int | None = None, event_cycle: int | None | str = "latest") -> Figure:
        """Render a detached snapshot; event_cycle=None explicitly selects setup events."""
        end = trace.current_cycle if end_cycle is None else end_cycle
        start = max(0, end-11) if start_cycle is None else start_cycle
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            raise ValueError("Cycle window must contain non-negative integers with start <= end.")
        if event_cycle != "latest" and event_cycle is not None and (type(event_cycle) is not int or event_cycle < 0):
            raise ValueError("event_cycle must be 'latest', None or a non-negative integer.")
        self.title.set_text(f"Digital timing | {trace.architecture} | Current cycle: {trace.current_cycle}")
        series_by_name = {s.name: s for s in trace.cycle_traces}
        for i, name in enumerate(self.CYCLE_NAMES):
            series = series_by_name[name]
            # Include a preceding observation for a clipped step at the window boundary.
            preceding = [s for s in series.samples if s.cycle < start]
            samples = tuple(preceding[-1:]) + tuple(s for s in series.samples if start <= s.cycle <= end)
            self._render_lane(series, samples, len(self.CYCLE_NAMES)-i-1,
                              self.lines[name], self.labels[name], self.notes[name])
        self.axes.set_xlim(start-.15, end+.85)
        ticks = list(range(start, end+1, max(1, (end-start)//11+1)))
        self.axes.set_xticks(ticks)
        self.marker.set_xdata([trace.current_cycle, trace.current_cycle])
        self.marker.set_visible(bool(series_by_name["CYCLE"].samples) and start <= trace.current_cycle <= end)

        if event_cycle == "latest":
            candidates = [e for e in trace.events if e.event.cycle is not None and
                          (not series_by_name["CYCLE"].samples or start <= e.event.cycle <= end)]
            event_cycle = candidates[-1].event.cycle if candidates else None
        events = [e for e in trace.events if e.event.cycle == event_cycle]
        shown = events[-self.MAX_LABELS:]
        orders = {e.order for e in shown}
        by_name = {s.name: s for s in trace.event_traces}
        for i, name in enumerate(self.EVENT_NAMES):
            series = by_name[name]
            samples = tuple(s for s in series.samples if s.event_order in orders)
            self._render_lane(series, samples, len(self.EVENT_NAMES)-i-1,
                              self.event_lines[name], self.event_labels[name], self.event_notes[name], event=True)
        if shown:
            group = f"Cycle {event_cycle}" if event_cycle is not None else "Setup / unknown CPU cycle"
            self.event_title.set_text(f"{group} — ordered events ({len(shown)} of {len(events)} shown); spacing is not duration")
            self.event_axes.set_xlim(shown[0].order-.15, shown[-1].order+.85)
            self.event_axes.set_xticks([e.order for e in shown],
                labels=[f"#{e.order} {e.event.event_type.name}" for e in shown], rotation=35, ha="right", fontsize=8)
        else:
            self.event_title.set_text("No memory events in the selected cycle / setup group")
            self.event_axes.set_xlim(0, 1)
            self.event_axes.set_xticks([])
        self.figure.canvas.draw_idle()
        return self.figure

    def update(self, trace: SimulationTrace, **kwargs) -> Figure:
        """Refresh existing artists; keyword arguments select the draw window."""
        return self.draw(trace, **kwargs)
