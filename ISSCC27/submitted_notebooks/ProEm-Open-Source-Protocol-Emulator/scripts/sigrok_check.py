# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: scripts/sigrok_check.py
# Type: Script: independent check of the standards waveforms with sigrok protocol decoders
# Author: Paul Vincent Bezzina
# Language: Python 3
# Description:
# =============================================================================

import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BIN = os.environ.get('PROEM_STD', os.path.join(ROOT, 'build', 't_standards'))
OUT = os.path.join(ROOT, 'build', 'vcd')


def crc16_modbus(data):
    c = 0xFFFF
    for x in data:
        c ^= x
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return [c & 0xFF, c >> 8]


def nmea(body):
    s = 0
    for ch in body[1:-1]:
        s ^= ord(ch)
    return body + '%02X\r\n' % s


def lin_pid(i):
    p0 = ((i >> 0) ^ (i >> 1) ^ (i >> 2) ^ (i >> 4)) & 1
    p1 = (~((i >> 1) ^ (i >> 3) ^ (i >> 4) ^ (i >> 5))) & 1
    return i | (p0 << 6) | (p1 << 7)


def lin_sum(b):
    s = 0
    for x in b:
        s += x
        if s > 255:
            s -= 255
    return (~s) & 0xFF


def crc8(b, poly=0x07):
    c = 0
    for x in b:
        c ^= x
        for _ in range(8):
            c = ((c << 1) ^ poly) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


def text(s):
    return [ord(c) for c in s]


req_modbus = [0x01, 0x03, 0x00, 0x00, 0x00, 0x02]
rsp_modbus = [0x01, 0x03, 0x04, 0x00, 0x0A, 0x00, 0x0B]
req_kline = [0x81, 0xEE, 0xF0, 0x81]
rsp_kline = [0x80, 0xF0, 0xEE, 0x03, 0xC1, 0xEA, 0x8F]
pid = lin_pid(0x10)

UART = 'uart:rx={pin}:baudrate={baud}'

CASES = [
    ('rs485', 'RS-485 receive 115200 8N1', UART.format(pin='p0', baud=115200), 'uart=rx-data', [0x01, 0x10, 0xA5, 0x5A, 0xFF, 0x00]),
    ('rs485', 'RS-485 transmit 115200 8N1', UART.format(pin='p3', baud=115200), 'uart=rx-data', [0x02, 0x47, 0x6F, 0x03]),
    ('midi', 'MIDI receive Note On', 'uart:rx=p0:baudrate=31250', 'uart=rx-data', [0x90, 0x3C, 0x64]),
    ('midi', 'MIDI transmit Note Off', 'uart:rx=p3:baudrate=31250', 'uart=rx-data', [0x80, 0x3C, 0x00]),
    ('nmea0183', 'NMEA 0183 receive', 'uart:rx=p0:baudrate=4800', 'uart=rx-data', text(nmea('$GPGLL,4916.45,N,12311.12,W,225444,A*'))),
    ('nmea0183', 'NMEA 0183 transmit', 'uart:rx=p3:baudrate=4800', 'uart=rx-data', text(nmea('$PPROE,1,TEST*'))),
    ('profibus', 'PROFIBUS receive 8E1', 'uart:rx=p0:baudrate=500000:parity=even', 'uart=rx-data', [0x10, 0x02, 0x01, 0x49, 0x4C, 0x16]),
    ('profibus', 'PROFIBUS transmit 8E1', 'uart:rx=p3:baudrate=500000:parity=even', 'uart=rx-data', [0x10, 0x01, 0x02, 0x00, 0x03, 0x16]),
    ('modbus', 'Modbus RTU request 8E1 with CRC', 'uart:rx=p0:baudrate=19200:parity=even', 'uart=rx-data', req_modbus + crc16_modbus(req_modbus)),
    ('modbus', 'Modbus RTU response 8E1 with CRC', 'uart:rx=p3:baudrate=19200:parity=even', 'uart=rx-data', rsp_modbus + crc16_modbus(rsp_modbus)),
    ('dmx', 'DMX512 transmit: break, MAB and start code 00', 'dmx512:dmx=p3', 'dmx512', ['Break | MAB | Start bit', 'Start code | 0 / 0x0'], ('p3', 10, 0)),
    ('dmx', 'DMX512 transmit: slots at 250 kbit/s 8N2', 'uart:rx=p3:baudrate=250000:stop_bits=2', 'uart=rx-data', [0x00, 0xFF, 0x80, 0x01, 0x7E]),
    ('lin', 'LIN master frame (sync, PID, data, checksum)', 'uart:rx=p0:baudrate=19200,lin', 'uart=rx-data', [0x55, pid, 0x34, 0x12, lin_sum([pid, 0x34, 0x12])]),
    ('kline', 'K-Line request (KWP2000)', 'uart:rx=p0:baudrate=10400', 'uart=rx-data', req_kline + [sum(req_kline) & 0xFF]),
    ('kline', 'K-Line response (KWP2000)', 'uart:rx=p0:baudrate=10400', 'uart=rx-data', rsp_kline + [sum(rsp_kline) & 0xFF]),
    ('sdi12', 'SDI-12 command 1200 7E1 inverted', 'uart:rx=p0:baudrate=1200:data_bits=7:parity=even:invert_rx=yes', 'uart=rx-data', text('0M!')),
    ('sdi12', 'SDI-12 response 1200 7E1 inverted', 'uart:rx=p0:baudrate=1200:data_bits=7:parity=even:invert_rx=yes', 'uart=rx-data', text('00011\r\n')),
    ('smbus', 'SMBus Write Word with PEC', 'i2c:scl=p2:sda=p0', 'i2c=address-write:data-write', [0x40, 0x21, 0x34, 0x12, crc8([0x80, 0x21, 0x34, 0x12])]),
    ('smbus', 'SMBus Read Word with PEC', 'i2c:scl=p2:sda=p0', 'i2c=address-read:data-read', [0x40, 0xCD, 0xAB, crc8([0x80, 0x21, 0x81, 0xCD, 0xAB])]),
    ('mdio', 'MDIO write PHY 1 register 4', 'mdio:mdc=p2:mdio=p0', 'mdio=decode', ['WRITE: 01E1 PHYAD: 01 REGAD: 04']),
    ('mdio', 'MDIO read PHY 1 registers 4 and 2', 'mdio:mdc=p2:mdio=p0', 'mdio=decode', ['READ:  01E1 PHYAD: 01 REGAD: 04', 'READ:  0022 PHYAD: 01 REGAD: 02']),
    ('sdcard', 'SD card SPI CMD0 with CRC-7', 'spi:clk=p5:mosi=p0:miso=p6:cs=select_b', 'spi=mosi-data', [0x40, 0x00, 0x00, 0x00, 0x00, 0x95]),
    ('sdcard', 'SD card SPI CMD8 with CRC-7', 'spi:clk=p5:mosi=p0:miso=p6:cs=select_b', 'spi=mosi-data', [0x48, 0x00, 0x00, 0x01, 0xAA, 0x87]),
    ('spi3', '3-wire SPI write', 'spi:clk=p2:mosi=p0:cs=select_a', 'spi=mosi-data', [0x34, 0x5A, 0xC3]),
    ('spi3', '3-wire SPI read', 'spi:clk=p2:mosi=p0:cs=select_a', 'spi=mosi-data', [0xB4, 0x9E, 0x07]),
    ('dali', 'DALI forward frame (address 03, command 90)', 'dali:dali=p3', 'dali=raw', ['Raw data: 03 | Raw data: 90']),
    ('dali', 'DALI backward frame A5', 'dali:dali=p0', 'dali=reply', ['Reply: 165']),
    ('dali', 'DALI second backward frame 3C', 'dali:dali=p0', 'dali=reply', ['Reply: 60'], ('p0', 1000, 20)),
    ('can_ext', 'CAN 2.0B extended frame (NMEA 2000 PGN 127250)', 'can:can_rx=p0:nominal_bitrate=250000', 'can=data', [0x01, 0x34, 0x12, 0xFF, 0x7F, 0xFF, 0x7F, 0xFD]),
    ('rc5', 'RC5 infrared (address 5, command 0x35)', 'ir_rc5:ir=p0', 'ir_rc5=address:command', ['5', '53']),
]


def capture(key):
    os.makedirs(OUT, exist_ok=True)
    vcd = os.path.join(OUT, key + '.vcd')
    if not os.path.exists(vcd):
        env = dict(os.environ, PROEM_VCD=vcd, PROEM_COV=os.devnull)
        r = subprocess.run([BIN, key], env=env, capture_output=True, text=True)
        if 'ALL PASS' not in r.stdout:
            print(r.stdout)
            raise SystemExit('simulation of %s failed' % key)
    return vcd


def decode(vcd, spec, annotations):
    cmd = ['sigrok-cli', '-I', 'vcd', '-i', vcd, '-P', spec, '-A', annotations]
    r = subprocess.run(cmd, capture_output=True, text=True)
    values = []
    for line in r.stdout.splitlines():
        m = re.match(r'^[\w-]+: (.*)$', line)
        if m:
            values.append(m.group(1).strip())
    return values, r.stderr


def as_bytes(values):
    out = []
    for v in values:
        m = re.search(r'(?:^|[\s:])(?:0x)?([0-9A-Fa-f]{1,2})$', v.strip())
        if m:
            out.append(int(m.group(1), 16))
    return out


def window(vcd, pin, pre_us, gap_ms=0):
    letter = {('p%d' % i): chr(ord('a') + i) for i in range(8)}[pin]
    events = []
    t = 0
    for line in open(vcd):
        if line[0] == '#':
            t = int(line[1:])
        elif line.strip() in ('0' + letter, '1' + letter):
            events.append((t, int(line[0])))
    start = None
    for k in range(1, len(events)):
        quiet = (events[k][0] - events[k - 1][0]) / 50000.0
        if events[k][1] == 0 and events[k - 1][1] == 1 and quiet >= gap_ms:
            start = events[k][0] - int(pre_us * 50)
            if gap_ms == 0:
                break
    out = vcd[:-4] + '_%s_%d.vcd' % (pin, gap_ms)
    with open(out, 'w') as f:
        f.write('$timescale 20 ns $end\n$scope module proem $end\n$var wire 1 a %s $end\n$upscope $end\n$enddefinitions $end\n#0\n1a\n' % pin)
        for t, v in events:
            if t > start:
                f.write('#%d\n%da\n' % (t - start, v))
        f.write('#%d\n%da\n' % (events[-1][0] - start + 500000, events[-1][1]))
    return out


def contains(seq, want):
    n = len(want)
    for i in range(len(seq) - n + 1):
        if seq[i:i + n] == want:
            return True
    return False


def main():
    only = sys.argv[1:]
    failed = 0
    for case in CASES:
        key, name, spec, ann, want = case[:5]
        if only and key not in only:
            continue
        vcd = capture(key)
        if len(case) > 5:
            pin, pre_us, gap_ms = case[5]
            vcd = window(vcd, pin, pre_us, gap_ms)
        values, err = decode(vcd, spec, ann)
        if want and isinstance(want[0], int):
            ok = contains(as_bytes(values), want)
            shown = ' '.join('%02X' % w for w in want)
        else:
            joined = ' | '.join(values)
            ok = all(w in joined for w in want)
            shown = ', '.join(want)
        failed += not ok
        print('  %-50s %-6s %s' % (name, 'PASS' if ok else 'FAIL', shown))
        if not ok:
            print('      decoded: ' + ' | '.join(values[:60]))
            if err.strip():
                print('      sigrok: ' + err.strip().splitlines()[-1])
    print('ALL PASS' if not failed else '%d FAILED' % failed)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
