"""Headless integration acceptance tests for the notebook controller."""

import asyncio
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import ipywidgets as widgets
import pytest

from riscv_memory_visualizer.ui.app import RiscVMemoryVisualizerApp
from riscv_memory_visualizer.simulation.events import MemoryEventType as T


@pytest.fixture
def app():
    instance = RiscVMemoryVisualizerApp()
    yield instance
    instance.close()


def test_components_and_controls(app):
    assert app.processor.memory.engine is app.engine
    assert app.engine.memory is app.array
    assert app.engine.timeline is app.timeline
    assert app.processor.memory.state is app.processor.state
    assert isinstance(app.instruction_input, widgets.Textarea)
    for name in ("load", "reset", "step", "run", "pause", "demo"):
        assert isinstance(getattr(app, name + "_button"), widgets.Button)
    assert "No SRAM cell selected" in app.cell_label.value


def test_load_comments_blanks_and_buttons(app):
    app.instruction_input.value = "\n# comment\naddi x1,x0,1 # inline\n\n"
    app.load_button.click()
    assert len(app.processor.instruction_memory) == 1
    assert "Program loaded: 1" in app.status_message
    app.step_button.click()
    assert app.processor.state.cpu_cycle == 1
    assert app.pipeline_view.instruction_labels["IF"].get_text() == "addi x1,x0,1"


@pytest.mark.parametrize("source, message", [("addi x1,x0,1\nbad", "line 2"),
                                           ("\n# only comment", "no instructions"),
                                           ("<script>", "line 1")])
def test_invalid_load_preserves_simulation(app, source, message):
    app.load_program("lw x5,8(x2)")
    app.load_demo_data()
    app.step()
    before = (app.processor.get_state(), app.processor.instruction_memory,
              app.array.get_state(), app.timeline.events())
    assert not app.load_program(source)
    assert message in app.status_message
    assert "<script>" not in app.status.value
    assert before == (app.processor.get_state(), app.processor.instruction_memory,
                      app.array.get_state(), app.timeline.events())


def test_end_to_end_real_load_and_all_views(app):
    app.load_program("lw x5,8(x2)")
    app.load_demo_data()
    setup_count = len(app.timeline)
    for cycle, stage in enumerate(("IF", "ID/EX", "MEM/WB"), 1):
        assert app.step()
        assert app.processor.state.cpu_cycle == cycle
        assert app.processor.pipeline.snapshot()[stage] == "lw x5,8(x2)"
        assert app.pipeline_view.instruction_labels[stage].get_text() == "lw x5,8(x2)"
        assert len(app.timeline) == setup_count
        assert app.processor.registers.read(5) == 0
    assert app.step()
    assert app.processor.state.cpu_cycle == 4
    assert app.processor.registers.read(5) == 1
    assert app.changed_registers == {5}
    assert "x5: 1" in app.register_panel.value
    assert "x5: 1 (changed)" in app.register_panel.value
    assert (app.array.selected_row, app.array.selected_column) == (0, 2)
    assert app.array_view.cell_patches[0, 2].get_linewidth() == 3
    assert app.array_view.value_labels[0, 2].get_text() == "1"
    assert app.cell_view.labels["Q"].get_text() == "Q = 1"
    assert app.cell_view.labels["Q_bar"].get_text() == "Q_bar = 0"
    events = app.timeline.events()[setup_count:]
    assert [e.event_type for e in events] == [T.INSTRUCTION, T.MEMORY_REQUEST,
        T.ADDRESS_DECODE, T.ROW_SELECT, T.COLUMN_SELECT, T.WORD_LINE_ACTIVE,
        T.SRAM_READ, T.MEMORY_RESPONSE, T.OPERATION_COMPLETE]
    assert all(e.cycle == 4 and e.instruction == "lw x5,8(x2)" for e in events)
    assert events[-1].value == 1
    assert "SRAM_READ" in app.timeline_panel.value
    assert app.status_message.startswith("Program complete")
    assert not app.step()
    assert app.processor.state.cpu_cycle == 4


def test_store_load_program(app):
    app.load_program("addi x1,x0,1\nsw x1,36(x0)\nlw x5,36(x0)\nadd x6,x5,x1")
    while not app.processor.finished:
        assert app.step()
    assert app.array.get_cell(2, 1).q == 1
    assert app.processor.registers.read(5) == 1
    assert app.processor.registers.read(6) == 2
    assert sum(e.event_type == T.SRAM_WRITE for e in app.timeline.events()) == 1


@pytest.mark.parametrize("program", ["lw x1,64(x0)", "lw x1,2(x0)",
                                    "addi x1,x0,2\nsw x1,0(x0)"])
def test_memory_errors_are_visible_and_stop_run(app, program):
    app.load_program(program)
    for _ in range(8):
        if not app.step():
            break
    assert app.status_message.startswith("Error:")
    assert not app.running
    assert not app.timeline.events()


def test_reset_retains_objects_and_program_clears_everything(app):
    app.load_program("lw x5,8(x2)")
    identities = (app.processor, app.array, app.timeline, app.array.get_cell(0, 2))
    app.load_demo_data()
    for _ in range(4):
        app.step()
    app.reset_button.click()
    assert identities == (app.processor, app.array, app.timeline, app.array.get_cell(0, 2))
    assert app.processor.state.cpu_cycle == app.processor.pc == 0
    assert app.processor.registers.get_all() == [0] * 32
    assert app.processor.pipeline.empty
    assert len(app.processor.instruction_memory) == 1
    assert not app.timeline.events()
    assert app.array.selected_row is app.array.selected_column is None
    assert app.array.get_cell(0, 2).q == 0
    assert app.array.get_state().word_lines == (0, 0, 0, 0)
    assert "No SRAM cell selected" in app.cell_label.value


def test_loading_does_not_silently_inject_demo_data(app):
    app.load_demo_data()
    app.load_program("lw x5,8(x2)")
    assert app.array.get_cell(0, 2).q == 0
    assert len(app.timeline) == 0


def test_run_pause_resume_and_completion(app):
    async def scenario():
        app.load_program("lw x5,8(x2)")
        app.load_demo_data()
        app.speed.value = .1
        assert app.run()
        task = app._task
        assert not app.run() and app._task is task
        await asyncio.sleep(0)
        assert app.processor.state.cpu_cycle == 1
        app.pause_button.click()
        cycle = app.processor.state.cpu_cycle
        await asyncio.sleep(.15)
        assert not app.running and app.processor.state.cpu_cycle == cycle
        assert app.run()
        await app._task
        assert app.processor.finished and not app.running
        assert app.processor.registers.read(5) == 1
    asyncio.run(scenario())


def test_cancel_restart_race_and_reset_during_run(app):
    async def scenario():
        app.load_program(app.DEMO_PROGRAM)
        app.run()
        app.pause()
        app.run()
        await asyncio.sleep(0)
        assert app.running
        app.reset()
        await asyncio.sleep(0)
        assert not app.running and app.processor.state.cpu_cycle == 0
        app.run()
        app.load_program("addi x1,x0,1")
        await asyncio.sleep(0)
        assert not app.running and app.processor.state.cpu_cycle == 0
    asyncio.run(scenario())


def test_run_without_event_loop_reports_requirement(app):
    app.load_program(app.DEMO_PROGRAM)
    assert not app.run()
    assert "Jupyter event loop" in app.status_message


def test_speed_changes_wait_between_cycles_without_changing_cycle_count(app):
    async def scenario():
        app.load_program(app.DEMO_PROGRAM)
        original_sleep = asyncio.sleep
        delays = []

        async def observed_sleep(delay):
            delays.append(delay)
            if len(delays) == 1:
                app.speed.value = .4
            elif len(delays) == 2:
                app.speed.value = 1.0
            else:
                app.pause()
            await original_sleep(0)

        app.speed.value = .1
        with patch("riscv_memory_visualizer.ui.app.asyncio.sleep", observed_sleep):
            assert app.run()
            await app._task
        assert delays == [.1, .4, 1.0]
        assert app.processor.state.cpu_cycle == 3
        assert not app.running
    asyncio.run(scenario())


def test_display_refresh_is_read_only_and_reuses_resources(app):
    app.load_program("lw x5,8(x2)")
    app.load_demo_data()
    views = (app.pipeline_view, app.array_view, app.cell_view)
    artists = [tuple(v.axes.get_children()) for v in views]
    figures = [v.figure for v in views]
    before = (app.processor.get_state(), app.processor.registers.get_all(),
              app.processor.pipeline.snapshot(), app.array.get_state(), app.timeline.events())
    with patch("riscv_memory_visualizer.ui.app.display") as display:
        app.display()
        display.assert_called_once_with(app.widget)
    widget_ids = set(widgets.Widget.get_manager_state()["state"])
    for _ in range(5):
        app.refresh()
    assert set(widgets.Widget.get_manager_state()["state"]) == widget_ids
    assert [v.figure for v in views] == figures
    assert [tuple(v.axes.get_children()) for v in views] == artists
    assert before == (app.processor.get_state(), app.processor.registers.get_all(),
                      app.processor.pipeline.snapshot(), app.array.get_state(), app.timeline.events())
    for output in (app.pipeline_output, app.array_output, app.cell_output):
        assert len(output.outputs) == 1
        assert "image/png" in output.outputs[0]["data"]
    app.reset()
    assert app.cell_output.outputs == ()


def test_close_stops_execution(app):
    async def scenario():
        app.load_program(app.DEMO_PROGRAM)
        app.run()
        app.close()
        await asyncio.sleep(0)
        assert not app.running and not app.step()
        with pytest.raises(RuntimeError, match="closed"):
            app.display()
    asyncio.run(scenario())


@pytest.mark.parametrize("architecture", ["6T", "8T"])
def test_architecture_load_regression(app, architecture):
    from riscv_memory_visualizer.memory.sram8t import SRAMCell8T
    app.architecture_selector.value = architecture
    app.load_program("lw x5,8(x2)")
    app.load_demo_data()
    for cycle in range(1, 5):
        assert app.step()
        assert app.processor.state.cpu_cycle == cycle
    assert app.processor.registers.read(5) == 1
    assert (app.array.selected_row, app.array.selected_column) == (0, 2)
    assert isinstance(app.array.get_cell(0, 2), SRAMCell8T) == (architecture == "8T")
    assert app.cell_view.labels["Q"].get_text() == "Q = 1"
    assert app.array_view.value_labels[0, 2].get_text() == "1"
    assert "Cycle: 4" in app.pipeline_view.context.get_text()
    assert architecture in app.cell_label.value
    assert any(e.event_type == T.SRAM_READ and e.cycle == 4 for e in app.timeline.events())


def test_switch_retains_cpu_adapter_program_and_reuses_views(app):
    cpu, adapter, engine, timeline = app.processor, app.processor.memory, app.engine, app.timeline
    app.load_program("lw x5,8(x2)")
    app.load_demo_data()
    app.step()
    views = dict(app._cell_views)
    widget_ids = set(widgets.Widget.get_manager_state()["state"])
    for architecture in ("8T", "6T") * 5:
        app.architecture_selector.value = architecture
        assert app.processor is cpu and cpu.memory is adapter
        assert app.engine is engine and app.timeline is timeline
        assert engine.memory is app.array
        assert app.processor.pc == app.processor.state.cpu_cycle == 0
        assert app.processor.registers.get_all() == [0] * 32
        assert app.processor.pipeline.empty and len(app.processor.instruction_memory) == 1
        assert not app.timeline.events()
        assert app.array.selected_row is None and app.array.get_cell(0, 2).q == 0
        assert app.cell_view is views[architecture]
        assert "program retained" in app.status_message
    assert set(widgets.Widget.get_manager_state()["state"]) == widget_ids


def test_switch_during_run_cancels_old_task_and_can_resume(app):
    async def scenario():
        app.load_program("lw x5,8(x2)")
        app.run()
        await asyncio.sleep(0)
        assert app.processor.state.cpu_cycle == 1
        app.architecture_selector.value = "8T"
        await asyncio.sleep(0)
        assert not app.running and app.processor.state.cpu_cycle == 0
        app.load_demo_data()
        app.speed.value = .1
        assert app.run()
        await app._task
        assert app.processor.registers.read(5) == 1
        app.reset()
        assert app.array.architecture_name == "8T (abstract)"
        assert app.array.get_cell(0, 2).q == 0
    asyncio.run(scenario())


def test_displayed_architecture_switch_clears_old_cell_image(app):
    app.load_demo_data()
    with patch("riscv_memory_visualizer.ui.app.display"):
        app.display()
    assert len(app.cell_output.outputs) == 1
    app.architecture_selector.value = "8T"
    assert app.cell_output.outputs == ()
    assert "abstract placeholder" in app.architecture_note.value
    app.load_demo_data()
    assert len(app.cell_output.outputs) == 1
    assert "image/png" in app.cell_output.outputs[0]["data"]


def test_waveform_step_pause_refresh_and_invalid_load_preserve_history(app):
    app.load_program("lw x5,8(x2)")
    app.load_demo_data()
    assert not app.trace_recorder.cycle_traces["CYCLE"].snapshot()
    for _ in range(4):
        app.step()
    assert app.trace_recorder.cycle_traces["CYCLE"].values() == (0, 1, 2, 3, 4)
    assert app.trace_recorder.cycle_traces["READ"].values() == (0, 0, 0, 0, 1)
    assert "Current cycle: 4" in app.waveform_view.title.get_text()
    assert app.trace_recorder.cycle_traces["Q"].value_at(4) == app.array.get_cell(0, 2).q
    before = app.trace_recorder.snapshot()
    app.pause()
    app.refresh()
    app.load_program("bad")
    app.step()  # Drained: no phantom cycle.
    assert app.trace_recorder.snapshot() == before


@pytest.mark.parametrize("action", ["reset", "load", "switch"])
def test_waveform_history_clears_on_simulation_restart(app, action):
    app.load_program("lw x5,8(x2)")
    app.load_demo_data()
    app.step()
    figure = app.waveform_view.figure
    if action == "reset":
        app.reset()
    elif action == "load":
        app.load_program("addi x1,x0,1")
    else:
        app.architecture_selector.value = "8T"
    trace = app.trace_recorder.snapshot()
    assert not trace.events and trace.current_cycle == 0
    assert all(not t.samples for t in (*trace.cycle_traces, *trace.event_traces))
    assert app.waveform_view.figure is figure
    assert not app.waveform_view.marker.get_visible()
    assert not len(app.waveform_view.lines["Q"].get_xdata())
    if action == "switch":
        assert "N/A" in app.waveform_view.notes["WL"].get_text()


def test_waveform_run_growth_pause_and_output(app):
    async def scenario():
        app.load_program("lw x5,8(x2)")
        app.load_demo_data()
        app.speed.value = .1
        app.run()
        await asyncio.sleep(0)
        app.pause()
        before = app.trace_recorder.snapshot()
        await asyncio.sleep(.15)
        assert app.trace_recorder.snapshot() == before
        app.run()
        await app._task
        assert len(app.trace_recorder.cycle_traces["CYCLE"].snapshot()) == 5
    asyncio.run(scenario())
    with patch("riscv_memory_visualizer.ui.app.display"):
        app.display()
    assert len(app.waveform_output.outputs) == 1
    assert "image/png" in app.waveform_output.outputs[0]["data"]
