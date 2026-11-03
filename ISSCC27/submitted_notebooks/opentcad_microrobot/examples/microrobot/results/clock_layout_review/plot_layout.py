"""Render actual flat Magic rectangles; not a GDS compliance proof."""
from collections import defaultdict
from pathlib import Path
import json
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch, Rectangle

DEST = Path(__file__).resolve().parent
source = DEST/'provenance/microrobot_clock.mag'
text = source.read_text()
assert 'magscale 1 2' in text
# SKY130 technology CIF scale is 10 nm; magscale 1/2 gives 5 nm per coordinate.
scale_um = .005
layers = defaultdict(list)
labels = {}
layer = None
for line in text.splitlines():
    match = re.fullmatch(r'<< (.*?) >>', line)
    if match:
        layer = match[1]
    fields = line.split()
    if fields and fields[0] == 'rect' and layer not in {'checkpaint', 'labels'}:
        x1, y1, x2, y2 = [int(v)*scale_um for v in fields[1:5]]
        layers[layer].append((x1, y1, x2, y2))
    if fields and fields[0] == 'rlabel' and fields[-1] in {'clk','vdd','vss','bias_n','bias_p'}:
        x1, y1, x2, y2 = [int(v)*scale_um for v in fields[2:6]]
        labels[fields[-1]] = ((x1+x2)/2, (y1+y2)/2)

colors = {'nwell':'#e2d9ef', 'pwell':'#ece4db', 'ndiff':'#74b87a',
          'pdiff':'#d5b263', 'ndiffc':'#478c4e', 'pdiffc':'#aa863d',
          'poly':'#cc5555', 'polycont':'#893d44', 'locali':'#af8eaa',
          'metal1':'#6089bf', 'metal2':'#b378bd', 'metal3':'#d6a440',
          'metal4':'#56a19c', 'metal5':'#9ba9aa', 'mimcap':'#46a79c',
          'mimcapcontact':'#286e69', 'via1':'#4d3e65', 'via2':'#624c2e',
          'via3':'#375c5a', 'viali':'#506070', 'psubdiff':'#aaa77a',
          'nsubdiff':'#aaa77a', 'psubdiffcont':'#777458', 'nsubdiffcont':'#777458'}
order = ['nwell','pwell','psubdiff','nsubdiff','ndiff','pdiff','ndiffc','pdiffc',
         'poly','polycont','locali','metal1','metal2','metal3','metal4','metal5',
         'mimcap','mimcapcontact','viali','via1','via2','via3','psubdiffcont','nsubdiffcont']
fig, ax = plt.subplots(figsize=(15, 4.6))
for layer in [*order, *sorted(set(layers)-set(order))]:
    if layer not in layers:
        continue
    patches = [Rectangle((x,y), xx-x, yy-y) for x,y,xx,yy in layers[layer]]
    ax.add_collection(PatchCollection(patches, facecolor=colors.get(layer, '#aaaaaa'),
                                     edgecolor='none', alpha=.8, rasterized=True))
all_rects = [rect for rects in layers.values() for rect in rects]
xmin = min(r[0] for r in all_rects)
xmax = max(r[2] for r in all_rects)
ymin = min(r[1] for r in all_rects)
ymax = max(r[3] for r in all_rects)
for name, (x,y) in labels.items():
    if name == 'clk':
        target = (x+10, ymax+8)
    else:
        target = (xmin-40, {'vss':53, 'vdd':67, 'bias_n':81, 'bias_p':95}[name])
    ax.annotate(name, (x,y), target, fontsize=9, ha='center',
                arrowprops={'arrowstyle':'->', 'lw':.75, 'color':'#172632'},
                bbox={'facecolor':'white','edgecolor':'none','alpha':.85,'pad':1})
bar_x, bar_y = xmax-110, ymin-10
ax.plot([bar_x,bar_x+100], [bar_y,bar_y], color='#111111', linewidth=3)
ax.text(bar_x+50, bar_y-3, '100 µm', ha='center', va='top', fontsize=9)
ax.set(xlim=(xmin-64,xmax+20), ylim=(ymin-25,ymax+21), aspect='equal',
       xlabel='x (µm)', ylabel='y (µm)')
fig.text(.08, .94, 'Actual full-clock Magic layout — prototype floorplan', fontsize=13)
fig.text(.08, .89, f'Paint extent {xmax-xmin:.2f} × {ymax-ymin:.2f} µm; 29 FET + 7 MIM; 5 nm file grid', fontsize=9)
legend_layers = [name for name in ['nwell','ndiff','pdiff','poly','locali','metal1','metal2','metal3','metal4','mimcap'] if name in layers]
ax.legend(handles=[Patch(color=colors[n], label=n) for n in legend_layers],
          loc='upper center', bbox_to_anchor=(.5,-.28), ncol=10, frameon=False, fontsize=8)
fig.text(.08,.025, 'Rendered from microrobot_clock.mag physical paint and terminal labels; checkpaint omitted. '
         'This preview is not GDS compliance proof or fabrication signoff.', fontsize=8)
fig.subplots_adjust(left=.08,right=.99,bottom=.27,top=.82)
fig.savefig(DEST/'prototype_layout.png',dpi=180)
(DEST/'layout_preview.json').write_text(json.dumps({
    'source':str(source.relative_to(DEST)), 'coordinate_scale_um':scale_um,
    'scale_provenance':'sky130A.tech CIF scalefactor 10 nanometers, Magic magscale 1 2; clock_layout.py parse_pins also specifies 5nm',
    'paint_extent_um':[xmin,ymin,xmax,ymax], 'layer_rectangles':{k:len(v) for k,v in layers.items()},
    'pin_centers_um':labels, 'status':'Prototype floorplan preview; not GDS compliance proof'},indent=2)+'\n')
print(DEST/'prototype_layout.png')
