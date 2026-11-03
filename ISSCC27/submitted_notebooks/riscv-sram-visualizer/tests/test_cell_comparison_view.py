"""Reusable comparison built from both existing view implementations."""

from io import BytesIO

import matplotlib
matplotlib.use("Agg")

from riscv_memory_visualizer.memory.sram6t import SRAMCell6T
from riscv_memory_visualizer.memory.sram8t import SRAMCell8T
from riscv_memory_visualizer.visualization.cell_comparison_view import SRAMCellComparisonView


def test_comparison_draws_both_without_mutation_or_artist_growth():
    six, eight = SRAMCell6T(), SRAMCell8T()
    six.set_word_line(1)
    eight.set_selected(1)
    view = SRAMCellComparisonView()
    figure = view.draw(six, eight)
    axes = (view.view6t.axes, view.view8t.axes, view.axes)
    artists = [tuple(ax.get_children()) for ax in axes]
    for value in (1, 0, 1):
        six.write(value)
        eight.write(1-value)
        before = six.get_state(), eight.get_state()
        assert view.update(six, eight) is figure
        assert before == (six.get_state(), eight.get_state())
        assert artists == [tuple(ax.get_children()) for ax in axes]
        assert view.view6t.labels["Q"].get_text() == f"Q = {value}"
        assert view.view8t.labels["Q"].get_text() == f"Q = {1-value}"
    labels = " ".join(c.get_text().get_text() for c in view.table.get_celld().values())
    assert "connectivity unknown" in labels and "physical path unspecified" in labels
    image = BytesIO()
    figure.savefig(image, format="png")
    assert image.getvalue().startswith(b"\x89PNG")
