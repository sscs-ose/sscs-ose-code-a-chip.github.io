"""Read-only visualization of the existing three-stage behavioral pipeline."""

from collections.abc import Mapping
from textwrap import fill

from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from riscv_memory_visualizer.cpu.processor import Processor


class PipelineView:
    """Reuse one figure to display stage occupancy, never to execute instructions.

    draw/update accept a Processor. render accepts Pipeline.snapshot() plus
    optional cycle/PC context; missing context is displayed as unknown.
    Processor rendering adds existing latched results and instruction fields.
    Snapshot rendering displays text only and recognizes the mnemonic for the
    conceptual memory indicator; it does not parse operands or calculate data.
    Occupied stages are labeled ACTIVE; multiple stages may be active at once.
    """

    STAGES = ("IF", "ID/EX", "MEM/WB")

    def __init__(self) -> None:
        self.figure = Figure(figsize=(13, 7), facecolor="white")
        self.axes = self.figure.add_axes((.03, .08, .94, .8))
        ax = self.axes
        ax.set(xlim=(0, 13), ylim=(0, 7))
        ax.axis("off")
        self.title = self.figure.suptitle("3-stage RISC-V pipeline", fontsize=18)
        self.context = self.figure.text(.06, .89, "Cycle: unknown | PC: unknown", fontsize=12)
        self.boxes = {}
        self.stage_labels = {}
        self.instruction_labels = {}
        self.detail_labels = {}
        for index, name in enumerate(self.STAGES):
            x = .2 + index*4.35
            patch = Rectangle((x, 2.1), 3.8, 4.2, facecolor="#f0f4f8", edgecolor="#9aa5b1")
            ax.add_patch(patch)
            self.boxes[name] = patch
            self.stage_labels[name] = ax.text(x+.2, 5.85, name, fontsize=14, weight="bold")
            self.instruction_labels[name] = ax.text(x+.2, 5.2, "EMPTY", fontsize=12, va="top")
            self.detail_labels[name] = ax.text(x+.2, 4.2, "", fontsize=10, va="top", linespacing=1.6)
            if index < 2:
                ax.annotate("", xy=(x+4.3, 4.5), xytext=(x+3.8, 4.5),
                            arrowprops=dict(arrowstyle="->", linewidth=2, color="#52606d"))
        self.memory_arrow = ax.annotate("", xy=(10.8, 1.2), xytext=(10.8, 2.1),
                                        arrowprops=dict(arrowstyle="->", linewidth=2, color="#176b91"))
        self.memory_label = ax.text(10.8, .9, "", ha="center", va="top", fontsize=11)
        self.summary = ax.text(.2, 1.65, "", va="top", fontsize=10, linespacing=1.6)
        self.figure.text(.05, .025, "Shows stage occupancy after a CPU step. ACTIVE means occupied; the view never advances the CPU.", fontsize=10)
        self.memory_arrow.set_visible(False)

    def draw(self, processor: Processor) -> Figure:
        """Read pipeline and simulation state without stepping or memory access."""
        state = processor.get_state()
        self.render(processor.pipeline.snapshot(), cycle=state.cpu_cycle, pc=state.pc)
        for stage in (processor.pipeline.if_stage, processor.pipeline.id_ex_stage, processor.pipeline.mem_wb_stage):
            instruction = stage.instruction
            if instruction is None:
                continue
            lines = [f"Operation: {instruction.opcode.upper()}"]
            registers = [f"{name}: x{getattr(instruction, name)}" for name in ("rd", "rs1", "rs2")
                         if getattr(instruction, name) is not None]
            lines.append("  ".join(registers))
            if instruction.immediate is not None:
                lines.append(f"Immediate: {instruction.immediate}")
            if stage.pc is not None:
                lines.append(f"Instruction PC: {stage.pc:#04x}")
            if stage.result is not None:
                lines.append(f"Latched result: {stage.result}")
            if stage.effective_address is not None:
                lines.append(f"Effective address: {stage.effective_address:#x}")
            if stage.store_data is not None:
                lines.append(f"Store data: {stage.store_data}")
            if instruction.opcode in ("lw", "sw"):
                lines.append("MEMORY ACCESS" + (" (pending)" if stage.name == "MEM/WB" else " instruction"))
            self.detail_labels[stage.name].set_text("\n".join(lines))
        # Prefer the real opcode over display text for live processor context.
        instruction = processor.pipeline.mem_wb_stage.instruction
        self._memory_indicator(instruction.opcode if instruction is not None else "")
        self.figure.canvas.draw_idle()
        return self.figure

    def update(self, processor: Processor) -> Figure:
        """Refresh persistent artists from the processor."""
        return self.draw(processor)

    def render(self, snapshot: Mapping[str, str | None], *, cycle: int | None = None,
               pc: int | None = None) -> Figure:
        """Render the existing text snapshot; unspecified cycle/PC stay unknown."""
        if set(snapshot) != set(self.STAGES):
            raise ValueError("snapshot must contain exactly IF, ID/EX, and MEM/WB.")
        if any(text is not None and (not isinstance(text, str) or not text.strip()) for text in snapshot.values()):
            raise ValueError("stage text must be non-empty text or None.")
        for name, value in (("cycle", cycle), ("pc", pc)):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be a non-negative integer or None.")
        self.context.set_text(f"Cycle: {cycle if cycle is not None else 'unknown'} | PC: {format(pc, '#04x') if pc is not None else 'unknown'}")
        for name in self.STAGES:
            text = snapshot[name]
            active = text is not None
            self.stage_labels[name].set_text(f"{name} | {'ACTIVE' if active else 'EMPTY'}")
            self.instruction_labels[name].set_text(fill(text, 29) if active else "EMPTY")
            self.boxes[name].set_facecolor("#dceef6" if active else "#f0f4f8")
            self.boxes[name].set_linewidth(2.5 if active else 1)
            self.detail_labels[name].set_text("")
        text = snapshot["MEM/WB"]
        self._memory_indicator(text.split()[0].lower() if text else "")
        self.summary.set_text("PIPELINE STATE\n" + "\n".join(f"{name}: {snapshot[name] or 'EMPTY'}" for name in self.STAGES))
        self.figure.canvas.draw_idle()
        return self.figure

    def _memory_indicator(self, opcode: str) -> None:
        """Label a pending memory instruction without generating a request."""
        active = opcode in ("lw", "sw")
        self.memory_arrow.set_visible(active)
        self.memory_label.set_text(("MEMORY READ" if opcode == "lw" else "MEMORY WRITE")
                                   + "\nCPU -> MEMORY\nAccess pending retirement" if active else "")
