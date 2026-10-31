#!/usr/bin/env python3
"""Convert locked Sail 0.14.1 instruction traces to T09 commit-port expectations.

This converter handles normal RV32I/Zicsr instructions, including byte/halfword
stores. Trap events need a separate oracle and must not be silently accepted.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STEP = re.compile(r"^\[(\d+)\] \[M\]: 0x([0-9a-fA-F]{8}) \(0x([0-9a-fA-F]{8})\)")
WRITE_REG = re.compile(r"^x(\d+) <- 0x([0-9a-fA-F]+)$")
WRITE_MEM = re.compile(r"^mem\[W,0x([0-9a-fA-F]+)\] <- 0x([0-9a-fA-F]+)$")
TRAP_CAUSE = re.compile(r"^CSR mcause \(0x342\) <- 0x([0-9a-fA-F]+)$")
TRAP_TVAL = re.compile(r"^CSR mtval \(0x343\) <- 0x([0-9a-fA-F]+)$")


def store_port(insn: int, address: int, value: int) -> tuple[int, int, int]:
    if insn & 0x7F != 0x23:
        raise ValueError(f"Sail memory write from non-store instruction 0x{insn:08x}")
    width = {0: 1, 1: 2, 2: 4}.get((insn >> 12) & 7)
    if width is None:
        raise ValueError(f"invalid RV32I store width 0x{insn:08x}")
    lane = address & 3
    if lane + width > 4 or lane % width:
        raise ValueError(f"unaligned Sail store address 0x{address:08x}")
    return (address & ~3, ((1 << width) - 1) << lane,
            (value & ((1 << (8 * width)) - 1)) << (8 * lane))


def parse_trace(lines: list[str], include_traps: bool = False) -> list[dict]:
    events: list[dict] = []
    current: dict | None = None
    for line in lines:
        if match := STEP.match(line):
            index, pc, insn = (int(part, 16) if pos else int(part)
                               for pos, part in enumerate(match.groups()))
            if index != len(events):
                raise ValueError(f"nonconsecutive Sail step {index}")
            current = {"index": index, "pc": pc, "insn": insn,
                       "rd": 0, "wdata": None, "mem_addr": None,
                       "mem_wstrb": 0, "mem_wdata": None}
            events.append(current)
            continue
        if current is None:
            continue
        if line.startswith("trapping ") or line.startswith("handling exc#"):
            if not include_traps:
                raise ValueError(f"trap trace needs separate oracle: step {current['index']}")
            current["kind"] = "trap"
        if include_traps and current.get("kind") == "trap":
            if match := TRAP_CAUSE.fullmatch(line):
                current["cause"] = int(match.group(1), 16)
            elif match := TRAP_TVAL.fullmatch(line):
                current["tval"] = int(match.group(1), 16)
            continue
        if match := WRITE_REG.fullmatch(line):
            rd, value = (int(match.group(1)), int(match.group(2), 16))
            if not 0 <= rd < 32 or current["rd"] or current["wdata"] is not None:
                raise ValueError(f"invalid or duplicate GPR write at step {current['index']}")
            if rd:
                current["rd"] = rd
                current["wdata"] = value & 0xFFFFFFFF
        elif match := WRITE_MEM.fullmatch(line):
            if current["mem_addr"] is not None:
                raise ValueError(f"multiple stores at step {current['index']}")
            address, value = (int(part, 16) for part in match.groups())
            (current["mem_addr"], current["mem_wstrb"],
             current["mem_wdata"]) = store_port(current["insn"], address, value)
    if not events:
        raise ValueError("Sail trace contains no instruction steps")
    for event in events:
        if event.get("kind") == "trap" and ("cause" not in event or "tval" not in event):
            raise ValueError(f"incomplete Sail trap record at step {event['index']}")
    return events


def compare_commits(expected: list[dict], observed: list[dict]) -> dict:
    last_cycle = -1
    last_kind: str | None = None
    for index, event in enumerate(observed):
        cycle = event.get("cycle")
        kind = event.get("kind")
        # The retirement and trap observation ports are independent.  In a
        # single-issue in-order pipeline an older normal instruction may retire
        # from WB in the same cycle that the following instruction raises a
        # precise trap in EX.  The testbench records the older commit first, so
        # that one commit->trap pair is a valid same-cycle ordering.  Every
        # other pair must still advance the cycle count.
        same_cycle_commit_trap = (
            cycle == last_cycle and last_kind == "commit" and kind == "trap"
        )
        if (not isinstance(cycle, int) or cycle < last_cycle or
                (cycle == last_cycle and not same_cycle_commit_trap)):
            return {"passed": False, "matched": index,
                    "reason": f"invalid event cycle ordering at index {index}"}
        last_cycle = cycle
        last_kind = kind
        if index >= len(expected):
            return {"passed": False, "matched": index,
                    "reason": "extra DUT commit after Sail reference ended"}
        oracle = expected[index]
        expected_kind = oracle.get("kind", "commit")
        if event.get("kind") != expected_kind:
            return {"passed": False, "matched": index,
                    "reason": f"event {index}: expected {expected_kind}, got {event.get('kind')}",
                    "expected": oracle, "observed": event}
        if expected_kind == "trap":
            for field in ("pc", "cause", "tval"):
                if event.get(field) != oracle[field]:
                    return {"passed": False, "matched": index,
                            "reason": f"trap {index} {field} mismatch",
                            "expected": oracle, "observed": event}
            continue
        fields = ("pc", "insn", "rd", "mem_wstrb")
        if oracle["rd"]:
            fields += ("wdata",)
        if oracle["mem_wstrb"]:
            fields += ("mem_addr",)
        for field in fields:
            if event.get(field) != oracle[field]:
                return {"passed": False, "matched": index,
                        "reason": f"commit {index} {field} mismatch",
                        "expected": oracle, "observed": event}
        if oracle["mem_wstrb"]:
            byte_mask = sum(0xFF << (8 * lane) for lane in range(4)
                            if oracle["mem_wstrb"] & (1 << lane))
            actual_data = event.get("mem_wdata")
            if (not isinstance(actual_data, int) or
                    (actual_data & byte_mask) != (oracle["mem_wdata"] & byte_mask)):
                return {"passed": False, "matched": index,
                        "reason": f"commit {index} strobed mem_wdata mismatch",
                        "expected": oracle, "observed": event}
    if len(observed) != len(expected):
        return {"passed": False, "matched": len(observed),
                "reason": f"missing {len(expected)-len(observed)} DUT commits"}
    return {"passed": True, "matched": len(expected)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dut-trace", type=Path,
                        help="evaluator-captured CPU commit/trap JSONL to compare")
    parser.add_argument("--include-traps", action="store_true",
                        help="parse Sail exception events using mcause/mtval writes")
    args = parser.parse_args()
    try:
        events = parse_trace(args.trace.read_text().splitlines(), args.include_traps)
        summary = {"steps": len(events), "stores": sum(x["mem_wstrb"] != 0
                                                    for x in events),
                   "gpr_writes": sum(x["rd"] != 0 for x in events),
                   "traps": sum(x.get("kind") == "trap" for x in events)}
        if args.dut_trace:
            observed = [json.loads(line) for line in
                        args.dut_trace.read_text().splitlines() if line.strip()]
            result = compare_commits(events, observed)
            print(json.dumps(summary | result))
            return 0 if result["passed"] else 1
        if args.output:
            with args.output.open("w") as output:
                for event in events:
                    output.write(json.dumps(event, separators=(",", ":")) + "\n")
        print(json.dumps(summary))
        return 0
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
