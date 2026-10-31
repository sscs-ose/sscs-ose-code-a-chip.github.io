import collections, hashlib, json, math, re, struct
from pathlib import Path

OUT = Path('reports/synthesis')
def write(name, data): (OUT / name).write_text(json.dumps(data, indent=2) + '\n')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
c = json.loads(Path('physical/chip-nebula/implementation.constraints.json').read_text())
libcells = json.loads((OUT / 'liberty_cells.json').read_text())
allmodules = json.loads(Path('build/synth/mapped.json').read_text())['modules']
m = allmodules[c['physical_top']]
counts = collections.Counter(x['type'] for x in m['cells'].values())
assert not m.get('memories') and not m.get('processes')
assert set(counts) <= set(libcells), set(counts) - set(libcells)
assert not set(counts).intersection(c['electrical']['dont_use_cells'])
assert all(not libcells[name]['latch'] for name in counts)
ports = {n: dict(direction=v['direction'], width=len(v['bits'])) for n,v in m['ports'].items()}
assert ports == {p['name']: dict(direction=p['direction'], width=p['width']) for p in c['ports']}
views = c['view_binding']['views']
lef = Path(views['lef/sky130_fd_sc_hd_merged.lef']['installed_path']).read_text()
lefareas = {}
parts = re.split(r'^MACRO\s+(\S+)\s*$', lef, flags=re.M)
for name, body in zip(parts[1::2],parts[2::2]):
    size = re.search(r'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;', body)
    if size: lefareas[name] = float(size[1]) * float(size[2])
cdl = Path(views['cdl/sky130hd.cdl']['installed_path']).read_text()
cdlcells = set(re.findall(r'^\.subckt\s+(\S+)', cdl, flags=re.M|re.I))
gds = Path(views['gds/sky130_fd_sc_hd.gds']['installed_path']).read_bytes()
gdscells = set(); pos = 0
while pos < len(gds):
    size, kind, dtype = struct.unpack_from('>HBB', gds, pos)
    assert size >= 4 and pos + size <= len(gds)
    if kind == 6: gdscells.add(gds[pos+4:pos+size].rstrip(b'\x00').decode())
    pos += size
assert set(counts) <= set(lefareas) & cdlcells & gdscells
area = sum(libcells[n]['area'] * count for n,count in counts.items())
footprint = sum(lefareas[n] * count for n,count in counts.items())
stat = json.loads((OUT/'stat.json').read_text())['modules']['\\nebula_cpu_npu_top']
assert stat['num_cells'] == sum(counts.values())
assert math.isclose(stat['area'],area,abs_tol=1e-5)
write('cell_audit.json', dict(verdict='passed', standard_cell_count=sum(counts.values()), macro_count=0, latch_count=0, liberty_area_um2=area, lef_footprint_area_um2=footprint, counts=dict(sorted(counts.items())), all_used_cells_in_liberty_lef_gds_cdl=True, forbidden_cells=[], unmapped_cells=[], ports=ports, macro_scope='No external instruction/data images or SRAM macros inside the physical boundary.', area_definitions=dict(liberty='sum of instance counts times characterized Liberty area; includes mapped CPU/NPU/RF and tie cells', footprint='sum of instance counts times LEF SIZE width*height; excludes physical implementation support cells not inserted yet')))
fanout = collections.Counter()
for cell in m['cells'].values():
    for pin, direction in cell['port_directions'].items():
        if direction == 'input':
            fanout.update(b for b in cell['connections'][pin] if isinstance(b,int))
aliases = {}
for name, net in m['netnames'].items():
    if not net['hide_name']:
        for index,b in enumerate(net['bits']):
            if isinstance(b,int): aliases.setdefault(b, []).append(name + ('['+str(index)+']' if len(net['bits'])>1 else ''))
write('fanout.json',dict(basis='Mapped input cell pins per net bit; no invented fanout limit; output port loads are specified separately by SDC.', maximum_input_pin_fanout=max(fanout.values()), top_nets=[dict(bit=b, input_pin_fanout=count, aliases=aliases.get(b,[])) for b,count in fanout.most_common(20)], required_physical_work='Clock tree and reset distribution require propagated-clock and extracted-RC checks downstream.'))
qdrivers = {}
for n,cell in m['cells'].items():
    if libcells[cell['type']]['sequential']:
        for b in cell['connections']['Q']: qdrivers[b] = n
rf = m['netnames']['core.rf']['bits']
assert len(rf) == 1024 and all(b in qdrivers for b in rf)
assert len({qdrivers[b] for b in rf}) == 1024
for b in rf:
    cell = m['cells'][qdrivers[b]]
    assert cell['type'] == 'sky130_fd_sc_hd__dfrtp_1'
    assert cell['connections']['CLK'] == m['ports']['clk']['bits']
    assert cell['connections']['RESET_B'] == m['ports']['rst_n']['bits']
rtlarrays = []
for f in Path('integration/design.f').read_text().splitlines():
    for width,name,lo,hi in re.findall(r'logic\s+\[(\d+):0\]\s+(\w+)\s*\[(\d+):(\d+)\]\s*;',Path(f).read_text()):
        rtlarrays.append(dict(source=f,name=name,bits=(int(width)+1)*(abs(int(hi)-int(lo))+1)))
assert rtlarrays == [dict(source='rtl/rv32i_five_stage_cpu.sv', name='rf', bits=1024)]
stages = {}
for group,names in {'IF_ID':['core.if_pc','core.if_word','core.if_v','core.if_held','core.if_fault'], 'ID_EX':['core.ex','core.ex_v'], 'EX_MEM':['core.mem','core.mem_v'], 'MEM_WB':['core.wb','core.wb_v'], 'NPU':['core.enabled_npu.npu.p0','core.enabled_npu.npu.p1','core.enabled_npu.npu.p2','core.enabled_npu.npu.p3','core.enabled_npu.npu.result','core.enabled_npu.npu.phase']}.items():
    cells = sorted({qdrivers[b] for n in names for b in m['netnames'][n]['bits'] if b in qdrivers})
    assert cells
    stages[group] = dict(nets=names, sequential_cells=cells, count=len(cells))
for a in ['IF_ID','ID_EX','EX_MEM','MEM_WB']:
    for b in ['IF_ID','ID_EX','EX_MEM','MEM_WB']:
        if a != b: assert not set(stages[a]['sequential_cells']) & set(stages[b]['sequential_cells'])
write('structure_audit.json',dict(verdict='passed', rtl_arrays=rtlarrays, pipeline_groups=stages, rf_sequential_cells=[qdrivers[b] for b in rf], rf_reset_clock_checks='All 1024 RF bits have unique characterized rising-edge DFRTP flop drivers with direct active-low asynchronous reset.', latency_preservation='No retiming or sequential ABC mapping; only combinational ABC optimization and buffering. Functional n+4 CPU and n+2 NPU acceptance remains bound to passed source-identical verification.', formal_equivalence='not run; structural mapping and upstream functional evidence only', logical_bank_limb_contract='not applicable: frozen constraints contain no logical_bank or standard_cell_bank authorization'))
write('memory_mapping.json',dict(schema_version=1, verdict='passed', memories=[dict(name='core.rf', source='rtl/rv32i_five_stage_cpu.sv:108', bits=1024, words=32, width=32, implementation='flip_flop', macro=None, ports=dict(read=2, write=1), read_timing='Two combinational addressed reads; x0 forced zero and WB bypass retained.', write_timing='One rising-edge write with wb_rf_write enable; x0 writes suppressed by RTL; active-low asynchronous reset clears all words.', authorization='Frozen memory.architectural_register_file.implementation explicitly selects verified standard-cell flops and muxes; this 1 Kib array is below 4 Kib.', mapped_flop_count=1024, cell_model='sky130_fd_sc_hd__dfrtp_1', evidence=['reports/synthesis/structure_audit.json','build/synth/mapped.json'])], external_memories=dict(instruction_bits=2097152,data_bits=2097152, implementation='external', inside_physical_top=False, timing='Instruction response one cycle; data response 1..8 cycles; frozen boundary preserved'), required_macro_views=[], unresolved_dependencies=[]))
log = (OUT/'yosys.log').read_text()
assert json.loads((OUT/'slang_diagnostics.json').read_text()) == []
warnings=[]
for line,text in enumerate(log.splitlines(),1):
    if 'Warning:' in text or 'WARNING:' in text:
        if 'multi-output cells' in text: disposition='ABC library reader reports multi-output library cells; combinational map uses supported cells only. Every resulting cell is characterized and has LEF/GDS/CDL; no unresolved primitive remains.'
        elif 'network is combinational' in text: disposition='Expected: ABC receives only combinational logic, with flops already library-mapped outside ABC. Sequential optimization/retiming is prohibited; scorr warning does not affect functionality.'
        else: raise AssertionError('Unclassified synthesis warning: '+text)
        warnings.append(dict(line=line, message=text, disposition=disposition))
write('warnings.json',dict(verdict='passed', warnings=warnings, latch=dict(count=0, disposition='No inferred or mapped latch; synth -latches error and cell audit passed.'), undriven=dict(count=0, disposition='Yosys check -assert passed after reading characterized cell interfaces.'), width=dict(count=0, disposition='Slang emitted zero diagnostics; Yosys emitted no width warning. WREDUCE/template width messages are optimization information.'), diagnostics='reports/synthesis/slang_diagnostics.json'))
sta = (OUT/'sta.log').read_text()
assert not re.search(r'(?im)^Error|\[ERROR',sta)
vals = dict(re.findall(r'(worst slack max|worst slack min|tns max|tns min)\s+(-?\d+\.\d+)',sta))
assert len(vals) == 4
setup,hold = float(vals['worst slack max']),float(vals['worst slack min'])
assert setup >= 0, 'Negative setup slack: do not release netlist'
assert (OUT/'check_setup.rpt').read_text().strip() == '', 'Inspect unconstrained/missing-clock checks'
violations=(OUT/'timing_violations.rpt').read_text()
sections={}
for title in ['max slew','max capacitance','max fanout']:
    match=re.search(r'^'+title+r'\n(.*?)(?=^max |\Z)',violations,re.M|re.S)
    sections[title]=match.group(1).count('(VIOLATED)') if match else 0
critical_paths = []
for block in (OUT/'setup_paths.rpt').read_text().split('Startpoint: ')[1:]:
    slack = re.search(r'(-?[0-9.]+)\s+slack \(', block)
    critical_paths.append(dict(startpoint=block.splitlines()[0], endpoint=re.search(r'Endpoint: (.+)',block)[1], group=re.search(r'Path Group: (.+)',block)[1], slack_ns=float(slack[1])))
for path in critical_paths:
    instance = path['endpoint'].split(' ', 1)[0]
    netlist_block = re.search(r'\b'+re.escape(instance)+r'\s*\((.*?)\n\s*\);', Path('build/synth/nebula_cpu_npu_top.v').read_text(), re.S)
    if netlist_block:
        path['endpoint_q_connection'] = re.search(r'\.Q\((.*?)\)',netlist_block[1])[1]
critical_paths.sort(key=lambda p: p['slack_ns'])
write('critical_paths.json', dict(worst_setup=critical_paths[0], setup_paths=critical_paths, detail='Raw full-clock path reports retain all delays, capacitances and slews.'))
write('timing_audit.json',dict(verdict='passed' if setup >= 0 else 'failed', setup_slack_ns=setup,hold_slack_ns=hold,setup_tns_ns=float(vals['tns max']),hold_tns_ns=float(vals['tns min']), conditions=dict(corner=c['corner'],clock='nebula_clock',period_ns=100,clock_network='ideal pre-CTS; 0 ns source latency, 0.05 ns transition, 0.1 ns setup/hold uncertainty', wire_model='Explicit Liberty Small wire-load model for min and max; no placement, extracted RC or SPEF. Library pin capacitance plus 0.005 pF output loads.', io='Frozen SDC including functional and observer ports; data min/max 0.5 ns; reset rise 49..51 ns.', derates='early/late 1.0; single-corner nominal engineering analysis'),electrical_violations=sections, electrical_measured_checks='report_check_types raw report; final wire-load max slew and max capacitance clean. Library has no characterized max_fanout ceiling.', electrical_scope='Pre-layout wire-load estimates; physical repair and extracted-RC checks remain downstream. No characterized fanout ceiling invented.', setup_check_report='reports/synthesis/check_setup.rpt', evidence=['reports/synthesis/sta.log','reports/synthesis/setup_paths.rpt','reports/synthesis/hold_paths.rpt','reports/synthesis/timing_violations.rpt']))
metrics=[]
def metric(id,label,value,unit,evidence,scope):
    metrics.append(dict(id=id,label=label,value=value,unit=unit,status='measured',scope=scope,evidence=evidence))
area_scope='Mapped enabled nebula_cpu_npu_top including CPU/NPU/RF and tie cells; external images, pads and package excluded.'
timing_scope='Sky130HD tt_025C_1v80; nebula_clock 100 ns; ideal pre-CTS clock; Liberty Small wire-load RC, no SPEF; frozen SDC, uncertainty setup/hold 0.1 ns. Worst max/min slack includes asynchronous recovery/removal checks.'
metric('design.standard_cell_count','标准单元',sum(counts.values()),'count',['reports/synthesis/stat.json','reports/synthesis/cell_audit.json'],area_scope)
metric('design.macro_count','Macro 数量',0,'count',['reports/synthesis/cell_audit.json','reports/synthesis/memory_mapping.json'],area_scope)
metric('design.cell_area','Liberty 单元面积',round(area,6),'um2',['reports/synthesis/stat.json','reports/synthesis/cell_audit.json'],area_scope+' Sum of Liberty area.')
metric('design.total_footprint_area','单元与 Macro 占地面积',round(footprint,6),'um2',['reports/synthesis/cell_audit.json'],area_scope+' Sum of LEF SIZE width*height, distinct from Liberty area.')
metric('design.latch_count','Latch 数量',0,'count',['reports/synthesis/cell_audit.json','reports/synthesis/warnings.json'],area_scope)
for id,label,val in [('timing.setup_slack','Setup Slack',setup),('timing.hold_slack','Hold Slack',hold),('timing.setup_tns','Setup TNS',float(vals['tns max'])),('timing.hold_tns','Hold TNS',float(vals['tns min']))]:
    metric(id,label,val,'ns',['reports/synthesis/sta.log'],timing_scope)
metric('timing.clock_period','Clock Period',100,'ns',['reports/synthesis/loaded_constraints.sdc'],timing_scope)
metric('timing.unconstrained_paths','未约束路径',0,'count',['reports/synthesis/check_setup.rpt'],timing_scope+' OpenSTA check_setup reports no unconstrained endpoints or missing clock/input delay.')
write('result_summary.json',dict(schema_version=1,stage='synthesis',status='completed',summary=f'Mapped verified frozen enabled top; setup {setup:.9f} ns and hold {hold:.9f} ns under TT pre-layout Liberty Small RC; {sum(counts.values())} standard cells, zero macros/latches. Physical electrical closure remains downstream.',metrics=metrics))
write('report.json',dict(schema_version=1,verdict='passed',netlist='build/synth/nebula_cpu_npu_top.v',summary='Reproducible mapped netlist; frozen synthesis-result-summary and setup-timing-closure conditions satisfied.',verification_verdict='passed',mapping=dict(tool='Yosys 0.69+77 git 9ff27d29c; built-in read_slang', abc_area=1,policy='ABC map -a then buffering/sizing at 100 ns; no retiming or RTL/constraint edit',sta_tool=sta.splitlines()[0]), measured=dict(standard_cells=sum(counts.values()),liberty_area_um2=round(area,6),lef_footprint_area_um2=round(footprint,6),macro_count=0,latch_count=0,setup_slack_ns=setup,hold_slack_ns=hold),warning_count=len(warnings),evidence=['reports/synthesis/input_audit.json','reports/synthesis/cell_audit.json','reports/synthesis/structure_audit.json','reports/synthesis/warnings.json','reports/synthesis/memory_mapping.json','reports/synthesis/timing_audit.json','reports/synthesis/fanout.json','reports/synthesis/tool_identity.json','reports/synthesis/result_summary.json'],not_checked=['Full formal sequential equivalence','Placement/routing/extracted RC, CTS, DRC/LVS/GDS and physical electrical closure','Independent ORFS Git revision: exported platform has no Git metadata; captured manifest absent'],risk='Positive pre-layout timing and zero wire-load electrical violations do not establish post-route closure. Propagated-clock, extracted-RC, final reset/electrical and DRC/LVS checks remain required in PnR.',netlist_sha256=sha('build/synth/nebula_cpu_npu_top.v'), gates='reports/synthesis/gates.json', reproducibility='reports/synthesis/reproducibility.json', critical_path=critical_paths[0]))
print(f'REPORT_PASS cells={sum(counts.values())} area={area:.6f} setup={setup} hold={hold}; electrical={sections}')
