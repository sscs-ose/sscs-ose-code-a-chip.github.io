"""Golden model for can_framer.v -- bit-exact CAN 2.0A data frame builder.

Builds SOF + 11-bit ID + RTR + IDE + r0 + DLC + data + CRC-15, applies
CAN bit-stuffing over SOF..CRC, then appends the trailer
(CRC-delimiter, ACK slot, ACK delimiter, EOF x7, IFS x3 -- all recessive).
Used both by the cocotb testbench and the Code-a-Chip notebook.
"""

CRC15_POLY = 0x4599  # x^15+x^14+x^10+x^8+x^7+x^4+x^3+1


def crc15(bits):
    """CRC-15/CAN over a list of bits (MSB first)."""
    crc = 0
    for b in bits:
        if ((crc >> 14) & 1) ^ b:
            crc = (((crc << 1) & 0x7FFF) ^ CRC15_POLY)
        else:
            crc = (crc << 1) & 0x7FFF
    return crc


def build_can_frame(can_id, dlc, data):
    """Return the full transmitted bitstream (list of 0/1) for a CAN data frame.

    can_id: 11-bit int, dlc: 0..8, data: list of dlc bytes (byte0 sent first).
    """
    assert 0 <= can_id < 2048
    assert 0 <= dlc <= 8 and len(data) == dlc
    raw = [0]  # SOF
    raw += [(can_id >> i) & 1 for i in range(10, -1, -1)]
    raw += [0, 0, 0]  # RTR, IDE, r0
    raw += [(dlc >> i) & 1 for i in range(3, -1, -1)]
    for byte in data:
        raw += [(byte >> i) & 1 for i in range(7, -1, -1)]
    crc = crc15(raw)
    raw += [(crc >> i) & 1 for i in range(14, -1, -1)]

    # bit stuffing over SOF..CRC: after five consecutive equal bits,
    # the transmitter inserts a complementary stuff bit (even if the run
    # ends at the last CRC bit -- the receiver expects it there).
    stuffed = []
    last, run = None, 0
    for b in raw:
        stuffed.append(b)
        if b == last:
            run += 1
        else:
            last, run = b, 1
        if run == 5:
            stuffed.append(1 - b)
            # The stuff bit is removed by the receiver before run-counting,
            # so it must not seed the next run: reset the counter.
            last, run = None, 0
    # trailer: no stuffing; ACK slot transmitted recessive (TX-only framer)
    stuffed += [1] * 13  # crc-delim, ack, ack-delim, EOF(7), IFS(3)
    return stuffed


def count_stuff_bits(can_id, dlc, data):
    raw_len = 34 + 8 * dlc
    return len(build_can_frame(can_id, dlc, data)) - 13 - raw_len


if __name__ == "__main__":
    # smoke test: worst-case stuffing pattern
    bits = build_can_frame(0x7FF, 8, [0xFF] * 8)
    print(f"frame bits: {len(bits)}, stuff bits: {count_stuff_bits(0x7FF, 8, [0xFF]*8)}")
    bits2 = build_can_frame(0x100, 8, [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88])
    print(f"frame bits: {len(bits2)}, stuff bits: {count_stuff_bits(0x100, 8, [0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88])}")
    print("SOF..:", "".join(map(str, bits2[:24])), "...")
