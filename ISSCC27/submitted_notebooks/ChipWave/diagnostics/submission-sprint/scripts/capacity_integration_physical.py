"""Prepare the frozen CPU integration with the existing public physical backend."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

import yaml

from chip_nebula.dashboard.workbench import WorkbenchProject
from study_protocol import digest, write_json
from study_portability import case_root

ROOT = Path(__file__).resolve().parents[1]
CASE = case_root(ROOT)
PERIOD_PS = 10526
CONFIGURATION = dict(CORE_UTILIZATION=40, PLACE_DENSITY=.55, ABC_AREA=0,
                     CAP_MARGIN=20, SLEW_MARGIN=20)


def verified_integration(task_name):
    if task_name not in ("A1", "A2", "B1", "B2"):
        raise ValueError("Unknown integration")
    source = ROOT/"integration"/task_name
    manifest = json.loads((source/"freeze-draft.json").read_text())
    if not json.loads((source/"qualification/qualification.json").read_text())["passed"]:
        raise ValueError("CPU integration prerequisite failed")
    for name, expected in manifest["source_sha256"].items():
        path = source/name
        if path.is_symlink() or not path.resolve().is_relative_to(source) or digest(path) != expected:
            raise ValueError("Frozen integration input changed: "+name)
    return source, manifest


def prepare(project, task_name, *, candidate=None):
    from freeze_tool_workflow import freeze

    source, frozen = verified_integration(task_name)
    if project.exists():
        raise ValueError("Existing physical project retained")
    project.mkdir()
    for name in ("rtl", "verification", "workloads"):
        shutil.copytree(source/name, project/name)
    settings = dict(CONFIGURATION)
    admitted = None
    if candidate is not None:
        candidate = Path(candidate)
        admitted = json.loads((candidate/"admission.json").read_text())
        if (not admitted["passed"] or admitted.get("configuration_checked") is not True or admitted["task"] != task_name
                or digest(candidate/"design.sv") != admitted["canonical_rtl_sha256"]):
            raise ValueError("Candidate admission/source mismatch")
        from capacity_candidate import ALLOWED_CONFIG, DEFAULT_CONFIG
        knobs = admitted["configuration"]
        if set(knobs) != set(ALLOWED_CONFIG) or any(
                type(knobs[k]) is not type(DEFAULT_CONFIG[k]) or knobs[k] not in values
                for k, values in ALLOWED_CONFIG.items()):
            raise ValueError("Unapproved physical parameters")
        settings.update(CORE_UTILIZATION=knobs["utilization"], PLACE_DENSITY=knobs["density"],
                        ABC_AREA=int(knobs["area_synthesis"]), CAP_MARGIN=knobs["repair_margin"],
                        SLEW_MARGIN=knobs["repair_margin"])
        shutil.rmtree(project/"rtl/candidate")
        (project/"rtl/candidate").mkdir()
        shutil.copy2(candidate/"design.sv", project/"rtl/candidate/design.sv")
        shutil.copy2(candidate/"admission.json", project/"candidate-admission.json")
    sources = sorted(project.glob("rtl/**/*.sv"))
    initial = dict(top_module="nebula_cpu_npu_top",
                   design_files=[str(p.relative_to(project)) for p in sources],
                   validation_mode="fileset", simulation_top="tb_cpu_elf",
                   testbench_files=["verification/tb_cpu_npu.sv"])
    (project/"workbench.yaml").write_text(yaml.safe_dump(initial, sort_keys=False))
    sdk = WorkbenchProject(project)
    sdk.save_config(initial)
    receipt = sdk.configure_physical_project(
        top_module="nebula_cpu_npu_top", clock_port="clk", clock_period_ns=PERIOD_PS/1000,
        platform="sky130hd", simulation_command="python3 scripts/check_integration.py")
    write_json(project/"configuration-receipt.json", receipt)
    if not receipt["environment"]["ready"]:
        raise RuntimeError("Physical environment not ready")
    physical = project/"physical/chip-nebula"
    config = physical/"config.mk"
    lines = [line for line in config.read_text().splitlines()
             if not any(line.startswith("export "+key+" =") for key in settings)]
    config.write_text("\n".join([*lines, *["export "+k+" = "+str(v)
                      for k, v in settings.items()]])+"\n")
    # Frozen integration ports; explicit reset also avoids the SDK's compact-port parser gap.
    inputs = ["rst_n", "imem_rdata[*]", "dmem_req_ready", "dmem_rsp_valid",
              "dmem_rsp_rdata[*]", "dmem_rsp_err"]
    if task_name.startswith("B"):
        inputs.append("dmem_rsp_tag[*]")
    (physical/"constraints.sdc").write_text(
        "current_design nebula_cpu_npu_top\n"
        f"create_clock -name capacity_clock -period {PERIOD_PS/1000:g} [get_ports {{clk}}]\n"
        "set_clock_uncertainty 0.1 [get_clocks capacity_clock]\n"
        "set_input_delay 0.5 -clock capacity_clock [get_ports {"
        +" ".join(inputs)+"}]\n"
        "set_output_delay 0.5 -clock capacity_clock [all_outputs]\n")
    cfg = asdict(sdk.config())
    cfg["physical"]["timeout"] = 14400
    sdk.save_config(cfg)
    (project/"workbench.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    (project/"scripts").mkdir()
    shutil.copy2(CASE/"scripts/run_physical.py", project/"scripts/run_physical.py")
    (project/"scripts/check_integration.py").write_text(CHECK_INTEGRATION)
    roles, recipes = project/".chip_nebula/roles", project/".chip_nebula/recipes"
    roles.mkdir(parents=True); recipes.mkdir(parents=True)
    shutil.copy2(CASE/"workflows/case-physical-tool.yaml", roles/"case-physical-tool.yaml")
    definition = yaml.safe_load((CASE/"workflows/cpu-npu-physical.yaml").read_text())
    node = definition["tasks"]["physical"]
    node.update(max_attempts=1,
                intent="One frozen CPU/subsystem integration at 95 MHz; preserve source and all gates.")
    node["execution"]["timeout_seconds"] = 14520
    node["permission"]["read"] += ["verification/**", "workloads/**", "configuration-receipt.json"]
    recipe = recipes/"benchmark-physical.yaml"
    recipe.write_text(yaml.safe_dump(definition, sort_keys=False))
    manifest = dict(task=task_name, top="nebula_cpu_npu_top", period_ps=PERIOD_PS,
        threads=2, configuration=settings, integration_sha256=frozen["source_sha256"],
        rtl_sha256={str(p.relative_to(project)): digest(p) for p in sources},
        sdc_sha256=digest(physical/"constraints.sdc"), config_sha256=digest(config),
        scope="Frozen CPU and neighbors; task subsystem reference; no AI experiment")
    if admitted is not None:
        manifest.update(candidate_admission=admitted,
                        scope="Frozen CPU/neighbors with admitted task module and permitted implementation knobs")
    write_json(project/"selected-delivery.json", dict(id="capacity-integration-"+task_name,
        exported_source_sha256=manifest["rtl_sha256"]))
    write_json(project/"benchmark-candidate.json", manifest)
    (project/".gitignore").write_text(".chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n")
    for args in (["init", "-q"], ["config", "user.name", "ChipNebula experiment"],
                 ["config", "user.email", "automation@chipnebula.invalid"], ["add", "."],
                 ["add", "-f", ".chip_nebula/roles", ".chip_nebula/recipes"],
                 ["commit", "-qm", "Freeze CPU integration and physical constraints"]):
        subprocess.run(["git", *args], cwd=project, check=True)
    freeze(project, recipe, "benchmark-physical", source_design_delivery="capacity-integration-"+task_name)
    return manifest


CHECK_INTEGRATION = '''from pathlib import Path
import subprocess
root=Path.cwd();obj=root/'build/integration-check';obj.mkdir(parents=True,exist_ok=True)
subprocess.run(['verilator','--binary','--timing','--assert','-Wno-fatal','-j','2',
 '--top-module','tb_cpu_elf','--Mdir',str(obj),*map(str,sorted(root.glob('rtl/**/*.sv'))),
 str(root/'verification/tb_cpu_npu.sv')],check=True,timeout=600)
for workload in ('short','mixed','long'):
 result=subprocess.run([str(obj/'Vtb_cpu_elf'),f"+IMAGE={root/'workloads'/workload/'memory.hex'}",
  '+SEED=20261021','+MAX_CYCLES=200000'],text=True,capture_output=True,timeout=120)
 print(result.stdout,end='');print(result.stderr,end='')
 if result.returncode or 'CPU_ELF_PASS' not in result.stdout:raise SystemExit(1)
print('CAPACITY_INTEGRATION_PASS')
'''
