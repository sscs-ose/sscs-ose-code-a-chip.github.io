#!/usr/bin/env python3
"""Generate per-UNROLL synthesis variants for the HashPareto flow.

For each UNROLL U in {1,2,4,8,16} it creates
  flow/variants/u<U>/src/    (4 SystemVerilog files, parameter baked in)
  flow/variants/u<U>/config.yaml

The parameterized RTL stays canonical at rtl/generated/; the per-variant copies
avoid relying on any synthesis-time parameter plumbing and make each run fully
self-contained for the competition notebook.

Usage:  python3 tools/gen_variants.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "rtl" / "generated"
ORIGINAL = ROOT / "rtl" / "original" / "rtl" / "core"
VARIANT_ROOT = ROOT / "flow" / "variants"

UNROLLS = [1, 2, 4, 8, 16]
CLOCK_PERIOD_NS = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0

PARAM_RE = re.compile(r"parameter\s+int\s+UNROLL\s*=\s*\d+")


def bake(text: str, unroll: int) -> str:
    match = PARAM_RE.search(text)
    if match is None:
        raise RuntimeError(f"no 'parameter int UNROLL = N' found:\n{text[:200]}")
    replacement = f"parameter int UNROLL = {unroll}"
    return text[: match.start()] + replacement + text[match.end():]


def strip_timescale(text: str) -> str:
    """Drop timeunit/timeprecision directives: Yosys's Verilog-2005 frontend
    (as invoked by LibreLane) rejects them, and they are irrelevant to
    synthesis."""
    lines = [
        ln
        for ln in text.splitlines()
        if not re.match(r"^\s*time(unit|precision)\s+[^;]*;?\s*$", ln)
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    top_src = strip_timescale((GENERATED / "sha_top.sv").read_text())
    core_src = strip_timescale((GENERATED / "sha256_core.sv").read_text())
    padder = ORIGINAL / "message_padder.sv"
    buffer = GENERATED / "digest_buffer.sv"
    padder_src = strip_timescale(padder.read_text())
    buffer_src = strip_timescale(buffer.read_text())

    for u in UNROLLS:
        d = VARIANT_ROOT / f"u{u}"
        src = d / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "sha_top.sv").write_text(bake(top_src, u))
        (src / "sha256_core.sv").write_text(bake(core_src, u))
        (src / "message_padder.sv").write_text(padder_src)
        (src / "digest_buffer.sv").write_text(buffer_src)

        cfg = d / "config.yaml"
        cfg.write_text(
            "\n".join(
                [
                    f"DESIGN_NAME: sha_top",
                    f"VERILOG_FILES: dir::src/*.sv",
                    "CLOCK_PORT: aclk",
                    f"CLOCK_PERIOD: {CLOCK_PERIOD_NS}",
                    "",
                ]
            )
        )
        print(f"{d.relative_to(ROOT)}")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())