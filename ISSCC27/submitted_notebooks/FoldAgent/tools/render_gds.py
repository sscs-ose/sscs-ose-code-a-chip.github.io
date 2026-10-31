"""Read existing GDS, check exported structure and render views; no design analysis."""
import pya
import json,re,hashlib,collections
from pathlib import Path
package=Path(__file__).resolve().parents[1]
out=package/"data/gds";out.mkdir(exist_ok=True)
palette={67:("Local interconnect","#64748b"),68:("M1","#5b9fc8"),69:("M2","#65d4ba"),70:("M3","#efba55"),71:("M4","#be91ed"),72:("M5","#f37883")}
views={"L0-full":dict(die="L0",box=[0,0,1000,1000],size=[1600,1600],kind="metal"),
"L1-full":dict(die="L1",box=[0,0,1000,1000],size=[1600,1600],kind="metal"),
"L0-link":dict(die="L0",box=[20,210,70,260],size=[1200,1200],kind="metal"),
"L1-diodes":dict(die="L1",box=[797,32,805,40],size=[1200,1200],kind="diode")}
results={}
for die,name in [("L0","control-storage.gds"),("L1","compute.gds")]:
    path=package/"physical/gds"/name
    ly=pya.Layout();ly.read(str(path))
    tops=list(ly.top_cells());assert len(tops)==1
    top=tops[0];assert top.name=={"L0":"lb_l0","L1":"lb_l1"}[die]
    assert abs(ly.dbu-.001)<1e-12
    assert all(not c.is_empty() for c in ly.each_cell())
    text=(package/"physical/gds"/(die+".def")).read_text()
    section=re.search(r"^COMPONENTS (\d+) ;(.*?)^END COMPONENTS",text,re.M|re.S)
    expected=collections.Counter(re.findall(r"^\s*-\s+\S+\s+(\S+)\s+\+",section[2],re.M))
    assert sum(expected.values())==int(section[1])
    actual=collections.Counter()
    diode_instances=[]
    for inst in top.each_inst():
        master=ly.cell(inst.cell_index).name
        if master in expected:
            actual[master]+=max(inst.na,1)*max(inst.nb,1)
        props=inst.properties()
        if any(str(v) in ["R3A2_242","R3A2_244"] for v in props.values()):
            diode_instances.append(dict(properties={str(k):str(v) for k,v in props.items()},master=master,transform=str(inst.dtrans),bbox=str(inst.dbbox())))
    assert actual==expected,(die,"master instance counts")
    pins=re.search(r"^PINS (\d+) ;(.*?)^END PINS",text,re.M|re.S)
    records=re.findall(r"^\s*- (\S+)(.*?);",pins[2],re.M|re.S);assert len(records)==int(pins[1])
    exported={}
    for layer in ly.layer_indexes():
        info=ly.get_info(layer)
        if info.datatype==16:
            exported[info.layer]={str(s.bbox()) for s in top.shapes(layer).each() if not s.is_text()}
    for pin,body in records:
        box=re.search(r"\+ LAYER (met[1-5]|li1) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)",body)
        at=re.search(r"\+ (?:FIXED|PLACED) \( (-?\d+) (-?\d+) \) (\S+)",body)
        assert box and at and at[3]=="N",(pin,"pin parse/orientation")
        dx,dy=int(at[1]),int(at[2])
        bounds=pya.Box(int(box[2])+dx,int(box[3])+dy,int(box[4])+dx,int(box[5])+dy)
        number=67 if box[1]=="li1" else 67+int(box[1][-1])
        assert str(bounds) in exported[number],(die,pin,"missing pin rectangle")
    results[die]=dict(top=top.name,gds_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cell_count=ly.cells(),dbu_um=ly.dbu,bbox_um=str(top.dbbox()),master_instance_count=sum(actual.values()),used_master_count=len(expected),nonempty_cells=True,pin_rectangles_matched=len(records),diode_instances=diode_instances)
    print(die,results[die],flush=True)
    view=pya.LayoutView();view.show_layout(ly,False);view.max_hier()
    view.set_config("background-color","#0b1323");view.set_config("grid-visible","false");view.set_config("text-visible","false")
    for key,spec in views.items():
        if spec["die"]!=die:continue
        view.clear_layers()
        layers=[(n,d) for n in range(68,73) for d in [20,16,44]]
        if spec["kind"]=="diode":
            layers=[(65,20),(65,44),(66,20),(66,44),(67,20),(67,44),(68,20),(68,16),(68,44),(69,20),(69,16)]
        for number,datatype in layers:
            if ly.find_layer(number,datatype) is None:continue
            color=palette.get(number,("Device","#5b6478"))[1]
            if datatype==44:color="#d6dae3"
            props=pya.LayerPropertiesNode();props.source=str(number)+"/"+str(datatype)+"@1"
            props.name=str(number)+"/"+str(datatype);props.fill_color=int(color[1:],16);props.frame_color=int(color[1:],16)
            props.dither_pattern=0;props.visible=True
            view.insert_layer(view.end_layers(),props)
        view.update_content()
        view.save_image_with_options(str(out/(key+".png")),spec["size"][0],spec["size"][1],0,2,0,pya.DBox(*spec["box"]),False)
        spec["displayed_layers"]=layers;spec["sha256"]=hashlib.sha256((out/(key+".png")).read_bytes()).hexdigest()
        print("rendered",key,flush=True)
    view._destroy()
report=dict(operation="Readback and graphics only",new_design_experiments=0,new_DRC_LVS_runs=0,layouts=results,views=views,palette={str(k):v for k,v in palette.items()},api_reference="https://www.klayout.de/doc-qt5/code/class_LayoutView.html")
(out/"render.json").write_text(json.dumps(report,indent=2)+"\n")
