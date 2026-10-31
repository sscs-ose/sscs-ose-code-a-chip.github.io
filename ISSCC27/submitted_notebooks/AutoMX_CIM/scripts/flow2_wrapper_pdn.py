"""Conservative ADC power access for the pinned OpenLane 1 wrapper flow.

The ADC LEF exposes its complete internal M4/M5 supply mesh as many PORTs.
Expose one real, continuous M4 landing per supply instead. All hidden supply
metal becomes OBS; signal ports, GDS, origin, dimensions and nets are unchanged.
This is an access abstraction, not a repair or proof of the ADC internal grid.
Final GDS DRC and independent transistor LVS remain required.
"""
# This file is also a standalone CLI in OpenLane's Python 3.6 container.
# Keep its import path and syntax compatible; host-only imports stay lazy.
from pathlib import Path
import re
import struct
from hashlib import sha256

POLICY = "adc_left_ring_m4_access_v1"
CHECKER_SELF_TEST_MARKER = "AUTOMX_WRAPPER_PDN_CHECKER_SELF_TEST_PASS"
RECIPE = Path("scripts/flow2_wrapper_pdn.py")
PDN_TCL = Path("physical/sky130/wrapper_prototype/pdn_mixed_wrapper.tcl")
GROUND_REPAIR_TCL = Path("physical/sky130/wrapper_prototype/repair_wrapper_ground.tcl")
LANDINGS = {"VDD": (-2.080, 3.280, -.480, 399.280),
            "VSS": (-5.380, -.020, -3.780, 402.580)}
PLACEMENT = (3100., 50.)
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
RECT = re.compile(r"\bRECT\s+(" + _NUMBER + r")\s+(" + _NUMBER +
                  r")\s+(" + _NUMBER + r")\s+(" + _NUMBER + r")\s*;")


def pins(text):
    return {m[1]: m[0] for m in re.finditer(
        r"(?ms)^  PIN (\S+)\s*\n.*?^  END \1\s*$", text)}


def geometry(block):
    """Only rectangular routing access is supported by this pinned recipe."""
    if re.search(r"\b(?:POLYGON|PATH|VIA|ITERATE)\b", block):
        raise ValueError("unsupported ADC pin geometry; inspect the new LEF")
    layer = None
    for line in block.splitlines():
        match = re.search(r"\bLAYER\s+(\S+)\s*;", line)
        if match:
            layer = match[1]
        for match in RECT.finditer(line):
            if layer is None:
                raise ValueError("ADC rectangle without layer")
            yield layer, tuple(map(float, match.groups()))


def abstract_adc(text):
    original = pins(text)
    if not re.search(r"(?m)^MACRO adc_top\s*$", text) or not {"VDD", "VSS"} <= original.keys():
        raise ValueError("pinned adc_top supply interface missing")
    hidden = []
    for name, landing in LANDINGS.items():
        block = original[name]
        shapes = list(geometry(block))
        if ("met4", landing) not in shapes:
            raise ValueError("real ADC left-ring landing changed: " + name)
        if len(shapes) != len(set(shapes)):
            raise ValueError("ambiguous duplicate ADC supply geometry")
        use = "POWER" if name == "VDD" else "GROUND"
        replacement = (f"  PIN {name}\n    DIRECTION INOUT ;\n    USE {use} ;\n    PORT\n"
                       "      LAYER met4 ;\n        RECT " + " ".join(f"{v:.3f}" for v in landing) +
                       f" ;\n    END\n  END {name}")
        text = text.replace(block, replacement, 1)
        hidden.extend((layer, rect) for layer, rect in shapes if (layer, rect) != ("met4", landing))
    # Preserve every original obstruction. The unused supply access rectangles
    # become additional obstacles, preventing a router from using hidden metal.
    match = re.search(r"(?ms)^  OBS\s*\n(.*?)^  END\s*\n(?=END adc_top)", text)
    if not match:
        raise ValueError("ADC obstruction section missing")
    extra = ""
    for layer, rect in hidden:
        extra += f"      LAYER {layer} ;\n        RECT " + " ".join(f"{v:.3f}" for v in rect) + " ;\n"
    text = text[:match.end(1)] + extra + text[match.end(1):]
    after = pins(text)
    if set(after) != set(original) or any(after[n] != b for n, b in original.items() if n not in LANDINGS):
        raise ValueError("ADC signal pin contract changed")
    return text, {"policy": POLICY, "supply_access": {n: {"layer": "met4", "rect_um": list(r)}
                     for n, r in LANDINGS.items()}, "hidden_supply_rectangles_preserved_as_OBS": len(hidden),
                 "signal_pin_count_unchanged": len(original)-2,
                 "gds_modified": False, "internal_ADC_PG_connectivity": "PENDING_FULL_TRANSISTOR_LVS"}


def verify_ring_gds(data):
    """Require both exposed rectangles on the actual adc_top M4 drawing layer.

    The pinned ADC draws these rings as rectangular BOUNDARY elements in its
    top structure. No recursive bounding-box approximation or pin text is used.
    """
    offset=0;cell=None;element=None;unit=None;rectangles=[]
    while offset<len(data):
        if offset+4>len(data):raise ValueError('truncated ADC GDS record')
        length,kind,_=struct.unpack('>HBB',data[offset:offset+4])
        if length<4 or length%2 or offset+length>len(data):raise ValueError('invalid ADC GDS record')
        value=data[offset+4:offset+length];offset+=length
        if kind==3:
            if len(value)!=16:raise ValueError('bad ADC GDS units')
            v=value[8:]
            unit=(-1 if v[0]&128 else 1)*(int.from_bytes(v[1:],'big')/2**56)*16.**((v[0]&127)-64)*1e6
        elif kind==6:cell=value.rstrip(b'\0').decode('ascii')
        elif kind==7:cell=None
        elif kind==8:element={}
        elif element is not None:
            if kind==13:element['layer']=int.from_bytes(value,'big')
            elif kind==14:element['datatype']=int.from_bytes(value,'big')
            elif kind==16:
                if len(value)%8:raise ValueError('bad ADC GDS coordinates')
                v=struct.unpack('>'+('i'*(len(value)//4)),value)
                element['xy']=list(zip(v[::2],v[1::2]))
            elif kind==17:
                xy=element.get('xy',[])
                if cell=='adc_top' and element.get('layer')==71 and element.get('datatype')==20:
                    if not unit or len(xy)!=5 or xy[0]!=xy[-1]:
                        element=None;continue
                    xs,ys={x for x,y in xy},{y for x,y in xy}
                    if len(xs)==len(ys)==2 and set(xy)=={(x,y) for x in xs for y in ys}:
                        rectangles.append((min(xs)*unit,min(ys)*unit,max(xs)*unit,max(ys)*unit))
                element=None
    for net,rect in LANDINGS.items():
        if not any(all(abs(a-b)<1e-7 for a,b in zip(rect,other)) for other in rectangles):
            raise ValueError('ADC supply landing is not a real top-level M4 GDS rectangle: '+net)
    return {'expanded_GDS_sha256':sha256(data).hexdigest(),'actual_GDS_M4_landings_verified':list(LANDINGS),
            'gds_layer_datatype':[71,20]}


def prepare(root, destination, *, gds_data):
    from scripts import audit_flow2_adc_ip as ip
    from scripts.flow2_integration_common import _sha
    root, destination = Path(root), Path(destination)
    source = root / ip.FILES["lef"]
    if _sha(source) != ip.EXPECTED_SHA256["lef"]:
        raise ValueError("pinned ADC LEF changed")
    derived, proof = abstract_adc(source.read_text(encoding="utf-8"))
    proof.update(verify_ring_gds(gds_data))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_text(encoding="utf-8") != derived:
        raise FileExistsError("ADC power-access abstract changed; use a new run tag")
    if not destination.exists():
        with destination.open('w',encoding='utf-8',newline='\n') as stream:
            stream.write(derived)
    proof.update(source_lef_sha256=_sha(source), derived_lef_sha256=_sha(destination),
                 recipe_sha256=_sha(root/RECIPE), pdn_tcl_sha256=_sha(root/PDN_TCL))
    return proof


def locate_unconnected(text):
    """Map the supplied PSM coordinates back to actual ADC power ring geometry."""
    result = []
    pattern = (r"Unconnected PDN node on net (\S+) at location \((" + _NUMBER +
               r")um,\s*(" + _NUMBER + r")um\), layer:\s*(\d+)")
    for net, x, y, layer in re.findall(pattern, text):
        x, y = float(x), float(y)
        local = (x-PLACEMENT[0], y-PLACEMENT[1])
        supply = "VDD" if net == "VPWR" else "VSS" if net == "VGND" else None
        rect = LANDINGS.get(supply)
        on_ring = bool(rect and rect[0] <= local[0] <= rect[2] and rect[1] <= local[1] <= rect[3])
        result.append({"net": net, "xy_um": [x,y], "routing_level": int(layer),
                       "ADC_local_xy_um": list(local), "on_ADC_left_power_ring": on_ring})
    return result


def audit_pdn(run_dir):
    run_dir = Path(run_dir)
    logs = sorted((run_dir/"logs/floorplan").glob("*-pdn.log"))
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in logs)
    complete = {net: f"All PDN stripes on net {net} are connected." in text for net in ("VPWR", "VGND")}
    errors = [s for s in text.splitlines() if re.search(r"\[(?:ERROR|FATAL)\b", s)]
    def_path = run_dir/"results/floorplan/automx_cim_mixed_signal_proto.def"
    data = def_path.read_text(encoding="utf-8", errors="replace") if def_path.is_file() else ""
    connections = def_supply_connections(data.splitlines())
    passed = bool(logs) and all(complete.values()) and not errors and all(all(v.values()) for v in connections.values())
    return {"status": "PASS_WRAPPER_PDN_CONNECTIVITY" if passed else "WRAPPER_PDN_NOT_VERIFIED",
            "policy": POLICY, "native_supply_checks": complete, "macro_supply_connections": connections,
            "errors": errors, "unconnected_nodes": locate_unconnected(text),
            "logs": [str(p) for p in logs], "scope": "PDN connectivity only; no IR-drop or EM qualification"}


def def_supply_connections(lines):
    """Read explicit ITerms from NETS and SPECIALNETS in linear time.

    The pinned OpenDB writer emits macro ITerms in NETS, while SPECIALNETS
    contains wildcard supply rails and routing. Wildcards alone are not used
    as evidence of a particular macro's connection. Stop parsing connection
    tuples at the first '+' option so routed coordinates cannot match a pin.
    """
    pairs={"VPWR":(("core_i","VPWR"),("condition_i","VPWR"),("adc_i","VDD")),
           "VGND":(("core_i","VGND"),("condition_i","VGND"),("adc_i","VSS"))}
    found={net:set() for net in pairs};section=None;net=None;connections=False
    for raw in lines:
        row=raw.strip()
        if row.startswith(('NETS ', 'SPECIALNETS ')):
            section=row.split()[0];net=None;connections=False;continue
        if row in ('END NETS','END SPECIALNETS'):
            section=None;net=None;connections=False;continue
        if section is None:continue
        if row.startswith('-'):
            fields=row[1:].lstrip().split(None,1)
            net=fields[0] if fields and fields[0] in pairs else None
            connections=net is not None
            row=fields[1] if len(fields)==2 else ''
        if connections:
            prefix=row.split('+',1)[0].split(';',1)[0]
            found[net].update(re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',prefix))
            if '+' in row or ';' in row:connections=False
    return {net:{inst+'/'+pin: (inst,pin) in found[net] and
                 not any((inst,pin) in v for n,v in found.items() if n!=net)
                 for inst,pin in targets} for net,targets in pairs.items()}


def floorplan_hook():
    # OpenLane's own gen_pdn performs the native PSM checks inside floorplan.
    # Save an explicit milestone only after that function actually returns.
    checker=Path(__file__).resolve().as_posix()
    if any(c in checker for c in '{}\n\r'):raise ValueError('unsupported checker path')
    return r'''if {[llength [info procs run_floorplan]] != 1} {error "run_floorplan missing"}
rename run_floorplan automx_original_wrapper_floorplan
proc run_floorplan {args} {
    if {$::env(FP_PDN_CHECK_NODES) != 1} {error "PDN connectivity check must stay enabled"}
    automx_original_wrapper_floorplan {*}$args
    set def [file join $::env(RUN_DIR) results floorplan $::env(DESIGN_NAME).def]
    if {[catch {exec python3 {@CHECKER@} --check-def $def 2>@1} output options]} {
        return -options $options "wrapper PDN DEF check failed:\n$output"
    }
    puts $output
    puts AUTOMX_WRAPPER_PDN_FLOORPLAN_COMPLETE
}
'''.replace('@CHECKER@',checker)


def checker_self_test():
    """Exercise the native CLI's positive and negative paths before synthesis."""
    import sys
    valid=('NETS 2 ;\n'
        '- VPWR ( core_i VPWR ) ( condition_i VPWR ) ( adc_i VDD ) + USE POWER ;\n'
        '- VGND ( core_i VGND ) ( condition_i VGND ) ( adc_i VSS ) + USE GROUND ;\n'
        'END NETS\nSPECIALNETS 2 ;\n'
        '- VPWR ( * VPWR ) + ROUTED met4 1600 ( 0 0 ) ( 10 10 ) ;\n'
        '- VGND ( * VGND ) + ROUTED met4 1600 ( 0 0 ) ( 10 10 ) ;\nEND SPECIALNETS\n')
    found=def_supply_connections(valid.splitlines())
    missing=def_supply_connections(valid.replace('( adc_i VSS )','').splitlines())
    conflict=def_supply_connections(valid.replace('- VGND ( core_i','- VGND ( adc_i VDD ) ( core_i',1).splitlines())
    if (not all(v for pins in found.values() for v in pins.values()) or
            missing['VGND']['adc_i/VSS'] or conflict['VPWR']['adc_i/VDD']):
        raise RuntimeError('DEF checker positive/negative self-test failed')
    return {'format':'automx-cim-wrapper-def-checker-runtime-v1','status':'PASS',
            'python_version':sys.version,'valid_DEF':True,'missing_ground_rejected':True,
            'conflicting_supply_rejected':True}


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description='Check explicit macro supply connections in native DEF')
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-def',type=Path)
    mode.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:
        print(json.dumps(checker_self_test(),sort_keys=True))
        print(CHECKER_SELF_TEST_MARKER)
        raise SystemExit(0)
    with args.check_def.open(encoding='utf-8',errors='replace') as stream:
        result=def_supply_connections(stream)
    print(json.dumps(result,sort_keys=True))
    missing=[net+':'+pin for net,pins in result.items() for pin,ok in pins.items() if not ok]
    if missing:raise SystemExit('wrapper macro supply connections missing or conflicting: '+', '.join(missing))
    print('AUTOMX_WRAPPER_PDN_DEF_CONNECTIONS_PASS')
