#!/usr/bin/env python3
"""
============================================================================
MicroRV8-GT Assembler - revision 2
============================================================================
ISA de 16 bits. 8 registros (r0-r7). Datos de 8 bits.

Formato de instruccion:
  I-type (ALU-Imm):  [15:13]=000 [12:10]=rd  [9:7]=rs1 [6:4]=funct3 [3:0]=imm4
  R-type (ALU-Reg):  [15:13]=001 [12:10]=rd  [9:7]=rs1 [6:4]=rs2    [3:1]=funct3 [0]=0
  L-type (LOAD):     [15:13]=010 [12:10]=rd  [9:7]=rs1 [6:4]=000    [3:0]=imm4
  S-type (STORE):    [15:13]=011 [12:10]=rs2 [9:7]=rs1 [6:4]=000    [3:0]=imm4
  B-type (BEQ):      [15:13]=100 [12:10]=rs1 [9:7]=rs2 [6:4]=000    [3:0]=imm4
  J-type (JUMP/JAL): [15:13]=111/101 [12:10]=rd [9:0]=target10
  O-type (OUT):      [15:13]=110 [12:10]=000 [9:7]=rs1 [6:0]=0

Uso:
  python3 assembler.py programa.asm
  python3 assembler.py programa.asm -o salida.hex
  python3 assembler.py programa.asm -o salida.bin --binary
============================================================================
"""

import re, sys, argparse
from pathlib import Path

# funct3 para ALU ops
FUNCT3 = {
    "ADD": 0, "SUB": 1, "AND": 2, "OR": 3,
    "XOR": 4, "SLL": 5, "SRL": 6, "SLT": 7,
}

MNEMONICS = {
    # I-type: rd, rs1, imm
    "ADDI": ("I", 0b000, FUNCT3["ADD"]),
    "SUBI": ("I", 0b000, FUNCT3["SUB"]),
    "ANDI": ("I", 0b000, FUNCT3["AND"]),
    "ORI":  ("I", 0b000, FUNCT3["OR"]),
    "XORI": ("I", 0b000, FUNCT3["XOR"]),
    "SLLI": ("I", 0b000, FUNCT3["SLL"]),
    "SRLI": ("I", 0b000, FUNCT3["SRL"]),
    "SLTI": ("I", 0b000, FUNCT3["SLT"]),
    # R-type: rd, rs1, rs2
    "ADD":  ("R", 0b001, FUNCT3["ADD"]),
    "SUB":  ("R", 0b001, FUNCT3["SUB"]),
    "AND":  ("R", 0b001, FUNCT3["AND"]),
    "OR":   ("R", 0b001, FUNCT3["OR"]),
    "XOR":  ("R", 0b001, FUNCT3["XOR"]),
    "SLL":  ("R", 0b001, FUNCT3["SLL"]),
    "SRL":  ("R", 0b001, FUNCT3["SRL"]),
    "SLT":  ("R", 0b001, FUNCT3["SLT"]),
    # L-type: rd, rs1, imm
    "LOAD":  ("L", 0b010, None),
    # S-type: rs2, rs1, imm   (dato, base, offset)
    "STORE": ("S", 0b011, None),
    # B-type: rs1, rs2, label|offset
    "BEQ":   ("B", 0b100, None),
    # J-type: [rd,] target
    "JUMP":  ("J", 0b111, None),
    "JAL":   ("J", 0b101, None),
    # O-type: rs1
    "OUT":   ("O", 0b110, None),
    # Pseudoinstrucciones
    "NOP":   ("P", None, None),
    "MOV":   ("P", None, None),
}


def parse_reg(s):
    s = s.strip().lower()
    if s.startswith("r") and s[1:].isdigit():
        n = int(s[1:])
        if 0 <= n <= 7:
            return n
    raise ValueError(f"Registro invalido: '{s}' (use r0-r7)")


def parse_imm(s):
    s = s.strip()
    if s.startswith("0x") or s.startswith("0X"): return int(s, 16)
    if s.startswith("0b") or s.startswith("0B"): return int(s, 2)
    return int(s)


def to4(v):
    if v < -8 or v > 15:
        raise ValueError(f"Inmediato {v} fuera de rango [-8..15]")
    return v & 0xF


class Assembler:
    def __init__(self):
        self.labels = {}
        self.prog   = []   # (addr, mnem, operands, lineno)
        self.code   = []

    def first_pass(self, lines):
        addr = 0
        for lineno, raw in enumerate(lines, 1):
            line = re.sub(r";.*", "", raw).strip()
            if not line:
                continue
            if ":" in line:
                label, rest = line.split(":", 1)
                label = label.strip()
                self.labels[label] = addr
                line = rest.strip()
            if not line:
                continue
            parts = re.split(r"[\s,]+", line)
            mnem = parts[0].upper()
            if mnem not in MNEMONICS:
                raise SyntaxError(f"Linea {lineno}: '{mnem}' desconocido")
            self.prog.append((addr, mnem, parts[1:], lineno))
            addr += 1

    def second_pass(self):
        for addr, mnem, ops, lineno in self.prog:
            kind, opcode, funct = MNEMONICS[mnem]
            word = 0
            try:
                if kind == "P":  # pseudoinstrucciones
                    if mnem == "NOP":
                        word = 0  # ADDI r0, r0, 0
                    elif mnem == "MOV":
                        # MOV rd, rs  -> ADD rd, rs, r0
                        rd = parse_reg(ops[0]); rs = parse_reg(ops[1])
                        word = (0b001 << 13) | (rd << 10) | (rs << 7) | (0 << 4) | (FUNCT3["ADD"] << 1)

                elif kind == "I":
                    rd  = parse_reg(ops[0])
                    rs1 = parse_reg(ops[1])
                    imm = to4(parse_imm(ops[2]))
                    word = (opcode << 13) | (rd << 10) | (rs1 << 7) | (funct << 4) | imm

                elif kind == "R":
                    rd  = parse_reg(ops[0])
                    rs1 = parse_reg(ops[1])
                    rs2 = parse_reg(ops[2])
                    word = (opcode << 13) | (rd << 10) | (rs1 << 7) | (rs2 << 4) | (funct << 1)

                elif kind == "L":
                    rd  = parse_reg(ops[0])
                    rs1 = parse_reg(ops[1])
                    imm = to4(parse_imm(ops[2]))
                    word = (opcode << 13) | (rd << 10) | (rs1 << 7) | imm

                elif kind == "S":
                    rs2 = parse_reg(ops[0])   # dato
                    rs1 = parse_reg(ops[1])   # base
                    imm = to4(parse_imm(ops[2]))
                    word = (opcode << 13) | (rs2 << 10) | (rs1 << 7) | imm

                elif kind == "B":
                    rs1 = parse_reg(ops[0])
                    rs2 = parse_reg(ops[1])
                    tgt = ops[2]
                    if tgt in self.labels:
                        offset = self.labels[tgt] - (addr + 1)
                    else:
                        offset = parse_imm(tgt)
                    imm = to4(offset)
                    word = (opcode << 13) | (rs1 << 10) | (rs2 << 7) | imm

                elif kind == "J":
                    tgt = ops[0] if mnem == "JUMP" else ops[1]
                    rd  = parse_reg(ops[0]) if mnem == "JAL" else 0
                    if tgt in self.labels:
                        target = self.labels[tgt]
                    else:
                        target = parse_imm(tgt)
                    if target < 0 or target > 511:
                        raise ValueError(f"Destino {target} fuera de rango [0..511]")
                    word = (opcode << 13) | (rd << 10) | (target & 0x3FF)

                elif kind == "O":
                    rs1 = parse_reg(ops[0])
                    word = (opcode << 13) | (rs1 << 7)

            except (IndexError, ValueError) as e:
                raise SyntaxError(f"Linea {lineno} ({mnem}): {e}")

            self.code.append(word & 0xFFFF)

    def assemble(self, source):
        self.first_pass(source.splitlines())
        self.second_pass()
        return self.code

    def write_hex(self, path):
        Path(path).write_text("\n".join(f"{w:04x}" for w in self.code) + "\n")

    def write_bin(self, path):
        n = len(self.code)
        data = bytes([0xAA, 0x55, (n >> 8) & 0x01, n & 0xFF])
        for w in self.code:
            data += w.to_bytes(2, "big")
        Path(path).write_bytes(data)

    def listing(self):
        print()
        print("=" * 72)
        print("MicroRV8-GT Assembly Listing")
        print("=" * 72)
        print(f"{'Addr':<6} {'Hex':>6}  {'Binary':>16}  Source")
        print("-" * 72)
        for (addr, mnem, ops, _), word in zip(self.prog, self.code):
            b = f"{word:016b}"
            bs = f"{b[0:3]}_{b[3:6]}_{b[6:9]}_{b[9:12]}_{b[12:]}"
            src = f"{mnem} {', '.join(ops)}"
            print(f"0x{addr:03x}  0x{word:04x}  {bs}  {src}")
        print("=" * 72)
        print(f"Total: {len(self.code)} instrucciones")
        print("=" * 72)


def main():
    ap = argparse.ArgumentParser(description="MicroRV8-GT Assembler")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default="program.hex")
    ap.add_argument("--binary", action="store_true")
    ap.add_argument("--no-listing", action="store_true")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"Error: '{args.input}' no encontrado"); sys.exit(1)

    asm = Assembler()
    try:
        asm.assemble(src.read_text())
    except SyntaxError as e:
        print(f"Error: {e}"); sys.exit(1)

    out = Path(args.output)
    asm.write_hex(str(out))
    print(f"Generado: {out}  ({len(asm.code)} instrucciones)")

    if args.binary:
        bp = out.with_suffix(".bin")
        asm.write_bin(str(bp))
        print(f"Generado: {bp}")

    if not args.no_listing:
        asm.listing()


if __name__ == "__main__":
    main()
