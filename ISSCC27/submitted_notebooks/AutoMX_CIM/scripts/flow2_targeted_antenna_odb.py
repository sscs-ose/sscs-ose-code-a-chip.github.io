"""Measured diode ECO worker for the pinned OpenROAD Python 3.6 runtime.

All old functional/decap/tap instances stay locked. Only ordinary fill cells
are removed. Unaffected signal wires are marked FIXED for the route trial.
The output is a candidate, never evidence of routed connectivity by itself.
"""
import argparse
import json
from pathlib import Path

PREFIX = 'AUTOMX_AE_'


def validate_targets(targets):
    seen = set()
    if not targets:
        raise ValueError('empty measured target list')
    for item in targets:
        key = (item['net'], item['pin'])
        if key in seen or '/' not in item['pin']:
            raise ValueError('duplicate or malformed antenna target')
        if item['pin'].split('/')[0] in ('core_i', 'condition_i', 'adc_i'):
            raise ValueError('analog macro antenna target requires a separate plan')
        seen.add(key)


def prepare(odb, db, targets, copies):
    validate_targets(targets)
    if copies not in (1, 2, 3):
        raise ValueError('one to three diodes per measured pin required')
    block = db.getChip().getBlock()
    master = db.findMaster('sky130_fd_sc_hd__diode_2')
    if not master or not master.findMTerm('DIODE'):
        raise ValueError('native diode master/port missing')
    insts = {i.getName(): i for i in block.getInsts()}
    if any(n.startswith(PREFIX) for n in insts):
        raise ValueError('fresh source required; ECO prefix already present')
    endpoints = []
    for item in targets:
        name, port = item['pin'].rsplit('/', 1)
        inst = insts.get(name)
        pin = inst.findITerm(port) if inst else None
        if (not inst or inst.getMaster().getName() != item['master'] or not pin
                or pin.getIoType() != 'INPUT' or not pin.getNet()
                or pin.getNet().getName() != item['net']):
            raise ValueError('measured target changed: '+item['pin'])
        endpoints.append((item, inst, pin.getNet()))
    rails = {n: block.findNet(n) for n in ('VPWR', 'VGND')}
    if not all(rails.values()):
        raise ValueError('missing power rails')
    # Validate all source endpoints before mutating the candidate database.
    removed = 0
    for inst in list(block.getInsts()):
        if '__fill_' in inst.getMaster().getName():
            odb.dbInst.destroy(inst)
            removed += 1
        else:
            inst.setPlacementStatus('LOCKED')
    nets = set(t['net'] for t in targets)
    # Incremental DEF import preserves an existing dbWire rather than replacing
    # its ROUTED property. Drop only these candidate wires, then the host's
    # routing-only DEF restores the identical paths as FIXED before placement.
    removed_wires = 0
    for net in block.getNets():
        wire = net.getWire()
        if wire and net.getName() not in nets:
            odb.dbWire.destroy(wire)
            removed_wires += 1
    created = []
    for index, (item, sink, net) in enumerate(endpoints):
        x, y = sink.getLocation()
        for k in range(copies):
            name = PREFIX+str(index)+'_'+str(k)
            diode = odb.dbInst_create(block, master, name)
            diode.setOrient(sink.getOrient())
            diode.setLocation(max(block.getDieArea().xMin(), x-(k+1)*master.getWidth()), y)
            diode.setPlacementStatus('PLACED')
            diode.findITerm('DIODE').connect(net)
            for port, rail in (('VPWR', 'VPWR'), ('VPB', 'VPWR'), ('VGND', 'VGND'), ('VNB', 'VGND')):
                pin = diode.findITerm(port)
                if pin:
                    pin.connect(rails[rail])
            created.append({'instance': name, 'net': net.getName(), 'target': item['pin']})
    return {'status': 'UNROUTED_DIODE_CANDIDATE', 'removed_fillers': removed,
            'preserved_decaps_taps': True,
            'unaffected_wires_pending_fixed_import': removed_wires,
            'target_nets': len(nets), 'created': created,
            'required_checks': ['legalization', 'routed connectivity', 'DRC', 'antenna', 'LVS', 'STA']}


if __name__ == '__main__':
    import odb
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--targets', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--copies', type=int, default=3)
    a = p.parse_args()
    db = odb.dbDatabase.create()
    odb.read_db(db, a.input)
    report = prepare(odb, db, json.loads(a.targets.read_text())['eco_targets'], a.copies)
    odb.write_db(db, a.output)
    a.report.write_text(json.dumps(report, indent=2)+'\n')
    print('AUTOMX_TARGETED_DIODES_DONE '+str(len(report['created'])))
