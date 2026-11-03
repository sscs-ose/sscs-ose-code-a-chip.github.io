"""A distinct fast power-ramp experiment with same-trajectory raw checkpoints.

Keep every modeled device, intentional resistor, native model and solver
tolerance. ``stop when time = ...`` / ``resume`` writes partial observations
without restarting the operating point. Partial plots are never a PASS.
"""
from pathlib import Path
import re

from scripts import flow2_waveforms as waves

PROFILE = {
    "name": "FAST_RAMP_SAME_TRAJECTORY_CHECKPOINTS_V6",
    "ramp_s": .5e-9,
    "load_shift_s": 20e-9,
    "load_max_step_s": 1e-9,
    "conversion_max_step_s": 2e-9,
    "load_stop_s": 50e-9,
    "conversion_stop_s": 3e-6,
    "load_checkpoint_s": [.5e-9, 5e-9, 20e-9, 32e-9],
    "conversion_checkpoint_s": [.5e-9, 20e-9, 100e-9, 300e-9, 1e-6, 2e-6],
    "scope": "new ideal-source startup stimulus; native transient validation required, not an ADC operating-point freeze",
}


def startup_options():
    return {k: PROFILE[k] for k in ("ramp_s", "load_shift_s", "load_max_step_s", "conversion_max_step_s")}


def checkpoint_deck(text, *, task):
    if task not in ("load", "conversion"):
        raise ValueError("invalid checkpoint task")
    points = PROFILE[task+"_checkpoint_s"]
    measurements = []
    outside = []
    for line in text.splitlines():
        if re.match(r"(?i)^\.measure\s+tran\s", line):
            measurements.append(re.sub(r"(?i)^\.measure\s+", "meas ", line))
        else:
            outside.append(line)
    text = "\n".join(outside)+"\n"
    found = re.findall(r"(?m)^write adc\.raw (.+)$", text)
    if len(found) != 1 or text.count(".control") != 1 or text.count(".endc") != 1:
        raise ValueError("one explicit ADC control block and raw write required")
    names = found[0].split()
    if task == "load" and not measurements:
        raise ValueError("load measurements must be deferred until full transient")
    if task == "conversion" and measurements:
        raise ValueError("unexpected conversion deck measurements")
    commands = [".control", "set filetype=ascii", "set numdgt=17",
        "echo AUTOMX_ADC_PHASE=DECK_PARSED", "rusage"]
    # All breakpoints are registered before run, as required by ngspice.
    commands += [f"stop when time = {time:.12g}" for time in points]
    commands += ["echo AUTOMX_ADC_PHASE=RUN_ENTER", "run"]
    for index, time in enumerate(points):
        commands += [f"write checkpoint_{index:02d}.raw {' '.join(names)}", "rusage",
            f"echo AUTOMX_ADC_CHECKPOINT={index:02d} TARGET_S={time:.12g}", "resume"]
    # .measure deck cards would run at every pause, creating out-of-window
    # errors and ambiguous scalar blocks. Execute meas only after final resume.
    if measurements:
        commands += ["echo Measurements for Transient Analysis", *measurements]
    commands += ["echo AUTOMX_ADC_PHASE=RUN_RETURNED",
        f"write adc.raw {' '.join(names)}", "rusage",
        "echo AUTOMX_ADC_PHASE=RAW_WRITTEN", ".endc"]
    return re.sub(r"(?ms)^\.control\s*$.*?^\.endc\s*$", lambda m: "\n".join(commands), text, count=1)


def observe(log, work=None):
    """Keep progress separate from completed scalar/conversion measurements."""
    references = re.findall(r"Reference value\s*:\s*([+\-\d.eE]+)", log)
    result = {
        "dynamic_gmin_completed": "Dynamic gmin stepping completed" in log,
        "last_transient_reference_s": float(references[-1]) if references else None,
        "checkpoints": [],
        "scope": "partial transient observations only; no conversion, input-load or signoff gate implied",
    }
    if work is not None:
        for path in sorted(Path(work).glob("checkpoint_*.raw")):
            item = {"filename": path.name, "status": "UNVALIDATED_PARTIAL"}
            try:
                vectors = waves.read_raw(path)
                item.update(status="VALID_PARTIAL_RAW", points=len(vectors["time"]),
                    start_s=float(vectors["time"][0]), stop_s=float(vectors["time"][-1]))
            except (OSError, ValueError) as error:
                item["error"] = str(error)
            result["checkpoints"].append(item)
    return result
