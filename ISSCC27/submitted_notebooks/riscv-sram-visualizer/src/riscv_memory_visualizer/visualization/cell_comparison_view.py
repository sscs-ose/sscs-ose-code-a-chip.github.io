"""Side-by-side existing 6T schematic and explicitly abstract 8T fallback."""

from matplotlib.figure import Figure

from riscv_memory_visualizer.memory.sram6t import SRAMCell6T
from riscv_memory_visualizer.memory.sram8t import SRAMCell8T
from riscv_memory_visualizer.visualization.cell_view import SRAMCell6TView
from riscv_memory_visualizer.visualization.cell8t_view import SRAMCell8TView


class SRAMCellComparisonView:
    """Reuse both cell views; inspect independent supplied cells without access.

    Facts describe the project models and their limits, not performance.
    The comparison owns no simulation cells and does not synchronize values.
    """

    def __init__(self) -> None:
        self.figure = Figure(figsize=(20, 10), facecolor="white")
        grid = self.figure.add_gridspec(2, 2, height_ratios=(4, 1.3),
                                       left=.02, right=.98, bottom=.03, top=.96)
        self.view6t = SRAMCell6TView(figure=self.figure.add_subfigure(grid[0, 0]))
        self.view8t = SRAMCell8TView(figure=self.figure.add_subfigure(grid[0, 1]))
        self.axes = self.figure.add_subplot(grid[1, :])
        self.axes.axis("off")
        self.table = self.axes.table(
            colLabels=["Comparison", "6T — existing project model", "8T — abstract fallback"],
            cellText=[
                ["Transistor count", "6 (conceptual devices drawn)", "8 (brief only; connectivity unknown)"],
                ["Storage", "Q / Q_bar, cross-coupled inverters", "Q / Q_bar logical assumption"],
                ["Read organization", "WL gates shared BL / BL_bar access", "Return Q; physical path unspecified"],
                ["Write organization", "WL gates shared BL / BL_bar access", "Store bit; physical path unspecified"],
                ["Scope", "Behavioral; no analog simulation", "Software selection; no circuit claims"],
            ], loc="center", cellLoc="left", colWidths=[.16, .40, .44])
        self.table.auto_set_font_size(False)
        self.table.set_fontsize(11)
        self.table.scale(1, 1.8)

    def draw(self, cell6t: SRAMCell6T, cell8t: SRAMCell8T) -> Figure:
        """Observe both supplied cells and return the shared comparison figure."""
        self.view6t.update(cell6t)
        self.view8t.update(cell8t)
        self.figure.canvas.draw_idle()
        return self.figure

    def update(self, cell6t: SRAMCell6T, cell8t: SRAMCell8T) -> Figure:
        """Refresh both existing views without modifying either model."""
        return self.draw(cell6t, cell8t)
