"""Immutable logical snapshots of an educational 6T SRAM access.

These states describe ordering and binary outcomes, not voltage or timing.
"""

from dataclasses import dataclass
from enum import Enum


class AccessPhase(str, Enum):
    PRECHARGE = "PRECHARGE"
    WORD_LINE_ACTIVE = "WORD_LINE_ACTIVE"
    BITLINE_DEVELOPMENT = "BITLINE_DEVELOPMENT"
    SENSE = "SENSE"
    READ_COMPLETE = "READ_COMPLETE"
    WRITE_DRIVER_ACTIVE = "WRITE_DRIVER_ACTIVE"
    BITLINES_DRIVEN = "BITLINES_DRIVEN"
    CELL_OVERWRITE = "CELL_OVERWRITE"
    WRITE_COMPLETE = "WRITE_COMPLETE"


@dataclass(frozen=True)
class PeripheralSnapshot:
    phase: AccessPhase
    q: int
    q_bar: int
    word_line: int
    bit_line: int | None
    bit_line_bar: int | None
    precharge_enabled: bool = False
    sense_enabled: bool = False
    write_driver_enabled: bool = False
    read_result: int | None = None
    write_value: int | None = None


def read_sequence(before: int, result: int) -> tuple[PeripheralSnapshot, ...]:
    """Describe precharge, access and sensing around an actual cell read result."""
    if before not in (0, 1) or result != before:
        raise ValueError("Read result must match the stored bit.")
    common = dict(q=before, q_bar=1-before)
    return (
        PeripheralSnapshot(AccessPhase.PRECHARGE, **common, word_line=0,
                           bit_line=1, bit_line_bar=1, precharge_enabled=True),
        PeripheralSnapshot(AccessPhase.WORD_LINE_ACTIVE, **common, word_line=1,
                           bit_line=1, bit_line_bar=1),
        PeripheralSnapshot(AccessPhase.BITLINE_DEVELOPMENT, **common, word_line=1,
                           bit_line=before, bit_line_bar=1-before),
        PeripheralSnapshot(AccessPhase.SENSE, **common, word_line=1,
                           bit_line=before, bit_line_bar=1-before, sense_enabled=True),
        PeripheralSnapshot(AccessPhase.READ_COMPLETE, **common, word_line=1,
                           bit_line=before, bit_line_bar=1-before, read_result=result),
    )


def write_sequence(before: int, value: int, after: int) -> tuple[PeripheralSnapshot, ...]:
    """Describe complementary drive and latch update around an actual write."""
    if before not in (0, 1) or value not in (0, 1) or after != value:
        raise ValueError("Write outcome must match the requested bit.")
    initial = dict(q=before, q_bar=1-before)
    driven = dict(bit_line=value, bit_line_bar=1-value, write_value=value)
    return (
        PeripheralSnapshot(AccessPhase.WRITE_DRIVER_ACTIVE, **initial, word_line=0,
                           bit_line=None, bit_line_bar=None, write_driver_enabled=True,
                           write_value=value),
        PeripheralSnapshot(AccessPhase.BITLINES_DRIVEN, **initial, word_line=0,
                           **driven, write_driver_enabled=True),
        PeripheralSnapshot(AccessPhase.WORD_LINE_ACTIVE, **initial, word_line=1,
                           **driven, write_driver_enabled=True),
        PeripheralSnapshot(AccessPhase.CELL_OVERWRITE, q=after, q_bar=1-after,
                           word_line=1, **driven, write_driver_enabled=True),
        PeripheralSnapshot(AccessPhase.WRITE_COMPLETE, q=after, q_bar=1-after,
                           word_line=1, **driven),
    )
