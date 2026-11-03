from dataclasses import dataclass, field
from typing import Dict, Tuple, List

FS_PER_PS = 1000

def ps_to_fs(x) -> int:
    return int(round(float(x) * FS_PER_PS))

def fs_to_ps(x: int) -> float:
    return x / FS_PER_PS

@dataclass(frozen=True)
class Cell:
    name: str
    kind: str
    inputs: Dict[str, str]
    output: str
    rise_fs: int
    fall_fs: int
    library_cell: str = ""
    library_output_pin: str = ""

@dataclass
class Network:
    primary_inputs: List[str]
    primary_outputs: List[str]
    cells: List[Cell]
    initial_inputs: Dict[str, int]

@dataclass(frozen=True)
class StimulusEpoch:
    time_fs: int
    updates: Dict[str, int]
    epoch_id: int

@dataclass(order=True, frozen=True)
class ScheduledEvent:
    time_fs: int
    sequence: int
    event_id: int
    net: str = field(compare=False)
    new_value: int = field(compare=False)
    source_instance: str = field(compare=False)
    parent_event_ids: Tuple[int, ...] = field(compare=False, default=())

@dataclass(frozen=True)
class TraceEvent:
    event_id: int
    time_fs: int
    epoch_id: int
    net: str
    old_value: int
    new_value: int
    source_instance: str
    parent_event_ids: Tuple[int, ...]
