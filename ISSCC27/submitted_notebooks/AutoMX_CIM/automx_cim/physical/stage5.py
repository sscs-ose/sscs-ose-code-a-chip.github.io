"""Executable Stage-5 Magic/KLayout/Netgen/PEX flow for the analog core."""
from __future__ import annotations
from hashlib import sha256
import json, os, re, shutil, subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Sequence

CORE = "automx_ternary_cim_4x4_core"
TOOLS = ("magic", "klayout", "netgen", "ngspice")

def core_pins(rows=4, cols=4):
    pins=[p for c in range(cols) for p in (f"BLP{c}",f"BLN{c}")]
    pins += [p for r in range(rows) for p in (f"WLP{r}",f"WLN{r}")]
    pins += [p for r in range(rows) for c in range(cols) for p in (f"WPOS_{r}_{c}",f"WNEG_{r}_{c}")]
    return tuple(pins+["VGND","VSUBS"])

def parse_spice_subckt_pins(path, name=CORE):
    text=Path(path).read_text(encoding="utf-8"); logical=re.sub(r"\n\s*\+\s*"," ",text)
    m=re.search(rf"(?im)^\s*\.subckt\s+{re.escape(name)}\s+([^\n]+)",logical)
    if not m: raise ValueError(f"subcircuit {name!r} not found in {path}")
    return tuple(m.group(1).split())

def _canonicalize_pex_interface(raw_path, output_path, name=CORE):
    """Expose the extracted core with Stage-4 pin order without rewiring it."""
    raw_path=Path(raw_path); output_path=Path(output_path)
    raw_name=f"{name}_pex"; internal_name=f"{name}_pex_raw"
    actual=parse_spice_subckt_pins(raw_path,raw_name)
    expected=core_pins()
    if len(actual)!=len(expected) or set(actual)!=set(expected):
        missing=sorted(set(expected)-set(actual)); extra=sorted(set(actual)-set(expected))
        raise ValueError(f"PEX pin contract mismatch: expected {len(expected)}, got {len(actual)}, missing={missing}, extra={extra}")
    source=raw_path.read_text(encoding="utf-8")
    head=rf"(?im)^(\s*\.subckt\s+){re.escape(raw_name)}(?=\s)"
    source,replacements=re.subn(head,lambda m:m.group(1)+internal_name,source,count=1)
    if replacements!=1:
        raise ValueError(f"PEX top subcircuit {raw_name} not found in {raw_path}")
    tail=rf"(?im)^(\s*\.ends\s+){re.escape(raw_name)}(?=\s|$)"
    source=re.sub(tail,lambda m:m.group(1)+internal_name,source,count=1)
    wrapper=(f"\n* Stage-4 ordered interface to Magic's extracted pin order\n"
             f".subckt {raw_name} {' '.join(expected)}\n"
             f"XPEX_RAW {' '.join(actual)} {internal_name}\n"
             f".ends {raw_name}\n")
    # This file is included by an ngspice testbench; a standalone .end from
    # Magic would terminate the parent deck before the testbench stimuli.
    source=re.sub(r"(?im)^\s*\.end\s*$","",source)
    source=source.rstrip()+"\n"+wrapper
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(source,encoding="utf-8")
    return actual

def _spice_device_count(path, top, device):
    """Count a primitive through nested SPICE subcircuits, not text matches."""
    logical=[]
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line=raw.strip()
        if line.startswith("+") and logical:
            logical[-1] += " " + line[1:].strip()
        else:
            logical.append(line)
    blocks={}; current=None
    for line in logical:
        fields=line.split()
        if not fields or line.startswith("*"):
            continue
        head=fields[0].lower()
        if head==".subckt" and len(fields)>1:
            current=fields[1].lower(); blocks[current]=[]
        elif head==".ends":
            current=None
        elif current and head.startswith(("x","m")):
            positional=[part for part in fields[1:] if "=" not in part]
            if positional:
                blocks[current].append(positional[-1].lower())

    target=device.lower()
    def expand(name, parents):
        if name==target:
            return 1
        if name in parents:
            raise ValueError(f"cyclic SPICE hierarchy at {name}")
        if name not in blocks:
            return 0
        return sum(expand(child, parents | {name}) for child in blocks[name])

    if top.lower() not in blocks:
        raise ValueError(f"subcircuit {top!r} not found in {path}")
    return expand(top.lower(), set())

def _validate_stage4_deck_receipt(artifact, receipt):
    """Reject a PASS receipt from different Stage-4 transient stimuli."""
    jobs=artifact.get("jobs") or [{"testbench":artifact["testbench"]}]
    expected={}
    for job in jobs:
        deck=Path(job["testbench"]).resolve()
        if not deck.is_file():
            raise FileNotFoundError(f"Stage-4 testbench is missing: {deck}")
        # UIC leaves the extracted parasitic capacitors at zero while only
        # the explicit bitline capacitors have IC=VDD.  That produces a
        # spurious 20-30mV differential offset before any wordline fires.
        if re.search(r"(?im)^\s*\.tran\b[^\n]*\bUIC\b",deck.read_text(encoding="utf-8")):
            raise RuntimeError(f"Stage-4 testbench still uses UIC: {deck}; copy the updated sky130.py, restart the notebook kernel, and rerun Stage 4")
        expected[str(deck)]=_hash(deck)
    recorded=receipt.get("inputs",{}).get("testbenches",[])
    actual={str(Path(item["path"]).resolve()):item["sha256"]
            for item in recorded if isinstance(item,dict) and "path" in item and "sha256" in item}
    if len(actual)!=len(recorded) or actual!=expected:
        raise RuntimeError("Stage-4 testbench hash mismatch; rerun Stage 4 before Stage 5")

def validate_core_contract(spice, blackbox, rows=4, cols=4):
    expected=core_pins(rows,cols); actual=parse_spice_subckt_pins(spice)
    if actual != expected: raise ValueError(f"SPICE pin order mismatch\nexpected={expected}\nactual={actual}")
    rtl=Path(blackbox).read_text(encoding="utf-8")
    missing=[x for x in expected if not re.search(rf"\b{re.escape(x)}\b",rtl)]
    forbidden=[x for x in ("clk_i","cfg_valid_i","act_x2_i","result_acc_o") if re.search(rf"\b{x}\b",rtl)]
    if missing or forbidden: raise ValueError(f"RTL core mismatch: missing={missing}, wrapper_only={forbidden}")
    return {"status":"PASS","macro":CORE,"pin_count":len(expected),"pins":list(expected)}

def discover_pdk(pdk_root=None,pdk="sky130A"):
    root=Path(pdk_root or os.environ.get("PDK_ROOT",Path.home()/".volare")).expanduser()
    direct=[root,root/pdk,root/"sky130"/pdk]
    version_patterns=(
        f"volare/sky130/versions/*/{pdk}",
        f"sky130/versions/*/{pdk}",
        f"versions/*/{pdk}",
    )
    candidates=list(direct)
    for pattern in version_patterns:
        candidates.extend(sorted(root.glob(pattern),reverse=True))
    checked=[]
    for c in dict.fromkeys(candidates):
        checked.append(str(c))
        if all((c/x).is_file() for x in ("libs.tech/magic/sky130A.tech","libs.tech/netgen/sky130A_setup.tcl","libs.tech/ngspice/sky130.lib.spice")):
            return c.resolve()
    raise FileNotFoundError(f"complete {pdk} installation not found; checked: {checked}")

def _find_tool(name):
    # A user-built Magic is normally newer than the Ubuntu package.  Prefer
    # explicit/local installations even when /usr/bin appears first on PATH.
    override=os.environ.get(f"AUTOMX_{name.upper()}_BIN")
    if override:
        path=Path(override).expanduser()
        if path.is_file() and os.access(path,os.X_OK):return str(path)
    candidates={
        "netgen": ("/usr/lib/netgen/bin/netgen", "/usr/local/lib/netgen/bin/netgen"),
        "magic": (str(Path.home()/".local/bin/magic"), "/usr/local/bin/magic", "/usr/bin/magic"),
        "klayout": ("/usr/bin/klayout", "/usr/local/bin/klayout"),
        "ngspice": ("/usr/bin/ngspice", "/usr/local/bin/ngspice"),
    }
    for value in candidates.get(name, ()):
        path=Path(value)
        if path.is_file() and os.access(path,os.X_OK):return str(path)
    return shutil.which(name)

def tool_inventory(): return {x:_find_tool(x) for x in TOOLS}

def _tool_version(name,path):
    try:
        args={"magic":["--version"],"klayout":["-b","-v"],
              "netgen":["-batch"],"ngspice":["--version"]}.get(name,["--version"])
        result=subprocess.run([path,*args],capture_output=True,text=True,timeout=20,check=False)
        return (result.stdout+result.stderr).strip()
    except Exception as error:
        return f"ERROR: {error}"

def _version_tuple(text):
    match=re.search(r"\b(\d+)\.(\d+)(?:\.(\d+))?\b",text)
    return tuple(int(x or 0) for x in match.groups()) if match else None
def _hash(path): return sha256(Path(path).read_bytes()).hexdigest()


def _write_core_lef_with_vgnd_landing(raw_lef, output_lef):
    """Expose only the via-capable M4 ground pad as the LEF power pin.

    Magic exports all connected M4 ground bars as one VGND pin. OpenROAD then
    selects the long 0.50um bar at the M5 crossing and cannot insert a legal
    via, even when a redundant full-pad RECT is added. The bars remain real
    GDS metal and become LEF routing obstructions; the pin exposes only the
    existing 1.60 x 2.10um landing pad.
    """
    raw_lef, output_lef = Path(raw_lef), Path(output_lef)
    text = raw_lef.read_text(encoding="utf-8")
    pin = re.search(r"(?ms)^  PIN VGND\s*$(.*?)^  END VGND\s*$", text)
    if pin is None or "LAYER met5 ;" in pin.group(1):
        raise ValueError("core LEF lacks met4-only VGND pin")
    layer = re.search(r"(?ms)^([ \t]*)LAYER met4 ;(?P<rects>.*?)(?=^[ \t]*LAYER |^[ \t]*END(?:\s|$))",
                      pin.group(1))
    if layer is None:
        raise ValueError("core LEF VGND lacks met4 geometry")
    rects = {tuple(map(float, values)) for values in re.findall(
        r"RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;",
        layer.group("rects"))}
    landing = (3.0, 10.4, 4.6, 12.5)
    pad_fragments = {
        (3.0, 10.4, 4.6, 10.95),
        (2.9, 10.95, 30.25, 11.45),
        (3.0, 11.45, 4.6, 12.5),
    }
    other_bars = {
        (2.9, 31.95, 30.25, 32.45),
        (2.9, 21.45, 30.25, 21.95),
        (2.9, 0.45, 30.25, 0.95),
    }
    if rects != pad_fragments | other_bars:
        raise ValueError("Magic LEF ground geometry changed; inspect GDS before abstracting")
    # Split the central bar at the pad boundary so OBS never overlaps VGND.
    obs_rects = [
        (2.9, 31.95, 30.25, 32.45),
        (2.9, 21.45, 30.25, 21.95),
        (2.9, 10.95, 3.0, 11.45),
        (4.6, 10.95, 30.25, 11.45),
        (2.9, 0.45, 30.25, 0.95),
    ]
    layer_start = pin.start(1) + layer.start()
    layer_end = pin.start(1) + layer.end()
    indent = layer.group(1)
    text = (text[:layer_start] + indent + "LAYER met4 ;\n" + indent +
            "  RECT 3.000 10.400 4.600 12.500 ;\n" + text[layer_end:])
    obs = re.search(r"(?ms)^  OBS[ \t]*\n(.*?)^  END[ \t]*$", text)
    if obs is None or "LAYER met4 ;" in obs.group(1):
        raise ValueError("unexpected Magic LEF OBS geometry")
    obs_lines = "      LAYER met4 ;\n" + "".join(
        "        RECT " + " ".join(f"{v:.3f}" for v in rect) + " ;\n"
        for rect in obs_rects)
    text = text[:obs.end(1)] + obs_lines + text[obs.end(1):]
    output_lef.parent.mkdir(parents=True, exist_ok=True)
    output_lef.write_text(text, encoding="utf-8")
    return {"mode": "single_vgnd_met4_landing_v2", "rect_um": list(landing),
            "obstruction_rects_um": [list(rect) for rect in obs_rects],
            "magic_raw_lef_sha256": _hash(raw_lef)}
def _now(): return datetime.now(timezone.utc).isoformat()
def _write(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); return payload

def _read_pass_receipt(path, expected_format=None):
    """Load a receipt and reject absent, stale, or non-PASS evidence."""
    path=Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"required PASS receipt is missing: {path}")
    payload=json.loads(path.read_text(encoding="utf-8"))
    if str(payload.get("status","")).upper() != "PASS":
        raise RuntimeError(f"required receipt is not PASS: {path}")
    if expected_format and payload.get("format") != expected_format:
        raise RuntimeError(f"unsupported receipt format in {path}: {payload.get('format')}")
    return payload

def _relative_delta(post, pre):
    if pre == 0:
        return None
    return (post-pre)/abs(pre)

def _run(command,cwd,timeout=900,input_text=None,env=None):
    return subprocess.run(command,cwd=cwd,input=input_text,text=True,capture_output=True,
                          timeout=timeout,check=False,env=env)

def _magic(exe,tech,cwd,tcl,timeout=900):
    tech=Path(tech).resolve()
    # sky130A.magicrc references $PDK_ROOT/$PDK/libs.tech/magic/sky130A.tech.
    # The caller's --pdk-root points at sky130A itself. Passing that directory
    # through as PDK_ROOT produces .../sky130A/sky130A/... and Magic exits
    # before executing any layout Tcl. Normalize the child-process environment
    # for every Magic phase, independent of the notebook kernel's variables.
    pdk_dir=tech.parents[2]
    if pdk_dir.name!="sky130A":
        raise ValueError(f"Magic tech is not inside a sky130A PDK: {tech}")
    magic_env=os.environ.copy()
    magic_env["PDK_ROOT"]=str(pdk_dir.parent)
    magic_env["PDK"]=pdk_dir.name
    rcfile=tech.with_name("sky130A.magicrc")
    command=[exe,"-dnull","-noconsole","-rcfile",str(rcfile)] if rcfile.is_file() else [exe,"-dnull","-noconsole","-T",str(tech)]
    return _run(command,cwd,timeout,tcl,magic_env)

def _klayout_deck(pdk):
    roots=[pdk/"libs.tech/klayout/drc",pdk/"libs.tech/klayout/tech"]
    patterns=("*mr*.drc","*sky130*.drc","*.lydrc")
    for root in roots:
        for pat in patterns:
            found=sorted(root.glob(pat)) if root.is_dir() else []
            if found:return found[0]
    raise FileNotFoundError("KLayout SKY130 DRC deck not found under libs.tech/klayout")

def write_preflight_receipt(root,contract_path,pdk_root=None):
    root=Path(root).resolve(); cp=Path(contract_path).resolve(); data=json.loads(cp.read_text())
    core=data["physical_core"]; base=cp.parent; views={k:(base/v).resolve() for k,v in core["views"].items()}
    tools=tool_inventory(); missing=[k for k,v in tools.items() if not v]; pdk=discover_pdk(pdk_root,data["pdk"])
    versions={name:_tool_version(name,path) if path else None for name,path in tools.items()}
    magic_version=_version_tuple(versions.get("magic") or "")
    incompatible=[]
    if magic_version is None or magic_version < (8,3,0):
        incompatible.append(f"magic >= 8.3 required for this SKY130 tech; found {versions.get('magic')}")
    pins=validate_core_contract(views["spice"],views["blackbox_rtl"])
    out={"format":"automx-cim-stage5-preflight-v1","status":"PASS" if not missing and not incompatible else "BLOCKED","timestamp_utc":_now(),"macro":core["macro"],"contract_sha256":_hash(cp),"pdk":str(pdk),"tools":tools,"tool_versions":versions,"missing_tools":missing,"incompatible_tools":incompatible,"pin_contract":pins}
    return _write(root/"results/receipts/physical/preflight.json",out)

def run_stage5(root,contract_path,pdk_root=None,timeout_s=900):
    root=Path(root).resolve(); cp=Path(contract_path).resolve(); contract=json.loads(cp.read_text())
    core=contract["physical_core"]; base=cp.parent; views={k:(base/v).resolve() for k,v in core["views"].items()}
    # Stage 5 is physically meaningful only for the exact Stage-4 schematic
    # that already passed ngspice validation.  Do this before invoking Magic.
    manifest_path=root/"generated/sky130/spice/stage4_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"run Stage 4 first; manifest is missing: {manifest_path}")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    macro_artifact=next((x for x in manifest.get("artifacts",[]) if x.get("stage")=="macro4x4"),None)
    if macro_artifact is None:
        raise RuntimeError("Stage-4 manifest has no macro4x4 artifact")
    pre_layout=_read_pass_receipt(
        macro_artifact["receipt"], "automx-cim-stage4-ngspice-receipt-v1")
    if Path(macro_artifact["netlist"]).resolve() != views["spice"]:
        raise RuntimeError("Stage-4 macro netlist does not match the contracted schematic view")
    if pre_layout.get("config_sha256") != manifest.get("config_sha256"):
        raise RuntimeError("Stage-4 macro receipt/config hash mismatch; rerun Stage 4")
    if pre_layout.get("inputs",{}).get("netlist_sha256") != _hash(views["spice"]):
        raise RuntimeError("Stage-4 macro receipt/netlist hash mismatch; rerun Stage 4")
    _validate_stage4_deck_receipt(macro_artifact,pre_layout)
    if pre_layout.get("model_library_sha256") != manifest.get("model_library_sha256"):
        raise RuntimeError("Stage-4 macro receipt/model-library hash mismatch; rerun Stage 4")
    pre=write_preflight_receipt(root,cp,pdk_root)
    if pre["status"]!="PASS": raise RuntimeError(f"preflight blocked: missing={pre['missing_tools']}, incompatible={pre.get('incompatible_tools',[])}")
    pdk=Path(pre["pdk"]); tools=pre["tools"]; tech=pdk/"libs.tech/magic/sky130A.tech"; setup=pdk/"libs.tech/netgen/sky130A_setup.tcl"
    build=root/"build/physical_stage5"; build.mkdir(parents=True,exist_ok=True); receipts=root/"results/receipts/physical"; logs=root/"results/sky130"
    # A failed rerun must not leave later PASS receipts looking current.
    for name in ("layout.json","magic_drc.json","klayout_drc.json","netgen_lvs.json",
                 "pex.json","post_layout.json","pre_post_comparison.json","stage5_summary.json"):
        stale=receipts/name
        if stale.is_file(): stale.unlink()
    recipe=root/"physical/sky130/layout/generate_automx_ternary_cim_4x4_core.tcl"
    if not recipe.is_file(): raise FileNotFoundError(recipe)
    gen=_magic(tools["magic"],tech,build,recipe.read_text(),timeout_s)
    generated_log=gen.stdout+gen.stderr
    (logs/"layout").mkdir(parents=True,exist_ok=True)
    (logs/"layout/magic_generate.log").write_text(generated_log)
    if gen.returncode or "AUTOMX_LAYOUT_DONE" not in generated_log:
        tail="\n".join(generated_log.splitlines()[-50:])
        raise RuntimeError(
            f"Magic layout generation failed (exit={gen.returncode}, "
            f"done_marker={'AUTOMX_LAYOUT_DONE' in generated_log}); "
            "see results/sky130/layout/magic_generate.log\n"
            f"Last 50 Magic log lines:\n{tail}")
    lef_abstraction=None
    for ext,key in (("gds","gds"),("lef","lef")):
        src=build/f"{CORE}.{ext}"
        if not src.is_file() or not src.stat().st_size: raise RuntimeError(f"Magic did not create {src}")
        views[key].parent.mkdir(parents=True,exist_ok=True)
        if key=="lef":
            lef_abstraction=_write_core_lef_with_vgnd_landing(src,views[key])
        else:
            shutil.copy2(src,views[key])
    _write(receipts/"layout.json",{"format":"automx-cim-stage5-layout-v1","status":"PASS","timestamp_utc":_now(),"generator":str(recipe),"generator_sha256":_hash(recipe),"gds_sha256":_hash(views["gds"]),"lef_sha256":_hash(views["lef"]),"lef_abstraction":lef_abstraction})
    drc_tcl=f'''crashbackups stop
load {CORE}
select top cell
drc on
drc check
drc catchup
puts "AUTOMX_DRC=[drc list count total]"
set rules [drc listall why]
foreach {{rule boxes}} $rules {{
    puts "AUTOMX_DRC_RULE: $rule COUNT=[llength $boxes]"
}}
quit -noprompt
'''
    drc=_magic(tools["magic"],tech,build,drc_tcl,timeout_s); text=drc.stdout+drc.stderr; (logs/"drc").mkdir(parents=True,exist_ok=True); (logs/"drc/magic.log").write_text(text)
    m=re.search(r"AUTOMX_DRC=(\d+)",text); count=int(m.group(1)) if m else -1; status="PASS" if drc.returncode==0 and count==0 else "FAIL"
    _write(receipts/"magic_drc.json",{"format":"automx-cim-magic-drc-v1","status":status,"timestamp_utc":_now(),"violations":count,"log":str(logs/"drc/magic.log")})
    if status!="PASS":
        rules=re.findall(r"AUTOMX_DRC_RULE: ([^\n]+)",text)
        detail="; ".join(rules) if rules else "no rule breakdown available"
        raise RuntimeError(f"Magic DRC failed with {count} violations: {detail}; see results/sky130/drc/magic.log")
    deck=_klayout_deck(pdk); report=logs/"drc/klayout.xml"
    kr=_run([tools["klayout"],"-b","-r",str(deck),"-rd",f"input={views['gds']}","-rd",f"report={report}"],build,timeout_s)
    (logs/"drc/klayout.log").write_text(kr.stdout+kr.stderr)
    violations=-1
    if report.is_file(): violations=len(re.findall(r"<item>",report.read_text(errors="replace")))
    kstatus="PASS" if kr.returncode==0 and violations==0 else "FAIL"
    _write(receipts/"klayout_drc.json",{"format":"automx-cim-klayout-drc-v1","status":kstatus,"timestamp_utc":_now(),"violations":violations,"deck":str(deck),"log":str(logs/"drc/klayout.log")})
    if kstatus!="PASS": raise RuntimeError(f"KLayout DRC failed or report could not be parsed: violations={violations}")
    lvs_spice=build/f"{CORE}.lvs.spice"
    ext_tcl=f'''crashbackups stop\nload {CORE}\nselect top cell\nextract do local\nextract all\next2spice lvs\next2spice scale off\next2spice subcircuit on\next2spice -o {lvs_spice.name}\nputs "AUTOMX_EXTRACT_DONE"\nquit -noprompt\n'''
    er=_magic(tools["magic"],tech,build,ext_tcl,timeout_s); (logs/"lvs").mkdir(parents=True,exist_ok=True); (logs/"lvs/magic_extract.log").write_text(er.stdout+er.stderr)
    if er.returncode or not lvs_spice.is_file(): raise RuntimeError("Magic LVS extraction failed")
    layout_nfets=_spice_device_count(lvs_spice,CORE,"sky130_fd_pr__nfet_01v8")
    expected_nfets=4*4*8
    if layout_nfets != expected_nfets:
        _write(receipts/"netgen_lvs.json",{"format":"automx-cim-netgen-lvs-v1","status":"FAIL","timestamp_utc":_now(),"reason":"layout transistor cardinality mismatch before Netgen","layout_nfets":layout_nfets,"expected_nfets":expected_nfets,"extracted_spice":str(lvs_spice)})
        raise RuntimeError(f"Magic extracted {layout_nfets} NFETs; expected {expected_nfets}. Inspect {lvs_spice} before Netgen LVS")
    reference=build/f"{CORE}.reference.spice"; reference.write_text(views["spice"].read_text().replace("VSUBS","VGND"),encoding="utf-8")
    extracted_norm=build/f"{CORE}.lvs_norm.spice"; extracted_norm.write_text(lvs_spice.read_text().replace("VSUBS","VGND"),encoding="utf-8")
    lvs_log=logs/"lvs/netgen.log"; nr=_run([tools["netgen"],"-batch","lvs",f"{extracted_norm} {CORE}",f"{reference} {CORE}",str(setup),str(lvs_log)],build,timeout_s)
    ltext=lvs_log.read_text(errors="replace") if lvs_log.is_file() else nr.stdout+nr.stderr
    match=("match uniquely" in ltext.lower() or "circuits match" in ltext.lower()) and "not equivalent" not in ltext.lower()
    _write(receipts/"netgen_lvs.json",{"format":"automx-cim-netgen-lvs-v1","status":"PASS" if nr.returncode==0 and match else "FAIL","timestamp_utc":_now(),"match":match,"log":str(lvs_log)})
    if nr.returncode or not match: raise RuntimeError("Netgen LVS mismatch; see results/sky130/lvs/netgen.log")
    pex=views["extracted_spice"]; raw_pex=build/f"{CORE}.pex.raw.spice"
    # Never treat an output from a previous successful run as current proof.
    for generated in (raw_pex,pex):
        if generated.is_file(): generated.unlink()
    # Magic >=8.3.597 performs full RCX during "extract all" when
    # "extract do resistance" is enabled.  Running extresist all again can
    # fail after extraction and is unnecessary.  Preserve the shorted
    # VGND/VSUBS ports as separate SPICE arguments for Stage-4 testbenches.
    pex_tcl=f'''crashbackups stop
load {CORE}
select top cell
flatten {CORE}_pex
load {CORE}_pex
select top cell
extract do local
# Flattening 16 leaf instances exposes repeated local labels (WPOS, WNEG,
# WLP, WLN, etc.).  Give electrically distinct nets unique names before
# RC extraction so ext2spice cannot conflate them in the flat PEX view.
extract do unique
extract do resistance
extresist threshold 100
extresist mindelay 0
extresist minres 10
extract all
puts "AUTOMX_PEX_EXTRACT_DONE"
ext2spice lvs
ext2spice scale off
ext2spice cthresh 0.1
ext2spice extresist on
ext2spice short resistor
ext2spice subcircuit on
ext2spice subcircuit top on
ext2spice -o {raw_pex}
puts "AUTOMX_PEX_DONE"
quit -noprompt
'''
    pr=_magic(tools["magic"],tech,build,pex_tcl,timeout_s); (logs/"pex").mkdir(parents=True,exist_ok=True)
    pex_text=pr.stdout+pr.stderr; pex_log=logs/"pex/magic.log"; pex_log.write_text(pex_text)
    rc_nets_output=sum(int(value) for value in re.findall(r"(?m)^Nets output:\s*(\d+)",pex_text))
    pex_error=None; raw_pins=None
    if pr.returncode==0 and "AUTOMX_PEX_DONE" in pex_text and raw_pex.is_file() and raw_pex.stat().st_size and rc_nets_output>0:
        try:
            raw_pins=_canonicalize_pex_interface(raw_pex,pex)
        except (OSError,ValueError) as error:
            pex_error=str(error)
    elif rc_nets_output==0 and "AUTOMX_PEX_DONE" in pex_text:
        pex_error="RC extraction produced zero resistor networks"
    else:
        pex_error="Magic did not finish RCX/SPICE output"
    pstatus="PASS" if pex_error is None and pex.is_file() and pex.stat().st_size else "FAIL"
    _write(receipts/"pex.json",{"format":"automx-cim-pex-v1","status":pstatus,"timestamp_utc":_now(),"extracted_spice":str(pex),"raw_extracted_spice":str(raw_pex),"sha256":_hash(pex) if pstatus=="PASS" else None,"returncode":pr.returncode,"extract_marker_seen":"AUTOMX_PEX_EXTRACT_DONE" in pex_text,"done_marker_seen":"AUTOMX_PEX_DONE" in pex_text,"rc_nets_output":rc_nets_output,"raw_pins":list(raw_pins) if raw_pins else None,"error":pex_error,"log":str(pex_log)})
    if pstatus!="PASS": raise RuntimeError(f"PEX failed (Magic exit {pr.returncode}): {pex_error}; see {pex_log}")
    # Post-layout decks retain Stage-4 stimuli/measurements and substitute only the included DUT.
    artifact=macro_artifact
    from automx_cim.spice import parse_measurements, validate_measurements
    all_values={}; failures=[]; postdir=logs/"post_layout"; postdir.mkdir(parents=True,exist_ok=True)
    for job in artifact.get("jobs",[]):
        src=Path(job["testbench"]).read_text()
        src=re.sub(r'(?im)^\.include\s+"[^"]*automx_ternary_cim_4x4_core\.spice"',f'.include "{pex.as_posix()}"',src)
        src=re.sub(rf'(?m)^(XMACRO[^\n]*\s){CORE}$',rf'\1{CORE}_pex',src)
        deck_path=postdir/f"{job['name']}.spice"; deck_path.write_text(src); log=postdir/f"{job['name']}.log"
        rr=_run([tools["ngspice"],"-b","-o",str(log),str(deck_path)],postdir,timeout_s)
        l=log.read_text(errors="replace") if log.is_file() else rr.stdout+rr.stderr
        expected=[x["measurement"] for x in job["cases"]]+list(job["delay_measurements"])+[artifact["energy_measurement"]]
        vals=parse_measurements(l,expected=expected); _,bad=validate_measurements(job["cases"],job["delay_measurements"],vals); failures += [f"{job['name']}: {x}" for x in bad]
        if rr.returncode: failures.append(f"{job['name']}: ngspice exit {rr.returncode}")
        all_values[job["name"]]=vals
    post={"format":"automx-cim-post-layout-v1","status":"PASS" if not failures else "FAIL","timestamp_utc":_now(),"jobs":all_values,"failures":failures[:100],"pex_sha256":_hash(pex)}
    _write(receipts/"post_layout.json",post)
    if failures: raise RuntimeError("post-layout validation failed: "+"; ".join(failures[:5]))
    # Preserve a compact, machine-readable pre/post comparison.  Measurement
    # keys are identical because post-layout reuses the Stage-4 stimuli.
    post_flat={k:v for values in all_values.values() for k,v in values.items()}
    pre_values=pre_layout.get("measurements",{})
    common=sorted(set(pre_values).intersection(post_flat))
    comparison={key:{"pre":pre_values[key],"post":post_flat[key],
                     "relative_delta":_relative_delta(post_flat[key],pre_values[key])}
                for key in common}
    compare_receipt={
        "format":"automx-cim-pre-post-comparison-v1",
        "status":"PASS",
        "timestamp_utc":_now(),
        "macro":CORE,
        "pre_layout_receipt":str(Path(macro_artifact["receipt"]).resolve()),
        "post_layout_receipt":str((receipts/"post_layout.json").resolve()),
        "measurement_count":len(comparison),
        "measurements":comparison,
    }
    _write(receipts/"pre_post_comparison.json",compare_receipt)
    evidence_names=("preflight.json","layout.json","magic_drc.json","klayout_drc.json",
                    "netgen_lvs.json","pex.json","post_layout.json","pre_post_comparison.json")
    summary={
        "format":"automx-cim-stage5-summary-v1",
        "status":"PASS",
        "timestamp_utc":_now(),
        "macro":CORE,
        "contract_sha256":_hash(cp),
        "config_sha256":manifest.get("config_sha256"),
        "views":{name:{"path":str(path),"sha256":_hash(path)}
                 for name,path in views.items() if path.is_file()},
        "receipts":{name:_hash(receipts/name) for name in evidence_names},
    }
    _write(receipts/"stage5_summary.json",summary)
    return {"status":"PASS","macro":CORE,"views":{k:str(v) for k,v in views.items()},"receipts":str(receipts),
            "pre_post_comparison":str((receipts/"pre_post_comparison.json").resolve()),
            "summary":str((receipts/"stage5_summary.json").resolve())}
