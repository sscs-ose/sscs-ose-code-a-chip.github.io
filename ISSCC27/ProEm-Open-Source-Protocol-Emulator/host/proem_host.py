# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: host/proem_host.py
# Type: Host library (builds ISA instruction bytes for the host link)
# Author: Paul Vincent Bezzina
# Language: Python
# Description:
# =============================================================================

SYNC, ASYNC, GENERATE, RECOVER = 0, 1, 2, 3
CLOCK_HZ = 50_000_000


def _op(code, ch, n=0):
    return (code << 4) | (ch << 3) | (n & 7)


def start(ch, val, cyc, cap, wr, pin=0):
    return [_op(1, ch), (wr << 7) | (cap << 6) | (cyc & 15), pin & 7, val & 0xFF]


def hdr(ch, n, val, cyc, cap, wr, grp=0, sr=0, any_value=0, seek=0):
    return [_op(2, ch, n), (wr << 7) | (cap << 6) | (grp << 4) | (cyc & 15), (sr << 7) | (any_value << 6) | (seek << 5), val & 0xFF]


def main(ch, bits, direction, we=0, ack=0, pin=0, sr=0):
    return [_op(3, ch), (direction << 6) | (we << 5) | (ack << 4) | (sr << 3) | (pin & 7), (bits >> 8) & 0xFF, bits & 0xFF]


def order(ch, msb):
    return [_op(6, ch, msb)]


def run(ch, mode=0):
    return [_op(7, ch, mode)]


def clear(ch):
    return [_op(9, ch)]


def line(ch, code, pin_a, stuff=0, pin_b=0, inv=0, sany=0, boundary=0):
    v = (code << 13) | (inv << 12) | (boundary << 11) | ((pin_a & 7) << 8) | (sany << 7) | ((stuff & 15) << 3) | (pin_b & 7)
    return [_op(0xA, ch), (v >> 8) & 0xFF, v & 0xFF]


def clock(ch, src, div, pin=0, edge=0, idle=0, etk=0):
    v = (src << 30) | (edge << 28) | (idle << 27) | ((pin & 7) << 24) | (etk << 22) | (div & 0x3FFFFF)
    return [_op(0xB, ch), (v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF]


def out(ch, drive, idle=0, pair=0, eop=0, i2c=0, cshigh=0):
    return [_op(0xD, ch), (drive << 6) | (idle << 5) | (pair << 4) | (eop << 3) | (i2c << 2) | (cshigh << 1)]


def data(ch, length, val):
    return [_op(0xC, ch, length - 1), val & 0xFF]


REPLY_OFF, REPLY_GOOD, REPLY_BAD, REPLY_ALWAYS = 0, 1, 2, 3
CRC_FROM_START, CRC_FROM_MAIN = 0, 7


def branch(ch, rule, hit, miss, src, block, mask=0, value=0):
    return [_op(0xF, ch, rule), (hit << 6) | (miss << 4) | (src << 3) | (block & 7), mask & 0xFF, value & 0xFF]


def crc_a(ch, width, poly, cover_from=CRC_FROM_MAIN, init_ones=0):
    return [_op(0xF, ch, 2), (((width - 1) & 15) << 4) | ((cover_from & 7) << 1) | (init_ones & 1), (poly >> 8) & 0xFF, poly & 0xFF]


def crc_b(ch, on=1, check=0, append=0, invert=0, residue=0, bytes_only=0, span=0):
    return [_op(0xF, ch, 3), (on << 7) | (check << 6) | (append << 5) | (invert << 4) | (bytes_only << 3) | (span << 2), (residue >> 8) & 0xFF, residue & 0xFF]


def reply(ch, when, length, pattern, gap=0):
    return [_op(0xF, ch, 4), ((when & 3) << 6) | (((length - 1) & 15) << 2) | (gap & 3), (pattern >> 8) & 0xFF, pattern & 0xFF]


def crc_wire(bits, width, poly, init_ones=0):
    shift = 16 - width
    crc = (0xFFFF << shift) & 0xFFFF if init_ones else 0
    for b in bits:
        fb = ((crc >> 15) & 1) ^ b
        crc = (crc << 1) & 0xFFFF
        if fb:
            crc ^= (poly << shift) & 0xFFFF
    return crc >> shift


def uart_divider(baud):
    return round(CLOCK_HZ / baud)


def uart_tx_setup(ch, baud):
    div = uart_divider(baud)
    return (clear(ch) + order(ch, 0) + line(ch, 0, 0) + clock(ch, ASYNC, div)
            + out(ch, 3, idle=1) + start(ch, 0x00, 1, 0, 1) + main(ch, 9, 1))


def uart_tx_byte(ch, value):
    return data(ch, 8, value) + data(ch, 1, 1)


def uart_tx(ch, baud, payload, preload=4):
    first = uart_tx_setup(ch, baud)
    for b in payload[:preload]:
        first += uart_tx_byte(ch, b)
    first += run(ch, 0)
    rest = []
    for b in payload[preload:]:
        rest += uart_tx_byte(ch, b)
    return first, rest


def decode_return(stream):
    events = []
    for i in range(0, len(stream) - 1, 2):
        head, value = stream[i], stream[i + 1]
        if (head & 0xC0) == 0xC0:
            events.append(("link", value))
        elif (head & 0xC0) == 0x80:
            ch = (head >> 5) & 1
            length = head & 0x0F
            if length == 0x0F:
                events.append(("status", ch, value))
            elif length == 0x0E:
                events.append(("crc", ch, value & 1, (value >> 1) & 1))
            else:
                events.append(("data", ch, length, value))
    return events
