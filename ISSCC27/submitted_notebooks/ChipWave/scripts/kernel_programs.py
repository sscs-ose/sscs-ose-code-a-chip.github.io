#!/usr/bin/env python3
"""Deterministic RV32I firmware emitter and independent instruction interpreter.

No external compiler is required. Programs include input loads, packing,
software multiplication, accumulation, output stores and completion MMIO.
"""
from __future__ import annotations

import json
import random
import struct
from pathlib import Path

BASE, SIZE, DATA, OUTPUT, TOHOST = 0x80000000, 256 * 1024, 0x80010000, 0x80020000, 0x8003F000
MASK = (1 << 32) - 1


def signed(value: int, width: int = 32) -> int:
    value &= (1 << width) - 1
    return value - (1 << width) if value >> (width - 1) else value


def dot4(a: int, b: int) -> int:
    return sum(signed(a >> (8 * i), 8) * signed(b >> (8 * i), 8) for i in range(4)) & MASK


class Program:
    def __init__(self):
        self.words, self.assembly, self.labels, self.fixups = [], [], {}, []

    def emit(self, word, text):
        self.words.append(word & MASK)
        self.assembly.append(text)

    def label(self, name):
        assert name not in self.labels
        self.labels[name] = len(self.words) * 4
        self.assembly.append(name + ':')

    def i(self, op, rd, rs1, imm=0):
        opcode, f3 = {'addi': (0x13, 0), 'slli': (0x13, 1), 'srli': (0x13, 5),
                      'andi': (0x13, 7), 'lb': (3, 0), 'lbu': (3, 4), 'lw': (3, 2)}[op]
        assert -2048 <= imm <= 2047
        self.emit((imm & 4095) << 20 | rs1 << 15 | f3 << 12 | rd << 7 | opcode,
                  f'{op} x{rd}, x{rs1}, {imm}')

    def r(self, op, rd, a, b):
        f7, f3, opcode = {'add': (0, 0, 0x33), 'sub': (32, 0, 0x33),
                          'xor': (0, 4, 0x33), 'or': (0, 6, 0x33), 'xdot4': (0, 0, 0x0B)}[op]
        self.emit(f7 << 25 | b << 20 | a << 15 | f3 << 12 | rd << 7 | opcode,
                  f'{op} x{rd}, x{a}, x{b}')

    def li(self, rd, value):
        value &= MASK
        low = signed(value, 12)
        high = ((value - low) >> 12) & 0xFFFFF
        self.emit(high << 12 | rd << 7 | 0x37, f'lui x{rd}, 0x{high:x}')
        self.i('addi', rd, rd, low)

    def sw(self, value, address, offset=0):
        assert -2048 <= offset <= 2047
        imm = offset & 4095
        self.emit((imm >> 5) << 25 | value << 20 | address << 15 | 2 << 12 |
                  (imm & 31) << 7 | 0x23, f'sw x{value}, {offset}(x{address})')

    def jump(self, label, rd=0):
        self.fixups.append((len(self.words), 'jal', rd, 0, label))
        self.emit(0, f'jal x{rd}, {label}')

    def branch(self, op, a, b, label):
        self.fixups.append((len(self.words), op, a, b, label))
        self.emit(0, f'{op} x{a}, x{b}, {label}')

    def finish(self):
        for index, op, a, b, label in self.fixups:
            offset = self.labels[label] - index * 4
            assert offset % 2 == 0
            if op == 'jal':
                assert -(1 << 20) <= offset < 1 << 20
                imm = offset & 0x1FFFFF
                word = ((imm >> 20) << 31 | ((imm >> 1) & 1023) << 21 |
                        ((imm >> 11) & 1) << 20 | ((imm >> 12) & 255) << 12 | a << 7 | 0x6F)
            else:
                assert -4096 <= offset < 4096
                imm = offset & 8191
                f3 = {'beq': 0, 'bne': 1, 'blt': 4}[op]
                word = ((imm >> 12) << 31 | ((imm >> 5) & 63) << 25 | b << 20 |
                        a << 15 | f3 << 12 | ((imm >> 1) & 15) << 8 | ((imm >> 11) & 1) << 7 | 0x63)
            self.words[index] = word
        return b''.join(struct.pack('<I', word) for word in self.words)


def software_multiply(p):
    """Signed inputs x10/x11, result x5; caller-saved x6/x7/x28, fixed 8 steps."""
    p.label('mul8')
    p.r('xor', 6, 10, 11)
    p.branch('blt', 10, 0, 'neg_a')
    p.jump('check_b')
    p.label('neg_a')
    p.r('sub', 10, 0, 10)
    p.label('check_b')
    p.branch('blt', 11, 0, 'neg_b')
    p.jump('mul_start')
    p.label('neg_b')
    p.r('sub', 11, 0, 11)
    p.label('mul_start')
    p.i('addi', 5, 0, 0)
    p.i('addi', 28, 0, 8)
    p.label('mul_loop')
    p.i('andi', 7, 11, 1)
    p.branch('beq', 7, 0, 'mul_skip')
    p.r('add', 5, 5, 10)
    p.label('mul_skip')
    p.i('slli', 10, 10, 1)
    p.i('srli', 11, 11, 1)
    p.i('addi', 28, 28, -1)
    p.branch('bne', 28, 0, 'mul_loop')
    p.branch('blt', 6, 0, 'neg_product')
    p.jump('mul_return')
    p.label('neg_product')
    p.r('sub', 5, 0, 5)
    p.label('mul_return')
    p.emit(1 << 15 | 0x67, 'jalr x0, x1, 0')


def workload(name, seed=20261012):
    rng = random.Random(seed)
    if name == 'DOT64':
        a, b = [rng.randrange(-128, 128) for _ in range(64)], [rng.randrange(-128, 128) for _ in range(64)]
        groups = [[(i, i) for i in range(64)]]
    elif name == 'GEMM8':
        a, b = [rng.randrange(-128, 128) for _ in range(64)], [rng.randrange(-128, 128) for _ in range(64)]
        groups = [[(row * 8 + k, k * 8 + col) for k in range(8)] for row in range(8) for col in range(8)]
    elif name == 'CONV3':
        a, b = [rng.randrange(-128, 128) for _ in range(64)], [rng.randrange(-128, 128) for _ in range(9)]
        groups = [[((row + dy) * 8 + col + dx, dy * 3 + dx) for dy in range(3) for dx in range(3)]
                  for row in range(6) for col in range(6)]
    else:
        raise ValueError(name)
    expected = [sum(a[i] * b[j] for i, j in group) for group in groups]
    return a, b, groups, expected


def build_kernel(name, accelerated, seed=20261012):
    a, b, groups, expected = workload(name, seed)
    p = Program()
    p.li(20, DATA)
    p.li(21, DATA + len(a))
    p.li(22, OUTPUT)
    for out_index, pairs in enumerate(groups):
        p.i('addi', 8, 0, 0)
        if accelerated:
            for start in range(0, len(pairs), 4):
                p.i('addi', 10, 0, 0)
                p.i('addi', 11, 0, 0)
                for lane, (ai, bi) in enumerate(pairs[start:start + 4]):
                    for packed, base, offset in ((10, 20, ai), (11, 21, bi)):
                        p.i('lbu', 12, base, offset)
                        if lane:
                            p.i('slli', 12, 12, 8 * lane)
                        p.r('or', packed, packed, 12)
                p.r('xdot4', 5, 10, 11)
                p.r('add', 8, 8, 5)
        else:
            for ai, bi in pairs:
                p.i('lb', 10, 20, ai)
                p.i('lb', 11, 21, bi)
                p.jump('mul8', 1)
                p.r('add', 8, 8, 5)
        p.sw(8, 22, out_index * 4)
    p.li(23, TOHOST)
    p.i('addi', 24, 0, 1)
    p.sw(24, 23)
    p.label('halt')
    p.jump('halt')
    if not accelerated:
        software_multiply(p)
    code = p.finish()
    assert len(code) < DATA - BASE, 'program overlaps input data'
    image = bytearray(SIZE)
    image[:len(code)] = code
    data = bytes(x & 255 for x in a + b)
    image[DATA - BASE:DATA - BASE + len(data)] = data
    return p, image, expected, data


def build_extension(seed=20261013):
    """Custom retirement, bypass, x0, operand overlap, loads and wrong paths."""
    rng, p, expected = random.Random(seed), Program(), []
    p.li(22, OUTPUT)
    p.li(20, DATA)
    values = [(0x80808080, 0x80808080), (0x80808080, 0x7F7F7F7F),
              (0x04030201, 0x01020304)] + [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(128)]
    for index, (a, b) in enumerate(values):
        p.li(10, a)
        p.li(11, b)
        if index % 5 == 0:
            p.sw(10, 20)
            p.i('lw', 10, 20, 0)
        rd = (5, 10, 11, 0)[index % 4]
        source_a = 0 if index % 17 == 0 else 10
        p.r('xdot4', rd, source_a, 11)
        if rd:
            p.r('add', 8, rd, 0)
            p.r('xdot4', 9, 8, 0)
            p.branch('beq', 9, 0, f'valid_{index}')
            p.jump('bad')
            p.label(f'valid_{index}')
            p.sw(8, 22, index * 4)
            expected.append(signed(dot4(0 if source_a == 0 else a, b)))
        else:
            p.i('addi', 8, 0, 37)
            p.sw(8, 22, index * 4)
            expected.append(37)
        p.jump(f'skip_{index}')
        p.r('xdot4', 8, 10, 11)
        p.sw(8, 22, index * 4)
        p.label(f'skip_{index}')
    p.i('addi', 24, 0, 1)
    p.jump('complete')
    p.label('bad')
    p.i('addi', 24, 0, 2)
    p.label('complete')
    p.li(23, TOHOST)
    p.sw(24, 23)
    p.label('halt')
    p.jump('halt')
    image = bytearray(SIZE)
    code = p.finish()
    assert len(code) < DATA - BASE
    image[:len(code)] = code
    return p, image, expected, bytes(8)


def interpret(image, max_steps=2000000):
    """Instruction semantics only: no DUT, pipeline, or cycle assumptions."""
    memory, regs, pc, events = bytearray(image), [0] * 32, BASE, []
    for _ in range(max_steps):
        assert BASE <= pc <= BASE + SIZE - 4 and pc % 4 == 0
        insn = int.from_bytes(memory[pc - BASE:pc - BASE + 4], 'little')
        opcode, rd, f3, a, b, f7 = insn & 127, insn >> 7 & 31, insn >> 12 & 7, insn >> 15 & 31, insn >> 20 & 31, insn >> 25
        next_pc, value, write, mem_addr, strobe, mem_data = pc + 4, 0, False, 0, 0, 0
        imm = signed(insn >> 20, 12)
        if opcode == 0x37:
            value, write = insn & 0xFFFFF000, True
        elif opcode == 0x13:
            write = True
            if f3 == 0: value = regs[a] + imm
            elif f3 == 1 and f7 == 0: value = regs[a] << (b & 31)
            elif f3 == 5 and f7 == 0: value = regs[a] >> (b & 31)
            elif f3 == 7: value = regs[a] & imm
            else: raise ValueError(f'unsupported immediate 0x{insn:x}')
        elif opcode in (0x33, 0x0B):
            write = True
            if opcode == 0x0B:
                if f7 or f3: raise ValueError('invalid xdot4')
                value = dot4(regs[a], regs[b])
            elif f3 == 0 and f7 in (0, 32): value = regs[a] + (-regs[b] if f7 else regs[b])
            elif f3 == 4 and f7 == 0: value = regs[a] ^ regs[b]
            elif f3 == 6 and f7 == 0: value = regs[a] | regs[b]
            else: raise ValueError(f'unsupported register 0x{insn:x}')
        elif opcode == 3:
            address = (regs[a] + imm) & MASK
            width = {0: 1, 4: 1, 2: 4}[f3]
            assert BASE <= address <= BASE + SIZE - width and address % width == 0
            value = int.from_bytes(memory[address - BASE:address - BASE + width], 'little')
            if f3 == 0: value = signed(value, 8)
            write = True
        elif opcode == 0x23:
            assert f3 == 2
            offset = signed((insn >> 25) << 5 | (insn >> 7 & 31), 12)
            mem_addr, strobe, mem_data = (regs[a] + offset) & MASK, 15, regs[b]
            assert mem_addr % 4 == 0 and BASE <= mem_addr <= BASE + SIZE - 4
            memory[mem_addr - BASE:mem_addr - BASE + 4] = struct.pack('<I', mem_data)
        elif opcode == 0x63:
            offset = signed((insn >> 31) << 12 | (insn >> 7 & 1) << 11 |
                            (insn >> 25 & 63) << 5 | (insn >> 8 & 15) << 1, 13)
            take = {0: regs[a] == regs[b], 1: regs[a] != regs[b], 4: signed(regs[a]) < signed(regs[b])}[f3]
            if take: next_pc = pc + offset
        elif opcode == 0x6F:
            offset = signed((insn >> 31) << 20 | (insn >> 12 & 255) << 12 |
                            (insn >> 20 & 1) << 11 | (insn >> 21 & 1023) << 1, 21)
            value, write, next_pc = pc + 4, True, pc + offset
        elif opcode == 0x67:
            assert f3 == 0
            value, write, next_pc = pc + 4, True, (regs[a] + imm) & ~1
        else:
            raise ValueError(f'unsupported opcode 0x{opcode:x} at 0x{pc:x}')
        events.append(dict(kind='commit', pc=pc, insn=insn, rd=rd if write and rd else 0,
                           wdata=value & MASK, mem_addr=mem_addr, mem_wstrb=strobe, mem_wdata=mem_data))
        if write and rd: regs[rd] = value & MASK
        regs[0] = 0
        pc = next_pc & MASK
        if strobe and mem_addr == TOHOST:
            assert mem_data == 1
            return events, memory
    raise RuntimeError('reference instruction limit exceeded')


def write_elf(path, code, data):
    ident = b'\x7fELF\x01\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIIIIIHHHHHH', ident, 2, 243, 1, BASE, 52, 0, 0, 52, 32, 2, 0, 0, 0)
    start = 52 + 64
    segments = struct.pack('<IIIIIIII', 1, start, BASE, BASE, len(code), len(code), 5, 4)
    segments += struct.pack('<IIIIIIII', 1, start + len(code), DATA, DATA, len(data), len(data), 6, 1)
    path.write_bytes(header + segments + code + data)


def self_check():
    assert dot4(0x80808080, 0x80808080) == 65536
    assert signed(dot4(0x80808080, 0x7F7F7F7F)) == -65024
    assert signed(0x80000000) == -(1 << 31)
    _, image, expected, _ = build_extension()
    _, memory = interpret(image)
    assert [struct.unpack_from('<i', memory, OUTPUT - BASE + i * 4)[0] for i in range(len(expected))] == expected
    for name in ('DOT64', 'GEMM8', 'CONV3'):
        outputs = []
        for accelerated in (False, True):
            p, image, expected, _ = build_kernel(name, accelerated)
            events, memory = interpret(image)
            actual = [struct.unpack_from('<i', memory, OUTPUT - BASE + i * 4)[0] for i in range(len(expected))]
            assert actual == expected, (name, accelerated, actual, expected)
            assert sum((e['insn'] & 127) == 0x0B for e in events) == (sum((len(g) + 3) // 4 for g in workload(name)[2]) if accelerated else 0)
            outputs.append(actual)
        assert outputs[0] == outputs[1]
    print('KERNEL_REFERENCE_SELF_CHECK_PASS')


if __name__ == '__main__':
    self_check()
