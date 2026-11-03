"""Observable zero-supply startup for the full active ADC RC network."""
import math
import re

from scripts import flow2_waveforms as waves

SHIFT_S = 100e-9
RAMP_S = 20e-9


def validate_four_terminal_mos(netlist, model):
    primitives, count = set(), 0
    for line in netlist.splitlines():
        f = line.split()
        if not f or not f[0].lower().startswith("x"):
            continue
        names = [i for i, token in enumerate(f) if token.startswith("sky130_fd_pr__")]
        if len(names) != 1:
            raise ValueError("unidentified ADC primitive")
        i = names[0]
        if "__cap_" in f[i]:
            continue
        if i != 5 or not any(t in f[i] for t in ("__nfet_", "__pfet_")):
            raise ValueError("skywater parser profile requires four-terminal MOS")
        primitives.add(f[i])
        count += 1
    logical = re.sub(r"\r?\n\s*\+", " ", model)
    for primitive in primitives:
        declarations = re.findall(r"(?im)^\s*\.subckt\s+"+re.escape(primitive)+r"\s+([^\r\n]+)", logical)
        if len(declarations) != 1:
            raise ValueError("native MOS wrapper missing or repeated: "+primitive)
        ports = []
        for token in declarations[0].split():
            if "=" in token or token.lower() == "params:":
                break
            ports.append(token)
        if len(ports) != 4:
            raise ValueError("native MOS wrapper is not four terminal: "+primitive)
    if count != 34187:
        raise ValueError("pinned ADC MOS count changed")
    return {"MOS": count, "four_terminal_wrappers": sorted(primitives),
        "profile": "skywaterpdk; model parameter checks remain enabled"}


def deck(text, *, task, cm, diff, ramp_s=RAMP_S, load_shift_s=SHIFT_S,
         load_max_step_s=100e-12, conversion_max_step_s=.5e-9):
    """Ramp every nonzero independent source from zero; keep a real OP solve.

    Load stimulus/measurement times shift by 100ns. Conversion reset/start
    stay at 100/200ns, well after the explicit 20ns power ramp.
    """
    if task not in ("load", "conversion"):
        raise ValueError("invalid startup ADC task")
    if (not all(math.isfinite(v) and v > 0 for v in
                (ramp_s, load_shift_s, load_max_step_s, conversion_max_step_s))
            or ramp_s >= min(load_shift_s, 100e-9)):
        raise ValueError("power ramp must finish before reset release")
    shift_ns = load_shift_s/1e-9
    ramp = f"{ramp_s/1e-9:.12g}n"
    if task == "load":
        def shift(match):
            return f"{float(match[1])+shift_ns:.12g}n"
        lines = []
        for line in text.splitlines():
            if line.startswith(("VRST ", "VSTART ", "VINP ", "VINN ", ".measure ")):
                line = re.sub(r"(?<![\w.])([0-9]+(?:\.[0-9]*)?)n\b", shift, line)
            if line.startswith(".tran "):
                line = f".tran 100p {30+shift_ns:.12g}n 0 {load_max_step_s/1e-12:.12g}p"
            lines.append(line)
        text = "\n".join(lines)+"\n"
    else:
        text = text.replace(".tran 1n 3u 0 .5n", f".tran 1n 3u 0 {conversion_max_step_s/1e-9:.12g}n")
    stop = f"{30+shift_ns:.12g}n" if task == "load" else "3u"
    text = text.replace("VVDD VPWR 0 1.8", f"VVDD VPWR 0 PWL(0 0 {ramp} 1.8 {stop} 1.8)")
    text = text.replace("VVCM VCM 0 .9", f"VVCM VCM 0 PWL(0 0 {ramp} .9 {stop} .9)")
    for pol, sign in (("P", 1), ("N", -1)):
        initial = cm-sign*.001 if task == "load" else cm+sign*diff/2
        if task == "load":
            value = (f"VIN{pol} AIN{pol} 0 PWL(0 0 {ramp} {initial:.12g} "
                f"{8+shift_ns:.12g}n {initial:.12g} {10+shift_ns:.12g}n {initial+.01:.12g} {stop} {initial+.01:.12g})")
        else:
            value = f"VIN{pol} AIN{pol} 0 PWL(0 0 {ramp} {initial:.12g} 3u {initial:.12g})"
        text = re.sub(r"(?m)^VIN"+pol+r" .*?$", value, text)
    # Retain supply/control witnesses in the same raw plot as ADC outputs.
    extra = "v(VPWR) v(VCM) v(RST_N) v(START)"
    for prefix in (".save ", "write adc.raw "):
        text = re.sub(r"(?m)^"+re.escape(prefix)+r"(.*)$", lambda m:
            prefix+" ".join(dict.fromkeys(m[1].split()+extra.split())), text)
    if re.search(r"(?im)^\s*\.ic\b|\buic\b|\brshunt\b", text):
        raise ValueError("startup must remain an observable powered transient with OP")
    return text


def validate(vectors, *, task, ramp_s=RAMP_S, load_shift_s=SHIFT_S):
    for signal, target in (("v(VPWR)", 1.8), ("v(VCM)", .9), ("v(AINP)", 0.), ("v(AINN)", 0.)):
        initial = waves.sample(vectors, signal, 0.)
        if abs(initial) > 1e-7:
            raise ValueError("startup independent source was not zero: "+signal)
        if signal in ("v(VPWR)", "v(VCM)") and abs(waves.sample(vectors, signal, ramp_s+5e-9)-target) > 1e-5:
            raise ValueError("power/reference ramp did not settle: "+signal)
    release = load_shift_s+2e-9 if task == "load" else 100e-9
    if abs(waves.sample(vectors, "v(RST_N)", ramp_s+5e-9)) > .18:
        raise ValueError("reset not held during power-up")
    return {"power_ramp_end_s": ramp_s, "reset_release_start_s": release,
        "initial_sources_zero": True, "power_and_reference_settled": True,
        "scope": "observable startup, no forced internal IC/UIC; not ADC accuracy/retention/PVT"}


def compare_model_reference(current, reference):
    a, b = current["resistance_ohms"], reference["resistance_ohms"]
    if set(a) != set(b) or any(not math.isclose(a[k], b[k], rel_tol=1e-6, abs_tol=1e-9) for k in a):
        raise ValueError("fast parser resistor smoke differs from verified native-model reference")
