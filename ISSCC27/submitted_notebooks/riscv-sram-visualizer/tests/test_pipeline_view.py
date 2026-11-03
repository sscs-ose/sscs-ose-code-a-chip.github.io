"""Read-only pipeline display and stable artist tests."""
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import pytest

from riscv_memory_visualizer.cpu.parser import InstructionParser
from riscv_memory_visualizer.cpu.processor import Processor
from riscv_memory_visualizer.visualization.pipeline_view import PipelineView


def test_movement_cycles_reset_and_artist_reuse():
    cpu = Processor()
    cpu.load_program([InstructionParser().parse(t) for t in
                      ("addi x2, x0, 256", "lw x5, 8(x2)", "add x6, x5, x2")])
    view = PipelineView()
    figure = view.draw(cpu)
    assert all(t.get_text() == "EMPTY" for t in view.instruction_labels.values())
    artists = tuple(view.axes.get_children())
    for _ in range(6):
        cpu.step()
        state, registers, stages = cpu.get_state(), cpu.registers.get_all(), cpu.pipeline.snapshot()
        assert view.update(cpu) is figure
        assert tuple(view.axes.get_children()) == artists
        assert cpu.get_state() == state and cpu.registers.get_all() == registers
        assert cpu.pipeline.snapshot() == stages
        assert f"Cycle: {state.cpu_cycle}" in view.context.get_text()
        assert f"PC: {state.pc:#04x}" in view.context.get_text()
        for name, text in stages.items():
            assert view.instruction_labels[name].get_text() == (text or "EMPTY")
    cpu.reset()
    view.update(cpu)
    assert all(t.get_text() == "EMPTY" for t in view.instruction_labels.values())
    assert "Cycle: 0 | PC: 0x00" == view.context.get_text()
    assert not view.memory_arrow.get_visible()
    output = BytesIO()
    figure.savefig(output, format="png")
    assert output.getvalue().startswith(b"\x89PNG")


@pytest.mark.parametrize("text,indicator", [("lw x5,8(x2)", "MEMORY READ"),
                                           ("sw x5,8(x2)", "MEMORY WRITE"),
                                           ("add x5,x2,x2", "")])
def test_latched_details_and_memory_indicator(text, indicator):
    class Memory:
        def read(self, address):
            pytest.fail("view accessed memory")
        def write(self, address, value):
            pytest.fail("view accessed memory")
    cpu = Processor(Memory())
    cpu.load_program([InstructionParser().parse(text)])
    cpu.registers.write(2, 256)
    cpu.registers.write(5, 7)
    for _ in range(3):
        cpu.step()
    view = PipelineView()
    view.draw(cpu)
    assert view.memory_arrow.get_visible() == bool(indicator)
    assert indicator in view.memory_label.get_text()
    details = view.detail_labels["MEM/WB"].get_text()
    assert "rs1: x2" in details
    if indicator:
        assert "Effective address: 0x108" in details
    else:
        assert "Latched result: 512" in details
        assert view.memory_label.get_text() == ""
    if text.startswith("sw"):
        assert "Store data: 7" in details


def test_snapshot_support_unknown_context_and_no_stale_details():
    view = PipelineView()
    snapshot = {"IF": "ADD x1,x2,x3", "ID/EX": None, "MEM/WB": "LW x5,8(x2)"}
    before = snapshot.copy()
    view.render(snapshot)
    assert snapshot == before
    assert view.context.get_text() == "Cycle: unknown | PC: unknown"
    assert view.instruction_labels["IF"].get_text() == snapshot["IF"]
    assert view.memory_arrow.get_visible()
    assert all(not text.get_text() for text in view.detail_labels.values())
    view.render(dict.fromkeys(view.STAGES))
    assert not view.memory_arrow.get_visible()


@pytest.mark.parametrize("snapshot", [{}, {"IF": None, "ID/EX": None, "MEM/WB": 3}])
def test_bad_snapshots_rejected(snapshot):
    with pytest.raises(ValueError):
        PipelineView().render(snapshot)
