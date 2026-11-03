"""KLayout server worker: validate/append only measured ground M4 bridges."""
import json
import os
from pathlib import Path
import pya

folder = Path(os.environ['AUTOMX_PG_WORK'])
plan = json.loads((folder/'plan.json').read_text())
layout = pya.Layout()
layout.read(os.environ['AUTOMX_PG_GDS'])
top = layout.cell('automx_cim_mixed_signal_proto')
layer = layout.find_layer(71, 20)
if top is None or layer is None:
    raise ValueError('native top/met4 missing')


def box(rect):
    return pya.Box(*[round(x/layout.dbu) for x in rect])


for target in plan:
    bridge = box(target['rect_um'])
    margin = round(.3/layout.dbu)
    roi = bridge.enlarged(margin, margin)
    actual = pya.Region(top.begin_shapes_rec_touching(layer, roi))
    allowed = pya.Region(box(target['pin_um']))+pya.Region(box(target['stripe_um']))
    foreign = (actual-allowed)&pya.Region(roi)
    pin = (actual&pya.Region(box(target['pin_um'])))&pya.Region(bridge)
    strap = (actual&pya.Region(box(target['stripe_um'])))&pya.Region(bridge)
    if not foreign.is_empty() or pin.is_empty() or strap.is_empty():
        raise ValueError('bridge obstruction or missing physical landing: '+target['instance'])
    target['foreign_clearance_polygons'] = foreign.count()
    target['pin_contact_area_um2'] = pin.area()*layout.dbu**2
    target['strap_contact_area_um2'] = strap.area()*layout.dbu**2
(folder/'geometry.json').write_text(json.dumps(plan, indent=2)+'\n')
for target in plan:
    top.shapes(layer).insert(box(target['rect_um']))
layout.write(str(folder/'ground_repaired.gds'))
print('AUTOMX_GROUND_GDS_REPAIRED')
