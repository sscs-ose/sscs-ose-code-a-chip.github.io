"""Native ODB invariants for the targeted diode candidate (Python 3.6).

Checks preserved placement, logical connectivity, supply geometry and every
unaffected signal wire. This is not a substitute for extracted LVS/DRC.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def digest(records):
    h = hashlib.sha256()
    for record in sorted(records):
        h.update((repr(record)+'\n').encode())
    return h.hexdigest()


def fingerprint(odb, path, target_nets):
    db = odb.dbDatabase.create()
    odb.read_db(db, str(path))
    block = db.getChip().getBlock()
    instances, connections = [], []
    diode_count = 0
    for inst in block.getInsts():
        name, master = inst.getName(), inst.getMaster().getName()
        if name.startswith('AUTOMX_AE_'):
            diode_count += 1
            continue
        if '__fill_' in master:
            continue
        instances.append((name, master, tuple(inst.getOrigin()), str(inst.getOrient())))
        connections.append((name, tuple(sorted((p.getMTerm().getName(), p.getNet().getName() if p.getNet() else None)
                                                for p in inst.getITerms()))))
    wires, supplies = [], []
    for net in block.getNets():
        name = net.getName()
        wire = net.getWire()
        if wire and name not in target_nets:
            # OpenDB PATH/JUNCTION/SHORT/VWIRE encode the DEF wire type in
            # their upper three bits. Ignore only that ROUTED/FIXED property;
            # preserve every coordinate, layer, via, junction and term ID.
            raw = hashlib.sha256()
            for index in range(wire.length()):
                opcode = wire.getOpcode(index)
                if opcode & 31 in (0, 1, 2, 3):
                    opcode &= 31
                raw.update(struct.pack('<ii', opcode, wire.getData(index)))
            wires.append((name, raw.hexdigest()))
        for swire in net.getSWires():
            for box in swire.getWires():
                if box.isVia():
                    via = box.getTechVia() or box.getBlockVia()
                    layer = 'VIA:'+via.getName()
                else:
                    layer = box.getTechLayer().getName()
                supplies.append((name, layer, box.xMin(), box.yMin(), box.xMax(), box.yMax()))
    result = {'instances_count': len(instances), 'instances': digest(instances),
              'logical_connections': digest(connections), 'unaffected_wires_count': len(wires),
              'unaffected_wires': digest(wires), 'special_shapes_count': len(supplies),
              'special_geometry': digest(supplies), 'new_diodes': diode_count,
              'nets_count': len(block.getNets())}
    # SWIG owns the DB allocation; destroy after the primitive signature is saved.
    odb.dbDatabase.destroy(db)
    return result


if __name__ == '__main__':
    import odb
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--targets', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    targets = json.loads(a.targets.read_text())['eco_targets']
    nets = {t['net'] for t in targets}
    before = fingerprint(odb, a.source, nets)
    after = fingerprint(odb, a.candidate, nets)
    keys = [k for k in before if k != 'new_diodes']
    differences = [key for key in keys if before[key] != after[key]]
    report = {'status': 'PASS_PRESERVATION_ONLY' if not differences else 'FAIL',
              'source': str(a.source), 'candidate': str(a.candidate),
              'before': before, 'after': after, 'differences': differences,
              'scope': 'No claim of new diode routed connectivity, physical DRC or extracted LVS.'}
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if differences:
        raise SystemExit(1)
