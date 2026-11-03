#!/usr/bin/env python3
"""T09 port-only latency, throughput and paired dependency-cycle checks.

Bus waits are NOT subtracted using DUT-selected ready signals. Dependent and
independent programs use identical externally fixed bus profiles; their cycle
difference measures the extra dependency penalty. Branch penalties without a
published bound are diagnostic only. No internal DUT signal names are assumed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path

if __package__:
    from .public_check import sources_from_filelist
else:
    from public_check import sources_from_filelist

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PC = 0x80000000
NOP = 0x13
PROFILES = ((1, 0), (8, 0), (1, 3))
KINDS = (("alu_rs1", 0), ("alu_rs2", 0), ("alu_both", 0),
         ("alu_rs1", 1), ("alu_rs1", 2), ("x0", 0),
         ("load_rs1", 0), ("load_rs2", 0), ("load_both", 0),
         ("load_store", 0), ("load_branch", 0))


def case_inventory() -> list[tuple[str, str, int, int, int]]:
    return [(f"{kind}_gap{gap}_response{latency}_ready{ready}", kind, gap, latency, ready)
            for kind, gap in KINDS
            for latency, ready in (PROFILES if kind.startswith("load_") else ((1, 0),))]


def apply_timing_groups(groups: dict, timing: dict) -> None:
    """Add one separately weighted cycle group; never debit legacy groups twice."""
    rows = timing["outcomes"]
    names = [row["name"] for row in rows]
    expected = {"continuous_addi", *(row[0] for row in case_inventory())}
    if timing.get("phase") not in {"run", "compile"} or \
            len(names) != len(expected) or set(names) != expected or \
            any(type(row.get("passed")) is not bool for row in rows):
        raise ValueError("T09 timing inventory incomplete, duplicated or changed")
    groups["CPU-PIPE-CYCLES"] = {"cases_passed": sum(row["passed"] for row in rows),
                                 "cases_total": len(rows)}


def addi(rd: int, rs: int, imm: int) -> int:
    return ((imm & 4095) << 20) | (rs << 15) | (rd << 7) | 0x13


def add(rd: int, rs1: int, rs2: int) -> int:
    return (rs2 << 20) | (rs1 << 15) | (rd << 7) | 0x33


def branch(rs1: int, rs2: int, offset: int) -> int:
    return (((offset >> 12) & 1) << 31) | (((offset >> 5) & 63) << 25) | \
        (rs2 << 20) | (rs1 << 15) | (1 << 12) | \
        (((offset >> 1) & 15) << 8) | (((offset >> 11) & 1) << 7) | 0x63


def program(kind: str, dependent: bool, gap: int = 0) -> tuple[list[int], int, int]:
    code = [addi(10, 0, 256), addi(11, 0, 11), *([NOP] * 6)]
    producer = len(code)
    is_load = kind.startswith("load_")
    code.append((10 << 15) | (2 << 12) | (1 << 7) | 3 if is_load
                else addi(0 if kind == "x0" else 1, 0, 17))
    code.extend([NOP] * gap)
    consumer = len(code)
    source = 1 if dependent else 11
    if kind.endswith("rs1"):
        code.append(add(2, source, 11))
    elif kind.endswith("rs2"):
        code.append(add(2, 11, source))
    elif kind.endswith("both"):
        code.append(add(2, source, source))
    elif kind == "x0":
        code.append(addi(2, 0, 1))
    elif kind == "load_store":
        code.append((source << 20) | (10 << 15) | (2 << 12) | (4 << 7) | 0x23)
    elif kind in {"load_branch", "branch"}:
        code.extend([branch(source, 0, 8), addi(5, 0, 55)])
    else:
        raise ValueError(kind)
    code.extend([NOP] * 8)
    return code, PC + 4 * producer, PC + 4 * consumer


def oracle(code: list[int]) -> list[dict]:
    """Independent ISA oracle for the probe's ALU/memory/control subset."""
    regs = [0] * 32
    memory = {256: 0x12345678}
    expected = []
    index = 0
    while index < len(code):
        insn = code[index]
        op = insn & 127
        rd, rs1, rs2 = (insn >> 7) & 31, (insn >> 15) & 31, (insn >> 20) & 31
        imm = insn >> 20
        imm = imm - 4096 if imm & 2048 else imm
        next_index = index + 1
        row = {"pc": PC + 4 * index, "insn": insn, "rd": 0, "strb": 0}
        if op == 0x13:
            value = (regs[rs1] + imm) & 0xffffffff
        elif op == 0x33:
            value = (regs[rs1] + regs[rs2]) & 0xffffffff
        elif op == 0x17:
            value = (PC + 4*index + (insn & 0xfffff000)) & 0xffffffff
        elif op == 3:
            value = memory.get((regs[rs1] + imm) & 0xffffffff, 0)
        elif op == 0x23:
            offset = ((insn >> 25) << 5) | ((insn >> 7) & 31)
            offset = offset - 4096 if offset & 2048 else offset
            address = (regs[rs1] + offset) & 0xffffffff
            memory[address] = regs[rs2]
            row.update(mem_addr=address, mem_data=regs[rs2], strb=15)
            value = 0
        elif op == 0x63:
            offset = ((insn >> 31) << 12) | (((insn >> 7) & 1) << 11) | \
                (((insn >> 25) & 63) << 5) | (((insn >> 8) & 15) << 1)
            offset = offset - 8192 if offset & 4096 else offset
            if regs[rs1] != regs[rs2]:
                next_index = index + offset // 4
            value = 0
        elif op == 0x6f:
            offset = ((insn >> 31) << 20) | (((insn >> 12) & 255) << 12) | \
                (((insn >> 20) & 1) << 11) | (((insn >> 21) & 1023) << 1)
            offset = offset - 2097152 if offset & 1048576 else offset
            value = PC + 4*index + 4
            next_index = index + offset//4
        elif op == 0x67:
            value = PC + 4*index + 4
            next_index = (((regs[rs1] + imm) & 0xfffffffe)-PC)//4
        else:
            raise ValueError(f"unsupported probe instruction {insn:08x}")
        if op in {0x13, 0x33, 0x17, 3, 0x6f, 0x67} and rd:
            regs[rd] = value
            row.update(rd=rd, data=value)
        expected.append(row)
        index = next_index
        if len(expected) > 256 or index < 0:
            raise ValueError("unbounded or invalid probe control flow")
    return expected


def decode_trace(stdout: str) -> list[dict]:
    rows = [json.loads(line[7:]) for line in stdout.splitlines() if line.startswith("TIMING ")]
    for row in rows:
        for key in ("pc", "insn", "data", "addr", "mem_addr", "mem_data", "memory_104"):
            if key in row:
                row[key] = int(row[key], 16)
    return rows


def validate_trace(code: list[int], rows: list[dict], response_cycles: int) -> dict:
    commits = [row for row in rows if row["kind"] == "commit"]
    expected = oracle(code)
    if len(commits) != len(expected):
        raise ValueError(f"commit count {len(commits)} != {len(expected)}")
    for index, (want, got) in enumerate(zip(expected, commits)):
        for key, value in want.items():
            if got.get(key) != value:
                raise ValueError(f"commit {index} {key}: {got.get(key)} != {value}")
    requests = [row for row in rows if row["kind"] == "request"]
    responses = [row for row in rows if row["kind"] == "response"]
    loads = sum(row["insn"] & 127 == 3 for row in expected)
    stores = [row for row in expected if row["strb"]]
    if len(requests) != loads + len(stores) or len(responses) != len(requests):
        raise ValueError("missing, repeated, or speculative data request/response")
    observed_stores = [row for row in requests if row["write"]]
    if [(row["addr"], row["data"], row["strb"]) for row in observed_stores] != \
            [(row["mem_addr"], row["mem_data"], row["strb"]) for row in stores]:
        raise ValueError("store bus transaction differs from oracle")
    for req, rsp in zip(requests, responses):
        if rsp["cycle"] - req["cycle"] < response_cycles:
            raise ValueError("response before externally configured latency")
    done = [row for row in rows if row["kind"] == "done"]
    if len(done) != 1 or done[0]["memory_104"] != (stores[-1]["mem_data"] if stores else 0):
        raise ValueError("missing completion or wrong final memory")
    return {"retired": len(commits), "first_commit_cycle": commits[0]["cycle"],
            "last_commit_cycle": commits[-1]["cycle"],
            "retirement_span_cycles": commits[-1]["cycle"] - commits[0]["cycle"] + 1,
            "commit_cycles": {str(row["pc"]): row["cycle"] for row in commits},
            "bus": [{"request_cycle": req["cycle"], "response_cycle": rsp["cycle"],
                     "response_wait_cycles": rsp["cycle"]-req["cycle"], "write": req["write"]}
                    for req, rsp in zip(requests, responses)]}


def check_continuous(rows: list[dict], count: int = 64) -> dict:
    fetches = [row for row in rows if row["kind"] == "fetch" and PC <= row["pc"] < PC + 4*count]
    commits = [row for row in rows if row["kind"] == "commit"]
    if len(commits) != count:
        raise ValueError("continuous ADDI retirement count differs from fixed inventory")
    if [row["pc"] for row in fetches] != [PC+4*i for i in range(count)]:
        raise ValueError("continuous ADDI fetches missing, duplicated or reordered")
    for i, (fetch, commit) in enumerate(zip(fetches, commits)):
        if commit["cycle"] != fetch["cycle"] + 4:
            raise ValueError(f"ADDI {i} fetch-to-commit latency is not four cycles")
        if i and (fetch["cycle"] != fetches[i-1]["cycle"]+1 or
                  commit["cycle"] != commits[i-1]["cycle"]+1):
            raise ValueError(f"ADDI {i}: unexpected fetch/retirement bubble")
    return {"steady_state_ipc": 1.0, "fetch_to_commit_cycles": 4}


def compare_pair(control: dict, dependent: dict, producer: int, consumer: int,
                 limit: int, control_budget: int | None = None) -> dict:
    def gap(run: dict) -> int:
        return run["commit_cycles"][str(consumer)] - run["commit_cycles"][str(producer)]
    control_gap, dependent_gap = gap(control), gap(dependent)
    extra = dependent_gap - control_gap
    total_extra = dependent["retirement_span_cycles"] - control["retirement_span_cycles"]
    dependency_passed = extra <= limit and total_extra <= limit
    budget_passed = control_budget is None or (
        control["retirement_span_cycles"] <= control_budget and
        dependent["retirement_span_cycles"] <= control_budget + limit)
    return {"control_commit_gap_cycles": control_gap, "dependent_commit_gap_cycles": dependent_gap,
            "extra_dependency_cycles": extra, "extra_workload_cycles": total_extra,
            "maximum_extra_cycles": limit, "dependency_penalty_passed": dependency_passed,
            "control_workload_budget_cycles": control_budget,
            "dependent_workload_budget_cycles": None if control_budget is None else control_budget+limit,
            "workload_budget_passed": budget_passed,
            "passed": dependency_passed and budget_passed}


def run(submission: Path) -> dict:
    started = time.monotonic()
    sources = sources_from_filelist(submission)
    provenance = {"rtl_sha256": {str(path.relative_to(submission/'rtl')):
                               hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
                  "checker_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in (Path(__file__), HERE/"t09_timing_tb.sv")}}
    outcomes, probes = [], []
    with tempfile.TemporaryDirectory(prefix="ic_bcmk_t09_timing_") as directory:
        work = Path(directory)
        build = work / "build"
        compiled = subprocess.run(
            ["verilator", "--binary", "--timing", "--assert", "-Wno-fatal", "-j", "4",
             "--top-module", "tb_t09_timing", "--Mdir", str(build), f"-I{ROOT}",
             f"-I{(submission/'rtl').resolve()}", *map(str, sources), str(HERE/"t09_timing_tb.sv")],
            text=True, capture_output=True, timeout=180)
        if compiled.returncode:
            return {"phase": "compile", "cases_total": 22, "cases_passed": 0,
                    "outcomes": [{"name": name, "passed": False}
                                 for name in ["continuous_addi", *(row[0] for row in case_inventory())]],
                    "error": (compiled.stdout+compiled.stderr)[-8000:], **provenance}
        binary = build / "Vtb_t09_timing"

        def simulate(code: list[int], latency: int, ready: int) -> tuple[dict, list[dict]]:
            image = work / "program.hex"
            image.write_text("".join(f"{word:08x}\n" for word in code+[NOP]*(256-len(code))))
            executed = subprocess.run([str(binary), f"+IMAGE={image}",
                                       f"+RETIRES={len(oracle(code))}",
                                       f"+RESPONSE_CYCLES={latency}", f"+READY_DELAY={ready}"],
                                      text=True, capture_output=True, timeout=20)
            if executed.returncode or "TIMING_PASS" not in executed.stdout:
                raise ValueError((executed.stdout+executed.stderr)[-3000:])
            rows = decode_trace(executed.stdout)
            return validate_trace(code, rows, latency), rows

        try:
            code = [addi((i % 31)+1, 0, i+1) for i in range(64)]
            metrics, rows = simulate(code, 1, 0)
            details = check_continuous(rows)
            outcomes.append({"name": "continuous_addi", "passed": True, **details, "metrics": metrics})
        except (ValueError, subprocess.TimeoutExpired) as exc:
            outcomes.append({"name": "continuous_addi", "passed": False, "error": str(exc)})
        for name, kind, gap, latency, ready in case_inventory():
            try:
                control_code, producer, consumer = program(kind, False, gap)
                dependent_code, _, _ = program(kind, True, gap)
                control, _ = simulate(control_code, latency, ready)
                dependent, _ = simulate(dependent_code, latency, ready)
                memory_count = sum(word & 127 in {3, 0x23} for word in control_code)
                # Published v1 bound: each serialized memory operation may add
                # response_cycles + ready_delay cycles; each load-use at most one.
                # Do NOT cancel common avoidable memory/front-end bubbles.
                budget = None if kind == "load_branch" else \
                    len(oracle(control_code)) + memory_count*(latency+ready)
                comparison = compare_pair(control, dependent, producer, consumer,
                                          1 if kind.startswith("load_") else 0, budget)
                outcomes.append({"name": name, **comparison, "control": control,
                                 "dependent": dependent})
            except (ValueError, subprocess.TimeoutExpired) as exc:
                outcomes.append({"name": name, "passed": False, "error": str(exc)})
        # No existing branch/JAL/JALR penalty limit: do not invent a scoring gate.
        for kind in ("taken_bne", "not_taken_bne", "jal", "jalr"):
            try:
                code, _, consumer = program("branch", False)
                target = consumer+8
                if kind == "not_taken_bne":
                    code[9] = branch(0, 0, 8)
                    target = consumer+4
                elif kind == "jal":
                    code[9] = (8 << 20) | (2 << 7) | 0x6f
                elif kind == "jalr":
                    code[0] = (12 << 7) | 0x17  # AUIPC x12, 0
                    code[9] = (44 << 20) | (12 << 15) | (2 << 7) | 0x67
                metrics, _ = simulate(code, 1, 0)
                cycles = metrics["commit_cycles"]
                probes.append({"name": kind, "scored": False,
                               "control_to_next_commit_gap_cycles": cycles[str(target)]-cycles[str(consumer)],
                               "metrics": metrics})
            except (ValueError, subprocess.TimeoutExpired) as exc:
                probes.append({"name": kind, "scored": False, "error": str(exc)})
    return {"task_id": "T09", "phase": "run", "timing_policy": "port_timing_v1",
            "cases_total": len(outcomes), "cases_passed": sum(row["passed"] for row in outcomes),
            "outcomes": outcomes, "diagnostic_probes": probes,
            "elapsed_seconds": round(time.monotonic()-started, 3), **provenance,
            "scope": "paired external cycle penalties, not internal stall-signal duration"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, default=HERE/"reference/T09")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.submission.resolve())
    if args.output:
        args.output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {"outcomes", "diagnostic_probes"}} if args.output else result, indent=2))
    return 0 if result["phase"] == "run" and result["cases_passed"] == result["cases_total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
