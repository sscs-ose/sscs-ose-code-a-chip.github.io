#!/usr/bin/env python3
"""Split the unmodified ORFS sky130hd.lydrc BEOL + OFFGRID checks into part decks for the chip sign-off.

Why: in deep mode the deck keeps every derived layer alive until the end. On the chip rule ct.1 (the edges
of every mcon) alone lifts KLayout from 6 to 21.6 GB, and the m1 rules that follow outgrew the memory of
the build machine; the deck's tiled mode holds the chip flat and failed earlier.
Each part deck is the original deck, byte for byte, except that
  * the three section switches select the part (BEOL parts: FEOL=false BEOL=true OFFGRID=false; the
    OFFGRID part: FEOL=false BEOL=false OFFGRID=true), and
  * BEOL rule lines that belong to other parts are replaced by a comment line, so every kept line keeps
    its original line number.
Execution mode (deep, threads(4), tiles) and every rule text are unchanged. The script proves that the BEOL
body lines are partitioned exactly once over the parts, that every part is if/do/end balanced, and that no
part uses a variable assigned only in another part.
usage: python3 scripts/split_beol_deck.py <ORFS sky130hd.lydrc> <out dir>
Each part deck then runs as  klayout -b -rd in_gds=<GDS> -rd report_file=<part>.lyrdb -r <part>.lydrc
SPDX-License-Identifier: Apache-2.0
"""
import hashlib
import json
import re
import sys
from pathlib import Path

DECK, OUT = Path(sys.argv[1]), Path(sys.argv[2])
EXPECTED = '029722ea1fc2cf8c48f09fc670c0b72efb295f799c4eb236b7e9767930ecf772'
raw = DECK.read_bytes()
assert hashlib.sha256(raw).hexdigest() == EXPECTED, 'deck hash'
lines = raw.decode().split('\n')

def find(pattern, start=0):
    for i in range(start, len(lines)):
        if re.match(pattern, lines[i]):
            return i
    raise SystemExit(f'pattern not found: {pattern}')

beol_if = find(r'^if BEOL\s*$')
beol_end = find(r'^end #BEOL', beol_if)
headers = [i for i in range(beol_if, beol_end) if re.match(r'^#   \S', lines[i])]
groups = {}
for k, h in enumerate(headers):
    name = lines[h][4:].strip()
    stop = headers[k + 1] if k + 1 < len(headers) else beol_end
    groups[name] = (h, stop)
body = set(range(headers[0], beol_end))

PARTS = {'p1_li': ['li'], 'p2_ct': ['ct'], 'p3_m1': ['m1'], 'p4_via_m2': ['via', 'm2'],
         'p5_via2_m3': ['via2', 'm3'], 'p6_via3_m4': ['via3', 'm4'],
         'p7_via4_m5_nsm_pad': ['via4', 'm5', 'nsm', 'pad']}
assert sorted(g for p in PARTS.values() for g in p) == sorted(groups), (sorted(groups), PARTS)

def keep_lines(names):
    keep = set()
    for n in names:
        keep |= set(range(*groups[n]))
    return keep

# partition proof
cover = {}
for part, names in PARTS.items():
    for i in keep_lines(names):
        assert i not in cover, f'line {i + 1} in two parts'
        cover[i] = part
assert set(cover) == body, 'BEOL body not fully covered'

ASSIGN = re.compile(r'^\s*([a-z_][a-z0-9_]*)\s*=[^=]')
pre_vars = {m.group(1) for l in lines[:beol_if] if (m := ASSIGN.match(l))}
part_vars = {p: {m.group(1) for i in keep_lines(n) if (m := ASSIGN.match(lines[i]))} for p, n in PARTS.items()}
for p, names in PARTS.items():
    text = '\n'.join(lines[i] for i in sorted(keep_lines(names)))
    for q, vs in part_vars.items():
        if q == p:
            continue
        for v in vs - pre_vars - part_vars[p]:
            assert not re.search(rf'\b{v}\b', text), f'{p} uses {v} assigned in {q}'
    opens = sum(bool(re.match(r'^\s*if\b', lines[i])) or bool(re.search(r'\bdo\b(\s*\|[^|]*\|)?\s*$', lines[i]))
                for i in keep_lines(names))
    ends = sum(bool(re.match(r'^\s*end\b', lines[i])) for i in keep_lines(names))
    assert opens == ends, f'{p}: {opens} openers vs {ends} ends'

SW = {'FEOL': re.compile(r'^FEOL    = false'), 'BEOL': re.compile(r'^BEOL    = true'),
      'OFFGRID': re.compile(r'^OFFGRID = true')}
sw_idx = {k: find(p.pattern) for k, p in SW.items()}

OUT.mkdir(parents=True, exist_ok=True)
manifest = {'source_deck': str(DECK), 'source_sha256': EXPECTED, 'parts': {}}

def write(part, beol, offgrid, keep):
    out = list(lines)
    out[sw_idx['BEOL']] = out[sw_idx['BEOL']].replace('BEOL    = true', f'BEOL    = {"true" if beol else "false"}', 1)
    out[sw_idx['OFFGRID']] = out[sw_idx['OFFGRID']].replace('OFFGRID = true',
                                                             f'OFFGRID = {"true" if offgrid else "false"}', 1)
    for i in body - keep:
        out[i] = f'# (chip v2 split: line belongs to part {cover[i]})'
    assert len(out) == len(lines)
    data = '\n'.join(out).encode()
    path = OUT / f'{part}.lydrc'
    path.write_bytes(data)
    rules = sorted({m.group(1) for i in keep for m in [re.search(r'\.output\("([^"]+)"', lines[i])] if m})
    manifest['parts'][part] = {'deck': path.name, 'sha256': hashlib.sha256(data).hexdigest(),
                               'beol': beol, 'offgrid': offgrid, 'kept_beol_lines': len(keep),
                               'groups': PARTS.get(part, []), 'rule_names': rules}

for part, names in PARTS.items():
    write(part, True, False, keep_lines(names))
write('p8_offgrid', False, True, set())
manifest['beol_body_lines'] = len(body)
(OUT / 'split_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('CHIPV2_DRC_SPLIT=PASS parts=' + ','.join(manifest['parts']) + f' beol_body_lines={len(body)}')
