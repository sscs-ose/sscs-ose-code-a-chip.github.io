"""Find constant-width routing spans and generate legal-area widening candidates."""
import json
import klayout.db as db
from .mesh import METALS


def node_nets(network,design):
    links={}
    for a,b,*_ in network["edges"]:
        links.setdefault(a,set()).add(b);links.setdefault(b,set()).add(a)
    anchors={n:n for n in design["pin_nodes"].values()}
    for d in design["devices"]:
        anchors.update({f't_{d["name"]}_{pin}':net for pin,net in d["nets"].items()})
    result={}
    for node in links:
        if node in result:continue
        pending=[node];group={node}
        while pending:
            for other in links[pending.pop()]:
                if other not in group:group.add(other);pending.append(other)
        names={anchors[n] for n in group if n in anchors}
        if len(names)!=1:raise ValueError(f"Conductor component has ambiguous nets: {names}")
        result.update(dict.fromkeys(group,names.pop()))
    return result


def straight_runs(region,axis):

    coordinates=sorted({(p.x if axis=="x" else p.y) for poly in region.each()
                        for ring in [list(poly.each_point_hull()),*[list(poly.each_point_hole(i)) for i in range(poly.holes())]]
                        for p in ring})
    bounds=region.bbox();active={};completed=[]
    for start,end in zip(coordinates,coordinates[1:]):
        clip=db.Box(start,bounds.bottom,end,bounds.top) if axis=="x" else db.Box(bounds.left,start,bounds.right,end)
        intervals={}
        for piece in (region & db.Region(clip)).each():
            box=piece.bbox()
            if piece.area()!=box.area():continue
            cross=(box.bottom,box.top) if axis=="x" else (box.left,box.right)
            intervals[cross]=(start,end)
        next_active={}
        for cross,(a,b) in intervals.items():
            next_active[cross]=(active[cross][0],b) if cross in active and active[cross][1]==a else (a,b)
        completed += [(axis,*run,*cross) for cross,run in active.items() if cross not in next_active]
        active=next_active
    completed += [(axis,*run,*cross) for cross,run in active.items()]
    return completed


def discover(project,source,network,design):
    layout=db.Layout();layout.read(str(source));top=layout.cell(project["top_cell"]);unit=layout.dbu
    rules=project["actions"];nets=node_nets(network,design)
    protected=db.Region()
    for instance in top.each_inst():protected.insert(instance.bbox())
    for number,datatype in [(v[0],16) for v in METALS.values()]+[(66,44),(67,44),(68,44),(69,44),(70,44),(71,44)]:
        protected+=db.Region(top.begin_shapes_rec(layout.layer(number,datatype)))
    for rectangle in rules.get("exclude_boxes_um",[]):
        protected.insert(db.DBox(*rectangle).to_itype(unit))
    protected=protected.merged()
    actions=[];spans=[];rejected=[]
    for layer in rules["layers"]:
        index=layout.layer(*METALS[layer][:2])
        metal=db.Region(top.begin_shapes_rec(index)).merged()
        by_net={}
        for polygon in metal.each():
            if (db.Region(polygon)-protected).is_empty():
                continue
            labels={nets[node] for node,kind,x,y,*_ in network["nodes"]
                    if kind==layer and polygon.inside(db.DPoint(x,y).to_itype(unit))}
            if len(labels)!=1:raise ValueError(f"Cannot assign one net to a {layer} conductor.")
            net=labels.pop();by_net.setdefault(net,db.Region()).insert(polygon)
        for net,region in sorted(by_net.items()):
            if net not in rules["nets"]:continue
            for axis,a,b,c,d in straight_runs((region-protected).merged(),"x")+straight_runs((region-protected).merged(),"y"):
                clearance=round(rules.get("end_clearance_um",.2)/unit)
                a+=clearance;b-=clearance
                length=(b-a)*unit;width=(d-c)*unit
                if length<rules.get("minimum_length_um",2) or length<rules.get("minimum_aspect_ratio",3)*width:continue
                bounds=[a,c,b,d] if axis=="x" else [c,a,d,b]
                span={"id":f'{layer}_{axis}_{len(spans):03d}',"net":net,"layer":layer,"axis":axis,
                      "bounds_um":[x*unit for x in bounds],"length_um":length,"old_width_um":width}
                spans.append(span)
                for option,increment in enumerate(rules["width_increments_um"]):

                    half=round(increment/(2*unit))
                    if half<=0 or abs(half*2*unit-increment)>1e-9:
                        raise ValueError("Width options must move both edges by an integer database unit.")
                    box=db.Box(a,c-half,b,d+half) if axis=="x" else db.Box(c-half,a,d+half,b)
                    added=db.Region(box)-metal
                    area=added.area()*unit**2
                    candidate={**span,"id":f'{span["id"]}_w{option:02d}',"box_um":[v*unit for v in (box.left,box.bottom,box.right,box.top)],
                               "new_width_um":width+increment,"added_area_um2":area}
                    reason=None
                    if area>rules["budget_um2"]+1e-9:reason="area budget"
                    elif area<=0:reason="no added conductor"
                    elif not (added & protected).is_empty():reason="protected geometry"
                    elif any(not added.interacting(other.sized(1)).is_empty() for name,other in by_net.items() if name!=net):reason="other net"
                    if reason:rejected.append({**candidate,"reason":reason})
                    else:actions.append(candidate)
    return {"spans":spans,"actions":actions,"rejected":rejected}


def widen(project,source,target,action):
    layout=db.Layout();layout.read(str(source));top=layout.cell(project["top_cell"])
    index=layout.layer(*METALS[action["layer"]][:2])
    top.shapes(index).insert(db.DBox(*action["box_um"]))
    options=db.SaveLayoutOptions();options.format="OASIS";options.write_context_info=True
    layout.write(str(target),options)


def resistance_changes(network,action):
    x0,y0,x1,y1=action["box_um"]
    nodes={n:(x,y) for n,layer,x,y,*_ in network["nodes"]}
    result={}
    for k,(a,b,r,layer,_) in enumerate(network["edges"]):
        if layer!=action["layer"] or a not in nodes or b not in nodes:continue
        ax,ay=nodes[a];bx,by=nodes[b]
        if action["axis"]=="y":ax,ay,bx,by=ay,ax,by,bx
        lo,hi,bottom,top=(x0,x1,y0,y1) if action["axis"]=="x" else (y0,y1,x0,x1)
        length=abs(ax-bx)
        if abs(ay-by)>1e-9 or length<1e-12 or not bottom<=ay<=top:continue
        overlap=max(0,min(max(ax,bx),hi)-max(min(ax,bx),lo))
        if overlap:result[k]=r*overlap/length*(action["old_width_um"]/action["new_width_um"]-1)
    return result
