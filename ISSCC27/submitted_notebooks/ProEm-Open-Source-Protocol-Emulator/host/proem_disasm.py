# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: host/proem_disasm.py
# Type: Host tool (turns ISA v0.7.1 instruction bytes back into readable text)
# Author: Jeffrey Chan
# Language: Python
# Description:
# =============================================================================
#
# The reverse of proem_host.py: proem_host builds instruction bytes from
# arguments, this file takes the bytes apart again. The field positions come
# from docs/protocol_emulator_isa.pdf and src/core/control_unit.sv.

# Operand bytes after the first byte, per OP (control_unit.sv lines 141-145)
OPERANDS = {
    0x0: 0,  # NOP
    0x1: 3,  # START
    0x2: 3,  # HDR
    0x3: 3,  # MAIN
    0x4: 4,  # END
    0x5: 2,  # WDOG
    0x6: 0,  # ORDER
    0x7: 0,  # RUN
    0x8: 0,  # HALT
    0x9: 0,  # CLEAR
    0xA: 2,  # LINE
    0xB: 4,  # CLOCK
    0xC: 1,  # DATA
    0xD: 1,  # OUT
    0xE: 2,  # LINK
    0xF: 3,  # BRANCH
}

NAMES = {
    0x0: "NOP",
    0x1: "START",
    0x2: "HDR",
    0x3: "MAIN",
    0x4: "END",
    0x5: "WDOG",
    0x6: "ORDER",
    0x7: "RUN",
    0x8: "HALT",
    0x9: "CLEAR",
    0xA: "LINE",
    0xB: "CLOCK",
    0xC: "DATA",
    0xD: "OUT",
    0xE: "LINK",
    0xF: "BRANCH",
}


# Step 1: cut the byte stream into instructions
def split(program):
    """Cut a byte stream into instructions, the way control_unit.sv does.

    Returns a list of bytes objects, one per instruction.
    """
    instructions = []
    i = 0
    while i < len(program):
        op = program[i] >> 4  # top 4 bits = OP
        size = 1 + OPERANDS[op]  # first byte + its operands
        instructions.append(bytes(program[i : i + size]))
        i += size  # the next byte starts a new instruction
    return instructions


# Step 2: take the first byte apart: OP | CH | N


def header(first):
    """Split the first byte into (op, ch, n).

    bit:  7 6 5 4 | 3  | 2 1 0
          ---OP-- | CH | --N--
    """
    op = (first >> 4) & 0xF
    ch = (first >> 3) & 1
    n = first & 0x7
    return op, ch, n


# ---------------------------------------------------------------------------
# Step 3: one function per instruction. Each takes (n, operands) and
# returns the text after the mnemonic and channel.
# ---------------------------------------------------------------------------


def _none(n, ops):
    # NOP, HALT, CLEAR: nothing more to say
    return ""


def _order(n, ops):
    # proem_host.order(): N[0] = 0 LSB first, 1 MSB first
    return "MSB first" if n & 1 else "LSB first"

def _wdog(n, ops):
    # ISA section "WDOG", 16-bit limit in clocks, high byte first; 0=off
    limit = ops[0] << 8 | ops[1]
    if limit == 0: 
        return "OFF"
    return f"LIMIT={limit} clock{'s' if limit != 1 else ''}"
    
    

def _run(n, ops):
    # ISA section "Run modes": N[1:0] = 00 RUN, 01 RUN READ, 10 RUN WRITE
    modes = {0: "mode=RUN", 1: "mode=READ", 2: "mode=WRITE"}
    return modes.get(n & 3, "mode=reserved")


def _data(n, ops):
    # proem_host.data(): N = length - 1, one operand byte = value
    length = n + 1
    value = ops[0]
    return f"{length} bit{'s' if length > 1 else ''}, value=0x{value:02X}"


def _start(n, ops):
    # proem_host.start():
    #   byte 1: W(7) CAP(6) GRP(5:4) CYC(3:0)
    #   byte 2: SR(7) ANY(6) SEEK(5) -- PIN(2:0)
    #   byte 3: VALUE
    w = (ops[0] >> 7) & 1
    cap = (ops[0] >> 6) & 1
    cyc = ops[0] & 0xF
    pin = ops[1] & 0x7
    value = ops[2]
    direction = "write" if w else "read"
    text = f"{direction} {cyc} bit{'s' if cyc != 1 else ''}, value=0x{value:02X}, pin={pin}"
    if cap:
        text += ", capture"
    return text


def _hdr(n, ops):
    # proem_host.hdr(): same layout as START, N = header number 1-6
    #   byte 1: W(7) CAP(6) GRP(5:4) CYC(3:0)
    #   byte 2: SR(7) ANY(6) SEEK(5) -- PIN(2:0), PIN is ignored (headers use MAIN's pin)
    #   byte 3: VALUE
    w = (ops[0] >> 7) & 1
    cap = (ops[0] >> 6) & 1
    grp = (ops[0] >> 4) & 0x3
    cyc = ops[0] & 0xF
    sr = (ops[1] >> 7) & 1
    any_value = (ops[1] >> 6) & 1
    seek = (ops[1] >> 5) & 1
    val = ops[2]
    direction = "write" if w else "read"
    groups = {0: "always", 1: "read runs", 2: "write runs"}
    text = f"#{n} {direction} {cyc} bit{'s' if cyc != 1 else ''}, value=0x{val:02X}, {groups.get(grp, 'reserved')}"
    if cap:
        text += ", capture"
    if sr:
        text += ", Sr"
    if any_value:
        text += ", any value"
    if seek:
        text += ", seek"
    return text


def _main(n, ops):
    # proem_host.main():
    #   byte 1: DIR[7:6] WE[5] ACK[4] SR[3] PIN[2:0]
    #   bytes 2-3: BITS, number of data bits per frame, high byte first
    d = (ops[0] >> 6) & 0b11
    we = (ops[0] >> 5) & 1
    ack = (ops[0] >> 4) & 1
    sr = (ops[0] >> 3) & 1
    pin = (ops[0] >> 0) & 0b111
    bits = (ops[1] << 8) | ops[2]
    direction = {0: "read", 1: "write", 2: "follow"}
    text = f"{direction.get(d, 'reserved')} {bits} bit{'s' if bits != 1 else ''}, pin={pin}"
    if we:
        text += ", wait END"
    if ack:
        text += ", ACK"
    if sr:
        text += ", Sr"
    return text


def _end(n, ops):
    # ISA section "END":
    #   byte 1: LEN(7:3) PIN_A(2:0)
    #   byte 2: PAIR(7) INV(6) ERR(5) -- PIN_B(2:0)
    #   bytes 3-4: PATTERN, high byte first; the last LEN bits of the window must match it
    length = (ops[0] >> 3) & 0x1F
    pin_a = ops[0] & 0x7
    pair = (ops[1] >> 7) & 1
    inv = (ops[1] >> 6) & 1
    err = (ops[1] >> 5) & 1
    pin_b = ops[1] & 0x7
    pattern = (ops[2] << 8) | ops[3]
    pattern_bits = f"{pattern & ((1 << length) - 1):0{length}b}" if length else "-"
    if pair:
        text = f"pair pin={pin_a},{pin_b}{' (B inverted)' if inv else ''}"
    else:
        text = f"pin={pin_a}"
    text += f", match last {length} bit{'s' if length != 1 else ''} = {pattern_bits}"
    if err:
        text += ", abort if both high"
    return text


def _line(n, ops):
    # proem_host.line(): one 16-bit number, high byte first
    #   CODE(15:13) INV(12) BND(11) PIN_A(10:8) SANY(7) STUFF(6:3) PIN_B(2:0)
    v = (ops[0] << 8) | ops[1]
    code = (v >> 13) & 0x7
    inv = (v >> 12) & 1
    bnd = (v >> 11) & 1
    pin_a = (v >> 8) & 0x7
    sany = (v >> 7) & 1
    stuff = (v >> 3) & 0xF
    pin_b = v & 0x7
    codes = {0: "NRZ", 1: "NRZI", 2: "NRZI pair", 3: "Manchester", 4: "Manchester (Thomas)"}
    text = f"code={codes.get(code, 'reserved')}, pin={pin_a}"
    if code == 2:
        text += f",{pin_b}"
    if inv:
        text += ", inverted"
    if bnd:
        text += ", first edge is a bit boundary"
    if stuff:
        text += f", unstuff after {stuff} {'equal bits' if sany else 'ones'}"
    return text


CLOCK_HZ = 50_000_000


def _rate(per_second):
    # A rate as short text with a metric prefix, to put a unit after: 115207 -> "115.2 k"
    for prefix, scale in (("M", 1e6), ("k", 1e3)):
        if per_second >= scale:
            return f"{per_second / scale:.4g} {prefix}"
    return f"{per_second:.4g} "


def _clock(n, ops):
    # proem_host.clock(): one 32-bit number, high byte first
    #   SRC(31:30) EDGE(29:28) IDLE(27) PIN(26:24) ETK(23:22) DIV(21:0)
    v = (ops[0] << 24) | (ops[1] << 16) | (ops[2] << 8) | ops[3]
    src = (v >> 30) & 0x3
    edge = (v >> 28) & 0x3
    idle = (v >> 27) & 1
    pin = (v >> 24) & 0x7
    etk = (v >> 22) & 0x3
    div = v & 0x3FFFFF
    edges = {0: "rising", 1: "falling", 2: "both"}.get(edge, "reserved")
    if src == 0:
        # SYNC: ticks come from an input clock pin, DIV is not used
        text = f"SYNC on pin {pin}, {edges} edge"
    elif src == 2:
        # GENERATE: DIV is the half period, so the clock runs at 50 MHz / (2 * DIV)
        rate = f" ({_rate(CLOCK_HZ / (2 * div))}Hz)" if div else ""
        text = f"GENERATE half period={div}{rate}, {edges} edge, idle={idle}, read back on pin {pin}"
    else:
        # ASYNC and RECOVER: DIV is the number of clocks per bit
        rate = f" (~{_rate(CLOCK_HZ / div)}bit/s)" if div else ""
        text = f"{'ASYNC' if src == 1 else 'RECOVER'} div={div}{rate}"
    if etk:
        text += ", end tick=" + {1: "every clock", 2: "mid-bit"}.get(etk, "reserved")
    return text


def _out(n, ops):
    # proem_host.out(): DRIVE(7:6) IDLE(5) PAIR(4) EOP(3) I2C(2) CSH(1)
    drive = (ops[0] >> 6) & 0x3
    idle = (ops[0] >> 5) & 1
    pair = (ops[0] >> 4) & 1
    eop = (ops[0] >> 3) & 1
    i2c = (ops[0] >> 2) & 1
    csh = (ops[0] >> 1) & 1
    drives = {0: "off", 1: "push-pull while sending", 2: "open drain", 3: "push-pull always"}
    text = drives[drive]
    if drive == 3:
        text += f", idle={idle}"
    if pair:
        text += ", complement on pair"
    if eop:
        text += ", end of packet"
    if i2c:
        text += ", I2C conditions"
    if csh:
        text += ", select active high"
    return text


def _link(n, ops):
    # ISA section "LINK": return UART clocks per bit, high byte first; 0 = the auto-baud rate
    div = (ops[0] << 8) | ops[1]
    if div == 0:
        return "return link at the auto-baud rate"
    return f"return link div={div} (~{_rate(CLOCK_HZ / div)}baud)"


def _branch(n, ops):
    # ISA sections "BRANCH" and "CRC and reply": N picks what the three operand bytes set up
    if n <= 1:
        return _branch_rule(n, ops)
    if n == 2:
        return _crc_a(ops)
    if n == 3:
        return _crc_b(ops)
    if n == 4:
        return _reply(ops)
    return f"N={n} (invalid, raises cmd_error)"


def _branch_rule(n, ops):
    #   byte 1: HIT(7:6) MISS(5:4) SRC(3) BLOCK(2:0)
    #   byte 2: MASK, byte 3: VALUE
    if ops[0] == 0:
        return f"rule {n} off"
    hit = (ops[0] >> 6) & 0x3
    miss = (ops[0] >> 4) & 0x3
    src = (ops[0] >> 3) & 1
    block = ops[0] & 0x7
    actions = {0: "keep", 1: "read", 2: "write", 3: "abort"}
    if src == 0:
        name = "START" if block == 0 else f"HDR {block}"
        return (f"rule {n}: if {name} & 0x{ops[1]:02X} == 0x{ops[2]:02X} "
                f"then {actions[hit]} else {actions[miss]}")
    if block == 0:
        return f"rule {n}: if read-back differs from what was driven then {actions[hit]}"
    if block == 1:
        return f"rule {n}: when the CRC check ends, good -> {actions[hit]}, bad -> {actions[miss]}"
    return f"rule {n}: line event {block} (reserved)"


def _crc_a(ops):
    #   byte 1: WIDTH-1(7:4) FROM(3:1) INIT(0), bytes 2-3: POLY, high byte first
    width = ((ops[0] >> 4) & 0xF) + 1
    start = (ops[0] >> 1) & 0x7
    init = ops[0] & 1
    poly = (ops[1] << 8) | ops[2]
    covers = {0: "START"}.get(start, "MAIN" if start == 7 else f"HDR {start}")
    return f"CRC-{width} poly=0x{poly:0{(width + 3) // 4}X}, from {covers}, init={'ones' if init else 'zeros'}"


def _crc_b(ops):
    #   byte 1: ON(7) CHK(6) APP(5) INV(4) BYTE(3) SPAN(2), bytes 2-3: RESIDUE, high byte first
    if ops[0] == 0:
        return "CRC off"
    flags = [name for bit, name in ((7, "on"), (6, "check"), (5, "append"), (4, "inverted"),
                                    (3, "bytes only"), (2, "span frames")) if (ops[0] >> bit) & 1]
    residue = (ops[1] << 8) | ops[2]
    return f"CRC {', '.join(flags)}, residue=0x{residue:04X}"


def _reply(ops):
    #   byte 1: WHEN(7:6) LEN-1(5:2) GAP(1:0), bytes 2-3: PATTERN, high byte first
    when = (ops[0] >> 6) & 0x3
    if when == 0:
        return "reply off"
    length = ((ops[0] >> 2) & 0xF) + 1
    gap = ops[0] & 0x3
    pattern = ((ops[1] << 8) | ops[2]) & ((1 << length) - 1)
    whens = {1: "CRC good", 2: "CRC bad", 3: "always"}
    return (f"reply when {whens[when]}: {length} bit{'s' if length != 1 else ''} "
            f"0x{pattern:0{(length + 3) // 4}X}, after {gap} bit time{'s' if gap != 1 else ''}")


def _todo(n, ops):
    # Placeholder until the instruction has its own decoder
    return "(not decoded yet)"


DECODERS = {
    0x0: _none,  # NOP
    0x1: _start,  # START
    0x2: _hdr,  # HDR
    0x3: _main,  # MAIN
    0x4: _end,  # END
    0x5: _wdog,  # WDOG
    0x6: _order,  # ORDER
    0x7: _run,  # RUN
    0x8: _none,  # HALT
    0x9: _none,  # CLEAR
    0xA: _line,  # LINE
    0xB: _clock,  # CLOCK
    0xC: _data,  # DATA
    0xD: _out,  # OUT
    0xE: _link,  # LINK
    0xF: _branch,  # BRANCH (N = 0, 1 rule; 2 CRC A; 3 CRC B; 4 reply)
}


# ---------------------------------------------------------------------------
# Putting it together
# ---------------------------------------------------------------------------


def decode(instr):
    """One instruction (bytes) -> one line of text, without the hex column."""
    op, ch, n = header(instr[0])
    ops = instr[1:]
    if len(ops) < OPERANDS[op]:
        return f"{NAMES[op]:<6} (cut short: needs {OPERANDS[op]} operand bytes, got {len(ops)})"
    text = f"{NAMES[op]:<6} ch={'AB'[ch]}"
    detail = DECODERS[op](n, ops)
    if detail:
        text += "  " + detail
    return text


def disassemble(program):
    """A whole program -> a multi-line string: hex bytes on the left, meaning on the right."""
    lines = []
    for instr in split(program):
        hex_bytes = " ".join(f"{b:02X}" for b in instr)
        lines.append(f"{hex_bytes:<16} {decode(instr)}")
    return "\n".join(lines)


if __name__ == "__main__":
    # The 25-byte program that sends 'A' on channel A at 115200 baud
    import proem_host as ph

    first, rest = ph.uart_tx(0, 115200, b"A")
    print(disassemble(first))
