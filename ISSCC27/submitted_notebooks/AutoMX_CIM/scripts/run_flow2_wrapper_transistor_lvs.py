"""Independent full-GDS transistor LVS/PEX after prototype OpenLane routing."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import re

from scripts import flow2_integration_common as common
from scripts import flow2_wrapper_design as d
from scripts import flow2_wrapper_physical as physical
from scripts import flow2_adc_c_only as reduction


def definitions(text):
    result, block, name = {}, [], None
    for row in reduction.cards(text):
        f = row.split()
        if f and f[0].lower() == '.subckt':
            if name is not None:
                raise ValueError('nested subcircuit definition')
            name = f[1].lower()
            if name in result:
                raise ValueError('duplicate subcircuit definition: '+name)
            block = [row]
        elif f and f[0].lower() == '.ends':
            if name is None or (len(f) > 1 and f[1].lower() != name):
                raise ValueError('unmatched .ends')
            result[name] = '\n'.join([*block, row])
            name = None
        elif name is not None:
            block.append(row)
    if name is not None:
        raise ValueError('unterminated subcircuit: '+name)
    return result


def port_order(block):
    fields = next(row.split()[2:] for row in reduction.cards(block) if row.lstrip().lower().startswith('.subckt'))
    pins = fields[:next((i for i, v in enumerate(fields) if '=' in v or v.lower() == 'params:'), len(fields))]
    if len(set(p.lower() for p in pins)) != len(pins):
        raise ValueError('duplicate formal ports')
    return pins


def instance(row):
    f = row.split()
    end = next((i for i, v in enumerate(f) if '=' in v or v.lower() == 'params:' or v.startswith('$')), len(f))
    return f, end-1


# These are device classes used by the actual core/conditioner/ADC/HD library.
# A prefix alone is not evidence that an unresolved X is a physical device.
PRIMITIVES = {name: count for name, count in (
    ('sky130_fd_pr__nfet_01v8', 4), ('sky130_fd_pr__nfet_01v8_lvt', 4),
    ('sky130_fd_pr__pfet_01v8', 4), ('sky130_fd_pr__pfet_01v8_hvt', 4),
    ('sky130_fd_pr__cap_mim_m3_1', 2), ('sky130_fd_pr__res_generic_po', 2),
    ('sky130_fd_pr__diode_pw2nd_05v5', 2))}
GEOMETRY_ONLY = re.compile(r'sky130_(?:fd|ef)_sc_hd__(?:fill_\d+|tap_\d+|tapvgnd2?_\d+|tapvpwrvgnd_\d+)$')


def validate_hierarchy(text, cell):
    """Resolve every reachable device and bulk through the full source hierarchy.

    Internal ADC ports remain internal nets; unconnected substrate names never
    become ground by convention. Source and bulk are checked independently.
    """
    defs = definitions(text)
    counts = Counter()
    ports = port_order(defs[cell.lower()])
    if not {'vgnd', 'vpwr'} <= {p.lower() for p in ports}:
        raise ValueError('wrapper must expose VPWR and VGND')

    def walk(model, nets, path, ancestors):
        if model in ancestors:
            raise ValueError('recursive reference hierarchy: '+model)
        block = defs[model]
        pins = port_order(block)
        if len(pins) != len(nets):
            raise ValueError('instance port count differs for '+path+': '+model)
        mapping = dict(zip((p.lower() for p in pins), nets))
        def resolve(node):
            return mapping.get(node.lower(), path+'/'+node.lower())
        elements = 0
        for row in reduction.cards(block):
            f = row.split()
            if not f or f[0].startswith(('*', '.')):
                continue
            elements += 1
            kind = f[0][0].lower()
            if kind in 'rc' and len(f) == 4 and reduction.number(f[3]) is not None:
                counts[kind] += 1
                continue
            if kind not in 'xmrcd':
                raise ValueError('unsupported reference element: '+row)
            f, index = instance(row)
            device = f[index].lower()
            args = [resolve(n) for n in f[1:index]]
            if device in PRIMITIVES:
                if len(args) != PRIMITIVES[device]:
                    raise ValueError('primitive terminal count differs: '+row)
                counts[device] += 1
                if device == 'sky130_fd_pr__diode_pw2nd_05v5' and args[0] != 'vgnd':
                    raise ValueError('unresolved/wrong diode p-body '+path+'/'+f[0]+': '+args[0])
                if '__nfet_' in device or '__pfet_' in device:
                    rail = 'vgnd' if '__nfet_' in device else 'vpwr'
                    if args[3] != rail:
                        raise ValueError('unresolved/wrong substrate '+path+'/'+f[0]+': '+args[3]+'; expected '+rail)
                    if f[0].upper().startswith('XPRE_') and args[2] != 'vpwr':
                        raise ValueError('precharge source is not VPWR: '+path+'/'+f[0])
                    if args[2] != args[3]:
                        counts['independent_source_bulk_devices'] += 1
            elif kind == 'x' and device in defs:
                walk(device, args, path+'/'+f[0], (*ancestors, model))
            else:
                raise ValueError('unresolved transistor reference cell: '+device)
        if not elements and not GEOMETRY_ONLY.fullmatch(model):
            raise ValueError('empty/blackbox reference cell: '+model)

    walk(cell.lower(), [p.lower() for p in ports], cell, ())
    return {'device_counts': dict(counts), 'nfet_bulk': 'VGND', 'pfet_bulk': 'VPWR',
            'scope': 'all reachable instances resolved; source and bulk remain separate'}


def stdcell_pdk(pdk, source_run):
    """Use the library that supplied native GDS, retaining analog PDK provenance."""
    config = source_run/'config.tcl'
    if not config.is_file():
        raise ValueError('native run config.tcl required for standard-cell PDK provenance')
    match = re.search(r'(?m)^set\s+::env\(PDKPATH\)\s+["{]([^"}\n]+)["}]\s*$', config.read_text())
    if not match:
        raise ValueError('native config lacks literal PDKPATH')
    native = Path(match[1]).resolve()
    if not native.is_dir():
        raise FileNotFoundError('native standard-cell PDK: '+str(native))
    def provenance(path):
        source = path/'SOURCES'
        return {'path': str(path), 'sources': source.read_text().strip() if source.is_file() else None}
    return native, {'analog_extraction_pdk': provenance(pdk), 'native_stdcell_pdk': provenance(native),
                    'native_config_sha256': common._sha(config)}


def validate_netgen(log):
    # Intermediate subcells can match while the wrapper fails. Require the
    # final result, and only allow undefined calls for known PDK device classes.
    for name in re.findall(r'(?im)^Call to undefined subcircuit\s+(\S+)', log):
        if name.lower() not in PRIMITIVES:
            raise ValueError('Netgen unresolved non-device cell: '+name)
    results = re.findall(r'(?im)^(?:Final result|Result):[ \t]*(?:\r?\n[ \t]*)?([^\r\n]+?)[ \t]*$', log)
    if not results or results[-1].lower() != 'circuits match uniquely.':
        raise ValueError('Netgen lacks a final unique wrapper match')


def reorder_top_instances(top, abstract_defs, real_defs):
    """The LEF-export X argument order must match the real SPICE definition.

    Pin NAME agreement is insufficient when replacing an abstract cell.
    Keep real transistor subcircuits intact and reorder only top X arguments.
    """
    result=[]
    for row in reduction.cards(top):
        f=row.split()
        if f and f[0][0].lower()=='x':
            f,model_index=instance(row)
            model=f[model_index].lower()
            if model not in abstract_defs or model not in real_defs:
                raise ValueError('missing abstract/real model for '+f[0]+': '+model)
            old,new=([p.lower() for p in port_order(defs[model])] for defs in (abstract_defs,real_defs))
            args=f[1:model_index]
            if len(args)!=len(old) or len(old)!=len(new) or set(old)!=set(new):
                raise ValueError('LEF/transistor pin contract differs for '+model)
            mapping=dict(zip(old,args))
            row=' '.join([f[0],*[mapping[p] for p in new],*f[model_index:]])
        result.append(row)
    return '\n'.join(result)


def reference(root, pdk, source_run, core_reference, condition_reference):
    root,pdk,source_run,core_reference,condition_reference=map(Path,(root,pdk,source_run,core_reference,condition_reference))
    preferred=source_run/f'results/signoff/{d.TOP}.lef.spice'
    if not preferred.is_file():preferred=source_run/f'results/final/spi/lvs/{d.TOP}.spice'
    if not preferred.is_file():
        raise ValueError("need one powered LEF-export SPICE top; refusing a blackbox-only LVS claim")
    top_path=preferred;abstracts=definitions(top_path.read_text(encoding='utf-8'))
    if d.TOP.lower() not in abstracts:raise ValueError('powered LEF export lacks wrapper top')
    top=abstracts[d.TOP.lower()]
    # Contract numeric extraction R only to recover topology for LVS.
    # The actual distributed RC PEX is extracted separately from final GDS.
    adc,proof=reduction.reduce_text((root/d.ip.FILES["rc_spice"]).read_text(encoding="utf-8"))
    adc="\n".join(line for line in adc.splitlines() if not line.lstrip().lower().startswith('c'))
    rows=reduction.cards(adc)
    ports=next(row.split()[2:] for row in rows if row.lower().startswith('.subckt'))
    cell=next(row.split()[1] for row in rows if row.lower().startswith('.subckt'))
    if any(row.split() and row.split()[0].lower().startswith('r') and len(row.split())==4
           and reduction.number(row.split()[3]) is not None for row in rows):
        raise ValueError("wire R remains between formal ADC ports; explicit alias review required")
    public=d.ip._lef_pins((root/d.ip.FILES["lef"]).read_text(encoding="utf-8"))
    if len(public) != len(set(public)) or not set(public) <= set(ports):
        raise ValueError('ADC public LEF pins are missing/duplicated in RC ports')
    # Indexing avoids collisions when distinct bus/internal names sanitize alike.
    mapped=[p if p in public else 'PRIVATE_ADC_'+str(i) for i,p in enumerate(ports)]
    if len(set(mapped)) != len(mapped):
        raise ValueError('ADC private nodes collide with public ports')
    adapter=f".subckt adc_top {' '.join(public)}\nXREAL_ADC {' '.join(mapped)} {cell}\n.ends adc_top\n"
    native,provenance=stdcell_pdk(pdk,source_run)
    stdpath=native/"libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
    if not stdpath.is_file():raise FileNotFoundError("native standard-cell transistor library: "+str(stdpath))
    std=stdpath.read_text(encoding="utf-8")
    # Open-pdks may put efabless decap extensions in additional SPICE files.
    std_defs=definitions(std)
    std_sources={str(stdpath):common._sha(stdpath)}
    for extra in sorted(stdpath.parent.glob('*.spice')):
        if extra==stdpath:continue
        std_sources[str(extra)]=common._sha(extra)
        for name,block in definitions(extra.read_text(encoding='utf-8')).items():
            if name not in std_defs:std_defs[name]=block
    std='\n'.join(std_defs.values())
    blocks=[std,core_reference.read_text(encoding="utf-8"),condition_reference.read_text(encoding="utf-8"),adc,adapter]
    real_defs=definitions('\n'.join(blocks))
    top=reorder_top_instances(top,abstracts,real_defs)
    blocks.append(top)
    text="\n".join(re.sub(r"(?im)^\s*\.end\s*$", "",v) for v in blocks)+"\n"
    # Reject unknown digital/macro models; Netgen must not silently compare
    # two unresolved black boxes with the same names.
    connectivity=validate_hierarchy(text,d.TOP)
    return text,{"lef_spice_path":str(top_path),"lef_spice_sha256":common._sha(top_path),"native_stdcell_sha256":common._sha(stdpath),
        "stdcell_sources_sha256":std_sources, **provenance, "connectivity":connectivity,
        "adc_public_ports":public,"adc_rc_ports":ports,
        "adc_private_nodes":{p:n for p,n in zip(ports,mapped) if p not in public},
        "adc_lvs_topology":{k:v for k,v in proof.items() if k!='node_aliases'},
        "scope":"all standard cells/core/conditioner/ADC have transistor references; no model blackbox waiver"}


def run(root, *, pdk_root, tag, source_run, core_reference, condition_reference, timeout_s=3600):
    root,pdk=Path(root).resolve(),Path(pdk_root).resolve()
    source_run,core_reference,condition_reference=map(Path,(source_run,core_reference,condition_reference))
    source_run,core_reference,condition_reference=(p.resolve() if p.is_absolute() else (root/p).resolve()
        for p in (source_run,core_reference,condition_reference))
    out=root/common.BASE/tag
    r={}
    try:
        gds=source_run/f"results/final/gds/{d.TOP}.gds"
        if not gds.is_file() or not gds.stat().st_size:
            raise ValueError('actual final native GDS required before transistor extraction')
        text,proof=reference(root,pdk,source_run,core_reference,condition_reference)
        r['reference_proof']=proof
        top=definitions(text)[d.TOP.lower()]
        pins=port_order(top)
        tcl=f"crashbackups stop\ndrc off\ngds read {{{gds.as_posix()}}}\nload {d.TOP}\nselect top cell\n"
        tcl+="box -100um -100um 10000um 5000um\ndrc on\ndrc check\ndrc catchup\n"
        tcl+='puts "AUTOMX_WRAPPER_DRC=[drc list count total]"\n'
        # Keep the extraction input byte-identical to native final GDS. Magic
        # must not rewrite/requantize it before independent LVS and RC PEX.
        tcl+=f"file copy -force {{{gds.as_posix()}}} {d.TOP}.gds\nlef write {d.TOP}.lef\nputs AUTOMX_WRAPPER_LAYOUT_DONE\nquit -noprompt\n"
        r=physical.physical(root,pdk=pdk,tag=tag,cell=d.TOP,pins=pins,layout_tcl=tcl,reference=text,
            sources=[d.core.acq._item(root,p) for p in
                     (gds,core_reference,condition_reference,Path(__file__),Path(physical.__file__))],timeout_s=timeout_s)
        r['reference_proof']=proof
        if r.get('status') == 'BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS':
            validate_netgen((out/'lvs.log').read_text())
            extracted=root/common.BUILD/tag/'lvs_extract'/f'{d.TOP}.lvs.spice'
            r['extracted_connectivity']=validate_hierarchy(extracted.read_text(),d.TOP)
            layout=root/common.BUILD/tag/'layout'/f'{d.TOP}.gds'
            if common._sha(layout) != common._sha(gds):
                raise ValueError('extraction GDS differs from native final GDS')
            r['native_final_gds_sha256']=common._sha(gds)
    except FileExistsError:
        raise  # Preserve existing evidence when the cache identity differs.
    except Exception as error:
        r.update(status="BLOCKED_COMPOSITE_TRANSISTOR_CHECKS",error=f"{type(error).__name__}: {error}",
           scope="no transistor LVS/PEX pass inferred from LEF macro LVS")
        r['transistor_lvs_match']=False
    common.save_summary(out/"summary.json",r)
    common.bundle(root,tag)
    return r
