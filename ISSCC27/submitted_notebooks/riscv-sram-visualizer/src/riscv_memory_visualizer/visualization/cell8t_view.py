"""Read-only abstract 8T view, deliberately without unverified circuit wiring."""

from textwrap import fill

from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from riscv_memory_visualizer.memory.sram8t import SRAMCell8T, SRAMCell8TState
from riscv_memory_visualizer.simulation.events import MemoryEvent


class SRAMCell8TView:
    """A logical-state block, not an eight-device schematic.

    No transistor symbols, supplies or read/write wires are drawn because the
    available source does not establish them. All artists are reused.
    """

    def __init__(self, *, figure=None) -> None:
        self.figure = figure if figure is not None else Figure(figsize=(12, 8), facecolor="white")
        self.axes = self.figure.add_axes((.05, .16, .90, .72))
        self.axes.set(xlim=(0, 10), ylim=(0, 8))
        self.axes.axis("off")
        self.title = self.figure.suptitle("8T SRAM | ABSTRACT PLACEHOLDER", fontsize=17)
        self.storage = Rectangle((1.5, 3), 7, 3, facecolor="#f0f4f8", edgecolor="#52606d", linewidth=2)
        self.axes.add_patch(self.storage)
        self.axes.text(5, 5.5, "Logical storage assumption", ha="center", fontsize=14)
        self.labels = {
            "Q": self.axes.text(3.3, 4.5, "Q = —", ha="center", fontsize=17),
            "Q_bar": self.axes.text(6.7, 4.5, "Q_bar = —", ha="center", fontsize=17),
            "selected": self.axes.text(5, 3.5, "Selection: —", ha="center", fontsize=12),
        }
        self.axes.text(5, 6.8, "8 transistors: count specified in brief\nRoles and connectivity: NOT SPECIFIED",
                       ha="center", fontsize=13, color="#8a4b08")
        self.axes.text(5, 1.8, "Read: return stored bit (software operation)\n"
                       "Write: replace stored bit (software operation)\n"
                       "Physical read/write paths and signals: unknown",
                       ha="center", fontsize=12, linespacing=1.6)
        self.explanation = self.figure.text(.06, .10, "", fontsize=10, va="top")
        self.figure.text(.06, .025, "No verified 8T topology available. This is not a transistor schematic.",
                         fontsize=11, color="#8a4b08")

    def draw(self, cell: SRAMCell8T) -> Figure:
        """Observe a live abstract cell and return the reusable figure."""
        return self.render(cell.get_state())

    def update(self, cell: SRAMCell8T) -> Figure:
        """Refresh existing artists without accessing or changing cell storage."""
        return self.draw(cell)

    def render(self, state: SRAMCell8TState) -> Figure:
        """Render an immutable abstract snapshot; reject other cell architectures."""
        return self._render(state, "Logical selection is software metadata, not a physical word line.")

    def render_event(self, event: MemoryEvent) -> Figure:
        """Display the event's historical 8T snapshot, never the current live cell."""
        if not isinstance(event.cell_state, SRAMCell8TState):
            raise ValueError("Event must contain an abstract 8T cell snapshot.")
        location = f"Cell ({event.row}, {event.column}). " if event.row is not None and event.column is not None else ""
        return self._render(event.cell_state, location + event.description)

    def _render(self, state: SRAMCell8TState, description: str) -> Figure:
        if not isinstance(state, SRAMCell8TState):
            raise ValueError("Expected an abstract 8T cell snapshot.")
        self.labels["Q"].set_text(f"Q = {state.q}")
        self.labels["Q_bar"].set_text(f"Q_bar = {state.q_bar}")
        self.labels["selected"].set_text(f"Logical selection = {state.selected} (software gate)")
        self.storage.set_facecolor("#dceef6" if state.selected else "#f0f4f8")
        self.explanation.set_text(fill(description, 115))
        self.figure.canvas.draw_idle()
        return self.figure
