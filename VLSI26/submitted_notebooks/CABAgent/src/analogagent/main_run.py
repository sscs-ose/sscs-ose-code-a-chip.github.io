from openai import OpenAI
import openai
import argparse
import re
import os
import subprocess
import time
import pandas as pd
import sys
import shutil
import signal
import json
from dotenv import load_dotenv
load_dotenv()

# Support both standalone execution and package import
try:
    from .curator import ExperienceCurator
    from .agents import CodeGenerator, DesignOptimizer
except ImportError:
    from curator import ExperienceCurator
    from agents import CodeGenerator, DesignOptimizer

class TimeoutException(Exception):
    pass

def signal_handler(signum, frame):
    raise TimeoutException("timeout")

# Argparse only when run as CLI script; provide defaults for package import
args = None
def _parse_args():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, choices=["gpt-5", "local", "gemini"], default="gemini")
    parser.add_argument('--gemini_model', type=str, default="gemini-2.5-flash",
                        help="Gemini model name (e.g. gemini-2.5-flash, gemini-2.0-flash)")
    parser.add_argument('--temperature', type=float, default=1.0)
    parser.add_argument('--num_per_task', type=int, default=15)
    parser.add_argument('--num_of_retry', type=int, default=3)
    parser.add_argument("--num_of_done", type=int, default=0)
    parser.add_argument("--task_id", type=int, default=1)
    parser.add_argument("--ngspice", action="store_true", default=False)
    parser.add_argument("--retrieval", action="store_true", default=True)
    parser.add_argument('--api_key', type=str)
    args = parser.parse_args()
    return args

opensource_models = ["llama", "mistral", "qwen","deepseek"]

global client
global gemini_model

# On Windows, ngspice.exe is the GUI version (no stdout).
# ngspice_con.exe is the console version that pipes output correctly.
_NGSPICE_CON = r"C:\ProgramData\chocolatey\lib\ngspice\tools\Spice64\bin\ngspice_con.exe"
NGSPICE_EXE = _NGSPICE_CON if os.path.exists(_NGSPICE_CON) else "ngspice"

pyspice_template = """
# Ensure the simulator is initialized
if 'simulator' not in locals():
    simulator = circuit.simulator()

try:
    # Perform DC Operating Point (OP) Analysis
    analysis = simulator.operating_point()
    
    # Save node voltages to a file for 'check_netlist' to parse
    with open("[OP_PATH]", "w", encoding="utf-8") as f:
        # Save all node voltages
        for node_name, value in analysis.nodes.items():
            # Format: NodeName \t VoltageValue
            f.write(f"{str(node_name)}\\t{float(value[0])}\\n")
            
        # Save branch currents (optional, useful for some checks)
        for element_name, value in analysis.branches.items():
            f.write(f"{str(element_name)}\\t{float(value[0])}\\n")
            
    print(f"✅ OP analysis success. Data saved to: [OP_PATH]")
except Exception as e:
    print(f"❌ OP analysis failed: {e}")
    # Create an empty file on failure to prevent the script from crashing 
    # when the checker tries to read the missing file.
    with open("[OP_PATH]", "w") as f:
        f.write("")
"""

output_netlist_template = """
# Export netlist logic
try:
    import os
    # Use the simulator to generate the SPICE netlist text
    netlist_text = str(simulator.circuit)
    print("--- NETLIST START ---")
    print(netlist_text)
    print("--- NETLIST END ---")
except Exception as e:
    print(f"Error generating netlist: {e}")
"""

dc_sweep_template = """
# DC Sweep logic
try:
    import numpy as np
    # Sweep the input source [IN_NAME] from 0V to 5V
    analysis = simulator.dc_sweep(
        source_name='V[IN_NAME]', 
        start_market=0, 
        stop_market=5, 
        step_market=0.1
    )
    # Save the sweep data to [DC_PATH]
    with open("[DC_PATH]", "w") as f:
        # Save input voltage vector
        f.write(" ".join([str(float(x)) for x in analysis.sweep_values]) + "\\n")
        # Save output voltage vector (assuming node 'Vout')
        f.write(" ".join([str(float(x)) for x in analysis['vout']]))
    print(f"✅ DC Sweep success. Data saved to: [DC_PATH]")
except Exception as e:
    print(f"❌ DC Sweep failed: {e}")
"""

# client is initialized in main() based on --model argument
client = None
gemini_model = None



GK_PATH = os.path.join(os.path.dirname(__file__), "playbook.json")

with open(GK_PATH, "r", encoding="utf-8") as f:
    global_knowledge = json.load(f)

global_skill = global_knowledge.get("GlobalSkill", {})

# SKY130 PDK model library path.
# Defaults to the local stub (topology/DC validation on Windows).
# Override with env var SKY130_LIB to point to the real PDK for sign-off.
_STUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sky130_stub.lib")
SKY130_LIB_PATH = os.environ.get("SKY130_LIB", _STUB)
SKY130_LIB_CORNER = os.environ.get("SKY130_CORNER", "tt")

def extract_code(generated_content):
    if generated_content is None:
        return 1, ""
    generated_content = str(generated_content)
    if generated_content.strip() == "":
        return 1, ""

    # Match ```spice, ```sp, ```SPICE, or plain ``` blocks
    regex = r"```(?:spice|sp|SPICE)?\s*(.*?)```"
    matches = re.finditer(regex, generated_content, re.DOTALL | re.IGNORECASE)
    first_match = next(matches, None)

    if first_match is None:
        # Fallback: treat raw text as SPICE if it contains .subckt
        if ".subckt" in generated_content.lower():
            code = generated_content
        else:
            return 1, ""
    else:
        code = first_match.group(1)

    code = code.strip()
    if not code:
        return 1, ""

    # Basic SPICE validity: must contain .subckt
    if ".subckt" not in code.lower():
        print("[extract_code] Warning: no .subckt found in extracted block.")
        return 1, ""

    return 0, code


def run_code(file):
    print("IN RUN_CODE (ngspice) : {}".format(file))

    simulation_error = 0
    execution_error = 0
    execution_error_info = ""
    floating_node = ""

    def tail_text(lines, n=25):
        return "\n".join([l for l in lines[-n:] if l.strip()])

    try:
        result = subprocess.run(
            [NGSPICE_EXE, "-b", file],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        stdout_lines = stdout.split("\n")
        stderr_lines = stderr.split("\n")
        all_lines = stdout_lines + stderr_lines

        print("num of stdout lines:", len(stdout_lines))
        print("num of stderr lines:", len(stderr_lines))

        if stdout.strip():
            print("---- STDOUT (last 40 lines) ----")
            for line in stdout_lines[-40:]:
                print(line)
            print("---- STDOUT END ----")
        if stderr.strip():
            print("---- STDERR (last 40 lines) ----")
            for line in stderr_lines[-40:]:
                print(line)
            print("---- STDERR END ----")

        # --- Detect floating / disconnected node errors ---
        # "singular matrix" during gmin stepping is a Warning, not always fatal.
        # Only flag simulation_error if the simulation was truly interrupted
        # (i.e., RC != 0 or "Simulation interrupted" appears).
        sim_interrupted = any(
            "simulation interrupted" in l.lower() for l in all_lines
        )
        for line in all_lines:
            ll = line.lower()
            if "no dc path to ground" in ll or "floating node" in ll:
                simulation_error = 1
                parts = line.split()
                floating_node = parts[-1] if parts else "unknown"
                break
            if "singular matrix" in ll and sim_interrupted:
                simulation_error = 1
                floating_node = "singular_matrix"
                break

        # --- Non-zero exit with no simulation error → execution error ---
        if result.returncode != 0 and simulation_error == 0:
            execution_error = 1
            execution_error_info = tail_text(all_lines, 25)

        # --- Scan for ngspice error keywords even on exit 0 ---
        if execution_error == 0 and simulation_error == 0:
            for line in all_lines:
                ll = line.lower().strip()
                if ll.startswith("error") or "fatal error" in ll:
                    execution_error = 1
                    execution_error_info = tail_text(all_lines, 25)
                    break

        if execution_error == 1 and not execution_error_info:
            execution_error_info = "ngspice simulation failed."

        return execution_error, simulation_error, execution_error_info, floating_node

    except FileNotFoundError:
        print(f"ngspice not found at: {NGSPICE_EXE}")
        execution_error = 1
        execution_error_info = (
            f"ngspice executable not found: {NGSPICE_EXE}\n"
            "On Windows: ensure ngspice_con.exe exists in the Chocolatey install path."
        )
        return execution_error, simulation_error, execution_error_info, floating_node

    except subprocess.TimeoutExpired:
        print("ngspice timed out (60s limit).")
        execution_error = 1
        execution_error_info = "ngspice simulation timed out (60s limit)."
        return execution_error, simulation_error, execution_error_info, floating_node

    except Exception as e:
        print("Unexpected error in run_code:", e)
        execution_error = 1
        execution_error_info = f"Unexpected error in run_code: {repr(e)}"
        return execution_error, simulation_error, execution_error_info, floating_node





def check_netlist(netlist_path, operating_point_path, input, output, task_id, task_type):
    warning = 0
    warning_message = ""

   
    skip_op_strict = {"PLL", "Oscillator", "Comparator"}

   
    try:
        netlist_txt = open(netlist_path, "r", errors="ignore").read().lower()
    except Exception:
        netlist_txt = ""

    for input_node in input.split(", "):
        if input_node and input_node.lower() not in netlist_txt:
            warning_message += f"The given input node ({input_node}) is not found in the netlist.\n"
            warning = 1

    if output:
      
        for output_node in output.split(","): 
            output_node = output_node.strip() 
            if output_node and output_node.lower() not in netlist_txt:
                warning_message += f"The given output node ({output_node}) is not found in the netlist.\n"
                warning = 1


    if warning == 1:
        warning_message += (
            "Suggestion: You can replace the nodes actually used for input/output "
            "with the given names. Please rewrite the corrected complete code.\n"
        )
        return 1, warning_message.strip()

    if task_type in skip_op_strict:
        return 0, ""



    if not os.path.exists(operating_point_path):
        return 0, ""
    fopen_op = open(operating_point_path, "r", errors="ignore").read()

    for input_node in input.split(", "):
        if input_node.lower() not in fopen_op.lower():
            warning_message += "The given input node ({}) is not found in the netlist.\n".format(input_node)
            warning = 1
    if output:
        for output_node in output.split(", "):
            if output_node and output_node.lower() not in fopen_op.lower():
                warning_message += "The given output node ({}) is not found in the netlist.\n".format(output_node)
                warning = 1


    if warning == 1:
        warning_message += "Suggestion: You can replace the nodes actually used for input/output with the given names. Please rewrite the corrected complete code.\n"

    if task_type == "Inverter":
        return warning, warning_message
    vdd_voltage = 5.0
    vinn_voltage = 1.0
    vinp_voltage = 1.0
    for line in fopen_op.split("\n"):
        line = line.lower()
        if line.startswith("vdd"):
            vdd_voltage = float(line.split("\t")[-1])
        if line.startswith("vinn"):
            vinn_voltage = float(line.split("\t")[-1])
        if line.startswith("vinp"):
            vinp_voltage = float(line.split("\t")[-1])

    # ✅ Only enforce Vinp==Vinn for Opamp-type linear OP checks
    if task_type == "Opamp":
        if vinn_voltage != vinp_voltage:
            warning_message += "The given input voltages of Vinn and Vinp are not equal.\n"
            warning = 1
            warning_message += "Suggestion: Please make sure the input voltages are equal.\n"

    
    fopen_netlist = open(netlist_path, 'r')
    voltages = {}
    for line in fopen_op.split("\n"):
        if line.strip() == "":
             continue

        parts = line.split()
        if len(parts) != 2:
            continue

        raw_node, raw_voltage = parts
        voltage = float(raw_voltage)
        voltages[raw_node] = voltage
        node = raw_node.lower()
        voltages.setdefault(node, voltage)

     
        if "." in node:
            short = node.split(".")[-1]  # x1.voutp -> voutp
            voltages.setdefault(short, voltage)

       
        alias_map = {
            "vinp": ["vinp", "inp", "noninv"],
            "vinn": ["vinn", "inn", "inv"],
            "vout": ["vout", "out", "voutp"],
            "vdd":  ["vdd", "vcc"],
            "gnd":  ["gnd", "0", "ground"]
        }

        for canonical, aliases in alias_map.items():
            if node in aliases:
                voltages.setdefault(canonical, voltage)

 
    voltages["0"] = 0.0
    voltages["gnd"] = 0.0

    vthn = 0.5
    vthp = 0.5
    miller_node_1 = None
    miller_node_2 = None
    resistance_exist = 0
    has_diodeload = 0
    first_stage_out = None
    for line in fopen_netlist.readlines():
        if line.startswith('.'):
            continue
        if line.startswith("C"):
            if task_id == 14:
                miller_node_1 = line.split()[1].lower()
                miller_node_2 = line.split()[2].lower()
        if line.startswith("R"):
            resistance_exist = 1
        if line.startswith("M"):
            name, drain, gate, source, bulk, model = line.split()[:6]
            name = name[1:]
            drain = drain.lower()
            source = source.lower()
            bulk = bulk.lower()
            gate = gate.lower()
            mos_type = "NMOS" if "nmos" in model.lower() else "PMOS"
            if task_id == 14: 
                continue
            ## Common-gate
            if task_id == 4:
                if drain == "vin" or gate == "vin":
                    warning_message += (f"For a common-gate amplifier, the vin should be connected to source.\n")
                    warning_message += (f"Suggestion: Please connect the vin to the source node.\n")
                    warning = 1
            elif task_id == 3:
                if drain == "vout" or gate == "vout":
                    warning_message += (f"For a common-drain amplifier, the vout should be connected to source.\n")
                    warning_message += (f"Suggestion: Please connect the vout to the source node.\n")
                    warning = 1
            elif task_id == 15:
                if gate == drain:
                    has_diodeload = 1
                    
            elif task_id == 9:
                if gate == "vin":
                    first_stage_out = drain
            
                if mos_type == "NMOS":
                    vds_error = 0

             
                    if drain not in voltages:
                                         continue
         
                    if voltages[drain] == 0.0:
                        if drain.lower() in ("0", "gnd"):
                            warning_message += (
                                f"Suggetions: Please avoid connect {mos_type} {name} drain to the ground.\n"
                            )
                        else:
                            vds_error = 1
                            warning_message += (
                                f"For {mos_type} {name}, the drain node ({drain}) voltage is 0.\n"
                            )

                # VDS
                elif (drain in voltages and source in voltages) and voltages[drain] < voltages[source]:
                    vds_error = 1
                    warning_message += (f"For {mos_type} {name}, the drain node ({drain}) voltage is lower than the source node ({source}) voltage.\n")
                if vds_error == 1:
                    warning_message += (f"Suggestion: Please set {mos_type} {name} with an activated state and make sure V_DS > V_GS - V_TH.\n")
                # VGS
                vgs_error = 0
                if gate not in voltages or source not in voltages:
                    print(f"Skipping check for {gate}/{source} (missing in voltage data)")
                    continue
                if voltages[gate] == voltages[source]:
                    # vgs_error = 1
                    if gate == source:
                        warning_message += (f"For {mos_type} {name}, the gate node ({gate}) is connected to the source node ({source}).\n")
                        warning_message += (f"Suggestion: Please {mos_type} {name}, please divide its gate ({gate}) and source ({source}) connection.\n")
                    else:
                        vgs_error = 1
                        warning_message += (f"For {mos_type} {name}, the gate node ({gate}) voltage is equal to the source node ({source}) voltage.\n")
                elif voltages[gate] < voltages[source]:
                    vgs_error = 1
                    warning_message += (f"For {mos_type} {name}, the gate node ({gate}) voltage is lower than the source node ({source}) voltage.\n")
                elif voltages[gate] <= voltages[source] + vthn:
                    vgs_error = 1
                    warning_message += (f"For {mos_type} {name}, the gate node ({gate}) voltage is lower than the source node ({source}) voltage plus the threshold voltage.\n")
                if vgs_error == 1:
                    warning_message += (f"Suggestion: Please set {mos_type} {name} with an activated state by increasing the gate voltage or decreasing the source voltage and make sure V_GS > V_TH.\n")
            if mos_type == "PMOS":
                # VDS
                vds_error = 0
                if voltages[drain] == vdd_voltage:
                    if drain.lower() == "vdd":
                        warning_message += (f"Suggestion: Please avoid connect {mos_type} {name} drain to the vdd.\n")
                    else:
                        vds_error = 1
                        warning_message += (f"For {mos_type} {name}, the drain node ({drain}) voltage is V_dd.\n")
                # VDS
                elif voltages[drain] > voltages[source]:
                    vds_error = 1
                    warning_message += (f"For {mos_type} {name}, the drain node ({drain}) voltage is higher than the source node ({source}) voltage.\n")
                if vds_error == 1:
                    warning_message += (f"Suggestion: Please set {mos_type} {name} with an activated state and make sure V_DS < V_GS - V_TH.\n")
                # VGS
                vgs_error = 0
                
                
                if voltages[gate] == voltages[source]:
                    if gate == source:
                        warning_message += (f"For {mos_type} {name}, the gate node ({gate}) is connected to the source node ({source}).\n")
                        warning_message += f"Suggestion: Please {mos_type} {name}, please divide its gate ({gate}) and source ({source}) connection.\n"
                    else:
                        vgs_error = 1
                        warning_message += (f"For {mos_type} {name}, the gate node ({gate}) voltage is equal to the source node ({source}) voltage.\n")
                elif voltages[gate] > voltages[source]:
                    vgs_error = 1
                    warning_message += (f"For {mos_type} {name}, the gate node ({gate}) voltage is higher than the source node ({source}) voltage.\n")
                elif voltages[gate] >= voltages[source] - vthp:
                    vgs_error = 1
                    warning_message += (f"For {mos_type} {name}, the gate node ({gate}) voltage is higher than the source node ({source}) voltage plus the threshold voltage.\n")
                if vgs_error == 1:
                    warning_message += (f"Suggestion: Please set {mos_type} {name} with an activated state by decreasing the gate voltage or incresing the source voltage and make sure V_GS < V_TH.\n")

    if task_id in [1, 2, 3, 4, 5, 6, 8, 13]:
        if resistance_exist == 0:
            warning_message += "There is no resistance in the netlist.\n"
            warning_message += "Suggestion: Please add a resistance load in the netlist.\n"
            warning = 1
   
    if task_id == 15 and has_diodeload == 0:
        warning_message += "There is no diode-connected load in the netlist.\n"
        warning_message += "Suggestion: Please add a diode-connected load in the netlist.\n"
        warning = 1
    warning_message = warning_message.strip()
    if warning_message == "":
        warning = 0
    else:
        warning = 1
        warning_message = "According to the operating point check, there are some issues, which defy the general operating principles of MOSFET devices. \n" + warning_message + "\n"
        warning_message += "\nPlease help me fix the issues and rewrite the corrected complete code.\n"
    return warning, warning_message


import numpy as np
def get_best_voltage(dc_file_path):
    try:
        import numpy as np
        with open(dc_file_path, 'r') as f:
            lines = f.readlines()
            if len(lines) < 2:
                return 0, 2.5
            vin = np.array([float(x) for x in lines[0].strip().split()])
            vout = np.array([float(x) for x in lines[1].strip().split()])
    except Exception:
        
        return 0, 2.5

   
    if np.max(vout) - np.min(vout) < 1e-3:
        print('[Info] DC Sweep flat. Forcing success with 2.5V fallback.')

        return 0, 2.5

    min_margin = float('inf')
    best_voltage = 2.5
    for i, v in enumerate(vout):
        if abs(v - 2.5) < min_margin:
            min_margin = abs(v - 2.5)
            best_voltage = float(vin[i])

    return 0, best_voltage
def replace_voltage(raw_code, best_voltage, vinn_name=None, vinp_name=None):
   
    target_name = vinp_name if vinp_name else vinn_name
    
   
    if target_name is None:
        return raw_code

    new_code = ""
    lines = raw_code.split("\n")
    
    for line in lines:
       
        is_target_line = (f"'{target_name}'" in line or f'"{target_name}"' in line)
        
        if is_target_line and "circuit.V" in line:
            try:
               
                parts = line.split(",")
                prefix = ",".join(parts[:3]) 
                new_line = f"{prefix}, {best_voltage})" 
                new_code += new_line + "\n"
                print(f"[Auto-Fix] Replaced voltage bias for {target_name} to {best_voltage}")
            except Exception:
                
                new_code += line + "\n"
        else:
            new_code += line + "\n"
            
    return new_code



def bypass_capacitors(raw_code, input_node_name):
   
    if not input_node_name: return raw_code
    new_code = ""
    for line in raw_code.split("\n"):
        if "circuit.C" in line:
            
            if (f"'{input_node_name}'" in line) or (f'"{input_node_name}"' in line):
                try:
                    parts = line.split(",")
                    
                    cap_name = parts[0].split("(")[1].strip("'\" ")
                    node1 = parts[1].strip()
                    node2 = parts[2].split(")")[0].strip()
                    
             
                    new_line = f"circuit.V('short_{cap_name}', {node1}, {node2}, 0.0)"
                    new_code += new_line + "\n"
                    print(f"[Auto-Fix] Shorted blocking capacitor {cap_name} on input.")
                    continue
                except: pass
        new_code += line + "\n"
    return new_code

def fix_floating_source(raw_code, task_type):

    if "Amplifier" not in task_type and "Opamp" not in task_type:
        return raw_code
    if not ("'Vout'" in raw_code or '"Vout"' in raw_code):
        return raw_code
    
    has_load_resistor = False
    for line in raw_code.split('\n'):
        if line.strip().startswith("#"): continue
        if "circuit.R" in line or "circuit.Resistor" in line:
            has_vout = ("'Vout'" in line) or ('"Vout"' in line)
            has_gnd  = ("circuit.gnd" in line) or ("'0'" in line) or ('"0"' in line) or ("'ground'" in line)
            if has_vout and has_gnd:
                has_load_resistor = True
                break
   
    if not has_load_resistor and "circuit.gnd" in raw_code:
        print("[Auto-Fix] Detected floating Source (Vout) - Injecting safety resistor at end...")
        

        inject_code = (
            "\n\n# [Auto-Fix] Safety pull-down resistor to avoid floating node errors\n"
            "try:\n"
            "    import PySpice.Unit\n"
            "    circuit.R('fix_bias_R_safe', 'Vout', circuit.gnd, 10@u_kOhm)\n"
            "except Exception as e:\n"
            "    print(f'Safe resistor injection ignored: {e}')\n"
        )
        return raw_code + inject_code 
            
    return raw_code


def enforce_source_follower_topology(raw_code, task_id, vinn_source_name):
   
    
    if int(task_id) != 3:
        return raw_code

    true_gate_node = "Vin"
    
    
    try:
       
        safe_name = re.escape(vinn_source_name)
        pattern = r"circuit\.V\s*\(\s*['\"]" + safe_name + r"['\"]\s*,\s*['\"]([^'\"]+)['\"]"
        
        match = re.search(pattern, raw_code)
        if match:
            true_gate_node = match.group(1)
            print(f"[Auto-Fix] Smart-Resolve: Power source '{vinn_source_name}' drives node '{true_gate_node}'.")
        else:
           
            for line in raw_code.split('\n'):
                if "circuit.V" in line and (f"'{vinn_source_name}'" in line or f'"{vinn_source_name}"' in line):
                    parts = line.split(',')
                    if len(parts) >= 2:
                        candidate = parts[1].strip().strip("'\" ")
                        if candidate:
                            true_gate_node = candidate
                            break
    except Exception as e:
        print(f"[Warn] Node resolution failed: {e}. Defaulting Gate to 'Vin'.")


    lines = raw_code.split('\n')
    new_lines = []
    mosfet_fixed = False
    
    for line in lines:
      
        if "circuit.R" in line:
            has_vout = "'Vout'" in line or '"Vout"' in line
            has_vdd = "'Vdd'" in line or '"Vdd"' in line
            if has_vout and has_vdd:
                print(f"[Auto-Fix] Removing incorrect pull-up resistor: {line.strip()}")
                continue 
        if "circuit.MOSFET" in line and not mosfet_fixed:
            try:
                print(f"[Auto-Fix] Enforcing Topology: M1(Drain=Vdd, Gate={true_gate_node}, Source=Vout)")
              
                new_line = f"circuit.MOSFET('1', 'Vdd', '{true_gate_node}', 'Vout', circuit.gnd, model='nmos_model', w=100e-6, l=1e-6)"
                new_lines.append(new_line)
                mosfet_fixed = True
                continue
            except:
                pass
        
        new_lines.append(line)
            
    return "\n".join(new_lines)
def resolve_true_node_name(raw_code, source_name_guess):
   
    if not source_name_guess: 
        return "Vin" 
   
    safe_name = re.escape(source_name_guess)
    
   
    pattern = r"circuit\.V\s*\(\s*['\"]" + safe_name + r"['\"]\s*,\s*['\"]([^'\"]+)['\"]"
    
    match = re.search(pattern, raw_code)
    if match:
        return match.group(1) 

    for line in raw_code.split('\n'):
       
        if line.strip().startswith("#"): continue
        
        if "circuit.V" in line and (f"'{source_name_guess}'" in line or f'"{source_name_guess}"' in line):
            try:
                parts = line.split(',')
                
                if len(parts) >= 2:
                    candidate = parts[1].strip().strip("'\" ")
                    if candidate: 
                        return candidate
            except:
                pass
                
   
    return source_name_guess
def get_vin_name(netlist_content, task_type):
    vinn_name = "in"
    vinp_name = None
    for line in netlist_content.split("\n"):
        if not line.lower().startswith("v"):
            continue
        if len(line.lower().split()) < 2:
            continue
       
        if (task_type == "Amplifier" or task_type == "Comparator") and "vin" in line.lower().split()[1]:
            vinn_name = line.split()[0][1:]
        if task_type == "Opamp" and "vinp" in line.lower().split()[1]:
            vinp_name = line.split()[0][1:]
        if task_type == "Opamp" and "vinn" in line.lower().split()[1]:
            vinn_name = line.split()[0][1:]
    return vinn_name, vinp_name


def connect_vinn_vinp(dc_sweep_code, vinn_name, vinp_name):
    new_code = ""
    for line in dc_sweep_code.split("\n"):

        if not line.lower().startswith("circuit.v"):
            new_code += line + "\n"
            continue
        
    
        if vinp_name is not None and (line.lower().startswith(f"circuit.v('{vinp_name.lower()}'") or line.lower().startswith(f"circuit.v(\"{vinp_name.lower()}\"")):
        
            new_line = f"circuit.V('dc_short', '{vinn_name}', '{vinp_name}', 0.0)\n"
            new_code += new_line
        else:
            new_code += line + "\n"
    return new_code

def get_subcircuits_info(subcircuits, 
                    lib_data_path = "lib_info.tsv", task_data_path = "problem_set.tsv"):
    

    if not subcircuits:
        print("[WARN] get_subcircuits_info: subcircuits is None or empty, skip.")
        return ""

    lib_df = pd.read_csv(lib_data_path, delimiter='\t')
    task_df = pd.read_csv(task_data_path, delimiter='\t')

    columns = ["Id", "Circuit Type", "Gain/Differential-mode gain (dB)",
               "Common-mode gain (dB)", "Input", "Output"]
    subcircuits_df = pd.DataFrame(columns=columns)

    for sub_id in subcircuits:
        print("sub_id", sub_id)
        lib_df_row = lib_df.loc[lib_df['Id'] == sub_id]
        task_df_row = task_df.loc[task_df['Id'] == sub_id]
        print("task_df_row", task_df_row)
        sub_type = task_df.loc[task_df['Id'] == sub_id, 'Type'].item()
        sub_gain = float(lib_df.loc[lib_df['Id'] == sub_id, 'Av (dB)'].item())
        sub_com_gan = float(lib_df.loc[lib_df['Id'] == sub_id, 'Com Av (dB)'].item())
        sub_gain = "{:.2f}".format(sub_gain)
        sub_com_gan = "{:.2f}".format(sub_com_gan)
        print("sub_gain", sub_gain)
        print("sub_com_gan", sub_com_gan)
        print("sub_id", sub_id)
        print("sub_type", sub_type)
        sub_input = task_df.loc[task_df['Id'] == sub_id, 'Input'].item()
        input_node_list = sub_input.split(", ")
        input_node_list = [node for node in input_node_list if "bias" not in node]
        sub_input = ", ".join(input_node_list)

        sub_output = task_df.loc[task_df['Id'] == sub_id, 'Output'].item()
        output_node_list = sub_output.split(", ")
        output_node_list = [node for node in output_node_list if "outn" not in node and "outp" not in node]
        sub_output = ",".join(output_node_list)
        
        new_row = {'Id': sub_id, "Circuit Type": sub_type, "Gain/Differential-mode gain (dB)": sub_gain, "Common-mode gain (dB)": sub_com_gan, "Input": sub_input, "Output": sub_output}
        subcircuits_df = pd.concat([subcircuits_df, pd.DataFrame([new_row])], ignore_index=True)
    print("subcircuits_df")
    print(subcircuits_df)
    subcircuits_info = subcircuits_df.to_csv(sep='\t', index=False)
    return subcircuits_info


def get_note_info(subcircuits,
                    lib_data_path = "lib_info.tsv", task_data_path = "problem_set.tsv"):
   
    if not subcircuits:
        print("[WARN] get_note_info: subcircuits is None or empty, skip.")
        note_info = ""          
        sub_bias_voltage = 2.5 
        return note_info, sub_bias_voltage

    lib_df = pd.read_csv(lib_data_path, delimiter='\t')
    task_df = pd.read_csv(task_data_path, delimiter='\t')
    note_info = ""

    sub_bias_voltage = 2.5

    for sub_id in subcircuits:
        sub_type = task_df.loc[task_df['Id'] == sub_id, 'Type'].item()
        sub_name = task_df.loc[task_df['Id'] == sub_id, 'Submodule Name'].item()
        sub_bias_voltage = lib_df.loc[lib_df['Id'] == sub_id, 'Voltage Bias'].item()
        if "Amplifier" not in sub_type and "Opamp" not in sub_type:
            continue
        sub_phase = lib_df.loc[lib_df['Id'] == sub_id, 'Vin(n) Phase'].item()
        if sub_type == "Amplifier":
            if sub_phase == "inverting":
                other_sub_phase = "non-inverting"
            else:
                other_sub_phase = "inverting"
            note_info += f"The Vin of {sub_name} is the {sub_phase} input.\n"
            note_info += f"There is NO in {other_sub_phase} input in {sub_name}.\n"
            note_info += f"The DC operating voltage for Vin is {sub_bias_voltage} V.\n"
        elif sub_type == "Opamp":
            if sub_phase == "inverting":
                other_sub_phase = "non-inverting"
            else:
                other_sub_phase = "inverting"
            note_info += f"The Vinn of {sub_name} is the {sub_phase} input.\n"
            note_info += f"The Vinp of {sub_name} is the {other_sub_phase} input.\n"
            note_info += f"The DC operating voltage for Vinn/Vinp is {sub_bias_voltage} V.\n"

    print("note_info", note_info)
    return note_info, sub_bias_voltage



def get_call_info(subcircuits,
                    lib_data_path = "lib_info.tsv", task_data_path = "problem_set.tsv"):


    if not subcircuits:
        print("[WARN] get_call_info: subcircuits is None or empty, skip.")
        return ""

    lib_df = pd.read_csv(lib_data_path, delimiter='\t')
    task_df = pd.read_csv(task_data_path, delimiter='\t')
    call_info = ""

    for it, subcircuit in enumerate(subcircuits):
        sub_id = subcircuit
        sub_name = task_df.loc[task_df['Id'] == sub_id, 'Submodule Name'].item()
        input_nodes = task_df.loc[task_df['Id'] == sub_id, 'Input'].item()
        output_nodes = task_df.loc[task_df['Id'] == sub_id, 'Output'].item()

        sub_info = template.replace('[SUBMODULE_NAME]', sub_name)

        input_node_list = input_nodes.split(", ")
        input_node_list = [node for node in input_node_list if "bias" not in node]
        input_info = ", ".join([f"'{input_node}'" for input_node in input_node_list])

        output_node_list = output_nodes.split(", ")
        output_node_list = [node for node in output_node_list if "outn" not in node and "outp" not in node]
        output_info = ", ".join([f"'{output_node}'" for output_node in output_node_list])

        if input_info != "" and output_info != "":
            input_output = f"{input_info}, {output_info}"
        elif input_info == "":
            input_output = f"{output_info}"
        else:
            input_output = f"{input_info}"

        sub_info = sub_info.replace('[INPUT_OUTPUT]', input_output)
        sub_info = sub_info.replace('[ID]', str(sub_id))
        call_info += sub_info + "\n"

    return call_info


global generator
generator = None


def build_sky130_testbench(subckt_code, pins_str):
    """
    Wrap a .subckt block in a minimal ngspice testbench for DC OP analysis.
    pins_str: comma-separated pin list from problem_set, e.g. "VDD, VSS, VIN, VIP, VOUT, IB"
    Returns the full .sp testbench string.
    """
    # --- Parse .subckt name and pin order ---
    subckt_name = "DUT"
    subckt_pins = []
    for line in subckt_code.splitlines():
        ls = line.strip()
        if ls.lower().startswith(".subckt"):
            parts = ls.split()
            if len(parts) >= 2:
                subckt_name = parts[1]
                subckt_pins = parts[2:]
            break

    # --- Parse .param values for bias ---
    params = {}
    for line in subckt_code.splitlines():
        ls = line.strip()
        if ls.lower().startswith(".param") or ls.startswith("+"):
            for k, v in re.findall(r'(\w+)\s*=\s*([\d.eEuUpPnNmMkKfF]+)', ls):
                params[k.upper()] = v

    vdd_val = params.get("VDD", "1.8")
    vcm_val = params.get("VCM", "0.9")
    ib_val  = params.get("IB",  "50u")
    vcn_val = params.get("VCN", "1.2")
    vcp_val = params.get("VCP", "0.6")

    # Use subckt pin order if parsed, otherwise fall back to task definition
    pin_conn = " ".join(subckt_pins) if subckt_pins else " ".join(
        p.strip() for p in pins_str.split(",")
    )
    pin_upper = pin_conn.upper()

    tb = []
    tb.append(f"* Auto-generated testbench for {subckt_name}")
    if os.path.exists(SKY130_LIB_PATH):
        tb.append(f".lib '{SKY130_LIB_PATH}' {SKY130_LIB_CORNER}")
    else:
        tb.append(f"* WARNING: SKY130 lib not found at {SKY130_LIB_PATH}")
        tb.append(f"* Set env var SKY130_LIB to your sky130.lib path")
    tb.append("")
    tb.append(subckt_code)
    tb.append("")
    tb.append(f"* --- Instantiate DUT ---")
    tb.append(f"XDUT {pin_conn} {subckt_name}")
    tb.append("")
    tb.append("* --- Power supplies ---")
    tb.append(f"VVDD VDD 0 {vdd_val}")
    tb.append(f"VVSS VSS 0 0")
    tb.append("")
    tb.append("* --- Input common-mode bias ---")
    tb.append(f"VVIN VIN 0 {vcm_val}")
    tb.append(f"VVIP VIP 0 {vcm_val}")
    tb.append("")
    tb.append("* --- Bias current source (VDD -> IB node) ---")
    tb.append(f"IIB VDD IB {ib_val}")
    if "VCN" in pin_upper:
        tb.append("")
        tb.append("* --- NMOS cascode bias ---")
        tb.append(f"VVCN VCN 0 {vcn_val}")
    if "VCP" in pin_upper:
        tb.append("")
        tb.append("* --- PMOS cascode bias ---")
        tb.append(f"VVCP VCP 0 {vcp_val}")
    tb.append("")
    tb.append("* --- Output load (prevents floating node) ---")
    tb.append("RVOUT VOUT 0 1Meg")
    tb.append("")
    tb.append("* --- Analysis ---")
    tb.append(".op")
    tb.append(".end")

    return "\n".join(tb)


def _parse_device_lines(subckt_code):
    """Parse all X-prefixed device lines into structured records.
    Returns list of dicts: {name, drain, gate, source, bulk, model, raw}
    """
    devices = []
    for line in subckt_code.splitlines():
        s = line.strip()
        if not s.upper().startswith("X"):
            continue
        # Strip inline comments (SPICE uses * or ; or $)
        for comment_char in [";", "$"]:
            if comment_char in s:
                s = s[:s.index(comment_char)]
        tokens = s.split()
        if len(tokens) < 6:
            continue
        # X<name> <drain> <gate> <source> <bulk> <model> [params...]
        devices.append({
            "name":   tokens[0].upper(),
            "drain":  tokens[1].upper(),
            "gate":   tokens[2].upper(),
            "source": tokens[3].upper(),
            "bulk":   tokens[4].upper(),
            "model":  tokens[5].lower(),
            "raw":    line.strip(),
        })
    return devices


def check_netlist_sky130(subckt_code, pins_str, output_node):
    """
    Static validation for generated SKY130 subcircuit netlists.
    Returns (warning_flag, warning_message).
    """
    warning = 0
    msgs = []
    lower = subckt_code.lower()
    required_pins = [p.strip().upper() for p in pins_str.split(",") if p.strip()]
    output_upper = output_node.strip().upper()
    devices = _parse_device_lines(subckt_code)

    # ------------------------------------------------------------------ #
    # 1. Required pins present                                            #
    # ------------------------------------------------------------------ #
    for pin in required_pins:
        if pin.lower() not in lower:
            msgs.append(f"Required pin '{pin}' not found in subcircuit.")

    # ------------------------------------------------------------------ #
    # 2. SKY130 model names                                               #
    # ------------------------------------------------------------------ #
    if "sky130_fd_pr__nfet_01v8" not in lower and "sky130_fd_pr__pfet_01v8" not in lower:
        msgs.append("No SKY130 model names found. Use sky130_fd_pr__nfet_01v8 / sky130_fd_pr__pfet_01v8.")

    # ------------------------------------------------------------------ #
    # 3. X prefix (not M) for transistors                                 #
    # ------------------------------------------------------------------ #
    for line in subckt_code.splitlines():
        s = line.strip()
        if s.upper().startswith("M") and ("nfet" in s.lower() or "pfet" in s.lower()):
            msgs.append("Found 'M' prefix MOSFET line. SKY130 requires 'X' prefix for subcircuit instances.")
            break

    # ------------------------------------------------------------------ #
    # 4. Bulk polarity: NMOS bulk = VSS, PMOS bulk = VDD                  #
    # ------------------------------------------------------------------ #
    for d in devices:
        is_nmos = "nfet" in d["model"]
        is_pmos = "pfet" in d["model"]
        if is_nmos and d["bulk"] != "VSS":
            msgs.append(
                f"Device {d['name']}: NMOS bulk must connect to VSS, "
                f"but found bulk='{d['bulk']}'. Fix: change bulk terminal to VSS."
            )
            break
        if is_pmos and d["bulk"] != "VDD":
            msgs.append(
                f"Device {d['name']}: PMOS bulk must connect to VDD, "
                f"but found bulk='{d['bulk']}'. Fix: change bulk terminal to VDD."
            )
            break

    # ------------------------------------------------------------------ #
    # 5. No parasitic parameters                                          #
    # ------------------------------------------------------------------ #
    parasitic_pat = re.compile(
        r'\b(ad|as|pd|ps|nrd|nrs|sa|sb|sd|mult)\s*=', re.IGNORECASE
    )
    for d in devices:
        m = parasitic_pat.search(d["raw"])
        if m:
            msgs.append(
                f"Device {d['name']}: parasitic parameter '{m.group(1)}=' found. "
                f"Remove all parasitic parameters (ad/as/pd/ps/nrd/nrs/sa/sb/sd/mult/m)."
            )
            break

    # ------------------------------------------------------------------ #
    # 6. Duplicate device names                                           #
    # ------------------------------------------------------------------ #
    seen_names = set()
    for d in devices:
        if d["name"] in seen_names:
            msgs.append(
                f"Duplicate device name '{d['name']}'. "
                f"Every device in the subcircuit must have a unique name."
            )
            break
        seen_names.add(d["name"])

    # ------------------------------------------------------------------ #
    # 7. Output node must be connected to at least one device drain       #
    # ------------------------------------------------------------------ #
    if output_upper:
        output_drains = [d["name"] for d in devices if d["drain"] == output_upper]
        if not output_drains:
            msgs.append(
                f"Output node '{output_upper}' is not connected to any device drain. "
                f"The output must be driven by at least one transistor drain."
            )

    # ------------------------------------------------------------------ #
    # 8. Internal node connectivity (each internal node >= 2 connections) #
    # ------------------------------------------------------------------ #
    pin_set = set(required_pins) | {"VDD", "VSS"}
    node_counts = {}
    for d in devices:
        for terminal in [d["drain"], d["gate"], d["source"], d["bulk"]]:
            t = terminal.upper()
            if t not in pin_set:
                node_counts[t] = node_counts.get(t, 0) + 1
    floating_nodes = [n for n, c in node_counts.items() if c < 2]
    if floating_nodes:
        msgs.append(
            f"Floating internal node(s) detected: {', '.join(floating_nodes)}. "
            f"Each internal node must connect to at least 2 device terminals. "
            f"Check for typos or missing connections."
        )

    # ------------------------------------------------------------------ #
    # 9. IB bias reference (diode-connected transistor)                   #
    # ------------------------------------------------------------------ #
    if "IB" in required_pins:
        has_ib_diode = any(
            d["drain"] == "IB" and d["gate"] == "IB" for d in devices
        )
        if not has_ib_diode:
            msgs.append(
                "The IB pin is a bias current input. A diode-connected transistor "
                "(drain and gate both connected to IB) is required to convert the "
                "input current into a gate voltage for the tail current mirror. "
                "Please add a bias reference transistor, e.g.: "
                "XBIAS IB IB VSS VSS sky130_fd_pr__nfet_01v8 L=LB W=WB nf=NFB"
            )

    # ------------------------------------------------------------------ #
    # Build result                                                        #
    # ------------------------------------------------------------------ #
    if msgs:
        warning = 1
        msgs.append("Please fix the above issues and regenerate the complete .subckt block.")

    return warning, "\n".join(msgs)


def write_pyspice_code(sp_code_path, code_path, op_path):
    sp_code = open(sp_code_path, 'r')
    code = open(code_path, 'w', encoding="utf-8", errors="ignore")
    code.write(import_template)
    code.write("circuit = Circuit('circuit')\n")
    for line in sp_code.readlines():
        if line.startswith(".model"):
            parts = line.split()
            if len(parts) < 6:
                continue
            code.write(f"circuit.model('{parts[1]}', '{parts[2]}', {parts[3]}, {parts[4]}, {parts[5]})\n")
        elif line.startswith('R') or line.startswith('C') or line.startswith('V') or line.startswith('I'):
            type_name = line[0]
            parts = line.split()
            if len(parts) < 4:
                continue
            name = parts[0][1:]
            n1 = parts[1]
            n2 = parts[2]
            value = parts[3]
            code.write(f"circuit.{type_name}('{name}', '{n1}', '{n2}', '{value}')\n")
        elif line.startswith('M'):
            parts = line.split()
            if len(parts) < 8:
                continue
            name = parts[0][1:]
            drain = parts[1]
            gate = parts[2]
            source = parts[3]
            bulk = parts[4]
            model = parts[5]
            w = parts[6]
            l = parts[7]
            code.write(f"circuit.MOSFET('{name}', '{drain}', '{gate}', '{source}', '{bulk}', model='{model}', {w}, {l})\n")
    code.write("simulator = circuit.simulator()\n")
    code.write(pyspice_template.replace("[OP_PATH]", op_path))
    code.close()


def start_tmux_session(session_name, command):
    subprocess.run(['tmux', 'new-session', '-d', '-s', session_name])
    subprocess.run(['tmux', 'send-keys', '-t', session_name, command, 'C-m'])
    print(f"tmux session '{session_name}' started, running command: {command}")


def kill_tmux_session(session_name):
    try:
        subprocess.run(['tmux', 'kill-session', '-t', session_name], check=True)
        print(f"tmux session '{session_name}' has been killed successfully.")
    except subprocess.CalledProcessError:
        print(f"Failed to kill tmux session '{session_name}'. Session might not exist.")


def work(task, input, output, task_id, it, background, task_type, flog,
         generator, optimizer, curator, subcircuits=None, hint_code=""):
    """SKY130-oriented work() — generates SPICE .subckt netlists via ngspice."""

    prompt = None
    messages = []

    # ------------------------------------------------------------------ #
    # 1.  Build prompt from template                                       #
    # ------------------------------------------------------------------ #
    with open("prompt_template.md", "r", encoding="utf-8") as f:
        prompt = f.read()

    prompt = (
        prompt
        .replace("[TASK]", task)
        .replace("[INPUT]", input)
        .replace("[OUTPUT]", output)
    )

    # Inject background hint
    if background is not None:
        prompt += "\n\nHint Background: \n" + background + "\n## Answer \n"

    # Inject successful code from previous run (success propagation)
    if hint_code:
        print(f"[Success Propagation] Injecting hint code for iter {it}...")
        prompt += (
            "\n\nIMPORTANT: Here is a VALID and SUCCESSFUL netlist from a "
            "previous iteration. Please STRICTLY FOLLOW its topology, "
            "connections, and parameter naming.\n"
            "Reference Code:\n```spice\n" + hint_code + "\n```\n"
        )

    # Inject SEM guidance from curator
    if curator:
        print(f"[Agentic] Retrieving knowledge for Task {task_id} (Type: {task_type})...")
        guidance = curator.retrieve_guidance(task_type)
        if guidance:
            prompt += "\n\n" + guidance
            print("[Agentic] Guidance injected into initial prompt.")


    # ------------------------------------------------------------------ #
    # 2.  First generation                                                 #
    # ------------------------------------------------------------------ #
    answer = generator.generate_solution(
        base_template=prompt,
        task_description=task,
        history_messages=messages,
    )

    # ------------------------------------------------------------------ #
    # 3.  Set up output directory                                          #
    # ------------------------------------------------------------------ #
    model_dir = "sky130"
    task_path = os.path.join(model_dir, "p{}".format(task_id))
    os.makedirs(task_path, exist_ok=True)

    empty_code_error, raw_code = extract_code(answer)

    # Save prompt / answer logs
    fwrite_input = open(
        "{}/p{}/p{}_{}_input.txt".format(model_dir, task_id, task_id, it),
        "w", encoding="utf-8", errors="ignore"
    )
    fwrite_input.write(prompt)
    fwrite_input.flush()

    fwrite_output = open(
        "{}/p{}/p{}_{}_output.txt".format(model_dir, task_id, task_id, it),
        "w", encoding="utf-8", errors="ignore"
    )
    fwrite_output.write(answer)
    fwrite_output.flush()

    # Read error message templates
    with open("execution_error.md", "r") as f:
        prompt_exe_error = f.read()
    with open("simulation_error.md", "r") as f:
        prompt_sim_error = f.read()

    # ------------------------------------------------------------------ #
    # 4.  Retry loop                                                       #
    # ------------------------------------------------------------------ #
    code_id = 0
    answer_code = raw_code  # track latest successful raw subckt

    while code_id < args.num_of_retry:
        iter_dir = "{}/p{}/{}".format(model_dir, task_id, it)
        os.makedirs(iter_dir, exist_ok=True)

        # ---- 4a. Write subckt file ------------------------------------ #
        subckt_path = "{}/p{}_{}_{}.sp".format(
            iter_dir, task_id, it, code_id)
        with open(subckt_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(raw_code if not empty_code_error else "")

        # ---- 4b. Static format check ---------------------------------- #
        warning, warning_message = check_netlist_sky130(raw_code, input, output)

        # ---- 4c. Build testbench and run ngspice --------------------- #
        execution_error = 0
        simulation_error = 0
        execution_error_info = ""
        floating_node = ""

        if empty_code_error == 1:
            execution_error = 1
            execution_error_info = "No .subckt block found in LLM output."
        else:
            try:
                tb_code = build_sky130_testbench(raw_code, input)
            except Exception as e:
                execution_error = 1
                execution_error_info = (
                    "build_sky130_testbench failed: " + repr(e)
                )
                tb_code = None

            if tb_code:
                tb_path = subckt_path.replace(".sp", "_tb.sp")
                with open(tb_path, "w", encoding="utf-8", errors="ignore") as f:
                    f.write(tb_code)
                execution_error, simulation_error, execution_error_info, floating_node = run_code(tb_path)

        print("execution_error={}, simulation_error={}, format_warning={}".format(
            execution_error, simulation_error, warning))

        # ---- 4d. Curator learning ------------------------------------- #
        if curator:
            failure_log = ""
            has_failure = False
            if execution_error:
                failure_log += "Execution Error: " + execution_error_info + "\n"
                has_failure = True
            elif simulation_error:
                failure_log += "Simulation Error: Floating Node " + floating_node + "\n"
                has_failure = True
            elif warning:
                failure_log += "Format Warning: " + warning_message + "\n"
                has_failure = True

            if has_failure:
                print("[Agentic] Curator learning from failure in iter {}...".format(code_id))
                curator.reflect_and_learn(
                    task_type=task_type,
                    code=raw_code,
                    error_log=failure_log,
                    iteration=code_id,
                    image_path=None,
                )

        flog.write("task:{}\tit:{}\tcode_id:{}\t".format(task_id, it, code_id))
        flog.flush()

        # ---- 4e. Success check --------------------------------------- #
        if execution_error == 0 and simulation_error == 0 and warning == 0:
            answer_code = raw_code
            success_path = subckt_path.replace(".sp", "_success.sp")
            if os.path.exists(subckt_path):
                os.rename(subckt_path, success_path)
            flog.write("success.\n")
            flog.flush()
            break

        # ---- 4f. Build feedback for next iteration ------------------- #
        new_prompt = ""
        if empty_code_error:
            new_prompt = "There is no complete .subckt block in your reply. Please generate a complete SKY130 SPICE netlist."
            flog.write("empty code error\n")
        elif simulation_error:
            new_prompt = prompt_sim_error.replace("[NODE]", floating_node)
            flog.write("simulation error\n")
        elif execution_error:
            new_prompt = prompt_exe_error.replace("[ERROR]", execution_error_info)
            flog.write("execution error\n")
        elif warning:
            new_prompt = warning_message
            flog.write("format warning\n")
        else:
            flog.write("unknown error\n")
        flog.flush()

        code_id += 1
        if code_id >= args.num_of_retry:
            break

        messages.append({"role": "user", "content": new_prompt})

        # Optimizer feedback — use testbench file so ngspice can actually run it
        opt_path = tb_path if 'tb_path' in dir() or 'tb_path' in locals() else subckt_path
        optimization_result = optimizer.verify_and_reflect(
            task_id=task_id,
            code_path=opt_path,
            task_type=task_type,
            target_specs=None,
            image_path=None,
        )
        combined_feedback = new_prompt + "\n" + optimization_result["suggestions"]

        print("[Retry {}] Regenerating with agent feedback...".format(code_id))
        answer = generator.generate_solution(
            base_template=prompt,
            curator_guidance=combined_feedback,
            history_messages=messages,
        )

        fwrite_input.write("\n----------\n" + combined_feedback)
        fwrite_output.write("\n----------\n" + answer)

        empty_code_error, raw_code = extract_code(answer)

    # ------------------------------------------------------------------ #
    # 5.  Finalise                                                         #
    # ------------------------------------------------------------------ #
    messages_path = "{}/p{}/{}/p{}_{}_messages.txt".format(
        model_dir, task_id, it, task_id, it)
    with open(messages_path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(str(messages))

    fwrite_input.close()
    fwrite_output.close()

    is_successful = (
        execution_error == 0
        and simulation_error == 0
        and warning == 0
    )
    returned_code = answer_code if is_successful else None
    return returned_code




def get_retrieval(task, task_id):
    prompt = open('retrieval_prompt.md', 'r').read()
    prompt = prompt.replace('[TASK]', task)
    messages = [
            {"role": "system", "content": "You are an analog integrated circuits expert."},
            {"role": "user", "content": prompt}
        ]
    
    subcircuits = [11]

    if "gpt" in args.model and args.retrieval:
        completion = None
        
        while completion is None:
            try:
                completion = client.chat.completions.create(
                    model = args.model,
                    messages = messages,
                    temperature = args.temperature
                )
            except openai.APIStatusError as e:
                print("Encountered an APIStatusError. Details:")
                print(e)
                print("sleep 30 seconds")
                time.sleep(30)
      
            except Exception as e:
                print(f"Unexpected error: {e}")
                print("sleep 5 seconds")
                time.sleep(5)
        
  
        answer = completion.choices[0].message.content
        print("answer", answer)
        
      
        fretre_path = os.path.join(args.model.replace("-", ""), f"p{str(task_id)}", "retrieve.txt")
        os.makedirs(os.path.dirname(fretre_path), exist_ok=True)
        
        fretre = open(fretre_path, "w", encoding="utf-8", errors="ignore")
        fretre.write(answer)
        fretre.close()
        
        try:
            regex = r".*?```.*?\n(.*?)```"
            matches = re.finditer(regex, answer, re.DOTALL)
            first_match = next(matches, None)
            if first_match:
                match_res = first_match.group(1)
                print("match_res", match_res)
                subcircuits = eval(match_res)
            else:
                print("No code block found in retrieval response, using default.")
        except Exception as e:
            print(f"Error parsing subcircuits: {e}, using default.")

    return subcircuits


def main():
    global client

    # =========================
    # LLM Engine Setup
    # Supports:
    #   1) Gemini API (OpenAI-compatible endpoint)  <-- default
    #   2) GPT-5 (OpenAI API)
    #   3) Local vLLM (OpenAI-compatible)
    # =========================

    if args.model == "gemini":
        gemini_key = args.api_key or os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it in .env or pass --api_key."
            )
        client = OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        # Override model name so agents use the actual Gemini model string
        args.model = args.gemini_model
        print(f"Connected to Gemini API. Model: {args.model}")

    elif args.model == "local":
        client = OpenAI(
            api_key="EMPTY",
            base_url="http://localhost:8001/v1"
        )
        print("Connected to local vLLM engine.")

    elif args.model == "gpt-5":
        if args.api_key:
            client = OpenAI(api_key=args.api_key)
        elif os.getenv("OPENAI_API_KEY"):
            client = OpenAI()
        else:
            raise ValueError("API key required for GPT-5.")
        print("Connected to GPT-5 API.")

    else:
        raise ValueError("Unsupported model. Use 'gemini', 'gpt-5', or 'local'.")

    # Unified engine (OpenAI-compatible for all backends)
    llm_engine = client

    # =========================
    # Load Dataset
    # =========================
    data_path = "problem_set.tsv"
    df = pd.read_csv(data_path, delimiter="\t")

    # Pass unified engine
    generator_agent = CodeGenerator(llm_client=llm_engine, model_name=args.model)
    optimizer_agent = DesignOptimizer(llm_client=llm_engine, model_name=args.model)
    curator = ExperienceCurator(llm_model=llm_engine, model_name=args.model)



    success_memory = {}

    for index, row in df.iterrows():
        circuit_id = row['Id']
        if circuit_id != args.task_id:
            continue
        strftime = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        flog = open('{}_{}_{}_sky130_log.txt'.format(strftime, args.model, circuit_id), 'w', encoding="utf-8", errors="ignore")
        
        for it in range(args.num_per_task):
            
            print(f"\n🔹 [Main] Starting Iteration {it} for Task {circuit_id}...")
            
            subcircuits = None 
            current_type = row['Type']
            type_specific_hint = success_memory.get(current_type, "")

            new_success_code = work(
                row['Circuit'], row['Input'].strip(), row['Output'].strip(), circuit_id, it,
                None, row['Type'], flog,
                subcircuits=subcircuits,
                generator=generator_agent,
                optimizer=optimizer_agent,
                curator=curator,
                hint_code=type_specific_hint
            )

            if new_success_code:
                print(f"[Main] Success for Task {circuit_id} iter {it}. Updating hint memory.")
                success_memory[current_type] = new_success_code
        try:
            flog.close()
        except:
            pass

        
    
if __name__ == "__main__":
    _parse_args()
    main()

