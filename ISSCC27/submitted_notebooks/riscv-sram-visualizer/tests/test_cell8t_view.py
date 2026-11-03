"""Read-only abstract views, honest labels, and stable headless rendering."""

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import pytest

from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.memory.sram6t import SRAMCell6T
from riscv_memory_visualizer.memory.sram8t import SRAMCell8T
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.events import MemoryEventType as T
from riscv_memory_visualizer.visualization.cell8t_view import SRAMCell8TView
from riscv_memory_visualizer.visualization.cell_view import SRAMCell6TView
from riscv_memory_visualizer.visualization.array_view import SRAMArrayView


def test_live_state_and_artist_reuse():
    cell = SRAMCell8T()
    view = SRAMCell8TView()
    figure = view.draw(cell)
    artists = tuple(view.axes.get_children())
    for value in (1, 0, 1):
        cell.set_selected(1)
        cell.write(value)
        before = cell.get_state()
        assert view.update(cell) is figure
        assert cell.get_state() == before
        assert tuple(view.axes.get_children()) == artists
        assert view.labels["Q"].get_text() == f"Q = {value}"
        assert view.labels["Q_bar"].get_text() == f"Q_bar = {1-value}"
    assert "ABSTRACT PLACEHOLDER" in view.title.get_text()
    assert "software gate" in view.labels["selected"].get_text()
    assert len(view.axes.patches) == 1  # One logical block, not fake devices.
    assert not view.axes.lines
    image = BytesIO()
    figure.savefig(image, format="png")
    assert image.getvalue().startswith(b"\x89PNG")


def test_historical_snapshot_and_wrong_architecture_rejection():
    engine = MemoryEventEngine(SRAMArray(1, 1, cell_type=SRAMCell8T))
    engine.write(0, 1)
    event = next(e for e in engine.timeline.events() if e.event_type == T.SRAM_WRITE)
    engine.write(0, 0)
    view = SRAMCell8TView()
    view.render_event(event)
    assert view.labels["Q"].get_text() == "Q = 1"
    assert engine.memory.get_cell(0, 0).q == 0
    with pytest.raises(ValueError, match="8T"):
        view.render_event(engine.timeline.events()[0])
    with pytest.raises(ValueError, match="8T"):
        view.render(SRAMCell6T().get_state())
    with pytest.raises(ValueError, match="6T"):
        SRAMCell6TView().render_event(event)


def test_array_view_switching_uses_logical_selection_labels():
    view = SRAMArrayView()
    six = SRAMArray(4, 4)
    eight = SRAMArray(4, 4, cell_type=SRAMCell8T)
    view.draw(six)
    artists = tuple(view.axes.get_children())
    for array in (eight, six, eight):
        array.write(0, 2, 1)
        before = array.get_state()
        view.update(array)
        assert array.get_state() == before
        assert tuple(view.axes.get_children()) == artists
        assert array.architecture_name in view.title.get_text()
        label = "WL0" if array.uses_word_line else "SEL0"
        assert view.word_line_labels[0].get_text() == label + " = 1 ACTIVE"
        assert view.value_labels[0, 2].get_text() == "1"
