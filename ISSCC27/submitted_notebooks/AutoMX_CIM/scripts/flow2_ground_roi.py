"""Export exact GDS geometry around PG bridges for a bounded local DRC.

Clipped edges are artificial. This file is not a whole-top DRC runset.
"""
import json
import os
from pathlib import Path
import pya

folder = Path(os.environ['AUTOMX_PG_WORK'])
source = pya.Layout()
source.read(os.environ['AUTOMX_PG_GDS'])
top = source.cell('automx_cim_mixed_signal_proto')
if top is None:
    raise ValueError('wrapper top missing')
output = pya.Layout()
output.dbu = source.dbu
clipped = output.create_cell('automx_ground_rois')
boxes = []
for item in json.loads((folder/'plan.json').read_text()):
    x1, y1, x2, y2 = item['rect_um']
    boxes.append(pya.Box(*[round(x/source.dbu) for x in (x1-20, y1-20, x2+20, y2+20)]))
for layer in source.layer_indexes():
    region = pya.Region()
    for box in boxes:
        region += pya.Region(top.begin_shapes_rec_touching(layer, box))&pya.Region(box)
    if not region.is_empty():
        clipped.shapes(output.layer(source.get_info(layer))).insert(region)
output.write(str(folder/'ground_rois.gds'))
print('AUTOMX_GROUND_CONTEXT_ROI_EXPORTED')
