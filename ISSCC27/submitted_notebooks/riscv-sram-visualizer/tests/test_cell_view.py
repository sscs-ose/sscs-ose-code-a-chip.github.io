"""Headless view checks using labels and artist identity, not pixels."""
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
import pytest

from riscv_memory_visualizer.memory.sram6t import SRAMCell6T
from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.events import MemoryEventType
from riscv_memory_visualizer.visualization.cell_view import SRAMCell6TView


@pytest.mark.parametrize("initial", [0, 1])
def test_render_update_and_no_model_mutation(initial):
    cell = SRAMCell6T(initial)
    view = SRAMCell6TView()
    before = cell.get_state()
    figure = view.draw(cell)
    assert cell.get_state() == before
    artists = tuple(view.axes.get_children())
    for value in (1, 0, 1):
        cell.set_word_line(1)
        cell.write(value)
        before = cell.get_state()
        assert view.update(cell) is figure
        assert tuple(view.axes.get_children()) == artists
        assert cell.get_state() == before
        for name, expected in dict(Q=value, Q_bar=1-value, WL=1, BL=value, BL_bar=1-value).items():
            assert view.labels[name].get_text() == f"{name} = {expected}"
    cell.set_word_line(0)
    view.update(cell)
    assert "IDLE" in view.title.get_text()
    assert view.lines["WL"].get_linestyle() == "--"
    output = BytesIO()
    figure.savefig(output, format="png")
    assert output.getvalue().startswith(b"\x89PNG")


@pytest.mark.parametrize("kind", [MemoryEventType.SRAM_READ, MemoryEventType.SRAM_WRITE, MemoryEventType.WORD_LINE_ACTIVE])
def test_historical_event_rendering(kind):
    array = SRAMArray(1, 1)
    engine = MemoryEventEngine(array)
    engine.write(0, 1)
    engine.read(0)
    event = next(e for e in engine.timeline.events() if e.event_type == kind)
    array.write(0, 0, 0)
    before = array.get_cell(0, 0).get_state()
    view = SRAMCell6TView()
    view.render_event(event)
    canvas = FigureCanvasAgg(view.figure)
    canvas.draw()
    renderer = canvas.get_renderer()
    assert view.explanation.get_window_extent(renderer).y0 > view.figure.texts[-1].get_window_extent(renderer).y1
    assert view.labels["Q"].get_text() == f"Q = {event.cell_state.q}"
    assert "CELL (0, 0)" in view.title.get_text()
    assert array.get_cell(0, 0).get_state() == before
    assert ("READ" if kind == MemoryEventType.SRAM_READ else
            "WRITE" if kind == MemoryEventType.SRAM_WRITE else "WORD LINE ACTIVE") in view.title.get_text()


def test_snapshotless_event_rejected_without_changing_view():
    engine = MemoryEventEngine(SRAMArray(1, 1))
    engine.read(0)
    view = SRAMCell6TView()
    title = view.title.get_text()
    with pytest.raises(ValueError, match="no cell snapshot"):
        view.render_event(engine.timeline.events()[0])
    assert view.title.get_text() == title
