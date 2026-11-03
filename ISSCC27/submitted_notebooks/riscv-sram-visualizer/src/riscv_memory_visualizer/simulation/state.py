from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulationState:
    """
    Stores the current state of the visualizer.

    CPU execution fields are authoritative here. SRAM-related fields are
    legacy foundation placeholders retained for compatibility, not live cell
    observations or electrical quantities. Views and traces read actual
    SRAM cell/array snapshots instead.
    """

    # -----------------------
    # Processor state
    # -----------------------

    cpu_cycle: int = 0
    pc: int = 0

    instruction_text: str = ""

    # -----------------------
    # Memory operation
    # -----------------------

    operation: Optional[str] = None

    effective_address: Optional[int] = None

    selected_row: Optional[int] = None
    selected_column: Optional[int] = None

    # -----------------------
    # SRAM signals
    # -----------------------

    word_line: int = 0

    bit_line: float = 1.0
    bit_line_bar: float = 1.0

    q: int = 0
    q_bar: int = 1

    sense_enable: int = 0
    write_enable: int = 0

    # -----------------------
    # Visualization state
    # -----------------------

    phase: str = "IDLE"

    explanation: str = "System is idle."

    def reset_memory_signals(self) -> None:
        """
        Reset legacy signal placeholders; does not reset an SRAM model.
        """

        self.word_line = 0

        self.bit_line = 1.0
        self.bit_line_bar = 1.0

        self.sense_enable = 0
        self.write_enable = 0

        self.phase = "IDLE"
        self.explanation = "System is idle."
        
