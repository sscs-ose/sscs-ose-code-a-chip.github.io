"""Reusable Matplotlib view of logical 6T cell state; never performs access."""

from textwrap import fill

from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from riscv_memory_visualizer.memory.sram6t import SRAMCell6T, SRAMCellState
from riscv_memory_visualizer.simulation.events import MemoryEvent, MemoryEventType


class SRAMCell6TView:
    """Conceptual six-device schematic with stable artists and no GUI requirement.

    draw/update inspect a live cell; render accepts an immutable snapshot.
    render_event uses only the event's historical snapshot and rejects events
    without one. Methods return the same Figure for display or savefig.
    Device boxes identify transistor roles, not electrical device geometry.
    M1-M6 are local labels, not a claimed lecture numbering convention.
    """

    def __init__(self, *, figure=None) -> None:
        # Optional Figure/SubFigure lets the comparison reuse this schematic.
        self.figure = figure if figure is not None else Figure(figsize=(12, 8), facecolor="white")
        self.axes = self.figure.add_axes((0.03, 0.12, 0.94, 0.8))
        ax = self.axes
        ax.set(xlim=(0, 12), ylim=(0, 9))
        ax.set_aspect("equal")
        ax.axis("off")
        self.labels = {}
        self.lines = {}
        self.access_devices = []
        self.title = self.figure.suptitle("6T SRAM cell | no state supplied", fontsize=17)
        self.explanation = self.figure.text(0.06, 0.085, "", fontsize=10, va="top")
        self.figure.text(0.06, 0.015, "Logical model • no currents or voltage simulation • M1–M6: local labels", fontsize=9, color="#52606d")

        def line(name, x, y, **kwargs):
            artist, = ax.plot(x, y, color="#52606d", linewidth=1.8, **kwargs)
            self.lines[name] = artist

        def label(name, x, y):
            self.labels[name] = ax.text(x, y, name, ha="center", fontsize=12,
                                       bbox=dict(facecolor="white", edgecolor="none", pad=2))

        # Shared supplies and the two complementary storage branches.
        line("vdd", [3, 7], [7.5, 7.5])
        line("gnd", [3, 7], [1.4, 1.4])
        ax.text(5, 7.7, "VDD", ha="center", fontsize=11)
        ax.text(5, 1.05, "GND", ha="center", fontsize=11)
        for x, name in ((3, "Q"), (7, "Q_bar")):
            line(name, [x, x], [1.4, 7.5])
            ax.plot(x, 4.5, "o", color="#243b53", markersize=6)
            label(name, x, 4.85)
        # Explicit cross-coupled gate buses: each output drives the opposite pair.
        line("left_gates", [4, 4], [2.8, 6.3])
        line("right_gates", [6, 6], [2.8, 6.3])
        for y in (2.8, 6.3):
            line(f"gate_left_{y}", [3.65, 4], [y, y])
            line(f"gate_right_{y}", [6, 6.35], [y, y])
        line("feedback_q", [3, 4.7, 6], [4.5, 3.8, 3.8])
        line("feedback_qbar", [7, 5.3, 4], [4.5, 5.2, 5.2])
        ax.text(5, 0.35, "Cross-coupled inverters maintain complementary Q / Q_bar", ha="center", fontsize=10)
        for x, y, text in ((3, 6.3, "M1\nPMOS"), (3, 2.8, "M2\nNMOS"),
                           (7, 6.3, "M3\nPMOS"), (7, 2.8, "M4\nNMOS"),
                           (1.65, 4.5, "M5\naccess"), (8.35, 4.5, "M6\naccess")):
            patch = Rectangle((x-.65, y-.5), 1.3, 1, facecolor="#f0f4f8", edgecolor="#52606d", zorder=3)
            ax.add_patch(patch)
            ax.text(x, y, text, ha="center", va="center", fontsize=10, zorder=4)
            if "access" in text:
                self.access_devices.append(patch)
        for x, name in ((.5, "BL"), (9.5, "BL_bar")):
            line(name, [x, x], [2, 7.6])
            label(name, x, 7.9)
        line("left_path", [.5, 3], [4.5, 4.5])
        line("right_path", [7, 9.5], [4.5, 4.5])
        line("WL", [1.65, 8.35], [8.5, 8.5])
        line("wl_left", [1.65, 1.65], [8.5, 5])
        line("wl_right", [8.35, 8.35], [8.5, 5])
        label("WL", 5, 8.7)
        self.panel = ax.text(10, 6.9, "", va="top", fontsize=11, linespacing=1.7)

    def draw(self, cell: SRAMCell6T) -> Figure:
        """Inspect a live cell without reading or writing it."""
        return self.render(cell.get_state())

    def update(self, cell: SRAMCell6T) -> Figure:
        """Refresh existing artists from a live cell."""
        return self.draw(cell)

    def render(self, state: SRAMCellState) -> Figure:
        """Render stored signals without inferring an unobserved read/write."""
        status = "WORD LINE ACTIVE" if state.word_line else "IDLE"
        return self._render(state, status, "WL controls both access transistors. BL / BL_bar carry logical data.")

    def render_event(self, event: MemoryEvent) -> Figure:
        """Render recorded signals, never substitute a newer live cell state."""
        if event.cell_state is None:
            raise ValueError("Event has no cell snapshot; render a state explicitly instead.")
        if not isinstance(event.cell_state, SRAMCellState):
            raise ValueError("Event does not contain a 6T cell snapshot.")
        status = {
            MemoryEventType.SRAM_READ: "READ",
            MemoryEventType.SRAM_WRITE: "WRITE",
            MemoryEventType.WORD_LINE_ACTIVE: "WORD LINE ACTIVE",
        }.get(event.event_type, event.event_type.name.replace("_", " "))
        if event.row is not None and event.column is not None:
            status += f" | CELL ({event.row}, {event.column})"
        return self._render(event.cell_state, status, event.description)

    def _render(self, state: SRAMCellState, status: str, description: str) -> Figure:
        """Update text and logical highlighting while retaining every artist."""
        values = dict(Q=state.q, Q_bar=state.q_bar, WL=state.word_line,
                      BL=state.bit_line, BL_bar=state.bit_line_bar)
        for name, value in values.items():
            self.labels[name].set_text(f"{name} = {value}")
            self.lines[name].set_color("#176b91" if value else "#77838f")
        active = bool(state.word_line)
        for name in ("wl_left", "wl_right", "left_path", "right_path", "WL"):
            self.lines[name].set_color("#176b91" if active else "#9aa5b1")
            self.lines[name].set_linestyle("-" if active else "--")
        for patch in self.access_devices:
            patch.set_facecolor("#cce8f4" if active else "#f0f4f8")
        self.title.set_text(f"6T SRAM cell | {status}")
        self.panel.set_text("LOGICAL STATE\n" + "\n".join(f"{k}: {v}" for k, v in values.items())
                            + "\n\nAccess\n" + ("ACTIVE" if active else "INACTIVE"))
        self.explanation.set_text(fill(description, 130))
        self.figure.canvas.draw_idle()
        return self.figure
