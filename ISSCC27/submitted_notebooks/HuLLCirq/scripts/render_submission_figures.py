"""Derive submitted figures from saved inputs and VCD; never execute a DUT.

Use --check for read-only verification, or --write to refresh only the derived
presentation files. Python standard library only; no model, network or EDA.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'submission/presentation'
NPU = 'submission/evidence/npu_explicit/'
COUNTER = 'submission/evidence/p1_counter/'


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def pin(relative):
    return {'path': relative, 'sha256': hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}


def signed32(value):
    return ((int(value) + (1 << 31)) % (1 << 32)) - (1 << 31)


def worked_example():
    design = load(NPU + 'design-inputs.json')
    job = design['verification_jobs'][0]
    actual = load(NPU + 'S14/functional-report.json')['outputs']
    assert job['k'] == 3 and job['relu'] is False
    raw, outputs, products = [], [], []
    for row in range(2):
        for col in range(2):
            terms = [job['A'][row][k] * job['B'][k][col] for k in range(job['k'])]
            mac = signed32(sum(terms))
            value = signed32(mac + job['bias'][col])
            value = max(0, value) if job['relu'] else value
            raw.append(mac)
            outputs.append(value)
            products.append({'row': row, 'column': col, 'products': terms,
                             'mac': mac, 'bias': job['bias'][col], 'result': value})
    assert outputs == [r['value'] for r in actual] == [-44, 56, 59, 9]
    roles = {
        'control': 'Latch one job; distribute independent scheduler/post configuration; complete only after four external transfers.',
        'buffer': 'Two banks of 16 byte registers; produce A0k, A1k, Bk0, Bk1 in one 32-bit response.',
        'scheduler': 'For each k request one bundle, then send one 34-bit bundle with first/last markers.',
        'dispatcher': 'Deliver four independent 18-bit pairs exactly once per operand batch.',
        'collector': 'Serialize the four final sums in row-major 00,01,10,11 order.',
        'post': 'Add the signed32 column bias with wrap, then optionally apply ReLU.',
        'fifo': 'Depth-two signed32 output queue; report actual external valid-and-ready transfers.',
    }
    nodes = []
    for node in design['nodes']:
        suffix = node['id'].removeprefix('npu2-')
        role = ('Output-stationary signed8 x signed8 MAC with signed32 wrap; one final sum per K transfers.'
                if suffix.startswith('pe') else roles[suffix])
        nodes.append({'id': node['id'], 'name': node['name'], 'module_name': node['module_name'],
                      'role': role, 'ports': [{k: p[k] for k in ['name', 'direction', 'width', 'signed']}
                                             for p in node['ports']]})
    by_id = {n['id']: n for n in design['nodes']}
    edges = []
    for edge in design['edges']:
        source = edge['source']
        port = next(p for p in by_id[source['node_id']]['ports'] if p['id'] == source['port_id'])
        edges.append({'id': edge['id'], 'source': source, 'target': edge['target'],
                      'payload_width': port['width'], 'protocol': edge['protocol']})
    return {'schema_version': 1, 'source': pin(NPU + 'design-inputs.json'),
            'functional_report_source': pin(NPU + 'S14/functional-report.json'),
            'settings': design['settings'],
            'job': {k: job[k] for k in ['id', 'k', 'A', 'B', 'bias', 'relu']},
            'arithmetic': {'operand_bits': 8, 'signed_product_bits': 16, 'accumulator_bits': 32,
                           'wrap': 'signed32 modulo 2^32 before optional ReLU', 'raw_mac': raw,
                           'after_bias_wrap': outputs, 'expected_outputs': outputs,
                           'products_by_output': products},
            'functional_observations': actual, 'nodes': nodes, 'edges': edges,
            'limits': ['Independent arithmetic is recomputed from the original input matrices, not from DUT output.',
                       'The 50 ns clock is the unchanged saved target; no frequency-optimality claim is made.',
                       'Original request preparation fields retain historical pending text; the separate source-bound execution report determines the recorded result.',
                       'This logical graph is not a physical floorplan, throughput comparison, exhaustive proof or new circuit execution.']}


def parse_vcd(text, aliases):
    """Parse the bounded scalar/binary four-state traces used by these fixtures."""
    scale = re.search(r'\$timescale\s+(1|10|100)\s*(s|ms|us|ns|ps|fs)\s+\$end', text)
    assert scale and '$enddefinitions' in text
    factor = int(scale[1]) * {'s': 1e9, 'ms': 1e6, 'us': 1e3, 'ns': 1, 'ps': .001, 'fs': .000001}[scale[2]]
    header, body = text.split('$enddefinitions', 1)
    body = body.split('$end', 1)[1]
    signals, by_code = [], {}
    for match in re.finditer(r'\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+(.*?)\s+\$end', header):
        original = match[4].split()[0]
        row = {'name': aliases.get(original, original), 'original': original,
               'width': int(match[2]), 'events': []}
        signals.append(row)
        by_code.setdefault(match[3], []).append(row)
    tokens, i, now, end = body.split(), 0, 0, 0
    while i < len(tokens):
        token = tokens[i]
        i += 1
        if token.startswith('#'):
            time = int(token[1:]) * factor
            assert time >= now
            now, end = time, max(end, time)
            continue
        if token.startswith('$'):
            if token not in ['$end', '$dumpvars', '$dumpall', '$dumpon', '$dumpoff']:
                while i < len(tokens) and tokens[i] != '$end':
                    i += 1
            continue
        if token.startswith(('b', 'B')):
            bits, code = token[1:], tokens[i]
            i += 1
        else:
            assert token[0] in '01xXzZ'
            bits, code = token[0], token[1:]
        assert re.fullmatch('[01xz]+', bits, re.I) and code in by_code
        for row in by_code[code]:
            assert len(bits) <= row['width']
            value = bits.upper() if re.search('[xz]', bits, re.I) else str(int(bits, 2))
            if row['events'] and row['events'][-1]['time_ns'] == now:
                row['events'].pop()
            row['events'].append({'time_ns': now, 'value': value})
    assert signals and len(signals) <= 256
    return signals, end


def waveform_summary():
    plan_path = COUNTER + 'S14/verification-plan.json'
    vector_path = COUNTER + 'S14/public-vectors.json'
    plan, vectors = load(plan_path), load(vector_path)
    ports = plan['interface']['ports']
    aliases = {'hc_p' + str(i): p['name'] for i, p in enumerate(ports)}
    timing = plan['stimulus_timing']
    period, half, offset = [timing[k] / 1000 for k in ['period_ps', 'half_period_ps', 'sample_after_rising_ps']]
    assert (period, half, offset) == (50, 25, 1)
    stages = []
    cases = [('S06', 'S06/workflow-c49be00c5ece413c9fd39023d9ce0e4f/', 'recorded_job_tb.v', 'Generic node-netlist simulation; zero delay; no PDK/SDF'),
             ('S10', 'S10/global-workflow-3d60b699a8c449f9acaf7889b6a0a2b9/', 'recorded_job_tb.v', 'Generic global-netlist simulation; zero delay; no PDK/SDF'),
             ('S14', 'S14/', 'functional-testbench.v', 'Routed-netlist functional simulation; original PDK functional models; no SDF')]
    for stage, folder, tb_name, kind in cases:
        vcd_path, tb_path = COUNTER + folder + 'simulation.vcd', COUNTER + folder + tb_name
        tb = (ROOT / tb_path).read_text(encoding='utf-8')
        actual_aliases = {m[2]: m[1] for m in re.finditer(r'\.(\w+)\s*\((hc_p\d+)\)', tb)}
        assert actual_aliases == aliases, 'Signal aliases must match the retained testbench.'
        signals, end = parse_vcd((ROOT / vcd_path).read_text(encoding='ascii'), aliases)
        by_name = {r['name']: r for r in signals}
        samples, missing, mismatches = [], 0, []
        for cycle, vector in enumerate(vectors):
            time = cycle * period + half + offset
            for name, expected in vector['expect'].items():
                seen = [e['value'] for e in by_name[name]['events'] if e['time_ns'] <= time] if time <= end else []
                observed = seen[-1] if seen else None
                if observed is None:
                    missing += 1
                match = observed == str(expected)
                sample = {'cycle': cycle, 'time_ns': time, 'signal': name,
                          'expected': str(expected), 'observed': observed, 'match': match}
                samples.append(sample)
                if not match and observed is not None:
                    mismatches.append(sample)
        assert missing == 0 and not mismatches and len(samples) == 42
        stages.append({'stage': stage, 'source': pin(vcd_path), 'testbench': pin(tb_path),
                       'observed_kind': kind, 'comparisons': len(samples) - missing,
                       'mismatches': mismatches, 'missing': missing, 'samples': samples,
                       'signals': signals, 'end_ns': end})
    return {'schema_version': 1, 'interface_source': pin(plan_path), 'vectors_source': pin(vector_path),
            'interface': plan['interface'], 'vectors': vectors,
            'timing': {'period_ns': period, 'half_ns': half, 'sample_after_rising_ns': offset},
            'stages': stages,
            'limits': ['Saved VCD observations are parsed again; no model, DUT, simulator or EDA is executed.',
                       'Expected markers come from the independent saved cycle contract; unknown values are not fabricated.',
                       'Same-timestamp values are presented as their final VCD value, not as delta-cycle or SDF timing proof.']}


def svg_begin(width, height, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            '<title>' + html.escape(title) + '</title>',
            '<style>text{font-family:Arial,sans-serif;fill:#132d4f} .title{font-size:25px;font-weight:700}.small{font-size:13px}.tiny{font-size:11px}.node{fill:#f1f6fc;stroke:#285987;stroke-width:2}.pe{fill:#e8f7f2;stroke:#087760;stroke-width:2}.wire{fill:none;stroke:#285987;stroke-width:2.5;marker-end:url(#arrow)}.control{stroke:#a36a14;stroke-dasharray:6 4}.label{font-size:14px;font-weight:700}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10z" fill="#285987"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="white"/>']


def text(svg, x, y, value, css='small', extra=''):
    svg.append(f'<text x="{x}" y="{y}" class="{css}" {extra}>{html.escape(str(value))}</text>')


def architecture_svg(worked):
    svg = svg_begin(1320, 960, 'Eleven-node explicit 2x2 NPU: saved logical architecture')
    text(svg, 35, 40, 'Eleven-node explicit 2x2 NPU', 'title')
    text(svg, 35, 66, 'Logical graph from the original saved specification. Boxes/grouping are not physical placement.')
    def box(x, y, w, h, title, lines, pe=False):
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{"pe" if pe else "node"}"/>')
        text(svg, x+14, y+27, title, 'label')
        for n, line in enumerate(lines):text(svg, x+14, y+52+n*19, line)
    def arrow(path):svg.append('<path class="wire" d="' + path + '"/>')
    box(60,180,235,125,'Operand buffer',['2 x 16-byte register banks','A0k,A1k,Bk0,Bk1 response','No SRAM macro is claimed'])
    box(390,180,235,125,'2x2 scheduler',['Iterate k = 0..K-1','First/last markers per batch','Exactly K accepted batches'])
    box(720,180,235,125,'Four-lane dispatcher',['Independent delivered flags','One transfer per PE per k','Hold stable under stalls'])
    box(1040,180,235,125,'Job control',['Accept one legal config','Independent config channels','Count 4 external transfers'])
    text(svg, 65, 145, 'External load: 13-bit address/bank/byte')
    arrow('M177 150 L177 178')
    text(svg, 1040, 145, 'External config: 69 bits')
    arrow('M1157 150 L1157 178')
    arrow('M295 220 L388 220');text(svg, 303, 210, '32-bit reply', 'tiny')
    arrow('M390 275 L297 275');text(svg, 300, 266, '3-bit index', 'tiny')
    arrow('M625 242 L718 242');text(svg, 633, 232, '34-bit batch', 'tiny')
    svg.append('<path class="wire control" d="M1080 180 L1080 110 L507 110 L507 178"/>')
    text(svg, 635, 101, '4-bit K configuration; independent valid/ready')
    svg.append('<rect x="705" y="395" width="570" height="280" rx="14" fill="#fafdfb" stroke="#80bcae" stroke-dasharray="6 4"/>')
    text(svg, 725, 420, 'Four explicit PE nodes (logical 2x2 grouping)', 'label')
    box(730,440,245,95,'PE 00: C[0,0]',['signed8 x signed8 -> 16','signed32 MAC accumulator'],True)
    box(1005,440,245,95,'PE 01: C[0,1]',['signed8 x signed8 -> 16','signed32 MAC accumulator'],True)
    box(730,555,245,95,'PE 10: C[1,0]',['signed8 x signed8 -> 16','signed32 MAC accumulator'],True)
    box(1005,555,245,95,'PE 11: C[1,1]',['signed8 x signed8 -> 16','signed32 MAC accumulator'],True)
    arrow('M837 305 L837 350 L990 350 L990 392')
    text(svg, 450, 335, '4 independent 18-bit pairs')
    text(svg, 450, 356, 'a[7:0], b[7:0], first, last')
    box(390,485,235,130,'Row-major collector',['Select 00, 01, 10, 11','Only chosen lane gets ready','Advance on actual transfer'])
    arrow('M705 550 L627 550');text(svg, 638, 500, '4 x 32-bit', 'tiny');text(svg, 638, 516, 'independent', 'tiny');text(svg, 638, 532, 'sum streams', 'tiny')
    box(60,485,235,130,'Bias and ReLU',['signed32 column-bias add','Wrap modulo 2^32','Optional ReLU after wrap'])
    arrow('M390 550 L297 550');text(svg, 313, 538, '32 bits', 'tiny')
    box(60,735,235,105,'Output FIFO',['Depth 2, signed32','Maintain row-major order'])
    arrow('M177 615 L177 733');text(svg, 190, 680, '32-bit result')
    arrow('M295 785 L600 785');text(svg, 315, 772, 'External output: signed32 + valid/ready')
    text(svg, 35, 880, 'Other saved control edges: Job control -> Bias/ReLU (65 bits); FIFO -> Job control (1-bit output_transfer pulse).')
    text(svg, 35, 902, 'All blue payload arrows use valid/ready; PE fanout/collection arrows group four independent channels, not one shared wire.')
    text(svg, 35, 924, 'Shared clk/rst: 50 ns target, synchronous active-high reset. No all-ready broadcast or systolic propagation is implied.')
    svg.append('</svg>')
    return '\n'.join(svg)+'\n'


def waveform_svg(summary, stage):
    svg = svg_begin(1320, 610, 'Counter '+stage['stage']+' saved VCD and independent expected samples')
    text(svg, 30, 35, 'Counter '+stage['stage']+' — measured saved VCD', 'title')
    text(svg, 30, 60, stage['observed_kind'])
    text(svg, 30, 82, 'Green dots: independent expected samples match observed VCD (42/42). Orange dashes: t = 26 + 50 x cycle ns.')
    left, width, top, step = 205, 1080, 145, 47
    xmax = 700
    px=lambda t:left+width*t/xmax
    ports=summary['interface']['ports']
    by_name={r['name']:r for r in stage['signals']}
    for cycle in range(15):
        x=px(cycle*50)
        svg.append(f'<path d="M{x:.2f} 125 V{top+8*step}" stroke="#d6e0ed"/>')
        text(svg,x-5,120,cycle*50,'tiny')
        if cycle<14:
            sample=px(cycle*50+26)
            svg.append(f'<path d="M{sample:.2f} 130 V{top+8*step}" stroke="#e0b46d" stroke-dasharray="2 5"/>')
    text(svg, 1220, 103, 'time / ns', 'tiny')
    for cycle in [0,9]:
        svg.append(f'<rect x="{px(cycle*50):.2f}" y="130" width="{width/14:.2f}" height="{8*step}" fill="#fff4cf" opacity="0.4"/>')
    for row_number, port in enumerate(ports):
        y=top+row_number*step
        row=by_name[port['name']]
        text(svg, 25, y+19, port['name'], 'label')
        text(svg, 25, y+35, str(port['width'])+' bit · VCD observed', 'tiny')
        events=row['events']
        scalar=port['width']==1
        for n,event in enumerate(events):
            start=max(0,event['time_ns']);end=events[n+1]['time_ns'] if n+1<len(events) else xmax
            end=min(end,xmax)
            if end<=start:continue
            a,b=px(start),px(end);value=event['value']
            if scalar and value in ['0','1']:
                level=y+(25 if value=='0' else 6)
                svg.append(f'<path d="M{a:.2f} {level} H{b:.2f}" stroke="#236b8e" fill="none" stroke-width="2"/>')
                if n and events[n-1]['value']!=value:
                    svg.append(f'<path d="M{a:.2f} {y+6} V{y+25}" stroke="#236b8e"/>')
            else:
                unknown=bool(re.search('[XZ]',value))
                svg.append(f'<rect x="{a:.2f}" y="{y+3}" width="{b-a:.2f}" height="26" fill="{"#fde3df" if unknown else "#e7f0fa"}" stroke="#5986ad"/>')
                if b-a>19:text(svg,(a+b)/2,y+21,value,'tiny','text-anchor="middle"')
        for sample in stage['samples']:
            if sample['signal']==port['name']:
                x=px(sample['time_ns'])
                svg.append(f'<circle cx="{x:.2f}" cy="{y+35}" r="3" fill="#118765"><title>cycle {sample["cycle"]}: expected {sample["expected"]}, observed {sample["observed"]}</title></circle>')
        svg.append(f'<path d="M{left} {y+43} H{left+width}" stroke="#edf1f6"/>')
    text(svg,30,550,'Original contract: 14 cycles, 50 ns period; reset at cycles 0 and 9; compare 1 ns after each rising edge.')
    text(svg,30,571,'This plot re-reads retained transitions; it is not a new simulator run or dynamic SDF timing qualification.')
    text(svg,30,592,'VCD SHA-256: '+stage['source']['sha256'],'tiny')
    svg.append('</svg>')
    return '\n'.join(svg)+'\n'


def generated():
    worked, waves = worked_example(), waveform_summary()
    result={'npu_worked_example.json':json.dumps(worked,ensure_ascii=False,indent=2)+'\n',
            'waveform_summary.json':json.dumps(waves,ensure_ascii=False,indent=2)+'\n',
            'npu_architecture.svg':architecture_svg(worked)}
    for stage in waves['stages']:
        result['counter_'+stage['stage'].lower()+'_waveform.svg']=waveform_svg(waves,stage)
    return result, worked, waves


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--write',action='store_true')
    args=parser.parse_args()
    files,worked,waves=generated()
    if args.write:
        OUT.mkdir(parents=True,exist_ok=True)
        for name,data in files.items():(OUT/name).write_text(data,encoding='utf-8',newline='\n')
    else:
        for name,data in files.items():
            if (OUT/name).read_bytes()!=data.encode('utf-8'):raise SystemExit('Derived presentation mismatch: '+name)
    print(json.dumps({'mode':'write' if args.write else 'read_only_check','derived_files':len(files),
                      'arithmetic_outputs':worked['arithmetic']['expected_outputs'],
                      'waveform_checks':[{'stage':s['stage'],'comparisons':s['comparisons'],'mismatches':len(s['mismatches']),'missing':s['missing']} for s in waves['stages']],
                      'model_or_eda_started':False},indent=2))


if __name__=='__main__':main()
