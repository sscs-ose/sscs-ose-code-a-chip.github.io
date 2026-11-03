"""Read-only Matplotlib visualization of logical SRAM array organization."""

from textwrap import fill

from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.simulation.events import MemoryEvent, MemoryEventType


class SRAMArrayView:
    """Display live array state without accessing or changing stored data.

    draw/update reuse the figure and artists. A dimension change rebuilds
    artists on the same axes. No memory values are cached in the view.
    render_event requires matching live selection and (when present) cell
    snapshot/value; stale events are rejected rather than replayed as state.
    This is an organization diagram, not shared electrical bit-line modeling.
    """

    def __init__(self) -> None:
        self.figure = Figure(figsize=(12, 7), facecolor="white")
        self.axes = self.figure.add_axes((.03, .17, .94, .72))
        self.title = self.figure.suptitle("SRAM array | no state supplied", fontsize=17)
        self.explanation = self.figure.text(.05, .12, "", fontsize=10, va="top")
        self.figure.text(.05, .025, "Blue: active row / selected column. Orange border: selected cell. Logical values only.", fontsize=10)
        self._shape = None
        self.cell_patches = {}
        self.value_labels = {}
        self.row_labels = []
        self.column_labels = []
        self.word_lines = []
        self.word_line_labels = []

    def _build(self, rows: int, columns: int) -> None:
        """Create a dimension-dependent layout, retaining the Figure and Axes."""
        ax = self.axes
        ax.clear()
        ax.set(xlim=(-4, columns+3.3), ylim=(rows+.5, -1.5), aspect="equal")
        ax.axis("off")
        self.figure.set_size_inches(max(11, columns*.7+6), max(6, rows*.65+3))
        self.cell_patches.clear()
        self.value_labels.clear()
        self.row_labels.clear()
        self.column_labels.clear()
        self.word_lines.clear()
        self.word_line_labels.clear()
        ax.add_patch(Rectangle((-3.7, 0), 1.15, rows, facecolor="#f0f4f8", edgecolor="#52606d"))
        self.decoder_label = ax.text(-3.12, rows/2, "Row\ndecoder", ha="center", va="center", fontsize=10)
        for r in range(rows):
            self.row_labels.append(ax.text(-.25, r+.65, f"R{r}", ha="right", fontsize=11))
            line, = ax.plot([-2.55, columns], [r+.18]*2, color="#aab4be", zorder=1)
            self.word_lines.append(line)
            self.word_line_labels.append(ax.text(-2.4, r+.6, "", fontsize=9))
            for c in range(columns):
                patch = Rectangle((c+.08, r+.3), .84, .62, facecolor="white", edgecolor="#aab4be", zorder=2)
                ax.add_patch(patch)
                self.cell_patches[r, c] = patch
                self.value_labels[r, c] = ax.text(c+.5, r+.61, "", ha="center", va="center", fontsize=13)
        for c in range(columns):
            self.column_labels.append(ax.text(c+.5, -.65, f"C{c}", ha="center", fontsize=11))
            ax.annotate("", xy=(c+.5, .05), xytext=(c+.5, -.4),
                        arrowprops=dict(arrowstyle="->", color="#aab4be"))
        self.panel = ax.text(columns+.45, 0, "", va="top", fontsize=11, linespacing=1.8)
        self._shape = (rows, columns)

    def draw(self, array: SRAMArray) -> Figure:
        """Render current values and selection without inferring an operation."""
        description = ("Rows use word lines; columns identify the accessed cell and its bit-line pair."
                       if array.uses_word_line else
                       "Rows show software selection only. Abstract cell: physical word/bit lines and read/write paths unspecified.")
        return self._render(array, "STATE", description)

    def update(self, array: SRAMArray) -> Figure:
        """Refresh the existing drawing from live array state."""
        return self.draw(array)

    def render_event(self, array: SRAMArray, event: MemoryEvent) -> Figure:
        """Annotate a matching event; reject stale/missing coordinates or data.

        Events contain only a cell snapshot, not historical array contents.
        Render immediately after the operation; use the cell view for isolated
        historical cell snapshots. Rendering never selects or accesses cells.
        """
        cell = array.get_cell(event.row, event.column)
        if (array.selected_row, array.selected_column) != (event.row, event.column):
            raise ValueError("Event selection does not match the live array.")
        if event.cell_state is not None and event.cell_state != cell.get_state():
            raise ValueError("Event cell snapshot does not match the live array.")
        if event.event_type in (MemoryEventType.SRAM_READ, MemoryEventType.SRAM_WRITE):
            if event.value != cell.q:
                raise ValueError("Event value does not match the live array.")
        status = {MemoryEventType.SRAM_READ: "READ", MemoryEventType.SRAM_WRITE: "WRITE"}.get(
            event.event_type, event.event_type.name.replace("_", " "))
        return self._render(array, status, event.description)

    def _render(self, array: SRAMArray, status: str, description: str) -> Figure:
        """Read one snapshot and apply it to display artists only."""
        state = array.get_state()
        if self._shape != (state.rows, state.columns):
            self._build(state.rows, state.columns)
        for r in range(state.rows):
            active = bool(state.word_lines[r])
            self.word_lines[r].set_color("#176b91" if active else "#aab4be")
            self.word_lines[r].set_linewidth(3 if active else 1)
            row_label = f"WL{r}" if array.uses_word_line else f"SEL{r}"
            self.word_line_labels[r].set_text(f"{row_label} = {state.word_lines[r]}" + (" ACTIVE" if active else ""))
            self.row_labels[r].set_fontweight("bold" if r == state.selected_row else "normal")
            for c in range(state.columns):
                selected = (r, c) == (state.selected_row, state.selected_column)
                patch = self.cell_patches[r, c]
                patch.set_facecolor("#dceef6" if active or c == state.selected_column else "white")
                patch.set_edgecolor("#b45309" if selected else "#aab4be")
                patch.set_linewidth(3 if selected else 1)
                self.value_labels[r, c].set_text(str(state.cells[r][c]))
        for c, label in enumerate(self.column_labels):
            label.set_text(f"C{c}" + (" *" if c == state.selected_column else ""))
            label.set_fontweight("bold" if c == state.selected_column else "normal")
        self.decoder_label.set_text(f"Row\ndecoder\n\nR = {state.selected_row if state.selected_row is not None else '-'}")
        selected = state.selected_row is not None and state.selected_column is not None
        value = state.cells[state.selected_row][state.selected_column] if selected else "-"
        location = f"({state.selected_row}, {state.selected_column})" if selected else "-"
        self.panel.set_text(f"SRAM ARRAY\nSize: {state.rows} x {state.columns}\n\nRow: {state.selected_row}\nColumn: {state.selected_column}\nSelected: {location}\nValue: {value}\n\nOperation: {status}")
        self.title.set_text(f"SRAM array | {array.architecture_name} | {status}")
        self.explanation.set_text(fill(description, 125))
        self.figure.canvas.draw_idle()
        return self.figure
