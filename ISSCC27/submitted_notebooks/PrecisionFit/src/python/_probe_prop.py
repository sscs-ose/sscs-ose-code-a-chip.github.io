"""Experiment: which property makes smtbmc-yices hang at ~step 11?

Renders the DUT template with one property neutralized, runs one sby task,
prints the deepest step reached.

Usage:  python3 src/python/_probe_prop.py <stream|live> <none|L2|L3|P4a|P4b|P4s|P2P3>
"""
import shutil
import sys
import tempfile
import time
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # noqa: E402  (src/python)
import paths  # noqa: E402
from build_comparison import headline_configs  # noqa: E402
import formal_verify as fv  # noqa: E402
import jinja2  # noqa: E402
import rtlgen as _rg  # noqa: E402
from reference import FILTER_A_SPEC, design_filter  # noqa: E402
from fixedpoint import FixedPointConfig  # noqa: E402

# property-name prefix -> (solo line to disable, replacement)
NEUTRALIZE = {
    "L2":  ("L2",  None),   # handled specially below
    "L3":  ("L3:", None),
    "P4a": ("P4a:", None),
    "P4b": ("P4b:", None),
    "P4s": ("P4s_", None),
    "P2P3": ("P2:", None),  # handled specially below
}


def _acc_bits(text: str) -> int:
    m = re.search(r"parameter\s+ACC_WIDTH\s*=\s*(\d+)", text)
    return int(m.group(1)) if m else 36


def render_variant(which: str, out: Path) -> Path:
    """Render DUT with all assert statements except property `which` removed."""
    tdir = out / "tpl"
    tdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(paths.VERILOG_DIR / "fir_symmetric.v.j2", tdir / "fir_symmetric.v.j2")
    shutil.copy(paths.VERILOG_DIR / "fir_nonuniform.v.j2", tdir / "fir_nonuniform.v.j2")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(tdir)),
                             trim_blocks=True, lstrip_blocks=True,
                             keep_trailing_newline=True)
    h = design_filter(FILTER_A_SPEC)
    cfg = FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=10,
        input_int_bits=2, input_frac_bits=14, acc_guard_bits=4,
        output_int_bits=2, output_frac_bits=14,
        rounding="round", saturate_output=True,
    )
    text = env.get_template("fir_symmetric.v.j2").render(**_rg.build_context(h, cfg, "probe"))

    if which == "Q1":
        # variant: f_acc_q1 cleared whenever the previous edge was not clean
        # (sound: after a reset edge out_data == 0 == f_requant(0)). Tests the
        # theory that free-reset $past interactions through f_requant are what
        # makes the live environment hard.
        old = "f_acc_q1     <= acc_reg;   // formal spec's own pipeline stage"
        new = ("f_acc_q1     <= (rst_n && f_rst_hist[0]) ? acc_reg : "
               "{ACC_WIDTH{1'b0}}; // [probe-q1]")
        assert old in text, "f_acc_q1 sample line not found"
        text = text.replace(old, new)

    if which == "Q2":
        # variant: P4s_a restated at the REGISTER boundary (guard corrected to
        # in_valid@(k-2): acc_reg@k = MAC(sr@(k-1)) freezes iff sr@(k-1)
        # == sr@(k-2) iff no load at edge k-2).
        old = ("            if (rst_n && f_rst_hist[0] && f_rst_hist[1]"
               " && !$past(in_valid)) begin\n"
               "                P4s_a: assert (acc_sum == $past(acc_sum));"
               "   // taps frozen ...\n"
               "            end")
        new = ("            if (rst_n && f_rst_hist[0] && f_rst_hist[1] && f_rst_hist[2] &&\n"
               "                !$past(in_valid, 2)) begin\n"
               "                P4s_a: assert (acc_reg == $past(acc_reg)); // [probe-q2]\n"
               "            end")
        assert old in text, "P4s_a block not found"
        text = text.replace(old, new)

    if which == "Q3":
        # variant: drop P4s_a entirely (redundant with L2a: sr freeze makes
        # the combinational acc_sum freeze trivially derivable, but the
        # cross-frame combinational equality forces expensive congruence
        # reasoning). P4s_b (output freeze) stays.
        old = ("            if (rst_n && f_rst_hist[0] && f_rst_hist[1]"
               " && !$past(in_valid)) begin\n"
               "                P4s_a: assert (acc_sum == $past(acc_sum));"
               "   // taps frozen ...\n"
               "            end\n")
        assert old in text, "P4s_a block not found"
        text = text.replace(old, "")

    if which == "Q5":
        # variant: P4s_b stated IN-FRAME via the spec function on a second
        # formal pipeline stage. f_acc_q2@k == acc_reg@(k-2), so
        #   out_data@k == f_requant(f_acc_q2@k)
        # is exactly the output freeze (out_data@k == out_data@(k-1)) given
        # P4b, but every term lives in the current frame -> no cross-frame
        # combinational congruence reasoning.
        old = ("            if (rst_n && f_rst_hist[0] && f_rst_hist[1] && f_rst_hist[2] &&\n"
               "                !$past(in_valid, 3)) begin\n"
               "                P4s_b: assert (out_data == $past(out_data));"
               " // ... so is the output\n"
               "            end")
        new = ("            if (rst_n && f_rst_hist[0] && f_rst_hist[1] && f_rst_hist[2] &&\n"
               "                !$past(in_valid, 3)) begin\n"
               "                P4s_b: assert (out_data == f_requant(f_acc_q2)); // [probe-q5]\n"
               "            end")
        assert old in text, "P4s_b block not found"
        # declare f_acc_q2 next to f_acc_q1 and pipeline it
        old2 = "    reg signed [{{ acc_bits - 1 }}:0] f_acc_q1;".replace(
            "{{ acc_bits - 1 }}", str(_acc_bits(text)))
        if old2 not in text:
            old2 = re.search(r"^\s*reg signed \[\d+:0\] f_acc_q1;", text,
                             re.M).group(0)
        text = text.replace(old2, old2 + "\n    " + old2.strip().replace(
            "f_acc_q1", "f_acc_q2"))
        old3 = "f_acc_q1     <= acc_reg;"
        assert old3 in text, "f_acc_q1 pipeline line not found"
        text = text.replace(old3, old3 + "\n"
                            "        f_acc_q2     <= f_acc_q1;"
                            "  // [probe-q5] second spec stage")

    if which == "Q7":
        # variant: register-level acc freeze with BOTH no-load edges in the
        # guard (acc_reg@k == acc_reg@(k-2) spans two production edges).
        old = ("            if (rst_n && f_rst_hist[0] && f_rst_hist[1] && f_rst_hist[2] &&\n"
               "                !$past(in_valid, 3)) begin\n"
               "                P4s_b: assert (out_data == $past(out_data));"
               " // ... so is the output\n"
               "            end")
        new = ("            if (rst_n && f_rst_hist[0] && f_rst_hist[1] && f_rst_hist[2] &&\n"
               "                !$past(in_valid, 2) && !$past(in_valid, 3)) begin\n"
               "                P4s_b: assert (acc_reg == $past(acc_reg, 2)); // [probe-q7]\n"
               "            end")
        assert old in text, "P4s_b block not found"
        text = text.replace(old, new)

    if which == "Q4":
        # variant: P4s_b restated at the register boundary. out_data@k =
        # requant(acc_reg@(k-1)) (P4b identity), so the output freeze follows
        # from acc_reg@k == acc_reg@(k-1) == acc_reg@(k-2), which holds when
        # edge k-2 performed no load (in_valid@(k-3) == 0). Register-history
        # equality avoids the cross-frame combinational miter.
        old = ("            if (rst_n && f_rst_hist[0] && f_rst_hist[1] && f_rst_hist[2] &&\n"
               "                !$past(in_valid, 3)) begin\n"
               "                P4s_b: assert (out_data == $past(out_data));"
               " // ... so is the output\n"
               "            end")
        new = ("            if (rst_n && f_rst_hist[0] && f_rst_hist[1] && f_rst_hist[2] &&\n"
               "                !$past(in_valid, 3)) begin\n"
               "                P4s_b: assert (acc_reg == $past(acc_reg, 2)); // [probe-q4]\n"
               "            end")
        assert old in text, "P4s_b block not found"
        text = text.replace(old, new)

    keep = which  # e.g. "P4a"
    prop_re = re.compile(
        r"\b(L2[a-p]?|L3|P1[a-d]|P2|P3|P4a|P4b|P4s_[ab]|P5):[ \t]*assert\b")

    exclude = bool(keep) and keep.startswith("!")  # "!P4b" = neutralize ONLY P4b
    keep = keep.lstrip("!") if keep else keep

    q_variant = keep is not None and keep.startswith("Q") and "," not in keep
    groups = [] if (keep is None or q_variant) else keep.split(",")

    def keep_label(lbl: str) -> bool:
        if keep is None or q_variant:
            return True  # Q-variants patch a line but keep ALL properties
        if exclude:
            keep_it = any(
                g == lbl
                or (g == "L2" and lbl.startswith("L2"))
                or (g == "P2P3" and lbl in ("P2", "P3"))
                or (g == "P4s" and lbl.startswith("P4s"))
                or (g == "P1" and lbl.startswith("P1"))
                for g in groups)
            return not keep_it
        return any(
            g == lbl
            or (g == "L2" and lbl.startswith("L2"))
            or (g == "P2P3" and lbl in ("P2", "P3"))
            or (g == "P4s" and lbl.startswith("P4s"))
            or (g == "P1" and lbl.startswith("P1"))
            for g in groups)

    # Replace each `LABEL: assert ( ... );` with `LABEL: begin end` so any
    # `if (...)` guard keeps a (null) body and the text stays parseable.
    out_lines, dropped = [], 0
    i = 0
    lines = text.splitlines()
    while i < len(lines):
        line = lines[i]
        m = prop_re.search(line)
        if not m or keep_label(m.group(1)):
            out_lines.append(line)
            i += 1
            continue
        # scan forward to the balanced close of `assert (`
        j = line.index("assert") + len("assert")
        buf = [line]
        depth = line.count("(") - line.count(")")
        # depth computed from after 'assert' onward; recompute properly:
        rest = line[j:]
        depth = rest.count("(") - rest.count(")")
        while depth > 0:
            i += 1
            line = lines[i]
            rest = line.split("//")[0]
            depth += rest.count("(") - rest.count(")")
            buf.append(line)
        # eat trailing `;` if it's on the closing line
        code = buf[-1].split("//")[0].rstrip()
        if not code.endswith(";"):
            i += 1
            buf.append(lines[i])
        indent = re.match(r"\s*", buf[0]).group(0)
        # NB: Yosys rejects labels on non-property statements (`P1a: begin end`)
        # so the label goes into the comment.
        out_lines.append(f"{indent}begin end  // [probe-off] {m.group(1)}")
        dropped += 1
        i += 1
    text = "\n".join(out_lines)
    print(f"  [probe] kept={keep!r} neutralized {dropped} assertions", flush=True)
    (out / "fir_probe.v").write_text(text + "\n")
    return out / "fir_probe.v"


def deepest_step(log: str) -> int:
    import re
    steps = [int(m) for m in re.findall(r"Checking assertions in step (\d+)", log)]
    return max(steps) if steps else -1


def main():
    env_name = sys.argv[1] if len(sys.argv) > 1 else "stream"
    which = sys.argv[2] if len(sys.argv) > 2 else "none"
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 120

    paths.ensure_dirs()
    info = headline_configs()["best_uniform"]
    wd = Path(tempfile.mkdtemp(prefix=f"probe_{env_name}_{which}_"))
    if which == "none":
        dut = Path(info["rtl_path"])
        module = info["module_name"]
    else:
        dut = render_variant(which, wd)
        module = "fir_probe"

    stream = (env_name == "stream")
    wrapper = fv._render_harness(dut, module, wd, stream_env=stream,
                                 top_name=f"harness_{env_name}")
    sby = fv._write_sby(f"{env_name}_probe", "bmc", "smtbmc yices",
                        f"harness_{env_name}", [wrapper, dut], wd)
    t0 = time.time()
    ok, log = fv._run_sby(sby, wd, timeout=timeout)
    print(f"[{env_name} / keep={which}] ok={ok} deepest_step={deepest_step(log)} "
          f"({time.time()-t0:.1f}s)", flush=True)
    tail = [ln for ln in log.splitlines()
            if "failed assertion" in ln or "TIMEOUT" in ln or "DONE" in ln]
    for ln in tail[-3:]:
        print("   " + ln.split("] ", 1)[-1], flush=True)


if __name__ == "__main__":
    main()
