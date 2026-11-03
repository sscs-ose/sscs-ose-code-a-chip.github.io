"""Independently compare complete images and measure source/functional coverage."""
import copy
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
FIXED = ROOT/'.nebula_inputs/authorized-common-verifier-resources/verification/fixed_common'
EVAL = FIXED/'verification/benchmark/evaluator'
OUT = ROOT/'reports/verification'
sys.path.insert(0, str(EVAL))
from elf_image import load_elf
from sail_commit import compare_commits
from score_run import load_rules, score_functional

def digest(data):
    return hashlib.sha256(data).hexdigest()

def image(path):
    # Both fixed loader and Verilator dumps use complete sequential byte images.
    data = bytes.fromhex(Path(path).read_text())
    assert len(data) == 256*1024, (path, len(data))
    return data

index = {}
for directory, key in [(EVAL/'act4_elfs', 'act'),
        (EVAL/'t09_data/programs/directed','directed'), (EVAL/'t09_data/programs/random','random')]:
    oracle_dir = EVAL/'t09_data/oracles/act4' if key == 'act' else directory
    manifest = json.loads((oracle_dir/'MANIFEST.json').read_text())
    for row in manifest.get('oracles', manifest.get('cases')):
        elf = directory/row.get('elf_path', row.get('elf'))
        data = bytes(load_elf(elf))
        with gzip.open(oracle_dir/row.get('oracle_path', row.get('oracle')), 'rt') as f:
            oracle = [json.loads(line) for line in f]
        index[digest(data)] = (key, str(elf.relative_to(ROOT)), oracle)
kernel_dir = ROOT/'build/perf/kernels-observed'
if not kernel_dir.exists():kernel_dir = ROOT/'build/perf/kernels'
for p in kernel_dir.glob('*/memory.hex'):
    oracle = [json.loads(line) for line in (p.parent/'reference.jsonl').read_text().splitlines()]
    index[digest(image(p))] = ('workload',str(p.parent.relative_to(ROOT)),oracle)
spec_manifest = json.loads((EVAL/'t09_data/programs/spec/MANIFEST.json').read_text())
for row in spec_manifest['cases']:
    elf = EVAL/'t09_data/programs/spec'/row['elf']
    source = (elf.parent/row['source']).read_text()
    assert source.count('sw s1,0(s0)') == 1 and source.count('sw a0, 0(a1)') == 2
    assert 'la t2,after_fault' in source and 'csrw mepc,t2' in source
    index[digest(bytes(load_elf(elf)))] = ('spec',str(elf.relative_to(ROOT)),None)

names = {
    0x37:'LUI',0x17:'AUIPC',0x6f:'JAL',0x67:'JALR',0x0f:'FENCE',0x0b:'XDOT4'}
reg_names = {0:'ADD',1:'SLL',2:'SLT',3:'SLTU',4:'XOR',5:'SRL',6:'OR',7:'AND'}
imm_names = {0:'ADDI',1:'SLLI',2:'SLTI',3:'SLTIU',4:'XORI',5:'SRLI',6:'ORI',7:'ANDI'}
load_names = {0:'LB',1:'LH',2:'LW',4:'LBU',5:'LHU'}
store_names = {0:'SB',1:'SH',2:'SW'}
branch_names = {0:'BEQ',1:'BNE',4:'BLT',5:'BGE',6:'BLTU',7:'BGEU'}
csr_names = {1:'CSRRW',2:'CSRRS',3:'CSRRC',5:'CSRRWI',6:'CSRRSI',7:'CSRRCI'}
def family(insn):
    op, f3 = insn & 127, (insn >> 12) & 7
    if op == 0x33:
        return 'SUB' if f3 == 0 and insn >> 25 == 32 else 'SRA' if f3 == 5 and insn >> 25 == 32 else reg_names[f3]
    if op == 0x13:
        return 'SRAI' if f3 == 5 and insn >> 25 == 32 else imm_names[f3]
    if op == 3:return load_names[f3]
    if op == 0x23:return store_names[f3]
    if op == 0x63:return branch_names[f3]
    if op == 0x73:
        return csr_names[f3] if f3 else {0x73:'ECALL',0x100073:'EBREAK',0x30200073:'MRET'}[insn]
    return names[op]

assert family(0x00100093) == 'ADDI' and family(0x40005033) == 'SRA'
supported = set(names.values()) | set(reg_names.values()) | {'SUB','SRA'} | set(imm_names.values()) | {'SRAI'} | set(load_names.values()) | set(store_names.values()) | set(branch_names.values()) | set(csr_names.values()) | {'ECALL','EBREAK','MRET'}
bins = {'instruction:'+s for s in supported}
bins |= {'branch:'+s+':'+d for s in branch_names.values() for d in ['taken','not_taken']}
bins |= {'lane:'+s+':'+str(l) for s in [*load_names.values(),*store_names.values()]
         for l in (range(4) if s in ['LB','LBU','SB'] else [0,2] if s in ['LH','LHU','SH'] else [0])}
hits = Counter()
records = []
objects = OUT/'memory-objects'
objects.mkdir(exist_ok=True)
def save_image(data):
    name = digest(data)+'.bin.gz'
    path = objects/name
    if not path.exists():
        with gzip.open(path,'wb') as f:f.write(data)
    return str(path.relative_to(ROOT))

for p in sorted((ROOT/'build/verify/capture').glob('*.json')):
    rec = json.loads(p.read_text())
    if not rec.get('final_memory') or not rec.get('initial_memory'):
        continue
    initial, final = image(rec['initial_memory']), image(rec['final_memory'])
    assert initial == image(rec['image']), p
    key = digest(initial)
    assert key in index, (p,key)
    label, source, oracle = index[key]
    actual = [json.loads(line) for line in Path(rec['trace']).read_text().splitlines()]
    if oracle is not None:
        comparison = compare_commits(oracle, actual)
        assert comparison['passed'], (source,comparison)
    expected = bytearray(initial)
    if label == 'spec':
        # These four immutable programs skip their only RAM store on the trap/MRET
        # PASS path. Both tohost stores are MMIO: expected final RAM equals initial.
        assert not any(e.get('mem_wstrb') and e['mem_addr'] != 0x8003f000 for e in actual)
    for event in oracle if oracle is not None else []:
        if event.get('kind','commit') != 'commit' or not event.get('mem_wstrb') or event['mem_addr'] == 0x8003f000:
            continue
        offset = event['mem_addr']-0x80000000
        assert 0 <= offset <= len(expected)-4
        for lane in range(4):
            if event['mem_wstrb'] & (1<<lane):expected[offset+lane] = (event['mem_wdata']>>(8*lane)) & 255
    assert final == expected, (source,p)
    normal = sum(e['kind']=='commit' for e in actual)
    records.append({'receipt':str(p.relative_to(ROOT)),'configuration':rec['configuration'],
                    'group':label,'source':source,'passed':True,'bytes_compared':len(initial),
                    'normal_retirements':normal,'expected_independent':True,
                    'initial':save_image(initial),'actual_final':save_image(final),
                    'expected_final':save_image(expected)})
    regs = [0]*32
    for e in actual:
        if e['kind'] == 'trap':
            if e['cause'] == 11:hits['instruction:ECALL'] += 1
            if e['cause'] == 3:hits['instruction:EBREAK'] += 1
            continue
        insn = e['insn'];f = family(insn)
        hits['instruction:'+f] += 1
        rs1,rs2 = (insn>>15)&31,(insn>>20)&31
        if f in load_names.values() or f in store_names.values():
            immediate = (insn>>20) if f in load_names.values() else ((insn>>25)<<5)|((insn>>7)&31)
            immediate -= 4096 if immediate & 2048 else 0
            hits['lane:'+f+':'+str((regs[rs1]+immediate)&3)] += 1
        if f in branch_names.values():
            a,b=regs[rs1],regs[rs2];sa=a-2**32 if a&2**31 else a;sb=b-2**32 if b&2**31 else b
            taken = {'BEQ':a==b,'BNE':a!=b,'BLT':sa<sb,'BGE':sa>=sb,'BLTU':a<b,'BGEU':a>=b}[f]
            hits['branch:'+f+':'+('taken' if taken else 'not_taken')] += 1
        if e['rd']:regs[e['rd']] = e['wdata']
    assert regs[0] == 0

assert len(records) >= 703, len(records)
(OUT/'memory-comparison.json').write_text(json.dumps({'passed':True,'scope':'two core configurations and enabled-top workload replays; all 262144 bytes before and after each run',
    'runs':len(records),'independent_oracle_runs':sum(r['expected_independent'] for r in records),
    'spec_scope_note':'Four immutable spec programs per core skip their only RAM write on the fixed trap/MRET PASS path; their independent expected final RAM equals the full initial image.',
    'records':records},indent=2)+'\n')

points = {}
coverage_sources = []
for p in sorted((ROOT/'build/verify/capture').glob('*.coverage.dat')):
    receipt = p.with_name(p.name.replace('.coverage.dat','.json'))
    if not receipt.exists():continue
    rec = json.loads(receipt.read_text())
    if rec.get('returncode') != 0:continue
    if 'tb_cpu_elf' in rec['command'] and not rec.get('final_memory'):continue
    coverage_sources.append(str(p.relative_to(ROOT)))
    for line in p.read_text().splitlines():
        if not line.startswith('C '):continue
        encoded, count = line[3:].rsplit("' ",1)
        attrs = dict(s.split('\x02',1) for s in encoded.split('\x01')[1:])
        if '/candidate/rtl/' not in attrs['f'] and '/rtl/' not in attrs['f']:continue
        file = attrs['f'].split('/rtl/',1)[1]
        key = (file,attrs.get('l'),attrs.get('n'),attrs.get('t'),attrs.get('o'),attrs.get('S'))
        points[key] = points.get(key,0)+int(count)
measures = {}
for kind in ['line','branch','toggle']:
    selected = {k:v for k,v in points.items() if k[3] == kind}
    assert selected
    numerator = sum(v>0 for v in selected.values());denominator=len(selected)
    measures[kind] = {'numerator':numerator,'denominator':denominator,'percent':100*numerator/denominator,
                     'scope':'union of unique Verilator 5.048 instrumented DUT source points across both core configurations and enabled physical-top RTL; testbench excluded'}
measures['functional'] = {'numerator':sum(hits[b]>0 for b in bins),'denominator':len(bins),
                          'percent':100*sum(hits[b]>0 for b in bins)/len(bins),
                          'scope':'48 supported instruction families, 12 branch outcomes and 20 legal load/store lanes; actual qualified retirement/trap observations; no numerical threshold'}
coverage = {'measures':measures,'functional_bins':[{'name':b,'hits':hits[b]} for b in sorted(bins)],
            'source_points':[{'source':k[0],'line':k[1],'column':k[2],'kind':k[3],'object':k[4],'lines':k[5],'hits':v} for k,v in sorted(points.items(),key=str)],
            'raw_coverage_sources':coverage_sources,
            'line_definition':'Verilator line instrumentation point coverage, not uninstrumented text-line percentage; branch and toggle reported separately.'}
(OUT/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')

results = []
for c in ['base','enabled']:
    path = ROOT/f'build/verify/regression/t09-{c}-observed.json'
    if not path.exists():path = ROOT/f'build/verify/regression/t09-{c}.json'
    results.append(json.loads(path.read_text()))
rules = load_rules()
assert all(r['score']['full_functional_pass'] for r in results)
boundaries = []
for good,want in [(0,0),(10,0),(11,5),(21,5),(22,10)]:
    groups=copy.deepcopy(results[0]['groups']);groups['CPU-PIPE-CYCLES']['cases_passed']=good
    _,_,items=score_functional('T09',groups,rules)
    got=next(i['points'] for i in items if i['id']=='P_CYCLES')
    assert abs(got-want)<1e-9,(good,got)
    boundaries.append({'passed_checks':good,'normalized_cycle_points':want})
groups=copy.deepcopy(results[0]['groups']);groups['CPU-PIPE-CYCLES']['safety_violation']=True
_,_,items=score_functional('T09',groups,rules)
assert next(i['points'] for i in items if i['id']=='P_CYCLES') == 0
exact=sum(Fraction(str(i['points'])) for i in rules['tasks']['T09'])*Fraction(50,75)
assert exact == 50
(OUT/'scoring.json').write_text(json.dumps({'policy':'t09_group_cycles10_v1','raw_F':48,'raw_P':27,
    'raw_total':75,'normalization':'50/75','exact_full_score':str(exact),'passed':True,
    'boundary_selfcheck':boundaries,'safety_selfcheck':'one affected item zeroed once',
    'time_eligible':False,'ppa_eligible':False,
    'eligibility_reason':'project delivery and independent evaluator release outstanding; complete workflow time receipt absent; no physical measurements',
    'historical_ACT4_attachment_weight':10,'approved_ACT4_weight':8},indent=2)+'\n')
print(json.dumps({'memory_runs':len(records),'coverage':measures},indent=2))
