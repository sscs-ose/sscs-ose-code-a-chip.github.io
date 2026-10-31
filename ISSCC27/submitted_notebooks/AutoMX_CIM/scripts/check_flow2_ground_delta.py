"""Prove the ECO changes only two M4 rectangles, without flattening all layers."""
from collections import Counter
import json
import os
from pathlib import Path
import pya

folder = Path(os.environ['AUTOMX_PG_WORK'])
before, after = pya.Layout(), pya.Layout()
before.read(os.environ['AUTOMX_PG_SOURCE'])
after.read(os.environ['AUTOMX_PG_GDS'])
top_name = 'automx_cim_mixed_signal_proto'
if before.dbu != after.dbu:
    raise ValueError('database units changed')


def instances(cell, layout):
    result = Counter()
    for inst in cell.each_inst():
        array = inst.cell_inst
        result[(layout.cell(array.cell_index).name, array.cplx_trans.to_s(),
                array.na, array.nb, array.a.x, array.a.y, array.b.x, array.b.y)] += 1
    return result


old_cells = {c.name: c for c in before.each_cell()}
new_cells = {c.name: c for c in after.each_cell()}
if old_cells.keys() != new_cells.keys():
    raise ValueError('cell hierarchy names changed')
old_layers = {(before.get_info(i).layer, before.get_info(i).datatype): i for i in before.layer_indexes()}
new_layers = {(after.get_info(i).layer, after.get_info(i).datatype): i for i in after.layer_indexes()}
if old_layers.keys() != new_layers.keys():
    raise ValueError('layers changed')
checked = 0
for name, cell in old_cells.items():
    new = new_cells[name]
    if instances(cell, before) != instances(new, after):
        raise ValueError('instance placement/hierarchy changed: '+name)
    for layer, index in old_layers.items():
        if name == top_name and layer == (71, 20):
            continue
        old_shapes = Counter(s.to_s() for s in cell.shapes(index).each())
        new_shapes = Counter(s.to_s() for s in new.shapes(new_layers[layer]).each())
        if old_shapes != new_shapes:
            raise ValueError('unplanned geometry/text changed: '+name+' '+str(layer))
        checked += sum(old_shapes.values())
old_m4 = pya.Region(old_cells[top_name].shapes(old_layers[(71, 20)]))
new_m4 = pya.Region(new_cells[top_name].shapes(new_layers[(71, 20)]))
bridges = pya.Region()
for item in json.loads((folder/'plan.json').read_text()):
    bridges.insert(pya.Box(*[round(v/before.dbu) for v in item['rect_um']]))
if not ((old_m4+bridges)^new_m4).is_empty() or not (old_m4-new_m4).is_empty():
    raise ValueError('M4 delta differs from the planned bridges')
report = {'status': 'PASS_ONLY_TWO_M4_BRIDGES', 'cells_checked': len(old_cells),
          'other_shapes_and_text_checked': checked,
          'added_m4_area_um2': (new_m4-old_m4).area()*before.dbu**2,
          'removed_m4_area_um2': (old_m4-new_m4).area()*before.dbu**2,
          'scope': 'All instance names/placements and non-target geometry/text compared; '
                   'top M4 compared as exact region union with the two specified bridges. '
                   'Not an extraction, DRC or electrical qualification.'}
(folder/'gds_delta.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
