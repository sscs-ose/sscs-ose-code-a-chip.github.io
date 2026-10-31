"""Native export for signal macro LVS, omitting cells with only PG terminals.

This deliberately does not verify tap/decap/body continuity or transistor LVS.
All cells with any non-PG terminal (including every antenna diode) are kept.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


if __name__ == '__main__':
    import odb
    import openroad
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--odb', required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--lib', action='append', default=[])
    a = p.parse_args()
    tech = openroad.Tech(); design = openroad.Design(tech)
    for lib in a.lib:
        design.evalTclString('read_liberty {'+lib+'}')
    design.readDb(a.odb)
    block = design.getBlock()
    removed = Counter(); retained = []
    for inst in list(block.getInsts()):
        terms = list(inst.getITerms())
        if terms and all(t.getSigType() in ('POWER', 'GROUND') for t in terms):
            removed[inst.getMaster().getName()] += 1
            odb.dbInst.destroy(inst)
        else:
            retained.append(inst)
    # Deletion must never remove a signal/analog/diode endpoint.
    signature = []
    for inst in retained:
        signature.append((inst.getName(), inst.getMaster().getName(),
                          tuple(sorted((t.getMTerm().getName(), t.getNet().getName() if t.getNet() else None)
                                       for t in inst.getITerms()))))
    design.writeDef(str(a.work/'signal_scope.def'))
    design.evalTclString('write_verilog -include_pwr_gnd {'+str(a.work/'signal_scope.v')+'}')
    report = {'status': 'EXPORTED_SIGNAL_MACRO_SCOPE_ONLY', 'retained_instances': len(retained),
              'removed_pg_only_instances': sum(removed.values()), 'removed_masters': dict(removed),
              'retained_connectivity_sha256': hashlib.sha256(repr(sorted(signature)).encode()).hexdigest(),
              'scope': 'PG-only cell instances omitted on BOTH physical and logical sides; no tap/body/decap or full GDS qualification.'}
    (a.work/'export.json').write_text(json.dumps(report, indent=2)+'\n')
    print('AUTOMX_FAST_MACRO_EXPORT_DONE '+str(len(retained)))
