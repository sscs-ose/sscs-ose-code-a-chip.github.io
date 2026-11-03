#!/usr/bin/env python3
"""Draw the repository's eight-NMOS compute cell with transistor symbols.

Produces a clean vector schematic for figures, verified against the exact
SPICE topology. Does not run, modify or characterize physical design inputs.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.render_ternary_cell_schematic import _source, _verify

INK='#202124'
MUTED='#59616b'
POS='#195d96'
NEG='#b66a16'
WEIGHT='#713ea4'
ACT='#087b70'


def text(x,y,value,size=17,*,color=INK,anchor='middle',bold=False):
    return (f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{700 if bold else 400}">{escape(value)}</text>')


def line(x1,y1,x2,y2,*,color=INK,width=2.8):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')


def dot(x,y,color=INK,r=4):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'


def nfet(x,y,gate,instance,gate_color):
    """Arrowless enhancement NMOS symbol; all bulk connections stated below.

    External drain/source lie at (x,y-45)/(x,y+45). Three channel strokes
    distinguish the transistor channel from the gate and connecting wires.
    No implicit source-to-bulk strap is drawn.
    """
    out=[line(x,y-45,x,y-22),line(x,y-22,x-18,y-22),
         line(x-18,y+22,x,y+22),line(x,y+22,x,y+45),
         line(x-36,y-25,x-36,y+25,color=gate_color,width=3.2),
         line(x-86,y,x-36,y,color=gate_color),
         text(x-94,y+6,gate,18,color=gate_color,anchor='end',bold=True),
         text(x+15,y+5,instance,14,color=MUTED,anchor='start')]
    out.extend(line(x-18,y+a,x-18,y+b,width=3.3) for a,b in ((-22,-10),(-5,5),(10,22)))
    return out


def render(root,output):
    root,output=Path(root).resolve(),Path(output).resolve()
    source=_source(root);source_sha=_verify(source)
    items=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="840" '
           'viewBox="0 0 1280 840" role="img" aria-label="Eight-NMOS differential ternary compute schematic">',
           '<title>AutoMX-CIM transistor-level ternary compute cell</title>',
           '<desc>'+escape(f'Source: {source.relative_to(root).as_posix()}; SHA256: {source_sha}. '
            'Eight SKY130 NMOS, four series discharge paths. All bulk terminals connect to VSUBS; '
            'bulk wires omitted. External WPOS/WNEG control signals, not an internal SRAM storage latch.')+'</desc>',
           '<rect x="0" y="0" width="1280" height="840" fill="#ffffff"/>',
           text(640,48,'Differential ternary compute cell',30,bold=True),
           text(640,80,'8 NMOS  ·  4 discharge paths  ·  ΔV = V(BLN) − V(BLP)',18,color=MUTED),
           line(220,140,520,140,color=POS,width=4),
           line(820,140,1120,140,color=NEG,width=4),
           text(220,122,'BLP',23,color=POS,anchor='start',bold=True),
           text(820,122,'BLN',23,color=NEG,anchor='start',bold=True),
           text(375,196,'Positive-product paths',17,color=POS),
           text(975,196,'Negative-product paths',17,color=NEG)]
    branches=[(250,'WPOS','WLP','NPP','XPP','+w, +a',POS),
              (500,'WNEG','WLN','NPN','XPN','−w, −a',POS),
              (850,'WNEG','WLP','NNP','XNP','−w, +a',NEG),
              (1100,'WPOS','WLN','NNN','XNN','+w, −a',NEG)]
    for x,w,a,node,inst,sign,color in branches:
        items += [dot(x,140,color),line(x,140,x,250,color=color),
                  *nfet(x,295,w,inst+'_W',WEIGHT),
                  line(x,340,x,410),dot(x,375),
                  text(x+15,380,node,13,color=MUTED,anchor='start'),
                  *nfet(x,455,a,inst+'_A',ACT),
                  line(x,500,x,590),dot(x,590),
                  text(x,674,sign,17,color=color,bold=True)]
    items += [line(205,590,1145,590,width=3.7),
              line(675,590,675,620),dot(675,590),
              line(653,620,697,620,width=3.2),
              line(660,629,690,629,width=3.2),
              line(668,638,682,638,width=3.2),
              text(716,631,'VGND',18,anchor='start',bold=True),
              line(80,710,1200,710,color='#d1d5da',width=1.4),
              text(640,745,'w = WPOS − WNEG;   (WPOS, WNEG):  10 → +1,  01 → −1,  00 → 0',17),
              text(640,775,'Signed activation: WLP / WLN.  Activation magnitude: pulse width.',16,color=MUTED),
              text(640,808,'All NMOS: SKY130 nfet_01v8, W/L = 0.84/0.15 µm; all bulks → VSUBS (wires omitted).',15,color=MUTED),
              '</svg>']
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('\n'.join(items)+'\n',encoding='utf-8')
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--output',type=Path,default=Path('docs/figures/ternary_cell_transistor_paper.svg'))
    a=p.parse_args();root=a.root.resolve();dest=a.output if a.output.is_absolute() else root/a.output
    print(render(root,dest))
