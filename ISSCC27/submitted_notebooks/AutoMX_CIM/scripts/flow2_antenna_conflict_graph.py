"""Conservative route-conflict closure; selection only, never a DRC waiver.

Native mode exports measured target wire/via boxes from immutable ODBs.
Host closure restores B whenever new(B) overlaps restored-original(A).
"""
import argparse
from collections import defaultdict
import json
import re
from pathlib import Path


def closure(original, candidate, seeds):
    size = 20000
    grid = defaultdict(list)
    def tiles(box, halo=0):
        layer,a,b,c,d = box
        for x in range((a-halo)//size, (c+halo)//size+1):
            for y in range((b-halo)//size, (d+halo)//size+1):
                yield (layer,x,y)
    for name, boxes in candidate.items():
        for box in boxes:
            for tile in tiles(box):grid[tile].append((name,box))
    restored = set(seeds); pending = list(sorted(seeds)); reasons = []
    while pending:
        name = pending.pop()
        for box in original[name]:
            layer,a,b,c,d = box
            halo = 300 if layer in ('met3','met4','met5') else 200
            for tile in tiles(box,halo):
                for other, shape in grid.get(tile, ()):
                    if other in restored:continue
                    _,x,y,u,v=shape
                    if x <= c+halo and a-halo <= u and y <= d+halo and b-halo <= v:
                        restored.add(other);pending.append(other)
                        reasons.append({'restored':other,'conflict_with':name,'layer':layer})
    return {'rollback_nets':sorted(restored),'propagated':reasons,
            'scope':'Conservative wire/via boxes with spacing halo; independent DRC/LVS still mandatory.'}


def read_patches(path, targets):
    result={name:[] for name in targets};active=False;name=None
    pattern=r'(?:NEW|\+ ROUTED|\+ FIXED)\s+(\S+)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+RECT\s+\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)'
    with Path(path).open() as stream:
        for line in stream:
            if line.startswith('NETS '):active=True;continue
            if line.startswith('END NETS'):break
            if not active:continue
            if line.lstrip().startswith('- '):name=line.split()[1]
            if name not in result or 'RECT' not in line:continue
            match=re.search(pattern,line)
            if not match:raise ValueError('unsupported DEF patch format')
            layer=match[1];x,y,a,b,c,d=map(int,match.groups()[1:])
            result[name].append((layer,x+a,y+b,x+c,y+d))
    return result


def wire_boxes(odb, wire, patches=()):
    decoder=odb.dbWireDecoder();decoder.begin(wire)
    boxes=[];point=None;layer=None;patch_count=0
    while True:
        op=decoder.next()
        if op==decoder.END_DECODE:break
        if op in (decoder.PATH,decoder.JUNCTION,decoder.SHORT,decoder.VWIRE):
            point=None;layer=decoder.getLayer()
        elif op in (decoder.POINT,decoder.POINT_EXT):
            next_point=tuple(decoder.getPoint()[:2])
            if point is not None:
                x,y=point;u,v=next_point
                if x!=u and y!=v:raise ValueError('non-Manhattan wire path')
                half=layer.getWidth()//2
                boxes.append((layer.getName(),min(x,u)-half,min(y,v)-half,max(x,u)+half,max(y,v)+half))
            point=next_point
        elif op in (decoder.VIA,decoder.TECH_VIA):
            via=decoder.getVia() if op==decoder.VIA else decoder.getTechVia()
            if point is None:raise ValueError('via without origin')
            x,y=point
            for box in via.getBoxes():
                boxes.append((box.getTechLayer().getName(),x+box.xMin(),y+box.yMin(),x+box.xMax(),y+box.yMax()))
            layer=via.getTopLayer() if layer.getName()==via.getBottomLayer().getName() else via.getBottomLayer()
        elif op==decoder.RECT:
            # This pinned Python binding exposes no int-reference outputs for
            # getRect. Use exact native DEF patches and reconcile cardinality.
            patch_count+=1
        elif op==decoder.RULE:
            raise ValueError('NDR not supported in graph selector')
    if patch_count != len(patches):raise ValueError('ODB/DEF patch cardinality differs')
    boxes.extend(patches)
    if not boxes:raise ValueError('empty target geometry')
    ok,bbox=wire.getBBox()
    # Default end caps overestimate truncated ends. Never allow undercoverage
    # of the native overall bounding box; failed decode cannot select a net.
    if not ok or (min(b[1] for b in boxes)>bbox.xMin() or min(b[2] for b in boxes)>bbox.yMin()
                  or max(b[3] for b in boxes)<bbox.xMax() or max(b[4] for b in boxes)<bbox.yMax()):
        raise ValueError('decoded boxes under-cover native wire bbox')
    return boxes


if __name__=='__main__':
    import odb
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',required=True);p.add_argument('--candidate',required=True)
    p.add_argument('--targets',type=Path,required=True);p.add_argument('--seeds',type=Path,required=True)
    p.add_argument('--patches',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    targets={v['net'] for v in json.loads(a.targets.read_text())['eco_targets']}
    exported=[]
    patch_sets=json.loads(a.patches.read_text())
    for index,filename in enumerate((a.original,a.candidate)):
        db=odb.dbDatabase.create();odb.read_db(db,filename);block=db.getChip().getBlock()
        shapes={name:wire_boxes(odb,block.findNet(name).getWire(),patch_sets[index][name]) for name in targets}
        if index==1:
            for inst in block.getInsts():
                if not inst.getName().startswith('AUTOMX_AE_'):continue
                name=inst.findITerm('DIODE').getNet().getName();box=inst.getBBox()
                for layer in ('li1','met1'):
                    shapes[name].append((layer,box.xMin(),box.yMin(),box.xMax(),box.yMax()))
        exported.append(shapes);odb.dbDatabase.destroy(db)
    seeds=json.loads(a.seeds.read_text())['rollback_nets']
    result=closure(exported[0],exported[1],seeds)
    result.update(target_nets=len(targets),original_boxes=sum(map(len,exported[0].values())),
                  candidate_boxes=sum(map(len,exported[1].values())))
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('AUTOMX_CONFLICT_CLOSURE',len(seeds),'->',len(result['rollback_nets']))
