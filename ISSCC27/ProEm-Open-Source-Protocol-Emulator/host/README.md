# Using ProEm from a host

ProEm does nothing on its own. A host (an RP2040, or a PC through a USB-UART adapter) programs it
over a serial line, and the chip then produces or receives the protocol at the pins with exact
timing. `proem_host.py` builds the instruction bytes and decodes the replies.

## Wiring

| Chip pin | Connect to |
| --- | --- |
| `ui[0]` (RX) | Host UART TX: instructions to the chip |
| `uo[0]` (TX) | Host UART RX: results from the chip |
| `uio[0]`, `uio[1]`, `uio[2]` | Channel A: data (TX, MOSI, SDA, D+), pair (D-), clock (SCK, SCL) |
| `uio[3]`, `uio[4]`, `uio[5]` | Channel B, same order |
| `uo[4]`, `uo[5]` | HOST_FULL for A and B: pause sending DATA while high |
| `clk`, `rst_n` | 50 MHz clock and reset (from the Tiny Tapeout demo board) |

The pins are logic level. USB, CAN, RS-485 and Ethernet need the usual transceiver or line driver.

## The sequence

1. **Reset**, then send `0x55` once. The chip measures it to learn the host's baud rate
   (auto-baud), so any common rate works.
2. **Program a channel.** Instructions set the line coding, the clock, how the pins are driven,
   and the shape of a frame (START, up to six headers, MAIN, END). These settings stay until they
   are rewritten, `CLEAR` is sent, or the chip is reset.
3. **Queue payload** with `DATA` (1 to 8 bits per entry; the host FIFO holds 8 entries per channel).
4. **Start** with `RUN`. Plain `RUN` also starts a new frame whenever payload is waiting, which is
   what a transmit stream needs; `RUN READ` and `RUN WRITE` run one transaction each.
5. **Read the replies** on `uo[0]`: every message is two bytes.

| First byte | Second byte | Meaning |
| --- | --- | --- |
| `0x80 + L` (A) or `0xA0 + L` (B), L = 0 to 8 | value | Data received: L bits |
| `0x8E` (A) or `0xAE` (B) | result | CRC result of a read frame, before its status: bit 0 good, bit 1 checked |
| `0x8F` (A) or `0xAF` (B) | flags | End of a frame: bit 0 complete, 1 abort, 2 timeout, 3 line error, 4 overflow, 5 underrun, 6 branch matched, 7 branch abort |
| `0xC0` | flags | Link events: bit 0 receive error, 1 bad instruction, 2 DATA dropped on A, 3 on B |

`decode_return()` turns a stream of these bytes into a list of events.

The full instruction set is in [docs/protocol_emulator_isa.pdf](../docs/protocol_emulator_isa.pdf),
with the exact bytes for every protocol in its examples.

## Example: send a UART message

```python
import serial
import proem_host as ph

s = serial.Serial("COM5", 115200, timeout=1)
s.write(bytes([0x55]))                          # once after reset
first, rest = ph.uart_tx(0, 115200, b"A0000")   # channel A, 115200 baud
s.write(bytes(first))                           # setup + first 4 bytes + RUN
s.write(bytes(rest))                            # the rest, streamed while it runs
print(ph.decode_return(s.read(10)))             # five ('status', 0, 1): each byte sent
```

`uart_tx` programs one frame per character: START writes the start bit, MAIN writes 9 bits
(8 data bits LSB first, then the stop bit) taken from two `DATA` entries. For `b"A0000"` it sends:

```
90 60                  CLEAR channel A, ORDER LSB first
A0 00 00               LINE: plain coding
B0 40 00 01 B2         CLOCK: timed, 434 clocks per bit (115200 baud at 50 MHz)
D0 E0                  OUT: push-pull, idle high
10 81 00 00            START: write 1 bit = 0
30 40 00 09            MAIN: write 9 bits
C7 41 C0 01            'A' and its stop bit
C7 30 C0 01 (x3)       '0' and its stop bit
70                     RUN
C7 30 C0 01            the last '0', streamed
```

For channel B use `ch=1`; the data goes out on `uio[3]`. The cocotb test
`test_send_uart_A0000` in `test/test.py` runs exactly this and checks the pin with a UART
receiver model.

## Other protocols

The same pattern covers every standard: fixed parts of a frame (addresses, commands, sync
patterns) go in START and the headers, the payload goes through `DATA`, and the ending comes from
`OUT` (I2C STOP, USB end of packet, chip select).
The ISA document lists complete programs for SPI, I2C (controller and target), USB low speed,
10BASE-T receive, PS/2, SWD-style and CAN-style arbitration.
[docs/standards_guide.pdf](../docs/standards_guide.pdf) gives tested programs for sixteen more
standards, from RS-485 and Modbus RTU to DALI, CAN 2.0B and RC5 infrared.

## CRC and reply

The chip can check or append a CRC itself and answer a good frame with a short reply. Three
builders set this up; `crc_wire()` computes the same CRC in Python, bit by bit in wire order, for
checking results or building test data.

```python
# USB low speed, channel A: check the DATA packet's CRC-16 and send an ACK handshake
prog  = ph.crc_a(0, 16, 0x8005, cover_from=ph.CRC_FROM_MAIN, init_ones=1)
prog += ph.crc_b(0, check=1, residue=0x800D)
prog += ph.reply(0, ph.REPLY_GOOD, 16, 0xD280, gap=3)   # SYNC 0x80, PID 0xD2, 3 bit times later

# CAN, channel B: append the CRC-15 to every frame it sends
prog += ph.crc_a(1, 15, 0x4599, cover_from=ph.CRC_FROM_START)
prog += ph.crc_b(1, append=1)
```

A read frame with the check on returns `('crc', channel, good, checked)` from `decode_return()`
just before its status. `branch(ch, rule, hit, miss, src=1, block=1)` makes a rule act on the
same result.
