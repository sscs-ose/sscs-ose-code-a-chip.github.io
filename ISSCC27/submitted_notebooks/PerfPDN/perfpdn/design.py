"""Export a flat design, verify its layout, and identify devices through LVS."""
import cmath
import math
import hashlib
import json
import re
import shutil
from pathlib import Path
import klayout.db as db
import klayout.rdb as rdb
from .native import execute, number
from .project import ROOT, PDK
from .mesh import METALS


def read_design(project, folder):
    folder.mkdir(parents=True, exist_ok=True)
    source = Path(project["testbench"])
    if source.suffix == ".sch":
        execute(["bash",str(ROOT/"scripts/xschem.sh"),"-x","-r","-q","-n",
                 "-o",str(folder),str(source)], folder, "xschem.log")
        netlist = folder/(source.stem+".spice")
    else:
        netlist = folder/"testbench.spice"
        shutil.copy2(source, netlist)
    text = re.sub(r"\n\+", " ", netlist.read_text())
    text = re.sub(r"(?ims)^\s*\.control\b.*?^\s*\.endc\b", "", text)
    blocks = {m[1].lower():(m[2].split(), m[3]) for m in
              re.finditer(r"(?ims)^\.subckt\s+(\S+)\s+([^\n]+)\n(.*?)^\.ends[^\n]*", text)}
    name = project["subcircuit"].lower()
    if name not in blocks:
        raise ValueError(f"Missing design subcircuit {name}")
    pins, body = blocks[name]
    outside = re.sub(r"(?ims)^\.subckt\b.*?^\.ends[^\n]*", "", text)
    rows = [s.strip() for s in outside.splitlines() if s.strip() and not s.lstrip().startswith("*")]
    instances = [s.split() for s in rows if s[0].lower()=="x" and s.split()[-1].lower()==name]
    if len(instances) != 1:
        raise ValueError("The testbench must contain one instance of the selected design.")
    if len(instances[0][1:-1])!=len(pins):
        raise ValueError("The design instance pin count does not match its subcircuit.")
    ground = {s.lower() for s in project.get("ground_aliases", ["0","GND"])}
    aliases = dict(zip((p.lower() for p in instances[0][1:-1]), (p.lower() for p in pins)))
    aliases.update({g:"0" for g in ground})
    pin_nodes = {p.lower():aliases[n.lower()] for p,n in zip(pins,instances[0][1:-1])}
    devices = []
    for row in body.splitlines():
        row = row.strip()
        if not row or row.startswith("*"):
            continue
        fields = row.split()
        if fields[0][0].upper() != "X":
            raise ValueError(f"Unsupported design statement: {row}")
        model_index = next((i for i,f in enumerate(fields) if f.startswith("sky130_fd_pr__")), None)
        if model_index is None:
            raise ValueError("Use a flat design subcircuit with supported PDK primitives.")
        model = fields[model_index]
        kind = "res_poly" if model.endswith("res_high_po_0p35") else "pfet" if "__pfet_" in model else "nfet" if "__nfet_" in model else None
        if kind is None:
            raise ValueError(f"Unsupported PDK device: {model}")
        terminals = "abw" if kind=="res_poly" else "dgsb"
        if model_index != len(terminals)+1:
            raise ValueError(f"Unexpected terminal count: {row}")
        values = {k.lower():float(v) for k,v in re.findall(r"\b(L|W|nf|mult|m)=([-+0-9.eE]+)", row)}
        if any(values.get(k,1)!=1 for k in ("nf","mult","m")):
            raise ValueError("The current PDK terminal rules require one finger and multiplicity one.")
        required={"l"} if kind=="res_poly" else {"l","w"}
        if not required<=values.keys() or any(values[k]<=0 for k in required):
            raise ValueError("Use positive numeric device dimensions in micrometres.")
        device_name = fields[0][1:].lower()
        nets = [pin_nodes.get(n.lower(), n.lower()) for n in fields[1:model_index]]
        devices.append({"name":device_name,"model":model,"kind":kind,"pins":terminals,
                        "nets":dict(zip(terminals,nets)),"tail":" ".join(fields[model_index:]),
                        "schematic_nets":fields[1:model_index],"dimensions":values,"instance":fields[0]})
    directives = [s for s in rows if re.match(r"(?i)^\.(lib|include|option|temp)\b",s)]
    sources, capacitors = [], []
    for row in rows:
        f = row.split()
        if f[0][0].upper() not in ("V","C"):
            if not row.startswith(".") and f not in instances:
                raise ValueError(f"Unsupported testbench element: {row}")
            continue
        a,b = [aliases.get(n.lower(),n.lower()) for n in f[1:3]]
        if f[0][0].upper()=="C":
            if len(f)>5 or (len(f)==5 and not f[4].lower().startswith("m=")):
                raise ValueError("Use a constant load capacitor with optional numeric m=.")
            capacitance=number(f[3])*(number(f[4][2:]) if len(f)==5 else 1)
            if capacitance<=0:raise ValueError("Load capacitance must be positive.")
            capacitors.append({"name":f[0],"a":a,"b":b,"F":capacitance})
        else:
            if b!="0":
                raise ValueError("External voltage sources must use the declared ground reference.")
            value = number(f[4] if f[3].lower()=="dc" else f[3])
            ac = re.search(r"(?i)\bac\s+(\S+)(?:\s+([-+\d.eE]+))?", row)
            phasor = 0j if not ac else number(ac[1])*cmath.exp(1j*float(ac[2] or 0)*math.pi/180)
            sources.append({"name":f[0].lower(),"node":a,"dc":value,"ac":[phasor.real,phasor.imag]})
    if len({s["node"] for s in sources}) != len(sources):
        raise ValueError("Use one voltage source per driven boundary.")
    design = {"devices":devices,"pin_nodes":pin_nodes,"sources":sources,
              "capacitors":capacitors,"directives":directives}
    reference = []
    labels={p.lower():project["pin_labels"].get(p.lower(),p) for p in pins}
    for d in devices:
        v=d["dimensions"]
        dimensions=f'l={v["l"]:g}u'+("" if d["kind"]=="res_poly" else f' w={v["w"]:g}u')
        reference.append(" ".join([d["instance"],*[labels.get(n.lower(),n) for n in d["schematic_nets"]],d["model"],dimensions]))
    top=project["top_cell"]
    (folder/"reference.spice").write_text(f".subckt {top} {' '.join(labels[p.lower()] for p in pins)}\n"+"\n".join(reference)+f"\n.ends {top}\n")
    (folder/"design.json").write_text(json.dumps(design,indent=2)+"\n")
    return design


def verify(project, source, folder, reference):
    folder=Path(folder).resolve();source=Path(source).resolve();reference=Path(reference).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    layout=db.Layout();layout.read(str(source))
    if len(list(layout.top_cells()))!=1 or layout.top_cell().name!=project["top_cell"]:
        raise ValueError("Supply one top-level cell matching top_cell.")
    options=db.SaveLayoutOptions();options.format="OASIS";options.write_context_info=True
    layout.write(str(folder/"layout.oas"),options);layout.write(str(folder/"layout.gds"))
    shutil.copy2(reference,folder/"reference.spice")
    rules=PDK/"libs.tech/klayout"
    execute(["klayout","-b","-r",str(rules/"drc/sky130A_mr.drc"),"-rd",f"input={folder/'layout.gds'}",
             "-rd",f"report={folder/'drc.lyrdb'}","-rd","feol=true","-rd","beol=true","-rd","offgrid=true",
             "-rd","floating_met=true","-rd","seal=false","-rd","sram_exclude=false","-rd","thr=2"],folder,"drc.log")
    report=rdb.ReportDatabase();report.load(str(folder/"drc.lyrdb"))
    if report.num_items():
        raise ValueError(f"DRC: {report.num_items()} markers; see {folder/'drc.lyrdb'}")
    execute(["klayout","-b","-r",str(rules/"lvs/sky130.lvs"),"-rd",f"input={folder/'layout.gds'}",
             "-rd",f"top_cell={project['top_cell']}","-rd",f"schematic={folder/'reference.spice'}",
             "-rd",f"report={folder/'lvs.lvsdb'}","-rd",f"target_netlist={folder/'extracted.spice'}",
             "-rd","convert_subckts=true","-rd","scale=false","-rd","run_mode=flat","-rd","thr=2",
             "-rd",f"lvs_sub={project['substrate_net']}","-rd","schematic_simplify=true"],folder,"lvs.log")
    lvs=db.LayoutVsSchematic();lvs.read(str(folder/"lvs.lvsdb"))
    if not list(lvs.xref().each_circuit_pair()) or any(str(p.status())!="Match" for p in lvs.xref().each_circuit_pair()):
        raise ValueError(f"LVS mismatch: {folder/'lvs.log'}")
    proof={"drc_markers":0,"lvs_status":"Match","source_sha256":hashlib.sha256(Path(source).read_bytes()).hexdigest()}
    (folder/"verification.json").write_text(json.dumps(proof,indent=2)+"\n")


def map_devices(project, design, folder):
    layout=db.Layout();layout.read(str(folder/"layout.gds"));top=layout.cell(project["top_cell"])
    lvs=db.LayoutVsSchematic();lvs.read(str(folder/"lvs.lvsdb"))
    pair=next(p for p in lvs.xref().each_circuit_pair() if p.first() and p.first().name==top.name)
    records={(d["model"].lower(),d["instance"][2:]):d for d in design["devices"]}
    placements={};seen=set()
    for match in lvs.xref().each_device_pair(pair):
        physical, schematic=match.first(),match.second()
        d=records[schematic.device_class().name.lower(),schematic.name]
        instances=[i for i in top.each_inst() if i.dbbox().contains(physical.trans.disp)]
        if len(instances)!=1:
            raise ValueError("Device mapping requires unambiguous supported PCell instances.")
        inst=instances[0];origin=(round(inst.dcplx_trans.disp.x,6),round(inst.dcplx_trans.disp.y,6))
        placements[origin]=(d["name"],d["kind"]);seen.add(d["name"])
    if seen!={d["name"] for d in design["devices"]}:
        raise ValueError("Incomplete LVS device mapping.")
    ports=[]
    for pin,node in design["pin_nodes"].items():
        label=project["pin_labels"].get(pin,pin).lower()
        found=[]
        for index in layout.layer_indices():
            info=layout.get_info(index)
            layers={v[0]:k for k,v in METALS.items()}
            if info.layer in layers and info.datatype==5:
                if any(s.is_text() and s.text.string.lower()==label for s in top.shapes(index).each()):
                    found.append((node,layers[info.layer],info.layer,label))
        if len(found)!=1:
            raise ValueError(f"Expected one labeled footprint for {pin}.")
        ports.extend(found)
    return placements,ports
