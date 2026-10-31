import collections
import csv
import hashlib
import json
from pathlib import Path
import pya

root = Path(__file__).resolve().parents[2]
out = root / 'build/gds'
top_name = 'nebula_cpu_npu_top'
version = pya.Application.instance().version().removeprefix('KLayout ')
assert version == '0.30.12', version
layout = pya.Layout()
layout.read(str(out / 'nebula_cpu_npu_top.gds'))
assert [c.name for c in layout.top_cells()] == [top_name]
top = layout.cell(top_name)
cells = {c.name: c for c in layout.each_cell()}
with (out / 'odb_instances.tsv').open() as f:
    used = collections.Counter(r['master'] for r in csv.DictReader(f, delimiter='\t'))
with (root / 'reports/pnr/database_instances.tsv').open() as f:
    prior = collections.Counter(r['master'] for r in csv.DictReader(f, delimiter='\t'))
assert used == prior, 'Actual ODB instance inventory differs from upstream evidence'
missing = sorted(set(used) - cells.keys())
empty = sorted(c.name for c in cells.values() if c.is_empty())
actual = collections.Counter()
for inst in top.each_inst():
    actual[layout.cell(inst.cell_index).name] += inst.na * inst.nb if inst.is_regular_array() else 1
assert not missing and not empty
assert all(actual[m] == n for m, n in used.items()), 'GDS master instance multiplicity mismatch'
labels = set()
layers = []
for li in layout.layer_indices():
    info = layout.get_info(li)
    count = sum(c.shapes(li).size() for c in layout.each_cell())
    layers.append(dict(layer=info.layer, datatype=info.datatype, shapes=count))
    for shape in top.shapes(li).each():
        if shape.is_text(): labels.add(shape.text.string)
with (root / 'reports/pnr/database_ports.tsv').open() as f:
    rows = list(csv.DictReader(f, delimiter='\t'))
directions=dict(collections.Counter(row['direction'] for row in rows))
assert directions=={'INPUT':69,'OUTPUT':371,'INOUT':2}
port_key = 'port' if 'port' in rows[0] else 'name'
ports = {r[port_key] for r in rows}
assert ports <= labels, 'Missing top port labels: ' + str(sorted(ports-labels))
assert not any('ram' in m.lower() or 'sram' in m.lower() for m in used)
result = dict(schema_version=1, status='passed', readable=True, top_cell=top_name,
              bytes=(out / 'nebula_cpu_npu_top.gds').stat().st_size,
              sha256=hashlib.sha256((out / 'nebula_cpu_npu_top.gds').read_bytes()).hexdigest(),
              klayout_version=version, dbu_um=layout.dbu, bbox_dbu=str(top.bbox()),
              cell_count=len(cells), odb_instances=sum(used.values()), used_masters=len(used),
              missing_masters=missing, empty_cells=empty, top_port_count=len(ports),
              layer_inventory=layers, master_coverage=[dict(master=m, odb_instances=n, gds_instances=actual[m]) for m,n in sorted(used.items())],
              cells=[dict(name=c.name, bbox_dbu=str(c.bbox())) for c in layout.each_cell()])
(out / 'readability.json').write_text(json.dumps(result,indent=2)+'\n')
(out / 'port_boundary.json').write_text(json.dumps(dict(status='passed',odb_port_directions=directions,
    gds_top_port_labels=len(ports),signal_bits=440,power_ground_bits=2,
    evidence=['reports/pnr/database_ports.tsv','build/gds/readability.json'],
    note='GDS has geometry/labels; directions are joined from the unchanged same-snapshot ODB port table.'),indent=2)+'\n')

# Negative controls alter only isolated GDS copies, never the accepted snapshot.
top.shapes(layout.layer(68,20)).insert(pya.Box(-2000,-2000,-1950,-1000))
layout.write(str(out / 'negative/drc_width.gds'))
layout = pya.Layout()
layout.read(str(out / 'nebula_cpu_npu_top.gds'))
inv = layout.cell('sky130_fd_sc_hd__inv_1')
poly = layout.layer(66,20)
removed = inv.shapes(poly).size()
assert removed > 0 and used[inv.name] > 0
inv.shapes(poly).clear()
layout.write(str(out / 'negative/lvs_missing_gate.gds'))
mutation = dict(drc=dict(layer='68/20', box_dbu=[-2000,-2000,-1950,-1000], expected_category='m1.1'),
                lvs=dict(master=inv.name, layer='66/20', removed_shapes=removed, affected_instances=used[inv.name], expected='Device-extracted LVS mismatch'))
(out / 'negative/mutations.json').write_text(json.dumps(mutation,indent=2)+'\n')
print('GDS_READABILITY_MASTER_PORT_PASS', result['bytes'], len(used), len(ports))
