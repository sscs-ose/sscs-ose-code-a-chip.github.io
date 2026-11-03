"""Headless checks of live state, event context, and artist reuse."""
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
import pytest

from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.events import MemoryEventType as T
from riscv_memory_visualizer.visualization.array_view import SRAMArrayView


def signals(array):
    return tuple(array.get_cell(r, c).get_state() for r in range(array.rows) for c in range(array.columns))


@pytest.mark.parametrize("rows,columns", [(2, 2), (4, 4), (4, 8), (8, 8)])
def test_sizes_values_labels_and_rendering(rows, columns):
    array = SRAMArray(rows, columns)
    view = SRAMArrayView()
    before = signals(array)
    view.draw(array)
    assert signals(array) == before
    assert [t.get_text() for t in view.row_labels] == [f"R{r}" for r in range(rows)]
    assert [t.get_text() for t in view.column_labels] == [f"C{c}" for c in range(columns)]
    assert len(view.value_labels) == rows * columns
    assert all(t.get_text() == "0" for t in view.value_labels.values())
    image = BytesIO()
    view.figure.savefig(image, format="png")
    assert image.getvalue().startswith(b"\x89PNG")


def test_updates_selection_reset_and_artist_identity():
    array = SRAMArray(4, 4)
    view = SRAMArrayView()
    figure = view.draw(array)
    artists = tuple(view.axes.get_children())
    for value in (1, 0, 1):
        array.write(2, 3, value)
        before = signals(array)
        assert view.update(array) is figure
        assert tuple(view.axes.get_children()) == artists
        assert signals(array) == before
        assert view.value_labels[2, 3].get_text() == str(value)
        assert view.word_line_labels[2].get_text() == "WL2 = 1 ACTIVE"
        assert view.column_labels[3].get_text() == "C3 *"
        assert "Selected: (2, 3)" in view.panel.get_text()
        assert view.cell_patches[2, 3].get_linewidth() == 3
    array.reset()
    view.update(array)
    assert all(t.get_text() == "0" for t in view.value_labels.values())
    assert all(p.get_linewidth() == 1 for p in view.cell_patches.values())
    assert "Selected: -" in view.panel.get_text()
    assert all("ACTIVE" not in t.get_text() for t in view.word_line_labels)


def test_column_only_and_resize_same_figure():
    view = SRAMArrayView()
    array = SRAMArray(2, 2)
    array.select_column(1)
    figure = view.draw(array)
    assert "Column: 1" in view.panel.get_text()
    assert "Selected: -" in view.panel.get_text()
    assert all("ACTIVE" not in t.get_text() for t in view.word_line_labels)
    assert view.update(SRAMArray(4, 8, 1)) is figure
    assert len(view.value_labels) == 32
    assert all(t.get_text() == "1" for t in view.value_labels.values())


@pytest.mark.parametrize("kind", [T.SRAM_READ, T.SRAM_WRITE])
def test_events_read_live_values_without_mutation(kind):
    array = SRAMArray(4, 4)
    engine = MemoryEventEngine(array)
    engine.write(44, 1)
    engine.read(44)
    event = next(e for e in engine.timeline.events() if e.event_type == kind)
    before = signals(array)
    view = SRAMArrayView()
    view.render_event(array, event)
    canvas = FigureCanvasAgg(view.figure)
    canvas.draw()
    renderer = canvas.get_renderer()
    assert view.explanation.get_window_extent(renderer).y0 > view.figure.texts[-1].get_window_extent(renderer).y1
    assert kind.name.removeprefix("SRAM_") in view.title.get_text()
    assert view.value_labels[2, 3].get_text() == "1"
    assert signals(array) == before
    array.write(2, 3, 0)
    with pytest.raises(ValueError, match="match"):
        view.render_event(array, event)
    view.update(array)
    assert view.value_labels[2, 3].get_text() == "0"


def test_wrong_selection_and_missing_coordinates_rejected():
    array = SRAMArray(2, 2)
    engine = MemoryEventEngine(array)
    engine.read(0)
    view = SRAMArrayView()
    with pytest.raises(ValueError):
        view.render_event(array, engine.timeline.events()[0])
    event = next(e for e in engine.timeline.events() if e.event_type == T.SRAM_READ)
    array.select_cell(1, 1)
    before = signals(array)
    with pytest.raises(ValueError, match="selection"):
        view.render_event(array, event)
    assert signals(array) == before
