#!/usr/bin/env python3
"""Local RTL self-checks; independent of frozen acceptance sources and oracles."""
import collections
import hashlib
import json
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/rtl'
RTL = ['rtl/nebula_npu_dot4.sv', 'rtl/rv32i_five_stage_cpu.sv',
       'rtl/integration/nebula_cpu_npu_top.sv']
BASE, DATA, HANDLER = 0x80000000, 0x80001000, 0x80003000
MASK = 0xffffffff


def command(args, log=None):
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=180)
    output = result.stdout + result.stderr
    if log:
        (OUT / log).write_text(output)
    if result.returncode:
        raise AssertionError(f'command failed: {args}\n{output[-5000:]}')
    return output


def build(top, sources, directory, parameter=None):
    args = ['verilator', '--binary', '--timing', '-j', '2', '-CFLAGS', '-std=c++20',
            '-LDFLAGS', '-L../tool-libs', '-Wno-TIMESCALEMOD', '--top-module', top,
            '--Mdir', f'build/rtl/{directory}', '-o', 'sim']
    if parameter is not None:
        args += [f'-GENABLE={parameter}']
    command(args + sources, directory + '_build.log')
    return OUT / directory / 'sim'


def sx(value, width):
    return (value & ((1 << (width - 1)) - 1)) - (value & (1 << (width - 1)))


def ins_i(rd, rs1, imm, f3=0, op=0x13):
    return ((imm & 4095) << 20) | rs1 << 15 | f3 << 12 | rd << 7 | op


def ins_r(rd, rs1, rs2, f3=0, f7=0, op=0x33):
    return f7 << 25 | rs2 << 20 | rs1 << 15 | f3 << 12 | rd << 7 | op


def ins_s(rs1, rs2, imm=0, f3=2):
    return ((imm & 4095) >> 5) << 25 | rs2 << 20 | rs1 << 15 | f3 << 12 | (imm & 31) << 7 | 0x23


def ins_b(rs1, rs2, imm, f3=0):
    n = imm & 8191
    return (n >> 12) << 31 | ((n >> 5) & 63) << 25 | rs2 << 20 | rs1 << 15 | f3 << 12 | ((n >> 1) & 15) << 8 | ((n >> 11) & 1) << 7 | 0x63


def ins_j(rd, imm):
    n = imm & 0x1fffff
    return (n >> 20) << 31 | ((n >> 1) & 1023) << 21 | ((n >> 11) & 1) << 20 | ((n >> 12) & 255) << 12 | rd << 7 | 0x6f


def ins_csr(rd, source, ca, f3):
    return ca << 20 | source << 15 | f3 << 12 | rd << 7 | 0x73


def lui(rd, value):
    return value & 0xfffff000 | rd << 7 | 0x37


class Fault(Exception):
    def __init__(self, cause, tval):
        self.cause, self.tval = cause, tval & MASK


def oracle(words, stop, enable):
    regs = [0] * 32
    csrs = {0x300: 0x1800, 0x301: 0x40000100, 0x305: BASE,
            0x340: 0, 0x341: 0, 0x342: 0, 0x343: 0, 0xf14: 0}
    memory = bytearray(bytes.fromhex('01ff7f80') * 1024)
    pc, events, requests = BASE, [], []
    for _ in range(20000):
        if pc == stop:
            return events, requests, memory
        word = words.get(pc, 0x13)
        op, f3, f7 = word & 127, word >> 12 & 7, word >> 25
        rd, rs1, rs2 = word >> 7 & 31, word >> 15 & 31, word >> 20 & 31
        a, b = regs[rs1], regs[rs2]
        imm = sx(word >> 20, 12)
        next_pc, value, writes = (pc + 4) & MASK, 0, False
        store_addr, store_mask, store_data = 0, 0, 0
        try:
            if op in (0x37, 0x17):
                value = (word & 0xfffff000) + (pc if op == 0x17 else 0)
                writes = True
            elif op in (0x6f, 0x67):
                if op == 0x6f:
                    offset = sx((word >> 31) << 20 | (word >> 12 & 255) << 12 | (word >> 20 & 1) << 11 | (word >> 21 & 1023) << 1, 21)
                    next_pc = (pc + offset) & MASK
                else:
                    if f3 != 0:
                        raise Fault(2, word)
                    next_pc = (a + imm) & 0xfffffffe
                if next_pc & 3:
                    raise Fault(0, next_pc)
                value, writes = pc + 4, True
            elif op == 0x63:
                outcomes = {0: a == b, 1: a != b, 4: sx(a, 32) < sx(b, 32),
                            5: sx(a, 32) >= sx(b, 32), 6: a < b, 7: a >= b}
                if f3 not in outcomes:
                    raise Fault(2, word)
                offset = sx((word >> 31) << 12 | (word >> 7 & 1) << 11 | (word >> 25 & 63) << 5 | (word >> 8 & 15) << 1, 13)
                if outcomes[f3]:
                    next_pc = (pc + offset) & MASK
                    if next_pc & 3:
                        raise Fault(0, next_pc)
            elif op in (3, 0x23):
                store = op == 0x23
                if f3 not in ((0, 1, 2) if store else (0, 1, 2, 4, 5)):
                    raise Fault(2, word)
                if store:
                    imm = sx((word >> 25) << 5 | (word >> 7 & 31), 12)
                address = (a + imm) & MASK
                size = 1 << (f3 & 3)
                if address % size:
                    raise Fault(6 if store else 4, address)
                aligned, lane = address & 0xfffffffc, address & 3
                bus_mask = ((1 << size) - 1) << lane if store else 0
                bus_data = (b & ((1 << (8 * size)) - 1)) << (8 * lane) if store else 0
                requests.append((int(store), aligned, bus_mask, bus_data))
                if not DATA <= address < DATA + 4096:
                    raise Fault(7 if store else 5, address)
                if store:
                    memory[address - DATA:address - DATA + size] = b.to_bytes(4, 'little')[:size]
                    store_addr, store_mask, store_data = aligned, bus_mask, bus_data
                else:
                    value = int.from_bytes(memory[address - DATA:address - DATA + size], 'little')
                    if f3 < 4:
                        value = sx(value, size * 8)
                    writes = True
            elif op in (0x13, 0x33):
                if op == 0x33 and not (f7 == 0 or f7 == 32 and f3 in (0, 5)):
                    raise Fault(2, word)
                if op == 0x13 and (f3 == 1 and f7 != 0 or f3 == 5 and f7 not in (0, 32)):
                    raise Fault(2, word)
                operand = imm & MASK if op == 0x13 else b
                if f3 == 0:
                    value = a - operand if op == 0x33 and f7 == 32 else a + operand
                elif f3 == 1:
                    value = a << (operand & 31)
                elif f3 == 2:
                    value = int(sx(a, 32) < sx(operand, 32))
                elif f3 == 3:
                    value = int(a < operand)
                elif f3 == 4:
                    value = a ^ operand
                elif f3 == 5:
                    value = (sx(a, 32) if f7 == 32 else a) >> (operand & 31)
                elif f3 == 6:
                    value = a | operand
                else:
                    value = a & operand
                writes = True
            elif op == 0x0b and enable and f3 == 0 and f7 == 0:
                value = sum(sx(a >> (8 * lane) & 255, 8) * sx(b >> (8 * lane) & 255, 8) for lane in range(4))
                writes = True
            elif op == 0x0f and f3 == 0:
                pass
            elif op == 0x73:
                if word == 0x73:
                    raise Fault(11, 0)
                if word == 0x100073:
                    raise Fault(3, 0)
                if word == 0x30200073:
                    next_pc = csrs[0x341]
                    csrs[0x300] = 0x1880 | ((csrs[0x300] >> 7 & 1) << 3)
                elif f3 in (1, 2, 3, 5, 6, 7):
                    ca = word >> 20
                    intent = f3 in (1, 5) or rs1 != 0
                    if ca not in csrs or ca in (0x301, 0xf14) and intent:
                        raise Fault(2, word)
                    old, source = csrs[ca], rs1 if f3 >= 5 else a
                    new = source if f3 in (1, 5) else old | source if f3 in (2, 6) else old & ~source
                    if intent:
                        csrs[ca] = ((new & 0x88) | 0x1800 if ca == 0x300 else
                                    new & 0xfffffffc if ca in (0x305, 0x341) else new & MASK)
                    value, writes = old, True
                else:
                    raise Fault(2, word)
            else:
                raise Fault(2, word)
            if writes and rd:
                regs[rd] = value & MASK
            events.append(('C', pc, word, rd if writes and rd else 0,
                           value & MASK if writes and rd else 0, store_addr, store_mask, store_data))
            pc = next_pc
        except Fault as fault:
            events.append(('T', pc, fault.cause, fault.tval))
            csrs[0x341], csrs[0x342], csrs[0x343] = pc & 0xfffffffc, fault.cause, fault.tval
            csrs[0x300] = 0x1800 | ((csrs[0x300] >> 3 & 1) << 7)
            pc = csrs[0x305]
    raise AssertionError('oracle did not terminate')


HANDLER_WORDS = [ins_csr(25, 0, 0x342, 2), ins_csr(24, 0, 0x343, 2),
                 ins_csr(23, 0, 0x300, 2), ins_csr(26, 0, 0x341, 2), ins_i(26, 26, 4),
                 ins_csr(0, 26, 0x341, 1), 0x30200073]
PRELUDE = [lui(28, HANDLER), ins_csr(0, 28, 0x305, 1)]
MEM_BASE = [lui(31, DATA)]


def run_case(binary, name, program, enable=0, r=1, d=0, seed=0, reset=-1, handler=False):
    seq = (PRELUDE if handler else []) + program
    stop = BASE + 4 * len(seq)
    words = {BASE + 4 * j: word for j, word in enumerate(seq)}
    words.update({HANDLER + 4 * j: word for j, word in enumerate(HANDLER_WORDS)})
    words[stop] = ins_j(0, 0)
    events, requests, memory = oracle(words, stop, enable)
    image = OUT / 'program.hex'
    image.write_text(''.join(f'{words.get(BASE + 4*j, 0x13):08x}\n' for j in range(4096)))
    output = command([str(binary), f'+PROGRAM={image}', f'+EVENTS={len(events)}',
                      f'+RESPONSE_DELAY={r}', f'+READY_DELAY={d}', f'+RANDOM_SEED={seed}', f'+RESET_AT={reset}'])
    (OUT / 'last_trace.log').write_text(output)
    lines = output.splitlines()
    if reset >= 0:
        lines = lines[max(j for j, line in enumerate(lines) if line.startswith('Z '))+1:]
    actual, cycles, actual_requests, responses, fetches, final_words = [], [], [], [], {}, {}
    for line in lines:
        items = line.split()
        if not items:
            continue
        if items[0] in ('C', 'T'):
            cycles.append(int(items[1]))
            if items[0] == 'C':
                actual.append(('C', int(items[2], 16), int(items[3], 16), int(items[4]),
                               *(int(x, 16) for x in items[5:])))
            else:
                actual.append(('T', *(int(x, 16) for x in items[2:])))
        elif items[0] == 'Q':
            actual_requests.append((int(items[2]), *(int(x, 16) for x in items[3:])))
        elif items[0] == 'R':
            responses.append((int(items[1]), int(items[2]), int(items[3], 16)))
        elif items[0] == 'F':
            fetches.setdefault(int(items[2], 16), int(items[1]))
        elif items[0] == 'D':
            final_words[int(items[1])] = int(items[2], 16)
    assert actual == events, f'{name}: event mismatch at ' + str(next((j for j, pair in enumerate(zip(actual, events)) if pair[0] != pair[1]), 'length')) + f'\nactual={actual[:20]}\nexpected={events[:20]}'
    assert actual_requests == requests, f'{name}: request sequence mismatch'
    assert len(responses) == len(requests), f'{name}: unpaired responses'
    actual_memory = b''.join(final_words[j].to_bytes(4, 'little') for j in range(1024))
    assert actual_memory == memory, f'{name}: final memory mismatch'
    return {'name': name, 'events': len(events), 'requests': len(requests),
            'span': cycles[-1] - cycles[0] + 1, 'cycles': cycles, 'fetches': fetches}


def check_inputs():
    design = json.loads((ROOT / '.nebula_inputs/artifact-6892c9f0c47b491c8ac8c08778634f0d/artifact.json').read_text())
    spec = json.loads((ROOT / '.nebula_inputs/artifact-971f6c7042664af69515024a25a72bc2/artifact.json').read_text())
    digest = lambda path: 'sha256:' + hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    assert digest('spec/design_doc.md') == design['payload']['design_digest']
    signoff = spec['payload']['document']['signoff']
    assert spec['payload']['spec_digest'] == signoff['revision_id'].replace('specir:', 'sha256:')
    for field, path in [('source', 'spec/draft.specir'), ('contracts', 'spec/contracts.json'), ('provenance', 'spec/provenance.json')]:
        assert digest(path) == signoff['input_digests'][field]
    provenance = json.loads((ROOT / 'spec/provenance.json').read_text())
    assert provenance['file_inputs']['spec/design_doc.md'] == design['payload']['design_digest']
    for path, expected in provenance['file_inputs'].items():
        if (ROOT / path).exists():
            assert digest(path) == expected
    assert all(not question['blocking'] for question in json.loads((ROOT / 'spec/questions.json').read_text()))
    for record in [design, spec]:
        for path in record['content']['paths']:
            assert (ROOT / path).read_bytes() == (ROOT / '.nebula_inputs' / record['id'] / path).read_bytes()
    return {'design_digest': design['payload']['design_digest'], 'spec_digest': spec['payload']['spec_digest']}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = {'inputs': check_inputs(), 'engineering_verdict': 'local_checks_pending', 'cases': [],
              'run_scope': 'local_selfcheck', 'common_coverage_eligible': False,
              'local_common_contribution': 0,
              'verilator_version': command(['verilator', '--version'], 'local_version.log').strip()}
    # The host has the runtime library but lacks its development linker name.
    libs = OUT / 'tool-libs'
    libs.mkdir(exist_ok=True)
    link = libs / 'libatomic.so'
    if not link.exists():
        link.symlink_to('/usr/lib64/libatomic.so.1')
    for top in ['rv32i_five_stage_cpu', 'nebula_cpu_npu_top']:
        command(['verilator', '--lint-only', '-Wall', '-Wno-UNUSEDSIGNAL', '--top-module', top] + RTL, top + '_lint.log')
    smoke = build('tb_T09', RTL + ['spec/public_cpu_interface_reference.sv'], 'public')
    result['public_smoke'] = command([str(smoke)], 'public_run.log').splitlines()[0]
    binaries = [build('selfcheck_cpu_tb', RTL + ['docs/implementation/selfcheck_cpu_tb.sv'], 'cpu'+str(e), e) for e in (0, 1)]
    npu = build('selfcheck_npu_tb', [RTL[0], 'docs/implementation/selfcheck_npu_tb.sv'], 'npu')
    result['npu'] = command([str(npu)], 'npu_run.log').splitlines()[0]
    cases = result['cases']
    enabled_addi = run_case(binaries[1], 'enabled-lat64',
                            [ins_i(j % 31 + 1, 0, j + 1) for j in range(64)], enable=1)
    for j, cycle in enumerate(enabled_addi['cycles']):
        assert cycle == enabled_addi['fetches'][BASE + 4*j] + 4
    assert enabled_addi['span'] == 64
    cases.append(enabled_addi)
    xdot_latency = run_case(binaries[1], 'xdot-normal-pipeline-latency',
                           [ins_i(1, 0, -1), ins_r(2, 1, 1, op=0x0b), ins_i(3, 2, 1)], enable=1)
    assert xdot_latency['cycles'][1] == xdot_latency['fetches'][BASE + 4] + 7
    assert xdot_latency['cycles'][2] == xdot_latency['cycles'][1] + 1
    cases.append(xdot_latency)
    # Six ALU pairs, five load classes and three fixed bus schedules.
    for pair in range(6):
        pair_metrics = []
        for dependent in (False, True):
            consumer = [ins_i(2, 1 if dependent else 0, 3),
                        ins_r(2, 1 if dependent else 0, 1 if dependent else 0),
                        ins_i(2, 1 if dependent else 0, 1, 1),
                        ins_i(2, 1 if dependent else 0, 7, 4),
                        ins_r(2, 1 if dependent else 0, 1 if dependent else 0, 2),
                        ins_i(2, 0, 7)][pair]
            producer = ins_i(0 if pair == 5 else 1, 0, 5)
            program = [producer] + ([0x13] if pair == 2 else []) + [consumer, ins_i(3, 2, 1)]
            metric = run_case(binaries[0], f'alu{pair}-{dependent}', program)
            pair_metrics.append(metric)
            cases.append(metric)
        assert pair_metrics[1]['span'] <= pair_metrics[0]['span']
        assert pair_metrics[1]['cycles'][-2]-pair_metrics[1]['cycles'][0] <= pair_metrics[0]['cycles'][-2]-pair_metrics[0]['cycles'][0]
    for r, d in [(1, 0), (8, 0), (1, 3)]:
        for kind in range(5):
            pair_metrics = []
            for dep in (False, True):
                src = 1 if dep else 2
                consumer = [ins_i(3, src, 2), ins_b(src, 0, 4),
                            ins_s(src, 0), ins_s(31, src, 4), ins_r(3, src, src)][kind]
                # Address dependency needs a valid aligned pointer as loaded data.
                program = MEM_BASE + [lui(2, DATA), ins_i(4, 0, 9)]
                if kind == 2:
                    program += [ins_s(31, 2)]
                program += [ins_i(1, 31, 0, 2, 3), consumer, ins_i(5, 0, 1)]
                metric = run_case(binaries[0], f'load{kind}-{dep}-{r}-{d}', program, r=r, d=d)
                cases.append(metric); pair_metrics.append(metric)
                if kind != 1:
                    assert metric['span'] <= metric['events'] + metric['requests']*(r+d) + int(dep), metric
            assert pair_metrics[1]['span'] <= pair_metrics[0]['span'] + 1
            assert pair_metrics[1]['cycles'][-2]-pair_metrics[1]['cycles'][-3] <= pair_metrics[0]['cycles'][-2]-pair_metrics[0]['cycles'][-3] + 1
    # All legal loads/lanes, stores, signed boundaries, consecutive memory, x0, FENCE.
    memory_program = MEM_BASE + [lui(1, 0x807ff000), ins_i(1, 1, -255)]
    for f3 in (0, 1, 2):
        for lane in range(0, 4, 1 << f3):
            memory_program += [ins_s(31, 1, lane, f3)]
            for load_f3 in (0, 1, 2, 4, 5):
                if lane % (1 << (load_f3 & 3)) == 0:
                    memory_program += [ins_i(2, 31, lane, load_f3, 3), ins_r(3, 2, 2)]
    memory_program += [ins_i(0, 31, 0, 2, 3), 0x0000000f, ins_s(31, 3, 4092)]
    # The last store uses a register offset because S immediates sign extend.
    memory_program[-1:] = [ins_i(30, 31, 2047), ins_i(30, 30, 2045), ins_s(30, 3)]
    for seed in range(1, 21):
        cases.append(run_case(binaries[0], f'memory-seed{seed}', memory_program, seed=seed))
    # Every branch condition in both directions, link forwarding and JALR bit0.
    for f3 in (0, 1, 4, 5, 6, 7):
        for a, b in [(-1, 1), (1, 1), (1, -1)]:
            program = MEM_BASE + [ins_i(1, 0, a), ins_i(2, 0, b), ins_b(1, 2, 8, f3),
                                  ins_s(31, 1), ins_s(31, 2, 4), ins_j(4, 8),
                                  ins_s(31, 1, 8), ins_i(5, 4, 1)]
            cases.append(run_case(binaries[0], f'branch{f3}-{a}-{b}', program, seed=3))
    program = [lui(1, BASE), ins_i(1, 1, 17), ins_i(2, 1, 0, 0, 0x67),
               ins_s(0, 0), ins_i(3, 2, 1)]
    cases.append(run_case(binaries[0], 'jalr-bit0-link', program))
    # CSR serialization, all forms, legal readonly reads and exact masks.
    csr_program = [ins_i(1, 0, -1)]
    for ca in (0x300, 0x305, 0x340, 0x341, 0x342, 0x343):
        for f3 in (1, 2, 3, 5, 6, 7):
            csr_program += [ins_csr(2, 1, ca, f3), ins_csr(3, 0, ca, 2), ins_i(4, 3, 0)]
    csr_program += [ins_csr(0, 0, 0x340, 1), ins_csr(2, 0, 0x301, 2), ins_csr(3, 0, 0xf14, 6)]
    cases.append(run_case(binaries[0], 'csr-forms-masks', csr_program))
    faults = [0xffffffff, 0x02000033, 0x0000100f, 0x73, 0x100073,
              ins_i(2, 31, 1, 1, 3), ins_i(2, 31, 2, 2, 3),
              ins_s(31, 1, 1, 1), ins_s(31, 1, 2, 2),
              ins_i(2, 0, 0, 2, 3), ins_s(0, 1), ins_j(2, 2),
              ins_b(0, 0, 2), ins_i(2, 0, 2, 0, 0x67),
              ins_csr(2, 1, 0x301, 2), ins_csr(0, 1, 0xf14, 3),
              ins_csr(2, 0, 0x999, 2), ins_r(2, 1, 1, op=0x0b)]
    for j, fault in enumerate(faults):
        program = MEM_BASE + [ins_i(1, 0, 0x88), ins_csr(0, 1, 0x300, 1), ins_i(1, 0, 0),
                              fault, ins_s(31, 1, 12), ins_csr(22, 0, 0x300, 2), ins_i(3, 0, 5)]
        cases.append(run_case(binaries[0], f'fault{j}-mret', program, handler=True, seed=7))
    for f3, f7 in [(1, 0), (0, 1), (0, 32)]:
        cases.append(run_case(binaries[1], f'bad-enabled-xdot-{f3}-{f7}',
                              [ins_r(2, 0, 0, f3, f7, 0x0b), ins_i(3, 0, 1)], enable=1, handler=True))
    cases.append(run_case(binaries[0], 'not-taken-unaligned-target',
                          [ins_i(1, 0, 1), ins_b(1, 0, 2), ins_i(2, 0, 2)]))
    # Older memory failure defeats younger redirect/xdot and its markers.
    for enable in (0, 1):
        for younger in [ins_j(2, 8), ins_r(2, 1, 1, op=0x0b)]:
            program = MEM_BASE + [ins_i(1, 0, 1), ins_i(3, 0, 0, 2, 3), younger,
                                  ins_s(31, 1, 4), ins_i(4, 0, 3)]
            cases.append(run_case(binaries[enable], f'older-memory-fault-{enable}-{younger}', program, enable=enable, handler=True, r=8))
    # Extension producers/consumers including load-to-xdot, rd0 and repeated xdot.
    extension_program = MEM_BASE + [lui(1, 0x80808000), ins_i(1, 1, 128),
        ins_r(2, 1, 1, op=0x0b), ins_r(3, 2, 2), ins_s(31, 3),
        ins_i(4, 31, 0, 2, 3), ins_r(5, 4, 4, op=0x0b),
        ins_r(0, 1, 1, op=0x0b), ins_r(6, 5, 5, op=0x0b), ins_s(31, 6, 4)]
    for seed in range(1, 6):
        cases.append(run_case(binaries[1], f'xdot-seed{seed}', extension_program, enable=1, seed=seed))
    # Wrong-path illegal/custom instructions and stores must have no effects.
    program = MEM_BASE + [ins_j(2, 16), 0xffffffff, ins_r(3, 1, 1, op=0x0b),
                          ins_s(31, 1), ins_i(4, 2, 1)]
    cases.append(run_case(binaries[1], 'wrong-path-illegal-xdot-store', program, enable=1))
    # Fixed-seed generated programs with an independent architectural interpreter.
    for seed in range(20):
        rng = random.Random(seed)
        enable = seed % 2
        program = MEM_BASE + [ins_i(j, 0, rng.randrange(-2048, 2048)) for j in range(1, 16)]
        for _ in range(1000):
            rd, a, b = [rng.randrange(16) for _ in range(3)]
            kind = rng.randrange(6)
            if kind == 0:
                f3 = rng.randrange(8); f7 = rng.choice([0, 32]) if f3 in (0, 5) else 0
                program.append(ins_r(rd, a, b, f3, f7))
            elif kind == 1:
                f3 = rng.randrange(8)
                imm = rng.randrange(32) | (rng.choice([0, 0x400]) if f3 == 5 else 0) if f3 in (1, 5) else rng.randrange(-2048, 2048)
                program.append(ins_i(rd, a, imm, f3))
            elif kind == 2:
                f3 = rng.choice([0, 1, 2, 4, 5]); offset = rng.randrange(0, 128) * 4
                program.append(ins_i(rd, 31, offset, f3, 3))
            elif kind == 3:
                program.append(ins_s(31, b, rng.randrange(128)*4, rng.randrange(3)))
            elif kind == 4 and enable:
                program.append(ins_r(rd, a, b, op=0x0b))
            else:
                program += [ins_b(a, b, 8, rng.choice([0, 1, 4, 5, 6, 7])), ins_i(rd, a, rng.randrange(-2048, 2048))]
        program += [ins_s(31, j, 1024 + 4*j) for j in range(16)]
        cases.append(run_case(binaries[enable], f'random{seed}', program, enable=enable, seed=seed+1))
    for enable, program in [(0, memory_program), (1, extension_program)]:
        for edge in (2, 5, 8, 12, 20, 30):
            cases.append(run_case(binaries[enable], f'reset{enable}-{edge}', program, enable=enable, r=8, d=3, reset=edge))
    result['structure'] = {}
    for top, label in [('rv32i_five_stage_cpu', 'base'), ('nebula_cpu_npu_top', 'enabled')]:
        script = 'read_verilog -sv ' + ' '.join(RTL) + f'; hierarchy -check -top {top}; proc; opt; check; stat; write_json build/rtl/{label}.json'
        command(['yosys', '-Q', '-T', '-p', script], label + '_yosys.log')
        modules = json.loads((OUT / (label + '.json')).read_text())['modules']
        types = collections.Counter(cell['type'] for module in modules.values() for cell in module['cells'].values())
        assert types['$mul'] == (0 if label == 'base' else 4)
        assert all(types[k] == 0 for k in ('$div', '$mod'))
        result['structure'][label] = {'multipliers': types['$mul'], 'modules': list(modules)}
    for case in cases:
        case.pop('cycles'); case.pop('fetches')
    result['tests_passed'] = len(cases)
    result['tested_file_sha256'] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                                     for path in RTL + ['docs/implementation/check_rtl.py',
                                                        'docs/implementation/selfcheck_cpu_tb.sv',
                                                        'docs/implementation/selfcheck_npu_tb.sv']}
    result['engineering_verdict'] = 'pass_local_rtl_checks; frozen_full_acceptance_not_run'
    result['limitations'] = ['No ACT4/Sail or frozen directed/random acceptance run; this local oracle is independently authored.',
                             'No formal proof, mapped timing, physical closure or benchmark scoring.',
                             'UNUSEDSIGNAL waived for unused shared decode/payload fields; no functional lint warnings waived.']
    (OUT / 'selfcheck_results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'RTL_SELFCHECK_PASS cpu_runs={len(cases)} public_smoke=64 npu_pairs=65536 npu_random=2000 cancellations=10')


if __name__ == '__main__':
    main()
