import re
import json

from pathlib import Path
from typing import Iterable


_NUM = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?$")
_INCLUDE_C = False

# =========================
# Helpers
# =========================

def _pins(pins: str | list[str]) -> list[str]:
    """Normalize pins input to list[str]."""
    return pins.split() if isinstance(pins, str) else list(pins)


def _read(p: str | Path) -> list[str]:
    """Read file as list of lines (keeps newline)."""
    return Path(p).read_text().splitlines(True)


def _write(p: str | Path, s: str) -> None:
    """Write text, creating parent dir if needed."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s)


def _kv(t: list[str], start: int) -> dict[str, str]:
    """Parse key=value tokens (case-insensitive keys)."""
    d: dict[str, str] = {}
    for tok in t[start:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            d[k.strip().lower()] = v.strip()
    return d


def _join_plus(lines: Iterable[str]) -> list[str]:
    """Join SPICE continuation lines starting with '+' into one line."""
    out, cur = [], []
    for raw in lines:
        s = raw.rstrip("\n")
        if not s.strip() or s.lstrip().startswith(("*", ";")):
            continue
        if s.lstrip().startswith("+"):
            if cur:
                cur.append(s.lstrip()[1:].strip())
            continue
        if cur:
            out.append(" ".join(cur))
        cur = [s.strip()]
    if cur:
        out.append(" ".join(cur))
    return out


def _parse_params(param_file: str | Path) -> dict[str, int | float]:
    """Collect numeric .param values for W*/L*/NF* (plain numbers only)."""
    p: dict[str, int | float] = {}
    for line in _read(param_file):
        s = line.strip()
        if not s or s[0] in "*;" or not s.lower().startswith(".param"):
            continue
        for tok in s.split()[1:]:
            if "=" not in tok:
                continue
            k, v = tok.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if not k.upper().startswith(("W", "L", "NF")):
                continue
            if re.fullmatch(r"[+-]?\d+", v):
                p[k] = int(v)
            elif _NUM.fullmatch(v):
                p[k] = float(v)
    return p


def _num_um(x: str, p: dict[str, int | float]) -> float:
    """Resolve token to um number (param lookup or plain numeric literal)."""
    x = x.strip().strip("'\"")
    if x in p:
        return float(p[x])
    if re.fullmatch(r"[+-]?\d+", x):
        return float(int(x))
    if _NUM.fullmatch(x):
        return float(x)
    raise ValueError(f"Bad numeric token: {x}")


# =========================
# Main conversions
# =========================

def sch2tb(
    input_netlist: str | Path,
    testbench_path: str | Path,
    output_netlist: str | Path,
    ckt_name: str,
    ckt_pins: str | list[str],
) -> None:
    """
    Embed a circuit netlist as a .subckt inside a testbench.

    Looks for commented markers in the testbench:
      *.subckt ...
      *.ends
    and replaces that region with:
      .subckt <ckt_name> <ckt_pins...>
      <ckt_netlist>
      .ends

    Output file is written to: Path(output_netlist)
    """
    pins = _pins(ckt_pins)

    # Read and sanitize circuit netlist body (avoid nesting if already wrapped)
    body_lines: list[str] = []
    for line in _read(input_netlist):
        if re.match(r"^\s*\.(subckt|ends|end)\b", line, flags=re.IGNORECASE):
            continue
        body_lines.append(line)
    if body_lines and not body_lines[-1].endswith("\n"):
        body_lines[-1] = body_lines[-1] + "\n"

    subckt_lines = [
        f".subckt {ckt_name} {' '.join(pins)}\n",
        *body_lines,
        ".ends\n",
    ]

    tb_lines = _read(testbench_path)

    # Find the commented placeholder region: *.subckt ...  to  *.ends
    start = None
    for i, line in enumerate(tb_lines):
        if re.match(r"^\s*\*\s*\.subckt\b", line, flags=re.IGNORECASE):
            start = i
            break

    if start is not None:
        end = None
        for j in range(start + 1, len(tb_lines)):
            if re.match(r"^\s*\*\s*\.ends\b", tb_lines[j], flags=re.IGNORECASE):
                end = j
                break
        if end is None:
            end = start  # replace only the subckt marker line if no *.ends marker exists

        tb_lines[start : end + 1] = subckt_lines
    else:
        # Fallback: insert before .GLOBAL, else before final .end, else append
        insert_at = None
        for i, line in enumerate(tb_lines):
            if re.match(r"^\s*\.global\b", line, flags=re.IGNORECASE):
                insert_at = i
                break
        if insert_at is None:
            for i, line in enumerate(tb_lines):
                if re.match(r"^\s*\.end\b", line, flags=re.IGNORECASE):
                    insert_at = i
                    break
        if insert_at is None:
            insert_at = len(tb_lines)

        # Ensure a blank line separation around the inserted block
        block = []
        if insert_at > 0 and tb_lines[insert_at - 1].strip():
            block.append("\n")
        block.extend(subckt_lines)
        if insert_at < len(tb_lines) and tb_lines[insert_at].strip():
            block.append("\n")

        tb_lines[insert_at:insert_at] = block

    out_path = Path(output_netlist)
    _write(out_path, "".join(tb_lines))


def input2align(
    input_netlist: str | Path,
    input_param: str | Path,
    input_constraint: str | Path,
    output_dir: str | Path,
    ckt_name: str,
    ckt_pins: str | list[str],
    include_C: bool = _INCLUDE_C,
) -> None:
    """Input netlist+params -> ALIGN .sp (+ .const.json). Optionally convert caps."""
    pins, p = _pins(ckt_pins), _parse_params(input_param)
    out = [f"* ALIGN-compatible netlist for {ckt_name}\n",
           f".subckt {ckt_name} {' '.join(pins)}\n"]

    for s in _join_plus(_read(input_netlist)):
        t = s.split()
        if not t:
            continue
        n0 = t[0].lower()

        if n0.startswith("xm") and len(t) >= 6:  # MOS: l=<um>e-6, w=(W/nf)<um>e-6, nf
            kv = _kv(t, 6)
            L, W = _num_um(kv["l"], p), _num_um(kv["w"], p)
            nf = max(1, int(round(_num_um(kv.get("nf", "1"), p))))
            out.append(f"{t[0]} {t[1]} {t[2]} {t[3]} {t[4]} {t[5]} "
                       f"l={L:g}e-6 w={(W/nf):g}e-6 nf={nf}\n")

        elif include_C and n0.startswith(("xc", "c")) and len(t) >= 4:  # CAP: force name to C*
            kv = _kv(t, 4)
            W, L = _num_um(kv["w"], p), _num_um(kv["l"], p)
            name = ("C" + t[0][2:]) if t[0][:2].lower() == "xc" else t[0]
            out.append(f"{name} {t[1]} {t[2]} {t[3]} w={W:g}e-6 l={L:g}e-6\n")

    out.append(".ends\n")
    od = Path(output_dir)
    _write(od / f"{ckt_name}.sp", "".join(out))

    align_const = json.loads(Path(input_constraint).read_text())["align"]
    _write(od / f"{ckt_name}.const.json", json.dumps(align_const, indent=2) + "\n")


def input2netgen(
    input_netlist: str | Path,
    input_param: str | Path,
    output_netlist: str | Path,
    ckt_name: str,
    ckt_pins: str | list[str],
    include_C: bool = _INCLUDE_C,
) -> None:
    """Input netlist+params -> Netgen subckt. Optionally convert caps; cap name forced to C*."""
    pins, p = _pins(ckt_pins), _parse_params(input_param)
    out = [f"* Netgen-compatible netlist for {ckt_name}\n",
           f".subckt {ckt_name} {' '.join(pins)}\n"]

    for s in _join_plus(_read(input_netlist)):
        t = s.split()
        if not t:
            continue
        n0 = t[0].lower()

        if n0.startswith("xm") and len(t) >= 6:  # MOS: L/W in um, keep nf
            kv = _kv(t, 6)
            L, W = _num_um(kv["l"], p), _num_um(kv["w"], p)
            nf = max(1, int(round(_num_um(kv.get("nf", "1"), p))))
            out.append(f"{t[0]} {t[1]} {t[2]} {t[3]} {t[4]} {t[5]} "
                       f"L={L:.2f} W={W:.2f} nf={nf}\n")

        elif include_C and n0.startswith(("xc", "c")) and len(t) >= 4:  # CAP: keep W/L (um), force name to C*
            kv = _kv(t, 4)
            W, L = _num_um(kv["w"], p), _num_um(kv["l"], p)
            name = ("C" + t[0][2:]) if t[0][:2].lower() == "xc" else t[0]
            out.append(f"{name} {t[1]} {t[2]} {t[3]} W={W:g} L={L:g}\n")

    out.append(".ends\n")
    _write(output_netlist, "".join(out))


def align2netgen(
    input_netlist: str | Path,
    output_netlist: str | Path,
    ckt_name: str,
    include_C: bool = _INCLUDE_C,
) -> None:
    """ALIGN .sp -> Netgen subckt. MOS: meters->um and W=w*nf; CAP: meters->um (expects C*)."""
    out = [f"* Netgen-compatible netlist for {ckt_name}\n"]
    for s in _join_plus(_read(input_netlist)):
        t = s.split()
        if not t:
            continue
        n0 = t[0].lower()

        if n0.startswith((".subckt", ".ends")):
            out.append(s + "\n")
            continue

        if n0.startswith("xm") and len(t) >= 6:
            kv = _kv(t, 6)
            if "l" in kv and "w" in kv:
                l_m, w_m = float(kv["l"]), float(kv["w"])
                nf = max(1, int(float(kv.get("nf", "1"))))
                out.append(f"{t[0]} {t[1]} {t[2]} {t[3]} {t[4]} {t[5]} "
                           f"L={l_m*1e6:.2f} W={w_m*nf*1e6:.2f} nf={nf}\n")

        elif include_C and n0.startswith("c") and len(t) >= 4:
            kv = _kv(t, 4)
            if "l" in kv and "w" in kv:
                out.append(f"{t[0]} {t[1]} {t[2]} {t[3]} "
                           f"W={float(kv['w'])*1e6:g} L={float(kv['l'])*1e6:g}\n")

    _write(output_netlist, "".join(out))


def pex2tb(
    input_netlist: str | Path,
    testbench_path: str | Path,
    output_netlist: str | Path,
    top_module: str,
    ckt_name: str,
    ckt_pins: str | list[str],
) -> None:
    """
    Embed a full PEX SPICE netlist into a testbench.

    Replaces the testbench region between:
      *.subckt ...
      *.ends
    with the entire PEX file contents (minus any top-level `.end` lines).

    Also rewrites the top-level subckt header in the PEX netlist:
      .subckt <top_module> ...
    to:
      .subckt <ckt_name> <ckt_pins...>

    Output file: Path(output_netlist)
    """
    pins = _pins(ckt_pins)

    # ---- Read PEX netlist and patch top subckt name/pins ----
    pex_in = _read(input_netlist)
    pex_out: list[str] = []

    top_lc = top_module.lower()

    for line in pex_in:
        s = line.rstrip("\n")
        s_strip = s.strip()

        # Drop top-level ".end" (but NOT ".ends") to avoid ending the whole TB early
        if re.match(r"^\s*\.end\b", s_strip, flags=re.IGNORECASE) and not re.match(
            r"^\s*\.ends\b", s_strip, flags=re.IGNORECASE
        ):
            continue

        # Rewrite the target top-module .subckt line
        m = re.match(r"^\s*\.subckt\s+(\S+)\b(.*)$", s, flags=re.IGNORECASE)
        if m:
            name = m.group(1)
            if name.lower() == top_lc:
                pex_out.append(f".subckt {ckt_name} {' '.join(pins)}\n")
                continue

        # If .ends explicitly names the top_module, normalize it
        m2 = re.match(r"^\s*\.ends\s+(\S+)\b", s, flags=re.IGNORECASE)
        if m2 and m2.group(1).lower() == top_lc:
            pex_out.append(".ends\n")
            continue

        # Keep everything else as-is
        pex_out.append(line if line.endswith("\n") else line + "\n")

    # If we never found the .subckt <top_module>, still proceed (but output won't rename it)
    # (No exception; this keeps the flow robust for different PEX formats.)

    # ---- Read testbench and replace placeholder region ----
    tb_lines = _read(testbench_path)

    start = None
    for i, line in enumerate(tb_lines):
        if re.match(r"^\s*\*\s*\.subckt\b", line, flags=re.IGNORECASE):
            start = i
            break

    if start is not None:
        end = None
        for j in range(start + 1, len(tb_lines)):
            if re.match(r"^\s*\*\s*\.ends\b", tb_lines[j], flags=re.IGNORECASE):
                end = j
                break
        if end is None:
            end = start  # replace only the marker line if no *.ends exists

        tb_lines[start : end + 1] = pex_out
    else:
        # Fallback: insert before .GLOBAL, else before final .end, else append
        insert_at = None
        for i, line in enumerate(tb_lines):
            if re.match(r"^\s*\.global\b", line, flags=re.IGNORECASE):
                insert_at = i
                break
        if insert_at is None:
            for i, line in enumerate(tb_lines):
                if re.match(r"^\s*\.end\b", line, flags=re.IGNORECASE):
                    insert_at = i
                    break
        if insert_at is None:
            insert_at = len(tb_lines)

        block: list[str] = []
        if insert_at > 0 and tb_lines[insert_at - 1].strip():
            block.append("\n")
        block.extend(pex_out)
        if insert_at < len(tb_lines) and tb_lines[insert_at].strip():
            block.append("\n")

        tb_lines[insert_at:insert_at] = block

    out_path = Path(output_netlist)
    _write(out_path, "".join(tb_lines))
