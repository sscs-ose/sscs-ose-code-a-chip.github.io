"""Render the final physical top twice with a fixed layer palette and inspect pixels."""
from pathlib import Path
import argparse,json,os,subprocess
from PIL import Image,ImageChops

RENDER_PROGRAM=r'''
"""Deterministic SKY130 routing overview; raw GDS geometry is unchanged."""
import os,json
from pathlib import Path
import pya

gds=Path(os.environ['AUTOMX_GDS']);png=Path(os.environ['AUTOMX_PNG'])
app=pya.Application.instance();window=app.main_window()
if window is None:raise RuntimeError('KLayout -z with offscreen Qt required')
window.load_layout(str(gds),1);view=window.current_view();cv=view.active_cellview()
cell=cv.layout().cell(os.environ.get('AUTOMX_TOP','automx_cim_mixed_signal_proto'))
if cell is None:raise RuntimeError('requested top missing')
cv.cell=cell;view.add_missing_layers();view.max_hier()
view.set_config('background-color','#ffffff')
view.set_config('grid-visible','false');view.set_config('text-visible','false')
view.set_config('cell-boxes-visible','false')
palette={65:0xb59b7b,66:0xc44e52,67:0x718096,68:0x3979a8,69:0xb45560,
         70:0x3e8c72,71:0x8270a4,72:0xb7953e}
is_top=cell.name=='automx_cim_mixed_signal_proto'
mode=os.environ.get('AUTOMX_RENDER_MODE','overview')
iterator=view.begin_layers();shown=[]
while not iterator.at_end():
    layer=iterator.current();number=layer.source_layer;datatype=layer.source_datatype
    layer.visible=number in palette and datatype in (20,44) and (not is_top or number >= (70 if mode=='overview' else 68))
    if layer.visible:
        layer.fill_color=palette[number];layer.frame_color=palette[number]
        layer.dither_pattern=1 if datatype==20 else 0
        layer.line_style=0;layer.width=1
        shown.append([number,datatype])
    view.set_layer_properties(iterator,layer);iterator.next()
box=cell.dbbox()
if box.empty():raise RuntimeError('empty GDS geometry')
margin=.02*max(box.width(),box.height())
view.zoom_box(pya.DBox(box.left-margin,box.bottom-margin,box.right+margin,box.top+margin))
png.parent.mkdir(parents=True,exist_ok=True)
width=int(os.environ.get('AUTOMX_WIDTH','2400'))
height=max(500,min(2400,round(width*(box.height()+2*margin)/(box.width()+2*margin))))
view.save_image(str(png),width,height)
if not png.is_file() or png.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':raise RuntimeError('PNG export failed')
geometry={'top':cell.name,'cells':cv.layout().cells(),'width_um':box.width(),'height_um':box.height(),
          'render_style':('fixed SKY130 met3–met5 overview' if mode=='overview' else 'fixed SKY130 met1–met5 detail') if is_top else 'fixed SKY130 device/metal view',
          'shown_layers':sorted(shown),'labels_visible':False,'geometry_modified':False}
png.with_suffix('.render.json').write_text(json.dumps(geometry,indent=2))
if os.environ.get('AUTOMX_GEOMETRY'):Path(os.environ['AUTOMX_GEOMETRY']).write_text(json.dumps(geometry,indent=2))
print('KLayout',app.version(),'GDS_READ_AND_RENDER',json.dumps(geometry),flush=True)
app.exit(0)

'''

def render(root,gds,work):
    root=Path(root).resolve();gds=Path(gds).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    script=work/'render.py';script.write_text(RENDER_PROGRAM);images={}
    for label,mode in [('overview','overview'),('overview_repeat','overview'),('detail','detail')]:
        png=work/(label+'.png');env=dict(os.environ,QT_QPA_PLATFORM='offscreen',AUTOMX_GDS=str(gds),AUTOMX_PNG=str(png),AUTOMX_TOP='automx_cim_mixed_signal_proto',AUTOMX_RENDER_MODE=mode)
        result=subprocess.run(['klayout','-z','-x','-r',str(script)],cwd=root,env=env,capture_output=True,text=True,timeout=180)
        (work/(label+'.log')).write_text(result.stdout+result.stderr);assert result.returncode==0,(result.stdout+result.stderr)[-1200:]
        if label!='overview_repeat':
            for line in result.stdout.splitlines():
                if line.startswith('KLayout '):print(line,flush=True)
        assert png.is_file();images[label]=str(png)
    with Image.open(images['overview']) as a,Image.open(images['overview_repeat']) as b:
        assert a.size==b.size and ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox() is None
    report={'status':'PASS','gds':str(gds),'images':images,'overview_repeat_pixel_equal':True,'scope':'Actual final GDS, fixed SKY130 layer/color configuration; two independent overview renders match every pixel.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('FINAL_TOP_KLAYOUT_RENDER_PASS','overview/detail; repeat pixel equal',flush=True);return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--gds',type=Path,required=True);parser.add_argument('--work',type=Path,required=True);args=parser.parse_args();render(args.root,args.gds,args.work)
