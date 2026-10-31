"""Order actual routed ECO wires and check native physical connectivity.

Runs in pinned OpenROAD Python; modifies only a disposable in-memory DB.
No missing connection is waived because antenna or router DRC looks better.
"""
import argparse
import json
from pathlib import Path


if __name__ == '__main__':
    import odb
    import openroad
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--odb', required=True)
    p.add_argument('--targets', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    tech = openroad.Tech()
    design = openroad.Design(tech)
    logger = design.getLogger()
    db = odb.dbDatabase.create(); odb.read_db(db, a.odb)
    block = db.getChip().getBlock()
    targets = json.loads(a.targets.read_text())['eco_targets']
    records = []
    for name in sorted({t['net'] for t in targets}):
        net = block.findNet(name)
        if not net or not net.getWire():
            raise ValueError('missing measured routed net: '+name)
        odb.orderWires(logger, net)
        wire = net.getWire()
        decoder = odb.dbWireDecoder(); decoder.begin(wire)
        attached = set()
        while True:
            opcode = decoder.next()
            if opcode == decoder.END_DECODE:
                break
            if opcode == decoder.ITERM:
                pin = decoder.getITerm()
                attached.add(pin.getInst().getName()+'/'+pin.getMTerm().getName())
        missing = []
        for pin in net.getITerms():
            pin_name = pin.getInst().getName()+'/'+pin.getMTerm().getName()
            if pin_name not in attached:
                missing.append(pin_name)
        records.append({'net': name, 'disconnected': net.isDisconnected(),
                        'wire_ordered': net.isWireOrdered(), 'unmapped_iterms': missing,
                        'iterms': len(net.getITerms())})
    failures = [r for r in records if r['disconnected'] or not r['wire_ordered'] or r['unmapped_iterms']]
    report = {'status': 'PASS_NATIVE_ROUTED_CONNECTIVITY' if not failures else 'FAIL_NATIVE_ROUTED_CONNECTIVITY',
              'checked_nets': len(records), 'checked_iterms': sum(r['iterms'] for r in records),
              'failures': failures, 'records': records,
              'scope': 'OpenDB geometric wire ordering/ITerm attachment only; no extracted GDS LVS or transistor claim.'}
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(report['status'], 'nets', len(records), 'failed', len(failures))
    if failures:
        raise SystemExit(1)
