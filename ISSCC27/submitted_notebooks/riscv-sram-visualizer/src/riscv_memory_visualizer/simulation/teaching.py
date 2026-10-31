"""Recorded, immutable manual teaching story driven by the existing CPU and SRAM."""

from dataclasses import dataclass, replace

from riscv_memory_visualizer.cpu.parser import InstructionParser
from riscv_memory_visualizer.cpu.processor import Processor
from riscv_memory_visualizer.memory.array import SRAMArray, SRAMArrayState
from riscv_memory_visualizer.memory.periphery import PeripheralSnapshot, read_sequence, write_sequence
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.events import MemoryEventType as E
from riscv_memory_visualizer.simulation.processor_memory import ProcessorEventMemory


@dataclass(frozen=True)
class TeachingStep:
    id: str
    scene: int
    substep: int
    title: str
    caption: str
    operation: str
    instruction: str
    address: int
    row: int
    column: int
    selected_cell: tuple[int, int]
    array_state: SRAMArrayState
    q: int
    q_bar: int
    circuit_snapshot: PeripheralSnapshot | None = None
    highlight_ids: tuple[str, ...] = ()
    result: int | None = None
    explanation: str = ""
    key_idea: str = ""
    animation_sequence: tuple[str, ...] = ()
    before_q: int | None = None


_LESSONS = {
    "Processor request": (
        "The processor issues a {action} request to SRAM using address {address:#04x}. "
        "That request identifies the memory location; the following steps trace what SRAM does internally. "
        "The request is now at the SRAM interface.",
        "The processor requests an access; SRAM performs the storage operation."),
    "Inside the SRAM macro": (
        "The address enters decoding circuitry beside the storage array. The decoder chooses a row and column, "
        "while peripheral circuits use word lines and bit lines to reach the chosen cell. "
        "These blocks together form one SRAM access path.",
        "Decoders locate the cell; peripheral circuits read or modify it."),
    "Address decode": (
        "Here x2=0, so base plus offset 0+8 gives address {address:#04x} ({address} decimal). "
        "Four-byte address slots give index {address} // 4 = {index}. In this 4x4 teaching array, "
        "row = {index} // {columns} = {row} and column = {index} % {columns} = {column}. "
        "Zero-based cell ({row},{column}) is selected; column {column} is the third column. "
        "Each slot models one bitcell, not a 32-bit word.",
        "The decoded row and column select one single-bit cell."),
    "Selected row": (
        "The row decoder selects Row {row} and its shared word line. Every cell on that row becomes eligible "
        "for access, so row selection alone does not identify a single cell. Column selection is still needed.",
        "Selecting a row does not uniquely select one cell."),
    "Selected column": (
        "Column {column} identifies the bit-line pair shared by cells in that column. The column path narrows "
        "the access to the selected vertical position. Together with Row {row}, it isolates one bitcell.",
        "The selected row and column intersect at one cell."),
    "Selected bitcell": (
        "Row {row} and Column {column} intersect at cell ({row},{column}). This cell holds the bit requested "
        "by the processor. The next view expands this array location into its transistor circuit.",
        "One array square represents one physical SRAM storage circuit."),
    "Bitcell close-up": (
        "The selected array square is expanded into its 6T circuit representation. Its complementary "
        "storage nodes currently hold Q={q} and Q_bar={q_bar}. The circuit view shows how those states are retained.",
        "A logical bitcell is implemented by a transistor latch."),
    "Cross-coupled inverters": (
        "Four transistors form two cross-coupled CMOS inverters. Each inverter feeds the other, reinforcing "
        "one of two stable binary states. This feedback holds the bit while power remains present.",
        "Positive feedback makes SRAM static storage."),
    "Storage nodes": (
        "The stored bit appears at complementary internal nodes Q={q} and Q_bar={q_bar}. Each inverter "
        "reinforces the opposite node, so the pair remains stable. These two nodes encode one bit.",
        "Q and Q_bar represent complementary stored states."),
    "Access transistors": (
        "M5 and M6 are NMOS access switches between the latch and the bit-line pair. When their gates are "
        "off, the latch is isolated; when on, the external circuitry can read or write it. "
        "They provide the cell's access path.",
        "Access transistors connect the latch to the memory circuitry."),
    "Word line": (
        "The word line controls both access-transistor gates. A low WL isolates the bitcell, while a high "
        "WL connects Q and Q_bar to BL and BL_bar. Row selection therefore controls when the cell participates.",
        "WL determines when the selected cell connects to the bit lines."),
    "Bit-line pair": (
        "BL and BL_bar are complementary rails between the cell and the peripheral circuitry. A read lets "
        "the cell create a difference between them; a write drives them with new data. The pair is ready "
        "for the selected operation.",
        "The same bit-line pair serves reading and writing differently."),
    "Precharge": (
        "Before a read, PMOS precharge devices prepare BL and BL_bar to the same logical starting state. "
        "A balanced pair makes the cell's later difference detectable. Both lines now start equal.",
        "Precharge gives both bit lines the same starting condition."),
    "Word-line activation": (
        "The selected WL rises and turns on M5 and M6. This connects the internal storage nodes to the "
        "bit-line pair, allowing the {operation} operation to proceed. The cell is now electrically accessible.",
        "WL opens the selected cell's access path."),
    "Bit-line development": (
        "Q and Q_bar hold opposite values, so the two bit lines respond differently after WL turns on. "
        "One side begins to discharge relative to the other. This difference carries the stored bit toward sensing.",
        "The cell turns its stored state into a bit-line difference."),
    "Sense": (
        "The differential sense circuit compares BL and BL_bar. It resolves their difference into a clear "
        "digital output without requiring a full swing on the long bit lines. The stored bit is now identified.",
        "The sense amplifier turns a differential into a digital result."),
    "Read result": (
        "The sense output reports the backend read result, {result}. The selected cell still holds "
        "Q={q} and Q_bar={q_bar}; reading does not intentionally change its stored state. "
        "The data is ready for the processor.",
        "Reading retrieves a bit without intentionally changing it."),
    "Write driver": (
        "The write driver receives new data {result} and prepares complementary outputs for BL and BL_bar. "
        "It actively drives the pair because the old latch state must be changed. The new value is ready at the periphery.",
        "The write driver controls the value presented to the cell."),
    "Bit-lines driven": (
        "The driver establishes BL={result} and BL_bar={result_bar}. These complementary rail states represent "
        "the new Q/Q_bar condition to be stored. The lines are ready before WL connects them to the latch.",
        "The bit-line pair carries the new value into the cell."),
    "Cell overwrite": (
        "The driven bit lines push the old nodes Q={old} and Q_bar={old_bar} toward new states "
        "Q={q} and Q_bar={q_bar}. Cross-coupled feedback reinforces the new condition once the latch flips. "
        "The backend now records the new bit.",
        "Writing forces the latch into a new stable state."),
    "Write complete": (
        "The write drive is no longer enabled in this teaching snapshot, but WL remains high in the "
        "existing array model. The cross-coupled latch holds Q={q} and Q_bar={q_bar}. "
        "A later WL deactivation is not simulated; the new bit remains stored.",
        "The latch retains the new value after access ends."),
    "Read summary": (
        "The read decoded address {address:#04x}, selected cell ({row},{column}), and prepared the bit lines. "
        "WL connected the cell, allowing a bit-line difference that the sense circuit resolved. "
        "The SRAM returned value {result} while preserving the stored state.",
        "Read = select, prepare, connect, develop, sense."),
    "Write summary": (
        "The write decoded address {address:#04x} and selected cell ({row},{column}). "
        "The driver set complementary bit-line values, then WL connected them to the latch and forced a new stable state. "
        "The SRAM now stores value {result}.",
        "Write = select, drive, connect, overwrite, retain."),
}


def _animation_sequence(title: str, row: int, column: int) -> tuple[str, ...]:
    if title == "Selected row":
        return (f"row-r{row}", *(f"cell-r{row}-c{c}" for c in range(4)))
    if title == "Selected column":
        return (f"column-c{column}", *(f"cell-r{r}-c{column}" for r in range(4)))
    if title == "Selected bitcell":
        return (f"row-r{row}", f"column-c{column}", f"cell-r{row}-c{column}")
    if title == "Bitcell close-up":
        return (f"cell-r{row}-c{column}", "bitcell-closeup")
    return {
        "Processor request": ("processor", "request-port", "sram"),
        "Inside the SRAM macro": ("address-input", "row-decoder", "column-selector", "sram-array", "periphery"),
        "Address decode": ("address-input", "row-decoder", "column-selector", "selected-cell"),
        "Cross-coupled inverters": ("left-inverter", "right-inverter", "feedback"),
        "Storage nodes": ("q", "q-bar"),
        "Access transistors": ("m5", "m6"),
        "Word line": ("wl", "m5", "m6"),
        "Bit-line pair": ("bl", "bl-bar"),
        "Precharge": ("precharge", "bl", "bl-bar"),
        "Word-line activation": ("wl", "m5", "m6", "q", "q-bar"),
        "Bit-line development": ("q", "m5", "bl", "bl-bar"),
        "Sense": ("bl", "bl-bar", "sense-amplifier", "sense-output"),
        "Read result": ("sense-output", "result"),
        "Write driver": ("data-input", "write-driver", "bl", "bl-bar"),
        "Bit-lines driven": ("data-input", "bl", "bl-bar"),
        "Cell overwrite": ("q", "bl", "m5", "q-bar", "stored-state"),
        "Write complete": ("q", "q-bar", "wl", "stored-state"),
        "Read summary": ("summary-decode", "summary-select", "summary-prepare",
                         "summary-access", "summary-finish", "summary-result"),
        "Write summary": ("summary-decode", "summary-select", "summary-prepare",
                          "summary-access", "summary-finish", "summary-result"),
    }[title]


class SRAMTeachingController:
    """Run one real access when constructing a branch; navigation only reads snapshots."""

    def __init__(self, operation: str = "READ") -> None:
        self.operation = ""
        self.steps: tuple[TeachingStep, ...] = ()
        self.index = 0
        self.array: SRAMArray | None = None
        self.engine: MemoryEventEngine | None = None
        self.processor: Processor | None = None
        self.select_operation(operation)

    @property
    def current_step(self) -> TeachingStep:
        return self.steps[self.index]

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    def next(self) -> TeachingStep:
        self.index = min(self.index + 1, len(self.steps) - 1)
        return self.current_step

    def previous(self) -> TeachingStep:
        self.index = max(self.index - 1, 0)
        return self.current_step

    def restart(self) -> TeachingStep:
        self.index = 0
        return self.current_step

    def select_operation(self, operation: str) -> TeachingStep:
        if operation not in ("READ", "WRITE"):
            raise ValueError("operation must be READ or WRITE")
        array = SRAMArray(4, 4)
        engine = MemoryEventEngine(array)
        parser = InstructionParser()
        processor = Processor(engine)
        processor.memory = ProcessorEventMemory(engine, processor.state)
        if operation == "READ":
            # Explicit example data, installed through the real backend.
            engine.write(8, 1)
            # The existing array holds selection after a write. Selecting a
            # different row leaves the target WL low before the read.
            array.select_row(1)
            instruction = "lw x5,8(x2)"
        else:
            instruction = "sw x1,8(x2)"
        engine.timeline.clear()
        before = array.get_state()
        program = ([parser.parse("addi x1,x0,1")] if operation == "WRITE" else []) + [parser.parse(instruction)]
        processor.load_program(program)
        while not processor.finished:
            processor.step()
        events = engine.timeline.events()
        decoded = next(event for event in events if event.event_type is E.ADDRESS_DECODE)
        accessed = next(event for event in events if event.event_type is (E.SRAM_READ if operation == "READ" else E.SRAM_WRITE))
        assert decoded.row is not None and decoded.column is not None and decoded.address is not None
        row, column, address = decoded.row, decoded.column, decoded.address
        after = array.get_state()
        old_bit = before.cells[row][column]
        new_bit = after.cells[row][column]
        assert accessed.cell_state is not None and accessed.value == new_bit
        phases = (read_sequence(old_bit, accessed.value) if operation == "READ"
                  else write_sequence(old_bit, accessed.value, new_bit))
        steps = self._build_steps(operation, instruction, address, row, column,
                                  before, after, phases, accessed.value)
        self.operation, self.array, self.engine, self.processor = operation, array, engine, processor
        self.steps = steps
        self.index = 0
        return self.current_step

    @staticmethod
    def _build_steps(operation, instruction, address, row, column, before, after, phases, result):
        steps = []
        # Selection precedes the backend cell access; storage is still the
        # pre-access value then, while the actual decoded row/WLs match after.
        selected_before = replace(before, selected_row=row, selected_column=column,
                                  word_lines=after.word_lines)
        def add(scene, title, caption, *, snapshot=None, highlights=(), state=None, bit=None):
            array_state = state or selected_before
            q = array_state.cells[row][column] if bit is None else bit
            context = dict(action="read" if operation == "READ" else "write",
                           operation=operation.lower(), address=address, index=address // 4,
                           columns=array_state.columns, row=row, column=column,
                           q=q, q_bar=1-q, result=result, result_bar=1-result,
                           old=before.cells[row][column], old_bar=1-before.cells[row][column])
            explanation, key_idea = _LESSONS[title]
            steps.append(TeachingStep(
                f"{scene:02d}-{sum(s.scene == scene for s in steps)+1:02d}", scene,
                sum(s.scene == scene for s in steps)+1, title, caption, operation,
                instruction, address, row, column, (row, column), array_state,
                q, 1-q, snapshot, tuple(highlights), result,
                explanation.format(**context), key_idea,
                _animation_sequence(title, row, column),
                before.cells[row][column]))
        add(1, "Processor request", "The processor issues a memory access request to SRAM.", highlights=("request",), state=before)
        add(2, "Inside the SRAM macro", "SRAM combines storage cells with decoding and read/write circuitry.", highlights=("array", "decoder", "periphery"), state=before)
        add(3, "Address decode", "The memory address selects one row and one column.", highlights=("address", "row", "column"))
        add(4, "Selected row", "The row decoder activates the selected word line.", highlights=("row",))
        add(4, "Selected column", "The column selector identifies one bit-line pair.", highlights=("column",))
        add(4, "Selected bitcell", "The selected row and column identify one SRAM bitcell.", highlights=("row", "column", "cell"))
        add(4, "Bitcell close-up", "The selected cell stores its bit at Q and the complement at Q_bar.", highlights=("row", "column", "cell", "zoom"))
        for title, caption, ids in (
            ("Cross-coupled inverters", "Two CMOS inverters hold complementary logic states.", ("M1", "M2", "M3", "M4")),
            ("Storage nodes", "The latch stores the bit at Q and its complement at Q_bar.", ("Q", "Q_bar")),
            ("Access transistors", "Two NMOS devices connect the latch to the bit-line pair.", ("M5", "M6")),
            ("Word line", "WL controls both access transistor gates.", ("WL", "M5", "M6")),
            ("Bit-line pair", "BL and BL_bar carry complementary logical information.", ("BL", "BL_bar")),
        ):
            add(5, title, caption, highlights=ids)
        if operation == "READ":
            descriptions = (
                ("Precharge", "Before the read, the bit-line pair is precharged.", ("precharge", "BL", "BL_bar")),
                ("Word-line activation", "The selected word line turns on the two access transistors.", ("WL", "M5", "M6")),
                ("Bit-line development", "The stored state creates a logical difference between BL and BL_bar.", ("Q", "Q_bar", "BL", "BL_bar")),
                ("Sense", "The sense circuit resolves the bit-line difference.", ("sense", "BL", "BL_bar")),
                ("Read result", "The read operation produces the stored bit.", ("result",)),
            )
            scene = 6
        else:
            descriptions = (
                ("Write driver", "The write driver prepares complementary bit-line values.", ("driver",)),
                ("Bit-lines driven", "The complementary bit-line pair represents the new data.", ("BL", "BL_bar")),
                ("Word-line activation", "The active word line connects the storage nodes to the bit-lines.", ("WL", "M5", "M6")),
                ("Cell overwrite", "The driven bit-lines overwrite the internal latch.", ("Q", "Q_bar", "M5", "M6")),
                ("Write complete", "The 6T cell now stores the new value.", ("result",)),
            )
            scene = 7
        if len(phases) != len(descriptions):
            raise ValueError("teaching phase count does not match the story")
        for phase, (title, caption, ids) in zip(phases, descriptions):
            add(scene, title, caption, snapshot=phase, highlights=ids,
                state=after if phase.phase.name in ("CELL_OVERWRITE", "WRITE_COMPLETE") else selected_before,
                bit=phase.q)
        add(8, "Read summary" if operation == "READ" else "Write summary",
            "An SRAM access selects one bitcell to retrieve or update its stored bit.",
            state=after, highlights=("result",))
        return tuple(steps)
