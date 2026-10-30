"""Construct the connected native circuit and retain its physical node solution."""
import csv
import json
from pathlib import Path
import numpy as np
from .native import spice, read_scalar_raw
from .mesh import build_network
from .project import PDK


def mesh(project, path, mapping):
    return build_network(path, PDK/"libs.tech/magic/sky130A.tech",
                         project["mesh_step_um"], *mapping)


def solve(design, network, folder):
    folder.mkdir(parents=True, exist_ok=False)
    fixed={"0":0.0, **{s["node"]:s["dc"] for s in design["sources"]}}
    adjacency={}
    for a,b,*_ in network["edges"]:
        adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
    offsets={}
    for node,value in fixed.items():
        if node in offsets:
            continue
        pending=[node];seen={node}
        while pending:
            for other in adjacency.get(pending.pop(),()):
                if other not in seen:
                    seen.add(other);pending.append(other)
        offsets.update(dict.fromkeys(seen,value))

    base=[*design["directives"],".option klu reltol=1e-8 abstol=1e-14 vntol=1e-10"]
    for source in design["sources"]:
        z=complex(*source["ac"])
        base.append(f'{source["name"]} {source["node"]} 0 DC {source["dc"]-offsets.get(source["node"],0):.17g} AC {abs(z):.17g} {np.angle(z,deg=True):.17g}')
    for load in design["capacitors"]:
        base.append(f'{load["name"]} {load["a"]} {load["b"]} {load["F"]:.17g}')
    ports=[];device_lines=[]
    for device in design["devices"]:
        nodes=[]
        for pin in device["pins"]:
            port=f'{device["name"]}_{pin}';terminal="t_"+port
            base.append(f'v_{port} {terminal} {port} {-offsets.get(terminal,0):.17g}')
            ports.append((port,terminal));nodes.append(port)
        row=" ".join([device["instance"],*nodes,device["tail"]])
        base.append(row);device_lines.append(row)
    base += [f"r{i} {a} {b} {r:.17g}" for i,(a,b,r,*_) in enumerate(network["edges"])]
    (folder/"base.cir").write_text("\n".join(base)+"\n")
    spice(["PerfPDN connected layout circuit",*base,".save all",".control","set filetype=ascii",
           "op","write op.raw all","quit",".endc",".end"],folder)
    raw=read_scalar_raw(folder/"op.raw")
    voltage=lambda n:0.0 if n=="0" else raw[f"v({n})"]+offsets.get(n,0)
    gauged=lambda n:0.0 if n=="0" else raw[f"v({n})"]
    balance={};loss=0;branches=[];drops=[]
    for i,(a,b,r,kind,face) in enumerate(network["edges"]):
        drop=gauged(a)-gauged(b);amps=drop/r
        drops.append(drop)
        balance[a]=balance.get(a,0)+amps;balance[b]=balance.get(b,0)-amps
        loss+=amps*drop
        branches.append([i,a,b,r,kind,drop,amps,amps/(face*1e-6) if face else None])
    for p,t in ports:
        balance[t]=balance.get(t,0)+raw[f"i(v_{p})"]
    currents={s["name"]:-raw[f'i({s["name"]})'] for s in design["sources"]}
    power=sum(s["dc"]*currents[s["name"]] for s in design["sources"])
    device_power=sum(raw[f"v({p})"]*raw[f"i(v_{p})"] for p,t in ports)
    residual=max((abs(v) for n,v in balance.items() if n not in fixed),default=0)
    if residual>1e-9 or abs(power-device_power-loss)>1e-9:
        raise ValueError("Connected solution failed current or power balance.")
    network["voltage_offsets_V"]=offsets
    state={"ports":ports,"design":design,"device_lines":device_lines,
           "source_currents_A":currents,"power_W":power,"metal_loss_W":loss,
           "KCL_residual_A":residual,"power_residual_W":power-device_power-loss,
           "node_voltages_V":{n:voltage(n) for n in adjacency},"edge_drops_V":drops,
           "terminal_voltages_V":{p:raw[f"v({p})"] for p,t in ports}}
    (folder/"network.json").write_text(json.dumps(network)+"\n")
    (folder/"summary.json").write_text(json.dumps(state,indent=2)+"\n")
    with (folder/"branches.csv").open("w") as f:
        writer=csv.writer(f);writer.writerow(["edge","a","b","R_ohm","kind","drop_V","current_A","sheet_current_A_per_m"]);writer.writerows(branches)
    with (folder/"nodes.csv").open("w") as f:
        writer=csv.writer(f);writer.writerow(["node","layer","x_um","y_um","dx_um","dy_um","voltage_V"])
        writer.writerows([*node,voltage(node[0])] for node in network["nodes"])
    return state
