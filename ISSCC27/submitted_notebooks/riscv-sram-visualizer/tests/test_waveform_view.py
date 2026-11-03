"""Headless timing rendering and stable artist counts, without pixel comparisons."""

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import pytest

from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.memory.sram8t import SRAMCell8T
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.signals import SimulationTraceRecorder
from riscv_memory_visualizer.visualization.waveform_view import WaveformView


def make_trace(eight=False):
    array = SRAMArray(4, 4, **({"cell_type": SRAMCell8T} if eight else {}))
    engine = MemoryEventEngine(array)
    recorder = SimulationTraceRecorder(engine.timeline, architecture=array.architecture_name, physical_signals=not eight)
    recorder.record_cycle(0, array, cell=(0, 2))
    engine.write(8, 1, cycle=1)
    recorder.record_cycle(1, array, cell=(0, 2))
    engine.read(8, cycle=2)
    recorder.record_cycle(2, array, cell=(0, 2))
    return array, engine, recorder


@pytest.mark.parametrize("eight", [False, True])
def test_render_reuses_artists_and_preserves_models(eight):
    array, engine, recorder = make_trace(eight)
    view = WaveformView()
    figure = view.draw(recorder.snapshot())
    artists = [tuple(a.get_children()) for a in (view.axes, view.event_axes)]
    before = array.get_state(), engine.timeline.events(), recorder.snapshot()
    for _ in range(8):
        assert view.update(recorder.snapshot()) is figure
        assert artists == [tuple(a.get_children()) for a in (view.axes, view.event_axes)]
    assert before == (array.get_state(), engine.timeline.events(), recorder.snapshot())
    assert "Current cycle: 2" in view.title.get_text()
    assert view.lines["Q"].get_drawstyle() == "steps-post"
    assert view.marker.get_visible() and list(view.marker.get_xdata()) == [2, 2]
    assert "Cycle 2" in view.event_title.get_text()
    assert "NOT additional CPU cycles" in view.event_axes.get_xlabel()
    assert "SRAM_READ" in " ".join(t.get_text() for t in view.event_axes.get_xticklabels())
    for name in ("WL", "BL", "BL_bar"):
        if eight:
            assert "N/A" in view.notes[name].get_text()
            assert not len(view.lines[name].get_xdata())
            assert "N/A" in view.event_notes[name].get_text()
        else:
            assert len(view.lines[name].get_xdata())
    output = BytesIO()
    figure.savefig(output, format="png")
    assert output.getvalue().startswith(b"\x89PNG")


def test_empty_reset_and_selected_window_remove_stale_artists():
    array, engine, recorder = make_trace()
    view = WaveformView()
    view.draw(recorder.snapshot())
    view.update(recorder.snapshot(), start_cycle=0, end_cycle=1)
    assert not view.marker.get_visible()
    assert "Cycle 1" in view.event_title.get_text()
    for kwargs in (dict(start_cycle=-1), dict(start_cycle=4, end_cycle=2), dict(event_cycle=-1)):
        with pytest.raises(ValueError):
            view.update(recorder.snapshot(), **kwargs)
    engine.timeline.clear()
    recorder.clear()
    view.update(recorder.snapshot())
    assert not view.marker.get_visible()
    assert all(len(line.get_xdata()) == 0 for line in (*view.lines.values(), *view.event_lines.values()))
    assert "No memory events" in view.event_title.get_text()
    assert all(not label.get_visible() for labels in view.labels.values() for label in labels)


def test_timeline_only_and_unknown_cycle_events_are_visible_without_fake_cycles():
    array = SRAMArray(1, 1)
    engine = MemoryEventEngine(array)
    recorder = SimulationTraceRecorder(engine.timeline)
    engine.write(0, 1)
    engine.read(0, cycle=4)
    recorder.record_events()
    view = WaveformView()
    view.draw(recorder.snapshot())
    assert "Cycle 4" in view.event_title.get_text()
    assert not len(view.lines["CYCLE"].get_xdata())
    view.update(recorder.snapshot(), event_cycle=None)
    assert "unknown CPU cycle" in view.event_title.get_text()
    assert "SRAM_WRITE" in " ".join(t.get_text() for t in view.event_axes.get_xticklabels())


def test_long_history_does_not_grow_artist_or_text_pools():
    array, engine, recorder = make_trace()
    view = WaveformView()
    view.draw(recorder.snapshot())
    counts = [(len(a.lines), len(a.texts), len(a.patches)) for a in (view.axes, view.event_axes)]
    for cycle in range(3, 30):
        engine.write(8, cycle % 2, cycle=cycle)
        recorder.record_cycle(cycle, array)
        view.update(recorder.snapshot())
    assert [(len(a.lines), len(a.texts), len(a.patches)) for a in (view.axes, view.event_axes)] == counts
    assert view.axes.get_xlim()[0] > 16
    assert len(recorder.cycle_traces["CYCLE"].snapshot()) == 30
