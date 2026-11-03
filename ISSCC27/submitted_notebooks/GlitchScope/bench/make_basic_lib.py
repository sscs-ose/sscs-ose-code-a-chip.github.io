"""Write bench/basic_cells.lib: the SKY130 HD Liberty restricted to the cells whose pulse
filtering is SPICE-calibrated (plus a buffer and the D flip-flop), so that Yosys/ABC map
benchmark circuits onto calibrated cells only.

    python bench/make_basic_lib.py [<full liberty>] [<out.lib>]

Default input: GS_LIB from tools.env; default output: bench/basic_cells.lib.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CELLS = ["a21oi_1", "and2_1", "buf_1", "dfxtp_1", "inv_1", "nand2_1", "nor2_1", "o21ai_0", "or2_1",
         "xnor2_1", "xor2_1"]


def block_end(text, start):
    depth, i = 0, start
    while True:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1


def main():
    sys.path.insert(0, str(ROOT))
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src is None:
        from glitchscope.test_support import lib_path_or_none
        src = lib_path_or_none()
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "bench/basic_cells.lib"
    text = Path(src).read_text()
    first = re.search(r'\n\s*cell\s*\(', text)
    header = text[:first.start()]
    lib_end = text.rstrip().rfind("}")
    parts = [header]
    for c in CELLS:
        m = re.search(r'\n\s*cell\s*\(\s*"?sky130_fd_sc_hd__%s"?\s*\)\s*\{' % re.escape(c), text)
        if not m:
            raise SystemExit(f"cell {c} not found in {src}")
        parts.append(text[m.start():block_end(text, m.end() - 1)])
    parts.append("\n}\n")
    out.write_text("".join(parts))
    print(f"wrote {out} ({len(CELLS)} cells)")


if __name__ == "__main__":
    main()
