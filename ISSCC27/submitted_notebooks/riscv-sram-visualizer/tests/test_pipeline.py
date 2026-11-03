"""Cycle occupancy, fetch addresses, draining, and snapshot behavior."""

from riscv_memory_visualizer.cpu.parser import InstructionParser
from riscv_memory_visualizer.cpu.processor import Processor
from riscv_memory_visualizer.cpu.registers import RegisterFile


def test_initial_and_empty_program():
    cpu = Processor()
    assert cpu.pc == 0
    assert isinstance(cpu.registers, RegisterFile)
    assert cpu.pipeline.snapshot() == {"IF": None, "ID/EX": None, "MEM/WB": None}
    assert cpu.finished
    assert cpu.step().cpu_cycle == 0


def test_pipeline_movement_and_pc():
    texts = ["lw x5, 8(x2)", "add x6, x5, x3", "sub x7, x6, x4"]
    cpu = Processor()
    cpu.load_program(map(InstructionParser().parse, texts))
    expected = [
        (texts[0], None, None),
        (texts[1], texts[0], None),
        (texts[2], texts[1], texts[0]),
        (None, texts[2], texts[1]),
        (None, None, texts[2]),
        (None, None, None),
    ]
    for cycle, stages in enumerate(expected, 1):
        state = cpu.step()
        assert tuple(cpu.pipeline.snapshot().values()) == stages
        assert state.cpu_cycle == cycle
        assert cpu.pc == min(cycle, 3) * 4
        for stage in (cpu.pipeline.if_stage, cpu.pipeline.id_ex_stage, cpu.pipeline.mem_wb_stage):
            if stage.instruction is not None:
                assert stage.pc == texts.index(str(stage.instruction)) * 4
    assert cpu.finished
    assert cpu.step().cpu_cycle == 6


def test_snapshots_do_not_change_with_future_steps():
    cpu = Processor()
    cpu.load_program([InstructionParser().parse("addi x1,x0,5")])
    state = cpu.step()
    snapshot = cpu.pipeline.snapshot()
    cpu.step()
    assert state.cpu_cycle == 1
    assert snapshot == {"IF": "addi x1,x0,5", "ID/EX": None, "MEM/WB": None}
    state.pc = 100
    snapshot["ID/EX"] = "changed"
    assert cpu.pc == 4
    assert cpu.pipeline.snapshot()["ID/EX"] == "addi x1,x0,5"
