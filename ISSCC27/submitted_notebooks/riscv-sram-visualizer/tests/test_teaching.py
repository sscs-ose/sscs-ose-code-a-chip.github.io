"""Acceptance tests for the manual SRAM lesson and its source of truth."""

import re
from xml.etree import ElementTree

import pytest

from riscv_memory_visualizer.memory.periphery import AccessPhase
from riscv_memory_visualizer.simulation.events import MemoryEventType as E
from riscv_memory_visualizer.simulation.teaching import SRAMTeachingController
from riscv_memory_visualizer.ui.teaching_app import SRAMTeachingApp
from riscv_memory_visualizer.visualization.schematic_svg import (
    decoder, driver, gnd, input_port, nmos, output_port, pmos, render_scene,
    selector, sense_amp, vdd,
)


@pytest.mark.parametrize("operation,scene,result", [("READ", 6, 1), ("WRITE", 7, 1)])
def test_real_access_drives_story(operation, scene, result):
    controller = SRAMTeachingController(operation)
    assert tuple(dict.fromkeys(s.scene for s in controller.steps)) == (1, 2, 3, 4, 5, scene, 8)
    decode = next(e for e in controller.engine.timeline.events() if e.event_type is E.ADDRESS_DECODE)
    access = next(e for e in controller.engine.timeline.events()
                  if e.event_type is (E.SRAM_READ if operation == "READ" else E.SRAM_WRITE))
    assert all((s.address, s.row, s.column, s.selected_cell) ==
               (decode.address, decode.row, decode.column, (decode.row, decode.column))
               for s in controller.steps)
    assert controller.steps[-1].result == access.value == result
    assert controller.steps[-1].q == controller.array.get_cell(decode.row, decode.column).q
    assert controller.steps[-1].q_bar == controller.array.get_cell(decode.row, decode.column).q_bar
    assert controller.processor.state.operation == operation
    assert controller.processor.state.effective_address == decode.address


def test_navigation_is_read_only_and_one_step():
    c = SRAMTeachingController("WRITE")
    before = (c.array.get_state(), c.engine.timeline.events(), c.processor.get_state())
    first = c.current_step
    assert c.next() == c.steps[1]
    assert c.previous() == first
    for _ in range(50): c.next()
    assert c.current_step == c.steps[-1]
    assert c.restart() == first
    assert before == (c.array.get_state(), c.engine.timeline.events(), c.processor.get_state())


def test_read_write_phases_retain_real_storage_outcome():
    read = SRAMTeachingController("READ")
    write = SRAMTeachingController("WRITE")
    r = [s.circuit_snapshot for s in read.steps if s.scene == 6]
    w = [s.circuit_snapshot for s in write.steps if s.scene == 7]
    assert [p.phase for p in r] == [AccessPhase.PRECHARGE, AccessPhase.WORD_LINE_ACTIVE,
                                  AccessPhase.BITLINE_DEVELOPMENT, AccessPhase.SENSE,
                                  AccessPhase.READ_COMPLETE]
    assert (r[0].bit_line, r[0].bit_line_bar, r[-1].read_result) == (1, 1, 1)
    assert r[0].word_line == 0 and r[-1].word_line == read.array.get_cell(0, 2).word_line == 1
    assert w[0].q == 0 and w[3].q == w[-1].q == write.array.get_cell(0, 2).q == 1
    assert w[0].word_line == 0 and w[-1].word_line == write.array.get_cell(0, 2).word_line == 1
    assert (w[1].bit_line, w[1].bit_line_bar) == (1, 0)
    complete = next(s for s in write.steps if s.title == "Write complete")
    assert "WL remains high" in complete.explanation


def test_svg_contains_real_six_device_cell_and_state():
    c = SRAMTeachingController()
    cell = render_scene(next(s for s in c.steps if s.scene == 5))
    assert len(re.findall(r'data-device="(?:NMOS|PMOS)"', cell)) == 6
    for name in ("M1", "M2", "M3", "M4", "M5", "M6", "Q = 1", "Q_bar = 0", "BL", "BL_bar", "WL", "VDD", "GND"):
        assert name in cell
    read_precharge = render_scene(next(s for s in c.steps if s.scene == 6))
    read_sense = render_scene(next(s for s in c.steps if s.scene == 6 and s.title == "Sense"))
    assert read_precharge != read_sense
    assert 'BL = 1' in read_precharge and 'BL = 1' in read_sense


def test_app_switches_branch_without_widget_growth():
    app = SRAMTeachingApp()
    try:
        ids = tuple(id(item) for item in app.widget.children)
        assert app.technical_details.selected_index is None
        assert "Previous" in app.previous_button.description
        assert "Next" in app.next_button.description
        assert "Restart" in app.restart_button.description
        for _ in range(5): app.next()
        assert "Selected bitcell" in app.caption_view.value
        app.operation_selector.value = "WRITE"
        assert app.controller.current_step.scene == 1
        assert app.controller.steps[-2].scene == 7
        app.restart()
        assert ids == tuple(id(item) for item in app.widget.children)
        assert "<svg" in app.scene_view.value
        assert "<table" not in app.scene_view.value
    finally:
        app.close()


@pytest.mark.parametrize("operation,branch_scene", [("READ", 6), ("WRITE", 7)])
def test_every_step_renders_and_navigation_crosses_step_twelve(operation, branch_scene):
    app = SRAMTeachingApp()
    try:
        app.operation_selector.value = operation
        assert app.controller.total_steps == 18
        for index in range(app.controller.total_steps):
            assert app.controller.index == index
            assert f"Step {index + 1} of 18" in app.step_counter.value
            assert "<svg" in app.scene_view.value
            assert 'class="teaching-glow ' in app.scene_view.value
            if index < app.controller.total_steps - 1:
                assert not app.next_button.disabled
                app.next_button.click()
        assert app.controller.steps[12].scene == branch_scene
        assert app.controller.current_step.scene == 8
        assert app.next_button.disabled
        app.previous_button.click()
        assert app.controller.index == 16
        app.restart_button.click()
        assert app.controller.index == 0
        assert app.previous_button.disabled
    finally:
        app.close()


def test_mode_switch_rebuilds_late_story_and_toolbar_stays_visible():
    app = SRAMTeachingApp()
    try:
        for _ in range(14):
            app.next_button.click()
        assert app.controller.index == 14
        app.operation_selector.value = "WRITE"
        assert app.controller.index == 0
        assert app.controller.total_steps == 18
        assert app.controller.steps[12].title == "Write driver"
        assert app.toolbar.children == (app.operation_selector, app.step_counter)
        assert app.controls.children == (app.previous_button, app.next_button, app.restart_button)
        assert "sram-toolbar" in app.toolbar._dom_classes
        assert app.widget.layout.height == "min(84vh, 720px)"
        assert app.widget.layout.overflow == "hidden"
        assert app.widget.children.index(app.toolbar) < app.widget.children.index(app.content)
        assert app.explanation_panel.children == (app.caption_view, app.explanation_view)
        assert "WHAT IS HAPPENING?" in app.explanation_view.value
        assert "Key idea:" in app.explanation_view.value
        assert "sw x1,8(x2)" in app.instruction_view.value
        app.operation_selector.value = "READ"
        assert app.controller.steps[12].title == "Precharge"
        assert app.controller.index == 0
    finally:
        app.close()


def test_scene_motion_uses_finite_boundary_glow_and_supports_reduced_motion():
    controller = SRAMTeachingController("READ")
    scenes = {step.title: render_scene(step) for step in controller.steps}
    assert all("@media(prefers-reduced-motion:reduce)" in svg for svg in scenes.values())
    assert all('class="teaching-glow ' in svg for svg in scenes.values())
    assert all("infinite" not in svg for svg in scenes.values())
    assert 'data-animation-sequence="processor,request-port,sram"' in scenes["Processor request"]
    assert 'data-animation-sequence="address-input,row-decoder,column-selector,selected-cell"' in scenes["Address decode"]
    assert 'data-animation-sequence="row-r0,cell-r0-c0,cell-r0-c1,cell-r0-c2,cell-r0-c3"' in scenes["Selected row"]
    assert 'data-animation-sequence="column-c2,cell-r0-c2,cell-r1-c2,cell-r2-c2,cell-r3-c2"' in scenes["Selected column"]
    assert 'sram-reveal' in scenes["Bitcell close-up"]
    assert 'id="precharge"' in scenes["Precharge"]
    assert 'id="sense-amplifier"' in scenes["Sense"]
    write = SRAMTeachingController("WRITE")
    assert 'id="write-driver"' in render_scene(next(s for s in write.steps if s.title == "Cell overwrite"))


@pytest.mark.parametrize("operation", ["READ", "WRITE"])
def test_all_explanations_have_result_and_key_idea(operation):
    controller = SRAMTeachingController(operation)
    assert controller.total_steps == 18
    for step in controller.steps:
        assert step.title and step.key_idea
        assert len(step.explanation.split()) >= 24
        assert len(step.animation_sequence) >= 2
        assert step.explanation.endswith(".")
        svg = render_scene(step)
        ElementTree.fromstring(svg)
        assert len(re.findall(r'class="teaching-glow ', svg)) == len(step.animation_sequence)
        assert all(f'data-target="{target}"' in svg for target in step.animation_sequence)


def test_symbol_primitives_and_semantic_ids():
    assert 'data-device="NMOS"' in nmos(100, 100, "M5")
    assert 'data-device="PMOS"' in pmos(100, 100, "M1")
    assert 'r="5"' in pmos(100, 100, "M1")  # gate bubble
    assert "VDD" in vdd(100, 100) and "GND" in gnd(100, 100)
    assert 'class="schematic-input"' in input_port(0, 0, "A", "0x08")
    assert 'class="schematic-output"' in output_port(0, 0, "DATA")
    assert 'class="schematic-decoder"' in decoder(0, 0, 200, 100)
    assert 'class="schematic-selector"' in selector(0, 0, 200, 100)
    assert 'class="schematic-sense-amp"' in sense_amp(0, 0, 200, 100)
    assert 'class="schematic-driver"' in driver(0, 0, 200, 100)
    read = SRAMTeachingController("READ")
    assert all(f'id="cell-r0-c{c}"' in render_scene(read.steps[3]) for c in range(4))
    macro = render_scene(read.steps[1])
    for ident in ("address-input", "row-decoder", "column-selector", "sram-array", "periphery"):
        assert f'id="{ident}"' in macro


@pytest.mark.parametrize("operation", ["READ", "WRITE"])
def test_late_backward_navigation_keeps_backend_and_rendered_values(operation):
    app = SRAMTeachingApp()
    try:
        app.operation_selector.value = operation
        before = (app.controller.array.get_state(), app.controller.engine.timeline.events(),
                  app.controller.processor.get_state())
        for _ in range(17):
            app.next_button.click()
        assert app.controller.current_step.result == 1
        for _ in range(6):
            app.previous_button.click()
            assert "<svg" in app.scene_view.value
            assert "WHAT IS HAPPENING?" in app.explanation_view.value
        assert app.controller.index == 11
        assert before == (app.controller.array.get_state(), app.controller.engine.timeline.events(),
                          app.controller.processor.get_state())
    finally:
        app.close()
