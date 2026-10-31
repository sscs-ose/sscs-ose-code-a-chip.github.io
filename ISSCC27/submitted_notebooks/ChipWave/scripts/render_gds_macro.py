"""Run inside KLayout: GDS/PNG/layer-property paths are explicit environment inputs."""
import hashlib
import json
import math
import os
from pathlib import Path
import pya

source=Path(os.environ['CHIP_CASE_GDS'])
output=Path(os.environ['CHIP_CASE_LAYOUT_IMAGE'])
layers=Path(os.environ['CHIP_CASE_LAYER_PROPERTIES'])
assert source.is_file() and layers.is_file()
view=pya.LayoutView()
index=view.load_layout(str(source),True)
top=view.cellview(index).layout().cell('nebula_cpu_npu_top')
assert top is not None
view.select_cell(top.cell_index(),index)
view.load_layer_props(str(layers))
displayed=[]
for node in view.each_layer():
    if node.source_layer>=0:
        node.visible=((67<=node.source_layer<=72 and node.source_datatype==20) or
                      (67<=node.source_layer<=71 and node.source_datatype==44))
        if node.visible:displayed.append([node.source_layer,node.source_datatype])
view.max_hier()
viewport=json.loads(os.environ['CHIP_CASE_VIEWPORT_MICRONS']) if os.environ.get('CHIP_CASE_VIEWPORT_MICRONS') else None
box=top.dbbox()
if viewport is None:
    view.zoom_fit()
else:
    assert len(viewport)==4 and all(type(v) in (int,float) and math.isfinite(v) for v in viewport)
    left,bottom,right,upper=viewport
    assert left<right and bottom<upper
    assert left<=box.left and bottom<=box.bottom and right>=box.right and upper>=box.top
    view.zoom_box(pya.DBox(left,bottom,right,upper))
view.set_config('background-color','#101827')
view.set_config('grid-visible','false')
view.save_image(str(output),1400,1400)
assert output.is_file() and output.stat().st_size>1000
output.with_suffix('.source.json').write_text(json.dumps({'gds_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'gds_input':str(source),'layer_properties_sha256':hashlib.sha256(layers.read_bytes()).hexdigest(),
    'renderer':'KLayout 0.30.12 LayoutView; actual GDS geometry','top_module':top.name,
    'displayed_layers':displayed,'view_scope':'routing/interconnect layers; well, implant and label layers hidden for clarity',
    'requested_viewport_microns':viewport,
    'top_bbox_microns':[box.left,box.bottom,box.right,box.top],
    'verification_status':'read separately from physical acceptance evidence'},indent=2)+'\n')
print('ACTUAL_GDS_IMAGE_RENDERED')
