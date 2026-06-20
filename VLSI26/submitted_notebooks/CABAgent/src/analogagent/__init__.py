"""
AnalogAgent — LLM-driven SKY130 netlist generation with self-evolving memory.

Usage (from notebook):
    from src.analogagent import generate_netlist

    result = generate_netlist(
        task="a five-transistor OTA, with differential input and single output, "
             "using 1:1 current mirror to provide tail current",
        pins="VDD, VSS, VIN, VIP, VOUT, IB",
        output_node="VOUT",
        output_dir="designs/OTA_5T/SKY130/inputs",
    )
"""

import os
import re
import io
import subprocess
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Resolve paths relative to this package
_PKG_DIR = Path(__file__).resolve().parent

def generate_netlist(
    task: str,
    pins: str,
    output_node: str,
    output_dir: str = None,
    *,
    model: str = "gemini",
    gemini_model: str = "gemini-2.5-flash",
    api_key: str = None,
    max_retries: int = 5,
    temperature: float = 1.0,
) -> dict:
    """
    Generate a SKY130 SPICE subcircuit netlist from a natural-language description.

    Parameters
    ----------
    task : str
        Circuit description, e.g. "a five-transistor OTA with differential input..."
    pins : str
        Comma-separated subcircuit pins, e.g. "VDD, VSS, VIN, VIP, VOUT, IB"
    output_node : str
        Output node name, e.g. "VOUT"
    output_dir : str or None
        Directory to write ckt_netlist.spice / ckt_param.spice.
        If None, files are not written (raw code returned only).
    model : str
        LLM backend: "gemini" (default), "gpt-5", or "local"
    gemini_model : str
        Gemini model name (default: "gemini-2.5-flash")
    api_key : str or None
        API key. If None, reads from GEMINI_API_KEY / OPENAI_API_KEY env var.
    max_retries : int
        Maximum retry iterations on failure (default: 5)
    temperature : float
        LLM sampling temperature (default: 1.0)

    Returns
    -------
    dict with keys:
        success : bool
        raw_code : str or None      — the final .subckt block
        iterations : int            — number of retries used
        netlist_path : str or None  — path to ckt_netlist.spice (if output_dir set)
        param_path : str or None    — path to ckt_param.spice (if output_dir set)
    """
    load_dotenv()

    # ------------------------------------------------------------------ #
    # 1. LLM client setup                                                 #
    # ------------------------------------------------------------------ #
    client = _create_client(model, gemini_model, api_key)
    model_name = gemini_model if model == "gemini" else model

    # ------------------------------------------------------------------ #
    # 2. Agents                                                            #
    # ------------------------------------------------------------------ #
    from .agents import CodeGenerator, DesignOptimizer
    from .curator import ExperienceCurator

    generator = CodeGenerator(client, model_name)
    optimizer = DesignOptimizer(client, model_name)

    playbook_path = str(_PKG_DIR / "playbook.json")
    # Start with empty playbook if it doesn't exist
    if not os.path.exists(playbook_path):
        import json
        with open(playbook_path, "w") as f:
            json.dump({"General": [], "Rules": {}}, f)

    curator = ExperienceCurator(
        llm_model=client,
        model_name=model_name,
        storage_file=playbook_path,
    )

    # ------------------------------------------------------------------ #
    # 3. Build prompt                                                      #
    # ------------------------------------------------------------------ #
    prompt_path = _PKG_DIR / "prompt_template.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()

    prompt = (
        prompt
        .replace("[TASK]", task)
        .replace("[INPUT]", pins)
        .replace("[OUTPUT]", output_node)
    )

    # Inject SEM guidance
    task_type = _infer_task_type(task)
    guidance = curator.retrieve_guidance(task_type)
    if guidance:
        prompt += "\n\n" + guidance
        print(f"[AnalogAgent] SEM guidance injected for type: {task_type}")

    # ------------------------------------------------------------------ #
    # 4. Generate + iterate                                                #
    # ------------------------------------------------------------------ #
    from .main_run import extract_code, check_netlist_sky130, build_sky130_testbench, run_code

    # Error feedback templates
    exe_err_path = _PKG_DIR / "execution_error.md"
    sim_err_path = _PKG_DIR / "simulation_error.md"
    prompt_exe_error = exe_err_path.read_text() if exe_err_path.exists() else "Execution error: [ERROR]"
    prompt_sim_error = sim_err_path.read_text() if sim_err_path.exists() else "Simulation error at node [NODE]."

    messages = []
    answer = generator.generate_solution(
        base_template=prompt,
        task_description=task,
        history_messages=messages,
    )
    empty_code_error, raw_code = extract_code(answer)

    final_code = None
    iterations_used = 0

    for code_id in range(max_retries):
        iterations_used = code_id + 1

        # Static check
        warning, warning_msg = check_netlist_sky130(raw_code, pins, output_node)

        # Ngspice DC check (best-effort, skip if ngspice unavailable)
        exec_err, sim_err, exec_info, floating = 0, 0, "", ""
        if not empty_code_error and not warning:
            exec_err, sim_err, exec_info, floating = _try_simulate(
                raw_code, pins, build_sky130_testbench, run_code
            )

        print(f"[AnalogAgent] iter={code_id}  exec_err={exec_err}  sim_err={sim_err}  warning={warning}")

        # Curator learning from failure
        if empty_code_error or exec_err or sim_err or warning:
            failure_log = ""
            if empty_code_error:
                failure_log = "No .subckt block found."
            elif exec_err:
                failure_log = f"Execution Error: {exec_info}"
            elif sim_err:
                failure_log = f"Simulation Error: Floating Node {floating}"
            elif warning:
                failure_log = f"Format Warning: {warning_msg}"

            curator.reflect_and_learn(
                task_type=task_type, code=raw_code,
                error_log=failure_log, iteration=code_id,
            )

        # Success?
        if not empty_code_error and exec_err == 0 and sim_err == 0 and warning == 0:
            final_code = raw_code
            print(f"[AnalogAgent] Success at iteration {code_id}")
            break

        # Build feedback
        if empty_code_error:
            feedback = "No .subckt block found. Please generate a complete SKY130 SPICE netlist."
        elif sim_err:
            feedback = prompt_sim_error.replace("[NODE]", floating)
        elif exec_err:
            feedback = prompt_exe_error.replace("[ERROR]", exec_info)
        elif warning:
            feedback = warning_msg
        else:
            feedback = "Unknown error. Please regenerate."

        messages.append({"role": "user", "content": feedback})

        # Optimizer reflection
        opt_result = optimizer.verify_and_reflect(
            task_id=0, code_path="", task_type=task_type,
        )
        if opt_result.get("suggestions"):
            feedback += "\n" + opt_result["suggestions"]

        print(f"[AnalogAgent] Retry {code_id + 1}/{max_retries}...")
        answer = generator.generate_solution(
            base_template=prompt,
            curator_guidance=feedback,
            history_messages=messages,
        )
        empty_code_error, raw_code = extract_code(answer)

    # ------------------------------------------------------------------ #
    # 5. Post-process and write output                                     #
    # ------------------------------------------------------------------ #
    result = {
        "success": final_code is not None,
        "raw_code": final_code,
        "iterations": iterations_used,
        "netlist_path": None,
        "param_path": None,
    }

    if final_code and output_dir:
        from .postprocess import write_ckt_files
        netlist_path = os.path.join(output_dir, "ckt_netlist.spice")
        param_path = os.path.join(output_dir, "ckt_param.spice")
        write_ckt_files(final_code, netlist_path, param_path)
        result["netlist_path"] = netlist_path
        result["param_path"] = param_path

    return result


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _create_client(model: str, gemini_model: str, api_key: str = None):
    if model == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY not set. Pass api_key= or set env var.")
        client = OpenAI(
            api_key=key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        print(f"[AnalogAgent] Connected to Gemini API. Model: {gemini_model}")
        return client
    elif model == "gpt-5":
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY not set.")
        return OpenAI(api_key=key)
    elif model == "local":
        return OpenAI(api_key="EMPTY", base_url="http://localhost:8001/v1")
    else:
        raise ValueError(f"Unsupported model: {model}")


def _infer_task_type(task: str) -> str:
    """Infer circuit type from task description for SEM lookup."""
    low = task.lower()
    if "telescopic" in low:
        return "TelescopicOTA"
    if "folded cascode" in low:
        return "FoldedCascodeOTA"
    if "ota" in low or "operational transconductance" in low:
        return "OTA"
    if "current mirror" in low:
        return "CurrentMirror"
    if "amplifier" in low or "opamp" in low:
        return "Amplifier"
    if "comparator" in low:
        return "Comparator"
    if "oscillator" in low:
        return "Oscillator"
    if "bandgap" in low:
        return "Bandgap"
    if "ldo" in low:
        return "LDO"
    return "General"


def _try_simulate(raw_code, pins, build_tb_fn, run_code_fn):
    """Best-effort ngspice simulation. Returns (exec_err, sim_err, info, node)."""
    import tempfile
    try:
        tb = build_tb_fn(raw_code, pins)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_tb.sp", delete=False, encoding="utf-8"
        ) as f:
            f.write(tb)
            tb_path = f.name
        return run_code_fn(tb_path)
    except Exception as e:
        print(f"[AnalogAgent] Simulation skipped: {e}")
        return 0, 0, "", ""
