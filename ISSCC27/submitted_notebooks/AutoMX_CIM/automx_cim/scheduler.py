"""Stage-2 dependency-aware schedule for the tiny SKY130 MHA demonstrator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from .config import Sky130MHAConfig


@dataclass(frozen=True)
class TileCommand:
    """One controller-visible command in the logical tiny-MHA execution graph."""

    command_id: int
    phase: str
    operation: str
    projection: str | None
    token: int | None
    head: int | None
    k_tile: int | None
    m_tile: int | None
    input_tensor: str
    output_tensor: str
    input_range: tuple[int, int] | None
    output_range: tuple[int, int] | None
    weight_context: str | None
    depends_on: tuple[int, ...]

    def to_mapping(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("input_range", "output_range", "depends_on"):
            if data[key] is not None:
                data[key] = list(data[key])
        return data


def _projection_command(
    command_id: int, projection: str, token: int, m_tile: int,
    config: Sky130MHAConfig, dependencies: Iterable[int] = (),
) -> TileCommand:
    start = m_tile * config.logical_cols
    end = start + config.logical_cols - 1
    head = start // config.d_head
    input_tensor = "X" if projection in {"WQ", "WK", "WV"} else "CONTEXT"
    output_tensor = projection[1] if projection != "WO" else "Y"
    return TileCommand(
        command_id=command_id,
        phase="projection",
        operation="cim_projection",
        projection=projection,
        token=token,
        head=head,
        k_tile=0,
        m_tile=m_tile,
        input_tensor=input_tensor,
        output_tensor=output_tensor,
        input_range=(0, config.d_model - 1),
        output_range=(start, end),
        weight_context=f"{projection}:k0:m{m_tile}",
        depends_on=tuple(dependencies),
    )


def build_tiny_mha_schedule(config: Sky130MHAConfig) -> list[TileCommand]:
    """Build an executable dependency graph, not merely a command inventory.

    Q/K/V projections for all tokens are emitted first.  Two digital attention
    commands wait for their matching head slices.  Output projection commands
    wait for both context heads because every `WO` column consumes all 32
    context elements.
    """
    commands: list[TileCommand] = []
    produced: dict[tuple[str, int, int], int] = {}
    command_id = 0
    tiles = config.d_model // config.logical_cols

    for projection in ("WQ", "WK", "WV"):
        for token in range(config.sequence_length):
            for m_tile in range(tiles):
                command = _projection_command(command_id, projection, token, m_tile, config)
                commands.append(command)
                produced[(projection, token, m_tile)] = command_id
                command_id += 1

    attention_ids: list[int] = []
    tiles_per_head = config.d_head // config.logical_cols
    for head in range(config.n_heads):
        head_tiles = range(head * tiles_per_head, (head + 1) * tiles_per_head)
        dependencies = tuple(
            produced[(projection, token, m_tile)]
            for projection in ("WQ", "WK", "WV")
            for token in range(config.sequence_length)
            for m_tile in head_tiles
        )
        commands.append(TileCommand(
            command_id=command_id,
            phase="attention_runtime",
            operation="digital_qk_softmax_av",
            projection=None,
            token=None,
            head=head,
            k_tile=None,
            m_tile=None,
            input_tensor="QKV",
            output_tensor="CONTEXT",
            input_range=(head * config.d_head, (head + 1) * config.d_head - 1),
            output_range=(head * config.d_head, (head + 1) * config.d_head - 1),
            weight_context=None,
            depends_on=dependencies,
        ))
        attention_ids.append(command_id)
        command_id += 1

    for token in range(config.sequence_length):
        for m_tile in range(tiles):
            commands.append(_projection_command(
                command_id, "WO", token, m_tile, config, dependencies=attention_ids,
            ))
            command_id += 1
    validate_schedule(commands, config)
    return commands


def validate_schedule(commands: Iterable[TileCommand], config: Sky130MHAConfig) -> None:
    """Reject schedule corruption before it reaches a controller or RTL bench."""
    schedule = list(commands)
    ids = [command.command_id for command in schedule]
    if ids != list(range(len(schedule))):
        raise ValueError("command IDs must be contiguous and topologically ordered")
    expected = 3 * config.sequence_length * (config.d_model // config.logical_cols)
    expected += config.n_heads
    expected += config.sequence_length * (config.d_model // config.logical_cols)
    if len(schedule) != expected:
        raise ValueError(f"unexpected command count: got {len(schedule)}, expected {expected}")
    for command in schedule:
        if any(dependency >= command.command_id for dependency in command.depends_on):
            raise ValueError(f"command {command.command_id} has a future/self dependency")
        if command.operation == "cim_projection":
            if command.output_range is None or command.output_range[1] >= config.d_model:
                raise ValueError(f"command {command.command_id} has an invalid output range")
            if command.projection == "WO" and set(command.depends_on) != set(
                item.command_id for item in schedule if item.operation == "digital_qk_softmax_av"
            ):
                raise ValueError("WO must depend on every attention head context")


def schedule_manifest(config: Sky130MHAConfig, commands: Iterable[TileCommand]) -> dict[str, Any]:
    encoded = [command.to_mapping() for command in commands]
    command_json = json.dumps(encoded, sort_keys=True, separators=(",", ":"))
    return {
        "format": "automx-cim-mha-schedule-v1",
        "config": config.to_mapping(),
        "config_sha256": config.sha256,
        "command_count": len(encoded),
        "command_sha256": sha256(command_json.encode("utf-8")).hexdigest(),
        "breakdown": {
            "cim_qkv": sum(item["projection"] in {"WQ", "WK", "WV"} for item in encoded),
            "digital_attention": sum(item["operation"] == "digital_qk_softmax_av" for item in encoded),
            "cim_wo": sum(item["projection"] == "WO" for item in encoded),
        },
        "execution_order": "Q/K/V projections -> per-head digital QK/softmax/AV -> O projections",
    }


def write_stage2_schedule(config: Sky130MHAConfig, directory: str | Path) -> dict[str, Any]:
    """Write schedule plus manifest consumed by later RTL/controller stages."""
    commands = build_tiny_mha_schedule(config)
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    schedule_path = destination / "mha_tiny_schedule.json"
    manifest_path = destination / "mha_tiny_schedule_manifest.json"
    schedule_path.write_text(
        json.dumps([command.to_mapping() for command in commands], indent=2) + "\n", encoding="utf-8",
    )
    manifest = schedule_manifest(config, commands)
    manifest["files"] = {"schedule": {"path": schedule_path.name, "sha256": sha256(schedule_path.read_bytes()).hexdigest()}}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
