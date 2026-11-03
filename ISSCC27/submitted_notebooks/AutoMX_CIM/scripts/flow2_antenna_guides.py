"""Extend only measured ECO nets' guides to their legalized diodes.

Native Python mode exports diode bounding boxes; host mode calls augment.
Guide rectangles are hints, not fabricated routing or signoff evidence.
"""
import argparse
import json
import math
from pathlib import Path


def augment(text, locations, grid=6900, targets_only=False):
    groups, key, records = [], None, []
    for line in text.splitlines():
        line = line.strip()
        if not line or line == '(':
            continue
        if line == ')':
            if key is None:
                raise ValueError('unmatched guide close')
            groups.append((key, records)); key, records = None, []
        elif key is None:
            key = line
        else:
            fields = line.split()
            if len(fields) != 5:
                raise ValueError('invalid guide rectangle')
            records.append(tuple(map(int, fields[:4]))+(fields[4],))
    if key is not None:
        raise ValueError('unfinished guide net')
    pending = {}
    for item in locations:
        pending.setdefault(item['net'].replace('\\', ''), []).append(item['bbox'])
    target_names = set(pending)
    output, patches = [], []
    for name, records in groups:
        if targets_only and name.replace('\\', '') not in target_names:
            continue
        additions = []
        for bbox in pending.pop(name.replace('\\', ''), []):
            cx, cy = (bbox[0]+bbox[2])//2, (bbox[1]+bbox[3])//2
            candidates = [r for r in records if r[4] in ('met1', 'met2', 'met3', 'met4', 'met5')]
            if not candidates:
                raise ValueError('target net has no metal guide')
            def nearest(r):
                return max(r[0]-cx, 0, cx-r[2])+max(r[1]-cy, 0, cy-r[3])
            old = min(candidates, key=nearest)
            px, py = min(max(cx, old[0]), old[2]), min(max(cy, old[1]), old[3])
            # Existing guides are on a 6.9 um grid in the pinned native run.
            rect = (max(0, (min(bbox[0], px)//grid-1)*grid),
                    max(0, (min(bbox[1], py)//grid-1)*grid),
                    (max(bbox[2], px)//grid+2)*grid,
                    (max(bbox[3], py)//grid+2)*grid)
            for layer in range(1, max(2, int(old[4][-1]))+1):
                additions.append(rect+('met'+str(layer),))
        if additions:
            patches.append({'net': name, 'rectangles': len(set(additions))})
        output += [name, '(']
        output += [' '.join(map(str, r)) for r in records+sorted(set(additions))]
        output.append(')')
    if pending:
        raise ValueError('ECO net missing from source guides: '+repr(sorted(pending)))
    return '\n'.join(output)+'\n', patches


if __name__ == '__main__':
    import odb
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--odb', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    db = odb.dbDatabase.create(); odb.read_db(db, a.odb)
    locations = []
    for inst in db.getChip().getBlock().getInsts():
        if not inst.getName().startswith('AUTOMX_AE_'):
            continue
        box = inst.getBBox()
        locations.append({'instance': inst.getName(),
                          'net': inst.findITerm('DIODE').getNet().getName(),
                          'bbox': [box.xMin(), box.yMin(), box.xMax(), box.yMax()]})
    a.output.write_text(json.dumps(locations, indent=2)+'\n')
    print('AUTOMX_DIODE_LOCATIONS '+str(len(locations)))
